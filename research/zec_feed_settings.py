"""View preferences never share the private trading-configuration write path."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

SOURCES = ("jupiter", "coinbase")


def load_feeds(path: Path | None) -> dict[str, bool]:
    defaults = dict.fromkeys(SOURCES, True)
    if path is None:
        return defaults
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            return defaults
        value = json.loads(path.read_text())
        feeds = value.get("feeds") if isinstance(value, dict) else None
        if isinstance(feeds, dict) and all(type(feeds.get(k)) is bool for k in SOURCES):
            return {k: feeds[k] for k in SOURCES}
    except (OSError, ValueError, TypeError):
        pass
    return defaults


def save_feeds(path: Path | None, feeds: dict[str, bool]) -> None:
    if path is None:
        return
    if set(feeds) != set(SOURCES) or any(type(v) is not bool for v in feeds.values()):
        raise ValueError("invalid_feed_preferences")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".view-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump({"version": 1, "feeds": feeds}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
