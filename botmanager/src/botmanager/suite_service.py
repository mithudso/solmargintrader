"""Explicit user-service installation for the availability suite.

launchd starts at user login, not before login/FileVault unlock. Linux uses the
user systemd manager; a persistent user manager across logout requires linger.
"""

from __future__ import annotations

import hashlib
import os
import plistlib
import stat
import subprocess
import sys
from pathlib import Path

from .domain import ManagerError
from .machine_health import homes
from .service import installed_executable
from .worker import lock_held


def label(home):
    return (
        "com.solmargintrader.suite."
        + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    )


def _invoke(arguments):
    try:
        return subprocess.run(arguments, capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManagerError(
            "suite_service_unavailable", "User service manager is unavailable.", 3
        ) from exc


def _registered(home, platform_name):
    if platform_name == "darwin":
        value = _invoke(["launchctl", "print", f"gui/{os.getuid()}/{label(home)}"])
        if value.returncode in (0, 113):
            return value.returncode == 0
    elif platform_name.startswith("linux"):
        value = _invoke(
            [
                "systemctl",
                "--user",
                "show",
                label(home) + ".service",
                "--property=LoadState,ActiveState",
                "--value",
            ]
        )
        if value.returncode == 0:
            states = value.stdout.decode(errors="replace").splitlines()
            return "loaded" in states and any(
                state in states for state in ("active", "activating", "reloading")
            )
        if value.returncode == 4:
            return False
    raise ManagerError(
        "suite_service_unavailable",
        "User service registration could not be confirmed.",
        4,
    )


def _directory(platform_name):
    if platform_name == "darwin":
        return Path.home() / "Library/LaunchAgents"
    return Path.home() / ".config/systemd/user"


def _enabled(home, platform_name):
    if not platform_name.startswith("linux"):
        return None
    value = _invoke(
        ["systemctl", "--user", "is-enabled", "--quiet", label(home) + ".service"]
    )
    if value.returncode == 0:
        return True
    if value.returncode in (1, 4):
        return False
    raise ManagerError(
        "suite_service_unavailable",
        "User service enablement could not be confirmed.",
        4,
    )


def _quote(value):
    text = str(value)
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise ManagerError(
            "suite_config_unavailable",
            "Service path contains unsupported characters.",
            3,
        )
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def definition(home, ecosystem_home, executable, platform_name):
    arguments = [
        str(executable),
        "--ecosystem-home",
        str(ecosystem_home),
        "stack",
        "run",
    ]
    if platform_name == "darwin":
        return plistlib.dumps(
            {
                "Label": label(home),
                "ProgramArguments": arguments,
                "EnvironmentVariables": {
                    "SOLBOT_HOME": str(home),
                    "SOLBOT_ECOSYSTEM_HOME": str(ecosystem_home),
                    "INDEX_NO_AUTO": "1",
                    "PYTHONNOUSERSITE": "1",
                },
                "RunAtLoad": True,
                "KeepAlive": True,
                "ThrottleInterval": 5,
                "Umask": 0o077,
                "WorkingDirectory": str(Path.home()),
                "StandardOutPath": str(home / ".suite" / "suite.stdout.log"),
                "StandardErrorPath": str(home / ".suite" / "suite.stderr.log"),
            }
        )
    lines = [
        "[Unit]",
        "Description=Solbot paper manager and control-room availability",
        "After=network-online.target",
        "",
        "[Service]",
        "Type=simple",
        "ExecStart=" + " ".join(_quote(value) for value in arguments),
        "Environment=" + _quote("SOLBOT_HOME=" + str(home)),
        "Environment=" + _quote("SOLBOT_ECOSYSTEM_HOME=" + str(ecosystem_home)),
        "Environment=INDEX_NO_AUTO=1",
        "Environment=PYTHONNOUSERSITE=1",
        "Restart=always",
        "RestartSec=5",
        "TimeoutStopSec=10",
        "KillMode=control-group",
        "UMask=0077",
        "NoNewPrivileges=true",
        "WorkingDirectory=" + _quote(Path.home()),
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ]
    return "\n".join(lines).encode()


def _path(home, platform_name, directory=None):
    suffix = ".plist" if platform_name == "darwin" else ".service"
    return (Path(directory) if directory is not None else _directory(platform_name)) / (
        label(home) + suffix
    )


def _supported(platform_name):
    return platform_name == "darwin" or platform_name.startswith("linux")


def _read_definition(path):
    """Do not trust a filename alone as authority to replace or unload a job."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > 65_536
        ):
            raise ManagerError(
                "identity_conflict",
                "Existing suite service definition is unverified; it was retained.",
                3,
            )
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read(65_537)
    finally:
        os.close(fd)


def operation(
    action, home=None, ecosystem_home=None, *, directory=None, platform_name=None
):
    platform_name = sys.platform if platform_name is None else platform_name
    home, ecosystem_home = homes(home, ecosystem_home)
    if not _supported(platform_name):
        if action == "status":
            return {
                "platform": platform_name,
                "backend": None,
                "installed": False,
                "registered": None,
                "reason": "native_windows_unavailable_use_wsl2",
                "automatic_install": False,
            }
        raise ManagerError(
            "capability_unavailable",
            "Native Windows is unsupported; use the documented WSL2 setup.",
            3,
        )
    path = _path(home, platform_name, directory)
    backend = "launchd-user" if platform_name == "darwin" else "systemd-user"
    if action == "status":
        try:
            registered = _registered(home, platform_name)
            enabled = _enabled(home, platform_name)
            reason = "available" if registered else "not_registered"
        except ManagerError:
            registered, enabled, reason = None, None, "registration_unavailable"
        return {
            "platform": platform_name,
            "backend": backend,
            "label": label(home),
            "definition_path": str(path),
            "installed": path.is_file(),
            "registered": registered,
            "enabled": enabled,
            "reason": reason,
            "boot_scope": "user_login",
            "automatic_install": False,
        }
    if action not in ("install", "uninstall", "start", "stop"):
        raise ManagerError("invalid_input", "Unknown suite service action.")
    try:
        executable = installed_executable()
        wanted = definition(home, ecosystem_home, executable, platform_name)
        exists = path.exists() or path.is_symlink()
        if exists and _read_definition(path) != wanted:
            raise ManagerError(
                "identity_conflict",
                "Existing suite service definition differs; it was retained.",
                3,
            )
        registered = _registered(home, platform_name)
        if registered and not exists:
            raise ManagerError(
                "identity_conflict",
                "A registered suite has no verified definition; it was retained.",
                3,
            )
        if action in ("install", "start"):
            if action == "start" and not exists:
                raise ManagerError(
                    "suite_service_unavailable",
                    "The suite service is not installed.",
                    3,
                )
            if lock_held(home / "supervisor.lock") and not lock_held(
                home / ".suite/owner.lock"
            ):
                raise ManagerError(
                    "suite_owner_conflict",
                    "An independent manager already owns this home; reconcile its service first.",
                    3,
                )
            from .suite import save_config

            save_config(home, ecosystem_home)
            if not exists:
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with path.open("xb") as handle:
                    handle.write(wanted)
                path.chmod(0o600)
            if platform_name == "darwin":
                target = f"gui/{os.getuid()}/{label(home)}"
                if _invoke(["launchctl", "enable", target]).returncode:
                    raise ManagerError(
                        "suite_service_unavailable",
                        "Service enablement could not be confirmed.",
                        4,
                    )
                if not _registered(home, platform_name):
                    _invoke(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)])
            else:
                if _invoke(["systemctl", "--user", "daemon-reload"]).returncode:
                    raise ManagerError(
                        "suite_service_unavailable",
                        "Service definition reload failed.",
                        4,
                    )
                if (
                    _invoke(
                        ["systemctl", "--user", "enable", "--now", path.name]
                    ).returncode
                    or _enabled(home, platform_name) is not True
                ):
                    raise ManagerError(
                        "suite_service_unavailable",
                        "Service enablement could not be confirmed.",
                        4,
                    )
            if not _registered(home, platform_name):
                raise ManagerError(
                    "suite_service_unavailable",
                    "Definition retained; service activation is unconfirmed.",
                    4,
                )
            return {
                **operation(
                    "status",
                    home,
                    ecosystem_home,
                    directory=directory,
                    platform_name=platform_name,
                ),
                "enabled": True,
            }
        if platform_name == "darwin":
            target = f"gui/{os.getuid()}/{label(home)}"
            if exists and _invoke(["launchctl", "disable", target]).returncode:
                raise ManagerError(
                    "suite_service_unavailable",
                    "Service disablement could not be confirmed.",
                    4,
                )
            if _registered(home, platform_name):
                _invoke(["launchctl", "bootout", target])
        else:
            if exists and (
                _invoke(
                    ["systemctl", "--user", "disable", "--now", path.name]
                ).returncode
                or _enabled(home, platform_name) is not False
            ):
                raise ManagerError(
                    "suite_service_unavailable",
                    "Service disablement could not be confirmed.",
                    4,
                )
        if _registered(home, platform_name):
            raise ManagerError(
                "suite_service_unavailable",
                "Service release is unconfirmed; its definition was retained.",
                4,
            )
        if action == "uninstall" and exists:
            path.unlink()
            if platform_name.startswith("linux"):
                _invoke(["systemctl", "--user", "daemon-reload"])
        return {
            "installed": action != "uninstall" and exists,
            "registered": False,
            "enabled": False,
            "label": label(home),
            "desired_bot_intent_retained": True,
        }
    except ManagerError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise ManagerError(
            "suite_service_unavailable",
            "Service operation could not be confirmed; state was retained.",
            4,
        ) from exc
