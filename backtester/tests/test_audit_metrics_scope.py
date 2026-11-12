"""Small fixed regressions for audit accounting and publication boundaries."""
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester import voltycli
from backtester.core import cpcv, gridsim, report, trianglesim
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.types import CostConfig


def bars(prices, first=0):
    p = np.asarray(prices, dtype=float)
    return {"ts": np.arange(first, first + len(p)) * 86400, "open": p, "high": p, "low": p, "close": p, "volume": np.ones(len(p))}


class CheckpointLong(BuyAndHold):
    def checkpoint_state(self):
        return {}

    def restore_state(self, state):
        pass


class MetricsScopeTests(unittest.TestCase):
    def test_block_preserves_entry_and_exit_costs_at_zero_warmup(self):
        cfg = EngineConfig(fill_delay=0, costs=CostConfig(fee_bps=100, slippage_bps=0))
        data = bars([100] * 4)
        result = run_backtest(BuyAndHold(), data, cfg)
        block = cpcv.evaluate_block(BuyAndHold, data, 0, 4, cfg)
        self.assertAlmostEqual(np.prod(1 + block.returns) - 1, result.equity[-1] / cfg.initial_capital - 1)
        self.assertLess(block.returns[0], 0)

    def test_pbo_ties_are_order_independent_and_not_below_median(self):
        values = [np.array([-.01, .02, .01])] * 6
        forward = cpcv.pbo_cscv({'a': values, 'b': values}, max_splits=11)
        reverse = cpcv.pbo_cscv({'b': values, 'a': values}, max_splits=11)
        self.assertEqual(forward, reverse)
        self.assertEqual(forward['pbo'], 0)
        selected = cpcv.split_positions(20, 11)
        self.assertEqual(len(selected), 11)
        self.assertTrue({0, 19}.issubset(selected))

    def test_continuation_reports_segment_return_and_retains_account_value(self):
        cfg = EngineConfig(fill_delay=0, costs=CostConfig(fee_bps=0, slippage_bps=0))
        prefix = run_backtest(CheckpointLong(), bars([100, 110]), cfg, close_at_end=False)
        resumed = run_backtest(CheckpointLong(), bars([110, 110], first=2), cfg, continuation=prefix.continuation)
        self.assertAlmostEqual(resumed.equity[-1], 11000)
        self.assertAlmostEqual(resumed.metrics.total_return, 0)
        self.assertAlmostEqual(resumed.gross_metrics.total_return, 0)

    def test_grid_lot_planning_preserves_nearest_tie_and_exit_without_linear_search(self):
        cfg = gridsim.GridConfig(100, 200, 4, 100, min_order_usd=0)
        levels = [100., 125., 150., 175., 200.]
        lot = gridsim.Lot(1, 137.5, 125, 0, 0, 0, 0)
        with patch.object(gridsim, 'nearest_level_index', side_effect=AssertionError('linear scan')):
            planned = gridsim._plan(cfg, levels, 160, [lot], Counter())
        exits = [x for x in planned if x.side == 'sell']
        self.assertEqual(exits[0].level, 150)

    def test_triangle_downstream_capacity_is_converted_to_starting_currency(self):
        tri = trianglesim.Triangle('A', 'B')
        quotes = {'A-USD': (9., 10., None, None, 0.), 'B-USD': (6., 7., 1., None, 0.), 'A-B': (2., 2.1, None, None, 0.)}
        self.assertEqual(trianglesim._size_cap_usd(tri, 'forward', quotes), 5.)
        self.assertAlmostEqual(trianglesim._size_cap_usd(tri, 'forward', quotes, 100), 5 / .99**2)
        for size, quote_time in [(-1, 0), (0, 0), (1, 1), (float('nan'), 0)]:
            bad = dict(quotes, **{'B-USD': (6., 7., size, None, quote_time)})
            result = trianglesim.run_triangle_backtest(trianglesim.TriangleConfig(latency_s=0, min_edge_bps=0), [(0, bad), (0, bad)], [tri])
            self.assertEqual(len(result.cycles), 0)

    def test_report_refuses_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / 'outside'
            outside.write_text('preserve')
            output = root / 'output'
            output.mkdir()
            (output / 'comparison.csv').symlink_to(outside)
            manifest = SimpleNamespace(to_dict=lambda: {'strategies': {'fixture': {}}})
            split = SimpleNamespace(full=SimpleNamespace(strategy_name='fixture'))
            with patch.object(report, 'results_frame', side_effect=lambda *a, **k: pd.DataFrame({'strategy': ['fixture']})), self.assertRaisesRegex(ValueError, 'symlink'):
                report.write_outputs(output, [split], manifest, '')
            self.assertEqual(outside.read_text(), 'preserve')

    def test_volty_rejects_invalid_source_before_aggregation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = pd.DataFrame({'timestamp': [0, 60, 121, 180], 'open': [1.] * 4, 'high': [1., np.nan, 1., 1.], 'low': [1.] * 4, 'close': [1.] * 4, 'volume': [1.] * 4})
            source = root / 'ZEC_1m.csv'
            frame.to_csv(source, index=False)
            (root / 'manifest.json').write_text(json.dumps({'1m': {'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}}))
            with self.assertRaisesRegex(ValueError, 'full-source'):
                voltycli.prepare(root, root / 'out', 1)
            self.assertFalse((root / 'out').exists())
