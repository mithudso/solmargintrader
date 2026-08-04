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
sets lot age, and lot age is what FIFO realization consumes. Portfolio totals do
not depend on it; which lot a given exit is matched against does.

Costs are never optional here (see the backtester's non-negotiables): the taker
fee, the slippage allowance and an explicit carry rate all stay in the P&L path.
Carry defaults to zero because Trigger V2 is a **spot** venue with no borrow —
not because carry is free. Pass `carry_bps_per_hour` to model a borrowed-margin
grid, and the number will be labelled in the result.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

from .metrics import Metrics, compute_metrics
from .types import CostConfig, Trade, hours_per_bar, periods_per_year

SPACING_GEOM = "geom"
SPACING_ARITH = "arith"
SPACINGS = (SPACING_GEOM, SPACING_ARITH)

SIDE_BUY = "buy"
SIDE_SELL = "sell"

# Jupiter Trigger V2's hard floor. A rung below it is not a small order, it is a
# rejected one, so the planner has to know the number.
VENUE_MIN_ORDER_USD = 10.0


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
        if not self.lower > 0:
            raise ValueError(f"lower must be > 0, got {self.lower}")
        if not self.upper > self.lower:
            raise ValueError(f"upper ({self.upper}) must exceed lower ({self.lower})")
        if not isinstance(self.rungs, int) or self.rungs < 2:
            raise ValueError(f"rungs must be an int >= 2, got {self.rungs!r}")
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
    return f"{side}:{round(level * 1e6)}"


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

    def summary_lines(self) -> list[str]:
        """Human-readable digest. Kept here so the CLI stays a thin adapter."""
        m, b = self.metrics, self.baseline_metrics
        return [
            f"rung width           {self.rung_width_bps:,.1f} bps",
            f"capital required     ${self.capital_required_usd:,.2f}",
            f"round trips          {self.round_trips}",
            f"gross captured       ${self.gross_captured_usd:,.2f}",
            f"fees + slippage      ${self.fees_paid_usd + self.slippage_paid_usd:,.2f}"
            f"  (fees ${self.fees_paid_usd:,.2f}, slippage ${self.slippage_paid_usd:,.2f})",
            f"carry                ${self.carry_paid_usd:,.2f}"
            f"  ({self.carry_bps_per_hour:g} bps/hr on inventory)",
            f"realized P&L         ${self.realized_pnl_usd:,.2f}",
            f"unmatched inventory  {self.unmatched_inventory_qty:,.6f} base"
            f" ({len(self.open_lots_at_end)} open lots, force-closed {self.forced_exit_qty:,.6f})",
            f"fills                {self.buys_filled} buys / {self.sells_filled} sells"
            f" from {self.orders_placed} placed, {self.orders_cancelled} cancelled",
            f"bars outside ladder  {self.bars_above_grid} above / {self.bars_below_grid} below",
            f"grid   total return  {m.total_return * 100:,.2f}%   "
            f"Sharpe {m.sharpe:,.2f}   maxDD {m.max_drawdown * 100:,.2f}%   "
            f"final ${m.final_equity:,.2f}",
            f"hold   total return  {b.total_return * 100:,.2f}%   "
            f"Sharpe {b.sharpe:,.2f}   maxDD {b.max_drawdown * 100:,.2f}%   "
            f"final ${b.final_equity:,.2f}",
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
    ) -> tuple[float, float]:
        """Fill a resting offer against the oldest lots (FIFO).

        Returns `(realized, matched_qty)`.

        FIFO is the IRS default for property and what crypto tax tools expect, so
        the numbers here reconcile with the extension's CSV export. Note that the
        *planner* pairs each exit to a specific lot while realization matches
        FIFO; with several rungs open these disagree per-trip, though portfolio
        totals are identical. The extension documents the same divergence.

        `max_open_index` bounds FIFO to lots opened strictly before that bar. It
        exists because the divergence above can otherwise become a real leak:
        when two exits fill in one bar, the first consumes the oldest lots, and
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
        while remaining > 1e-15 and eligible:
            lot = eligible[0]
            take = min(lot.qty, remaining)
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
                eligible.pop(0)
                self.lots.remove(lot)

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
    exit_buckets: dict[float, float] = {}

    for lot in lots:
        if lot.qty <= 0:
            continue
        # A lot's rung is known exactly — it is the level the bid rested at — so
        # look it up rather than re-deriving it from the fill price. Besides being
        # O(1) instead of O(rungs), it cannot mis-snap a lot to a neighbouring rung
        # when slippage is a large fraction of the rung width.
        idx = level_index.get(lot.level) if level_index else None
        if idx is None:
            idx = nearest_level_index(levels, lot.level)
        lot_level_indexes.add(idx)
        exit_level = (
            levels[idx + 1]
            if idx < len(levels) - 1
            else paired_exit_level(levels, lot.level)
        )
        exit_buckets[exit_level] = exit_buckets.get(exit_level, 0.0) + lot.qty

    for exit_level, qty in exit_buckets.items():
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
) -> GridRunResult:
    """Run one ladder over one OHLCV series.

    See the module docstring for the per-bar ordering and the three pessimism
    conventions. `carry_bps_per_hour` defaults to 0 because the executable venue
    is spot; it is a parameter rather than a constant so a borrowed-margin grid
    can be modelled without editing the P&L path.
    """
    costs = costs or CostConfig()
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

    missing = [k for k in ("ts", "high", "low", "close") if k not in arrays]
    if missing:
        raise ValueError(f"arrays is missing required series: {', '.join(missing)}")

    ts = np.asarray(arrays["ts"])
    highs = np.asarray(arrays["high"], dtype="float64")
    lows = np.asarray(arrays["low"], dtype="float64")
    closes = np.asarray(arrays["close"], dtype="float64")
    n = closes.size
    if n == 0:
        raise ValueError("cannot backtest an empty series")

    # Length and finiteness are checked up front rather than trusted. A `high`
    # array longer than `close` would silently truncate the run — the dangerous
    # direction, because it returns a plausible number for the wrong window — and
    # a NaN close survives `max(0.0, nan)` as 0.0, poisoning every metric with no
    # error anywhere.
    lengths = {"ts": ts.size, "high": highs.size, "low": lows.size, "close": closes.size}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"series lengths disagree: {lengths}")
    for name, series in (("high", highs), ("low", lows), ("close", closes)):
        if not np.all(np.isfinite(series)):
            bad = int(np.argmin(np.isfinite(series)))
            raise ValueError(f"{name} contains a non-finite value at index {bad}")
    if np.any(lows <= 0.0):
        raise ValueError(
            f"low contains a non-positive price at index {int(np.argmin(lows > 0.0))}; "
            "a grid divides by its levels and cannot price a zero market"
        )
    if np.any(highs < lows):
        raise ValueError(
            f"high < low at index {int(np.argmax(highs < lows))}; the bars are malformed"
        )

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

    for i in range(n):
        # -- 1. carry on inventory carried into this bar -------------------
        book.accrue_carry(closes[i], hpb, carry_bps_per_hour)

        # -- 2/3. fills. Buys first: cash a sell frees must not fund a buy in
        # the same bar, because the intrabar path is unknown.
        for key, order in sorted(resting.items(), key=lambda kv: -kv[1].level):
            if order.side != SIDE_BUY or order.planned_index >= i:
                continue
            if lows[i] <= order.level:
                if book.buy(order.level, order.qty, int(ts[i]), i):
                    del resting[key]
                else:
                    skipped["insufficient-cash"] += 1

        for key, order in sorted(resting.items(), key=lambda kv: kv[1].level):
            if order.side != SIDE_SELL or order.planned_index >= i:
                continue
            if highs[i] >= order.level:
                # `max_open_index=i` is what forbids the same-bar round trip: the
                # exit may only consume inventory bought on an earlier bar.
                _, matched = book.sell(
                    order.level,
                    order.qty,
                    int(ts[i]),
                    i,
                    reason="grid_exit",
                    max_open_index=i,
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
        equity[i] = max(0.0, book.equity(closes[i]))
        exposure[i] = (
            book.inventory_qty * closes[i] / equity[i] if equity[i] > 1e-12 else 0.0
        )
        if closes[i] > cfg.upper:
            bars_above += 1
        elif closes[i] < cfg.lower:
            bars_below += 1

        # -- 5. re-plan from this close; fillable from the next bar --------
        # Diff desired against resting. An order already on the venue keeps its
        # original `planned_index`, so re-planning cannot reset a rung's fill
        # eligibility and thereby delay it forever.
        wanted = _plan(cfg, levels, closes[i], book.lots, skipped, level_index)
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
        book.sell(closes[-1], forced_qty, int(ts[-1]), n - 1, reason="grid_forced_exit")
        equity[-1] = max(0.0, book.equity(closes[-1]))
        exposure[-1] = 0.0

    ppy = periods_per_year(interval)
    metrics = compute_metrics(equity, ts, book.trades, exposure, ppy, risk_free_rate, 0)
    baseline = _baseline_equity(closes, initial_capital, costs)
    baseline_metrics = compute_metrics(
        baseline, ts, [], np.ones(n, dtype="float64"), ppy, risk_free_rate, 0
    )

    return GridRunResult(
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
