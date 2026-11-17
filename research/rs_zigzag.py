"""Research-only RS ZigZag signal model; no networking or trading.

The user-supplied legacy Pine source is not distributed here. The `legacy`
mode intentionally projects a completed hourly bar into its first child bar
and is unsuitable for live use. `confirmed` delays the hourly expression by
one complete hourly bar. Neither mode is certified TradingView parity.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float


def _validate(bars: Sequence[Bar], step: int) -> None:
    if step not in (600, 900):
        raise ValueError("step must be 600 or 900 seconds")
    for i, bar in enumerate(bars):
        values = (bar.open, bar.high, bar.low, bar.close)
        if (not isinstance(bar.timestamp, int) or bar.timestamp % step or
                any(not math.isfinite(v) or v <= 0 for v in values) or
                bar.low > min(bar.open, bar.close) or
                bar.high < max(bar.open, bar.close) or bar.low > bar.high):
            raise ValueError("invalid aligned OHLC bar")
        if i and bar.timestamp - bars[i - 1].timestamp != step:
            raise ValueError("bars must be contiguous; missing bars are not filled")


def _hourly(bars: Sequence[Bar], step: int) -> tuple[list[Bar], dict[int, int]]:
    groups: dict[int, list[Bar]] = {}
    for b in bars:
        groups.setdefault(b.timestamp // 3600 * 3600, []).append(b)
    hours, indices = [], {}
    for start, group in groups.items():
        # Partial leading/trailing hours are not treated as completed hours.
        if len(group) != 3600 // step or group[0].timestamp != start:
            continue
        indices[start] = len(hours)
        hours.append(Bar(start, group[0].open, max(b.high for b in group),
                         min(b.low for b in group), group[-1].close))
    return hours, indices


def _zigzags(hours: Sequence[Bar]) -> list[float | None]:
    values: list[float | None] = [None] * len(hours)
    direction = 0
    for i in range(1, len(hours)):
        prev, cur = hours[i - 1], hours[i]
        was_up, was_down = prev.close >= prev.open, prev.close <= prev.open
        is_up, is_down = cur.close >= cur.open, cur.close <= cur.open
        old_direction = direction
        if was_up and is_down:
            direction = -1
        elif was_down and is_up:
            direction = 1
        if was_up and is_down and old_direction != -1:
            values[i] = max(prev.high, cur.high)
        elif was_down and is_up and old_direction != 1:
            values[i] = min(prev.low, cur.low)
    return values


def pivot_events(bars: Sequence[Bar], step: int, mode: str = "confirmed") -> list[float | None]:
    """Map hourly pivot observations to hour-start child bars.

    `legacy` is deliberately noncausal; `confirmed` uses the prior completed
    hourly expression. Both require complete hourly input and omit an event if
    a required complete hour is unavailable. No data gaps are synthesized.
    """
    if mode not in ("legacy", "confirmed"):
        raise ValueError("mode must be legacy or confirmed")
    _validate(bars, step)
    hours, indices = _hourly(bars, step)
    values = _zigzags(hours)
    out: list[float | None] = [None] * len(bars)
    for i in range(1, len(bars)):
        ts = bars[i].timestamp
        if ts % 3600:
            continue
        # Pine's change(time(tf)) is evaluated at a new hour. In the causal
        # path, the immediately prior completed hour is required; in legacy,
        # the current completed hour is intentionally accessed prematurely.
        hour = ts if mode == "legacy" else ts - 3600
        index = indices.get(hour)
        if index is not None:
            out[i] = values[index]
    return out


def _patterns(x: float, a: float, b: float, c: float, d: float) -> bool:
    # Both source direction branches use the same ratio bounds; direction
    # itself is applied by the caller. A zero denominator makes its ratio
    # unavailable; patterns that do not use that ratio can still match.
    xab = abs(b-a)/abs(x-a) if x != a else math.nan
    xad = abs(a-d)/abs(x-a) if x != a else math.nan
    abc = abs(b-c)/abs(a-b) if a != b else math.nan
    bcd = abs(c-d)/abs(b-c) if b != c else math.nan
    inside = lambda v, lo, hi: lo <= v <= hi
    return any((
        inside(abc, .382, .886) and inside(bcd, 1.13, 2.618),
        inside(xab, .382, .5) and inside(abc, .382, .886) and inside(bcd, 1.618, 2.618) and xad <= .618,
        inside(xab, .5, .886) and inside(abc, 1, 2.618) and inside(bcd, 1.618, 2.618) and inside(xad, .886, 1),
        xab <= .382 and inside(abc, .382, .886) and inside(bcd, 2, 3.618) and xad <= 1.13,
        xab <= .786 and inside(abc, .382, .886) and inside(bcd, 1.618, 2.618) and inside(xad, 1.27, 1.618),
        inside(xab, .236, .886) and inside(abc, 1.13, 2.618) and inside(bcd, 1, 1.382) and inside(xad, .5, .886),
        inside(xab, .5, .618) and inside(abc, .382, .886) and inside(bcd, 1.13, 2.618) and inside(xad, .75, .875),
        inside(xab, .5, .886) and inside(abc, 1, 2.618) and inside(bcd, 1.5, 5) and inside(xad, 1, 5),
        inside(xab, .5, .875) and inside(abc, .382, .886) and inside(bcd, 2, 5) and inside(xad, 1.382, 5),
        inside(xab, .25, .5) and inside(abc, 1.13, 2.618) and inside(bcd, 1.618, 2.618) and inside(xad, .5, .75),
        inside(xab, .5, .875) and inside(abc, 1.13, 1.618) and inside(bcd, 1.27, 2.24) and inside(xad, .886, 1.13),
        inside(xab, .382, .875) and inside(abc, .5, 1) and inside(bcd, 1.25, 2.618) and inside(xad, .5, 1.25),
        inside(xab, 1.13, 1.618) and inside(abc, 1.618, 2.24) and inside(bcd, .5, .625) and inside(xad, 0, .236),
        inside(xab, 1.27, 1.618) and inside(abc, 0, 5) and inside(bcd, 1.27, 1.618) and inside(xad, 0, 5),
        inside(xab, 2, 10) and inside(abc, .9, 1.1) and inside(bcd, .236, .88) and inside(xad, .9, 1.1),
        inside(xab, .382, .618) and inside(abc, .382, .618) and inside(bcd, .382, .618) and inside(xad, .236, .764),
        inside(xab, 1.236, 1.618) and inside(abc, 1, 1.618) and inside(bcd, 1.236, 2) and inside(xad, 2, 2.236),
    ))


def signals(bars: Sequence[Bar], step: int, mode: str = "confirmed") -> list[dict[str, bool]]:
    """Source-level Target 1 decisions after each bar close; no fills."""
    events = pivot_events(bars, step, mode)
    history: list[float] = []
    result = []
    for bar, event in zip(bars, events):
        if event is not None:
            history.append(event)
        flags = {"buy_entry": False, "buy_close": False, "sell_entry": False, "sell_close": False}
        if len(history) >= 5:
            x, a, b, c, d = history[-5:]
            width = abs(d-c)
            sign = -1 if d > c else 1
            entry_level = d + sign*width*.236
            take_level = d + sign*width*.618
            stop_level = d - sign*width*.236
            pattern = _patterns(x, a, b, c, d)
            flags["buy_entry"] = pattern and d < c and bar.close <= entry_level
            flags["sell_entry"] = pattern and d > c and bar.close >= entry_level
            flags["buy_close"] = bar.high >= take_level or bar.low <= stop_level
            flags["sell_close"] = bar.low <= take_level or bar.high >= stop_level
        result.append(flags)
    return result


@dataclass(frozen=True)
class ExecutionAssumptions:
    """Explicit illustrative model; not TradingView or exchange fill parity."""
    initial_capital: float = 100_000.0
    quantity: float = 10_000.0
    fee_bps: float = 0.0
    slippage_bps: float = 0.0
    margin_fraction: float | None = None

    def __post_init__(self) -> None:
        if (not math.isfinite(self.initial_capital) or self.initial_capital <= 0 or
                not math.isfinite(self.quantity) or self.quantity <= 0 or
                not math.isfinite(self.fee_bps) or self.fee_bps < 0 or
                not math.isfinite(self.slippage_bps) or not 0 <= self.slippage_bps < 10_000):
            raise ValueError("invalid capital, quantity, fee or slippage")
        if self.margin_fraction is not None and (
                not math.isfinite(self.margin_fraction) or not 0 < self.margin_fraction <= 1):
            raise ValueError("margin_fraction must be in (0, 1] or None")


def simulate_decisions(bars: Sequence[Bar], step: int, decisions: Sequence[dict[str, bool]],
                       assumptions: ExecutionAssumptions) -> dict[str, object]:
    """Run a transparent next-open fixed-quantity sensitivity, not TV parity.

    Entries/close commands are processed in source order on the next open.
    Quantity assumes one price unit per contract; instrument multiplier and
    settlement currency are not modelled. Explicit quantity overrides any
    default. An opposite entry closes then
    reverses; repeated same-side entries are ignored. Fees apply to both legs.
    With a margin fraction, reject an entry if its required initial collateral
    exceeds cash after its entry fee. If worst-bar equity subsequently falls
    below that same fraction of worst-bar notional, liquidate at the adverse
    extreme; this conservative stress convention is not a venue liquidation
    rule. Funding and spread are not modelled. Final open exposure is marked,
    not closed, so terminal trade count excludes that open exposure.
    """
    _validate(bars, step)
    if len(bars) != len(decisions):
        raise ValueError("one decision record is required per bar")
    keys = ("buy_entry", "buy_close", "sell_entry", "sell_close")
    if any(set(d) != set(keys) or any(type(d[k]) is not bool for k in keys) for d in decisions):
        raise ValueError("decision record must contain four boolean fields")
    cash = assumptions.initial_capital
    signed_qty = 0.0
    entry = 0.0
    fees = 0.0
    closed = wins = rejected = liquidations = 0
    trade_start = cash
    equity_curve = []
    pending: dict[str, bool] | None = None
    slip, rate = assumptions.slippage_bps / 10_000, assumptions.fee_bps / 10_000

    def transact(direction: int, raw: float) -> None:
        nonlocal cash, signed_qty, entry, fees, closed, wins, rejected, trade_start
        price = raw * (1 + direction * slip)
        if signed_qty and (direction == 0 or math.copysign(1, signed_qty) != direction):
            closing_direction = -1 if signed_qty > 0 else 1
            price = raw * (1 + closing_direction * slip)
            charge = abs(signed_qty) * price * rate
            cash += signed_qty * (price - entry) - charge
            fees += charge
            closed += 1
            wins += int(cash > trade_start)
            signed_qty = 0.0
        if direction and not signed_qty:
            price = raw * (1 + direction * slip)
            charge = assumptions.quantity * price * rate
            margin = assumptions.margin_fraction
            if cash <= charge or (margin is not None and cash - charge < assumptions.quantity * price * margin):
                rejected += 1
                return
            trade_start = cash
            cash -= charge
            fees += charge
            signed_qty = direction * assumptions.quantity
            entry = price

    for i, bar in enumerate(bars):
        if pending is not None:
            flags = pending
            if flags["buy_entry"]:
                transact(1, bar.open)
            if flags["buy_close"] and signed_qty > 0:
                transact(0, bar.open)
            if flags["sell_entry"]:
                transact(-1, bar.open)
            if flags["sell_close"] and signed_qty < 0:
                transact(0, bar.open)
        if signed_qty and assumptions.margin_fraction is not None:
            worst = bar.low if signed_qty > 0 else bar.high
            worst_equity = cash + signed_qty * (worst - entry)
            required = abs(signed_qty) * worst * assumptions.margin_fraction
            if worst_equity < required:
                transact(0, worst)
                liquidations += 1
        equity_curve.append(cash + signed_qty * (bar.close - entry))
        # strategy.close() targets an already open entry at calculation time.
        pending = dict(decisions[i])
        pending["buy_close"] &= signed_qty > 0
        pending["sell_close"] &= signed_qty < 0
    final = equity_curve[-1] if equity_curve else assumptions.initial_capital
    return {"final_equity": final, "return_fraction": final / assumptions.initial_capital - 1,
            "closed_trades": closed, "winning_trades": wins, "rejected_entries": rejected,
            "liquidations": liquidations, "fees": fees, "open_quantity": signed_qty,
            "equity_curve": equity_curve,
            "model_limits": "next-open sensitivity; unit multiplier assumed 1; no funding/spread; margin stress is not venue parity"}
