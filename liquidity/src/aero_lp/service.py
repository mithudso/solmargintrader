"""Serialize launchd configuration. Rendering does not start or inspect any service."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path


def render(binary: str, directory: str, label: str, *, live: bool = False) -> bytes:
    args = [binary, "daemon", "-c", str(Path(directory) / "config.toml")]
    if live:
        args.append("--live")
    doc = {
        "Label": label,
        "ProgramArguments": args,
        "EnvironmentVariables": {"AERO_LP_HOME": directory, "PYTHONUNBUFFERED": "1"},
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 60,
        "ExitTimeOut": 180,
        "ProcessType": "Background",
        "StandardOutPath": str(Path(directory) / "daemon.log"),
        "StandardErrorPath": str(Path(directory) / "daemon.log"),
    }
    body = plistlib.dumps(doc)
    plistlib.loads(body)
    return body


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[4] not in ("--dry-run", "--live"):
        raise SystemExit("expected binary, state directory, label and explicit mode")
    sys.stdout.buffer.write(render(*sys.argv[1:4], live=sys.argv[4] == "--live"))
