"""Install, remove or inspect the hourly portfolio-snapshot LaunchAgent.

    python -m soltui.portfolio_agent install [--python P] [--repo R] [--no-start]
    python -m soltui.portfolio_agent uninstall
    python -m soltui.portfolio_agent status

The job is `com.mitchhudson.soltui.portfolio`: once an hour (and once at load) it runs
`python -m soltui.cli call portfolio.snapshot` from the repo root, so it goes through the same registry,
call log and envelope as every other surface. It reads public data and appends a snapshot; it holds no key
and moves nothing. The plist lives in `~/Library/LaunchAgents`, which is where the automation watchdog
(`automation_health.py`) discovers jobs, so its failing/paused checks see this one with no registration.
The job's stdout is the registry envelope (counts and totals, no addresses); it goes to
`~/Library/Logs/soltui/portfolio.log`.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any

LABEL = "com.mitchhudson.soltui.portfolio"
INTERVAL_S = 3600
DEFAULT_PYTHON = Path.home() / ".venvs" / "soltui" / "bin" / "python"
REPO = Path(__file__).resolve().parent.parent


def agents_dir() -> Path:
    return Path(os.environ.get("SOLTUI_LAUNCHAGENTS_DIR") or Path.home() / "Library" / "LaunchAgents")


def plist_path() -> Path:
    return agents_dir() / f"{LABEL}.plist"


def log_path() -> Path:
    return Path.home() / "Library" / "Logs" / "soltui" / "portfolio.log"


def plist_dict(python: Path = DEFAULT_PYTHON, repo: Path = REPO) -> dict[str, Any]:
    return {
        "Label": LABEL,
        "ProgramArguments": [str(python), "-m", "soltui.cli", "call", "portfolio.snapshot"],
        "WorkingDirectory": str(repo),
        "StartInterval": INTERVAL_S,
        "RunAtLoad": True,
        "ProcessType": "Background",
        "Nice": 10,
        "StandardOutPath": str(log_path()),
        "StandardErrorPath": str(log_path()),
        # launchd starts with no LANG, which makes the locale US-ASCII.
        "EnvironmentVariables": {"PYTHONUTF8": "1", "LANG": "en_US.UTF-8"},
    }


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=30)


def domain() -> str:
    return f"gui/{os.getuid()}"


def install(python: Path = DEFAULT_PYTHON, repo: Path = REPO, start: bool = True) -> dict[str, Any]:
    if not python.exists():
        raise SystemExit(f"interpreter not found: {python}")
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    log_path().parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(plist_dict(python, repo)))
    path.chmod(0o644)
    out: dict[str, Any] = {"plist": str(path), "label": LABEL}
    if start:
        _launchctl("bootout", f"{domain()}/{LABEL}")  # reload cleanly when it is already loaded
        boot = _launchctl("bootstrap", domain(), str(path))
        out["bootstrap"] = boot.returncode
        if boot.returncode:
            out["bootstrap_error"] = boot.stderr.strip()[:200]
        else:
            out["kickstart"] = _launchctl("kickstart", f"{domain()}/{LABEL}").returncode
    return out


def uninstall() -> dict[str, Any]:
    _launchctl("bootout", f"{domain()}/{LABEL}")
    path = plist_path()
    existed = path.exists()
    if existed:
        path.unlink()
    return {"plist": str(path), "removed": existed}


def status() -> dict[str, Any]:
    printed = _launchctl("print", f"{domain()}/{LABEL}")
    info: dict[str, Any] = {"label": LABEL, "plist_exists": plist_path().exists(), "loaded": printed.returncode == 0}
    for line in printed.stdout.splitlines():
        key, _, value = line.strip().partition(" = ")
        if key in ("state", "runs", "last exit code", "run interval"):
            info[key.replace(" ", "_")] = value
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soltui.portfolio_agent", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    inst = sub.add_parser("install")
    inst.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    inst.add_argument("--repo", type=Path, default=REPO)
    inst.add_argument("--no-start", action="store_true", help="write the plist but do not bootstrap it")
    sub.add_parser("uninstall")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    import json

    if args.verb == "install":
        result = install(args.python, args.repo, not args.no_start)
    elif args.verb == "uninstall":
        result = uninstall()
    else:
        result = status()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
