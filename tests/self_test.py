"""本地自测入口。不需要 API Key，也不会访问模型接口。

在项目根目录运行：

    python tests/self_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    print("开始自测：文件解析、法规库为空时的降级、API 失败提示、三个必需标题。")
    print("本自测使用内置示例材料和模拟模型，不会访问网络。")
    target = Path(__file__).resolve().parent / "test_analysis.py"
    code = pytest.main(["-v", str(target)])
    if code == 0:
        print("自测通过。")
    else:
        print("自测未通过，请根据上方失败项检查。")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
