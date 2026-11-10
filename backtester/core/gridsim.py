"""Resting-ladder grid simulator — the strategy the extension actually trades.

This is deliberately NOT a `Strategy` in the `core.engine` sense. That protocol
maps history to one target exposure filled at a bar boundary, and a grid's entire
edge comes from **resting limit orders that fill intrabar at known prices**. An
exposure staircase (see `strategies.signals.GridLong`) can imitate a grid's
*position profile* but not its economics: it never captures a rung width, because
it never has an order sitting at a level waiting to be hit.

So this module owns its own bar loop, and mirrors `extension/src/core/grid.js`
level-for-level. Divergence between the two would be worse than having no grid
backtest at all — a confident wrong number about the strategy running live.

Bar ordering, which is the whole correctness story:

    1. accrue carry on inventory held into this bar
    2. fill resting BUYS  against this bar's low
    3. fill resting SELLS against this bar's high
    4. mark to market at this bar's close
    5. re-plan the ladder from the close (orders become fillable NEXT bar)

Three conventions make this pessimistic rather than flattering, which is the
point — an optimistic grid simulator makes a losing grid look profitable:

* **An order cannot fill on the bar that planned it.** Planning happens at step
  5 from the close of bar *i*; the earliest fill is step 2/3 of bar *i+1*. This
  is the structural no-lookahead guard, and it also makes a same-bar round trip
  impossible. Same-bar buy-then-sell is the classic grid-backtest lie: within one
  bar we know only OHLC, not the path, so "price dipped to the bid then rallied
  to the offer" is an assumption, not an observation.
* **Fills are adverse.** A buy fills at its level moved *up* by the full slippage
  allowance and a sell at its level moved *down* by it, matching the extension's
  dry-run convention.
* **Buys are processed before sells.** Cash freed by a sell therefore cannot fund
  a buy in the same bar. Where the intrabar path is unknown, spend first.

One more convention worth stating, because it changes *attribution* rather than
totals: when a single bar sweeps through several bids they fill **highest level
first**, since a falling price reaches the higher rung earlier. That ordering
sets lot age, and lot age is what the FIFO fallback consumes (paired exits close
their own lots first). Portfolio totals do not depend on it.

Costs are never optional here (see the backtester's non-negotiables): the taker
fee, the slippage allowance and an explicit carry rate all stay in the P&L path.
Carry defaults to zero because Trigger V2 is a **spot** venue with no borrow —
not because carry is free. Pass `carry_bps_per_hour` to model a borrowed-margin
grid, and the number will be labelled in the result.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any

import numpy as np

from .metrics import Metrics, compute_metrics
from .types import (
    INTERVAL_SECONDS,
    CostConfig,
    Trade,
    hours_per_bar,
    periods_per_year,
    validate_bar_arrays,
)

SPACING_GEOM = "geom"
SPACING_ARITH = "arith"
SPACINGS = (SPACING_GEOM, SPACING_ARITH)

SIDE_BUY = "buy"
SIDE_SELL = "sell"

# Jupiter Trigger V2's hard floor. A rung below it is not a small order, it is a
# rejected one, so the planner has to know the number.
VENUE_MIN_ORDER_USD = 10.0
MAX_GRID_RUNGS = 10_000


def _validate_rung_count(rungs: int) -> None:
    if not isinstance(rungs, int) or not 2 <= rungs <= MAX_GRID_RUNGS:
        raise ValueError(f"rungs must be an integer in [2, {MAX_GRID_RUNGS}]")


@dataclass(frozen=True)
class GridConfig:
    """One grid ladder. Field names and defaults mirror the extension's config."""

    lower: float
    upper: float
    rungs: int
    notional_per_rung_usd: float
    spacing: str = SPACING_GEOM
    deadband_bps: float = 25.0
    min_order_usd: float = VENUE_MIN_ORDER_USD

    def __post_init__(self) -> None:
        """Reject a ladder that cannot be built, with the offending value named."""
        for name in ("lower", "upper", "notional_per_rung_usd", "deadband_bps", "min_order_usd"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not self.lower > 0:
            raise ValueError(f"lower must be > 0, got {self.lower}")
        if not self.upper > self.lower:
            raise ValueError(f"upper ({self.upper}) must exceed lower ({self.lower})")
        _validate_rung_count(self.rungs)
        if not self.notional_per_rung_usd > 0:
            raise ValueError(
                f"notional_per_rung_usd must be > 0, got {self.notional_per_rung_usd}"
            )
        if self.spacing not in SPACINGS:
            raise ValueError(f"unknown spacing {self.spacing!r}; expected one of {SPACINGS}")
        if self.deadband_bps < 0:
            raise ValueError("deadband_bps cannot be negative")
        if self.min_order_usd < 0:
            raise ValueError("min_order_usd cannot be negative")

        # Check actual identities: rounding the minimum gap can miss two
        # distinct levels that fall into the same quantization interval.
        levels = grid_levels(self)
        keys = [_level_key(SIDE_BUY, level) for level in levels]
        if len(set(keys)) != len(levels):
            raise ValueError("distinct rungs collide at the 1e-6 resolution of an order key")

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict form for the run manifest."""
        return {
            "lower": self.lower,
            "upper": self.upper,
            "rungs": self.rungs,
            "notional_per_rung_usd": self.notional_per_rung_usd,
            "spacing": self.spacing,
            "deadband_bps": self.deadband_bps,
            "min_order_usd": self.min_order_usd,
        }


# -- ladder geometry ------------------------------------------------------
# Ports of gridLevels / rungWidthBps / nearestLevelIndex / pairedExitLevel /
# sideForLevel / expectedRoundTripUsd from extension/src/core/grid.js.


def grid_levels(cfg: GridConfig) -> list[float]:
    """Ladder prices, lowest first.

    Geometric spacing gives every rung the same percentage width, which is what
    a percentage-moving asset wants; arithmetic gives every rung the same dollar
    width. Endpoints are pinned because float drift otherwise leaves the top rung
    a hair off `upper`, which reads as a phantom level change every re-plan.
    """
    _validate_rung_count(cfg.rungs)
    levels: list[float] = []
    if cfg.spacing == SPACING_ARITH:
        step = (cfg.upper - cfg.lower) / (cfg.rungs - 1)
        levels = [cfg.lower + i * step for i in range(cfg.rungs)]
    else:
        ratio = (cfg.upper / cfg.lower) ** (1.0 / (cfg.rungs - 1))
        levels = [cfg.lower * ratio**i for i in range(cfg.rungs)]
    levels[0] = cfg.lower
    levels[-1] = cfg.upper
    return levels


def rung_width_bps(cfg: GridConfig) -> float:
    """Mean percentage width between adjacent rungs — the gross edge per trip."""
    levels = grid_levels(cfg)
    widths = [(levels[i] / levels[i - 1] - 1.0) * 10_000.0 for i in range(1, len(levels))]
    return float(sum(widths) / len(widths))


def nearest_level_index(levels: Sequence[float], price: float) -> int:
    """Index of the ladder level closest to `price`."""
    best, best_dist = 0, float("inf")
    for i, level in enumerate(levels):
        dist = abs(level - price)
        if dist < best_dist:
            best, best_dist = i, dist
    return best


def paired_exit_level(levels: Sequence[float], entry_price: float) -> float:
    """Where the exit for a lot bought at `entry_price` belongs: one rung up.

    This is the economic engine of a grid. Offering at the level just bought
    captures nothing and pays two fees; the exit has to sit at the next level so
    the captured spread equals the rung width. A lot bought on the top rung has
    no rung above it, so extrapolate one more step at the same ratio rather than
    selling flat.
    """
    idx = nearest_level_index(levels, entry_price)
    if idx < len(levels) - 1:
        return levels[idx + 1]
    ratio = levels[-1] / levels[-2]
    return levels[-1] * ratio


def side_for_level(level: float, price: float, deadband_bps: float = 25.0) -> str | None:
    """Which side a level would rest on in isolation; `None` inside the deadband.

    Entries only. Exits come from open lots via `paired_exit_level`, never from a
    level's position relative to the market — that mix-up is what produced the
    zero-spread-exit bug the extension documents.
    """
    band = price * deadband_bps / 10_000.0
    if level < price - band:
        return SIDE_BUY
    if level > price + band:
        return SIDE_SELL
    return None


def expected_round_trip_usd(cfg: GridConfig, level: float) -> float:
    """Gross spread one round trip captures at `level`, before costs."""
    levels = grid_levels(cfg)
    exit_level = paired_exit_level(levels, level)
    base_qty = cfg.notional_per_rung_usd / level
    return base_qty * (exit_level - level)


def capital_requirement(cfg: GridConfig, price: float) -> dict[str, float]:
    """Quote capital the ladder needs before it can run.

    Only bids need funding: each becomes the inventory backing its own paired
    exit, so no base balance is required to start.
    """
    levels = grid_levels(cfg)
    quote_usd = 0.0
    base_qty = 0.0
    for level in levels:
        if side_for_level(level, price, cfg.deadband_bps) != SIDE_BUY:
            continue
        if cfg.notional_per_rung_usd < cfg.min_order_usd:
            continue
        quote_usd += cfg.notional_per_rung_usd
        base_qty += cfg.notional_per_rung_usd / level
    return {
        "quote_usd": quote_usd,
        "base_qty": base_qty,
        "base_value_usd": base_qty * price,
        "total_usd": quote_usd,
    }


def _level_key(side: str, level: float) -> str:
    """Restart-stable order identity, mirroring the extension's `intentKey`."""
    scaled = level * 1e6
    if not math.isfinite(scaled):
        raise ValueError("order key requires a finite scaled level")
    integer = math.floor(scaled)
    # Python round uses ties-to-even; JavaScript Math.round rounds positive
    # halves upward. Avoid adding 0.5, which can itself round near a boundary.
    rounded = integer + (scaled - integer >= 0.5)
    return f"{side}:{rounded}"


# -- book -----------------------------------------------------------------


@dataclass
class Lot:
    """One open buy lot.

    Entry fee and entry slippage both ride on the lot, so a partial close
    realizes only their proportional share — the rule
    `extension/src/core/pnl.js` uses for fees.

    `price` is what was actually paid (the level plus the adverse slippage);
    `level` is the rung it was bought at. Both are needed: `price` is the real
    cash outlay, while `level` is what the *rung spread* is measured between. Using
    `price` for the spread would net slippage inside the gross figure and then net
    it again as an explicit cost.
    """

    qty: float
    price: float
    level: float
    entry_fee_usd: float
    entry_slippage_usd: float
    opened_index: int
    opened_ts: int
    accrued_carry_usd: float = 0.0


@dataclass
class RestingOrder:
    """An order sitting on the venue, planned at `planned_index`."""

    side: str
    level: float
    qty: float
    notional_usd: float
    planned_index: int
    # Exits only: the (lot rung level, qty) pairs this order was planned to close.
    # Port of `lots` on the extension's exit intents / `closesLots` on its fills.
    # Realization closes these lots first, then falls back to FIFO.
    closes: tuple[tuple[float, float], ...] = ()


@dataclass
class GridRunResult:
    """Everything one ladder run produced."""

    config: dict[str, Any]
    metrics: Metrics
    baseline_metrics: Metrics
    timestamps: np.ndarray
    equity: np.ndarray
    exposure: np.ndarray
    baseline_equity: np.ndarray
    trades: list[Trade]
    rung_width_bps: float
    capital_required_usd: float
    round_trips: int
    gross_captured_usd: float
    realized_pnl_usd: float
    fees_paid_usd: float
    slippage_paid_usd: float
    carry_paid_usd: float
    carry_bps_per_hour: float
    buys_filled: int
    sells_filled: int
    orders_placed: int
    orders_cancelled: int
    open_lots_at_end: list[Lot]
    unmatched_inventory_qty: float
    forced_exit_qty: float
    bars_above_grid: int
    bars_below_grid: int
    skipped: dict[str, int]
    continuation: dict | None = None

    def summary_lines(self) -> list[str]:
        """Human-readable digest. Kept here so the CLI stays a thin adapter."""
        m, b = self.metrics, self.baseline_metrics
        return [
            f"rung width           {self.rung_width_bps:,.1f} bps",
            f"capital required     ${self.capital_required_usd:,.2f}",
            f"round trips          {self.round_trips}",
            f"gross captured       ${self.gross_captured_usd:,.2f}",
            (f"fees + slippage      ${self.fees_paid_usd + self.slippage_paid_usd:,.2f}"
            f"  (fees ${self.fees_paid_usd:,.2f}, slippage ${self.slippage_paid_usd:,.2f})"),
            (f"carry                ${self.carry_paid_usd:,.2f}"
            f"  ({self.carry_bps_per_hour:g} bps/hr on inventory)"),
            f"realized P&L         ${self.realized_pnl_usd:,.2f}",
            (f"unmatched inventory  {self.unmatched_inventory_qty:,.6f} base"
            f" ({len(self.open_lots_at_end)} open lots, force-closed {self.forced_exit_qty:,.6f})"),
            (f"fills                {self.buys_filled} buys / {self.sells_filled} sells"
            f" from {self.orders_placed} placed, {self.orders_cancelled} cancelled"),
            f"bars outside ladder  {self.bars_above_grid} above / {self.bars_below_grid} below",
            (f"grid   total return  {m.total_return * 100:,.2f}%   "
            f"Sharpe {m.sharpe:,.2f}   maxDD {m.max_drawdown * 100:,.2f}%   "
            f"final ${m.final_equity:,.2f}"),
            (f"hold   total return  {b.total_return * 100:,.2f}%   "
            f"Sharpe {b.sharpe:,.2f}   maxDD {b.max_drawdown * 100:,.2f}%   "
            f"final ${b.final_equity:,.2f}"),
        ]


class _GridBook:
    """Cash, inventory and FIFO realization for one ladder run."""

    def __init__(self, initial_capital: float, costs: CostConfig) -> None:
        self.cash = initial_capital
        self.costs = costs
        self.lots: list[Lot] = []
        self.trades: list[Trade] = []
        self.fees = 0.0
        self.slippage = 0.0
        self.carry = 0.0
        self.realized = 0.0
        self.gross_captured = 0.0
        self.round_trips = 0
        self.buys = 0
        self.sells = 0
        self.unmatched_sell_qty = 0.0

    @property
    def inventory_qty(self) -> float:
        """Base units currently held across all open lots."""
        return sum(lot.qty for lot in self.lots)

    @property
    def unsettled_carry(self) -> float:
        """Carry accrued on open lots but not yet realized by an exit."""
        return sum(lot.accrued_carry_usd for lot in self.lots)

    def equity(self, price: float) -> float:
        """Cash plus inventory marked at `price`, less carry still owed."""
        return self.cash + self.inventory_qty * price - self.unsettled_carry

    def accrue_carry(self, price: float, hours: float, bps_per_hour: float) -> None:
        """Charge carry on each open lot's mark-to-market notional."""
        if bps_per_hour <= 0.0:
            return
        for lot in self.lots:
            lot.accrued_carry_usd += lot.qty * price * bps_per_hour / 10_000.0 * hours

    def buy(self, level: float, qty: float, ts: int, index: int) -> bool:
        """Fill a resting bid. Returns False when cash cannot cover it.

        The fill price is the level moved against us by the full slippage
        allowance; `qty` is the quantity the planner sized at the level, so the
        cash outlay is slightly more than the planned notional. Refusing on
        insufficient cash rather than allowing an overdraft keeps a grid from
        reporting fills it could never have funded.
        """
        fill_price = level * (1.0 + self.costs.slippage_bps / 10_000.0)
        notional = qty * fill_price
        fee = notional * self.costs.fee_bps / 10_000.0
        if notional + fee > self.cash:
            return False
        slip = qty * (fill_price - level)

        self.cash -= notional + fee
        self.fees += fee
        self.slippage += slip
        self.buys += 1
        self.lots.append(
            Lot(
                qty=qty,
                price=fill_price,
                level=level,
                entry_fee_usd=fee,
                entry_slippage_usd=slip,
                opened_index=index,
                opened_ts=ts,
            )
        )
        # A buy realizes nothing: its fee rides on the lot and is realized with
        # the exit. Recording -fee here instead would count every entry as a
        # losing "trade" and quietly halve the reported win rate.
        self.trades.append(
            Trade(
                ts=ts,
                bar_index=index,
                side=SIDE_BUY,
                price=fill_price,
                units=qty,
                notional=notional,
                fee=fee,
                slippage=slip,
                borrow_fee_settled=0.0,
                realized_pnl=0.0,
                equity_after=self.equity(fill_price),
                reason="grid_entry",
            )
        )
        return True

    def sell(
        self,
        level: float,
        qty: float,
        ts: int,
        index: int,
        reason: str,
        max_open_index: int | None = None,
        closes: Sequence[tuple[float, float]] = (),
    ) -> tuple[float, float]:
        """Fill a resting offer, closing the lots it was paired with first.

        Returns `(realized, matched_qty)`.

        `closes` is the `(rung level, qty)` list the planner paired this exit with
        (port of `closesLots` in `extension/src/core/pnl.js`). Those lots are
        closed first, oldest per rung; whatever they cannot cover, and any sell
        with no `closes` (the end-of-run forced exit), is matched FIFO.

        Pairing first matters because the planner derives each exit from the
        residual inventory's rung. Strict FIFO let exit B (paired to a lot bought
        at a lower rung) consume the older, higher-rung lot A, leaving B's lot as
        the residual; the next plan then rested that lot's exit at the level A
        was bought at, so the sell captured zero spread and paid two fees. The
        extension had the same defect and the same fix, and the two must agree
        (CLAUDE.md backtester rule 6).

        `max_open_index` bounds matching to lots opened strictly before that bar. It
        exists because pairing and FIFO can otherwise become a real leak:
        when two exits fill in one bar, the first can consume the older lots, and
        the second can then reach a lot bought *in this same bar* — an indirect
        same-bar round trip, which is the path assumption this simulator refuses
        to make. Short of old inventory the exit fills partially and the rest is
        re-planned from the close.
        """
        fill_price = level * (1.0 - self.costs.slippage_bps / 10_000.0)
        eligible = [
            lot
            for lot in self.lots
            if max_open_index is None or lot.opened_index < max_open_index
        ]
        available = sum(lot.qty for lot in eligible)
        matched = min(qty, available)
        if matched <= 0:
            if not eligible and self.lots:
                # Held inventory exists but all of it was bought this bar, so this
                # is a deferral, not a naked sell.
                return 0.0, 0.0
            self.unmatched_sell_qty += qty
            return 0.0, 0.0

        notional = matched * fill_price
        fee = notional * self.costs.fee_bps / 10_000.0
        slip = matched * (level - fill_price)

        remaining = matched
        gross = 0.0
        entry_fee_share = 0.0
        entry_slip_share = 0.0
        carry_share = 0.0

        def close(lot: Lot, want: float) -> None:
            nonlocal remaining, gross, entry_fee_share, entry_slip_share, carry_share
            take = min(lot.qty, want)
            frac = take / lot.qty
            # Gross is the rung spread, measured level to level. Measuring it
            # between *fill* prices would fold both slippage legs into gross and
            # then subtract them again below, understating realized P&L by the
            # full slippage on every round trip — and it would silently break
            # `final_equity == capital + realized` at any non-zero slippage.
            gross += (level - lot.level) * take
            entry_fee_share += lot.entry_fee_usd * frac
            entry_slip_share += lot.entry_slippage_usd * frac
            carry_share += lot.accrued_carry_usd * frac
            lot.entry_fee_usd -= lot.entry_fee_usd * frac
            lot.entry_slippage_usd -= lot.entry_slippage_usd * frac
            lot.accrued_carry_usd -= lot.accrued_carry_usd * frac
            lot.qty -= take
            remaining -= take
            if lot.qty <= 1e-15:
                eligible.remove(lot)
                self.lots.remove(lot)

        # Paired lots first. Lots match on their rung level, which is the exact
        # float the planner read from the lot, so equality is safe.
        for link_level, link_qty in closes:
            want = min(remaining, link_qty)
            for lot in [l for l in eligible if l.level == link_level]:
                if want <= 1e-15:
                    break
                before = remaining
                close(lot, want)
                want -= before - remaining
        while remaining > 1e-15 and eligible:
            close(eligible[0], remaining)

        realized = gross - fee - slip - entry_fee_share - entry_slip_share - carry_share
        # Carry leaves cash when it settles. Subtracting it from `realized` only
        # would let the equity curve dip while a lot is open (via
        # `unsettled_carry`) and then step back up when the lot closed, which
        # reads as free money at exactly the moment the cost becomes real.
        self.cash += notional - fee - carry_share
        if self.cash < -1e-9:
            # Only reachable with carry on: accrued carry has exceeded what the
            # inventory sold for, i.e. an account that should have been margin
            # called. Clamping cash to zero here would drop a real cost and hand
            # back a flattering equity curve, so refuse instead and say why.
            raise RuntimeError(
                f"bar {index}: cash went negative (${self.cash:,.6f}) after settling "
                f"${carry_share:,.6f} of carry. This run models carry but not "
                "liquidation, so the result would describe an account that could "
                "not have existed. Lower --carry-bps-per-hour, shorten the holding "
                "period, or add a liquidation model."
            )
        self.fees += fee
        self.slippage += slip
        self.carry += carry_share
        self.realized += realized
        self.gross_captured += gross
        self.sells += 1
        if reason == "grid_exit":
            self.round_trips += 1

        self.trades.append(
            Trade(
                ts=ts,
                bar_index=index,
                side=SIDE_SELL,
                price=fill_price,
                units=-matched,
                notional=notional,
                fee=fee,
                slippage=slip,
                borrow_fee_settled=carry_share,
                realized_pnl=realized,
                equity_after=self.equity(fill_price),
                reason=reason,
            )
        )
        return realized, matched


def _plan(
    cfg: GridConfig,
    levels: Sequence[float],
    price: float,
    lots: Iterable[Lot],
    skipped: Counter,
    level_index: dict[float, int] | None = None,
) -> list[RestingOrder]:
    """Every order the ladder wants resting at `price`. Port of `planGrid`.

    Returns the full desired set, including orders already on the venue — the
    caller diffs it against what is resting to decide placements and
    cancellations. Filtering "already resting" out here instead would make the
    desired set indistinguishable from "newly wanted", and every still-wanted
    order would look like a cancellation on the next bar.

    Exits are aggregated by exit level before emission: two lots on the same rung
    map to one level and therefore one order, and emitting them separately would
    place the rung twice while the book recorded it once.
    """
    wanted: list[RestingOrder] = []
    lot_level_indexes: set[int] = set()
    exit_buckets: dict[float, list[tuple[float, float]]] = {}

    for lot in lots:
        if lot.qty <= 0:
            continue
        # The extension anchors occupancy and exits to the actual fill price.
        # Keep lot.level only as the lot-matching and attribution identity.
        idx = nearest_level_index(levels, lot.price)
        lot_level_indexes.add(idx)
        exit_level = paired_exit_level(levels, lot.price)
        if not math.isfinite(exit_level) or exit_level <= lot.price:
            skipped["exit-not-above-entry"] += 1
            continue
        exit_buckets.setdefault(exit_level, []).append((lot.level, lot.qty))

    for exit_level, closes in exit_buckets.items():
        qty = sum(q for _, q in closes)
        notional = qty * exit_level
        if notional < cfg.min_order_usd:
            skipped["exit-below-venue-minimum"] += 1
            continue
        wanted.append(
            RestingOrder(
                side=SIDE_SELL,
                level=exit_level,
                qty=qty,
                notional_usd=notional,
                planned_index=-1,
                closes=tuple(closes),
            )
        )

    for i, level in enumerate(levels):
        side = side_for_level(level, price, cfg.deadband_bps)
        if side is None:
            skipped["inside-deadband"] += 1
            continue
        if side != SIDE_BUY:
            skipped["above-market-entry-not-taken"] += 1
            continue
        if i in lot_level_indexes:
            skipped["lot-already-held-at-level"] += 1
            continue
        if cfg.notional_per_rung_usd < cfg.min_order_usd:
            skipped["entry-below-venue-minimum"] += 1
            continue
        wanted.append(
            RestingOrder(
                side=SIDE_BUY,
                level=level,
                qty=cfg.notional_per_rung_usd / level,
                notional_usd=cfg.notional_per_rung_usd,
                planned_index=-1,
            )
        )
    return wanted


def _baseline_equity(closes: np.ndarray, initial_capital: float, costs: CostConfig) -> np.ndarray:
    """Buy-and-hold equity on the same bars, paying entry costs once.

    The mandatory baseline: a grid that underperforms holding the asset has not
    earned its complexity, and the comparison is meaningless if only one leg pays
    fees.
    """
    if closes.size == 0:
        return np.zeros(0, dtype="float64")
    c = (costs.fee_bps + costs.slippage_bps) / 10_000.0
    notional = initial_capital / (1.0 + c)
    units = notional / closes[0]
    return units * closes.astype("float64")


def run_grid_backtest(
    cfg: GridConfig,
    arrays: dict[str, np.ndarray],
    *,
    initial_capital: float = 10_000.0,
    interval: str = "1d",
    costs: CostConfig | None = None,
    carry_bps_per_hour: float = 0.0,
    risk_free_rate: float = 0.0,
    close_at_end: bool = True,
    continuation: dict | None = None,
    entries_paused: bool = False,
) -> GridRunResult:
    """Run one ladder over one OHLCV series.

    See the module docstring for the per-bar ordering and the three pessimism
    conventions. `carry_bps_per_hour` defaults to 0 because the executable venue
    is spot; it is a parameter rather than a constant so a borrowed-margin grid
    can be modelled without editing the P&L path.
    """
    costs = CostConfig() if costs is None else costs
    if not isinstance(costs, CostConfig):
        raise ValueError("costs must be a CostConfig")  # noqa: TRY004 -- retain public validation contract
    costs.validate()
    for name, value in (("initial_capital", initial_capital), ("carry_bps_per_hour", carry_bps_per_hour), ("risk_free_rate", risk_free_rate)):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if carry_bps_per_hour < 0:
        raise ValueError("carry_bps_per_hour cannot be negative")
    if not 0.0 <= costs.slippage_bps < 10_000.0:
        # At 10,000 bps a sell's fill price reaches zero and beyond it goes
        # negative, so a sale would *reduce* cash.
        raise ValueError(
            f"slippage_bps must be in [0, 10000), got {costs.slippage_bps}"
        )
    if costs.fee_bps < 0:
        raise ValueError(f"fee_bps cannot be negative, got {costs.fee_bps}")

    checked = validate_bar_arrays(arrays, interval, require_open_volume=False)
    ts, highs, lows, closes = (checked[name] for name in ("ts", "high", "low", "close"))
    n = closes.size

    levels = grid_levels(cfg)
    # The ladder is fixed for the whole run, so its level -> index map is built
    # once instead of scanning every level for every lot on every bar.
    level_index = {level: i for i, level in enumerate(levels)}
    book = _GridBook(initial_capital, costs)
    resting: dict[str, RestingOrder] = {}
    skipped: Counter = Counter()
    hpb = hours_per_bar(interval)

    equity = np.empty(n, dtype="float64")
    exposure = np.zeros(n, dtype="float64")
    orders_placed = 0
    orders_cancelled = 0
    bars_above = 0
    bars_below = 0

    offset = 0
    if continuation is not None:
        from dataclasses import asdict
        if continuation["binding"] != repr((cfg.to_dict(), initial_capital, interval, asdict(costs), carry_bps_per_hour)):
            raise ValueError("continuation configuration changed")
        offset = continuation["cursor"]
        if int(ts[0]) != continuation["last_ts"] + INTERVAL_SECONDS[interval]:
            raise ValueError("continuation source gap")
        for key, value in continuation["book"].items():
            setattr(book, key, value)
        book.lots = [Lot(**x) for x in continuation["lots"]]
        resting = {k: RestingOrder(**v) for k, v in continuation["resting"].items()}
        skipped = Counter(continuation["skipped"])
        orders_placed, orders_cancelled, bars_above, bars_below = continuation["counts"]
    for j in range(n):
        i = j + offset
        # -- 1. carry on inventory carried into this bar -------------------
        book.accrue_carry(closes[j], hpb, carry_bps_per_hour)

        # -- 2/3. fills. Buys first: cash a sell frees must not fund a buy in
        # the same bar, because the intrabar path is unknown.
        for key, order in sorted(resting.items(), key=lambda kv: -kv[1].level):
            if entries_paused or order.side != SIDE_BUY or order.planned_index >= i:
                continue
            if lows[j] <= order.level:
                if book.buy(order.level, order.qty, int(ts[j]), i):
                    del resting[key]
                else:
                    skipped["insufficient-cash"] += 1

        for key, order in sorted(resting.items(), key=lambda kv: kv[1].level):
            if order.side != SIDE_SELL or order.planned_index >= i:
                continue
            if highs[j] >= order.level:
                # `max_open_index=i` is what forbids the same-bar round trip: the
                # exit may only consume inventory bought on an earlier bar.
                _, matched = book.sell(
                    order.level,
                    order.qty,
                    int(ts[j]),
                    i,
                    reason="grid_exit",
                    max_open_index=i,
                    closes=order.closes,
                )
                if matched <= 0:
                    skipped["exit-deferred-no-older-inventory"] += 1
                    continue
                if order.qty - matched > 1e-12:
                    skipped["exit-partial-older-inventory-only"] += 1
                # Drop the order either way; the close re-plans the remaining
                # inventory's exit at the level its lots actually imply.
                del resting[key]

        # -- 4. mark to market --------------------------------------------
        # No `max(0.0, ...)` floor here, deliberately, and unlike `core/engine.py`
        # — that engine's floor is justified by isolated per-position margin,
        # which a spot ladder does not have. Clamping would let accrued carry push
        # true equity below zero while the *reported* curve sat at 0.0, and every
        # drawdown and return figure would inherit the floor in the flattering
        # direction. Refusing matches the cash guard in `_GridBook.sell`; the two
        # insolvency paths must not disagree.
        equity[j] = book.equity(closes[j])
        if equity[j] < -1e-9:
            raise RuntimeError(
                f"bar {i}: equity went negative (${equity[j]:,.6f}) with "
                f"${book.unsettled_carry:,.6f} of carry accrued on open inventory. "
                "This run models carry but not liquidation, so the curve past this "
                "bar would describe an account that could not have existed. Lower "
                "--carry-bps-per-hour, shorten the holding period, or add a "
                "liquidation model."
            )
        exposure[j] = (
            book.inventory_qty * closes[j] / equity[j] if equity[j] > 1e-12 else 0.0
        )
        if closes[j] > cfg.upper:
            bars_above += 1
        elif closes[j] < cfg.lower:
            bars_below += 1

        # -- 5. re-plan from this close; fillable from the next bar --------
        # Diff desired against resting. An order already on the venue keeps its
        # original `planned_index`, so re-planning cannot reset a rung's fill
        # eligibility and thereby delay it forever.
        wanted = _plan(cfg, levels, closes[j], book.lots, skipped, level_index)
        desired = {_level_key(o.side, o.level): o for o in wanted}
        for key in list(resting):
            if key not in desired:
                del resting[key]
                orders_cancelled += 1
        for key, order in desired.items():
            if key in resting:
                skipped["already-resting"] += 1
                continue
            order.planned_index = i
            resting[key] = order
            orders_placed += 1

    forced_qty = 0.0
    if close_at_end and book.lots:
        # Force-close leftover inventory at the final close so metrics see the
        # real end state. Flagged separately from `round_trips`: a forced exit is
        # not a captured rung width, and counting it as one would inflate the
        # win rate of a grid that simply ran out of range.
        forced_qty = book.inventory_qty
        # No `max_open_index` here: the run is over, so every lot must be closed
        # even one opened on the final bar.
        book.sell(closes[-1], forced_qty, int(ts[-1]), offset + n - 1, reason="grid_forced_exit")
        equity[-1] = book.equity(closes[-1])
        exposure[-1] = 0.0

    ppy = periods_per_year(interval)
    metrics = compute_metrics(equity, ts, book.trades, exposure, ppy, risk_free_rate, 0, initial_equity=initial_capital)
    baseline = _baseline_equity(closes, initial_capital, costs)
    baseline_metrics = compute_metrics(
        baseline, ts, [], np.ones(n, dtype="float64"), ppy, risk_free_rate, 0,
        initial_equity=initial_capital,
    )

    from dataclasses import asdict
    state = {
        "schema_version": 1, "cursor": offset + n, "last_ts": int(ts[-1]),
        "binding": repr((cfg.to_dict(), initial_capital, interval, asdict(costs), carry_bps_per_hour)),
        "book": {k: v for k, v in vars(book).items() if k not in ("costs", "lots", "trades")},
        "lots": [asdict(x) for x in book.lots],
        "resting": {k: asdict(v) for k, v in resting.items()},
        "skipped": dict(skipped), "counts": [orders_placed, orders_cancelled, bars_above, bars_below],
    }
    return GridRunResult(
        continuation=state,
        config=cfg.to_dict(),
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        timestamps=ts,
        equity=equity,
        exposure=exposure,
        baseline_equity=baseline,
        trades=book.trades,
        rung_width_bps=rung_width_bps(cfg),
        capital_required_usd=capital_requirement(cfg, closes[0])["total_usd"],
        round_trips=book.round_trips,
        gross_captured_usd=book.gross_captured,
        realized_pnl_usd=book.realized,
        fees_paid_usd=book.fees,
        slippage_paid_usd=book.slippage,
        carry_paid_usd=book.carry,
        carry_bps_per_hour=carry_bps_per_hour,
        buys_filled=book.buys,
        sells_filled=book.sells,
        orders_placed=orders_placed,
        orders_cancelled=orders_cancelled,
        open_lots_at_end=list(book.lots),
        unmatched_inventory_qty=book.inventory_qty,
        forced_exit_qty=forced_qty,
        bars_above_grid=bars_above,
        bars_below_grid=bars_below,
        skipped=dict(skipped),
    )


def rebind_grid_state(state, cfg, *, initial_capital, interval, costs, carry_bps_per_hour=0.0):
    """Replace a paused flat ladder's geometry without funding a new account."""
    import copy
    from dataclasses import asdict

    if state.get("schema_version") != 1 or state["lots"]:
        raise ValueError("grid configuration adoption requires a flat canonical account")
    result = copy.deepcopy(state)
    result["binding"] = repr((cfg.to_dict(), initial_capital, interval, asdict(costs), carry_bps_per_hour))
    # Old resting entries belong to the old geometry. The next observed close
    # plans the replacement ladder; no synthetic bar or fill is introduced.
    result["resting"] = {}
    return result
