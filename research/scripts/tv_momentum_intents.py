"""TradingView Momentum v29 close-of-bar order intents; no execution or fills."""
from __future__ import annotations

import math
from collections.abc import Sequence

from research.pine_bar_emulator import Intent


def momentum_intents(
    closes: Sequence[float], high: float, low: float, tick_size: float, length: int = 12
) -> list[Intent]:
    """Emit the two source-ordered actions for the latest completed bar.

    ``closes`` must end at that bar. The shared emulator makes new orders
    eligible later; this function neither fills orders nor chooses position size.
    """
    if isinstance(length, bool) or not isinstance(length, int) or length < 1:
        raise ValueError("length must be a positive integer")
    if not all(math.isfinite(x) for x in (high, low, tick_size)) or tick_size <= 0 or high < low:
        raise ValueError("invalid bar extrema or tick size")
    if len(closes) < length + 2:
        return [Intent("MomLE", "cancel", 1), Intent("MomSE", "cancel", -1)]
    current, previous, past, past_previous = closes[-1], closes[-2], closes[-1-length], closes[-2-length]
    if not all(math.isfinite(x) for x in (current, previous, past, past_previous)):
        return [Intent("MomLE", "cancel", 1), Intent("MomSE", "cancel", -1)]
    momentum = current - past
    change = momentum - (previous - past_previous)
    long = (Intent("MomLE", "entry", 1, "stop", high + tick_size)
            if momentum > 0 and change > 0 else Intent("MomLE", "cancel", 1))
    short = (Intent("MomSE", "entry", -1, "stop", low - tick_size)
             if momentum < 0 and change < 0 else Intent("MomSE", "cancel", -1))
    return [long, short]
