"""USD spot prices from Coinbase's public endpoint (no key). A price it cannot give is None, never 0.

`https://api.coinbase.com/v2/prices/<SYMBOL>-USD/spot` answers `{"data": {"amount": "76021.455"}}`.
A symbol Coinbase does not list answers an error body; that, a network failure and a non-positive or
non-finite amount all become None, so the caller reports the value as unknown instead of as zero.
"""

from __future__ import annotations

import math
from typing import Any, Callable

COINBASE_SPOT = "https://api.coinbase.com/v2/prices/{symbol}-USD/spot"


def spot_prices(fetch: Callable[..., Any], symbols: list[str]) -> tuple[dict[str, float | None], list[str]]:
    """({symbol: price or None}, [error messages]). One request per distinct symbol."""
    from .wallet import WalletHttpError  # noqa: PLC0415 - wallet imports this module's callers

    prices: dict[str, float | None] = {}
    errors: list[str] = []
    for sym in dict.fromkeys(symbols):
        try:
            reply = fetch(COINBASE_SPOT.format(symbol=sym))
        except WalletHttpError as exc:
            # 404 is Coinbase saying it does not list the symbol: unknown, not an outage.
            if exc.status != 404:
                errors.append(f"coinbase {sym}: {exc}")
            prices[sym] = None
            continue
        try:
            value = float(((reply or {}).get("data") or {}).get("amount"))
        except (TypeError, ValueError, AttributeError):
            value = math.nan
        prices[sym] = value if math.isfinite(value) and value > 0 else None
    return prices, errors
