#!/usr/bin/env python3
"""Install, verify and start the resumable paper ecosystem; status/stop are inert."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--help" in arguments or "-h" in arguments:
        from ecosystem.cli import main as cli_main

        return cli_main(["--help"])
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--venv", type=Path, default=Path.home() / ".venvs/solecosystem-0.3.0"
    )
    args, forwarded = parser.parse_known_args(arguments)
    from ecosystem.cli import build_parser

    parsed = build_parser().parse_args(forwarded)
    command = parsed.command
    from ecosystem.installation import install_environment, verify_environment

    python = args.venv.expanduser().absolute() / "bin/python"
    if command == "start" and not parsed.offline:
        result = install_environment(REPO, args.venv)
    else:
        if not python.is_file():
            print(json.dumps({"ok": False, "error": "ecosystem_not_installed"}))
            return 2
        result = verify_environment(python, REPO)
    if result.get("status") != "complete":
        print(json.dumps({"ok": False, "setup": result}, allow_nan=False))
        return 2
    return subprocess.run(
        [str(python), "-I", "-m", "ecosystem.cli", *forwarded], cwd="/tmp", check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
