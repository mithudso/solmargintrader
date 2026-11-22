"""Low / medium / high margin tiers: run any long/flat strategy as a perp position.

A tier is only a leverage multiple plus the venue's cost model. The wrapped
strategy decides WHEN to hold exposure; the engine decides what holding it costs
at leverage L: open/close fees, slippage, the hourly borrow fee on notional,
maintenance margin, and liquidation with an adverse fill and forfeited collateral.

Defaults are 2x / 5x / 20x and are configurable. Nothing here touches the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .engine import EngineConfig
from .types import CostConfig, IntrabarLayer, Mode

# Forced-close slippage on top of the liquidation level. 50 bps is an assumption,
# not a venue constant; `--penalty-bps` style overrides exist because the true
# value depends on keeper latency and book depth that public data cannot show.
DEFAULT_LIQUIDATION_PENALTY_BPS = 50.0


@dataclass(frozen=True)
class LeverageTier:
    """A named leverage multiple."""

    name: str
    leverage: float


DEFAULT_TIERS: tuple[LeverageTier, ...] = (
    LeverageTier("low", 2.0),
    LeverageTier("medium", 5.0),
    LeverageTier("high", 20.0),
)


def tier_costs(base: CostConfig | None = None,
               penalty_bps: float = DEFAULT_LIQUIDATION_PENALTY_BPS) -> CostConfig:
    """Cost model for tier runs: the repo defaults plus a liquidation penalty."""
    c = base or CostConfig()
    return CostConfig(
        fee_bps=c.fee_bps, slippage_bps=c.slippage_bps,
        perp_base_fee_bps=c.perp_base_fee_bps,
        max_hourly_rate_bps_long=c.max_hourly_rate_bps_long,
        max_hourly_rate_bps_short=c.max_hourly_rate_bps_short,
        utilization=c.utilization, min_hourly_rate_bps=c.min_hourly_rate_bps,
        kink_utilization=c.kink_utilization,
        kink_slope_multiplier=c.kink_slope_multiplier,
        max_lev_constant=c.max_lev_constant,
        liquidation_penalty_bps=penalty_bps,
        liquidation_forfeits_collateral=True,
    )


def tier_config(leverage: float, interval: str, *, initial_capital: float = 10_000.0,
                intrabar: Sequence[IntrabarLayer] = (), allow_short: bool = False,
                costs: CostConfig | None = None, fill_delay: int = 1) -> EngineConfig:
    """EngineConfig that runs a strategy as a Jupiter-Perps position at `leverage`."""
    return EngineConfig(
        mode=Mode.PERP, leverage=float(leverage), interval=interval,
        initial_capital=initial_capital, fill_delay=fill_delay,
        costs=costs or tier_costs(), allow_short=allow_short,
        intrabar=tuple(intrabar),
    )


def resolve_tiers(spec: str | None) -> tuple[LeverageTier, ...]:
    """Parse '2,5,20' into low/medium/high; empty means the defaults."""
    if not spec:
        return DEFAULT_TIERS
    vals = [float(x) for x in spec.split(",")]
    if len(vals) != 3 or any(v <= 1.0 for v in vals) or sorted(vals) != vals:
        raise ValueError("tiers must be three ascending leverages above 1, e.g. 2,5,20")
    return tuple(LeverageTier(n, v) for n, v in zip(("low", "medium", "high"), vals))


def liquidation_distance(leverage: float, costs: CostConfig | None = None) -> float:
    """Adverse move (fraction) that triggers liquidation at entry, before carry."""
    c = costs or CostConfig()
    return max(0.0, 1.0 / leverage - c.perp_base_fee_bps / 10_000.0 - c.maintenance_margin_fraction)


def describe(strategy: Any) -> dict[str, Any]:
    """Params of a tier strategy, for reports."""
    return dict(getattr(strategy, "params", {}))
