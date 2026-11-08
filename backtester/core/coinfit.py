"""Offline coin-fit simulations over the existing spot bot engines.

This module performs no fetching, ranking, configuration writes, or trading.
Quick and audit callers use the same adverse fills; only the number of windows
and cost scenarios changes. Returns are on the whole funded account.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

import numpy as np

from .dcasim import DcaConfig, run_dca_backtest
from .gridsim import GridConfig, run_grid_backtest
from .types import CostConfig, validate_bar_arrays


def underwater_days(equity: np.ndarray, ts: np.ndarray, capital: float) -> float:
    """Longest underwater episode, including one still open at the endpoint."""
    peak, since, longest = capital, None, 0.0
    step = float(ts[1] - ts[0]) if len(ts) > 1 else 0.0
    for stamp, value in zip(ts, equity):
        if value >= peak - 1e-10:
            peak, since = max(peak, float(value)), None
        else:
            since = float(stamp) if since is None else since
            longest = max(longest, float(stamp) - since + step)
    return longest / 86400


def matched_hold(
    arrays: dict[str, np.ndarray], capital: float, costs: CostConfig
) -> np.ndarray:
    """Fund at t0, buy at the next open, liquidate at the final adverse close.

    The legacy bots' built-in baseline buys at the first close. This comparison
    instead matches the earliest bar on which the bot can execute, and charges
    both terminal costs. It never gives the baseline free entry or exit.
    """
    opening = float(arrays["open"][1])
    fee, slip = costs.fee_bps / 10000, costs.slippage_bps / 10000
    quantity = capital / ((1 + fee) * opening * (1 + slip))
    values = quantity * arrays["close"].astype(float)
    values[0] = capital
    values[-1] *= (1 - slip) * (1 - fee)
    return values


def _scheduled(
    arrays: dict[str, np.ndarray],
    capital: float,
    costs: CostConfig,
    interval_hours: int = 168,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Equal funded cash portions, submitted at close and filled next open.

    This is an explicit prefunded comparison, not an as-earned cash-flow model.
    Cash stays in account equity. The final coin inventory is liquidated with
    both fee and adverse slippage; zero interest on idle cash is explicit.
    """
    if (
        isinstance(interval_hours, bool)
        or not isinstance(interval_hours, int)
        or interval_hours < 1
    ):
        raise ValueError("contribution interval must be a positive whole hour")
    indices = list(range(1, len(arrays["ts"]), interval_hours))
    budget = capital / len(indices)
    fee, slip = costs.fee_bps / 10000, costs.slippage_bps / 10000
    cash, quantity = capital, 0.0
    equity = np.empty(len(arrays["ts"]), dtype=float)
    due = set(indices)
    fees, slippage = 0.0, 0.0
    fills = []
    for i, price in enumerate(arrays["close"]):
        if i in due:
            fill = float(arrays["open"][i]) * (1 + slip)
            notional = min(budget, cash) / (1 + fee)
            bought = notional / fill
            quantity += bought
            cash -= notional * (1 + fee)
            fees += notional * fee
            slippage += bought * (fill - float(arrays["open"][i]))
            fills.append(
                {
                    "ts": int(arrays["ts"][i]),
                    "bar_index": i,
                    "side": "buy",
                    "price": fill,
                    "units": bought,
                    "notional": notional,
                    "fee": notional * fee,
                    "slippage": bought * (fill - float(arrays["open"][i])),
                    "reason": "scheduled_contribution",
                }
            )
        equity[i] = cash + quantity * price
    gross = quantity * float(arrays["close"][-1]) * (1 - slip)
    fees += gross * fee
    slippage += quantity * float(arrays["close"][-1]) * slip
    equity[-1] = cash + gross * (1 - fee)
    fills.append(
        {
            "ts": int(arrays["ts"][-1]),
            "bar_index": len(equity) - 1,
            "side": "sell",
            "price": float(arrays["close"][-1]) * (1 - slip),
            "units": quantity,
            "notional": gross,
            "fee": gross * fee,
            "slippage": quantity * float(arrays["close"][-1]) * slip,
            "reason": "scheduled_terminal_liquidation",
        }
    )
    return equity, {
        "cycles": 0,
        "trades": len(indices) + 1,
        "costs_usd": fees + slippage,
        "fees_usd": fees,
        "slippage_usd": slippage,
        "open_inventory_before_exit": quantity,
        "contributions": len(indices),
        "contribution_budget": budget,
        "contribution_interval_hours": interval_hours,
        "funding_mode": "prefunded",
        "idle_cash_interest": 0.0,
        "_fills": fills,
    }


def simulate(
    bot: str,
    cfg: dict[str, Any],
    arrays: dict[str, np.ndarray],
    *,
    capital: float,
    costs: CostConfig,
    trace_limit: int = 200,
    include_fills: bool = False,
) -> dict[str, Any]:
    """Run one fixed configuration on a complete hourly window, no gap filling."""
    checked = validate_bar_arrays(arrays, "1h", require_open_volume=False)
    if "open" not in checked:
        raise ValueError("coin-fit needs observed opens; no close-to-open substitution")
    if len(checked["ts"]) < 24:
        raise ValueError("coin-fit windows need at least24complete hourly bars")
    if isinstance(capital, bool) or not math.isfinite(capital) or capital <= 0:
        raise ValueError("capital must be finite and positive")
    costs.validate()
    if costs.fee_bps < 0 or costs.slippage_bps < 0:
        raise ValueError("fees and slippage must not be negative")
    if costs.fee_bps >= 10000 or costs.slippage_bps >= 10000:
        raise ValueError("per-fill costs must be below10000bps")
    if not isinstance(trace_limit, int) or trace_limit < 2:
        raise ValueError("trace_limit must be at least2")
    if bot == "grid":
        price = float(checked["close"][0])
        gcfg = GridConfig(
            lower=price * (1 - cfg["range_pct"] / 100),
            upper=price * (1 + cfg["range_pct"] / 100),
            rungs=cfg["rungs"],
            notional_per_rung_usd=capital / cfg["rungs"],
            spacing=cfg["spacing"],
            deadband_bps=cfg["deadband_bps"],
        )
        result = run_grid_backtest(
            gcfg,
            checked,
            interval="1h",
            costs=costs,
            initial_capital=capital,
            close_at_end=True,
        )
        equity = result.equity
        detail = {
            "cycles": result.round_trips,
            "trades": len(result.trades),
            "costs_usd": result.fees_paid_usd + result.slippage_paid_usd,
            "fees_usd": result.fees_paid_usd,
            "slippage_usd": result.slippage_paid_usd,
            "spacing_bps": result.rung_width_bps,
            "open_inventory_before_exit": result.forced_exit_qty,
            "bars_below": result.bars_below_grid,
            "bars_above": result.bars_above_grid,
            "realized_pnl_usd": result.realized_pnl_usd,
        }
    elif bot == "dca":
        result = run_dca_backtest(
            DcaConfig(**cfg),
            checked,
            interval="1h",
            costs=costs,
            initial_capital=capital,
            close_at_end=True,
        )
        equity = result.equity
        first_open = None
        recoveries = []
        for trade in result.trades:
            if trade.reason == "open":
                first_open = trade.ts
            elif trade.side == "sell" and first_open is not None:
                if trade.reason == "dca_take_profit":
                    recoveries.append((trade.ts - first_open) / 86400)
                first_open = None
        unfinished = int(result.open_deal_at_end is not None)
        attempts = result.deals_completed + result.deals_stopped + unfinished
        detail = {
            "cycles": result.deals_completed,
            "trades": len(result.trades),
            "costs_usd": result.fees_paid_usd + result.slippage_paid_usd,
            "fees_usd": result.fees_paid_usd,
            "slippage_usd": result.slippage_paid_usd,
            "open_inventory_before_exit": result.forced_exit_qty,
            "open_deal_at_end": result.open_deal_at_end,
            "stopped_deals": result.deals_stopped,
            "unfinished_deals": unfinished,
            "exit_hit_rate": result.deals_completed / attempts if attempts else None,
            "recovery_p95_days": float(np.quantile(recoveries, 0.95))
            if recoveries
            else None,
            "max_safety_used": result.max_safety_used,
            "skipped": result.skipped,
            "realized_pnl_usd": result.realized_pnl_usd,
        }
    elif bot == "scheduled_dca":
        equity, detail = _scheduled(
            checked, capital, costs, cfg.get("interval_hours", 168)
        )
        scheduled_fills = detail.pop("_fills")
    else:
        raise ValueError("coin-fit supports grid, dca or scheduled_dca")
    hold = matched_hold(checked, capital, costs)
    peak = np.maximum.accumulate(np.r_[capital, equity])[1:]
    max_dd = float(np.min(equity / peak - 1))
    # Preserve the worst risk on the full curve before reducing display points.
    metrics = {
        "total_return": float(equity[-1] / capital - 1),
        "hold_return": float(hold[-1] / capital - 1),
        "excess_return": float((equity[-1] - hold[-1]) / capital),
        "max_drawdown": max_dd,
        "final_equity": float(equity[-1]),
        "capital_usd": capital,
        "time_underwater_days": underwater_days(equity, checked["ts"], capital),
        "bars": len(equity),
        **detail,
    }
    if not all(
        math.isfinite(metrics[k])
        for k in ("total_return", "hold_return", "max_drawdown", "final_equity")
    ):
        raise ValueError("simulation produced non-finite account metrics")
    points = np.unique(
        np.linspace(0, len(equity) - 1, min(trace_limit, len(equity))).astype(int)
    )
    return {
        "metrics": metrics,
        "equity": [
            [int(checked["ts"][i]), float(equity[i]), float(hold[i])] for i in points
        ],
        "baseline": "Same full capital; buy at next observed open, terminal adverse liquidation; cash baseline0%",
        "terminal_policy": "Force liquidation with costs; pre-exit inventory and unresolved deals retained",
        "engine": "existing grid/dca simulator"
        if bot != "scheduled_dca"
        else "prefunded equal-dollar next-open schedule",
        "fills": (
            [asdict(t) for t in result.trades]
            if bot != "scheduled_dca"
            else scheduled_fills
        )
        if include_fills
        else [],
    }
