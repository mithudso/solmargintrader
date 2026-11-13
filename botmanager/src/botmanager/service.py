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


def _registered(service_target: str) -> bool:
    """Probe the exact launchd service, without parsing unstable print output.

    launchctl error 113 is "Could not find specified service". Other failures
    are uncertainty, including unavailable GUI domains and authorization errors.
    """
    try:
        result = subprocess.run(
            ["launchctl", "print", service_target],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManagerError(
            "service_unavailable", "Launchd registration could not be confirmed.", 4
        ) from exc
    if result.returncode == 0:
        return True
    if result.returncode == 113:
        return False
    raise ManagerError(
        "service_unavailable", "Launchd registration could not be confirmed.", 4
    )


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
    suite_label = (
        "com.solmargintrader.suite."
        + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    )
    suite_definition = directory / (suite_label + ".plist")
    suite_running = lock_held(home / ".suite/owner.lock")
    managed_by_suite = suite_definition.is_file() or suite_running
    if action == "status":
        return {
            "platform": sys.platform,
            "label": label,
            "plist_path": str(path),
            "installed": path.is_file(),
            "definition_present": path.is_file(),
            "managed_by_suite": managed_by_suite,
            "suite_definition_present": suite_definition.is_file(),
            "suite_owner_lock_held": suite_running,
            "registered": None,
            "registration_reason": "launchd_registration_not_queried",
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
    if action == "install" and managed_by_suite:
        raise ManagerError(
            "suite_owner_conflict",
            "The managed suite owns this manager; use its stack controls instead of installing a competing daemon.",
            3,
        )
    target = f"gui/{os.getuid()}"
    service_target = target + "/" + label
    try:
        if action == "uninstall":
            if path.exists():
                saved = plistlib.loads(path.read_bytes())
                if (
                    not isinstance(saved, dict)
                    or saved.get("Label") != label
                    or saved.get("EnvironmentVariables") != {"SOLBOT_HOME": str(home)}
                ):
                    raise ManagerError(
                        "identity_conflict",
                        "Existing service definition does not match this home.",
                    )
                if _registered(service_target):
                    try:
                        subprocess.run(
                            ["launchctl", "bootout", service_target],
                            check=True,
                            capture_output=True,
                            timeout=5,
                        )
                    except subprocess.SubprocessError:
                        # An interrupted/failed acknowledgment does not establish
                        # either presence or absence. Reconcile before removing.
                        pass
                    if _registered(service_target):
                        raise ManagerError(
                            "service_unavailable",
                            "Service removal is unconfirmed; its definition was retained.",
                            4,
                        )
                path.unlink()
            elif _registered(service_target):
                raise ManagerError(
                    "identity_conflict",
                    "A registered service has no matching local definition; no removal was attempted.",
                )
            return {
                "installed": False,
                "definition_present": False,
                "registered": False,
                "desired_intent_retained": True,
            }

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
        existing = path.exists()
        if existing and plistlib.loads(path.read_bytes()) != definition:
            raise ManagerError(
                "identity_conflict",
                "An existing service definition differs; no replacement was made.",
            )
        if _registered(service_target):
            if not existing:
                raise ManagerError(
                    "identity_conflict",
                    "A registered service has no matching local definition; no replacement was made.",
                )
            return {
                "installed": True,
                "definition_present": True,
                "registered": True,
                "label": label,
                "already_registered": True,
            }
        if not existing:
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
                "Service definition exists but launchd activation is unconfirmed.",
                4,
            ) from exc
        if not _registered(service_target):
            raise ManagerError(
                "service_unavailable",
                "Service definition exists but launchd activation is unconfirmed.",
                4,
            )
        return {
            "installed": True,
            "definition_present": True,
            "registered": True,
            "label": label,
            "executable": str(executable),
            "already_registered": False,
        }
    except ManagerError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise ManagerError(
            "service_unavailable",
            "Service operation could not be confirmed; local state was retained where possible.",
            4,
        ) from exc
