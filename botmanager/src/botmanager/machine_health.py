"""Bounded, inert availability measurements for collectors and alert engines.

This module never opens an owner for writing. Availability is not a claim about
financial reconciliation, market certification or permission to trade.
"""

from __future__ import annotations

import json
import math
import os
import socket
import sqlite3
import stat
import time
from pathlib import Path

from .domain import ManagerError
from .store import data_home
from .transport import _owner_path, _peer, _read, request
from .worker import lock_held

SCHEMA_VERSION = 1
MAX_BYTES = 256 * 1024
SUITE_STALE_SECONDS = 15.0
MARKET_STALE_SECONDS = 120.0
COMPONENTS = ("suite", "manager", "control_room", "market_data")
STATES = ("up", "degraded", "down", "unknown")


def private_read(path: Path, *, limit: int = MAX_BYTES):
    """Read one private bounded JSON object without following its final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > limit
        ):
            raise ValueError("private_record_unverified")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
    finally:
        os.close(fd)
    if len(raw) > limit:
        raise ValueError("private_record_budget_exceeded")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise TypeError("private_record_invalid")
    return result


def homes(home=None, ecosystem_home=None):
    home = Path(home).expanduser().absolute() if home is not None else data_home()
    if home.is_symlink() or (home.exists() and not home.is_dir()):
        raise ManagerError(
            "suite_config_unavailable", "Manager home is unavailable.", 3
        )
    selected = ecosystem_home or os.environ.get("SOLBOT_ECOSYSTEM_HOME")
    if selected is None:
        try:
            config = private_read(home / ".suite" / "config.json", limit=16_384)
        except FileNotFoundError:
            config = None
        except (OSError, ValueError, TypeError) as exc:
            raise ManagerError(
                "suite_config_unavailable", "Suite configuration is unavailable.", 3
            ) from exc
        if config is not None:
            if config.get("schema_version") != 1 or config.get("manager_home") != str(
                home
            ):
                raise ManagerError(
                    "suite_config_unavailable", "Suite configuration is unavailable.", 3
                )
            selected = config.get("ecosystem_home")
            if not isinstance(selected, str) or not selected:
                raise ManagerError(
                    "suite_config_unavailable", "Suite configuration is unavailable.", 3
                )
    ecosystem = (
        Path(selected).expanduser().absolute()
        if selected is not None
        else Path.home() / ".local/share/solmargintrader/ecosystem-paper-v2"
    )
    if ecosystem.is_symlink() or (ecosystem.exists() and not ecosystem.is_dir()):
        raise ManagerError(
            "suite_config_unavailable", "Ecosystem home is unavailable.", 3
        )
    return home, ecosystem


def component(state, reason, *, ready=None, **values):
    return {"state": state, "ready": ready, "reason": reason, **values}


def _held(path):
    try:
        return lock_held(path)
    except OSError:
        return None


def suite_probe(home, now):
    held = _held(home / ".suite" / "owner.lock")
    if held is False:
        return component("down", "suite_not_running", ready=False)
    if held is None:
        return component("unknown", "suite_owner_unverified")
    try:
        saved = private_read(home / ".suite" / "state.json", limit=16_384)
        if (
            saved.get("schema_version") != 1
            or saved.get("manager_home") != str(home)
            or not isinstance(saved.get("instance"), str)
            or len(saved["instance"]) != 32
            or type(saved.get("heartbeat")) not in (int, float)
            or not 0 <= saved["heartbeat"] <= now + 5
            or type(saved.get("pid")) is not int
            or saved["pid"] <= 0
            or type(saved.get("monitor_ready")) is not bool
        ):
            raise ValueError("suite_checkpoint_invalid")
        age = max(0, now - saved["heartbeat"])
        path = home / ".suite" / "control.sock"
        _owner_path(path)
        deadline = time.monotonic() + 0.25
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.25)
            client.connect(str(path))
            _peer(client)
            client.sendall(
                (
                    json.dumps({"operation": "ping", "instance": saved["instance"]})
                    + "\n"
                ).encode()
            )
            response = _read(client, 4096, deadline)
        if response != {
            "schema_version": 1,
            "instance": saved["instance"],
            "pid": saved["pid"],
        }:
            raise ValueError("suite_owner_mismatch")
        ready = age <= SUITE_STALE_SECONDS and saved["monitor_ready"]
        return component(
            "up" if ready else "degraded",
            "available"
            if ready
            else "component_alert_journal_unavailable"
            if not saved["monitor_ready"]
            else "suite_heartbeat_stale",
            ready=ready,
            heartbeat_age_seconds=round(age, 3),
        )
    except (OSError, ValueError, TypeError, KeyError, ManagerError):
        return component("unknown", "suite_probe_unavailable")


def manager_probe(home):
    held = _held(home / "supervisor.lock")
    if held is False:
        return component("down", "manager_not_running", ready=False)
    if held is None:
        return component("unknown", "manager_owner_unverified")
    try:
        result = request(home, "help", {})
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise ValueError("manager_probe_invalid")
        return component("up", "available", ready=True)
    except (OSError, ValueError, ManagerError):
        return component("degraded", "manager_probe_unavailable", ready=False)


def ui_probe(ecosystem_home, manager_home=None):
    try:
        from ecosystem.ui_service import status

        result = status(ecosystem_home, manager_home)
        if result.get("running"):
            return component("up", "available", ready=True), result.get("url")
        reason = result.get("reason", "control_server_unavailable")
        if not isinstance(reason, str) or not reason.replace("_", "").isalnum():
            reason = "control_server_unavailable"
        return component(
            "unknown" if result.get("occupied") else "down", reason, ready=False
        ), None
    except (ImportError, OSError, ValueError):
        return component("unknown", "control_room_unavailable"), None


def market_probe(ecosystem_home, now):
    """Observe the documented SOL reference archive; never initialize an archive."""
    archive = ecosystem_home / "oracle" / "SOL" / "history.sqlite3"
    if not archive.exists():
        return component("unknown", "reference_archive_absent")
    if archive.is_symlink() or not archive.is_file():
        return component("unknown", "reference_archive_unverified")
    db = None
    try:
        db = sqlite3.connect(archive.as_uri() + "?mode=ro", uri=True, timeout=0.05)
        db.execute("PRAGMA query_only=ON")
        deadline = time.monotonic() + 0.05
        db.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 100)
        if db.execute("PRAGMA application_id").fetchone()[0] != 0x4F52434C:
            raise ValueError("reference_archive_unverified")
        latest = db.execute(
            "SELECT observed FROM observations ORDER BY observed DESC LIMIT 1"
        ).fetchone()
        if latest is None:
            return component("unknown", "reference_observations_absent")
        observed = latest[0]
        if (
            type(observed) not in (int, float)
            or not math.isfinite(observed)
            or not 0 <= observed <= now + 5
        ):
            raise ValueError("reference_clock_unverified")
        age = max(0, now - observed)
        available = age <= MARKET_STALE_SECONDS
        return component(
            "up" if available else "degraded",
            "reference_fresh" if available else "reference_stale",
            ready=available,
            freshness_age_seconds=round(age, 3),
            certified=False,
        )
    except (OSError, sqlite3.Error, ValueError):
        return component("unknown", "reference_archive_unavailable")
    finally:
        if db is not None:
            db.close()


def snapshot(
    home, ecosystem_home, *, now=None, owned_manager=None, owned_suite=None, ui=None
):
    now = time.time() if now is None else now
    interface, url = ui if ui is not None else ui_probe(ecosystem_home, home)
    values = {
        "suite": owned_suite if owned_suite is not None else suite_probe(home, now),
        "manager": owned_manager if owned_manager is not None else manager_probe(home),
        "control_room": interface,
        "market_data": market_probe(ecosystem_home, now),
    }
    critical = [values[name] for name in ("suite", "manager", "control_room")]
    ready = all(value["state"] == "up" and value["ready"] is True for value in critical)
    states = [value["state"] for value in values.values()]
    overall = (
        "down"
        if any(value["state"] == "down" for value in critical)
        else "unknown"
        if any(value["state"] == "unknown" for value in critical)
        else "degraded"
        if any(state != "up" for state in states)
        else "up"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": now,
        "overall": overall,
        "ready": ready,
        "components": values,
        "ui_url": url,
        "orders_available": False,
    }


def check(home=None, ecosystem_home=None):
    home, ecosystem_home = homes(home, ecosystem_home)
    return snapshot(home, ecosystem_home)


def prometheus(value):
    """Only fixed component/state labels; unknown clocks are omitted, never zero."""
    lines = [
        "# HELP solbot_component_state Component state as a one-hot gauge.",
        "# TYPE solbot_component_state gauge",
    ]
    for name in COMPONENTS:
        row = value.get("components", {}).get(name, {})
        actual = row.get("state", "unknown")
        if actual not in STATES:
            actual = "unknown"
        for state in STATES:
            lines.append(
                f'solbot_component_state{{component="{name}",state="{state}"}} {int(actual == state)}'
            )
    lines.extend(
        [
            "# TYPE solbot_component_ready gauge",
            "# TYPE solbot_component_age_seconds gauge",
        ]
    )
    for name in COMPONENTS:
        row = value.get("components", {}).get(name, {})
        if type(row.get("ready")) is bool:
            lines.append(
                f'solbot_component_ready{{component="{name}"}} {int(row["ready"])}'
            )
        for field in ("heartbeat_age_seconds", "freshness_age_seconds"):
            age = row.get(field)
            if type(age) in (int, float) and math.isfinite(age) and age >= 0:
                lines.append(
                    f'solbot_component_age_seconds{{component="{name}",kind="{field}"}} {age}'
                )
    lines.extend(
        [
            "# TYPE solbot_suite_ready gauge",
            f"solbot_suite_ready {int(value.get('ready') is True)}",
        ]
    )
    return "\n".join(lines) + "\n"
