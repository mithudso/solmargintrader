"""Shared Jupiter Perps assumptions and causal paper-trading controls.

The fee schedule is 6 bps on entry and exit, on notional. Borrow rates and
slippage are editable scenarios, not historical quotes. Coinbase supplies bars.
https://docs.jup.ag/user-docs/trade/perps/fees
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, asdict
from numbers import Real
from typing import Any, TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from .config import Settings
from backtester.core.types import BarWindow

from backtester.core import perps
from backtester.core.engine import EngineConfig
from backtester.core.types import CostConfig, Mode, Side, hours_per_bar

FIELDS = ("use_leverage", "leverage", "allow_short", "min_confidence",
          "borrow_long_bps_hour", "borrow_short_bps_hour")
MIN_CONFIDENCE_SAMPLES = 20
CONFIDENCE_WINDOW = 100


@dataclass(frozen=True)
class Execution:
    fee_schedule: str = "jupiter-perps"
    fee_bps: float = 6.0
    slippage_bps: float = 2.0
    use_leverage: bool = False
    leverage: float = 2.0
    allow_short: bool = False
    min_confidence: float = 0.80
    borrow_long_bps_hour: float = 0.8
    borrow_short_bps_hour: float = 0.15

    def __post_init__(self) -> None:
        if self.fee_schedule != "jupiter-perps":
            raise ValueError("fee_schedule must be jupiter-perps")
        for name in ("use_leverage", "allow_short"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        for name in ("fee_bps", "slippage_bps", "leverage", "min_confidence",
                     "borrow_long_bps_hour", "borrow_short_bps_hour"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if not 1 <= self.leverage <= 250:
            raise ValueError("leverage must be between 1 and 250")
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        if self.fee_bps >= 10000 or self.slippage_bps >= 10000:
            raise ValueError("fee_bps and slippage_bps must be below 10000")

    @property
    def effective_leverage(self) -> float:
        return self.leverage if self.use_leverage else 1.0

    @property
    def round_trip_bps(self) -> float:
        return 2 * (self.fee_bps + self.slippage_bps)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def costs(self) -> CostConfig:
        # These are explicit hourly scenario rates, not utilization ceilings.
        return CostConfig(fee_bps=self.fee_bps, perp_base_fee_bps=self.fee_bps,
                          slippage_bps=self.slippage_bps, utilization=1.0,
                          max_hourly_rate_bps_long=self.borrow_long_bps_hour,
                          max_hourly_rate_bps_short=self.borrow_short_bps_hour,
                          liquidation_forfeits_collateral=True)

    def engine(self, capital: float = 10000.0, interval: str = "1d", fill_delay: int = 1) -> EngineConfig:
        return EngineConfig(mode=Mode.PERP, leverage=self.effective_leverage,
                            allow_short=self.allow_short, initial_capital=capital,
                            interval=interval, fill_delay=fill_delay, costs=self.costs())

    def permits(self, direction: int, confidence: float | None) -> bool:
        return bool(direction and (direction > 0 or self.allow_short)
                    and (self.min_confidence == 0 or
                         (confidence is not None and confidence >= self.min_confidence)))


def from_settings(settings: Settings, overrides: dict[str, Any] | None = None) -> Execution:
    names = ("fee_schedule", "fee_bps", "slippage_bps", *FIELDS)
    values = {name: getattr(settings, name) for name in names}
    values.update(overrides or {})
    return Execution(**values)


def confidence_score(hits: int, count: int) -> float | None:
    """Beta(1,1) posterior mean after 20 resolved directional calls; not a guarantee."""
    return (hits + 1) / (count + 2) if count >= MIN_CONFIDENCE_SAMPLES else None


class ConfidenceGate:
    """Keep exposure separate from confidence; train only on resolved prior bars."""
    def __init__(self, strategy: Any, execution: Execution, interval: str = "1d", fill_delay: int = 1) -> None:
        self.strategy, self.execution = strategy, execution
        self.name, self.params = strategy.name, dict(strategy.params)
        self.delay = max(1, fill_delay)
        self.hours = hours_per_bar(interval)
        self.pending = deque()
        self.results = deque(maxlen=CONFIDENCE_WINDOW)
        self.confidence = None

    def warmup_bars(self) -> int:
        return self.strategy.warmup_bars()

    def on_bar(self, history: BarWindow) -> float:
        while self.pending and self.pending[0][0] <= history.i:
            index, direction = self.pending.popleft()
            ret = direction * (history.closes[index] / history.opens[index] - 1) * 10000
            rate = (self.execution.borrow_long_bps_hour if direction > 0
                    else self.execution.borrow_short_bps_hour)
            self.results.append(ret > self.execution.round_trip_bps + rate * self.hours)
        target = float(self.strategy.on_bar(history))
        if not math.isfinite(target):
            raise ValueError("strategy returned non-finite exposure")
        direction = (target > 0) - (target < 0)
        if direction:
            self.pending.append((history.i + self.delay, direction))
        self.confidence = confidence_score(sum(self.results), len(self.results))
        return target if self.execution.permits(direction, self.confidence) else 0.0


class DirectionalComposite:
    """Apply combination agreement to both directions when shorts are selected."""
    def __init__(self, strategy: Any) -> None:
        self.strategy = strategy
        self.members, self.mode = strategy.members, strategy.mode
        self.name, self.params = strategy.name, dict(strategy.params)

    def warmup_bars(self) -> int:
        return self.strategy.warmup_bars()

    def on_bar(self, history: BarWindow) -> float:
        values = [float(member.on_bar(history)) for member in self.members]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("combination member returned non-finite exposure")
        positive, negative = any(v > 0 for v in values), any(v < 0 for v in values)
        if self.mode == "all":
            if all(v > 0 for v in values):
                return min(values)
            return max(values) if all(v < 0 for v in values) else 0.0
        if self.mode == "any":
            if positive and negative:
                return 0.0
            return max(values) if positive else min(values)
        if self.mode == "vote":
            return sum((v > 0) - (v < 0) for v in values) / len(values)
        return sum(values) / len(values)


def prepare_strategy(strategy: Any, allow_short: bool) -> Any:
    """Enable a strategy's explicit bearish branch without treating FLAT as DOWN."""
    if allow_short and hasattr(strategy, "short_when_below"):
        strategy.short_when_below = True
        strategy.params = {**strategy.params, "short_when_below": True}
    if hasattr(strategy, "members"):
        strategy.members = [prepare_strategy(member, allow_short) for member in strategy.members]
        if allow_short:
            return DirectionalComposite(strategy)
    if hasattr(strategy, "_inner"):
        strategy._inner = prepare_strategy(strategy._inner, allow_short)
    return strategy


def gate(strategy: Any, settings: Settings, interval: str | None = None) -> ConfidenceGate:
    execution = from_settings(settings)
    return ConfidenceGate(prepare_strategy(strategy, execution.allow_short), execution,
                          interval or settings.interval, settings.fill_delay)


def settle(execution: Execution, direction: int,
           candles: Sequence[Sequence[float]]) -> dict[str, float | int]:
    """Return one fixed isolated position's net return, including intraminute liquidation.

    `candles` are ordered (open, high, low, close). Each window starts with one
    unit of equity. Fees use entry/exit notional; borrow uses entry notional.
    Liquidation forfeits collateral and does not re-enter during this call.
    """
    if direction not in (-1, 1) or not candles:
        raise ValueError("Settlement needs a direction and OHLC candles")
    for row in candles:
        if len(row) != 4 or any(not math.isfinite(v) or v <= 0 for v in row):
            raise ValueError("Settlement needs finite positive OHLC prices")
        op, high, low, close = row
        if high < max(op, close) or low > min(op, close) or low > high:
            raise ValueError("Invalid settlement OHLC range")
    costs = execution.costs()
    lev = execution.effective_leverage
    notional = 1 / (1 / lev + (execution.fee_bps + execution.slippage_bps) / 10000)
    collateral = notional / lev
    entry = candles[0][0]
    side = Side.LONG if direction > 0 else Side.SHORT
    borrow = 0.0
    entry_fee = notional * execution.fee_bps / 10000
    entry_slip = notional * execution.slippage_bps / 10000
    for op, high, low, close in candles:
        borrow += perps.accrue_borrow_fee(costs, side, notional, 1 / 60)
        liq = perps.liquidation_price(entry, side, collateral, notional, borrow, costs)
        if perps.is_liquidated(side, liq, low, high):
            price = min(op, liq.price) if direction > 0 else max(op, liq.price)
            exit_notional = notional * max(0, price) / entry
            fee = entry_fee + exit_notional * execution.fee_bps / 10000
            slip = entry_slip + exit_notional * execution.slippage_bps / 10000
            return {"net_return": -1.0, "fees_bps": fee * 10000,
                    "slippage_bps": slip * 10000, "borrow_bps": borrow * 10000,
                    "liquidated": 1}
    exit_notional = notional * close / entry
    fee = entry_fee + exit_notional * execution.fee_bps / 10000
    slip = entry_slip + exit_notional * execution.slippage_bps / 10000
    net = max(-1.0, direction * notional * (close / entry - 1) - fee - slip - borrow)
    return {"net_return": net, "fees_bps": fee * 10000, "slippage_bps": slip * 10000,
            "borrow_bps": borrow * 10000, "liquidated": 0}
