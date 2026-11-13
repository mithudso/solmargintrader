#!/usr/bin/env python3
"""Run the read-only ZEC winning-strategy display from this checkout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.zec_live import main

if __name__ == "__main__":
    raise SystemExit(main())
