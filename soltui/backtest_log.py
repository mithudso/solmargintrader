"""Bounded, nonblocking reads of the detached backtest worker's append-only log."""

from __future__ import annotations

import codecs
import os
from pathlib import Path


class BacktestLog:
    """Follow bytes written after construction, including after rotation or truncation.

    Poll from the UI timer.  The worker owns its process and log; this object owns no
    thread, file descriptor or process, so destroying the view needs no teardown.
    """

    def __init__(self, path: Path, *, max_bytes: int = 64 * 1024) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.path = path
        self.max_bytes = max_bytes
        self._identity: tuple[int, int] | None = None
        self._offset = 0
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            stat = path.stat()
        except OSError:
            pass
        else:
            self._identity = (stat.st_dev, stat.st_ino)
            self._offset = stat.st_size

    def poll(self) -> str:
        """Return newly appended text, reading at most max_bytes on any one poll."""
        try:
            with self.path.open("rb") as stream:
                stat = stream.seek(0, 2)
                info = os.fstat(stream.fileno())
                identity = (info.st_dev, info.st_ino)
                if identity != self._identity or stat < self._offset:
                    self._identity = identity
                    self._offset = 0
                    self._decoder.reset()
                if stat - self._offset > self.max_bytes:
                    self._offset = stat - self.max_bytes
                    self._decoder.reset()
                stream.seek(self._offset)
                data = stream.read(self.max_bytes)
                self._offset = stream.tell()
        except OSError:
            return ""
        return self._decoder.decode(data, final=False)
