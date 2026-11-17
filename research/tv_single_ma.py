"""Source-level TradingView single-SMA order intents, not a fill simulator.

Pinned built-in source: src:d009b1e195649778, Pine 31.0. The shared
emulator supplies the order factory; this module does not size or fill orders.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable
from math import fsum, isfinite
from typing import Any


class SingleMovingAverage:
    """Evaluate one completed close at a time, retaining only causal state."""

    def __init__(self, length: int = 9, confirm_bars: int = 1) -> None:
        if not isinstance(length, int) or isinstance(length, bool) or length < 1:
            raise ValueError("length must be a positive integer")
        if not isinstance(confirm_bars, int) or isinstance(confirm_bars, bool) or confirm_bars < 1:
            raise ValueError("confirm_bars must be a positive integer")
        self.length = length
        self.confirm_bars = confirm_bars
        self._closes: deque[float] = deque(maxlen=length)
        self._above = 0
        self._below = 0

    def on_close(self, close: float, intent_factory: Callable[..., Any] | None = None,
                 *, qty: float | None = None) -> list[Any]:
        """Emit at most one market entry intent. Never fill on this bar.

        Missing/nonfinite closes are rejected pending a proven Pine `na` policy.
        The rejection precedes every state mutation, so callers cannot silently
        bridge missing data. No performance or live-trading claim is implied.
        """
        if not isfinite(close):
            raise ValueError("close must be finite; missing data is not simulated")
        if qty is not None and (not isfinite(qty) or qty <= 0):
            raise ValueError("quantity override must be positive and finite")
        self._closes.append(float(close))
        if len(self._closes) < self.length:
            self._above = self._below = 0
            return []
        average = fsum(self._closes) / self.length
        self._above = self._above + 1 if close > average else 0
        self._below = self._below + 1 if close < average else 0
        if self._above != self.confirm_bars and self._below != self.confirm_bars:
            return []
        if intent_factory is None:
            from research.pine_bar_emulator import Intent
            intent_factory = Intent
        arguments = {"id": "MACrossLE" if self._above == self.confirm_bars else "MACrossSE",
                     "action": "entry", "side": 1 if self._above == self.confirm_bars else -1}
        if qty is not None:
            arguments["qty"] = qty
        return [intent_factory(**arguments)]
