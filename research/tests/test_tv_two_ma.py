from __future__ import annotations

import unittest

from research.tv_two_ma import TwoMovingAverages


def intent(**kwargs):
    return kwargs


class TwoMovingAveragesTests(unittest.TestCase):
    def test_crosses_from_previous_equality_and_strict_comparisons(self):
        strategy = TwoMovingAverages(2, 3)
        got = [strategy.on_close(x, intent) for x in [2, 2, 2, 3, 4, 3, 1, 1, 3]]
        self.assertEqual(got[3], [{"id": "MA2CrossLE", "action": "entry", "side": 1}])
        self.assertEqual(got[6], [{"id": "MA2CrossSE", "action": "entry", "side": -1}])
        self.assertEqual(got[8], [{"id": "MA2CrossLE", "action": "entry", "side": 1}])
        self.assertEqual([i for i, x in enumerate(got) if x], [3, 6, 8])

    def test_first_defined_averages_do_not_create_a_previous_cross(self):
        strategy = TwoMovingAverages(2, 3)
        self.assertEqual([strategy.on_close(x, intent) for x in [1, 2, 3, 4]], [[], [], [], []])

    def test_same_lengths_never_cross(self):
        strategy = TwoMovingAverages(2, 2)
        self.assertEqual([strategy.on_close(x, intent) for x in [1, 4, 2, 5]], [[], [], [], []])

    def test_invalid_observation_does_not_mutate_history(self):
        strategy = TwoMovingAverages(2, 3)
        for x in (2, 2, 2):
            strategy.on_close(x, intent)
        with self.assertRaises(ValueError):
            strategy.on_close(float("nan"), intent)
        self.assertEqual(strategy.on_close(3, intent, qty=100),
                         [{"id": "MA2CrossLE", "action": "entry", "side": 1, "qty": 100}])

    def test_future_observations_cannot_change_past_intents(self):
        prefix = [2, 2, 2, 3, 4, 3, 1]
        a, b = TwoMovingAverages(2, 3), TwoMovingAverages(2, 3)
        self.assertEqual([a.on_close(x, intent) for x in prefix],
                         [b.on_close(x, intent) for x in prefix + [10]][:len(prefix)])

    def test_invalid_lengths_and_quantity(self):
        for values in ((0, 2), (2, -1), (True, 2)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                TwoMovingAverages(*values)
        with self.assertRaises(ValueError):
            TwoMovingAverages().on_close(1, intent, qty=0)

    def test_shared_emulator_fills_crosses_on_following_open(self):
        try:
            from research.pine_bar_emulator import Bar, simulate
        except ModuleNotFoundError as exc:
            if exc.name != "research.pine_bar_emulator":
                raise
            self.skipTest("shared emulator has not been integrated")
        closes = [2., 2., 2., 3., 4., 3., 1., 1., 3., 4.]
        strategy = TwoMovingAverages(2, 3)
        bars = [Bar(i * 600, x, x, x, x) for i, x in enumerate(closes)]
        orders = [strategy.on_close(x) for x in closes]
        result = simulate(bars, orders, default_qty=1, step_seconds=600,
                          fee_bps=10, slippage_bps=0)
        self.assertEqual([(f["timestamp"], f["event"], f["side"]) for f in result["fills"]],
                         [(2400, "open", 1), (4200, "close", -1), (4200, "open", -1),
                          (5400, "close", 1), (5400, "open", 1)])


if __name__ == "__main__":
    unittest.main()
