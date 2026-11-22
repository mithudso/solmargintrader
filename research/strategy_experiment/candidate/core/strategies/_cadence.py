"""Annualization from visible bars; never assume that one bar is one day."""
from __future__ import annotations

import numpy as np

from ..types import BarWindow


def observed_periods_per_year(history: BarWindow) -> float:
    timestamps = history.ts
    if len(timestamps) < 2:
        raise ValueError("volatility sizing requires at least two timestamps")
    steps = np.diff(timestamps)
    if not np.all(np.isfinite(steps)) or steps[-1] <= 0 or not np.all(steps == steps[-1]):
        raise ValueError("volatility sizing requires a positive regular bar cadence")
    return float(365 * 86400 / steps[-1])
