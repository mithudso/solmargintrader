"""Keep the installed control room independent of the paper pipeline process.

A process ID is diagnostic. Readiness requires the canonical owner lock, its
private generation checkpoint and a matching response from the bound HTTP port.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from .runner import save

LOCK_NAME = "control-server.lock"
CHECKPOINT_NAME = "control-server.json"
LAUNCH_LOCK_NAME = "control-launch.lock"
STARTUP_SECONDS = 10.0
POLL_SECONDS = 0.05
HTTP_TIMEOUT = 0.4
MAX_BYTES = 16_384
INSTANCE = re.compile(r"(?:[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\Z")
_OWNED: ContextVar[dict[str, int] | None] = ContextVar(
    "control_room_owned_locks", default=None
)


def _home(home) -> Path:
    home = Path(home).expanduser().absolute()
    if home.is_symlink() or (home.exists() and not home.is_dir()):
        raise ValueError("control_home_unavailable")
    return home


def _identity(path: Path, fd: int):
    current = os.stat(path, follow_symlinks=False)
    opened = os.fstat(fd)
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.getuid()
        or stat.S_IMODE(opened.st_mode) & 0o077
        or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
    ):
        raise ValueError("control_file_owner_unverified")
    return opened


@contextmanager
def _exclusive(home: Path, name: str, *, wait_seconds=0.0):
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = home / name
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        _identity(path, fd)
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(POLL_SECONDS)
        _identity(path, fd)
        yield fd
    finally:
        os.close(fd)


@contextmanager
def lock(home):
    """Hold only the control-server lock; never use the pipeline's lock."""
    home = _home(home)
    with _exclusive(home, LOCK_NAME) as fd:
        token = _OWNED.set({**(_OWNED.get() or {}), str(home): fd})
        try:
            yield fd
        finally:
            _OWNED.reset(token)


def _owned(home: Path):
    fd = (_OWNED.get() or {}).get(str(home))
    if fd is None:
        raise RuntimeError("control_server_lock_required")
    return _identity(home / LOCK_NAME, fd)


def _url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError("invalid_control_url")
    parts = urlsplit(value)
    if (
        parts.scheme != "http"
        or parts.hostname != "127.0.0.1"
        or parts.username
        or parts.password
        or not parts.port
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("invalid_control_url")
    return f"http://127.0.0.1:{parts.port}"


def checkpoint(home, instance: str, url: str, pid: int | None = None) -> dict:
    """Publish bound identity while this context holds the canonical lock."""
    home = _home(home)
    identity = _owned(home)
    if not isinstance(instance, str) or not INSTANCE.fullmatch(instance):
        raise ValueError("invalid_control_instance")
    pid = os.getpid() if pid is None else pid
    if type(pid) is not int or not 0 < pid < 2**31:
        raise ValueError("invalid_control_pid")
    result = {
        "schema_version": 1,
        "instance": instance,
        "home": str(home),
        "url": _url(url),
        "pid": pid,
        "version": __version__,
        "lock_device": identity.st_dev,
        "lock_inode": identity.st_ino,
    }
    save(home / CHECKPOINT_NAME, result)
    return result


def _read(home: Path) -> dict:
    path = home / CHECKPOINT_NAME
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        _identity(path, fd)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(MAX_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_BYTES:
        raise ValueError("invalid_control_checkpoint")
    value = json.loads(raw)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or value.get("home") != str(home)
        or not isinstance(value.get("instance"), str)
        or not INSTANCE.fullmatch(value["instance"])
        or not isinstance(value.get("version"), str)
        or not re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}", value["version"])
        or type(value.get("pid")) is not int
        or not 0 < value["pid"] < 2**31
        or any(
            type(value.get(key)) is not int or value[key] < 0
            for key in ("lock_device", "lock_inode")
        )
    ):
        raise ValueError("invalid_control_checkpoint")
    value["url"] = _url(value.get("url"))
    return value


def clear_checkpoint(home, instance: str) -> None:
    """Remove this generation's pointer before releasing the owner lock."""
    home = _home(home)
    _owned(home)
    try:
        current = _read(home)
    except FileNotFoundError:
        return
    if current["instance"] == instance:
        (home / CHECKPOINT_NAME).unlink()


def _locked(home: Path):
    path = home / LOCK_NAME
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    except FileNotFoundError:
        return False, None
    try:
        identity = _identity(path, fd)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True, identity
        return False, identity
    finally:
        os.close(fd)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, newurl):
        return None


def _health(record: dict) -> bool:
    # Local readiness must never follow a redirect or an inherited HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(
        record["url"] + "/health", headers={"Accept": "application/json"}
    )
    try:
        with opener.open(request, timeout=HTTP_TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES:
                return False
        body = json.loads(raw)
        if not isinstance(body, dict):
            return False
        data = body.get("data")
        return bool(
            body.get("schema_version") == 1
            and body.get("ok") is True
            and isinstance(data, dict)
            and data.get("control_instance") == record["instance"]
            and data.get("control_home") == record["home"]
            and data.get("ecosystem_version") == record["version"]
        )
    except (OSError, ValueError, UnicodeError, HTTPException):
        return False


def _unavailable(reason, *, occupied=False, held=False):
    return {
        "running": False,
        "url": None,
        "pid": None,
        "version": __version__,
        "reason": reason,
        "occupied": occupied,
        "owner_lock_held": held,
    }


def status(home) -> dict:
    """Read lock plus HTTP identity; never create a directory or trust a PID."""
    try:
        home = _home(home)
        held, identity = _locked(home)
        try:
            record = _read(home)
        except FileNotFoundError:
            return _unavailable(
                "control_checkpoint_pending" if held else "control_server_not_running",
                occupied=held,
                held=held,
            )
        except (OSError, ValueError, UnicodeError):
            return _unavailable(
                "control_checkpoint_unverified", occupied=True, held=held
            )
        if held:
            if (identity.st_dev, identity.st_ino) != (
                record["lock_device"],
                record["lock_inode"],
            ):
                return _unavailable(
                    "control_server_owner_unverified", occupied=True, held=True
                )
            if record["version"] != __version__:
                return _unavailable(
                    "control_server_version_mismatch", occupied=True, held=True
                )
            if _health(record):
                return {
                    "running": True,
                    "url": record["url"],
                    "pid": record["pid"],
                    "version": record["version"],
                    "instance": record["instance"],
                    "reason": None,
                    "occupied": True,
                    "owner_lock_held": True,
                }
            return _unavailable(
                "control_server_health_unverified", occupied=True, held=True
            )
        if _health(record):
            # A server whose lock file was replaced may still answer its port.
            return _unavailable("control_server_owner_unverified", occupied=True)
        return _unavailable("control_server_not_running")
    except (OSError, ValueError, UnicodeError):
        return _unavailable("control_server_owner_unverified", occupied=True)


def _environment():
    return {
        **{
            key: value
            for key, value in os.environ.items()
            if not key.startswith("PYTHON")
        },
        "PYTHONNOUSERSITE": "1",
    }


def ensure(home, manager_home=None, *, on_spawn=None) -> dict:
    """Start at most one installed server and observe real readiness for 10s."""
    process = None
    deadline = time.monotonic() + STARTUP_SECONDS
    try:
        home = _home(home)
        with _exclusive(home, LAUNCH_LOCK_NAME, wait_seconds=STARTUP_SECONDS):
            current = status(home)
            if current["running"]:
                return current
            if time.monotonic() >= deadline:
                return _unavailable(
                    "control_start_in_progress",
                    occupied=current["occupied"],
                    held=current["owner_lock_held"],
                )
            if not current["occupied"]:
                command = [
                    sys.executable,
                    "-I",
                    "-m",
                    "ecosystem.web",
                    "--home",
                    str(home),
                    "--persistent",
                    "--port",
                    "0",
                ]
                if manager_home is not None:
                    command.extend(["--manager-home", str(_home(manager_home))])
                log_path = home / "control-room.log"
                fd = os.open(
                    log_path,
                    os.O_CREAT | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW,
                    0o600,
                )
                try:
                    _identity(log_path, fd)
                    with os.fdopen(fd, "ab", closefd=False) as log:
                        process = subprocess.Popen(
                            command,
                            cwd="/tmp",
                            stdin=subprocess.DEVNULL,
                            stdout=log,
                            stderr=log,
                            env=_environment(),
                            close_fds=True,
                            start_new_session=True,
                        )
                        # Availability supervisors receive only the process
                        # they actually created, never an adopted owner's PID.
                        if on_spawn is not None:
                            on_spawn(process)
                finally:
                    os.close(fd)
            elif current["reason"] != "control_checkpoint_pending":
                return current
            while time.monotonic() < deadline:
                current = status(home)
                if current["running"]:
                    return current
                if process is not None and process.poll() is not None:
                    return _unavailable("control_server_exited")
                time.sleep(POLL_SECONDS)
            return _unavailable(
                "control_server_start_timeout",
                occupied=current["occupied"],
                held=current["owner_lock_held"],
            )
    except BlockingIOError:
        current = status(home)
        return (
            current
            if current["running"]
            else _unavailable("control_start_in_progress", occupied=True)
        )
    except (OSError, RuntimeError, ValueError, TypeError):
        return _unavailable("control_server_start_failed")
