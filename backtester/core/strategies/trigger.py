"""Trigger trading: wait for a mined trigger, enter next open, exit when the context expires.

The conditions come from `core/trigger_conditions.py`, the same causal code the
miner (`research/triggers.py`) scores, so what is traded is what was measured:

  * the trigger is evaluated at the CLOSE of bar t from bars <= t;
  * the target is returned then, so the engine fills it at the OPEN of bar t+1;
  * the position is held for `horizon` bars and the exit is decided at the close
    of bar t+horizon (filled at the next open), or earlier if the close is
    `stop` below the entry open (stop fractions come from the trigger's MAE).

A funding condition is refused: this strategy sees OHLCV only.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..trigger_conditions import BASE_CONDITIONS, FUNDING_CONDITIONS, compute_conditions
from ..types import BarWindow

# Trailing bars handed to the condition code. EMAs forget geometrically, so 600
# bars reproduce full-history values to far better than a decision threshold.
WINDOW = 600


class TriggerTrade:
    """Directional trade on a conjunction of conditions, flat otherwise."""

    def __init__(self, conditions: str = "rsi_lt30&bb_touch_lo", direction: int = 1,
                 horizon: int = 3, stop: float = 0.0) -> None:
        names = tuple(x for x in conditions.split("&") if x)
        if not names or len(names) > 3:
            raise ValueError("conditions must name 1 to 3 conditions joined by '&'")
        for n in names:
            if n not in BASE_CONDITIONS:
                raise ValueError(f"unknown condition {n!r}")
            if n in FUNDING_CONDITIONS:
                raise ValueError("funding conditions need funding data; trigger_trade sees OHLCV only")
        if direction not in (1, -1):
            raise ValueError("direction must be 1 (long) or -1 (short)")
        if horizon < 1:
            raise ValueError("horizon must be at least 1 bar")
        if not np.isfinite(stop) or not stop >= 0.0:
            raise ValueError("stop must be a nonnegative fraction")
        self.names, self.direction, self.horizon, self.stop = names, int(direction), int(horizon), float(stop)
        self._entry_i: int | None = None
        self.name = f"trigger_{'+'.join(names)}_{'L' if direction == 1 else 'S'}{horizon}"
        self.params: dict[str, Any] = {"conditions": conditions, "direction": direction,
                                       "horizon": horizon, "stop": stop}

    def warmup_bars(self) -> int:
        """Longest condition lookback: a 60-bar high plus slack."""
        return 120

    def _fires(self, history: BarWindow) -> bool:
        o, h, l, c, v = (a[-WINDOW:] for a in (history.opens, history.highs, history.lows,
                                               history.closes, history.volumes))
        cond = compute_conditions(o, h, l, c, v, None, names=set(self.names))
        return all(bool(cond[n][-1]) for n in self.names)

    def on_bar(self, history: BarWindow) -> float:
        """+/-1 while a trigger's context is live, else 0. Reads bars <= i only."""
        i = history.i
        if self._entry_i is not None and i >= self._entry_i:
            held_through_here = i - self._entry_i + 1
            entry = float(history.opens[self._entry_i])
            r = self.direction * (float(history.closes[i]) / entry - 1.0)
            expired = held_through_here >= self.horizon
            stopped = self.stop > 0 and r <= -self.stop
            if expired or stopped:
                self._entry_i = None
                # A same-side target would retain the old position and erase
                # its stop baseline. The next open must first execute flat.
                return 0.0
            return float(self.direction)
        if self._entry_i is None and self._fires(history):
            self._entry_i = i + 1
            return float(self.direction)
        return float(self.direction) if self._entry_i is not None else 0.0
