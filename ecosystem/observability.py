"""Bounded, redacted tails of explicit owner log sinks; no arbitrary file API."""

from __future__ import annotations

import os
import plistlib
import re
import stat
from pathlib import Path

from . import runner

SENSITIVE = re.compile(
    r"secret|password|passphrase|mnemonic|seed.?phrase|authorization|bearer|credential|private.?key|api.?key|\bkey\b|token",
    re.IGNORECASE,
)
OPAQUE = re.compile(r"[A-Za-z0-9+/_=-]{20,}")
MAX_BYTES = 32768


def redact(line: str) -> tuple[str, bool]:
    if SENSITIVE.search(line) or re.search(r"\[[\d,\s]{80,}\]", line):
        return "[redacted sensitive log line]", True
    original = line
    for key, value in os.environ.items():
        if SENSITIVE.search(key) and len(value) >= 6:
            line = line.replace(value, "[redacted]")
    line = OPAQUE.sub("[redacted opaque value]", line)
    line = "".join(c if c in "\t" or ord(c) >= 32 else "�" for c in line)
    return line[:2000], line != original


def _tail(path: Path, limit: int) -> dict:
    if path.is_symlink():
        raise ValueError("unsafe_log_path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("unsafe_log_path")
        offset = max(0, metadata.st_size - MAX_BYTES)
        handle.seek(offset)
        raw = handle.read(MAX_BYTES)
    if offset:
        raw = raw.split(b"\n", 1)[1] if b"\n" in raw else b""
    rows = raw.decode("utf-8", errors="replace").splitlines()
    return {
        "path": str(path),
        "bytes": metadata.st_size,
        "modified_at": metadata.st_mtime,
        "truncated": offset > 0 or len(rows) > limit,
        "lines": [
            {"text": value, "redacted": hidden}
            for value, hidden in (redact(line) for line in rows[-limit:])
        ],
    }


def logs(
    home: Path, server: str, *, limit: int = 100, manager_home: Path | None = None
) -> dict:
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("invalid_log_limit")
    home = Path(home).expanduser().absolute()
    if server == "pipeline":
        paths = [home / "supervisor.log"]
    elif server == "control":
        paths = [home / "control-room.log"]
    elif server == "backtest":
        state = runner.load(home)
        paths = (
            [home / "batches" / state["batch_id"] / "worker.log"]
            if state.get("batch_id")
            else []
        )
    elif server == "recorder":
        from soltui.pricefeed import paths as recorder_paths

        paths = [recorder_paths()["log"]]
    elif server == "manager":
        from botmanager.service import service
        from botmanager.store import data_home

        owner_home = Path(manager_home or data_home()).absolute()
        definition = Path(service("status", owner_home)["plist_path"])
        paths = []
        if (
            definition.is_file()
            and not definition.is_symlink()
            and definition.stat().st_size <= 65536
        ):
            payload = plistlib.loads(definition.read_bytes())
            for field in ("StandardOutPath", "StandardErrorPath"):
                value = payload.get(field)
                if isinstance(value, str):
                    path = Path(value)
                    if (
                        path.is_absolute()
                        and path.resolve().is_relative_to(owner_home.resolve())
                        and not SENSITIVE.search(path.name)
                    ):
                        paths.append(path)
    else:
        raise ValueError("unknown_log_owner")
    files = []
    for path in paths:
        try:
            files.append(_tail(Path(path), limit))
        except (OSError, ValueError):
            continue
    return {
        "schema_version": 1,
        "server": server,
        "status": "available" if files else "unavailable",
        "files": files,
        "reason": None if files else "owner_log_sink_missing_or_unavailable",
        "semantics": "bounded_redacted_log_tail_not_complete_history",
    }
