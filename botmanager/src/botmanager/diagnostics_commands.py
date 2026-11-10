"""Local, shareable setup diagnostics with an explicit data allowlist."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import stat
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from .store import data_home


def _setup_report(context):
    home = Path(context.home).expanduser().absolute() if context.home else data_home()
    required = (
        "solbot-manager",
        "solmargintrader-backtester",
        "solmargintrader-research-runtime",
        "solmargintrader-oracle",
    )
    packages = {}
    for name in required:
        try:
            packages[name] = {"state": "installed", "version": importlib.metadata.version(name)}
        except importlib.metadata.PackageNotFoundError:
            packages[name] = {"state": "missing"}
    parent = home if home.exists() else home.parent
    writable = bool(parent.exists() and os.access(parent, os.W_OK))
    return {
        "schema_version": 1,
        "checked_at": time.time(),
        "runtime": {"python": platform.python_version(), "python_supported": sys.version_info >= (3, 13),
                    "operating_system": platform.system(), "architecture": platform.machine()},
        "packages": packages,
        "manager_home": {"state": "present" if home.is_dir() else "not_initialized",
                         "readable": bool(home.is_dir() and os.access(home, os.R_OK)),
                         "writable_parent": writable},
        "checks": [
            {"name": "python_version", "state": "pass" if sys.version_info >= (3, 13) else "fail"},
            {"name": "required_packages", "state": "pass" if all(v["state"] == "installed" for v in packages.values()) else "fail"},
            {"name": "manager_home_parent", "state": "pass" if writable else "fail"},
        ],
    }


def _component_report(context):
    from .machine_health import check

    try:
        value = check(context.home, context.ecosystem_home)
        # Never place the exact home path or UI URL in a support archive.
        return {"schema_version": value["schema_version"], "overall": value["overall"],
                "ready": value["ready"], "orders_available": False,
                "components": value["components"]}
    except Exception as exc:  # noqa: BLE001 - diagnostic failure itself remains safe to share
        return {"schema_version": 1, "overall": "unknown", "ready": False,
                "orders_available": False, "error_code": getattr(exc, "code", "health_probe_failed")}


def _write_bundle(path: Path, setup: dict, components: dict) -> Path:
    path = path.expanduser().absolute()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ValueError("output file already exists")
    report = {
        "README.txt": (
            "solbot local troubleshooting bundle\n\n"
            "This archive contains allowlisted runtime, package, setup-check and component-health data.\n"
            "It contains no configuration files, environment values, wallet data, account history, or raw logs.\n"
            "Review this archive before sharing it. The command does not upload anything.\n"
        ),
        "setup-checks.json": json.dumps(setup, indent=2, sort_keys=True, allow_nan=False) + "\n",
        "component-health.json": json.dumps(components, indent=2, sort_keys=True, allow_nan=False) + "\n",
    }
    fd, temp_name = tempfile.mkstemp(prefix=".solbot-diagnostics-", suffix=".zip", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, body in report.items():
                archive.writestr(name, body)
        os.replace(temp, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        temp.unlink(missing_ok=True)
    return path


def diagnostics_command(params, context):
    setup = _setup_report(context)
    components = _component_report(context)
    output = params.get("output")
    if output is None:
        output = Path.home() / "Downloads" / f"solbot-diagnostics-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    try:
        path = _write_bundle(Path(output), setup, components)
    except (OSError, ValueError) as exc:
        from .domain import ManagerError

        raise ManagerError("invalid_input", f"Could not create diagnostics archive ({type(exc).__name__}).") from None
    return {"archive": str(path), "size_bytes": path.stat().st_size,
            "overall_health": components.get("overall", "unknown"),
            "setup_check_failures": [row["name"] for row in setup["checks"] if row["state"] != "pass"],
            "uploaded": False}


def command_specs(command_type):
    return (command_type(
        "diagnostics",
        "Create a private local setup-check and component-health ZIP for troubleshooting; never uploads it.",
        diagnostics_command,
        (( ("--output",), {"type": Path, "help": "Write the archive here (default: ~/Downloads)."}),),
    ),)
