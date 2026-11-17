"""RSI mean-reversion: buy oversold, exit on reversion to the midline."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..types import BarWindow


def _averages(closes: np.ndarray, period: int) -> tuple[float, float]:
    deltas = np.diff(closes)
    gains = np.maximum(deltas, 0.0)
    losses = np.maximum(-deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for k in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[k]) / period
        avg_loss = (avg_loss * (period - 1) + losses[k]) / period
    return avg_gain, avg_loss


def _value(avg_gain, avg_loss):
    if avg_loss <= 1e-15:
        return 100.0 if avg_gain > 0 else 50.0
    return float(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)))


def wilder_rsi(closes: np.ndarray, period: int) -> float:
    """Wilder's RSI over the trailing window, returned for the latest bar.

    Uses Wilder's smoothing (an EMA with alpha = 1/period) seeded by the
    simple average of the first `period` changes, which is the standard
    definition. Returns 50.0 (neutral) when there is not enough history.
    """
    if len(closes) < period + 1:
        return 50.0
    return _value(*_averages(closes, period))


class RsiMeanReversion:
    """Enter long below `oversold`, exit above `exit_level`, else hold.

    Holding requires state, which is legitimate: the state is derived only
    from past decisions and past bars, never from future prices.
    """

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        exit_level: float = 50.0,
    ) -> None:
        if period < 2:
            raise ValueError("RSI period must be >= 2")
        if not 0 < oversold < exit_level <= 100:
            raise ValueError("require 0 < oversold < exit_level <= 100")
        self.period = period
        self.oversold = oversold
        self.exit_level = exit_level
        self._holding = False
        self._cursor = None
        self._gain = self._loss = 0.0
        self.name = f"rsi_{period}_{int(oversold)}_{int(exit_level)}"
        self.params: dict[str, Any] = {
            "period": period,
            "oversold": oversold,
            "exit_level": exit_level,
        }

    def warmup_bars(self) -> int:
        """One extra bar because RSI is computed on differences."""
        return self.period + 1

    def on_bar(self, history: BarWindow) -> float:
        """Long when oversold; flat once RSI recovers past the exit level."""
        current = history.bar()
        if len(history) < self.period + 1:
            rsi = 50.0
        else:
            previous = history.bar(1)
            if self._cursor == (history.i - 1, previous.ts, previous.close):
                delta = current.close - previous.close
                self._gain = (self._gain * (self.period - 1) + max(delta, 0.0)) / self.period
                self._loss = (self._loss * (self.period - 1) + max(-delta, 0.0)) / self.period
            else:
                self._gain, self._loss = _averages(history.closes, self.period)
            self._cursor = (history.i, current.ts, current.close)
            rsi = _value(self._gain, self._loss)
        if not self._holding and rsi < self.oversold:
            self._holding = True
        elif self._holding and rsi > self.exit_level:
            self._holding = False
        return 1.0 if self._holding else 0.0
