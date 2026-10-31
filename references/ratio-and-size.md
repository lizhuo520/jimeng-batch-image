# 画幅比例与出图尺寸完全对照

本文档记录即梦 AI 请求体里与「比例 / 尺寸」相关的全部字段、枚举值与实测出图尺寸。
**改动 `submit.py` 的 `RATIO_KEYS` / `SIZE_MAP_2K` 前必须对照本文核对。**

---

## 1. 三个字段的分工（这是最容易搞错的地方）

一次生图请求里，`core_param` 下有三个字段和构图相关：

| 字段 | 作用 | 是否决定最终像素 |
|---|---|---|
| `large_image_info.width` / `.height` | **真正决定出图尺寸的字段** | ✅ **是** |
| `large_image_info.resolution_type` | 分辨率档标识（`1k`/`1_5k`/`2k`/`4k`） | 间接（影响尺寸档） |
| `core_param.image_ratio` | 比例枚举标记 | ❌ **否**，只是配套标记 |
| `core_param.intelligent_ratio` | 智能构图开关 | ❌ **否** |

### 踩过的坑（务必记住）

> 曾长期以为「改 `image_ratio` 就能改比例」，于是只改 `image_ratio` 而让
> `large_image_info` 停在 `2048×2048`。结果：**无论选 4:3 还是 16:9，出来全是方图。**

服务端确实按 `large_image_info` 出图。**改比例必须同时改 `image_ratio` 和 `large_image_info.width/height`。**

---

## 2. 完整枚举（零成本实测）

用 `page.route("**/mweb/v1/aigc_draft/generate*", ...)` 拦截请求后 `route.abort()`，
既能拿到真实请求体又不扣积分，逐个比例点 UI 抓包得到：

| UI 比例 | `image_ratio` | `intelligent_ratio` | `large_image_info`（2K 档） |
|---|---|---|---|
| **智能**（工具栏显示「智能比例」） | **字段不存在** | `true` | **2048×2048** |
| 1:1 | 1 | false | 2048×2048 |
| 3:4 | 2 | false | 1728×2304 |
| **16:9** | **3** | false | 2560×1440 |
| **4:3** | **4** | false | 2304×1728 |
| 9:16 | 5 | false | 1440×2560 |
| 2:3 | 6 | false | 1664×2496 |
| 3:2 | 7 | false | 2496×1664 |
| 21:9 | 8 | false | 3024×1296 |

与服务端返回的 `model_config.resolution_map.2k.image_ratio_sizes[]` 完全吻合
（`ratio_type 1 → 2048x2048`、`2 → 1728x2304`、`3 → 2560x1440`、`4 → 2304x1728` …）。

> [!CAUTION]
> **`16:9 = 3`、`4:3 = 4`，这两个极易写反。**
> 本项目历史上就写反过，导致用户选 4:3 却拿到横版 2560×1440。

---

## 3. 「智能比例」名不副实（重要结论）

**「智能比例」的尺寸不可预测 —— 由服务端按提示词自己算构图。**

实测两种结果都出现过：2048×2048（方图）和 2304×1728（4:3）。

验证方式：在同一次浏览器 session 内，用 UI 真实点击提交「秋天的麦田…」，
出图是 `(2048, 2048)`；同一份 body 用模板重放，也是 `(2048, 2048)`。

所以：
- 这不是策略 A 重放的问题，**平台行为本身如此**。
- 想要稳定的非方图，**必须显式指定比例**。
- 项目默认值按用户要求仍是 `智能比例`，但**遇到用户对画幅有要求时必须显式传 `--ratio`**。

---

## 4. 各分辨率换算规则

`SIZE_MAP_2K` 以 2K 为基准，其它分辨率按边长等比缩放并 **32 对齐**
（服务端自己用的也是 32 对齐）：

```
scale = 目标边长 / 2048
新宽 = round(基准宽 × scale / 32) × 32
新高 = round(基准高 × scale / 32) × 32
```

对应关系：`1K → 1024`、`1.5K → 1536`、`2K → 2048`、`4K → 4096`。

> 注意各模型支持的分辨率档位不同，不能写死。例如：
> `Seedream 4.7` 支持 `2K/4K`；`Seedream 5.0 Flash` 支持 `1.5K/2K`；
> `图片美学模型 V8.2` 支持 `1K/2K`；`Seedream 3.x` 只有 `1K` 且张数锁 1。
> 真实可选档位必须每次从面板现读（`list_resolutions()`）。

---

## 5. 相关代码位置

| 内容 | 位置 |
|---|---|
| `RATIO_KEYS`（比例 → 枚举值 + 智能标志） | `jimeng-batch/src/jimeng_batch/submit.py` |
| `SIZE_MAP_2K`（比例 → 2K 宽高） | `jimeng-batch/src/jimeng_batch/submit.py` |
| `_size_for(resolution, ratio)`（分辨率换算） | `jimeng-batch/src/jimeng_batch/submit.py` |
| `RATIO_ALIASES`（「智能比例」↔「智能」归一化） | `jimeng-batch/src/jimeng_batch/model_select.py` |
| `select_ratio()` / `list_ratios()` / `list_ratio_items()` | `jimeng-batch/src/jimeng_batch/model_select.py` |

---

## 6. 零成本验证方法（改完代码先跑这个）

改完比例/尺寸逻辑后，不要在真实提交上验证（会扣积分）。用下面这段直接检查生成的请求体：

```python
import json, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lizhuo\Desktop\即梦AI")
sys.path.insert(0, str(ROOT / "jimeng-batch" / "src"))
sys.path.insert(0, str(ROOT / "jimeng-batch"))
from jimeng_batch import submit

tpl = submit.load_template()
for ratio in ("4:3", "16:9", "1:1", "智能比例", "3:4", "21:9"):
    settings = {"model": "Seedream 4.7", "resolution": "2K", "ratio": ratio, "count": 1}
    body, _ = submit._apply_prompt(json.loads(json.dumps(tpl["body"])), "测试", settings)
    cp = json.loads(body["draft_content"])["component_list"][0]["abilities"]["generate"]["core_param"]
    lii = cp.get("large_image_info") or {}
    print(f"{ratio:6s} image_ratio={cp.get('image_ratio', '<缺失>')!r} "
          f"intel={cp.get('intelligent_ratio')} "
          f"size={lii.get('width')}x{lii.get('height')}")
```

期望输出与第 2 节的表格逐行一致。
