"""Known-answer auxiliary defects: gap-aligned labels and causal quote time."""
from __future__ import annotations

import importlib
import unittest

import numpy as np

from research.strategy_snapshots import ensure_snapshots

ensure_snapshots()


def module(variant: str, name: str):
    return importlib.import_module(f'research.strategy_experiment.{variant}.core.{name}')


class CandidateAuxiliaryTests(unittest.TestCase):
    @staticmethod
    def stats(sc):
        bars = sc.Bars(np.arange(3) * 300,
                       np.array([100., 120., 130.]), np.array([101., 121., 131.]),
                       np.array([99., 109., 119.]), np.array([100., 110., 120.]), np.ones(3))
        ev = sc.Evaluation(bars, sc.default_config(), {}, {}, np.full(3, 'neutral'),
                           np.ones(3), np.ones(3), np.zeros(3, dtype=bool), np.ones(3, dtype='int8'))
        return sc.forecast_stats([ev])

    def test_gap_returns_use_executable_next_open(self):
        old = self.stats(module('original', 'scorecard'))
        new = self.stats(module('candidate', 'scorecard'))
        self.assertEqual(old['hit_rate'], 1.)
        self.assertGreater(old['net_bps_per_call_if_one_bar'], 0.)
        self.assertEqual(new['hit_rate'], 0.)
        self.assertEqual(new['active_majority_baseline'], 1.)
        self.assertLess(new['net_bps_per_call_if_one_bar'], 0.)
        self.assertEqual(new['net_bps_per_call_if_one_bar'], new['horizons'][0]['net_bps'])
        # Independent expected executable gross is the average of two log losses.
        expected = 5000 * (np.log(110 / 120) + np.log(120 / 130))
        self.assertAlmostEqual(new['gross_bps_per_call'], round(expected, 3))

    @staticmethod
    def replay(ts, quote_ts):
        tri = ts.Triangle('A', 'B')
        quotes = {'A-USD': (100, 100, 100, 100, quote_ts),
                  'B-USD': (10, 10, 100, 100, quote_ts),
                  'A-B': (11, 11, 100, 100, quote_ts)}
        return ts.run_triangle_backtest(ts.TriangleConfig(taker_fee_bps=0, latency_s=0),
                                        [(100, quotes)], [tri])

    def test_future_quotes_cannot_trade(self):
        self.assertEqual(self.replay(module('original', 'trianglesim'), 200).executed, 1)
        self.assertEqual(self.replay(module('candidate', 'trianglesim'), 200).executed, 0)

    def test_current_quotes_still_trade(self):
        self.assertEqual(self.replay(module('candidate', 'trianglesim'), 100).executed, 1)

    def test_stale_or_nonfinite_quotes_refused(self):
        for value in (90, float('nan'), float('inf')):
            with self.subTest(timestamp=value):
                self.assertEqual(self.replay(module('candidate', 'trianglesim'), value).executed, 0)
