#!/usr/bin/env python
"""即梦 AI 批量生图环境自检门禁脚本 (Doctor)。

可直接在任意目录下独立调用：
    python doctor.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# 确保控制台以 UTF-8 编码输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 默认项目工作目录
BATCH_ROOT = Path(r"C:\Users\Lizhuo\Desktop\即梦AI\jimeng-batch")


def main() -> int:
    if not BATCH_ROOT.exists():
        print(f"[doctor] ✗ 找不到即梦工作目录: {BATCH_ROOT}")
        return 1

    cli_path = BATCH_ROOT / "cli.py"
    if not cli_path.exists():
        print(f"[doctor] ✗ 找不到 cli.py: {cli_path}")
        return 1

    print(f"[doctor] 正在调起项目自检程序: {cli_path}")
    cmd = [sys.executable, str(cli_path), "doctor"]
    res = subprocess.run(cmd, cwd=str(BATCH_ROOT))
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
