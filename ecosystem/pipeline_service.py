"""Install only the planned paper pipeline's foreground launchd owner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from . import runner


def label(home):
    return (
        "com.solmargintrader.pipeline."
        + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    )


def definition(home, python):
    return {
        "Label": label(home),
        "ProgramArguments": [
            str(python),
            "-I",
            "-m",
            "ecosystem.cli",
            "run",
            "--home",
            str(home),
        ],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "StartInterval": 30,
        "ThrottleInterval": 10,
        "Umask": 0o077,
        "WorkingDirectory": str(Path.home()),
        "EnvironmentVariables": {"INDEX_NO_AUTO": "1", "PYTHONNOUSERSITE": "1"},
        "StandardOutPath": str(home / "pipeline-service.stdout.log"),
        "StandardErrorPath": str(home / "pipeline-service.stderr.log"),
    }


def registered(target):
    result = subprocess.run(
        ["launchctl", "print", target], capture_output=True, timeout=5, check=False
    )
    if result.returncode not in (0, 113):
        raise ValueError("pipeline_registration_unverified")
    return result.returncode == 0


def operate(action, home):
    if sys.platform != "darwin":
        raise ValueError("macos_pipeline_service_required")
    home = home.expanduser().absolute()
    if home.is_symlink() or not home.is_dir() or home.stat().st_uid != os.getuid():
        raise ValueError("owned_planned_home_required")
    state = runner.load(home)
    if state["phase"] == "not_initialized" or state["config"]["mode"] != "paper":
        raise ValueError("paper_plan_required")
    python = Path(sys.executable).absolute()
    module = Path(__file__).resolve()
    if "site-packages" not in module.parts or not module.is_relative_to(
        Path(sys.prefix).resolve()
    ):
        raise ValueError("stable_installed_pipeline_required")
    path = Path.home() / "Library/LaunchAgents" / (label(home) + ".plist")
    expected = definition(home, python)
    present = path.exists()
    if path.is_symlink() or (present and plistlib.loads(path.read_bytes()) != expected):
        raise ValueError("pipeline_service_identity_conflict")
    target = f"gui/{os.getuid()}/{label(home)}"
    active = registered(target)
    if active and not present:
        raise ValueError("pipeline_definition_missing")
    if action == "status":
        return {
            "label": label(home),
            "definition_present": present,
            "registered": active,
        }
    if action == "uninstall":
        if active:
            subprocess.run(
                ["launchctl", "bootout", target],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if registered(target):
                raise ValueError("pipeline_unload_unconfirmed_definition_retained")
        if present:
            if plistlib.loads(path.read_bytes()) != expected:
                raise ValueError("pipeline_definition_changed")
            path.unlink()
        return {"installed": False, "state_preserved": True}
    if not present:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out:
            out.write(plistlib.dumps(expected))
        path.chmod(0o600)
    if not active:
        subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)],
            capture_output=True,
            timeout=10,
            check=True,
        )
    if not registered(target):
        raise ValueError("pipeline_start_unconfirmed")
    return {
        "installed": True,
        "label": label(home),
        "definition": str(path),
        "home": str(home),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    parser.add_argument("--home", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = operate(args.action, args.home)
    except (OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps({"ok": False, "error": "pipeline_service_unavailable"}))
        return 3
    print(json.dumps({"ok": True, "data": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
