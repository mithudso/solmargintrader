"""One monotonic deadline for an inbound HTTP request, including slow drips."""
from __future__ import annotations

import time


class DeadlineReader:
    def __init__(self, source, connection, seconds, *, clock=time.monotonic):
        self.source, self.connection, self.clock = source, connection, clock
        self.deadline = clock() + seconds

    def read(self, size=-1):
        if size < 0:
            raise ValueError("bounded request read required")
        data = bytearray()
        while len(data) < size:
            remaining = self.deadline - self.clock()
            if remaining <= 0:
                raise TimeoutError("request deadline exceeded")
            self.connection.settimeout(remaining)
            chunk = self.source.read(1)
            if not chunk:
                break
            data.extend(chunk)
        return bytes(data)

    def readline(self, size=-1):
        data = bytearray()
        limit = 65537 if size < 0 else size
        while len(data) < limit:
            byte = self.read(1)
            if not byte:
                break
            data.extend(byte)
            if byte == b"\n":
                break
        return bytes(data)

    def close(self):
        self.source.close()
