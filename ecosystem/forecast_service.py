"""Explicit launchd ownership for the independent ten-second display evaluator."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from .pipeline_service import label as pipeline_label
from .pipeline_service import registered


def definition(home, python, prices):
    return {
        "Label": pipeline_label(home).replace(".pipeline.", ".forecast."),
        "ProgramArguments": [
            str(python),
            "-I",
            "-m",
            "ecosystem.forecast",
            "--home",
            str(home),
            "--prices",
            str(prices),
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "Umask": 0o077,
        "WorkingDirectory": str(Path.home()),
        "EnvironmentVariables": {"INDEX_NO_AUTO": "1", "PYTHONNOUSERSITE": "1"},
        "StandardOutPath": str(home / "forecast-service.stdout.log"),
        "StandardErrorPath": str(home / "forecast-service.stderr.log"),
    }


def operate(action, home, prices):
    home, prices = home.expanduser().absolute(), prices.expanduser().absolute()
    if (
        sys.platform != "darwin"
        or home.is_symlink()
        or not home.is_dir()
        or home.stat().st_uid != os.getuid()
    ):
        raise ValueError("owned_macos_home_required")
    module = Path(__file__).resolve()
    if "site-packages" not in module.parts or not module.is_relative_to(
        Path(sys.prefix).resolve()
    ):
        raise ValueError("immutable_installed_evaluator_required")
    expected = definition(home, Path(sys.executable).absolute(), prices)
    path = Path.home() / "Library/LaunchAgents" / (expected["Label"] + ".plist")
    target = f"gui/{os.getuid()}/" + expected["Label"]
    if path.is_symlink() or (
        path.exists() and plistlib.loads(path.read_bytes()) != expected
    ):
        raise ValueError("forecast_service_identity_conflict")
    active = registered(target)
    if active and not path.exists():
        raise ValueError("forecast_service_definition_missing")
    if action == "status":
        return {
            "label": expected["Label"],
            "registered": active,
            "definition_present": path.exists(),
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
                raise ValueError("forecast_unload_unconfirmed")
        if path.exists():
            if plistlib.loads(path.read_bytes()) != expected:
                raise ValueError("forecast_definition_changed")
            path.unlink()
        return {"installed": False, "state_preserved": True}
    if not path.exists():
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
    return {
        "installed": registered(target),
        "label": expected["Label"],
        "definition": str(path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument(
        "--prices", type=Path, default=Path.home() / ".config/soltui/prices"
    )
    args = parser.parse_args(argv)
    try:
        result = operate(args.action, args.home, args.prices)
    except (OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps({"ok": False, "error": "forecast_service_unavailable"}))
        return 3
    print(json.dumps({"ok": True, "data": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
