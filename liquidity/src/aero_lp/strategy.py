"""Range selection and the rebalance decision. Pure functions: no I/O, fully unit-tested.

Profit model
------------
A concentrated deposit earns only while price sits inside its range. Narrow ranges earn more
per dollar while in range but fall out sooner; each rebalance costs gas, a swap fee plus price
impact on roughly half the value, and (for AERO-earning deposits withdrawn inside the gauge's
minimum stake window) a forfeited share of unclaimed AERO. The bot therefore:

1. sizes the range from realized volatility: half-width (log-price) = k * sigma_daily * sqrt(horizon),
   clamped to [min, max] and snapped outward to the pool's tick spacing;
2. rebalances only when price has left the range, or has sat inside the edge buffer for
   `confirm_checks` consecutive checks, and the cooldown has passed;
3. requires expected extra earnings over the horizon to beat total cost by `benefit_cost_ratio`;
4. if the gauge penalty window is still open, waits when waiting is cheaper than the penalty.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from . import clmath
from .validation import finite_number


class Action(StrEnum):
    HOLD = "hold"
    REBALANCE = "rebalance"
    WAIT_PENALTY = "wait_penalty"
    WAIT_CONFIRM = "wait_confirm"
    WAIT_COOLDOWN = "wait_cooldown"
    SKIP_UNPROFITABLE = "skip_unprofitable"


@dataclass(frozen=True)
class StrategyConfig:
    width_mode: str = "optimal"  # "optimal" (yield - LVR - rebalance cost), "vol" (k*sigma*sqrt(h)), "fixed"
    fixed_half_width_pct: float = 8.0
    vol_k: float = 2.0
    horizon_days: float = 3.0
    min_half_width_pct: float = 0.05  # pegged pairs need a few-bp ranges; snapping to tick spacing widens it
    max_half_width_pct: float = 40.0
    edge_buffer: float = 0.10  # fraction of range (log space) treated as "about to exit"
    confirm_checks: int = 2
    cooldown_minutes: float = 60.0
    benefit_cost_ratio: float = 1.5
    max_slippage_bps: float = 50.0
    expected_price_impact_bps: float = 5.0
    # Weight on loss-versus-rebalancing in every profit estimate. 1.0 = honest expected-profit mode.
    # 0.0 = ignore LVR, i.e. "always get back in range" even when fees/AERO do not cover adverse selection.
    lvr_weight: float = 1.0

    def __post_init__(self) -> None:
        for name in (
            "fixed_half_width_pct", "vol_k", "horizon_days", "min_half_width_pct", "max_half_width_pct",
            "edge_buffer", "cooldown_minutes", "benefit_cost_ratio", "max_slippage_bps",
            "expected_price_impact_bps", "lvr_weight",
        ):
            finite_number(getattr(self, name), name, positive=name in (
                "fixed_half_width_pct", "vol_k", "horizon_days", "min_half_width_pct", "max_half_width_pct",
            ))
        finite_number(self.confirm_checks, "confirm_checks", positive=True, integer=True)
        if self.max_slippage_bps >= 10_000:
            raise ValueError("max_slippage_bps must be below 10000")
        if self.width_mode not in ("optimal", "vol", "fixed"):
            raise ValueError("width_mode must be 'optimal', 'vol' or 'fixed'")
        if self.lvr_weight < 0:
            raise ValueError("lvr_weight must be >= 0")
        if not 0 <= self.edge_buffer < 0.5:
            raise ValueError("edge_buffer must be in [0, 0.5)")
        if self.min_half_width_pct <= 0 or self.max_half_width_pct < self.min_half_width_pct:
            raise ValueError("bad half-width bounds")
        if self.fixed_half_width_pct <= 0 or self.vol_k <= 0:
            raise ValueError("fixed_half_width_pct and vol_k must be > 0")
        if self.horizon_days <= 0:  # in_range_probability divides by sqrt(t) at t = horizon/steps
            raise ValueError("horizon_days must be > 0")
        if self.cooldown_minutes < 0 or self.benefit_cost_ratio < 0 or self.expected_price_impact_bps < 0:
            raise ValueError("cooldown_minutes, benefit_cost_ratio and expected_price_impact_bps must be >= 0")


@dataclass(frozen=True)
class Range:
    tick_lower: int
    tick_upper: int

    def contains(self, tick: int) -> bool:
        # Slipstream/Uniswap v3: active iff tick_lower <= tick < tick_upper
        return self.tick_lower <= tick < self.tick_upper

    @property
    def width_ticks(self) -> int:
        return self.tick_upper - self.tick_lower


def half_width_log(cfg: StrategyConfig, sigma_daily: float | None) -> float:
    """Half-width of the target range in natural-log price units ("vol"/"fixed" modes, and the
    fallback for "optimal" when no yield curve is available)."""
    lo = math.log1p(cfg.min_half_width_pct / 100)
    hi = math.log1p(cfg.max_half_width_pct / 100)
    if cfg.width_mode == "fixed" or not sigma_daily or sigma_daily <= 0:
        w = math.log1p(cfg.fixed_half_width_pct / 100)
    else:
        w = cfg.vol_k * sigma_daily * math.sqrt(cfg.horizon_days)
    return min(max(w, lo), hi)


def lvr_fraction_per_day(half_width: float, sigma_daily: float | None) -> float:
    """Expected loss-versus-rebalancing per day as a fraction of position value, price at range centre.

    For concentrated liquidity L on [p*e^-w, p*e^w], LVR rate = sigma^2 * L * sqrt(P) / 4 and position
    value = 2 * L * sqrt(p) * (1 - e^(-w/2)), so LVR / value = sigma^2 / (8 * (1 - e^(-w/2))).
    Full range (w -> inf) gives the Uniswap-v2 result sigma^2 / 8.
    """
    if not sigma_daily or sigma_daily <= 0 or half_width <= 0:
        return 0.0
    return sigma_daily**2 / (8 * (1 - math.exp(-half_width / 2)))


def rebalances_per_day(half_width: float, sigma_daily: float | None) -> float:
    """Expected exits per day for driftless log-price starting at the centre: 1 / E[T] = sigma^2 / w^2."""
    if not sigma_daily or sigma_daily <= 0 or half_width <= 0:
        return 0.0
    return sigma_daily**2 / half_width**2


@dataclass(frozen=True)
class WidthScore:
    half_width: float
    yield_frac_day: float
    lvr_frac_day: float
    rebalance_cost_frac_day: float

    @property
    def net_frac_day(self) -> float:
        return self.yield_frac_day - self.lvr_frac_day - self.rebalance_cost_frac_day


def score_widths(
    yield_frac_day: Callable[[float], float],
    sigma_daily: float | None,
    cost_per_rebalance_frac: float,
    cfg: StrategyConfig,
    points: int = 60,
) -> list[WidthScore]:
    """Score a geometric grid of half-widths between the configured min and max.

    yield_frac_day(w): expected fee or AERO income per day per unit of position value while in range.
    cost_per_rebalance_frac: gas + swap fee + impact of one rebalance, as a fraction of position value.
    """
    lo = math.log1p(cfg.min_half_width_pct / 100)
    hi = math.log1p(cfg.max_half_width_pct / 100)
    out = []
    for i in range(points):
        w = lo * (hi / lo) ** (i / max(1, points - 1))
        out.append(
            WidthScore(
                w,
                yield_frac_day(w),
                cfg.lvr_weight * lvr_fraction_per_day(w, sigma_daily),
                rebalances_per_day(w, sigma_daily) * cost_per_rebalance_frac,
            )
        )
    return out


def best_width(scores: list[WidthScore]) -> WidthScore:
    return max(scores, key=lambda s: s.net_frac_day)


def target_range(tick_current: int, spacing: int, half_width: float, skew: float = 0.0) -> Range:
    """Range around the current tick, snapped outward to `spacing`.

    `skew` in [-1, 1] shifts the centre toward the expected drift direction (+ = token0 price up).
    Each side keeps at least one tick spacing.
    """
    skew = max(-1.0, min(1.0, skew))
    half_ticks = half_width / clmath.LOG_BASE
    centre = tick_current + skew * half_ticks * 0.5
    lower = clmath.floor_tick(centre - half_ticks, spacing)
    upper = clmath.ceil_tick(centre + half_ticks, spacing)
    lower = min(lower, clmath.floor_tick(tick_current, spacing))
    upper = max(upper, clmath.floor_tick(tick_current, spacing) + spacing)
    min_t, max_t = clmath.usable_tick_bounds(spacing)
    return Range(max(lower, min_t), min(upper, max_t))


def range_position(tick: float, rng: Range) -> float:
    """Where the price sits inside the range: 0 = lower edge, 1 = upper edge (can exceed [0,1])."""
    return (tick - rng.tick_lower) / max(1, rng.width_ticks)


def near_edge(tick: int, rng: Range, edge_buffer: float) -> bool:
    u = range_position(tick, rng)
    return u < edge_buffer or u > 1 - edge_buffer


@dataclass(frozen=True)
class CostInputs:
    value_usd: float  # current position value incl. uncollected fees
    pool_fee: float  # fraction, e.g. 0.0005
    gas_usd: float  # all txs of a rebalance (withdraw, swap, mint, stake)
    swap_fraction: float  # share of value that must be swapped (0..1)
    unclaimed_aero_usd: float = 0.0
    penalty_rate: float = 0.0  # fraction forfeited if exiting inside the window
    penalty_blocks_left: int = 0
    block_time_s: float = 2.0


@dataclass(frozen=True)
class EarnInputs:
    earn_usd_per_day_new: float  # expected earnings of the fresh range while in range
    earn_usd_per_day_current: float  # current deposit's earnings (0 when out of range)
    lvr_usd_per_day_new: float = 0.0  # expected adverse-selection cost of the fresh range while active
    lvr_usd_per_day_current: float = 0.0  # 0 when out of range (an idle deposit has no LVR)


@dataclass
class Decision:
    action: Action
    reason: str
    new_range: Range | None = None
    cost_usd: float = 0.0
    benefit_usd: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)


def rebalance_cost(c: CostInputs, cfg: StrategyConfig) -> dict[str, float]:
    swap_notional = c.value_usd * max(0.0, min(1.0, c.swap_fraction))
    in_window = c.penalty_blocks_left > 0
    return {
        "gas": c.gas_usd,
        "swap_fee": swap_notional * c.pool_fee,
        "price_impact": swap_notional * cfg.expected_price_impact_bps / 1e4,
        "penalty": c.unclaimed_aero_usd * c.penalty_rate if in_window else 0.0,
    }


def in_range_probability(half_width: float, sigma_daily: float | None, horizon_days: float) -> float:
    """Expected fraction of the horizon a fresh symmetric range stays active.

    Model: driftless Brownian log-price with daily vol `sigma_daily`. At time t the price is inside
    +/-half_width with probability P(|W_t| < a) = 1 - 2*(1 - Phi(a / (sigma*sqrt(t)))). The
    time-average of that probability over the horizon approximates occupancy. It ignores the fact
    that the bot re-centres after an exit, so it understates occupancy (conservative).
    """
    if not sigma_daily or sigma_daily <= 0:
        return 0.9
    steps = 24
    acc = 0.0
    for i in range(1, steps + 1):
        t = horizon_days * i / steps
        z = half_width / (sigma_daily * math.sqrt(t))
        tail = 0.5 * math.erfc(z / math.sqrt(2))
        acc += max(0.0, 1 - 2 * tail)  # P(|W_t| < a) at time t; time-average approximates occupancy
    return acc / steps


def decide(
    *,
    tick: int,
    current: Range,
    spacing: int,
    sigma_daily: float | None,
    cfg: StrategyConfig,
    cost: CostInputs,
    earn: EarnInputs,
    consecutive_edge_checks: int,
    minutes_since_last_rebalance: float | None,
    skew: float = 0.0,
    half_width: float | None = None,
) -> Decision:
    """`half_width`: target half-width chosen by the caller (e.g. the optimizer); default from cfg."""
    in_range = current.contains(tick)
    edge = in_range and near_edge(tick, current, cfg.edge_buffer)
    if in_range and not edge:
        return Decision(Action.HOLD, f"in range (pos {range_position(tick, current):.2f})")

    if minutes_since_last_rebalance is not None and minutes_since_last_rebalance < cfg.cooldown_minutes:
        return Decision(
            Action.WAIT_COOLDOWN,
            f"cooldown: {minutes_since_last_rebalance:.0f}/{cfg.cooldown_minutes:.0f} min since last rebalance",
        )

    if edge and consecutive_edge_checks + 1 < cfg.confirm_checks:
        return Decision(
            Action.WAIT_CONFIRM,
            f"near edge (pos {range_position(tick, current):.2f}); confirm "
            f"{consecutive_edge_checks + 1}/{cfg.confirm_checks}",
        )

    hw = half_width if half_width is not None else half_width_log(cfg, sigma_daily)
    new = target_range(tick, spacing, hw, skew)
    parts = rebalance_cost(cost, cfg)
    total_cost = sum(parts.values())

    occupancy = in_range_probability(hw, sigma_daily, cfg.horizon_days)
    net_new = earn.earn_usd_per_day_new - cfg.lvr_weight * earn.lvr_usd_per_day_new
    net_cur = earn.earn_usd_per_day_current - cfg.lvr_weight * earn.lvr_usd_per_day_current
    benefit = (net_new * occupancy - net_cur) * cfg.horizon_days
    breakdown = {**parts, "benefit": benefit, "occupancy": occupancy, "lvr_new_day": earn.lvr_usd_per_day_new}
    if net_new <= 0 and not in_range:
        return Decision(
            Action.SKIP_UNPROFITABLE,
            f"re-entering is expected to lose: income ${earn.earn_usd_per_day_new:.2f}/day < LVR "
            f"${earn.lvr_usd_per_day_new:.2f}/day at current volatility (set lvr_weight=0 to re-enter anyway)",
            new,
            total_cost,
            benefit,
            breakdown,
        )

    # Penalty window open: compare paying the penalty now with waiting it out.
    if parts["penalty"] > 0:
        wait_days = cost.penalty_blocks_left * cost.block_time_s / 86400
        cost_of_waiting = max(0.0, net_new * occupancy - net_cur) * wait_days
        if cost_of_waiting < parts["penalty"]:
            return Decision(
                Action.WAIT_PENALTY,
                f"gauge penalty ${parts['penalty']:.2f} > earnings lost waiting ${cost_of_waiting:.2f} "
                f"({cost.penalty_blocks_left} blocks)",
                new,
                total_cost,
                benefit,
                breakdown,
            )

    if benefit < total_cost * cfg.benefit_cost_ratio:
        return Decision(
            Action.SKIP_UNPROFITABLE,
            f"benefit ${benefit:.2f} < {cfg.benefit_cost_ratio}x cost ${total_cost:.2f}",
            new,
            total_cost,
            benefit,
            breakdown,
        )

    why = "out of range" if not in_range else f"edge confirmed ({consecutive_edge_checks + 1} checks)"
    return Decision(
        Action.REBALANCE,
        f"{why}; benefit ${benefit:.2f} vs cost ${total_cost:.2f}",
        new,
        total_cost,
        benefit,
        breakdown,
    )
