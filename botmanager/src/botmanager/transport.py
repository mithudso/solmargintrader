"""Bounded mode-0600 local command socket; registry is the sole dispatcher."""

from __future__ import annotations

import ctypes
import json
import os
import socket
import stat
import struct
import sys
import time
from pathlib import Path

from .domain import ManagerError, canonical

MAX_REQUEST = 65536
MAX_RESPONSE = 1024 * 1024
CLIENT_REQUEST_SECONDS = 1.0
SERVER_REQUEST_SECONDS = 0.2


def _owner_path(path: Path, socket_required=True):
    info = path.lstat()
    if (
        info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or (socket_required and not stat.S_ISSOCK(info.st_mode))
    ):
        raise ManagerError(
            "unsafe_transport", "Local socket ownership or mode is invalid.", 3
        )


def _peer(connection):
    if sys.platform == "darwin":
        # CPython exposes LOCAL_PEERCRED but not getpeereid on macOS. Use the
        # platform libc function rather than guessing xucred ABI struct offsets.
        libc = ctypes.CDLL(None, use_errno=True)
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        getpeereid = libc.getpeereid
        getpeereid.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
        ]
        getpeereid.restype = ctypes.c_int
        if (
            getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0
            or uid.value != os.getuid()
        ):
            raise ManagerError(
                "unsafe_transport", "Socket peer is not the current user.", 3
            )
    elif hasattr(connection, "getpeereid"):
        if connection.getpeereid()[0] != os.getuid():
            raise ManagerError(
                "unsafe_transport", "Socket peer is not the current user.", 3
            )
    elif hasattr(socket, "SO_PEERCRED"):
        _, uid, _ = struct.unpack(
            "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        if uid != os.getuid():
            raise ManagerError(
                "unsafe_transport", "Socket peer is not the current user.", 3
            )


def _remaining(connection, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Local command deadline expired")
    connection.settimeout(remaining)


def _read(connection, limit, deadline):
    data = bytearray()
    while b"\n" not in data:
        _remaining(connection, deadline)
        chunk = connection.recv(min(4096, limit + 1 - len(data)))
        if not chunk:
            raise ValueError
        data.extend(chunk)
        if len(data) > limit:
            raise ValueError
    if data.count(b"\n") != 1 or not data.endswith(b"\n"):
        raise ValueError
    return json.loads(data)


def request(home: Path, command: str, params: dict):
    path = home / "supervisor.sock"
    deadline = time.monotonic() + CLIENT_REQUEST_SECONDS
    try:
        _owner_path(path)
        payload = (canonical({"command": command, "params": params}) + "\n").encode()
        if len(payload) > MAX_REQUEST:
            raise ValueError
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            _remaining(client, deadline)
            client.connect(str(path))
            _peer(client)
            _remaining(client, deadline)
            client.sendall(payload)
            return _read(client, MAX_RESPONSE, deadline)
    except ManagerError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise ManagerError(
            "supervisor_unreachable",
            "Local supervisor did not return a valid response.",
            3,
        ) from exc


class CommandServer:
    def __init__(self, home: Path):
        self.home = home
        self.path = home / "supervisor.sock"
        if self.path.exists():
            _owner_path(self.path)
            self.path.unlink()
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.socket.bind(str(self.path))
            self.path.chmod(0o600)
            self.socket.listen(8)
            self.socket.setblocking(False)
        except BaseException:
            self.socket.close()
            raise

    def poll(self):
        from .registry import CommandContext, dispatch

        try:
            connection, _ = self.socket.accept()
        except BlockingIOError:
            return
        with connection:
            deadline = time.monotonic() + SERVER_REQUEST_SECONDS
            try:
                _peer(connection)
                message = _read(connection, MAX_REQUEST, deadline)
                if (
                    set(message) != {"command", "params"}
                    or message["command"]
                    not in {
                        "start",
                        "stop",
                        "status",
                        "config",
                        "list",
                        "events",
                        "help",
                    }
                    or not isinstance(message["params"], dict)
                    or ":" in str(message["params"].get("identity", ""))
                    or (
                        message["command"] == "status"
                        and not message["params"].get("identity")
                    )
                ):
                    raise ValueError
                response = dispatch(
                    message["command"],
                    message["params"],
                    CommandContext(home=self.home),
                )
                encoded = (canonical(response) + "\n").encode()
                if len(encoded) > MAX_RESPONSE:
                    raise ValueError
                _remaining(connection, deadline)
                connection.sendall(encoded)
            except (OSError, ValueError, TypeError, KeyError, ManagerError):
                return

    def close(self):
        self.socket.close()
        if self.path.exists():
            _owner_path(self.path)
            self.path.unlink()
