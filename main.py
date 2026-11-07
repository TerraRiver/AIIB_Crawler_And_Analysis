"""兼容启动入口：`uv run python main.py [参数]`（可通过 `--help` 查看说明）。"""

import sys

from aiib_crawler.cli import main

if __name__ == "__main__":
    sys.exit(main())
