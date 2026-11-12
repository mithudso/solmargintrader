"""Clock bridges accrue time and mark equity but never supply executable prices."""
import unittest

import numpy as np

from backtester.core.dcasim import DcaConfig, run_dca_backtest
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.gridsim import GridConfig, run_grid_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.types import CostConfig, Mode, validate_bar_arrays


def bars(prices, observed):
    p = np.asarray(prices, dtype=float)
    return {"ts": np.arange(len(p)) * 86400, "open": p, "high": p.copy(), "low": p.copy(), "close": p,
            "volume": np.ones(len(p)), "observed": np.asarray(observed)}


class RecordingLong(BuyAndHold):
    def __init__(self):
        super().__init__()
        self.calls = []

    def on_bar(self, history):
        self.calls.append(history.i)
        return 1.

    def checkpoint_state(self):
        return {'calls': list(self.calls)}

    def restore_state(self, state):
        self.calls = list(state['calls'])


class ObservedExecutionTests(unittest.TestCase):
    def test_mask_must_be_exact_boolean_and_match_bars(self):
        for mask in ([1, 0], [True], [np.nan, 1.]):
            with self.assertRaisesRegex(ValueError, 'observed'):
                validate_bar_arrays(bars([100, 100], mask), '1d')

    def test_trend_defers_pending_and_skips_signals_and_terminal_exit(self):
        data = bars([100, 100, 200, 200], [True, False, True, False])
        strategy = RecordingLong()
        result = run_backtest(strategy, data, EngineConfig(fill_delay=1, costs=CostConfig(fee_bps=0, slippage_bps=0)))
        self.assertEqual(strategy.calls, [0, 2])
        self.assertEqual([t.bar_index for t in result.trades], [2])
        self.assertEqual(result.trades[0].price, 200)
        self.assertEqual(result.equity[-1], 10000)
        self.assertNotEqual(result.continuation['position']['units'], 0)

    def test_deferred_target_survives_a_continuation_boundary(self):
        data = bars([100, 100, 200, 200], [True, False, True, False])
        config = EngineConfig(fill_delay=1, costs=CostConfig(fee_bps=0, slippage_bps=0))
        full = run_backtest(RecordingLong(), data, config, close_at_end=False)
        prefix = run_backtest(RecordingLong(), {k: v[:2] for k, v in data.items()}, config, close_at_end=False)
        resumed = run_backtest(RecordingLong(), {k: v[2:] for k, v in data.items()}, config,
                               close_at_end=False, continuation=prefix.continuation)
        self.assertEqual([trade.bar_index for trade in resumed.trades], [2])
        self.assertEqual(resumed.trades[0].price, 200)
        np.testing.assert_array_equal(np.r_[prefix.equity, resumed.equity], full.equity)
        self.assertEqual(resumed.continuation['tail']['observed'], [False])

    def test_trend_carry_accrues_without_synthetic_liquidation(self):
        data = bars([100, 100, 100], [True, False, False])
        # An unobserved artificial wick is never a liquidation observation.
        data['low'][1:] = 1
        cfg = EngineConfig(mode=Mode.PERP, leverage=2, fill_delay=0, costs=CostConfig(fee_bps=0, slippage_bps=0, perp_base_fee_bps=0))
        result = run_backtest(RecordingLong(), data, cfg)
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.liquidation_count, 0)
        self.assertGreater(result.continuation['position']['accrued_borrow_fee'], 0)
        self.assertLess(result.equity[-1], result.equity[0])

    def test_grid_resting_orders_wait_for_observed_price_and_keep_carry(self):
        cfg = GridConfig(90, 110, 3, 100, deadband_bps=0, min_order_usd=0)
        data = bars([100, 100, 90, 90], [True, False, True, False])
        data['low'][1] = 80
        data['high'][1] = 120
        result = run_grid_backtest(cfg, data, initial_capital=1000, costs=CostConfig(fee_bps=0, slippage_bps=0), carry_bps_per_hour=1)
        self.assertTrue(result.trades)
        self.assertTrue(all(t.bar_index == 2 for t in result.trades))
        self.assertTrue(all(t.side == 'buy' for t in result.trades))
        self.assertGreater(sum(lot["accrued_carry_usd"] for lot in result.continuation["lots"]), 0)
        self.assertLess(result.equity[3], result.equity[2])
        self.assertEqual(result.forced_exit_qty, 0)

    def test_dca_pending_base_waits_and_gap_does_not_take_profit(self):
        data = bars([100, 100, 100, 100], [True, False, True, False])
        data['high'][3] = 1000
        result = run_dca_backtest(DcaConfig(max_safety_orders=0), data, interval='1d', costs=CostConfig(fee_bps=0, slippage_bps=0))
        self.assertEqual([t.bar_index for t in result.trades], [2])
        self.assertEqual(result.trades[0].side, 'buy')
        self.assertEqual(result.forced_exit_qty, 0)

    def test_all_unobserved_has_no_decisions_orders_or_trades(self):
        data = bars([100, 100, 100], [False, False, False])
        strategy = RecordingLong()
        trend = run_backtest(strategy, data, EngineConfig())
        grid = run_grid_backtest(GridConfig(90, 110, 3, 100), data)
        dca = run_dca_backtest(DcaConfig(), data, interval='1d')
        self.assertEqual(strategy.calls, [])
        self.assertEqual(trend.trades, [])
        self.assertEqual(grid.orders_placed, 0)
        self.assertEqual(grid.trades, [])
        self.assertEqual(dca.trades, [])
