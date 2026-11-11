"""Economic and causality controls for the fixed historical followups."""

from __future__ import annotations

import unittest
from itertools import pairwise

import numpy as np
import pandas as pd

from backtester.core.data import frame_to_arrays
from backtester.core.zec_ensemble import component_signal_series
from research.meta_followups import (
    FrozenTargets,
    fixed_slot_curve,
    longest_common_calendar,
    replay,
)


def bars(n=500, first=1700002800, seconds=3600):
    close = np.full(n, 100.0)
    return pd.DataFrame({"timestamp": first + np.arange(n) * seconds, "open": close, "high": close + 1, "low": close - 1, "close": close, "volume": np.full(n, 100.0)})


class FollowupTests(unittest.TestCase):
    def test_passive_charges_two_sides_exactly_and_costs_are_monotone(self):
        arrays = frame_to_arrays(bars(20))
        returns = []
        for fee in (0, 10, 50, 90):
            result, metrics = replay(arrays, np.ones(20), 8, fee)
            rate = (fee + 2) / 10000
            self.assertAlmostEqual(metrics["final_equity"], 10000 * (1 - rate) / (1 + rate), places=9)
            self.assertEqual(len(result.trades), 2)
            self.assertEqual(result.trades[0].bar_index, 8)
            returns.append(metrics["return_pct"])
        self.assertTrue(all(a > b for a, b in pairwise(returns)))

    def test_training_history_is_only_indicator_warmup(self):
        frame = bars(80)
        frame.loc[:29, ["open", "high", "low", "close"]] *= 4
        result, _ = replay(frame_to_arrays(frame), np.ones(80), 30, 90)
        np.testing.assert_allclose(result.equity[:30], 10000)
        self.assertTrue(all(t.bar_index >= 30 for t in result.trades))
        self.assertEqual(result.trades[0].bar_index, 30)

    def test_completed_signal_can_fill_only_on_next_observation(self):
        frame = bars(20)
        frame.loc[10:, ["open", "high", "low", "close"]] *= 2
        targets = np.zeros(20)
        targets[10:] = 1
        result, _ = replay(frame_to_arrays(frame), targets, 5, 0, execution_bps=0)
        self.assertEqual(result.trades[0].bar_index, 11)
        self.assertAlmostEqual(result.trades[0].price, 200)
        self.assertAlmostEqual(result.equity[-1], 10000)

    def test_component_signals_are_prefix_causal_under_future_price_poisoning(self):
        frame = bars(450)
        value = 100 * np.exp(np.linspace(0, 0.6, len(frame)) + 0.05 * np.sin(np.arange(len(frame)) / 5))
        for column in ("open", "close"):
            frame[column] = value
        frame.high, frame.low = value * 1.01, value * 0.99
        arrays = frame_to_arrays(frame)
        poisoned = {key: value.copy() for key, value in arrays.items()}
        for key in ("open", "close", "high", "low"):
            poisoned[key][320:] *= 6
        for spec in ({"strategy": "bb_breakout", "params": {"window": 40, "num_std": 2.5}}, {"strategy": "sma_regime", "params": {"window": 200}}):
            a = component_signal_series(spec, arrays, "1h")
            b = component_signal_series(spec, poisoned, "1h")
            np.testing.assert_array_equal(a[:320], b[:320])

    def test_common_calendar_does_not_bridge_gaps_or_choose_by_return(self):
        first = bars(12)
        second = first.drop(index=[3, 4]).reset_index(drop=True)
        chosen, metadata = longest_common_calendar({"A": first, "B": second}, minimum=3)
        self.assertEqual(metadata["chosen_bars"], 7)
        self.assertEqual(chosen["A"].timestamp.iloc[0], first.timestamp.iloc[5])
        self.assertTrue(np.all(np.diff(chosen["A"].timestamp) == 3600))
        with self.assertRaisesRegex(ValueError, "insufficient"):
            longest_common_calendar({"A": first, "B": second}, minimum=10)

    def test_remove_coin_to_cash_keeps_other_weights_and_idle_slots(self):
        curves = {"ZEC": np.array([1, 3.0]), "BTC": np.array([1, 1.1])}
        np.testing.assert_allclose(fixed_slot_curve(curves, ["ZEC", "BTC"], slots=10), [1, 1.21])
        np.testing.assert_allclose(fixed_slot_curve(curves, ["ZEC", "BTC"], slots=10, removed_to_cash=("ZEC",)), [1, 1.01])
        np.testing.assert_allclose(fixed_slot_curve(curves, ["ZEC", "BTC"], slots=10, removed_to_cash=("ZEC", "BTC")), 1)
        with self.assertRaises(ValueError):
            fixed_slot_curve(curves, ["ZEC", "ZEC"], slots=10)
        with self.assertRaises(ValueError):
            fixed_slot_curve(curves, ["ZEC", "BTC"], slots=1)

    def test_target_domain_and_boundary_types_fail_closed(self):
        for target in ([0, 1.1], [0, -1], [0, np.nan]):
            with self.assertRaises(ValueError):
                FrozenTargets(target)
        arrays = frame_to_arrays(bars(10))
        for boundary in (True, 0, 10, 1.5):
            with self.assertRaises(ValueError):
                replay(arrays, np.ones(10), boundary, 10)
        with self.assertRaises(ValueError):
            replay(arrays, np.ones(9), 5, 10)


if __name__ == "__main__":
    unittest.main()
