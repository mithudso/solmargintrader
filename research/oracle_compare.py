"""Common-window equal-notional order sensitivity; no live execution."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from research.oracle_common_window import equal_notional_qty
from research.pine_bar_emulator import Bar, Intent, simulate


def size_at_close(bars: Sequence[Bar], orders: Sequence[Sequence[Intent]], *,
                  target_usd: float = 1000.) -> list[list[Intent]]:
    """Counterfactual sizing, separate from a strategy's source defaults."""
    if len(bars) != len(orders):
        raise ValueError("one intent list per completed bar is required")
    return [[replace(intent, qty=equal_notional_qty(bar.close, target_usd))
             if intent.action == "entry" else intent for intent in group]
            for bar, group in zip(bars, orders, strict=True)]


def compare(bars: Sequence[Bar], orders: Sequence[Sequence[Intent]], *,
            step_seconds: int, default_qty: float, target_usd: float = 1000.,
            before_run: Callable[[], None] | None = None,
            after_run: Callable[[], None] | None = None) -> list[dict]:
    """Replay equal-notional and source-sized intents under explicit costs.

    This uncollateralized OHLC model has no funding, spread beyond slippage,
    exchange leverage, margin or liquidation. `default_qty` must be supplied
    explicitly for the source-sized case. If source default is not proven,
    callers must not label an arbitrary value as its faithful strategy size.
    """
    sizing = [("equal_notional", size_at_close(bars, orders, target_usd=target_usd)),
              ("source_sizing", orders)]
    result = []
    for size_name, sized_orders in sizing:
        for scenario, fee, slip in (("zero_cost", 0., 0.), ("fee10_slippage1", 10., 1.)):
            if before_run is not None:
                before_run()
            try:
                run = simulate(bars, sized_orders, default_qty=default_qty, step_seconds=step_seconds,
                               initial_capital=100000, fee_bps=fee, slippage_bps=slip)
            finally:
                if after_run is not None:
                    after_run()
            equity = run.pop("equity_curve")
            fills = run.pop("fills")
            peak, drawdown, open_fill, closed, wins = 100000., 0., None, 0, 0
            for value in equity:
                peak = max(peak, value)
                drawdown = max(drawdown, 1-value/peak)
            for fill in fills:
                if fill["event"] == "open":
                    open_fill = fill
                elif fill["event"] == "close" and open_fill is not None:
                    pnl = (open_fill["side"] * open_fill["quantity"] *
                           (fill["price"] - open_fill["price"]) - open_fill["fee"] - fill["fee"])
                    closed += 1
                    wins += int(pnl > 0)
                    open_fill = None
            result.append({"sizing": size_name, "scenario": scenario, "fee_bps": fee,
                           "slippage_bps": slip, "closed_trades": closed,
                           "winning_trades": wins, "max_drawdown_fraction": drawdown, **run})
    return result
