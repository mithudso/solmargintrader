"""Jupiter-Perps-style borrow fees, margin, and liquidation.

The one thing to get right about this venue: it charges a **borrow fee**, not
a funding rate. Consequences encoded here:

  * Longs and shorts BOTH pay. There is no long-pays-short transfer.
  * The rate is a product of two non-negative quantities, so it is
    floor-bounded at zero. No position is ever paid to stay open.
  * The fee accrues on NOTIONAL, not on collateral and not on units.
  * Accrual is an index difference times notional -- additive, not fee-on-fee.

Rates are configured in basis points per hour. 1.6 bps/hr == 0.016%/hr, the
documented SOL reference point (~140% APR); stablecoin custody is far cheaper
(~0.3 bps/hr), which is why longs and shorts take separate rates.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import CostConfig, Side


@dataclass
class LiquidationInfo:
    """Liquidation price and whether the published formula is in its domain."""

    price: float
    buffer_fraction: float
    in_domain: bool
    below_maintenance: bool


def hourly_borrow_rate(costs: CostConfig, side: Side, utilization: float) -> float:
    """Borrow rate per hour as a decimal fraction of notional.

    Flat-linear published model: `rate = max_rate * utilization`.

    Governance separately proposed a dual-slope ("jump rate") curve with a
    kink and a minimum rate floor, which is mathematically incompatible with
    the flat-linear formula at low utilization. Which is live cannot be
    settled from documentation, so both are available: `kink_utilization`
    enables the second slope and `min_hourly_rate_bps` applies the floor.
    Defaults reproduce the published flat-linear behaviour exactly.

    Always returns a non-negative value.
    """
    if not 0.0 <= utilization <= 1.0:
        raise ValueError(f"utilization must be in [0, 1], got {utilization}")

    max_bps = (
        costs.max_hourly_rate_bps_long
        if side is Side.LONG
        else costs.max_hourly_rate_bps_short
    )
    if max_bps < 0:
        raise ValueError("max hourly borrow rate cannot be negative")

    base = max_bps / 10_000.0  # bps -> fraction

    kink = costs.kink_utilization
    if kink is not None and utilization > kink:
        rate = base * kink + base * (utilization - kink) * costs.kink_slope_multiplier
    else:
        rate = base * utilization

    rate = max(rate, costs.min_hourly_rate_bps / 10_000.0)
    # Structural guarantee, restated defensively: never negative.
    return max(rate, 0.0)


def accrue_borrow_fee(
    costs: CostConfig,
    side: Side,
    notional: float,
    hours: float,
    utilization: float | None = None,
) -> float:
    """Borrow fee owed for holding `notional` for `hours`.

    Linear in time and in notional: this models a cumulative-index difference
    times a fixed notional, which is additive rather than fee-on-fee. What a
    trader experiences as compounding is second-order -- fees erode collateral,
    effective leverage rises, and the liquidation price drifts toward spot.
    That effect is captured in `liquidation_price`, not here.
    """
    if hours < 0:
        raise ValueError("hours cannot be negative")
    if notional < 0:
        raise ValueError("notional cannot be negative")
    u = costs.utilization if utilization is None else utilization
    rate = hourly_borrow_rate(costs, side, u)
    return rate * notional * hours


def liquidation_price(
    entry_price: float,
    side: Side,
    collateral: float,
    notional: float,
    accrued_borrow_fee: float,
    costs: CostConfig,
) -> LiquidationInfo:
    """Liquidation price for an open position.

    Published venue formula:

        Liq (Long)  = entry - (|collateral - close_fee - borrow_fee - size/max_lev| * entry) / size
        Liq (Short) = entry + (|collateral - close_fee - borrow_fee - size/max_lev| * entry) / size

    where `max_lev` is a protocol constant of 500, making maintenance margin
    0.2% of notional -- distinct from the user-facing leverage cap.

    Equivalently, the buffer as a fraction of entry price is:

        buffer = collateral/size - f_close - 0.002 - borrow_fee/size

    Because accrued borrow fees appear in that expression, the liquidation
    price DRIFTS toward spot the longer a position is held. Recompute it every
    bar rather than fixing it at entry.

    Domain caveat: the absolute-value bars in the published formula are only
    valid while the bracketed term is positive. Once collateral falls below
    maintenance the sign flips and `abs()` would push a long's liquidation
    price *below* entry, which is nonsense. That case is reported via
    `in_domain=False` and `below_maintenance=True` instead of being propagated
    as a plausible-looking price.
    """
    if notional <= 0:
        return LiquidationInfo(0.0, 0.0, in_domain=False, below_maintenance=True)

    close_fee = notional * (costs.perp_base_fee_bps / 10_000.0)
    maintenance = notional * costs.maintenance_margin_fraction
    bracket = collateral - close_fee - accrued_borrow_fee - maintenance
    buffer_fraction = bracket / notional

    if bracket <= 0:
        # Already at or past maintenance: liquidatable at the current price.
        return LiquidationInfo(
            price=entry_price,
            buffer_fraction=buffer_fraction,
            in_domain=False,
            below_maintenance=True,
        )

    if side is Side.LONG:
        price = entry_price * (1.0 - buffer_fraction)
    else:
        price = entry_price * (1.0 + buffer_fraction)

    return LiquidationInfo(
        price=price,
        buffer_fraction=buffer_fraction,
        in_domain=True,
        below_maintenance=False,
    )


def is_liquidated(
    side: Side, liq: LiquidationInfo, bar_low: float, bar_high: float
) -> bool:
    """Whether the bar's range touched the liquidation price.

    Uses the intrabar low for longs and high for shorts: a wick through the
    liquidation level closes the position even if the bar closes back above
    it. Ignoring the wick would systematically understate liquidations.
    """
    if liq.below_maintenance:
        return True
    if side is Side.LONG:
        return bar_low <= liq.price
    if side is Side.SHORT:
        return bar_high >= liq.price
    return False


def required_collateral(notional: float, leverage: float) -> float:
    """Collateral needed to open `notional` at `leverage`."""
    if leverage <= 0:
        raise ValueError("leverage must be positive")
    return notional / leverage
