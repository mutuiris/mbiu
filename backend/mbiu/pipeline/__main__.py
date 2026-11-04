"""Entry point for ``python -m mbiu.pipeline``."""

import sys

from mbiu.pipeline.cli import main

if __name__ == "__main__":
    sys.exit(main())
