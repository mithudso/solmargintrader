"""A retained account must not report earlier performance as a new chunk's gain."""
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
