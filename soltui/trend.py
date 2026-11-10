"""Long-only moving-average momentum for the paper Bots workbench.

Decisions use completed closes. The shared engine fills at the next open, charges
fees and slippage, and liquidates at the sample's final close for comparison.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from typing import Any

import numpy as np

from backtester.core.engine import BacktestResult, EngineConfig, run_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.types import BarWindow, CostConfig


@dataclass(frozen=True)
class TrendConfig:
    fast_period: int = 10
    slow_period: int = 30
    entry_buffer_bps: float = 10.0
    capital_usd: float = 1000.0

    def __post_init__(self) -> None:
        for key in ("fast_period", "slow_period"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        for key in ("entry_buffer_bps", "capital_usd"):
            value = getattr(self, key)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(value)
            ):
                raise ValueError(f"{key} must be finite")
        if not 0 <= self.entry_buffer_bps < 10000:
            raise ValueError("entry_buffer_bps must be between 0 and 10000 (exclusive)")
        if self.capital_usd <= 0:
            raise ValueError("capital_usd must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TrendFollowing:
    """Enter above a buffered SMA crossover; hold until fast SMA <= slow SMA."""

    def __init__(self, config: TrendConfig) -> None:
        self.config = config
        self.name = "trend_bot"
        self.params = config.to_dict()
        self.holding = False

    def checkpoint_state(self) -> dict:
        return {"schema_version": 1, "holding": self.holding}

    def restore_state(self, state: dict) -> None:
        if state.get("schema_version") != 1 or type(state.get("holding")) is not bool:
            raise ValueError("unsupported trend continuation state")
        self.holding = state["holding"]

    def warmup_bars(self) -> int:
        return self.config.slow_period - 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        if closes.size < self.config.slow_period:
            return 0.0
        fast = float(np.mean(closes[-self.config.fast_period :]))
        slow = float(np.mean(closes[-self.config.slow_period :]))
        if fast <= slow:
            self.holding = False
        elif fast > slow * (1 + self.config.entry_buffer_bps / 10000):
            self.holding = True
        return float(self.holding)


def run_trend_backtest(
    config: TrendConfig,
    arrays: dict[str, np.ndarray],
    *,
    interval: str,
    costs: CostConfig,
    close_at_end: bool = True,
) -> tuple[BacktestResult, BacktestResult]:
    if close_at_end and len(arrays["close"]) <= config.slow_period:
        raise ValueError(
            f"Trend needs at least {config.slow_period + 1} completed bars for warmup and a next-open fill"
        )
    execution = EngineConfig(
        initial_capital=config.capital_usd, interval=interval, fill_delay=1, costs=costs
    )
    # Bot OHLC slices omit traded volume, including quote-derived forward bars.
    # Neither this price-only signal nor the shared fill model uses volume.
    result = run_backtest(
        TrendFollowing(config),
        arrays,
        execution,
        close_at_end=close_at_end,
        price_only=True,
    )
    hold = run_backtest(
        BuyAndHold(), arrays, execution, close_at_end=close_at_end, price_only=True
    )
    return result, hold
