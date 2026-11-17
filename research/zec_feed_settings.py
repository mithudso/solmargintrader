"""View preferences never share the private trading-configuration write path."""

from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
from pathlib import Path

SOURCES = ("jupiter", "coinbase")
_LOGGER = logging.getLogger(__name__)


def load_feeds(path: Path | None) -> dict[str, bool]:
    defaults = dict.fromkeys(SOURCES, True)
    if path is None:
        return defaults
    try:
        info = path.lstat()
    except FileNotFoundError:
        return defaults
    except OSError:
        _LOGGER.warning("Saved feed preferences are unavailable; feeds remain disabled")
        return dict.fromkeys(SOURCES, False)
    try:
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            raise ValueError("invalid_feed_preferences")
        value = json.loads(path.read_text())
        feeds = value.get("feeds") if isinstance(value, dict) else None
        if isinstance(feeds, dict) and all(type(feeds.get(k)) is bool for k in SOURCES):
            return {k: feeds[k] for k in SOURCES}
    except (OSError, ValueError, TypeError):
        _LOGGER.warning("Saved feed preferences are unavailable; feeds remain disabled")
        return dict.fromkeys(SOURCES, False)
    _LOGGER.warning("Saved feed preferences are invalid; feeds remain disabled")
    return dict.fromkeys(SOURCES, False)


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
