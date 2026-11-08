"""DCA safety-order bot: arithmetic, fill timing, costs, and the one-bar leak guard."""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.dcasim import (
    DcaConfig,
    capital_required_usd,
    plan_deal,
    run_dca_backtest,
    safety_deviations_pct,
    safety_sizes_usd,
)
from backtester.core.types import CostConfig

FREE = CostConfig(fee_bps=0.0, slippage_bps=0.0)


def bars(opens, highs, lows, closes, step=3600, start=1_700_000_000):
    n = len(closes)
    return {
        "ts": np.arange(n, dtype="int64") * step + start,
        "open": np.asarray(opens, dtype="float64"),
        "high": np.asarray(highs, dtype="float64"),
        "low": np.asarray(lows, dtype="float64"),
        "close": np.asarray(closes, dtype="float64"),
    }


def flat_then(path):
    """Bars whose open, high, low and close are all the given price (a path of points)."""
    return bars(path, path, path, path)


class LadderArithmetic(unittest.TestCase):
    def test_deviations_compound_by_step_scale(self) -> None:
        cfg = DcaConfig(max_safety_orders=3, price_deviation_pct=1.0, step_scale=2.0)
        self.assertEqual(safety_deviations_pct(cfg), [1.0, 3.0, 7.0])

    def test_sizes_compound_by_volume_scale(self) -> None:
        cfg = DcaConfig(safety_order_usd=10.0, max_safety_orders=3, volume_scale=1.5)
        self.assertEqual(safety_sizes_usd(cfg), [10.0, 15.0, 22.5])
        self.assertEqual(capital_required_usd(cfg), cfg.base_order_usd + 47.5)

    def test_plan_lowers_the_average_and_the_take_profit(self) -> None:
        cfg = DcaConfig(base_order_usd=100, safety_order_usd=100, max_safety_orders=1,
                        price_deviation_pct=10.0, take_profit_pct=5.0)
        plan = plan_deal(cfg, 100.0)
        base, so = plan["orders"]
        self.assertAlmostEqual(base["take_profit"], 105.0)
        self.assertAlmostEqual(so["price"], 90.0)
        # 200 USD buys 1 + 100/90 units: average = 200 / (1 + 1.1111) = 94.7368
        self.assertAlmostEqual(so["avg_entry"], 200 / (1 + 100 / 90))
        self.assertLess(so["take_profit"], base["take_profit"])

    def test_a_ladder_past_zero_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            DcaConfig(max_safety_orders=10, price_deviation_pct=20.0)

    def test_orders_below_the_venue_minimum_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            DcaConfig(base_order_usd=5.0)
        with self.assertRaises(ValueError):
            DcaConfig(safety_order_usd=5.0)
        DcaConfig(safety_order_usd=5.0, max_safety_orders=0)  # no safety orders, no minimum to meet

    def test_non_finite_and_bool_values_are_refused(self) -> None:
        for bad in ({"take_profit_pct": float("nan")}, {"max_safety_orders": True},
                    {"stop_loss_pct": 100.0}, {"step_scale": 0.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                DcaConfig(**bad)


class FillTiming(unittest.TestCase):
    def test_base_order_fills_at_the_next_open_not_the_first_bar(self) -> None:
        cfg = DcaConfig(max_safety_orders=0, take_profit_pct=50.0)
        r = run_dca_backtest(cfg, flat_then([100, 110, 110]), costs=FREE, close_at_end=False)
        self.assertEqual(r.trades[0].bar_index, 1)
        self.assertEqual(r.trades[0].price, 110.0)

    def test_take_profit_closes_the_deal_and_a_new_one_starts(self) -> None:
        cfg = DcaConfig(base_order_usd=100, max_safety_orders=0, take_profit_pct=10.0)
        # base fills at 100 (bar 1), TP at 110 rests from bar 1's close, fills on bar 2's high.
        r = run_dca_backtest(cfg, bars([100, 100, 100, 100], [100, 100, 111, 100],
                                       [100, 100, 100, 100], [100, 100, 100, 100]),
                             costs=FREE, close_at_end=False)
        self.assertEqual(r.deals_completed, 1)
        self.assertAlmostEqual(r.realized_pnl_usd, 10.0)
        sells = [t for t in r.trades if t.side == "sell"]
        self.assertEqual(sells[0].bar_index, 2)
        # A new deal's base order was queued at bar 2's close and filled at bar 3's open.
        self.assertEqual([t.bar_index for t in r.trades if t.reason == "open"], [1, 3])

    def test_take_profit_cannot_fill_on_the_bar_that_bought(self) -> None:
        # Bar 2 dips to the safety order AND spikes past every take-profit. Within one bar
        # the path is unknown, so the deal must still be open after bar 2.
        cfg = DcaConfig(base_order_usd=100, safety_order_usd=100, max_safety_orders=1,
                        price_deviation_pct=10.0, take_profit_pct=1.0)
        r = run_dca_backtest(cfg, bars([100, 100, 100], [100, 100, 150], [100, 100, 80],
                                       [100, 100, 100]), costs=FREE, close_at_end=False)
        self.assertEqual(r.deals_completed, 0)
        self.assertEqual(r.safety_orders_filled, 1)
        self.assertEqual(r.skipped.get("take-profit-deferred-same-bar-buy"), 1)

    def test_a_safety_order_cannot_fill_on_the_base_order_bar(self) -> None:
        cfg = DcaConfig(base_order_usd=100, safety_order_usd=100, max_safety_orders=1,
                        price_deviation_pct=10.0, take_profit_pct=50.0)
        # Bar 1 opens at 100 (base fill) and trades down to 80 in the same bar.
        r = run_dca_backtest(cfg, bars([100, 100, 100], [100, 100, 100], [100, 80, 100],
                                       [100, 90, 100]), costs=FREE, close_at_end=False)
        self.assertEqual(r.safety_orders_filled, 0)

    def test_a_future_spike_does_not_change_earlier_decisions(self) -> None:
        # The one-bar leak test: altering bar k must leave every fill before bar k unchanged.
        rng = np.random.default_rng(7)
        closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 200)))
        opens = np.r_[closes[0], closes[:-1]]
        highs = np.maximum(opens, closes) * 1.01
        lows = np.minimum(opens, closes) * 0.99
        cfg = DcaConfig(base_order_usd=50, safety_order_usd=50, max_safety_orders=4,
                        price_deviation_pct=2.0, take_profit_pct=1.5)
        a = run_dca_backtest(cfg, bars(opens, highs, lows, closes), close_at_end=False)
        k = 120
        highs2, lows2 = highs.copy(), lows.copy()
        highs2[k], lows2[k] = highs[k] * 3, lows[k] * 0.3
        b = run_dca_backtest(cfg, bars(opens, highs2, lows2, closes), close_at_end=False)
        before = lambda r: [(t.bar_index, t.side, round(t.price, 9)) for t in r.trades if t.bar_index < k]
        self.assertEqual(before(a), before(b))
        np.testing.assert_allclose(a.equity[:k], b.equity[:k])


class Costs(unittest.TestCase):
    def test_fees_and_slippage_reduce_a_round_trip(self) -> None:
        cfg = DcaConfig(base_order_usd=100, max_safety_orders=0, take_profit_pct=10.0)
        data = bars([100, 100, 100], [100, 100, 111], [100, 100, 100], [100, 100, 100])
        free = run_dca_backtest(cfg, data, costs=FREE, close_at_end=False)
        paid = run_dca_backtest(cfg, data, costs=CostConfig(fee_bps=10.0, slippage_bps=10.0),
                                close_at_end=False)
        self.assertAlmostEqual(free.realized_pnl_usd, 10.0)
        self.assertLess(paid.realized_pnl_usd, free.realized_pnl_usd)
        self.assertGreater(paid.fees_paid_usd, 0)
        self.assertGreater(paid.slippage_paid_usd, 0)

    def test_equity_is_cash_plus_marked_inventory(self) -> None:
        cfg = DcaConfig(base_order_usd=100, safety_order_usd=100, max_safety_orders=2,
                        price_deviation_pct=5.0, take_profit_pct=50.0)
        data = flat_then([100, 100, 94, 89, 92])
        r = run_dca_backtest(cfg, data, costs=CostConfig(fee_bps=6.0, slippage_bps=2.0),
                             close_at_end=False)
        cash_spent = sum(t.notional + t.fee for t in r.trades if t.side == "buy")
        qty = sum(t.units for t in r.trades if t.side == "buy")
        start = r.capital_required_usd * (1 + 6.0 / 10_000)
        self.assertAlmostEqual(r.equity[-1], start - cash_spent + qty * 92.0, places=6)


class Lifecycle(unittest.TestCase):
    def test_a_falling_market_fills_the_ladder_and_reports_the_bag(self) -> None:
        cfg = DcaConfig(base_order_usd=100, safety_order_usd=100, max_safety_orders=3,
                        price_deviation_pct=5.0, take_profit_pct=3.0)
        data = flat_then(list(np.linspace(100, 60, 30)))
        r = run_dca_backtest(cfg, data, costs=FREE)
        self.assertEqual(r.max_safety_used, 3)
        self.assertEqual(r.deals_completed, 0)
        self.assertIsNotNone(r.open_deal_at_end)
        self.assertLess(r.metrics.total_return, 0)
        self.assertGreater(r.forced_exit_qty, 0)

    def test_stop_loss_exits_at_the_next_open(self) -> None:
        cfg = DcaConfig(base_order_usd=100, max_safety_orders=0, take_profit_pct=50.0, stop_loss_pct=5.0)
        r = run_dca_backtest(cfg, flat_then([100, 100, 94, 90, 90]), costs=FREE, close_at_end=False)
        stop = [t for t in r.trades if t.reason == "dca_stop_loss"]
        self.assertEqual(len(stop), 1)
        self.assertEqual(stop[0].bar_index, 3)  # signalled at bar 2's close, filled at bar 3's open
        self.assertEqual(r.deals_stopped, 1)

    def test_unfundable_safety_orders_are_skipped_and_counted(self) -> None:
        cfg = DcaConfig(base_order_usd=100, safety_order_usd=100, max_safety_orders=3,
                        price_deviation_pct=5.0, take_profit_pct=50.0)
        r = run_dca_backtest(cfg, flat_then([100, 100, 94, 89, 84]), initial_capital=250.0,
                             costs=FREE, close_at_end=False)
        self.assertEqual(r.safety_orders_filled, 1)
        self.assertGreaterEqual(r.skipped.get("safety-order-insufficient-cash", 0), 1)

    def test_baseline_pays_entry_costs(self) -> None:
        cfg = DcaConfig(max_safety_orders=0)
        r = run_dca_backtest(cfg, flat_then([100, 100, 100]), initial_capital=500.0,
                             costs=CostConfig(fee_bps=10.0, slippage_bps=0.0))
        self.assertAlmostEqual(r.baseline_equity[-1], 500.0 / 1.001)

    def test_first_plan_records_what_the_bot_set(self) -> None:
        cfg = DcaConfig(max_safety_orders=2)
        r = run_dca_backtest(cfg, flat_then([100, 120, 120]), costs=FREE)
        self.assertEqual(r.first_plan["base_price"], 120.0)
        self.assertEqual(len(r.first_plan["orders"]), 3)


if __name__ == "__main__":
    unittest.main()
