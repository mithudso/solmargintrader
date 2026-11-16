"""Close-time intents for TradingView Volatility Expansion Close v30."""
from __future__ import annotations

import math
from collections.abc import Sequence

from research.pine_bar_emulator import Intent


def volty_close_intents(closes: Sequence[float], highs: Sequence[float],
                        lows: Sequence[float], length: int = 5,
                        multiplier: float = .75) -> list[Intent]:
    """Use simple mean of true range, not Wilder ATR, on complete bars."""
    if type(length) is not int or length < 1 or not math.isfinite(multiplier):
        raise ValueError("invalid length or multiplier")
    if len(closes) != len(highs) or len(closes) != len(lows):
        raise ValueError("bar fields must have equal lengths")
    if len(closes) <= length or not math.isfinite(closes[-1-length]):
        return []
    c, h, lo = closes[-length-1:], highs[-length:], lows[-length:]
    if not all(math.isfinite(x) and x > 0 for x in (*c,*h,*lo)):
        raise ValueError("bar fields must be positive and finite")
    if any(a < b for a,b in zip(h,lo,strict=True)):
        raise ValueError("bar high must not be below low")
    ranges = [max(a-b,abs(a-p),abs(b-p)) for a,b,p in zip(h,lo,c[:-1],strict=True)]
    offset = sum(ranges) / length * multiplier
    return [Intent("VltClsLE", "entry", 1, "stop", c[-1] + offset),
            Intent("VltClsSE", "entry", -1, "stop", c[-1] - offset)]
