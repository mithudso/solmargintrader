"""Research adapter for TradingView Parabolic SAR strategy v33.0.

Derived independently from the owner-requested built-in source; unregistered,
offline and not certified TradingView fill parity. The source snapshot is
src:260da27279d3c3e8, SHA-256
800f3fe7f02df408f9f144951e6e44744240a67dec2825d0953d5309b0a4bef1.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from research.pine_bar_emulator import Bar, Intent


def sar_intents(bars: Sequence[Bar], *, step_seconds: int, start: float = .02,
                increment: float = .02, maximum: float = .2) -> list[list[Intent]]:
    """Emit confirmed-bar next-SAR stop entry and opposite cancellation."""
    if (type(step_seconds) is not int or step_seconds <= 0 or
            any(not math.isfinite(v) or v <= 0 for v in (start, increment, maximum)) or start > maximum):
        raise ValueError("invalid SAR parameters or cadence")
    for i, b in enumerate(bars):
        if (type(b.timestamp) is not int or b.timestamp % step_seconds or
                any(not math.isfinite(v) or v <= 0 for v in (b.open, b.high, b.low, b.close)) or
                b.low > min(b.open, b.close) or b.high < max(b.open, b.close) or
                (i and b.timestamp-bars[i-1].timestamp != step_seconds)):
            raise ValueError("invalid, unaligned or missing OHLC bar")
    result: list[list[Intent]] = [[] for _ in bars]
    uptrend = False
    extreme = sar = next_sar = 0.0
    acceleration = start
    for i in range(1, len(bars)):
        b, prev = bars[i], bars[i-1]
        first = False
        sar = next_sar
        if i == 1:
            uptrend = b.close > prev.close
            extreme = b.high if uptrend else b.low
            prior_sar = prev.low if uptrend else prev.high
            prior_extreme = b.high if uptrend else b.low
            first = True
            sar = prior_sar + start*(prior_extreme-prior_sar)
        if uptrend:
            if sar > b.low:
                first, uptrend = True, False
                sar, extreme, acceleration = max(extreme, b.high), b.low, start
        elif sar < b.high:
            first, uptrend = True, True
            sar, extreme, acceleration = min(extreme, b.low), b.high, start
        if not first:
            if uptrend and b.high > extreme:
                extreme, acceleration = b.high, min(acceleration+increment, maximum)
            elif not uptrend and b.low < extreme:
                extreme, acceleration = b.low, min(acceleration+increment, maximum)
        if uptrend:
            sar = min(sar, prev.low)
            if i > 1:
                sar = min(sar, bars[i-2].low)
        else:
            sar = max(sar, prev.high)
            if i > 1:
                sar = max(sar, bars[i-2].high)
        next_sar = sar + acceleration*(extreme-sar)
        if uptrend:
            result[i] = [Intent("ParSE", "entry", -1, "stop", next_sar), Intent("ParLE", "cancel", 1)]
        else:
            result[i] = [Intent("ParLE", "entry", 1, "stop", next_sar), Intent("ParSE", "cancel", -1)]
    return result
