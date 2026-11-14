#!/usr/bin/env python3
"""Run the read-only ZEC winning-strategy display from this checkout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    arguments = sys.argv[1:]
    if any(
        value in ("--plain", "--json", "--frames", "--limit")
        or value.startswith(("--frames=", "--limit="))
        for value in arguments
    ):
        from research.zec_live import main as run

        return run([value for value in arguments if value != "--plain"])
    from research.zec_tui import main as run

    return run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
