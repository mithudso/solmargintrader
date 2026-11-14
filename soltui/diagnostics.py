"""Fixed metadata for external reads; never pass URLs or provider text as labels.

Use ``@external_read("component.operation")`` on a transport wrapper, or use
the same helper as a context manager. Request/success use DEBUG; failure uses
WARNING with the exception class only. The original exception still propagates.
The helper uses the Python standard library and needs no separate setup.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

_LOGGER = logging.getLogger(__name__)


@contextmanager
def external_read(operation: str):
    """Observe one bounded read without retaining its arguments or result."""
    _LOGGER.debug("external read", extra={"operation": operation, "phase": "request"})
    try:
        yield
    except Exception as exc:
        _LOGGER.warning("external read failed", extra={"operation": operation, "phase": "failure",
                                                       "error_kind": type(exc).__name__})
        raise
    _LOGGER.debug("external read", extra={"operation": operation, "phase": "success"})
