"""Event-driven backtest engine.

Bar ordering inside the loop is the whole correctness story:

    1. execute any fill scheduled for this bar       at this bar's OPEN
    2. accrue borrow fees through this bar's close   (perp only)
    3. liquidation check against this bar's low/high (perp only)
    4. ask the strategy for a target, given data <= i only
    5. schedule that target for bar i + fill_delay   (or fill at close if 0)
    6. mark to market at this bar's close and record

The strategy is consulted at step 4 with a BarWindow that cannot read past
bar i, and the resulting order is filled at step 1 of a LATER bar. There is no
code path by which a decision uses a price it could not have observed.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import asdict, dataclass, field
from numbers import Integral, Real
from typing import Any, Protocol, runtime_checkable

import numpy as np

from . import perps
from .metrics import Metrics, compute_metrics
from .types import (
    INTERVAL_SECONDS,
    BarWindow,
    CostConfig,
    IntrabarLayer,
    Mode,
    Position,
    Side,
    Trade,
    hours_per_bar,
    periods_per_year,
    validate_bar_arrays,
)


@runtime_checkable
class Strategy(Protocol):
    """A strategy maps visible history to a target exposure for the next bar."""

    name: str
    params: dict[str, Any]

    def warmup_bars(self) -> int:
        """Bars required before the first valid signal."""
        ...

    def on_bar(self, history: BarWindow) -> float:
        """Target exposure for the NEXT bar, in [-1, 1]."""
        ...


@dataclass
class EngineConfig:
    """Execution settings for one backtest run."""

    mode: Mode = Mode.SPOT
    leverage: float = 1.0
    initial_capital: float = 10_000.0
    interval: str = "1d"
    # 0 == fill at this bar's close (close-to-close); >=1 == fill at the open
    # of bar i+delay. Default 1 is the conservative choice.
    fill_delay: int = 1
    rebalance_threshold: float = 0.0
    risk_free_rate: float = 0.0
    costs: CostConfig = field(default_factory=CostConfig)
    allow_short: bool = False
    seed: int = 0
    # Finer bars, finest first, used to look inside each held coarse bar for a
    # liquidation (see IntrabarLayer). Empty means coarse low/high only.
    intrabar: tuple = ()

    def __post_init__(self) -> None:
        """Validate settings that would otherwise fail deep in the loop."""
        self.validate()
        if self.allow_short and self.mode is Mode.SPOT:
            # Silently clamping to long-only would hide a contradictory config.
            warnings.warn(
                "allow_short has no effect in spot mode; short exposure is "
                "clamped to 0. Pass mode='perp' to trade short.",
                UserWarning,
                stacklevel=2,
            )

    def validate(self) -> None:
        """Validate again at run entry because callers may mutate this config."""
        try:
            self.mode = Mode(self.mode)
        except (TypeError, ValueError) as exc:
            raise ValueError("mode must be spot or perp") from exc
        for name in (
            "initial_capital",
            "leverage",
            "rebalance_threshold",
            "risk_free_rate",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(value)
            ):
                raise ValueError(f"{name} must be finite")
        if self.initial_capital <= 0 or self.leverage <= 0:
            raise ValueError("initial_capital and leverage must be positive")
        if self.rebalance_threshold < 0:
            raise ValueError("rebalance_threshold cannot be negative")
        if (
            isinstance(self.fill_delay, bool)
            or not isinstance(self.fill_delay, Integral)
            or self.fill_delay < 0
        ):
            raise ValueError("fill_delay must be a nonnegative integer")
        if not isinstance(self.interval, str) or self.interval not in INTERVAL_SECONDS:
            raise ValueError("unsupported bar interval")
        if not isinstance(self.allow_short, bool):
            raise ValueError("allow_short must be boolean")  # noqa: TRY004 -- retain public validation contract
        if self.mode is Mode.SPOT and self.leverage != 1.0:
            raise ValueError(
                "spot mode does not borrow; use --mode perp for leverage > 1"
            )
        if not isinstance(self.costs, CostConfig):
            raise ValueError("costs must be a CostConfig")  # noqa: TRY004 -- retain public validation contract
        self.costs.validate()
        self.intrabar = tuple(self.intrabar or ())
        for layer in self.intrabar:
            if not isinstance(layer, IntrabarLayer):
                raise ValueError("intrabar must hold IntrabarLayer objects")  # noqa: TRY004 -- retain public validation contract
            if (
                layer.seconds >= INTERVAL_SECONDS[self.interval]
                or INTERVAL_SECONDS[self.interval] % layer.seconds
            ):
                raise ValueError(
                    "intrabar layers must be finer than, and divide, the bar interval"
                )


@dataclass(frozen=True)
class AccountState:
    """End-of-prefix book; pending indices refer to the original input origin."""

    cash: float
    position: Position
    pending_targets: dict[int, float]
    fees_paid: float
    slippage_paid: float
    borrow_paid: float
    realized_pnl: float


@dataclass
class BacktestResult:
    """Everything one strategy run produced."""

    strategy_name: str
    params: dict[str, Any]
    timestamps: np.ndarray
    equity: np.ndarray
    exposure: np.ndarray
    trades: list[Trade]
    metrics: Metrics
    gross_metrics: Metrics
    liquidation_count: int
    first_tradeable_index: int
    mode: str
    leverage: float
    # Held perp bars that a finer layer covered completely / that fell back to
    # the coarse range / whose coarse range exceeded the fine range.
    continuation: dict | None = None
    account: AccountState | None = None
    bars_refined: int = 0
    bars_unrefined: int = 0
    bars_range_mismatch: int = 0


class _Book:
    """Mutable cash-and-position book for a single run.

    Spot: equity = cash + units * price.
    Perp: equity = cash + collateral + unrealized_pnl - accrued_borrow_fee.

    At leverage 1 with zero costs the two reduce to the same number, which is
    what makes the buy-and-hold identity test meaningful in both modes.
    """

    def __init__(self, config: EngineConfig) -> None:
        self.cfg = config
        self.cash = config.initial_capital
        self.pos = Position()
        self.trades: list[Trade] = []
        self.liquidations = 0
        # Gross book: identical decisions, zero costs. Runs in parallel so the
        # report can show cost drag without a second pass over the data.
        self.gross_cash = config.initial_capital
        self.gross_units = 0.0

    # -- valuation -------------------------------------------------------

    def equity(self, price: float) -> float:
        """Mark-to-market equity at `price`."""
        if not self.pos.is_open:
            return self.cash
        if self.cfg.mode is Mode.SPOT:
            return self.cash + self.pos.units * price
        return (
            self.cash
            + self.pos.collateral
            + self.pos.unrealized_pnl(price)
            - self.pos.accrued_borrow_fee
        )

    def gross_equity(self, price: float) -> float:
        """Equity of the parallel zero-cost book."""
        return self.gross_cash + self.gross_units * price

    def signed_notional(self, price: float) -> float:
        """Current signed notional exposure at `price`."""
        if not self.pos.is_open:
            return 0.0
        sign = 1.0 if self.pos.side is Side.LONG else -1.0
        return sign * abs(self.pos.units) * price

    # -- fills -----------------------------------------------------------

    def _costs_on(self, notional: float) -> tuple[float, float]:
        """(fee, slippage) charged on `notional` for the configured mode."""
        c = self.cfg.costs
        fee_bps = c.perp_base_fee_bps if self.cfg.mode is Mode.PERP else c.fee_bps
        return (
            notional * fee_bps / 10_000.0,
            notional * c.slippage_bps / 10_000.0,
        )

    def close(
        self,
        price: float,
        ts: int,
        index: int,
        reason: str,
        forfeit: bool = False,
    ) -> None:
        """Close the whole position at `price`, settling fees and borrow."""
        if not self.pos.is_open:
            return
        notional = self.pos.notional_at(price)
        fee, slip = self._costs_on(notional)
        borrow = self.pos.accrued_borrow_fee
        price_pnl = self.pos.unrealized_pnl(price)
        collateral = self.pos.collateral
        entry_costs = self.pos.entry_costs

        if self.cfg.mode is Mode.SPOT:
            self.cash += self.pos.units * price - fee - slip
        else:
            # Isolated margin cannot debit the wallet's unposted free cash,
            # including when a gap overshoots the liquidation threshold.
            payout = max(0.0, collateral + price_pnl - borrow - fee - slip)
            if forfeit:
                payout = 0.0  # venue keeps the remaining collateral
            self.cash += payout

        realized = (
            price_pnl - borrow - fee - slip
            if self.cfg.mode is Mode.SPOT
            else payout - collateral
        ) - entry_costs
        units_closed = self.pos.units
        self.pos = Position()

        # Mirror the decision in the gross book at zero cost.
        self.gross_cash += self.gross_units * price
        if self.cfg.mode is Mode.PERP:
            self.gross_cash += max(0.0, -collateral - price_pnl)
        self.gross_units = 0.0

        self.trades.append(
            Trade(
                ts=ts,
                bar_index=index,
                side="close",
                price=price,
                units=-units_closed,
                notional=notional,
                fee=fee,
                slippage=slip,
                borrow_fee_settled=borrow,
                realized_pnl=realized,
                equity_after=self.cash,
                reason=reason,
            )
        )

    def resize(self, target_notional: float, price: float, ts: int, index: int) -> None:
        """Adjust an open position toward `target_notional` on the same side.

        Costs are charged on the SIZE CHANGE, not on a synthetic round trip.
        This matches the venue: opening more of the same asset and side merges
        into the existing position at a blended average entry price rather than
        closing and reopening. Charging a full round trip here would roughly
        double the real fee and, at leverage, dominate every other term.
        """
        if not self.pos.is_open:
            return
        side = self.pos.side
        cur_units = abs(self.pos.units)
        cur_notional = cur_units * price
        delta_notional = target_notional - cur_notional
        if abs(delta_notional) <= 1e-12 or price <= 0:
            return

        fee, slip = self._costs_on(abs(delta_notional))
        delta_units = abs(delta_notional) / price
        direction = 1.0 if side is Side.LONG else -1.0

        if delta_notional > 0:
            # The target uses pre-fill equity. Reserve costs before spending the
            # remaining cash, just as open() does for a full allocation.
            collateral_rate = (
                1.0 if self.cfg.mode is Mode.SPOT else 1.0 / self.cfg.leverage
            )
            cost_rate = (fee + slip) / delta_notional
            delta_notional = min(
                delta_notional, max(0.0, self.cash) / (collateral_rate + cost_rate)
            )
            if delta_notional <= 1e-12:
                return
            fee, slip = self._costs_on(delta_notional)
            delta_units = delta_notional / price
            if self.cfg.mode is Mode.SPOT:
                self.cash = max(0.0, self.cash - delta_notional - fee - slip)
            else:
                add_collateral = delta_notional / self.cfg.leverage
                self.cash = max(0.0, self.cash - add_collateral - fee - slip)
                self.pos.collateral += add_collateral
            new_units = cur_units + delta_units
            self.pos.entry_price = (
                cur_units * self.pos.entry_price + delta_units * price
            ) / new_units
            self.pos.units = new_units * direction
            self.pos.entry_costs += fee + slip
            realized = 0.0
            borrow_settled = 0.0
            self.gross_cash -= delta_units * direction * price
            self.gross_units += delta_units * direction
        else:
            # -- decrease: realise PnL and a proportional share of borrow ---
            frac = min(delta_units / cur_units, 1.0)
            price_pnl = direction * (price - self.pos.entry_price) * delta_units
            borrow_settled = self.pos.accrued_borrow_fee * frac
            self.pos.accrued_borrow_fee -= borrow_settled
            entry_cost_share = self.pos.entry_costs * frac
            self.pos.entry_costs -= entry_cost_share
            if self.cfg.mode is Mode.SPOT:
                self.cash += delta_units * price - fee - slip
            else:
                released = self.pos.collateral * frac
                self.pos.collateral -= released
                payout = max(0.0, released + price_pnl - borrow_settled - fee - slip)
                self.cash += payout
            new_units = cur_units - delta_units
            self.pos.units = new_units * direction
            realized = (
                price_pnl - borrow_settled - fee - slip
                if self.cfg.mode is Mode.SPOT
                else payout - released
            ) - entry_cost_share
            self.gross_cash += delta_units * direction * price
            if self.cfg.mode is Mode.PERP:
                self.gross_cash += max(0.0, -released - price_pnl)
            self.gross_units -= delta_units * direction
            if abs(new_units) <= 1e-12:
                self.pos = Position()

        self.trades.append(
            Trade(
                ts=ts,
                bar_index=index,
                side=str(side),
                price=price,
                units=delta_units * direction * (1.0 if delta_notional > 0 else -1.0),
                notional=abs(delta_notional),
                fee=fee,
                slippage=slip,
                borrow_fee_settled=borrow_settled,
                realized_pnl=realized,
                equity_after=self.equity(price),
                reason="resize_up" if delta_notional > 0 else "resize_down",
            )
        )

    def open(
        self,
        target_notional: float,
        side: Side,
        price: float,
        ts: int,
        index: int,
    ) -> None:
        """Open a position of `target_notional` USD at `price`."""
        if target_notional <= 0 or price <= 0:
            return
        fee, slip = self._costs_on(target_notional)
        units = target_notional / price

        if self.cfg.mode is Mode.SPOT:
            # Cannot spend more cash than is on hand once costs are counted.
            # Solve N + N*c == cash exactly rather than iterating toward it,
            # so a full-capital entry leaves cash at precisely zero.
            c = (self.cfg.costs.fee_bps + self.cfg.costs.slippage_bps) / 10_000.0
            max_notional = self.cash / (1.0 + c)
            if max_notional <= 0:
                return
            if target_notional > max_notional:
                target_notional = max_notional
                fee, slip = self._costs_on(target_notional)
            units = target_notional / price
            self.cash -= target_notional + fee + slip
            collateral = 0.0
        else:
            collateral = perps.required_collateral(target_notional, self.cfg.leverage)
            if collateral + fee + slip > self.cash:
                # Scale down to what the free cash supports.
                cost_rate = (
                    1.0 / self.cfg.leverage
                    + (self.cfg.costs.perp_base_fee_bps + self.cfg.costs.slippage_bps)
                    / 10_000.0
                )
                target_notional = max(self.cash / cost_rate, 0.0)
                if target_notional <= 0:
                    return
                fee, slip = self._costs_on(target_notional)
                collateral = perps.required_collateral(
                    target_notional, self.cfg.leverage
                )
                units = target_notional / price
            units = target_notional / price
            self.cash -= collateral + fee + slip

        self.pos = Position(
            side=side,
            units=units if side is Side.LONG else -units,
            entry_price=price,
            collateral=collateral,
            opened_ts=ts,
            opened_index=index,
            accrued_borrow_fee=0.0,
            entry_costs=fee + slip,
        )

        # Gross book: same notional, no costs.
        gross_units = target_notional / price
        self.gross_units = gross_units if side is Side.LONG else -gross_units
        self.gross_cash -= self.gross_units * price

        self.trades.append(
            Trade(
                ts=ts,
                bar_index=index,
                side=str(side),
                price=price,
                units=self.pos.units,
                notional=target_notional,
                fee=fee,
                slippage=slip,
                borrow_fee_settled=0.0,
                realized_pnl=0.0,
                equity_after=self.equity(price),
                reason="open",
            )
        )


def _resolve_target(raw: float, mode: Mode, allow_short: bool) -> float:
    """Clamp a strategy's raw target exposure to what the mode permits."""
    if not np.isfinite(raw):
        raise ValueError(f"strategy returned a non-finite exposure: {raw!r}")
    lo = -1.0 if (allow_short and mode is Mode.PERP) else 0.0
    return float(min(max(raw, lo), 1.0))


def run_backtest(
    strategy: Strategy,
    arrays: dict[str, np.ndarray],
    config: EngineConfig,
    *,
    close_at_end: bool = True,
    price_only: bool = False,
    continuation: dict | None = None,
) -> BacktestResult:
    """Run one strategy over one price series.

    See the module docstring for the per-bar ordering that prevents look-ahead.
    """
    config.validate()
    if type(close_at_end) is not bool or type(price_only) is not bool:
        raise ValueError("prefix options must be boolean")
    arrays = validate_bar_arrays(
        arrays, config.interval, require_open_volume=not price_only
    )
    if "open" not in arrays:
        raise ValueError("next-open execution requires observed open prices")
    binding = repr((strategy.name, strategy.params, asdict(config)))
    start = offset = 0
    totals = {"fees_paid": 0.0, "slippage_paid": 0.0, "borrow_paid": 0.0, "realized_pnl": 0.0}
    if continuation is not None:
        if not hasattr(strategy, "restore_state"):
            raise ValueError("strategy does not support continuation")
        if continuation["binding"] != binding:
            raise ValueError("continuation configuration changed")
        if int(arrays["ts"][0]) != continuation["last_ts"] + INTERVAL_SECONDS[config.interval]:
            raise ValueError("continuation source gap")
        start = len(continuation["tail"]["ts"])
        offset = continuation["cursor"] - start
        arrays = {k: np.concatenate((np.asarray(continuation["tail"][k]), v)) for k, v in arrays.items()}
        strategy.restore_state(continuation["strategy_state"])
        totals = continuation["totals"]
    ts = arrays["ts"]
    op, hi, lo, cl, vol = (
        arrays["open"],
        arrays["high"],
        arrays["low"],
        arrays["close"],
        arrays.get("volume"),
    )
    n = len(cl)
    if n == 0:
        raise ValueError("cannot backtest an empty series")

    warmup = strategy.warmup_bars()
    if isinstance(warmup, bool) or not isinstance(warmup, Integral) or warmup < 0:
        raise ValueError("strategy warmup_bars must be a nonnegative integer")
    if warmup >= n and close_at_end:
        raise ValueError(
            f"strategy '{strategy.name}' needs {warmup} warmup bars but the "
            f"series has only {n}; widen the date range or shorten the lookback"
        )

    book = _Book(config)
    ppy = periods_per_year(config.interval)
    hpb = hours_per_bar(config.interval)
    is_perp = config.mode is Mode.PERP

    equity_curve = np.empty(n, dtype="float64")
    gross_curve = np.empty(n, dtype="float64")
    exposure_curve = np.zeros(n, dtype="float64")

    pending: dict[int, float] = {}
    first_tradeable = warmup
    if continuation is not None:
        for key in ("cash", "gross_cash", "gross_units", "liquidations"):
            setattr(book, key, continuation["book"][key])
        position = dict(continuation["position"])
        position["side"] = Side(position["side"])
        book.pos = Position(**position)
        if book.pos.is_open:
            book.pos.opened_index -= offset
        pending = {int(k) - offset: v for k, v in continuation["pending"].items()}

    # Coverage of each coarse bar by each finer layer, computed once. A bar is
    # refined by the FIRST (finest) layer that covers it completely.
    layers = list(config.intrabar) if is_perp else []
    layer_of = None
    lo_idx: list[np.ndarray] = []
    hi_idx: list[np.ndarray] = []
    refined = unrefined = mismatched = 0
    if layers:
        span = INTERVAL_SECONDS[config.interval]
        layer_of = np.full(n, -1, dtype="int64")
        for k, lay in enumerate(layers):
            a_ix = np.searchsorted(lay.ts, ts, side="left")
            b_ix = np.searchsorted(lay.ts, ts + span, side="left")
            lo_idx.append(a_ix)
            hi_idx.append(b_ix)
            expected = span // lay.seconds
            full = (b_ix - a_ix) == expected
            # IntrabarLayer permits gaps. A matching count alone can hide a
            # shifted last candle that closes after this coarse decision.
            for i in np.flatnonzero(full):
                grid = ts[i] + np.arange(expected, dtype="int64") * lay.seconds
                full[i] = span % lay.seconds == 0 and np.array_equal(
                    lay.ts[a_ix[i] : b_ix[i]], grid
                )
            layer_of = np.where((layer_of < 0) & full, k, layer_of)

    for i in range(start, n):
        # A gap can breach the OLD position before any queued exit or rebalance
        # releases collateral. Only fees through the prior boundary are due here.
        if is_perp and book.pos.is_open:
            liq = perps.liquidation_price(
                book.pos.entry_price,
                book.pos.side,
                book.pos.collateral,
                book.pos.entry_notional,
                book.pos.accrued_borrow_fee,
                config.costs,
            )
            if perps.is_liquidated(book.pos.side, liq, op[i], op[i]):
                _liquidate(book, config, liq, op[i], op[i], int(ts[i]), i)

        # -- 1. execute open-price fills before this bar starts accruing --
        if i in pending:
            _apply_target(book, pending.pop(i), op[i], ts[i], i, config)

        # -- 2/3. accrue borrow fees and check liquidation ------------------
        # A close at OPEN owes no new interval; an entry at OPEN owes this one.
        # A fill_delay=0 entry happens later at CLOSE and starts accruing next bar.
        if is_perp and book.pos.is_open:
            layer_k = int(layer_of[i]) if layer_of is not None else -1
            if layer_k >= 0:
                lay = layers[layer_k]
                a, b = int(lo_idx[layer_k][i]), int(hi_idx[layer_k][i])
                _liquidated, mismatch = _walk_fine_bar(
                    book,
                    config,
                    lay,
                    a,
                    b,
                    lo[i],
                    hi[i],
                    op[i],
                    cl[i],
                    i,
                )
                refined += 1
                mismatched += int(mismatch)
            else:
                if layers:
                    unrefined += 1
                book.pos.accrued_borrow_fee += perps.accrue_borrow_fee(
                    config.costs,
                    book.pos.side,
                    book.pos.entry_notional,
                    hpb,
                )
                liq = perps.liquidation_price(
                    book.pos.entry_price,
                    book.pos.side,
                    book.pos.collateral,
                    book.pos.entry_notional,
                    book.pos.accrued_borrow_fee,
                    config.costs,
                )
                if perps.is_liquidated(book.pos.side, liq, lo[i], hi[i]):
                    _liquidate(book, config, liq, op[i], cl[i], int(ts[i]), i)
            # Re-entry semantics after a liquidation: the strategy is asked
            # for a fresh target at step 4 of this same bar, so a strategy
            # that still wants exposure re-enters on the next fill. That is
            # deliberate -- a liquidation is not a signal, and suppressing
            # re-entry would silently impose a cooldown the strategy never
            # asked for. Model a cooldown inside the strategy if you want
            # one. Any target queued by an EARLIER bar and not yet filled
            # is left in place for the same reason.

        # -- 4. strategy decision, from data <= i only --------------------
        target: float | None = None
        if i + offset >= warmup:
            window = BarWindow(ts, op, hi, lo, cl, vol, i)
            target = _resolve_target(
                strategy.on_bar(window), config.mode, config.allow_short
            )

        # -- 5. schedule or execute the resulting order -------------------
        if target is not None:
            if config.fill_delay == 0:
                _apply_target(book, target, cl[i], int(ts[i]), i, config)
            elif not close_at_end or i + config.fill_delay < n:
                pending[i + config.fill_delay] = target

        # -- 6. mark to market -------------------------------------------
        # Margin is isolated per position, so a trader cannot lose more than
        # the collateral posted. Floor at zero: negative equity is unphysical
        # here and would poison CAGR and drawdown with a sign flip.
        equity_curve[i] = max(0.0, book.equity(cl[i]))
        gross_curve[i] = book.gross_equity(cl[i])
        eq = equity_curve[i]
        exposure_curve[i] = book.signed_notional(cl[i]) / eq if eq > 1e-12 else 0.0

    # Close any open position at the final close so metrics see realised PnL.
    if close_at_end and book.pos.is_open:
        book.close(cl[-1], int(ts[-1]), n - 1, reason="final")
        equity_curve[-1] = max(0.0, book.equity(cl[-1]))
        gross_curve[-1] = book.gross_equity(cl[-1])

    for trade in book.trades:
        trade.bar_index += offset
    if book.pos.is_open:
        book.pos.opened_index += offset
    totals = dict(totals)
    for trade in book.trades:
        for key, attr in (("fees_paid", "fee"), ("slippage_paid", "slippage"),
                          ("borrow_paid", "borrow_fee_settled"), ("realized_pnl", "realized_pnl")):
            totals[key] += getattr(trade, attr)
    tail_size = strategy.warmup_bars() + 1
    state = {
        "schema_version": 1, "binding": binding, "cursor": offset + n, "last_ts": int(ts[-1]),
        "tail": {k: v[-tail_size:].tolist() for k, v in arrays.items()},
        "strategy_state": strategy.checkpoint_state() if hasattr(strategy, "checkpoint_state") else None,
        "book": {k: getattr(book, k) for k in ("cash", "gross_cash", "gross_units", "liquidations")},
        "position": asdict(book.pos), "pending": {k + offset: v for k, v in pending.items() if k >= n},
        "totals": totals,
    }
    import json
    state = json.loads(json.dumps(state, default=lambda value: value.item())) if hasattr(strategy, "checkpoint_state") else None
    ts, equity_curve, gross_curve, exposure_curve = (x[start:] for x in (ts, equity_curve, gross_curve, exposure_curve))
    net = compute_metrics(
        equity_curve,
        ts,
        book.trades,
        exposure_curve,
        ppy,
        config.risk_free_rate,
        book.liquidations,
        initial_equity=config.initial_capital,
    )
    gross = compute_metrics(
        gross_curve,
        ts,
        [],
        exposure_curve,
        ppy,
        config.risk_free_rate,
        0,
        initial_equity=config.initial_capital,
    )

    return BacktestResult(
        continuation=state,
        strategy_name=strategy.name,
        params=dict(strategy.params),
        timestamps=ts,
        equity=equity_curve,
        exposure=exposure_curve,
        trades=book.trades,
        metrics=net,
        gross_metrics=gross,
        liquidation_count=book.liquidations,
        first_tradeable_index=first_tradeable,
        mode=str(config.mode),
        leverage=config.leverage,
        account=AccountState(
            cash=book.cash,
            position=book.pos,
            pending_targets={k + offset: v for k, v in pending.items() if k >= n}
            if not close_at_end
            else {},
            fees_paid=totals["fees_paid"],
            slippage_paid=totals["slippage_paid"],
            borrow_paid=totals["borrow_paid"],
            realized_pnl=totals["realized_pnl"],
        ),
        bars_refined=refined,
        bars_unrefined=unrefined,
        bars_range_mismatch=mismatched,
    )


def _liquidate(
    book, config, liq, open_px, close_px, ts, index, *, fine_open=None, fine_close=None
):
    """Close the book at the liquidation fill, penalty applied adversely.

    If the bar GAPPED through the level the fill is roughly the open, not a
    level that never traded; SOL has gapped >20% in a day and assuming the
    better price would flatter every leveraged result. A position already below
    maintenance has no meaningful level, so it fills at the close.
    """
    o = open_px if fine_open is None else fine_open
    c = close_px if fine_close is None else fine_close
    side = book.pos.side
    if not liq.in_domain:
        fill = c
    elif side is Side.LONG:
        fill = min(liq.price, o)
    else:
        fill = max(liq.price, o)
    pen = config.costs.liquidation_penalty_bps / 10_000.0
    fill = fill * (1.0 - pen) if side is Side.LONG else fill * (1.0 + pen)
    book.close(
        fill,
        ts,
        index,
        reason="liquidation",
        forfeit=config.costs.liquidation_forfeits_collateral,
    )
    book.liquidations += 1


def _walk_fine_bar(book, config, lay, a, b, c_low, c_high, c_open, c_close, index):
    """Accrue and check one coarse bar by walking its finer bars in order.

    Returns (liquidated, range_mismatch). Fees accrue to the end of each fine
    bar, so the liquidation price drifts toward spot exactly as time passes.
    A cheap pre-screen skips the walk when even the END-of-bar liquidation
    price (the most severe, since fees only accumulate) is not touched by the
    widest of the coarse and fine ranges; it never changes the outcome.
    """
    costs = config.costs
    pos = book.pos
    side = pos.side
    hours = lay.seconds / 3600.0
    fine_low = float(lay.low[a:b].min())
    fine_high = float(lay.high[a:b].max())
    tol = 5e-4  # 5 bps: coarse and fine feeds round differently
    mismatch = (
        (c_low < fine_low * (1 - tol))
        if side is Side.LONG
        else (c_high > fine_high * (1 + tol))
    )
    wide_low, wide_high = min(c_low, fine_low), max(c_high, fine_high)

    n_fine = b - a
    end_fee = pos.accrued_borrow_fee + perps.accrue_borrow_fee(
        costs,
        side,
        pos.entry_notional,
        hours * n_fine,
    )
    liq_end = perps.liquidation_price(
        pos.entry_price,
        side,
        pos.collateral,
        pos.entry_notional,
        end_fee,
        costs,
    )
    if not perps.is_liquidated(side, liq_end, wide_low, wide_high):
        pos.accrued_borrow_fee = end_fee
        return False, mismatch

    for j in range(a, b):
        pos.accrued_borrow_fee += perps.accrue_borrow_fee(
            costs,
            side,
            pos.entry_notional,
            hours,
        )
        liq = perps.liquidation_price(
            pos.entry_price,
            side,
            pos.collateral,
            pos.entry_notional,
            pos.accrued_borrow_fee,
            costs,
        )
        if perps.is_liquidated(side, liq, float(lay.low[j]), float(lay.high[j])):
            _liquidate(
                book,
                config,
                liq,
                c_open,
                c_close,
                int(lay.ts[j]),
                index,
                fine_open=float(lay.open[j]),
                fine_close=float(lay.close[j]),
            )
            return True, mismatch
    # Fine path found nothing. If the coarse range reaches past the fine range,
    # trust the more severe one: a daily low that no hourly bar shows is a data
    # disagreement, and ignoring it would let the cleaner feed rescue the position.
    # Diagnostic rounding tolerance must never suppress a known coarse touch.
    liq = perps.liquidation_price(
        pos.entry_price,
        side,
        pos.collateral,
        pos.entry_notional,
        pos.accrued_borrow_fee,
        costs,
    )
    if perps.is_liquidated(side, liq, c_low, c_high):
        _liquidate(book, config, liq, c_open, c_close, int(lay.ts[b - 1]), index)
        return True, mismatch
    return False, mismatch


def _apply_target(
    book: _Book,
    target: float,
    price: float,
    ts: int,
    index: int,
    config: EngineConfig,
) -> None:
    """Move the book toward `target` exposure at `price`.

    Sizing rule: target exposure `e` means notional of
    `|e| * current_equity * leverage`, marked at the fill price -- current
    equity, not initial capital, so the strategy compounds. A rebalance only
    fires when the gap exceeds `rebalance_threshold` as a fraction of equity,
    which makes fee drag from trivial rebalances a visible parameter.
    """
    equity = book.equity(price)
    if equity <= 0:
        # Account is wiped out; there is nothing left to allocate.
        if book.pos.is_open:
            book.close(price, ts, index, reason="wipeout")
        return

    desired_side = Side.FLAT
    if target > 0:
        desired_side = Side.LONG
    elif target < 0:
        desired_side = Side.SHORT

    target_notional = abs(target) * equity * config.leverage
    current_signed = book.signed_notional(price)
    desired_signed = target_notional * (1.0 if desired_side is Side.LONG else -1.0)
    if desired_side is Side.FLAT:
        desired_signed = 0.0

    gap = abs(desired_signed - current_signed) / equity
    threshold = max(config.rebalance_threshold, 1e-12)
    if gap <= threshold:
        return

    # Any change of side, or a move to flat, closes first.
    if book.pos.is_open and (
        desired_side is Side.FLAT or desired_side is not book.pos.side
    ):
        book.close(price, ts, index, reason="signal")

    if desired_side is Side.FLAT:
        return

    if book.pos.is_open:
        # Same side, still open: adjust incrementally and pay cost on the size
        # change only. See _Book.resize -- this is what the venue actually does.
        book.resize(target_notional, price, ts, index)
        return

    book.open(target_notional, desired_side, price, ts, index)


def rebind_signal_state(state, strategy, config):
    """Reconfigure a flat signal book only when retained observed history suffices."""
    import copy

    config.validate()
    if (state.get("schema_version") != 1 or state["position"]["units"] != 0
            or any(target != 0 for target in state["pending"].values())):
        raise ValueError("signal configuration adoption requires flat exposure without pending entries")
    needed = min(state["cursor"], strategy.warmup_bars() + 1)
    if len(state["tail"]["ts"]) < needed:
        raise ValueError("new signal warmup exceeds retained observed history")
    result = copy.deepcopy(state)
    result["binding"] = repr((strategy.name, strategy.params, asdict(config)))
    result["tail"] = {k: v[-needed:] for k, v in state["tail"].items()}
    # At a flat adoption boundary the new strategy begins with no held signal.
    # Its first new observed bar computes indicators from the retained prices.
    result["strategy_state"] = strategy.checkpoint_state()
    return result
