"""Close-time intents for the TradingView Price Channel v29 built-in."""
from __future__ import annotations

import math
from collections.abc import Sequence

from research.pine_bar_emulator import Intent


def price_channel_intents(closes: Sequence[float], highs: Sequence[float],
                          lows: Sequence[float], length: int = 20) -> list[Intent]:
    """Emit both resting stops after the source's ``close[length]`` guard."""
    if type(length) is not int or length < 1:
        raise ValueError("length must be a positive integer")
    if len(closes) != len(highs) or len(closes) != len(lows):
        raise ValueError("bar fields must have equal lengths")
    if len(closes) <= length or not math.isfinite(closes[-1-length]):
        return []
    window_high, window_low = highs[-length:], lows[-length:]
    if not all(math.isfinite(x) and x > 0 for x in (*window_high, *window_low)):
        raise ValueError("channel extrema must be positive and finite")
    return [Intent("PChLE", "entry", 1, "stop", max(window_high)),
            Intent("PChSE", "entry", -1, "stop", min(window_low))]
