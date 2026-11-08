#!/usr/bin/env python3
"""Skill entrypoint; symlink installation preserves the owning checkout."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
if not (root / "soltui" / "coin_fit.py").is_file():
    raise SystemExit(
        "This skill requires its containing solmargintrader checkout; install by symlink or retain the repository layout."
    )
sys.path.insert(0, str(root))
from soltui.coin_fit import cli_main

if __name__ == "__main__":
    raise SystemExit(cli_main())
