# 即梦 AI 批量生图故障排查速查表

本文档汇集即梦 AI 批量生图系统在实际运行中可能遭遇的异常现象、底层根因与标准化处理预案。

---

## 1. 退出码（Exit Code）速查与应急预案

| 退出码 | 含义 | 触发原因 | 标准处理预案 |
|---|---|---|---|
| `0` | **成功** | 预检通过或生图全部完成 | 正常交付，展示生成结果与统计数据 |
| `1` | **余额读取失败** | DOM 变更或未加载出余额数字 | 先确认网络是否正常，用 `python cli.py check` 确认登录态，必要时有头模式观察 |
| `2` | **输入参数/提示词错误** | 提示词文件不存在或无有效提示词 | 检查文件路径，确保每行一条有效提示词（非空行、非 `#` 注释） |
| `3` | **未登录 / 登录态失效** | `sid_guard` 过期或未登录 | 运行 `python cli.py login` 弹出有头浏览器，由用户扫码登录 |
| `4` | **付费墙拦截 / 积分不足** | 选到了 VIP 专享档或积分耗尽（`bal == 0`） | 确认模型是否被锁定在 `Seedream 4.7 + 2K`；若积分为 0 提示用户次日重置或充值 |

---

## 2. 常见核心故障与技术应对

### 2.1 登录态失效（Exit Code 3）


- **现象**：输出 `[cli] 登录态: ✗ 未登录`。
- **机制**：即梦依赖 Cookie 中的 `sid_guard` 维持会话，正常有效期约 60 天。当会话过期或被多端登出时失效。
- **解决**：
  ```powershell
  python cli.py login
  ```
  该命令会打开有头窗口并导航至登录页，等待用户本人手机扫码。完成后自动保存持久化 profile。

### 2.2 视口高度不足导致的点击拦截（Pointer Events Intercepted）


- **现象**：Playwright 报 `Element is outside of viewport` 或 `... intercepts pointer events`。
- **机制**：即梦前端编辑器固定在页面底部（y≈739~1039）。当视口高度低于 900（如 1280x720）时，编辑器和底部工具栏会掉出视口外，导致无法点击。
- **解决**：
  - 确保视口高度 ≥ 900。系统默认配置为 `1920x1200`。
  - 若屏幕较小，可通过环境变量覆盖：
    ```powershell
    $env:JIMENG_VIEWPORT="1280x900"; python cli.py run prompts.txt
    ```

### 2.3 纯 HTTP 接口风控：`ret=1019 shark not pass`


- **现象**：直接发起 HTTP 请求返回 `{"ret":"1019","errmsg":"shark not pass"}`。
- **机制**：即梦服务端对 API 开启了严格的客户端特征指纹与流量防护（Shark 风控系统），必须携带合法的 `a_bogus` 与 `msToken` 请求签名。
- **解决**：**切勿尝试绕过浏览器进行纯 HTTP 发包**。所有接口请求均必须由 Playwright 在真实 Edge 页面上下文中调度发包，借由前端 JavaScript 引擎自然生成合规签名。

### 2.4 积分查询接口失效：`ret=1014 system busy`


- **现象**：调用 `/commerce/v1/benefits/user_credit` 恒定返回 `ret=1014`。
- **机制**：该后台接口已对普通 Web 上下文停用或限制。
- **解决**：不要再尝试请求该接口。系统内置了三级 DOM 深度扫描算法，直接从右上角钻石图标区域提取真实积分数字。

### 2.5 找图报错：`FileNotFoundError` 与扩展名漂移


- **现象**：根据提示词拼出的 `.png` 路径报找不到文件。
- **机制**：即梦 CDN 图片 URL 结尾多为 `~tplv-...resize:0:0.image` 无扩展名形态。虽然接口返回的 format 字段标称 `png`，但 CDN 实际下发的大多是 JPEG 或 WEBP。下载器通过文件头魔数嗅探自动将扩展名修正为 `.jpg` 或 `.webp`。
- **解决**：**严禁写死 `.png`**。必须在批次目录中使用真实文件扫描（列目录或 glob）获取落盘文件名。

### 2.6 多进程占用导致浏览器启动崩溃


- **现象**：报 `BrowserType.launch_persistent_context: Target page, context or browser has been closed`。
- **机制**：Edge 用户配置目录（Profile）具有进程排他锁，不能同时被多个 Playwright 实例或常规 Edge 窗口打开。
- **解决**：检查并关闭可能残留的后台 Edge / Python 进程，确认同一时间只有一个 batch 任务在运行。

### 2.7 出图全是方图 / 比例不生效（2048×2048）



- **现象**：明明选了 `4:3` 或 `16:9`，下载下来的图都是 `2048×2048`。
- **根因（三层）**：
  1. **只改了 `image_ratio`，没改 `large_image_info.width/height`**。服务端按 `large_image_info` 出图，`image_ratio` 只是配套标记 → 必须两者同步改。
  2. **用了「智能比例」**。该档请求体里 `image_ratio` 字段整个不存在（只有 `intelligent_ratio=true`），服务端会自己算构图——**但结果不稳定**：实测既出现过 2048×2048 方图，也出现过 2304×1728。UI 手动提交同样如此，是**平台行为**，不是代码问题。
  3. **枚举值写反**。`16:9` 是 `3`、`4:3` 是 `4`，写反会导致比例错乱。
- **解决**：
  - **要确定尺寸就必须显式指定比例**（`4:3`/`16:9`/`3:4`/`9:16`…），不要指望 `智能比例`。
  - 改完代码先跑零成本校验（见 [ratio-and-size.md](ratio-and-size.md) 第 6 节），确认请求体字段正确再真实提交。
  - 全部枚举对照见 [ratio-and-size.md](ratio-and-size.md)。

### 2.8 提交报 `invalid parameter`（ret=1000）而账号正常



- **现象**：`[submit] 提交结果: ✗ invalid parameter (A-template) ret=1000`，响应 `data={aigc_data=None, fail_code=1001}`。
- **机制**：保存的提交模板里 `workspace_id` 属于登录时那个账号。**换账号后旧模板里的 workspace 就不属于当前用户了**，服务端拒绝。
- **解决**：程序会自动降级到 UI 提交（策略 B）并在成功后重新保存模板，**无需手工干预**。下次提交即可恢复 A-template 快路径。
- **注意**：这是设计内的自我修复，不要因此去删模板或重试 A，反而可能重复扣费。

### 2.9 账号更换后单价突然变贵（16 积分/条）



- **现象**：新账号首跑时按 `Seedream 5.0 Pro + 2K + 2张` 提交，一条扣 16 积分。
- **机制**：新会话的页面默认档位是**付费档**（Pro + 2K + 2张）。程序靠 `ensure_free_setting()` 降档，若某次跳过或失败就会按默认档扣费。
- **解决**：任务开始前用 `python cli.py setting` 确认档位是 `Seedream 4.7 / 2K / 1张 / 单价 1`。看到单价 > 1 立刻停下排查。

### 2.10 `--count N` 不生效，永远只出 1 张



- **现象**：传了 `--count 2`，日志却是 `档位: … / 1张`，最终只下载到 1 张图。
- **根因（历史 bug，两处都犯）**：调张数的判断写成了**单向**的
  ```python
  # model_select.py · 主流程
  if cur_count and cur_count > want_count:   # ← 只能降，不能升
      ...
  # model_select.py · _already_ok() 快路径
  if cur_count is not None and cur_count > want_count:
      return False                           # ← 1 张被误判成「已满足」
  ```
  当页面停在 1 张、用户要 2 张时，`1 > 2` 不成立 → 整个调整分支被跳过。
  **后果：在此之前所有 `--count > 1` 的调用其实都只出了 1 张。**
- **正确写法**必须双向：
  ```python
  if cur_count is not None and cur_count != want_count:
      for cand in (want_count, 1, 2, 4, 3, 6, 8):   # 目标优先，失败按接近程度退让
          if cand == cur_count or cand in tried: continue
          if select_count(page, cand): break
  ```
- **验证方法**：`python cli.py setting --apply --count 2`（会真的把页面切到 2 张并回读确认），
  或看 `run` 日志里的 `档位: … / 2张`，以及 `[submit] 同步 UI 设置 → … gen_count=2`。
  三者对得上才算真的生效。
- **注意**：`Seedream 3.x` 张数锁死为 1、没有张数下拉，那是模型限制不是 bug，降级逻辑会兜住。

### 2.11 大批量时「智能比例」尺寸不一致，混在一批里很乱



- **现象**：同一批任务，有的图 2048×2048、有的 2304×1728。
- **机制**：`智能比例` 由服务端逐条按提示词语义算构图，所以同一批不同提示词可能得到不同比例。
- **解决**：如果一批图需要尺寸统一（排版、网页、画册），**必须显式传 `--ratio`**。
  用户明确说「竖构图 / 横图 / 壁纸 / 海报」时同样必须显式传，不能依赖默认值。

---

## 附：仓库迁移记录

本技能自 v1.3.1 起，`~/.dsh/skills/jimeng-batch-image` 目录本身就是 git 仓库，
远端为 <https://github.com/lizhuo520/jimeng-batch-image>。

改完技能后直接在技能目录内提交推送即可，不再需要中间副本目录：

```bash
cd ~/.dsh/skills/jimeng-batch-image
git status
git diff
git add -A && git commit -m "fix: ..." && git push
```
