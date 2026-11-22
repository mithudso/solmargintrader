"""Donchian-channel breakout: long on a new N-bar high, flat on an M-bar low."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..types import BarWindow


class DonchianBreakout:
    """Classic turtle-style channel breakout.

    The entry channel deliberately EXCLUDES the current bar. Comparing the
    current close against a channel that already contains the current bar's
    own high would make the test nearly always false (and the reverse framing
    nearly always true) -- the channel must describe the past the breakout is
    breaking out of.
    """

    def __init__(self, entry_lookback: int = 20, exit_lookback: int = 10) -> None:
        if entry_lookback < 2 or exit_lookback < 2:
            raise ValueError("lookbacks must be >= 2")
        self.entry_lookback = entry_lookback
        self.exit_lookback = exit_lookback
        self._holding = False
        self.name = f"breakout_{entry_lookback}_{exit_lookback}"
        self.params: dict[str, Any] = {
            "entry_lookback": entry_lookback,
            "exit_lookback": exit_lookback,
        }

    def warmup_bars(self) -> int:
        """Longest channel, plus one bar so the channel excludes the present."""
        return max(self.entry_lookback, self.exit_lookback) + 1

    def on_bar(self, history: BarWindow) -> float:
        """Long above the prior-N-bar high; flat below the prior-M-bar low."""
        highs, lows, closes = history.highs, history.lows, history.closes
        need = self.warmup_bars()
        if len(closes) < need:
            return 0.0

        close = float(closes[-1])
        # [-1] is the current bar, so slice up to it and exclude it.
        upper = float(np.max(highs[-self.entry_lookback - 1 : -1]))
        lower = float(np.min(lows[-self.exit_lookback - 1 : -1]))

        if not self._holding and close > upper:
            self._holding = True
        elif self._holding and close < lower:
            self._holding = False
        return 1.0 if self._holding else 0.0
