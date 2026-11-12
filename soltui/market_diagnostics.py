"""Safe read-only market operation events through the standard logging handler.

Use ``with market_operation("fixed.operation")`` or apply it as a decorator.
Operation names are source constants. Never pass symbols, URLs or user text.
The logger emits only operation, outcome and exception class; handlers own storage.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import logging

LOGGER = logging.getLogger("soltui.market")


@contextmanager
def market_operation(operation: str):
    """Record one synchronous attempt/outcome without replacing its exception."""
    def emit(outcome, *, error=None, level=logging.INFO):
        row = {"event": "market.operation", "operation": operation, "outcome": outcome}
        if error is not None:
            row["error_type"] = type(error).__name__
        LOGGER.log(level, "%s", json.dumps(row, sort_keys=True))

    emit("started")
    try:
        yield
    except Exception as error:
        unavailable = getattr(error, "status", None) == 404
        emit("unavailable" if unavailable else "failed", error=error,
             level=logging.INFO if unavailable else logging.WARNING)
        raise
    else:
        emit("completed")
