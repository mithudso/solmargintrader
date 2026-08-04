"""Moving-average crossover: long while the fast SMA is above the slow SMA."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..types import BarWindow


class MaCrossover:
    """Trend-following SMA crossover.

    Both averages are computed from the trailing window only, so the signal at
    bar t uses closes at or before t. `short_when_below` emits -1.0 instead of
    0.0 on a bearish cross, which the engine clamps to 0.0 unless the run is
    in perp mode with shorting enabled.
    """

    def __init__(
        self,
        fast: int = 20,
        slow: int = 50,
        short_when_below: bool = False,
    ) -> None:
        if fast < 1 or slow < 1:
            raise ValueError("SMA windows must be >= 1")
        if fast >= slow:
            raise ValueError(f"fast ({fast}) must be shorter than slow ({slow})")
        self.fast = fast
        self.slow = slow
        self.short_when_below = short_when_below
        self.name = f"ma_crossover_{fast}_{slow}"
        self.params: dict[str, Any] = {
            "fast": fast,
            "slow": slow,
            "short_when_below": short_when_below,
        }

    def warmup_bars(self) -> int:
        """Need `slow` closes before the slow average is defined."""
        return self.slow

    def on_bar(self, history: BarWindow) -> float:
        """Long while fast SMA > slow SMA."""
        closes = history.closes
        if len(closes) < self.slow:
            return 0.0
        fast_ma = float(np.mean(closes[-self.fast :]))
        slow_ma = float(np.mean(closes[-self.slow :]))
        if fast_ma > slow_ma:
            return 1.0
        return -1.0 if self.short_when_below else 0.0
