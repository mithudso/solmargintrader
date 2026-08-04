"""Event-driven backtest engine.

Bar ordering inside the loop is the whole correctness story:

    1. accrue borrow fees for the elapsed bar        (perp only)
    2. execute any fill scheduled for this bar       at this bar's OPEN
    3. liquidation check against this bar's low/high (perp only)
    4. ask the strategy for a target, given data <= i only
    5. schedule that target for bar i + fill_delay   (or fill at close if 0)
    6. mark to market at this bar's close and record

The strategy is consulted at step 4 with a BarWindow that cannot read past
bar i, and the resulting order is filled at step 2 of a LATER bar. There is no
code path by which a decision uses a price it could not have observed.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

import numpy as np

from . import perps
from .metrics import Metrics, compute_metrics
from .types import (
    BarWindow,
    CostConfig,
    Mode,
    Position,
    Side,
    Trade,
    hours_per_bar,
    periods_per_year,
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

    def __post_init__(self) -> None:
        """Validate settings that would otherwise fail deep in the loop."""
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.fill_delay < 0:
            raise ValueError("fill_delay cannot be negative")
        if self.leverage <= 0:
            raise ValueError("leverage must be positive")
        if self.mode is Mode.SPOT and self.leverage != 1.0:
            raise ValueError(
                "spot mode does not borrow; use --mode perp for leverage > 1"
            )
        if self.rebalance_threshold < 0:
            raise ValueError("rebalance_threshold cannot be negative")
        if self.allow_short and self.mode is Mode.SPOT:
            # Silently clamping to long-only would hide a contradictory config.
            warnings.warn(
                "allow_short has no effect in spot mode; short exposure is "
                "clamped to 0. Pass mode='perp' to trade short.",
                UserWarning,
                stacklevel=2,
            )


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
        self, price: float, ts: int, index: int, reason: str
    ) -> None:
        """Close the whole position at `price`, settling fees and borrow."""
        if not self.pos.is_open:
            return
        notional = self.pos.notional_at(price)
        fee, slip = self._costs_on(notional)
        borrow = self.pos.accrued_borrow_fee
        price_pnl = self.pos.unrealized_pnl(price)

        if self.cfg.mode is Mode.SPOT:
            self.cash += self.pos.units * price - fee - slip
        else:
            self.cash += self.pos.collateral + price_pnl - borrow - fee - slip

        realized = price_pnl - borrow - fee - slip
        units_closed = self.pos.units
        self.pos = Position()

        # Mirror the decision in the gross book at zero cost.
        self.gross_cash += self.gross_units * price
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

    def resize(
        self, target_notional: float, price: float, ts: int, index: int
    ) -> None:
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
            # -- increase: merge at a blended average entry price ----------
            if self.cfg.mode is Mode.SPOT:
                if delta_notional + fee + slip > self.cash:
                    return
                self.cash -= delta_notional + fee + slip
            else:
                add_collateral = delta_notional / self.cfg.leverage
                if add_collateral + fee + slip > self.cash:
                    return
                self.cash -= add_collateral + fee + slip
                self.pos.collateral += add_collateral
            new_units = cur_units + delta_units
            self.pos.entry_price = (
                cur_units * self.pos.entry_price + delta_units * price
            ) / new_units
            self.pos.units = new_units * direction
            realized = -(fee + slip)
            borrow_settled = 0.0
            self.gross_cash -= delta_notional
            self.gross_units += delta_units * direction
        else:
            # -- decrease: realise PnL and a proportional share of borrow ---
            frac = min(delta_units / cur_units, 1.0)
            price_pnl = direction * (price - self.pos.entry_price) * delta_units
            borrow_settled = self.pos.accrued_borrow_fee * frac
            self.pos.accrued_borrow_fee -= borrow_settled
            if self.cfg.mode is Mode.SPOT:
                self.cash += delta_units * price - fee - slip
            else:
                released = self.pos.collateral * frac
                self.pos.collateral -= released
                self.cash += released + price_pnl - borrow_settled - fee - slip
            new_units = cur_units - delta_units
            self.pos.units = new_units * direction
            realized = price_pnl - borrow_settled - fee - slip
            self.gross_cash += delta_units * price
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


def _resolve_target(
    raw: float, mode: Mode, allow_short: bool
) -> float:
    """Clamp a strategy's raw target exposure to what the mode permits."""
    if not np.isfinite(raw):
        raise ValueError(f"strategy returned a non-finite exposure: {raw!r}")
    lo = -1.0 if (allow_short and mode is Mode.PERP) else 0.0
    return float(min(max(raw, lo), 1.0))


def run_backtest(
    strategy: Strategy,
    arrays: dict[str, np.ndarray],
    config: EngineConfig,
) -> BacktestResult:
    """Run one strategy over one price series.

    See the module docstring for the per-bar ordering that prevents look-ahead.
    """
    ts = arrays["ts"]
    op, hi, lo, cl, vol = (
        arrays["open"],
        arrays["high"],
        arrays["low"],
        arrays["close"],
        arrays["volume"],
    )
    n = len(cl)
    if n == 0:
        raise ValueError("cannot backtest an empty series")

    warmup = max(0, int(strategy.warmup_bars()))
    if warmup >= n:
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

    for i in range(n):
        # -- 1. borrow-fee accrual for the bar just elapsed ---------------
        if is_perp and book.pos.is_open:
            book.pos.accrued_borrow_fee += perps.accrue_borrow_fee(
                config.costs,
                book.pos.side,
                book.pos.entry_notional,
                hpb,
            )

        # -- 2. execute a fill scheduled for this bar, at this bar's open --
        if i in pending:
            _apply_target(book, pending.pop(i), op[i], ts[i], i, config)

        # -- 3. liquidation check on this bar's range ----------------------
        if is_perp and book.pos.is_open:
            liq = perps.liquidation_price(
                book.pos.entry_price,
                book.pos.side,
                book.pos.collateral,
                book.pos.entry_notional,
                book.pos.accrued_borrow_fee,
                config.costs,
            )
            if perps.is_liquidated(book.pos.side, liq, lo[i], hi[i]):
                # If the bar GAPPED through the level, the liquidation happens
                # at roughly the open, not at a level that never traded. SOL has
                # gapped >20% in a day; assuming the better price would flatter
                # every leveraged result.
                if not liq.in_domain:
                    fill = cl[i]
                elif book.pos.side is Side.LONG:
                    fill = min(liq.price, op[i])
                else:
                    fill = max(liq.price, op[i])
                book.close(fill, int(ts[i]), i, reason="liquidation")
                book.liquidations += 1
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
        if i >= warmup:
            window = BarWindow(ts, op, hi, lo, cl, vol, i)
            target = _resolve_target(
                strategy.on_bar(window), config.mode, config.allow_short
            )

        # -- 5. schedule or execute the resulting order -------------------
        if target is not None:
            if config.fill_delay == 0:
                _apply_target(book, target, cl[i], int(ts[i]), i, config)
            elif i + config.fill_delay < n:
                pending[i + config.fill_delay] = target

        # -- 6. mark to market -------------------------------------------
        # Margin is isolated per position, so a trader cannot lose more than
        # the collateral posted. Floor at zero: negative equity is unphysical
        # here and would poison CAGR and drawdown with a sign flip.
        equity_curve[i] = max(0.0, book.equity(cl[i]))
        gross_curve[i] = book.gross_equity(cl[i])
        eq = equity_curve[i]
        exposure_curve[i] = (
            book.signed_notional(cl[i]) / eq if eq > 1e-12 else 0.0
        )

    # Close any open position at the final close so metrics see realised PnL.
    if book.pos.is_open:
        book.close(cl[-1], int(ts[-1]), n - 1, reason="final")
        equity_curve[-1] = max(0.0, book.equity(cl[-1]))
        gross_curve[-1] = book.gross_equity(cl[-1])

    net = compute_metrics(
        equity_curve,
        ts,
        book.trades,
        exposure_curve,
        ppy,
        config.risk_free_rate,
        book.liquidations,
    )
    gross = compute_metrics(
        gross_curve, ts, [], exposure_curve, ppy, config.risk_free_rate, 0
    )

    return BacktestResult(
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
    )


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
