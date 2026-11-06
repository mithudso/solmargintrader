"""Offline counterexamples for money, timing and history-boundary invariants."""
from __future__ import annotations

import math
import unittest
import numpy as np

from backtester.core.engine import EngineConfig, _Book, run_backtest
from backtester.core.gridsim import GridConfig, _level_key, run_grid_backtest
from backtester.core.metrics import compute_metrics
from backtester.core.types import CostConfig, Mode, Side


def zero_cost(**patch):
    return CostConfig(fee_bps=0, slippage_bps=0, perp_base_fee_bps=0,
                      max_hourly_rate_bps_long=patch.pop('max_hourly_rate_bps_long', 0),
                      max_hourly_rate_bps_short=patch.pop('max_hourly_rate_bps_short', 0), **patch)


def bars(closes=(100., 100.), opens=None):
    close = np.asarray(closes, dtype=float)
    op = np.asarray(opens if opens is not None else closes, dtype=float)
    return dict(ts=1_700_000_000 + np.arange(len(close), dtype=np.int64) * 86400,
                open=op, high=np.maximum(op, close), low=np.minimum(op, close),
                close=close, volume=np.ones(len(close)))


class Always:
    name = 'audit-always'
    params = {}
    def warmup_bars(self): return 0
    def on_bar(self, history): return 1.


class EngineAudit(unittest.TestCase):
    def test_short_resize_keeps_zero_cost_gross_and_net_identical(self):
        for side in (Side.SHORT, Side.LONG):
            for target in (2000., 500.):
                with self.subTest(side=side, target=target):
                    book = _Book(EngineConfig(mode=Mode.PERP, costs=zero_cost()))
                    book.open(1000, side, 100, 0, 0)
                    book.resize(target, 100, 1, 1)
                    self.assertAlmostEqual(book.equity(100), 10000)
                    self.assertAlmostEqual(book.gross_equity(100), book.equity(100))
                    book.close(110, 2, 2, 'final')
                    self.assertAlmostEqual(book.gross_equity(110), book.equity(110))

    def test_isolated_gap_liquidation_preserves_unposted_cash(self):
        for side, price in ((Side.LONG, 70), (Side.SHORT, 130)):
            book = _Book(EngineConfig(mode=Mode.PERP, leverage=10, initial_capital=1000, costs=zero_cost()))
            book.open(1000, side, 100, 0, 0)
            self.assertEqual(book.cash, 900)
            book.close(price, 1, 1, 'liquidation')
            self.assertAlmostEqual(book.cash, 900)
            self.assertAlmostEqual(book.trades[-1].realized_pnl, -100)
            self.assertAlmostEqual(book.gross_equity(price), book.equity(price))

    def test_open_fill_accrues_held_bar_and_open_exit_does_not_accrue_an_extra_bar(self):
        class Exit(Always):
            def on_bar(self, history): return 1. if history.i == 0 else 0.
        cfg = EngineConfig(mode=Mode.PERP, fill_delay=1,
                           costs=zero_cost(max_hourly_rate_bps_long=1, utilization=1))
        for strategy, arrays in ((Always(), bars()), (Exit(), bars((100., 100., 100.)))):
            with self.subTest(strategy=strategy.name, length=len(arrays['close'])):
                result = run_backtest(strategy, arrays, cfg)
                self.assertAlmostEqual(sum(t.borrow_fee_settled for t in result.trades), 24)
                self.assertAlmostEqual(result.metrics.final_equity, 9976)
        result = run_backtest(Always(), bars((100.,)), EngineConfig(mode=Mode.PERP, fill_delay=0, costs=cfg.costs))
        self.assertEqual(result.metrics.total_borrow_fees, 0)

    def test_mode_strings_cannot_bypass_perp_controls(self):
        arrays = bars((100., 50.), (100., 100.))
        a = run_backtest(Always(), arrays, EngineConfig(mode='perp', leverage=10, costs=zero_cost(), fill_delay=0))
        b = run_backtest(Always(), arrays, EngineConfig(mode=Mode.PERP, leverage=10, costs=zero_cost(), fill_delay=0))
        self.assertEqual(a.liquidation_count, b.liquidation_count)
        np.testing.assert_array_equal(a.equity, b.equity)
        with self.assertRaises(ValueError): EngineConfig(mode='unknown')

    def test_material_engine_config_and_costs_refuse_nonfinite_or_invalid_values(self):
        for patch in ({'fill_delay': 1.5}, {'fill_delay': float('nan')}, {'initial_capital': float('nan')},
                      {'initial_capital': float('inf')}, {'leverage': float('nan')},
                      {'rebalance_threshold': float('nan')}, {'risk_free_rate': float('inf')}, {'interval': 'bogus'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError): EngineConfig(**patch)
        for field in ('fee_bps', 'slippage_bps', 'perp_base_fee_bps', 'max_hourly_rate_bps_long',
                      'max_hourly_rate_bps_short', 'min_hourly_rate_bps', 'max_lev_constant',
                      'utilization', 'kink_slope_multiplier'):
            for value in (float('nan'), float('inf'), -1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): CostConfig(**{field: value})
        for patch in ({'max_lev_constant': 0}, {'utilization': 1.1}, {'kink_utilization': float('nan')}, {'kink_utilization': 1.1}):
            with self.subTest(patch=patch), self.assertRaises(ValueError): CostConfig(**patch)

    def test_runtime_revalidates_mutated_configuration(self):
        cfg = EngineConfig()
        cfg.fill_delay = 1.5
        with self.assertRaises(ValueError): run_backtest(Always(), bars(), cfg)
        cfg = EngineConfig()
        cfg.costs.fee_bps = float('nan')
        with self.assertRaises(ValueError): run_backtest(Always(), bars(), cfg)

    def test_public_history_is_owned_readonly_and_cannot_mutate_input_or_expose_future(self):
        class Inspect(Always):
            def on_bar(inner, h):
                for name in ('ts', 'opens', 'highs', 'lows', 'closes', 'volumes'):
                    visible = getattr(h, name)
                    self.assertEqual(len(visible), h.i + 1)
                    self.assertIsNone(visible.base)
                    self.assertFalse(visible.flags.writeable)
                values = h.closes
                values.setflags(write=True)
                values[-1] = 123
                return 0.
        arrays = bars((100., 110., 120.))
        original = {k: v.copy() for k, v in arrays.items()}
        run_backtest(Inspect(), arrays, EngineConfig())
        for key, value in arrays.items(): np.testing.assert_array_equal(value, original[key])
        a = run_backtest(Always(), arrays, EngineConfig(costs=zero_cost(), fill_delay=0))
        b = run_backtest(Always(), arrays, EngineConfig(costs=zero_cost(), fill_delay=0))
        np.testing.assert_array_equal(a.equity, b.equity)

    def test_initial_cost_is_in_return_drawdown_and_cagr_without_extra_bars(self):
        for delay in (0, 1):
            arrays = bars()
            r = run_backtest(Always(), arrays, EngineConfig(fill_delay=delay, costs=CostConfig(fee_bps=100, slippage_bps=0)))
            expected = r.metrics.final_equity / 10000 - 1
            self.assertAlmostEqual(r.metrics.total_return, expected)
            self.assertAlmostEqual(r.metrics.max_drawdown, expected)
            self.assertAlmostEqual(r.metrics.cagr, (1 + expected) ** 365 - 1)
            self.assertEqual(r.metrics.bars, 2)
            self.assertEqual(len(r.equity), 2)
            np.testing.assert_array_equal(r.timestamps, arrays['ts'])

    def test_closing_trade_outcomes_include_entry_and_resize_costs_exactly_once(self):
        r = run_backtest(Always(), bars((100., 100., 101.5), (100., 100., 100.)),
                         EngineConfig(fill_delay=1, costs=CostConfig(fee_bps=100, slippage_bps=0)))
        self.assertLess(r.metrics.final_equity, 10000)
        self.assertEqual(r.metrics.win_rate, 0)
        self.assertEqual(r.metrics.profit_factor, 0)
        self.assertAlmostEqual(sum(t.realized_pnl for t in r.trades), r.metrics.final_equity - 10000)
        for mode, side in ((Mode.SPOT, Side.LONG), (Mode.PERP, Side.LONG), (Mode.PERP, Side.SHORT)):
            costs = CostConfig(fee_bps=10, perp_base_fee_bps=10, slippage_bps=5)
            book = _Book(EngineConfig(mode=mode, costs=costs))
            book.open(1000, side, 100, 0, 0)
            book.resize(2000, 100, 1, 1)
            book.resize(500, 110, 2, 2)
            book.close(110, 3, 3, 'final')
            self.assertAlmostEqual(sum(t.realized_pnl for t in book.trades), book.cash - 10000)
            self.assertEqual([t.realized_pnl for t in book.trades if t.reason in ('open', 'resize_up')], [0, 0])

    def test_break_even_close_is_decided_but_grid_entry_is_not(self):
        from backtester.core.gridsim import _GridBook
        from backtester.core.metrics import trade_stats
        result = run_backtest(Always(), bars(), EngineConfig(costs=zero_cost(), fill_delay=0))
        self.assertEqual(result.metrics.trade_count, 1)
        self.assertEqual(result.metrics.win_rate, 0)
        self.assertEqual(result.metrics.profit_factor, 0)
        book = _GridBook(1000, zero_cost())
        book.buy(100, 1, 0, 0)
        book.sell(100, 1, 1, 1, 'grid_exit')
        self.assertEqual(trade_stats(book.trades)['trade_count'], 1)

    def test_oos_trim_keeps_boundary_entry_cost_and_closing_cost_basis(self):
        from backtester.cli import _trimmed_metrics
        class Late(Always):
            def warmup_bars(self): return 1
        result = run_backtest(Late(), bars((100., 100., 100.)),
                              EngineConfig(fill_delay=0, costs=CostConfig(fee_bps=100, slippage_bps=0)))
        trimmed = _trimmed_metrics(result, 1, 365, 0)
        self.assertAlmostEqual(trimmed.total_return, result.metrics.final_equity / 10000 - 1)
        self.assertEqual(trimmed.bars, 2)
        self.assertEqual(trimmed.trade_count, 1)
        self.assertAlmostEqual(trimmed.avg_loss, result.metrics.final_equity - 10000)

    def test_initial_drawdown_peak_keeps_original_timestamp_and_duration(self):
        from backtester.core.metrics import max_drawdown
        result = max_drawdown(np.array([90., 95., 80.]), np.array([10, 20, 30]), initial_equity=100)
        self.assertEqual(result.peak_index, 0)
        self.assertEqual(result.peak_ts, 10)
        self.assertEqual(result.duration_bars, 2)
        self.assertAlmostEqual(result.max_drawdown, -0.2)


class GridAudit(unittest.TestCase):
    def test_rung_allocation_limit_refuses_before_building_the_ladder(self):
        from types import SimpleNamespace
        from backtester.core.gridsim import grid_levels, MAX_GRID_RUNGS
        for rungs in (10_001, 10**100, float('inf'), 1.5):
            with self.subTest(rungs=rungs), self.assertRaises(ValueError): GridConfig(100, 200, rungs, 25)
            with self.subTest(direct_rungs=rungs), self.assertRaises(ValueError):
                grid_levels(SimpleNamespace(lower=100, upper=200, rungs=rungs, spacing='arith'))
        self.assertEqual(len(grid_levels(GridConfig(100, 200, MAX_GRID_RUNGS, 25))), MAX_GRID_RUNGS)

    def test_actual_order_key_collisions_are_rejected_and_half_keys_match_javascript(self):
        with self.assertRaises(ValueError): GridConfig(100, 100.0000018, 4, 25, spacing='arith')
        self.assertEqual(_level_key('buy', 100.0000005), 'buy:100000001')

    def test_baseline_keeps_entry_cost_in_cumulative_return(self):
        r = run_grid_backtest(GridConfig(80, 120, 3, 25), bars((110., 110.)), costs=CostConfig(fee_bps=100, slippage_bps=0))
        self.assertAlmostEqual(r.baseline_metrics.total_return, r.baseline_metrics.final_equity / 10000 - 1)
        self.assertLess(r.baseline_metrics.max_drawdown, 0)
        self.assertEqual(r.baseline_metrics.bars, 2)

    def test_grid_never_plans_an_exit_below_the_actual_lot_entry(self):
        from collections import Counter
        from backtester.core.gridsim import Lot, _plan, grid_levels
        cfg = GridConfig(10, 20, 5, 25, spacing='arith')
        lot = Lot(qty=1, price=100, level=100, entry_fee_usd=0, entry_slippage_usd=0,
                  opened_index=0, opened_ts=0)
        skipped = Counter()
        orders = _plan(cfg, grid_levels(cfg), 30, [lot], skipped)
        self.assertFalse(any(o.side == 'sell' and o.level <= lot.price for o in orders))
        self.assertEqual(skipped['exit-not-above-entry'], 1)

    def test_grid_material_configuration_rejects_nonfinite_values(self):
        for field in ('lower', 'upper', 'notional_per_rung_usd', 'deadband_bps', 'min_order_usd'):
            for value in (float('nan'), float('inf')):
                values = dict(lower=80, upper=120, rungs=3, notional_per_rung_usd=25)
                values[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): GridConfig(**values)
        for patch in ({'initial_capital': float('nan')}, {'initial_capital': float('inf')},
                      {'carry_bps_per_hour': float('nan')}, {'carry_bps_per_hour': float('inf')}, {'risk_free_rate': float('nan')}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                run_grid_backtest(GridConfig(80, 120, 3, 25), bars(), **patch)


if __name__ == '__main__': unittest.main()
