"""Metric windows retain current performance and every modeled boundary cost."""
from __future__ import annotations

import unittest
import numpy as np

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.types import CostConfig, Mode


class Holding:
    name = "constant-checkpoint-fixture"
    params = {}

    def warmup_bars(self):
        return 0

    def on_bar(self, _history):
        return 1.0

    def checkpoint_state(self):
        return {}

    def restore_state(self, _state):
        pass


def bars(prices, start=0):
    values = np.asarray(prices, dtype=float)
    return {"ts": (np.arange(len(values)) + start) * 86400,
            **{name: values.copy() for name in ("open", "high", "low", "close")},
            "volume": np.ones(len(values))}


class ContinuationMetricTests(unittest.TestCase):
    def test_flat_new_chunk_does_not_repeat_prior_gain_or_entry_cost(self):
        for mode in (Mode.SPOT, Mode.PERP):
            with self.subTest(mode=mode):
                config = EngineConfig(mode=mode, initial_capital=100, fill_delay=0,
                                      leverage=1 if mode is Mode.SPOT else 2,
                                      costs=CostConfig(max_hourly_rate_bps_long=0))
                previous = run_backtest(Holding(), bars([100, 110]), config, close_at_end=False)
                self.assertGreater(previous.metrics.total_return, 0)
                current = run_backtest(Holding(), bars([110, 110], start=2), config,
                                       close_at_end=False, continuation=previous.continuation)
                self.assertEqual(current.trades, [])
                self.assertAlmostEqual(current.metrics.total_return, 0)
                self.assertAlmostEqual(current.gross_metrics.total_return, 0)
                self.assertAlmostEqual(current.metrics.max_drawdown, 0)
                self.assertAlmostEqual(current.metrics.final_equity, previous.metrics.final_equity)
                whole = run_backtest(Holding(), bars([100, 110, 110, 110]), config,
                                     close_at_end=False)
                self.assertEqual(current.account, whole.account)
                self.assertEqual(current.continuation["book"], whole.continuation["book"])

    def test_wiped_account_can_remain_flat_without_repeating_earlier_loss(self):
        costs = CostConfig(fee_bps=0, slippage_bps=0, perp_base_fee_bps=0,
                           max_hourly_rate_bps_long=0, liquidation_forfeits_collateral=True)
        config = EngineConfig(mode=Mode.PERP, leverage=2, initial_capital=100,
                              fill_delay=0, costs=costs)
        previous = run_backtest(Holding(), bars([100, 10]), config, close_at_end=False)
        self.assertEqual(previous.metrics.final_equity, 0)
        current = run_backtest(Holding(), bars([10, 10], start=2), config,
                               close_at_end=False, continuation=previous.continuation)
        values = {"net_return": current.metrics.total_return,
                  "gross_return": current.gross_metrics.total_return,
                  "liquidation_count": current.liquidation_count,
                  "metric_liquidations": current.metrics.liquidation_count}
        for field, value in values.items():
            with self.subTest(field=field):
                self.assertEqual(value, 0)
        self.assertEqual(current.trades, [])


class CpcvCostBoundaryTests(unittest.TestCase):
    def test_close_fill_paths_include_entry_and_exit_fees(self):
        from backtester.core.cpcv import evaluate_block

        class WarmHolding(Holding):
            def warmup_bars(self):
                return 2

        for warmup, factory in ((0, Holding), (2, WarmHolding)):
            for delay in (0, 1):
                with self.subTest(warmup=warmup, fill_delay=delay):
                    config = EngineConfig(initial_capital=100, fill_delay=delay,
                                          costs=CostConfig(fee_bps=100, slippage_bps=0))
                    block = evaluate_block(factory, bars([100] * 7), warmup, 7, config)
                    self.assertTrue(block.usable)
                    self.assertEqual(block.trades, 2)
                    # One purchase reserves its1%fee, and the sale charges1%again.
                    expected = .99 / 1.01 - 1
                    observed = float(np.prod(1 + block.returns) - 1)
                    self.assertAlmostEqual(observed, expected)


class BotContinuationMetricTests(unittest.TestCase):
    def test_legacy_checkpoint_without_valuation_boundary_refuses(self):
        from backtester.core.dcasim import DcaConfig, run_dca_backtest
        from backtester.core.gridsim import GridConfig, run_grid_backtest

        cases = [(run_dca_backtest, DcaConfig(base_order_usd=20, max_safety_orders=0)),
                 (run_grid_backtest, GridConfig(lower=80, upper=120, rungs=5, notional_per_rung_usd=20))]
        kwargs = {"initial_capital": 100, "interval": "1d", "close_at_end": False}
        for run, config in cases:
            previous = run(config, bars([100, 100]), **kwargs)
            for field in ("last_close", "baseline_units"):
                checkpoint = {k: v for k, v in previous.continuation.items() if k != field}
                with self.subTest(engine=run.__name__, missing=field), self.assertRaises(ValueError):
                    run(config, bars([100], start=2), continuation=checkpoint, **kwargs)

    def test_grid_new_flat_chunk_does_not_repeat_previous_return_or_rebuy_baseline(self):
        from backtester.core.gridsim import GridConfig, run_grid_backtest

        config = GridConfig(lower=80, upper=120, rungs=5, spacing="arith", notional_per_rung_usd=20)
        kwargs = {"initial_capital": 100, "interval": "1d", "close_at_end": False}
        previous = run_grid_backtest(config, bars([100, 90, 100]), **kwargs)
        self.assertGreater(previous.metrics.total_return, 0)
        current = run_grid_backtest(config, bars([100, 100], start=3), continuation=previous.continuation, **kwargs)
        self.assertEqual(current.trades, [])
        for label, value in (("net", current.metrics.total_return), ("baseline", current.baseline_metrics.total_return)):
            with self.subTest(metric=label):
                self.assertAlmostEqual(value, 0)
        whole = run_grid_backtest(config, bars([100, 90, 100, 100, 100]), **kwargs)
        self.assertEqual(current.continuation["book"], whole.continuation["book"])
        np.testing.assert_allclose(np.concatenate([previous.baseline_equity, current.baseline_equity]), whole.baseline_equity)

    def test_dca_new_flat_chunk_does_not_repeat_previous_return_or_rebuy_baseline(self):
        from backtester.core.dcasim import DcaConfig, run_dca_backtest

        config = DcaConfig(base_order_usd=20, max_safety_orders=0, take_profit_pct=5, cooldown_bars=10)
        kwargs = {"initial_capital": 100, "interval": "1d", "close_at_end": False}
        previous = run_dca_backtest(config, bars([100, 100, 110]), **kwargs)
        self.assertGreater(previous.metrics.total_return, 0)
        current = run_dca_backtest(config, bars([110, 110], start=3), continuation=previous.continuation, **kwargs)
        self.assertEqual(current.trades, [])
        for label, value in (("net", current.metrics.total_return), ("baseline", current.baseline_metrics.total_return)):
            with self.subTest(metric=label):
                self.assertAlmostEqual(value, 0)
        whole = run_dca_backtest(config, bars([100, 100, 110, 110, 110]), **kwargs)
        self.assertEqual(current.continuation["control"], whole.continuation["control"])
        self.assertEqual(current.continuation["totals"], whole.continuation["totals"])
        np.testing.assert_allclose(np.concatenate([previous.baseline_equity, current.baseline_equity]), whole.baseline_equity)
