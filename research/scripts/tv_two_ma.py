"""Source-level TradingView two-SMA crossover intents; not an order simulator."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable
from math import fsum, isfinite
from typing import Any


class TwoMovingAverages:
    """Evaluate the current and previous completed-bar averages causally."""

    def __init__(self, fast_length: int = 9, slow_length: int = 18) -> None:
        for length in (fast_length, slow_length):
            if not isinstance(length, int) or isinstance(length, bool) or length < 1:
                raise ValueError("SMA lengths must be positive integers")
        self.fast_length = fast_length
        self.slow_length = slow_length
        self._closes: deque[float] = deque(maxlen=max(fast_length, slow_length))
        self._previous: tuple[float, float] | None = None

    def on_close(self, close: float, intent_factory: Callable[..., Any] | None = None,
                 *, qty: float | None = None) -> list[Any]:
        """Emit market entry at a crossing; reject missing prices before mutation."""
        if not isfinite(close):
            raise ValueError("close must be finite; missing data is not simulated")
        if qty is not None and (not isfinite(qty) or qty <= 0):
            raise ValueError("quantity override must be positive and finite")
        self._closes.append(float(close))
        if len(self._closes) < max(self.fast_length, self.slow_length):
            return []
        values = list(self._closes)
        fast = fsum(values[-self.fast_length:]) / self.fast_length
        slow = fsum(values[-self.slow_length:]) / self.slow_length
        previous = self._previous
        self._previous = (fast, slow)
        if previous is None:
            return []
        side = 1 if fast > slow and previous[0] <= previous[1] else (
            -1 if fast < slow and previous[0] >= previous[1] else 0)
        if side == 0:
            return []
        if intent_factory is None:
            from research.pine_bar_emulator import Intent
            intent_factory = Intent
        arguments = {"id": "MA2CrossLE" if side == 1 else "MA2CrossSE", "action": "entry", "side": side}
        if qty is not None:
            arguments["qty"] = qty
        return [intent_factory(**arguments)]
