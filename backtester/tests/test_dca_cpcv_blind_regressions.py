"""Synthetic known answers from the independent backtester acceptance gate."""

from __future__ import annotations

import itertools
import unittest

import numpy as np

from backtester.core.cpcv import pbo_cscv
from backtester.core.dcasim import DcaConfig, run_dca_backtest
from backtester.core.types import CostConfig


def market_bars():
    opens = np.array([100.0, 100.0, 120.0])
    closes = np.array([100.0, 120.0, 120.0])
    return {
        "ts": 1_800_000_000 + np.arange(3) * 3600,
        "open": opens,
        "high": np.maximum(opens, closes),
        "low": np.minimum(opens, closes),
        "close": closes,
        "volume": np.ones(3),
    }


class DcaObservedOpenTests(unittest.TestCase):
    def run_fixture(self, bars):
        return run_dca_backtest(
            DcaConfig(max_safety_orders=0, take_profit_pct=50),
            bars,
            initial_capital=1000,
            interval="1h",
            costs=CostConfig(fee_bps=6, slippage_bps=2),
            close_at_end=False,
        )

    def test_missing_open_refuses_instead_of_filling_at_future_close(self):
        bars = market_bars()
        del bars["open"]
        with self.assertRaisesRegex(ValueError, "open"):
            self.run_fixture(bars)

    def test_observed_next_open_fill_includes_adverse_costs(self):
        result = self.run_fixture(market_bars())
        trade = result.trades[0]
        self.assertEqual(trade.bar_index, 1)
        self.assertEqual(trade.ts, 1_800_003_600)
        self.assertAlmostEqual(trade.price, 100.02)
        self.assertAlmostEqual(trade.fee, 0.06)

    def test_a_different_future_close_does_not_reprice_the_opening_fill(self):
        original = self.run_fixture(market_bars()).trades[0]
        changed = market_bars()
        changed["close"][1] = 140.0
        changed["high"][1] = 140.0
        actual = self.run_fixture(changed).trades[0]
        self.assertEqual((actual.price, actual.units), (original.price, original.units))

    def test_unused_volume_remains_optional(self):
        bars = market_bars()
        del bars["volume"]
        self.assertAlmostEqual(self.run_fixture(bars).trades[0].price, 100.02)


class CscvTiedRankTests(unittest.TestCase):
    def test_identical_test_scores_never_rank_strictly_below_their_median(self):
        blocks = [np.array([0.01, -0.01, 0.01]) for _ in range(4)]
        for labels in itertools.permutations(("first", "second", "third")):
            with self.subTest(labels=labels):
                result = pbo_cscv(dict.fromkeys(labels, blocks), max_splits=6)
                self.assertEqual(result["n_splits"], 6)
                self.assertEqual(result["pbo"], 0)

    def test_actual_out_of_sample_losers_still_count_among_tied_splits(self):
        strong = np.array([0.02, -0.01, 0.02])
        weak = -strong
        result = pbo_cscv(
            {"a": [strong, strong, weak, weak], "b": [weak, weak, strong, strong]},
            max_splits=6,
        )
        self.assertEqual(result["n_splits"], 6)
        self.assertAlmostEqual(result["pbo"], 1 / 3)

    def test_distinct_generalizing_winner_remains_above_the_median(self):
        result = pbo_cscv(
            {
                "weak": [np.array([0.01, -0.02, 0.01])] * 4,
                "strong": [np.array([0.02, -0.01, 0.02])] * 4,
            },
            max_splits=6,
        )
        self.assertEqual(result["n_splits"], 6)
        self.assertEqual(result["pbo"], 0)


if __name__ == "__main__":
    unittest.main()
