"""DCA (dollar-cost averaging) safety-order bot simulator.

This is the "DCA bot" of the 3Commas / Pionex kind, not the periodic-purchase
`dca` exposure strategy in `strategies/textbook.py`. A deal works like this:

    1. a **base order** buys at market;
    2. a ladder of **safety orders** rests below the base fill, each one deeper
       and (optionally) larger than the last, so every fill drags the average
       entry price down;
    3. one **take-profit** order rests a fixed percentage above the *average*
       entry and sells the whole position; the deal closes and a new one starts.

An optional stop loss below the average entry closes a deal at a loss. Without
one, a falling market fills every safety order and then simply holds the bag;
that is the strategy's dominant failure mode, and this simulator reports it
(`open_deal_at_end`, `max_safety_used`) instead of hiding it.

Like `core/gridsim.py` this owns its own bar loop rather than being a
`Strategy`: its edge, such as it is, comes from resting limit orders that fill
intrabar at known prices, which a target-exposure engine cannot express.

Bar ordering, which is the whole correctness story (it mirrors gridsim):

    1. fill a queued MARKET order (base order or stop-loss exit) at this bar's open
    2. fill resting safety-order BUYS against this bar's low, highest level first
    3. fill the resting take-profit SELL against this bar's high
    4. mark to market at this bar's close
    5. plan from the close (orders become fillable NEXT bar)

The pessimism conventions, each of which an optimistic simulator gets wrong:

* **Nothing fills on the bar that placed it.** A market order queued at the
  close of bar *i* fills at the open of bar *i+1*; a limit order placed at the
  close of bar *i* is first eligible on bar *i+1*. This is the structural
  no-lookahead guard: a decision at bar *t* reads data through bar *t* only.
* **A bar that filled a buy cannot also fill the take-profit.** Within one bar
  we know OHLC, not the path, so "it dipped to the safety order and then rallied
  to the take-profit" is an assumption, not an observation. The take-profit is
  re-planned from the new average at the close and is eligible next bar.
* **Fills are adverse.** A buy fills at its price moved *up* by the slippage
  allowance and a sell *down* by it; the taker fee is charged on every fill.
* **Buys spend first.** A safety order that cash cannot fund is skipped and
  counted, never partially or magically filled.

Costs are never optional: fee and slippage stay in the P&L path, and the
buy-and-hold baseline pays its own entry costs.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from numbers import Real
from typing import Any

import numpy as np

from .continuation import configuration_binding
from .metrics import Metrics, compute_metrics
from .types import (
    INTERVAL_SECONDS,
    CostConfig,
    Trade,
    periods_per_year,
    validate_bar_arrays,
)

VENUE_MIN_ORDER_USD = 10.0
MAX_SAFETY_ORDERS = 50


def _finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


@dataclass(frozen=True)
class DcaConfig:
    """One DCA bot. Percentages are percent (1.5 = 1.5%), not fractions."""

    base_order_usd: float = 100.0
    safety_order_usd: float = 100.0
    max_safety_orders: int = 5
    price_deviation_pct: float = 2.0
    step_scale: float = 1.0
    volume_scale: float = 1.0
    take_profit_pct: float = 2.0
    stop_loss_pct: float = 0.0
    cooldown_bars: int = 0
    min_order_usd: float = VENUE_MIN_ORDER_USD

    def __post_init__(self) -> None:
        """Refuse a bot that cannot be built, naming the offending value."""
        for name in ("base_order_usd", "safety_order_usd", "price_deviation_pct", "step_scale",
                     "volume_scale", "take_profit_pct", "stop_loss_pct", "min_order_usd"):
            _finite(name, getattr(self, name))
        for name in ("max_safety_orders", "cooldown_bars"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")  # noqa: TRY004 -- retain public validation contract
        if not 0 <= self.max_safety_orders <= MAX_SAFETY_ORDERS:
            raise ValueError(f"max_safety_orders must be in [0, {MAX_SAFETY_ORDERS}]")
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars cannot be negative")
        if self.min_order_usd < 0:
            raise ValueError("min_order_usd cannot be negative")
        if self.base_order_usd < max(self.min_order_usd, 1e-9):
            raise ValueError(
                f"base_order_usd ({self.base_order_usd}) is below the venue minimum ({self.min_order_usd})"
            )
        if self.max_safety_orders and self.safety_order_usd < max(self.min_order_usd, 1e-9):
            raise ValueError(
                f"safety_order_usd ({self.safety_order_usd}) is below the venue minimum ({self.min_order_usd})"
            )
        if not self.price_deviation_pct > 0:
            raise ValueError("price_deviation_pct must be > 0")
        if not self.step_scale > 0 or not self.volume_scale > 0:
            raise ValueError("step_scale and volume_scale must be > 0")
        if not self.take_profit_pct > 0:
            raise ValueError("take_profit_pct must be > 0")
        if not 0 <= self.stop_loss_pct < 100:
            raise ValueError("stop_loss_pct must be in [0, 100); 0 disables it")
        deviations = safety_deviations_pct(self)
        if deviations and deviations[-1] >= 100.0:
            raise ValueError(
                f"the deepest safety order sits {deviations[-1]:.2f}% below the base fill; "
                "it must be under 100% or its price is not positive"
            )

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict form for manifests and the TUI."""
        return {
            "base_order_usd": self.base_order_usd,
            "safety_order_usd": self.safety_order_usd,
            "max_safety_orders": self.max_safety_orders,
            "price_deviation_pct": self.price_deviation_pct,
            "step_scale": self.step_scale,
            "volume_scale": self.volume_scale,
            "take_profit_pct": self.take_profit_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "cooldown_bars": self.cooldown_bars,
            "min_order_usd": self.min_order_usd,
        }


def safety_deviations_pct(cfg: DcaConfig) -> list[float]:
    """Cumulative percentage below the base fill at which each safety order rests.

    The first sits `price_deviation_pct` below; each later step is the previous
    step times `step_scale`, so step_scale > 1 spaces the deeper orders wider.
    """
    out: list[float] = []
    step, depth = cfg.price_deviation_pct, 0.0
    for _ in range(cfg.max_safety_orders):
        depth += step
        out.append(depth)
        step *= cfg.step_scale
    return out


def safety_sizes_usd(cfg: DcaConfig) -> list[float]:
    """USD size of each safety order: the first is `safety_order_usd`, then x volume_scale each."""
    return [cfg.safety_order_usd * cfg.volume_scale ** k for k in range(cfg.max_safety_orders)]


def capital_required_usd(cfg: DcaConfig) -> float:
    """Cash a deal needs to fill its base order and every safety order."""
    return cfg.base_order_usd + sum(safety_sizes_usd(cfg))


def plan_deal(cfg: DcaConfig, base_price: float, fee_bps: float = 0.0) -> dict[str, Any]:
    """What the bot sets at a base fill of `base_price`: every safety level and size, and the
    take-profit after the base order alone and after each further safety fill.

    This is the "what would it have set at that moment" view. It is pure arithmetic on the
    config; the backtest adds slippage and fees on top.
    """
    _finite("base_price", base_price)
    if base_price <= 0:
        raise ValueError("base_price must be positive")
    rows = []
    spent = cfg.base_order_usd
    qty = cfg.base_order_usd / base_price
    rows.append({"order": "base", "price": base_price, "usd": cfg.base_order_usd,
                 "deviation_pct": 0.0, "avg_entry": base_price,
                 "take_profit": base_price * (1 + cfg.take_profit_pct / 100.0), "cum_usd": spent})
    for k, (dev, usd) in enumerate(zip(safety_deviations_pct(cfg), safety_sizes_usd(cfg)), start=1):
        price = base_price * (1 - dev / 100.0)
        spent += usd
        qty += usd / price
        avg = spent / qty
        rows.append({"order": f"safety {k}", "price": price, "usd": usd, "deviation_pct": dev,
                     "avg_entry": avg, "take_profit": avg * (1 + cfg.take_profit_pct / 100.0),
                     "cum_usd": spent})
    return {"base_price": base_price, "capital_required_usd": capital_required_usd(cfg),
            "orders": rows, "fee_bps": fee_bps}


@dataclass
class DcaRunResult:
    """Everything one DCA bot run produced."""

    config: dict[str, Any]
    metrics: Metrics
    baseline_metrics: Metrics
    timestamps: np.ndarray
    equity: np.ndarray
    exposure: np.ndarray
    baseline_equity: np.ndarray
    trades: list[Trade]
    capital_required_usd: float
    deals_completed: int
    deals_stopped: int
    safety_orders_filled: int
    max_safety_used: int
    realized_pnl_usd: float
    fees_paid_usd: float
    slippage_paid_usd: float
    open_deal_at_end: dict[str, Any] | None
    forced_exit_qty: float
    avg_deal_bars: float
    skipped: dict[str, int]
    first_plan: dict[str, Any] | None
    continuation: dict | None = None

    def summary(self) -> dict[str, Any]:
        """JSON-ready digest (no arrays)."""
        m, b = self.metrics, self.baseline_metrics
        return {
            "config": self.config,
            "capital_required_usd": self.capital_required_usd,
            "deals_completed": self.deals_completed,
            "deals_stopped": self.deals_stopped,
            "safety_orders_filled": self.safety_orders_filled,
            "max_safety_used": self.max_safety_used,
            "realized_pnl_usd": self.realized_pnl_usd,
            "fees_paid_usd": self.fees_paid_usd,
            "slippage_paid_usd": self.slippage_paid_usd,
            "open_deal_at_end": self.open_deal_at_end,
            "forced_exit_qty": self.forced_exit_qty,
            "avg_deal_bars": self.avg_deal_bars,
            "skipped": self.skipped,
            "total_return": m.total_return,
            "sharpe": m.sharpe,
            "max_drawdown": m.max_drawdown,
            "final_equity": m.final_equity,
            "hold_total_return": b.total_return,
            "hold_max_drawdown": b.max_drawdown,
            "bars": m.bars,
        }

    def summary_lines(self) -> list[str]:
        """Human-readable digest. Kept here so the CLI stays a thin adapter."""
        m, b = self.metrics, self.baseline_metrics
        open_deal = self.open_deal_at_end
        return [
            f"capital required     ${self.capital_required_usd:,.2f} per deal",
            f"deals                {self.deals_completed} took profit, {self.deals_stopped} stopped out",
            f"safety orders        {self.safety_orders_filled} filled (deepest used: {self.max_safety_used})",
            f"realized P&L         ${self.realized_pnl_usd:,.2f}",
            (f"fees + slippage      ${self.fees_paid_usd + self.slippage_paid_usd:,.2f}"
            f"  (fees ${self.fees_paid_usd:,.2f}, slippage ${self.slippage_paid_usd:,.2f})"),
            "open deal at end     " + ("none" if not open_deal else
                                       f"{open_deal['qty']:,.6f} base at avg ${open_deal['avg_entry']:,.4f}, "
                                       f"{open_deal['safety_filled']} safety orders, force-closed"),
            (f"bot    total return  {m.total_return * 100:,.2f}%   Sharpe {m.sharpe:,.2f}   "
            f"maxDD {m.max_drawdown * 100:,.2f}%   final ${m.final_equity:,.2f}"),
            (f"hold   total return  {b.total_return * 100:,.2f}%   Sharpe {b.sharpe:,.2f}   "
            f"maxDD {b.max_drawdown * 100:,.2f}%   final ${b.final_equity:,.2f}"),
        ]


def _baseline_equity(closes: np.ndarray, initial_capital: float, costs: CostConfig) -> np.ndarray:
    """Buy-and-hold on the same bars, paying entry costs once (same convention as gridsim)."""
    c = (costs.fee_bps + costs.slippage_bps) / 10_000.0
    return (initial_capital / (1.0 + c)) / closes[0] * closes.astype("float64")


class _Deal:
    """The open deal: its lots in aggregate and its resting orders."""

    def __init__(self, base_price: float, start_index: int) -> None:
        self.base_price = base_price
        self.start_index = start_index
        self.qty = 0.0
        self.cost_usd = 0.0  # cash spent including fees, the basis realized P&L is measured from
        self.notional_usd = 0.0  # cash spent excluding fees, the basis the take-profit is measured from
        self.safety_filled = 0
        # Resting safety orders: (level, usd, k, planned_index).
        self.safety: list[tuple[float, float, int, int]] = []
        self.tp_level: float | None = None
        self.tp_planned_index = -1

    @property
    def avg_entry(self) -> float:
        return self.notional_usd / self.qty if self.qty > 0 else math.nan


def run_dca_backtest(
    cfg: DcaConfig,
    arrays: dict[str, np.ndarray],
    *,
    initial_capital: float | None = None,
    interval: str = "1h",
    costs: CostConfig | None = None,
    risk_free_rate: float = 0.0,
    close_at_end: bool = True,
    continuation: dict | None = None,
    entries_paused: bool = False,
) -> DcaRunResult:
    """Run one DCA bot over one OHLCV series, starting a deal from the first bar's close.

    `initial_capital` defaults to exactly what one deal needs, fees included. A smaller figure is
    allowed and makes the deeper safety orders unfundable; each skip is counted in `skipped`.
    """
    costs = CostConfig() if costs is None else costs
    if not isinstance(costs, CostConfig):
        raise ValueError("costs must be a CostConfig")  # noqa: TRY004 -- retain public validation contract
    costs.validate()
    if not 0.0 <= costs.slippage_bps < 10_000.0:
        raise ValueError(f"slippage_bps must be in [0, 10000), got {costs.slippage_bps}")
    if costs.fee_bps < 0:
        raise ValueError(f"fee_bps cannot be negative, got {costs.fee_bps}")
    # The default funds every order of one deal plus its taker fee; without the fee headroom
    # the base order alone would be unfundable at any nonzero fee.
    capital = (capital_required_usd(cfg) * (1 + costs.fee_bps / 10_000.0) if initial_capital is None
               else _finite("initial_capital", initial_capital))
    if capital <= 0:
        raise ValueError("initial_capital must be positive")
    _finite("risk_free_rate", risk_free_rate)

    checked = validate_bar_arrays(arrays, interval, require_open_volume=False)
    if "open" not in checked:
        raise ValueError("open prices are required for DCA next-open fills")
    ts, highs, lows, closes = (checked[name] for name in ("ts", "high", "low", "close"))
    opens = checked["open"]
    n = closes.size
    fee = costs.fee_bps / 10_000.0
    slip = costs.slippage_bps / 10_000.0

    cash = capital
    deal: _Deal | None = None
    # The market order queued for the next open: "base" or "exit". Nothing is queued before
    # bar 0's close, because the bot decides on a close and the first decision is that one.
    pending: str | None = None
    pending_index = -1  # the bar whose close queued it
    cooldown_until = -1
    trades: list[Trade] = []
    skipped: Counter = Counter()
    deals_completed = deals_stopped = safety_filled_total = max_safety_used = 0
    realized = fees_paid = slip_paid = 0.0
    deal_lengths: list[int] = []
    first_plan: dict[str, Any] | None = None
    equity = np.empty(n, dtype="float64")
    exposure = np.zeros(n, dtype="float64")

    offset = 0
    length_sum = length_count = 0
    metric_initial_equity = capital
    baseline = _baseline_equity(closes, capital, costs)
    baseline_units = float(baseline[0] / closes[0])
    baseline_initial_equity = capital
    binding = configuration_binding(cfg.to_dict(), capital, interval, costs)
    if continuation is not None:
        if continuation["binding"] != binding:
            raise ValueError("continuation configuration changed")
        offset = continuation["cursor"]
        if int(ts[0]) != continuation["last_ts"] + INTERVAL_SECONDS[interval]:
            raise ValueError("continuation source gap")
        cash, pending, pending_index, cooldown_until = continuation["control"]
        deals_completed, deals_stopped, safety_filled_total, max_safety_used = continuation["counts"]
        realized, fees_paid, slip_paid = continuation["totals"]
        length_sum, length_count = continuation["lengths"]
        first_plan = continuation["first_plan"]
        skipped = Counter(continuation["skipped"])
        if continuation["deal"] is not None:
            deal = _Deal(1, 0)
            deal.__dict__.update(continuation["deal"])
        last_close = continuation.get("last_close")
        baseline_units = continuation.get("baseline_units")
        if any(isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
               for value in (last_close, baseline_units)) or last_close <= 0 or baseline_units < 0:
            raise ValueError("continuation is missing a valid valuation boundary")
        metric_initial_equity = cash + (deal.qty * last_close if deal is not None else 0.0)
        baseline_initial_equity = baseline_units * last_close
        baseline = baseline_units * closes.astype("float64")

    def buy(price_level: float, usd: float, i: int, reason: str) -> bool:
        nonlocal cash, fees_paid, slip_paid
        fill = price_level * (1 + slip)
        fee_usd = usd * fee
        if usd + fee_usd > cash + 1e-9:
            return False
        qty = usd / fill
        cash -= usd + fee_usd
        fees_paid += fee_usd
        slip_paid += qty * (fill - price_level)
        assert deal is not None
        deal.qty += qty
        deal.cost_usd += usd + fee_usd
        deal.notional_usd += usd
        trades.append(Trade(int(ts[i - offset]), i, "buy", fill, qty, usd, fee_usd, qty * (fill - price_level),
                            0.0, 0.0, cash + deal.qty * closes[i - offset], reason))
        return True

    def sell_all(price_level: float, i: int, reason: str) -> float:
        nonlocal cash, fees_paid, slip_paid, realized, deal
        assert deal is not None and deal.qty > 0
        fill = price_level * (1 - slip)
        gross = deal.qty * fill
        fee_usd = gross * fee
        pnl = gross - fee_usd - deal.cost_usd
        cash += gross - fee_usd
        fees_paid += fee_usd
        slip_paid += deal.qty * (price_level - fill)
        realized += pnl
        trades.append(Trade(int(ts[i - offset]), i, "sell", fill, deal.qty, gross, fee_usd,
                            deal.qty * (price_level - fill), 0.0, pnl, cash, reason))
        qty = deal.qty
        deal_lengths.append(i - deal.start_index)
        deal = None
        return qty

    for j in range(n):
        i = j + offset
        bought_this_bar = False

        # -- 1. queued market order at this bar's open ----------------------
        if not entries_paused and pending == "base" and pending_index < i:
            pending = None
            if cash >= cfg.base_order_usd * (1 + fee) - 1e-9:
                deal = _Deal(float(opens[j]), i)
                buy(float(opens[j]), cfg.base_order_usd, i, "open")
                bought_this_bar = True
                if first_plan is None:
                    first_plan = plan_deal(cfg, float(opens[j]), costs.fee_bps)
                for k, (dev, usd) in enumerate(zip(safety_deviations_pct(cfg), safety_sizes_usd(cfg)), start=1):
                    deal.safety.append((deal.base_price * (1 - dev / 100.0), usd, k, i))
            else:
                skipped["base-order-insufficient-cash"] += 1
        elif pending == "exit" and pending_index < i and deal is not None:
            pending = None
            sell_all(float(opens[j]), i, "dca_stop_loss")
            deals_stopped += 1
            cooldown_until = i + cfg.cooldown_bars

        # -- 2. safety orders against the low, highest (shallowest) first ----
        if not entries_paused and deal is not None and deal.safety:
            remaining = []
            for level, usd, k, planned in sorted(deal.safety, key=lambda o: -o[0]):
                if planned < i and lows[j] <= level:
                    if buy(level, usd, i, "resize_up"):
                        deal.safety_filled += 1
                        safety_filled_total += 1
                        max_safety_used = max(max_safety_used, k)
                        bought_this_bar = True
                        continue
                    skipped["safety-order-insufficient-cash"] += 1
                    continue  # unfundable now means unfundable for this deal: drop it
                remaining.append((level, usd, k, planned))
            deal.safety = remaining

        # -- 3. take-profit against the high ---------------------------------
        if (deal is not None and deal.tp_level is not None and not bought_this_bar
                and deal.tp_planned_index < i and highs[j] >= deal.tp_level):
            sell_all(deal.tp_level, i, "dca_take_profit")
            deals_completed += 1
            cooldown_until = i + cfg.cooldown_bars
        elif deal is not None and bought_this_bar and deal.tp_level is not None and highs[j] >= deal.tp_level:
            skipped["take-profit-deferred-same-bar-buy"] += 1

        # -- 4. mark to market ----------------------------------------------
        held = deal.qty if deal is not None else 0.0
        equity[j] = cash + held * closes[j]
        exposure[j] = held * closes[j] / equity[j] if equity[j] > 1e-12 else 0.0

        # -- 5. plan from this close ----------------------------------------
        if deal is not None:
            deal.tp_level = deal.avg_entry * (1 + cfg.take_profit_pct / 100.0)
            deal.tp_planned_index = i
            if cfg.stop_loss_pct > 0 and closes[j] <= deal.avg_entry * (1 - cfg.stop_loss_pct / 100.0):
                pending, pending_index = "exit", i
                deal.safety = []  # a stopped deal cancels its ladder
                deal.tp_level = None
        elif not entries_paused and pending is None and i >= cooldown_until:
            pending, pending_index = "base", i

    forced_qty = 0.0
    open_deal = None
    if deal is not None:
        open_deal = {"qty": deal.qty, "avg_entry": deal.avg_entry, "safety_filled": deal.safety_filled,
                     "cost_usd": deal.cost_usd, "bars_open": offset + n - 1 - deal.start_index,
                     "unrealized_usd": deal.qty * closes[-1] - deal.cost_usd}
        if close_at_end:
            forced_qty = sell_all(float(closes[-1]), offset + n - 1, "dca_forced_exit")
            equity[-1] = cash
            exposure[-1] = 0.0

    ppy = periods_per_year(interval)
    metrics = compute_metrics(equity, ts, trades, exposure, ppy, risk_free_rate, 0,
                              initial_equity=metric_initial_equity if metric_initial_equity > 0 else None)
    baseline_metrics = compute_metrics(baseline, ts, [], np.ones(n, dtype="float64"), ppy,
                                       risk_free_rate, 0,
                                       initial_equity=baseline_initial_equity if baseline_initial_equity > 0 else None)
    state = {
        "schema_version": 1, "cursor": offset + n, "last_ts": int(ts[-1]), "binding": binding,
        "last_close": float(closes[-1]), "baseline_units": float(baseline_units),
        "control": [cash, pending, pending_index, cooldown_until],
        "counts": [deals_completed, deals_stopped, safety_filled_total, max_safety_used],
        "totals": [realized, fees_paid, slip_paid], "deal": vars(deal).copy() if deal else None,
        "lengths": [length_sum + sum(deal_lengths), length_count + len(deal_lengths)],
        "first_plan": first_plan, "skipped": dict(skipped),
    }
    return DcaRunResult(
        continuation=state,
        config=cfg.to_dict(),
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        timestamps=ts,
        equity=equity,
        exposure=exposure,
        baseline_equity=baseline,
        trades=trades,
        capital_required_usd=capital_required_usd(cfg),
        deals_completed=deals_completed,
        deals_stopped=deals_stopped,
        safety_orders_filled=safety_filled_total,
        max_safety_used=max_safety_used,
        realized_pnl_usd=realized,
        fees_paid_usd=fees_paid,
        slippage_paid_usd=slip_paid,
        open_deal_at_end=open_deal,
        forced_exit_qty=forced_qty,
        avg_deal_bars=state["lengths"][0] / state["lengths"][1] if state["lengths"][1] else 0.0,
        skipped=dict(skipped),
        first_plan=first_plan,
    )


def rebind_dca_state(state, cfg, *, initial_capital, interval, costs):
    """Replace a paused flat deal constructor while preserving its cash book."""
    import copy

    if (state.get("schema_version") != 1 or state["deal"] is not None
            or state["control"][1] is not None):
        raise ValueError("DCA configuration adoption requires a flat account without pending intent")
    result = copy.deepcopy(state)
    result["binding"] = configuration_binding(cfg.to_dict(), initial_capital, interval, costs)
    result["first_plan"] = None
    return result
