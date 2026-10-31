# 即梦 AI 批量生图技能 (jimeng-batch-image)

> 给一批中文提示词，全自动提交到 [即梦 AI](https://jimeng.jianying.com) 生成图片并下载原图。
> 无头浏览器 + 流水线提交，**平均 8.6 秒/张，1 积分/张**。

这是一个 [DSH (DeepSeek Harness)](https://github.com/) Skill，也可以照着文档手写调用脚本。

---

## 它解决什么问题

即梦 AI 网页版没有开放 API，批量出图只能手动一条条敲提示词、等、下载。
本项目用 Playwright 驱动本地已登录的 Edge 浏览器，把这件事全自动化：

- **自动降档**：默认档位是 `Seedream 5.0 Pro + 2K + 2张`（16 积分/条），程序会自动切到 `Seedream 4.7 + 2K + 1张`（**1 积分/条**），省 16 倍
- **模板重放**：第一次走 UI 提交并抓下请求体，之后在页面上下文内 `fetch` 重放（**0.6s/条**），绕过运行时签名（`a_bogus` + `msToken`）
- **流水线**：批内连续提交，4 条约 34s（串行要 80s）
- **真实积分**：读页面右上角真实余额，不用固定值瞎算
- **断点续跑**：`jobs.jsonl` 账本 + `resume`

---

## 核心难点与解法

| 难点 | 解法 |
|---|---|
| 请求签名 `a_bogus` 由页面 JS 运行时生成，无法静态复刻 | 在页面上下文 `page.evaluate(fetch(...))` 里发请求，让页面自己签名 |
| 纯 HTTP 直连返回 `ret=1019 shark not pass` | 同上，必须走浏览器上下文 |
| 页面没有 textarea，编辑器是 ProseMirror | `click` + `keyboard.type`，`fill()` 无效；Enter 会提交，换行须 Shift+Enter |
| 视口 1280×720 时编辑器掉出视口 | 用 **1920×1200**（最小 900 高） |
| 跨域 CDN 图片被 CORS 挡 | 用 `page.context.request.get()`，复用 cookie 且不受 CORS 限制 |
| `get_history_by_ids` 参数名易错 | 纯数字 id 走 `history_ids`，UUID 走 `submit_ids`，搞反会静默返回空 |
| 选任何比例都出方图 | 真正决定尺寸的是 `large_image_info.width/height`，不是 `image_ratio` |

---

## 快速上手

### 1. 环境

```bash
pip install playwright
python -m playwright install msedge   # 或直接装 Edge
```

### 2. 登录一次

```bash
python cli.py login      # 弹出浏览器，扫码登录
python cli.py check      # 验证登录态
```

### 3. 准备提示词

`prompts.txt`，一行一条，`#` 开头是注释：

```
# 风景
雪山之巅的孤松，水墨画风格，留白构图
秋天的白桦林，晨雾弥漫，印象派油画
```

### 4. 批量生成

```bash
python cli.py run prompts.txt --headless --pipeline 4
```

图片下载到 `data/outputs/<批次时间戳>/`。

---

## 常用命令

| 命令 | 说明 |
|---|---|
| `python cli.py run prompts.txt` | 跑一批 |
| `python cli.py credit` | 查真实剩余积分（**零成本**） |
| `python cli.py setting` | 只看档位不提交 |
| `python cli.py setting --apply` | 切到默认档位（4.7 / 2K / 智能比例 / 1张）并回读确认 |
| `python cli.py check` | 检查登录态 |
| `python cli.py status` | 看批次状态 |
| `python cli.py resume --batch <id>` | 断点续跑 |
| `python cli.py doctor` | 环境自检 |

---

## 关键参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--model` | `Seedream 4.7` | 最便宜，1 积分/张 |
| `--ratio` | `智能比例` | ⚠️ **尺寸不稳定**，要确定画幅必须显式指定 |
| `--count` | `1` | 每条张数，1~8 |
| `--headless` | 关 | 无头模式 |
| `--pipeline` | `0`（串行） | 流水线批大小，推荐 `4`，上限 `6` |

### 画幅对照表（2K）

| 比例 | 尺寸 | 比例 | 尺寸 |
|---|---|---|---|
| `1:1` | 2048×2048 | `16:9` | 2560×1440 |
| `4:3` | 2304×1728 | `9:16` | 1440×2560 |
| `3:4` | 1728×2304 | `21:9` | 3024×1296 |
| `2:3` | 1664×2496 | `3:2` | 2496×1664 |

> ⚠️ `智能比例`（默认值）由服务端按提示词自己算构图，实测既出过 2048×2048 也出过 2304×1728。
> 要确定画幅请显式传 `--ratio`。

---

## 价格矩阵（实测）

| 模型 | 可选分辨率 | 积分/张 |
|---|---|---|
| Seedream 4.7 / 4.6 / 4.1 / 4.0 | 2K | **1** |
| Seedream 4.7 / 4.6 / 4.1 | 4K | 2 |
| Seedream 5.0 Pro | 1.5K / 2K / 4K | 2.5 / 8 / 12 |
| Seedream 5.0 Flash | 1.5K / 2K | 3 |
| Seedream 5.0 Lite | 2K / 4K | 3 / 4 |
| 图片美学模型 V8.2 | 1K / 2K | 5 / 7 |
| Seedream 3.1 / 3.0 | 1K | 不显示（张数锁 1） |

> 每日免费额度约 66 积分，用最便宜档位约可跑 66 张/天。

---

## 目录结构

```
jimeng-batch-image/
├── SKILL.md                        # 技能主文档（SOP + 铁律 + 参数表）
├── references/
│   ├── cli-reference.md            # CLI 全部子命令与参数
│   ├── price-matrix.md             # 完整价格矩阵与选型策略
│   ├── ratio-and-size.md           # 比例枚举值、请求体字段、出图尺寸
│   └── troubleshooting.md          # 排错手册（按现象索引）
└── scripts/
    └── doctor.py                   # 环境自检脚本
```

---

## 已知限制

- **需要真实登录态**：登录要用户自己扫码，程序不代劳
- **智能比例尺寸不稳定**：见上文
- **选择器会随改版失效**：集中在 `selectors.py` 多级回退，但平台大改版仍可能失效
- **每日额度有限**：约 66 积分
- **无头模式暴露点**：`outerWidth` 与 `innerWidth` 不一致，目前未触发风控但并非无痕

---

## 免责声明

本项目仅用于**个人学习与自动化研究**，通过模拟正常用户操作实现。
请遵守即梦 AI 的服务条款，不要用于高频刷取、商业转售或其他滥用场景。
因使用本项目导致账号受限或产生费用，作者不承担责任。

---

## License

MIT
