"""Shared asset exclusions for active strategy and acquisition universes."""

from __future__ import annotations

from collections.abc import Iterable

REMOVED_ASSETS = frozenset({"RAIN", "WBT", "HTX", "JST", "MNT", "XMR"})


def filter_removed_assets(assets: Iterable[str]) -> tuple[str, ...]:
    """Return normalized assets while omitting symbols removed from active lists."""
    return tuple(
        symbol
        for asset in assets
        if (symbol := str(asset).strip().upper()) and symbol not in REMOVED_ASSETS
    )


def require_active_asset(asset: str) -> str:
    """Normalize a selected symbol and refuse one removed from active lists."""
    symbol = str(asset).strip().upper()
    if symbol in REMOVED_ASSETS:
        raise ValueError(f"asset {symbol} has been removed from active coin lists")
    return symbol
