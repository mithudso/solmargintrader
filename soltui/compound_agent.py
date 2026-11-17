"""Install, remove or inspect the compound 5m autopilot LaunchAgent.

    python -m soltui.compound_agent install [--python P] [--repo R] [--no-start]
    python -m soltui.compound_agent uninstall
    python -m soltui.compound_agent status

The job is `com.mitchhudson.soltui.compound-autopilot`: every five minutes (and once at load) it runs
`python -m soltui.compound autopilot` from the repo root. That call starts the unattended forward-training
loop of every coin whose loop is not running, and does nothing when autopilot is off. So the trainer
survives a reboot, a crash or a closed console with no one pressing Start. Each loop already holds its
coin's lock for its whole life, which makes the check idempotent.

The loops it starts read public market data, record paper calls and adopt tuned settings into
`~/.config/soltui/compound/config.json`. They hold no key and place no order.

Two plist keys matter. `AbandonProcessGroup` stops launchd from killing the loops when this short check
exits; the loops also start their own session, so this is belt and braces. And the repo must be the main
checkout, never a worktree: a worktree can be deleted at any time, and the agent would then fail silently
at every interval. `install` refuses a worktree path for that reason.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any

LABEL = "com.mitchhudson.soltui.compound-autopilot"
INTERVAL_S = 300
DEFAULT_PYTHON = Path.home() / ".venvs" / "soltui" / "bin" / "python"
REPO = Path(__file__).resolve().parent.parent


def agents_dir() -> Path:
    return Path(os.environ.get("SOLTUI_LAUNCHAGENTS_DIR") or Path.home() / "Library" / "LaunchAgents")


def plist_path() -> Path:
    return agents_dir() / f"{LABEL}.plist"


def log_path() -> Path:
    return Path.home() / "Library" / "Logs" / "soltui" / "compound-autopilot.log"


def is_worktree(repo: Path) -> bool:
    """A linked git worktree has a `.git` FILE; the main checkout has a `.git` directory."""
    return (repo / ".git").is_file()


def plist_dict(python: Path = DEFAULT_PYTHON, repo: Path = REPO) -> dict[str, Any]:
    return {
        "Label": LABEL,
        "ProgramArguments": [str(python), "-m", "soltui.compound", "autopilot"],
        "WorkingDirectory": str(repo),
        "StartInterval": INTERVAL_S,
        "RunAtLoad": True,
        "AbandonProcessGroup": True,
        "ProcessType": "Background",
        "Nice": 10,
        "StandardOutPath": str(log_path()),
        "StandardErrorPath": str(log_path()),
        # launchd starts with no LANG, which makes the locale US-ASCII.
        "EnvironmentVariables": {"PYTHONUTF8": "1", "LANG": "en_US.UTF-8", "PYTHONPATH": str(repo)},
    }


def _launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=30)


def domain() -> str:
    return f"gui/{os.getuid()}"


def install(python: Path = DEFAULT_PYTHON, repo: Path = REPO, start: bool = True) -> dict[str, Any]:
    python, repo = Path(os.path.abspath(python.expanduser())), repo.expanduser().resolve()
    if not python.exists():
        raise SystemExit(f"interpreter not found: {python}")
    if is_worktree(repo):
        raise SystemExit(f"{repo} is a git worktree; install from the main checkout so the agent "
                         "does not point at a directory that can be deleted")
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
    result = _launchctl("bootout", f"{domain()}/{LABEL}")
    path = plist_path()
    if result.returncode:
        return {"plist": str(path), "removed": False, "bootout": result.returncode,
                "error": "agent unload failed; registration retained"}
    existed = path.exists()
    if existed:
        path.unlink()
    return {"plist": str(path), "removed": existed}


def status() -> dict[str, Any]:
    info: dict[str, Any] = {"label": LABEL, "plist_exists": plist_path().exists(), "loaded": False}
    try:
        printed = _launchctl("print", f"{domain()}/{LABEL}")
    except (OSError, subprocess.SubprocessError):  # no launchctl (Linux CI) or it hung
        return info
    info["loaded"] = printed.returncode == 0
    for line in printed.stdout.splitlines():
        key, _, value = line.strip().partition(" = ")
        if key in ("state", "runs", "last exit code", "run interval"):
            info[key.replace(" ", "_")] = value
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soltui.compound_agent", description=(__doc__ or "").splitlines()[0])
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
    return 1 if result.get("error") or result.get("bootstrap") not in (None, 0) or result.get("kickstart") not in (None, 0) else 0


if __name__ == "__main__":
    sys.exit(main())
