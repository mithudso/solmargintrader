"""Hourly backtest of range widths on a historical price path.

Model (deliberately simple and conservative):
  * Earnings while in range = yield_per_usd_day(half_width) * position value / 24 per hour, where
    the yield curve comes from today's on-chain pool economics (fee or AERO flow per unit liquidity).
  * Out of range earns nothing.
  * A rebalance re-centres the range at the current price and pays gas + swap fee + price impact on
    the share of value that must be swapped.
  * Position value follows exact concentrated-liquidity amounts (so impermanent loss is included).
It ignores changes in pool volume, emissions and competing liquidity over the window.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .strategy import StrategyConfig


@dataclass
class BacktestResult:
    label: str
    final_value: float
    earned: float
    costs: float
    rebalances: int
    hours_in_range: int
    hours: int
    hodl_value: float
    start_value: float = 0.0  # capital at the start; 0 = unknown (APR then falls back to hodl_value)

    @property
    def total(self) -> float:
        return self.final_value + self.earned

    @property
    def pnl_vs_hodl(self) -> float:
        return self.total - self.hodl_value

    @property
    def in_range_pct(self) -> float:
        return 100 * self.hours_in_range / max(1, self.hours)


def _amounts(liq: float, p: float, pa: float, pb: float) -> tuple[float, float]:
    sp = min(max(math.sqrt(p), math.sqrt(pa)), math.sqrt(pb))
    return liq * (1 / sp - 1 / math.sqrt(pb)), liq * (sp - math.sqrt(pa))


def _liq_for_value(value: float, p: float, pa: float, pb: float) -> float:
    a0, a1 = _amounts(1.0, p, pa, pb)
    per_unit = a0 * p + a1
    return value / per_unit if per_unit > 0 else 0.0


def run(
    prices: Sequence[float],
    half_width: float,
    yield_per_usd_day: Callable[[float], float],
    *,
    start_value: float = 10_000.0,
    gas_cost: float = 0.10,
    pool_fee: float = 0.0005,
    impact_bps: float = 5.0,
    cfg: StrategyConfig | None = None,
    label: str | None = None,
) -> BacktestResult:
    """Values are in token1 units (USD when token1 is a stablecoin)."""
    cfg = cfg or StrategyConfig()
    p0 = prices[0]
    pa, pb = p0 * math.exp(-half_width), p0 * math.exp(half_width)
    liq = _liq_for_value(start_value, p0, pa, pb)
    h0, h1 = _amounts(liq, p0, pa, pb)
    y = yield_per_usd_day(half_width)
    earned = costs = 0.0
    rebalances = in_range_hours = edge_hours = 0
    last_rb = -(10**9)
    cooldown_h = cfg.cooldown_minutes / 60
    for i, p in enumerate(prices[1:], start=1):
        a0, a1 = _amounts(liq, p, pa, pb)
        value = a0 * p + a1
        inside = pa <= p < pb
        if inside:
            in_range_hours += 1
            earned += y * value / 24
            u = math.log(p / pa) / math.log(pb / pa)
            edge_hours = edge_hours + 1 if (u < cfg.edge_buffer or u > 1 - cfg.edge_buffer) else 0
        trigger = (not inside) or (edge_hours >= cfg.confirm_checks)
        if trigger and i - last_rb >= cooldown_h:
            new_pa, new_pb = p * math.exp(-half_width), p * math.exp(half_width)
            u0, u1 = _amounts(1.0, p, new_pa, new_pb)
            t0 = u0 * p / (u0 * p + u1)
            have0 = a0 * p / value if value > 0 else 0.0
            swapped = abs(have0 - t0) * value
            cost = gas_cost + swapped * (pool_fee + impact_bps / 1e4)
            costs += cost
            value -= cost
            pa, pb = new_pa, new_pb
            liq = _liq_for_value(value, p, pa, pb)
            rebalances += 1
            last_rb = i
            edge_hours = 0
    p_end = prices[-1]
    a0, a1 = _amounts(liq, p_end, pa, pb)
    return BacktestResult(
        label=label or f"+/-{(math.exp(half_width) - 1) * 100:.1f}%",
        final_value=a0 * p_end + a1,
        earned=earned,
        costs=costs,
        rebalances=rebalances,
        hours_in_range=in_range_hours,
        hours=len(prices) - 1,
        hodl_value=h0 * p_end + h1,
        start_value=start_value,
    )


def format_table(results: list[BacktestResult], days: float) -> str:
    rows = [
        f"{'range':>10} {'in-range':>9} {'rebal':>6} {'earned':>11} {'costs':>9} {'final+earned':>13} "
        f"{'vs HODL':>10} {'net APR':>8}"
    ]
    for r in results:
        # Return on the capital put in, not on the end-of-window HODL value (which moves with the price).
        start = r.start_value or r.hodl_value or 1
        apr = (r.pnl_vs_hodl / start) * 365 / max(days, 1e-9) * 100
        rows.append(
            f"{r.label:>10} {r.in_range_pct:>8.1f}% {r.rebalances:>6} {r.earned:>11,.2f} {r.costs:>9,.2f} "
            f"{r.total:>13,.2f} {r.pnl_vs_hodl:>+10,.2f} {apr:>7.1f}%"
        )
    return "\n".join(rows)
