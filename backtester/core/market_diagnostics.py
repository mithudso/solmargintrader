"""Safe request events; application logging configuration owns persistence."""

from contextlib import contextmanager
import logging

_LOGGER = logging.getLogger("backtester.market")
_OPERATIONS = frozenset({"coinbase", "coinbase_minutes", "alternate_candles", "kucoin_history", "spot_archive", "hyperliquid_funding", "okx_funding"})


@contextmanager
def market_request(operation: str):
    """Emit fixed operation/outcome fields without URL, body or exception text."""
    if operation not in _OPERATIONS:
        raise ValueError("unknown market request operation")
    _LOGGER.info("market.request %s attempt", operation, extra={"operation": operation, "outcome": "attempt"})
    try:
        yield
    except Exception as exc:
        _LOGGER.warning("market.request %s failed (%s)", operation, type(exc).__name__, extra={"operation": operation, "outcome": "failed", "error_type": type(exc).__name__})
        raise
    else:
        _LOGGER.info("market.request %s success", operation, extra={"operation": operation, "outcome": "success"})
