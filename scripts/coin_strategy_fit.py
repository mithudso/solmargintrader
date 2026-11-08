#!/usr/bin/env python3
"""Stable direct-script entrypoint for the shared SolTUI coin-fit backend."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from soltui.coin_fit import cli_main

if __name__ == "__main__":
    raise SystemExit(cli_main())
