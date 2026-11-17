"""Control boundary for one private, exclusive auto-trading session owner."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import time
from contextlib import closing
from pathlib import Path

_DEFAULT = {
    "mode": "paper",
    "asset": "BTC",
    "venue": "jupiter-cli-10x",
    "base_collateral_usd": 10.0,
    "max_collateral_usd": 15.0,
    "max_session_loss_usd": 50.0,
    "advice_enabled": False,
}
_BLOCK = (
    "Auto-trading unavailable: the existing feed exposes snapshots and buffers "
    "ticks; ordered continuous barrier monitoring and owner recovery are not verified."
)


def _home():
    if "ORACLE_AUTOTRADE_HOME" in os.environ:
        return Path(os.environ["ORACLE_AUTOTRADE_HOME"])

    default = Path.home() / ".local/state/oracle-autotrade"
    directory = Path.home() / ".config/oracle-autotrade"
    try:
        dirfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return default
    except OSError:
        raise ValueError("Auto-trade connection directory must be private") from None
    try:
        info = os.fstat(dirfd)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("Auto-trade connection directory must be private")
        try:
            fd = os.open(
                "connection.json",
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=dirfd,
            )
        except FileNotFoundError:
            return default
        except OSError:
            raise ValueError("Auto-trade connection file must be private") from None
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
                or info.st_nlink != 1
            ):
                raise ValueError("Auto-trade connection file must be private")
            with os.fdopen(fd, "rb") as stream:
                fd = -1
                raw = stream.read(4097)
        finally:
            if fd >= 0:
                os.close(fd)
    except OSError:
        raise ValueError("Auto-trade connection file cannot be read") from None
    finally:
        os.close(dirfd)

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate connection field")
            result[key] = value
        return result

    try:
        if len(raw) > 4096:
            raise ValueError("Connection file too large")
        value = json.loads(raw, object_pairs_hook=unique_pairs)
        if (
            not isinstance(value, dict)
            or set(value) != {"version", "state_home"}
            or type(value["version"]) is not int
            or value["version"] != 1
            or not isinstance(value["state_home"], str)
            or "\x00" in value["state_home"]
            or not Path(value["state_home"]).is_absolute()
        ):
            raise ValueError("Invalid connection schema")
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("Invalid auto-trade connection file") from None
    return Path(value["state_home"])


def _private_home_exists(home):
    try:
        info = home.lstat()
    except FileNotFoundError:
        return False
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise ValueError("Auto-trade state directory must be owner-only")
    return True


def _connect(home=None):
    home = _home() if home is None else home
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    _private_home_exists(home)
    path = home / "journal.sqlite3"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("Auto-trade journal must be owner-only")
    finally:
        os.close(fd)
    db = sqlite3.connect(path, timeout=5)
    db.execute(
        "CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL, at REAL NOT NULL)"
    )
    db.commit()
    return db


def _startup_receipt(home, code):
    path = home / "owner-start-error.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("Owner error receipt must be private")
        with os.fdopen(fd, "w") as stream:
            fd = -1
            json.dump({"error": "owner_start_failed", "exit_code": code}, stream)
    finally:
        if fd >= 0:
            os.close(fd)


def _saved_status(home):
    path = home / "journal.sqlite3"
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {}
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise ValueError("Auto-trade journal must be owner-only")
    with closing(
        sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True, timeout=0.2)
    ) as db:
        db.execute("PRAGMA query_only=ON")
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session'"
        ).fetchone():
            return {}
        row = db.execute("SELECT value FROM session WHERE singleton=1").fetchone()
    if not row:
        return {}
    value = json.loads(row[0])
    if not isinstance(value, dict):
        raise TypeError("Invalid saved auto-trade session")
    from oracle_leverage.autotrade_worker import public_state

    return public_state(value)


def _unavailable_status(home):
    result = {
        "state": "unavailable",
        "mode": None,
        "session_id": None,
        "position": None,
        "reason": (
            "Auto-trade owner unavailable; session and position are unknown. "
            "Inspection did not start or recover an owner. Use an explicit session action."
        ),
        "defaults": dict(_DEFAULT),
        "readiness": {
            "paper": "requires explicit Start Paper and fresh observed input",
            "live": "unavailable: position, fill and settlement binding unverified",
            "1000x": "paper proxy only; live close, queue and payout unverified",
            "advice": "off by default; credentials checked only on an advice call",
        },
    }
    # Retain saved next-session choices without migrating or recovering the owner.
    try:
        saved = _saved_status(home)
    except sqlite3.Error:
        raise RuntimeError(
            "Auto-trade owner and saved state unavailable; nothing was recovered"
        ) from None
    result.update(saved)
    result["last_known_state"] = saved.get("state")
    result["state"] = "unavailable"
    result["reason"] = (
        "Auto-trade owner unavailable; current session and position are unknown. "
        "Saved details are historical. Inspection did not start or recover an owner. "
        "Use an explicit session action."
    )
    position = result.get("position")
    if isinstance(position, dict) and position.get("state") in {"open", "closing"}:
        position["state"] = "unknown"
        position["reason"] = (
            "Owner unavailable; continuity and the current outcome are unknown"
        )
    return result


def _call(action, request_id=None, config=None):
    import socket
    import subprocess
    import sys

    home = _home()
    may_start_owner = action in {"start", "stop", "configure"}
    if may_start_owner:
        # Only an explicit session action may initialize storage or recover an owner.
        with closing(_connect(home)):
            pass
    else:
        _private_home_exists(home)
    request = (
        json.dumps(
            {"action": action, "request_id": request_id, "config": config},
            allow_nan=False,
        ).encode()
        + b"\n"
    )
    path = str(home / "owner.sock")

    def exchange():
        with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as client:
            client.settimeout(2)
            client.connect(path)
            client.sendall(request)
            data = bytearray()
            while b"\n" not in data and len(data) <= 1024 * 1024:
                part = client.recv(4096)
                if not part:
                    break
                data.extend(part)
            if b"\n" not in data:
                raise ValueError("Incomplete owner response")
            result = json.loads(data.split(b"\n", 1)[0])
            if not result.get("ok"):
                raise ValueError(result.get("error", "Owner refused request"))
            return result["result"]

    try:
        return exchange()
    except (FileNotFoundError, ConnectionRefusedError):
        if not may_start_owner:
            if action == "status":
                return _unavailable_status(home)
            raise RuntimeError(
                "Auto-trade owner unavailable; forecast was not sent"
            ) from None
        env = os.environ.copy()
        env["ORACLE_AUTOTRADE_HOME"] = str(home)
        try:
            child = subprocess.Popen(
                [sys.executable, "-m", "oracle_leverage.autotrade_worker"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
                env=env,
                cwd=str(Path(__file__).resolve().parent.parent),
            )
        except OSError:
            _startup_receipt(home, None)
            raise RuntimeError(
                "Auto-trade owner failed to start; private receipt recorded"
            ) from None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                return exchange()
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.05)
        code = child.poll()
        if code is None:
            child.terminate()
            try:
                code = child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                code = child.wait(timeout=2)
        _startup_receipt(home, code)
        raise RuntimeError("Auto-trade owner failed to start; private receipt recorded")


def status():
    return _call("status")


def start(request_id: str, config: dict) -> dict:
    return _call("start", request_id, config)


def stop(request_id: str, acknowledge_unknown: bool = False) -> dict:
    return _call("stop", request_id, {"acknowledge_unknown": acknowledge_unknown})


def configure(request_id: str, config: dict) -> dict:
    return _call("configure", request_id, config)


def ingest_forecast(request_id: str, forecast: dict) -> dict:
    return _call("forecast", request_id, forecast)
