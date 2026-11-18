"""TradingView Pivot Reversal v33.0 adapter with explicit tie sensitivity.

The built-in Pine snapshot is src:f1cf879aa1a71c9a, SHA-256
cd6def72548fb84e02312f302dd2799f897638d0a2c688aef04ca861b5a5628f.
Pine pivot tie semantics remain unverified; no mode is certified parity.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from research.pine_bar_emulator import Bar, Intent


def pivot_intents(bars: Sequence[Bar], *, step_seconds: int, tick_size: float,
                  left: int = 4, right: int = 2, ties: str = "strict") -> list[list[Intent]]:
    """Emit source-ordered stop entries after pivots are confirmed.

    `ties` is an explicit research sensitivity: `strict` rejects equal peers,
    `latest` allows equals only to the left, and `earliest` only to the right.
    The source issues no cancellation when a pivot arm turns false; this
    adapter deliberately does not invent one.
    """
    if (type(step_seconds) is not int or step_seconds <= 0 or type(left) is not int or left < 1 or
            type(right) is not int or right < 1 or not math.isfinite(tick_size) or tick_size <= 0 or
            ties not in ("strict", "latest", "earliest")):
        raise ValueError("invalid cadence, tick, pivot window or tie policy")
    for i, b in enumerate(bars):
        if (type(b.timestamp) is not int or b.timestamp % step_seconds or
                any(not math.isfinite(v) or v <= 0 for v in (b.open, b.high, b.low, b.close)) or
                b.low > min(b.open, b.close) or b.high < max(b.open, b.close) or
                (i and b.timestamp-bars[i-1].timestamp != step_seconds)):
            raise ValueError("invalid, unaligned or missing OHLC bar")
    out: list[list[Intent]] = []
    high_level: float | None = None
    low_level: float | None = None
    long_armed = short_armed = False
    for i, bar in enumerate(bars):
        pivot_index = i-right
        high_pivot = low_pivot = None
        if pivot_index >= left:
            pivot = bars[pivot_index]
            prior = bars[pivot_index-left:pivot_index]
            later = bars[pivot_index+1:i+1]
            high_prior = all(pivot.high >= x.high if ties == "latest" else pivot.high > x.high for x in prior)
            high_later = all(pivot.high >= x.high if ties == "earliest" else pivot.high > x.high for x in later)
            low_prior = all(pivot.low <= x.low if ties == "latest" else pivot.low < x.low for x in prior)
            low_later = all(pivot.low <= x.low if ties == "earliest" else pivot.low < x.low for x in later)
            if high_prior and high_later:
                high_pivot = pivot.high
            if low_prior and low_later:
                low_pivot = pivot.low
        if high_pivot is not None:
            high_level, long_armed = high_pivot, True
        elif long_armed and high_level is not None and bar.high > high_level:
            long_armed = False
        if low_pivot is not None:
            low_level, short_armed = low_pivot, True
        elif short_armed and low_level is not None and bar.low < low_level:
            short_armed = False
        group = []
        if long_armed and high_level is not None:
            group.append(Intent("PivRevLE", "entry", 1, "stop", high_level+tick_size))
        if short_armed and low_level is not None:
            group.append(Intent("PivRevSE", "entry", -1, "stop", low_level-tick_size))
        out.append(group)
    return out
