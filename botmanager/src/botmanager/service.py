"""Explicit per-home launchd installation from a stable installed environment."""

from __future__ import annotations

import hashlib
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from .domain import ManagerError
from .store import data_home
from .worker import lock_held


def installed_executable() -> Path:
    import botmanager

    package = Path(botmanager.__file__).resolve()
    prefix = Path(sys.prefix).absolute()
    # Source/editable imports and disposable checkout environments cannot become
    # boot-persistent services. A normal wheel installation lives in site-packages.
    if (
        "site-packages" not in package.parts
        or not package.is_relative_to(prefix)
        or any(
            part.startswith(("solmargintrader-wt-", ".worktrees"))
            for part in prefix.parts
        )
        or prefix.is_relative_to(Path("/tmp"))
        or prefix.is_relative_to(Path("/private/tmp"))
    ):
        raise ManagerError(
            "stable_install_required",
            "Install a non-editable wheel in a stable environment before installing the service.",
            3,
        )
    executable = prefix / "bin" / "solbot"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ManagerError(
            "stable_install_required", "Installed solbot executable is unavailable.", 3
        )
    return executable


def service(action: str, home: Path | None = None, *, agents_dir: Path | None = None):
    home = Path(home).absolute() if home is not None else data_home()
    label = (
        "com.solmargintrader.solbot."
        + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    )
    directory = (
        agents_dir
        if agents_dir is not None
        else Path.home() / "Library" / "LaunchAgents"
    )
    path = directory / (label + ".plist")
    if action == "status":
        return {
            "platform": sys.platform,
            "label": label,
            "plist_path": str(path),
            "installed": path.is_file(),
            "supervisor_lock_held": lock_held(home / "supervisor.lock"),
            "automatic_install": False,
        }
    if action not in ("install", "uninstall"):
        raise ManagerError("invalid_input", "Unknown service action.")
    if sys.platform != "darwin":
        raise ManagerError(
            "capability_unavailable",
            "Only explicit macOS launchd installation is supported.",
            3,
        )
    target = f"gui/{os.getuid()}"
    if action == "uninstall":
        if path.exists():
            try:
                saved = plistlib.loads(path.read_bytes())
                if saved.get("Label") != label or saved.get(
                    "EnvironmentVariables", {}
                ).get("SOLBOT_HOME") != str(home):
                    raise ValueError
                # bootout failing is not proof of an absent service; retain plist.
                subprocess.run(
                    ["launchctl", "bootout", target + "/" + label],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
                path.unlink()
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise ManagerError(
                    "service_unavailable",
                    "Service removal could not be confirmed; registration was retained.",
                    4,
                ) from exc
        return {"installed": False, "desired_intent_retained": True}
    executable = installed_executable()
    definition = {
        "Label": label,
        "ProgramArguments": [str(executable), "daemon"],
        "EnvironmentVariables": {"SOLBOT_HOME": str(home)},
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
        "Umask": 0o077,
        "WorkingDirectory": str(Path.home()),
    }
    try:
        if path.exists():
            if plistlib.loads(path.read_bytes()) != definition:
                raise ManagerError(
                    "identity_conflict",
                    "An existing service definition differs; no replacement was made.",
                )
            return {"installed": True, "label": label, "already_registered": True}
        directory.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out:
            out.write(plistlib.dumps(definition))
        path.chmod(0o600)
        try:
            subprocess.run(
                ["launchctl", "bootstrap", target, str(path)],
                check=True,
                capture_output=True,
                timeout=5,
            )
        except subprocess.SubprocessError as exc:
            raise ManagerError(
                "service_unavailable",
                "Service registration exists but launchd activation is unconfirmed.",
                4,
            ) from exc
    except ManagerError:
        raise
    except (OSError, ValueError) as exc:
        raise ManagerError(
            "service_unavailable", "Service definition could not be installed.", 4
        ) from exc
    return {"installed": True, "label": label, "executable": str(executable)}
