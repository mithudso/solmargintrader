"""Trend decisions, execution economics and shared bot workflows; no network."""
from __future__ import annotations

import unittest
from unittest import mock

import numpy as np

from backtester.core.types import BarWindow, CostConfig
from soltui import bots, commands, pricefeed
from soltui.tests.test_bots import Isolated, write_hourly, write_snapshots
from soltui.trend import TrendConfig, TrendFollowing, run_trend_backtest


def bars(closes, *, step=3600):
    close = np.asarray(closes, dtype=float)
    return {"ts": np.arange(len(close), dtype="int64") * step + 1_794_000_000,
            "open": close.copy(), "high": close + 1, "low": close - 1,
            "close": close, "volume": np.ones(len(close))}


def decisions(arrays, config):
    strategy = TrendFollowing(config)
    return [strategy.on_bar(BarWindow(*(arrays[k] for k in
            ("ts", "open", "high", "low", "close", "volume")), i))
            for i in range(len(arrays["close"]))]


class TrendPolicy(unittest.TestCase):
    def test_rejects_invalid_settings(self):
        for values in ({"fast_period": True}, {"slow_period": 3.5}, {"fast_period": 30},
                       {"fast_period": 0}, {"entry_buffer_bps": -1},
                       {"capital_usd": 0}, {"capital_usd": float("nan")},
                       {"entry_buffer_bps": float("inf")}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                TrendConfig(**values)

    def test_trends_enter_exit_and_flat_or_falling_markets_stay_in_cash(self):
        cfg = TrendConfig(fast_period=2, slow_period=4, entry_buffer_bps=0)
        sequence = decisions(bars([100, 100, 100, 110, 120, 110, 90, 80]), cfg)
        self.assertEqual(sequence, [0, 0, 0, 1, 1, 1, 0, 0])
        self.assertEqual(decisions(bars([100] * 12), cfg), [0] * 12)
        self.assertEqual(decisions(bars(range(120, 100, -1)), cfg), [0] * 20)

    def test_entry_buffer_holds_until_the_averages_reverse(self):
        cfg = TrendConfig(fast_period=1, slow_period=3, entry_buffer_bps=100)
        self.assertEqual(decisions(bars([100, 100, 103, 102, 101]), cfg), [0, 0, 1, 1, 0])

    def test_signals_and_fills_ignore_future_prices_and_fill_at_next_open(self):
        cfg = TrendConfig(fast_period=2, slow_period=4, entry_buffer_bps=0)
        arrays = bars([100, 100, 100, 110, 125, 130, 120, 100, 95, 90])
        signals = decisions(arrays, cfg)
        result, _ = run_trend_backtest(cfg, arrays, interval="1h", costs=CostConfig())
        self.assertEqual(result.trades[0].bar_index, 4)
        self.assertEqual(result.trades[0].price, 125)
        for end in range(5, len(arrays["close"])):
            prefix = {key: value[:end] for key, value in arrays.items()}
            self.assertEqual(decisions(prefix, cfg), signals[:end])
            partial, _ = run_trend_backtest(cfg, prefix, interval="1h", costs=CostConfig())
            # The final sample liquidation is accounting, not an earlier signal fill.
            self.assertEqual([(t.bar_index, t.price, t.side) for t in partial.trades if t.reason != "final"],
                             [(t.bar_index, t.price, t.side) for t in result.trades if t.bar_index < end and t.reason != "final"])
            np.testing.assert_allclose(partial.equity[:-1], result.equity[:end - 1])

    def test_costs_reach_both_bot_and_hold_and_short_history_is_refused(self):
        cfg = TrendConfig(fast_period=2, slow_period=4, entry_buffer_bps=0)
        arrays = bars([100, 100, 100, 110, 120, 130, 140, 150])
        free, free_hold = run_trend_backtest(cfg, arrays, interval="1h", costs=CostConfig(fee_bps=0, slippage_bps=0))
        paid, paid_hold = run_trend_backtest(cfg, arrays, interval="1h", costs=CostConfig(fee_bps=50, slippage_bps=30))
        self.assertLess(paid.metrics.final_equity, free.metrics.final_equity)
        self.assertLess(paid_hold.metrics.final_equity, free_hold.metrics.final_equity)
        self.assertGreater(sum(t.fee + t.slippage for t in paid.trades), 0)
        self.assertEqual(paid.mode, "spot")
        self.assertEqual(paid.leverage, 1)
        with self.assertRaisesRegex(ValueError, "at least 5 completed bars"):
            run_trend_backtest(cfg, bars([100] * 4), interval="1h", costs=CostConfig())


class TrendWorkbench(Isolated):
    def test_optimizer_evaluates_trend_without_ungated_adoption(self):
        write_hourly(self.data, "SOL", n=24 * 18)
        baseline = bots.get_config("trend", "SOL")
        report = bots.optimize("trend", self.settings, coins=["SOL"], windows=6, window_days=3, adopt=False)
        self.assertNotIn("SOL", report["skipped"], report)
        self.assertIn("SOL", report["coins_used"])
        self.assertEqual(report["reports"]["SOL"]["status"], "completed")
        self.assertGreater(report["train_cells"], 0)
        self.assertFalse(report["verdict"]["saved"])
        self.assertEqual(bots.get_config("trend", "SOL"), baseline)

    def test_five_bot_overview_and_saved_coin_config_backtest_and_candidates(self):
        write_hourly(self.data, "SOL", n=240)
        ctx = commands.Context.from_settings(self.settings)
        overview = commands.dispatch("bots.overview", {}, ctx=ctx, quiet=True)
        self.assertTrue(overview["ok"], overview)
        self.assertEqual([row["label"] for row in overview["result"]["bots"]],
                         ["DCA", "Grid", "Arbitrage", "Trend", "Council"])
        saved = commands.dispatch("bots.save", {"bot": "trend", "asset": "SOL", "mode": "manual",
            "values": {"fast_period": 3, "slow_period": 8}}, ctx=ctx, quiet=True)
        self.assertTrue(saved["ok"], saved)
        self.assertEqual(bots.get_config("trend", "BTC"), bots.DEFAULTS["trend"])
        run = commands.dispatch("bots.backtest", {"bot": "trend", "asset": "SOL"}, ctx=ctx, quiet=True)
        self.assertTrue(run["ok"], run)
        self.assertEqual(run["result"]["errors"], {})
        measured = run["result"]["runs"][0]
        self.assertEqual(measured["config"]["slow_period"], 8)
        self.assertGreater(measured["results"]["costs_usd"], 0)
        self.assertTrue(measured["equity"])
        with self.assertRaisesRegex(bots.BotError, "manual mode"):
            bots.save_config("trend", {"slow_period": 10}, coin="SOL", reason="experiment run: improvement")
        for candidate in bots.candidates("trend", bots.DEFAULTS["trend"]):
            self.assertEqual(bots.validate("trend", candidate), candidate)

    def test_recorded_forward_warmup_replay_snapshot_and_stop(self):
        start = 1_794_000_000
        bots.save_config("trend", {"fast_period": 2, "slow_period": 4}, coin="SOL")
        with mock.patch.object(bots, "_triangle_products", return_value=["SOL-USD"]):
            bots.forward_start("trend", "SOL", self.settings, ensure_recorder=False, now=start)
        bots.save_config("trend", {"slow_period": 8}, coin="SOL")
        rows = [(start + i * 60 + sec, {"SOL-USD": [99.99 + i, 100.01 + i, 100 + i, 10, 10, start + i * 60 + sec]})
                for i in range(8) for sec in (0, 30)]
        write_snapshots(pricefeed.prices_dir(), rows)
        warming = bots.forward_status("trend", self.settings, now=start + 180)
        self.assertIn("3/5", warming["message"])
        # Reuse the same session to catch state leaked between refreshes.
        result = bots.forward_status("trend", self.settings, now=start + 480)
        self.assertEqual(result["forward"]["config"]["slow_period"], 4)
        self.assertGreater(result["results"]["costs_usd"], 0)
        self.assertTrue(result["running"])
        stopped = bots.forward_stop("trend", now=start + 480)
        self.assertTrue(stopped["stopped"])
        self.assertFalse(bots.forward_status("trend", self.settings, now=start + 600)["running"])
