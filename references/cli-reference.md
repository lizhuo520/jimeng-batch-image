# 即梦 AI 批量生图 CLI 完整指令手册

本文档提供 `cli.py` 所有子命令、控制参数、流水线调优选项及使用范例。

---

## 1. 入口与全局通用说明

所有命令均在以下工作目录下运行：
```powershell
cd "C:\Users\Lizhuo\Desktop\即梦AI\jimeng-batch"
```

> [!TIP]
> 核心脚本已内置 UTF-8 输出重定向，在 Windows PowerShell 或 CMD 下无需手动加环境变量，直接运行 `python cli.py <subcommand>` 即可。

---

## 2. 子命令概览

| 子命令 | 功能定位 | 运行模式 | 积分消耗 | 耗时估计 |
|---|---|---|---|---|
| `credit` | **极速读余额**：读取真实积分与预测可跑条数 | 无头 | **0** | ~4s |
| `doctor` | **环境体检**：全自动检查环境、配置、网络与账号状态 | 无头 | **0** | ~4s |
| `check` | **验登录态**：仅检查当前登录态是否有效 | 有头 | **0** | ~6s |
| `setting` | **查档位**：读当前模型、分辨率、比例与单价 | 有头 | **0** | ~6s |
| `login` | **用户扫码登录**：弹窗供用户完成登录验证并保存会话 | 有头 | **0** | 最长 10 分钟 |
| `logout` | **退出旧账号**：安全备份并清理旧账号会话，重置为未登录态 | 本地 | **0** | <1s |
| `import-cookie` | **Cookie 导入**：通过 sessionid / sid_guard 注入并验证登录态 | 无头 | **0** | ~3s |
| `run` | **批量生图**：提交提示词、轮询结果并下载原图 | 默认有头/可选无头 | 按条计费 | ~8.6s/条（流水线） |

---

## 3. `run` 批量生图详细参数

```text
python cli.py run [prompts_file] [-p PROMPT] [--limit N] [--model MODEL]
                  [--ratio RATIO] [--count COUNT] [--timeout SECONDS]
                  [--interval SECONDS] [--headless] [--pipeline BATCH_SIZE]
```

### 参数说明表

| 参数名 | 简写 / 类型 | 默认值 | 详细说明 |
|---|---|---|---|
| `prompts_file` | 位置参数 | 无 | 提示词 txt 文件路径。自动忽略空行与以 `#` 开头的注释行 |
| `--prompt` | `-p` (字符串) | 无 | 直接传提示词，可重复传递多次，例如 `-p "提示词1" -p "提示词2"` |
| `--limit` | 整数 | `0` (全部) | 限制只处理前 N 条。**首次批量必须先用 `--limit 3` 试水！** |
| `--headless` | 标志 | `False` | 启用无头模式。不弹浏览器窗口，每条可节省约 2s |
| `--pipeline` | 整数 | `0` (串行) | 流水线批大小。例如 `4` 表示连续提交 4 条再统一批量等结果，强烈推荐 |
| `--model` | 字符串 | `Seedream 4.7` | 指定生图模型。默认 4.7 为 1 积分高性价比档 |
| `--ratio` | 字符串 | `智能比例` | 画幅比例。⚠️ `智能比例` 由服务端按提示词自算构图，**尺寸不稳定**，要确定画幅请显式指定：`4:3`(2304×1728)、`16:9`(2560×1440)、`3:4`(1728×2304)、`9:16`(1440×2560)、`1:1`(2048×2048)、`2:3`、`3:2`、`21:9`。详见 [ratio-and-size.md](ratio-and-size.md) |
| `--count` | 整数 | `1` | 每条提示词生成张数（推荐保持 1 张最省积分） |
| `--timeout` | 整数 | `300` | 单条任务最大生成等待超时（秒） |
| `--interval` | 浮点数 | `1.5` | 串行模式下各条任务之间的提交等待间隔（秒） |

---

## 4. 常见场景命令范本

### 场景 A：日常最快生成（标准流程）
```powershell
# 1. 查余额
python cli.py credit

# 2. 试水 3 条
python cli.py run prompts.txt --limit 3 --headless --pipeline 3

# 3. 确认无误后全量跑完
python cli.py run prompts.txt --headless --pipeline 4
```

### 场景 B：单条或少量临时生图
```powershell
python cli.py run -p "水墨山水画，孤舟蓑笠翁，意境幽远，留白" --headless
```

### 场景 C：指定特定比例（如壁纸/海报）
```powershell
# 16:9 壁纸（2560x1440）
python cli.py run prompts.txt --ratio "16:9" --headless --pipeline 4

# 9:16 手机竖屏（1440x2560）
python cli.py run prompts.txt --ratio "9:16" --headless --pipeline 4
```

> 默认是 `智能比例`，但它**尺寸不稳定**（实测 2048×2048 与 2304×1728 都出现过）。
> 只要用户对画幅有要求，就必须显式传 `--ratio`。

### 场景 D：登录失效恢复
```powershell
python cli.py login --timeout-min 5
```
