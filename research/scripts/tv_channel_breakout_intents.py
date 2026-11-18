"""Close-time intents for TradingView Channel Breakout v29, not Price Channel."""
from __future__ import annotations

import math
from collections.abc import Sequence

from research.pine_bar_emulator import Intent


def channel_breakout_intents(closes: Sequence[float], highs: Sequence[float],
                             lows: Sequence[float], tick_size: float,
                             length: int = 5) -> list[Intent]:
    """Emit source-ordered stops; only the long has the close[length] guard."""
    if type(length) is not int or not 1 <= length <= 1000:
        raise ValueError("length must be in [1, 1000]")
    if not math.isfinite(tick_size) or tick_size <= 0:
        raise ValueError("tick size must be positive and finite")
    if len(closes) != len(highs) or len(closes) != len(lows):
        raise ValueError("bar fields must have equal lengths")
    if not closes:
        return []
    window_high, window_low = highs[-length:], lows[-length:]
    if not all(math.isfinite(x) and x > 0 for x in (*window_high, *window_low)):
        raise ValueError("channel extrema must be positive and finite")
    orders = []
    if len(closes) > length and math.isfinite(closes[-1-length]):
        orders.append(Intent("ChBrkLE", "entry", 1, "stop", max(window_high) + tick_size))
    orders.append(Intent("ChBrkSE", "entry", -1, "stop", min(window_low) - tick_size))
    return orders
