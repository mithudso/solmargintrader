from __future__ import annotations

import unittest

from research.tv_single_ma import SingleMovingAverage


def intent(**kwargs):
    return kwargs


class SingleMovingAverageTests(unittest.TestCase):
    def test_default_warmup_and_first_consecutive_signal(self):
        strategy = SingleMovingAverage()
        outputs = [strategy.on_close(x, intent) for x in range(1, 12)]
        self.assertEqual(outputs[:8], [[]] * 8)
        self.assertEqual(outputs[8], [{"id": "MACrossLE", "action": "entry", "side": 1}])
        self.assertEqual(outputs[9:], [[], []])

    def test_equal_close_resets_counter_and_reentry_fires(self):
        strategy = SingleMovingAverage(length=2)
        outputs = [strategy.on_close(x, intent) for x in [1, 2, 2, 3, 1]]
        self.assertEqual(outputs, [[], [{"id": "MACrossLE", "action": "entry", "side": 1}], [],
                                   [{"id": "MACrossLE", "action": "entry", "side": 1}],
                                   [{"id": "MACrossSE", "action": "entry", "side": -1}]])

    def test_confirmation_requires_consecutive_bars(self):
        strategy = SingleMovingAverage(length=2, confirm_bars=2)
        outputs = [strategy.on_close(x, intent) for x in [1, 2, 3, 4, 2, 1]]
        self.assertEqual(outputs[2], [{"id": "MACrossLE", "action": "entry", "side": 1}])
        self.assertEqual(outputs[3:5], [[], []])
        self.assertEqual(outputs[5], [{"id": "MACrossSE", "action": "entry", "side": -1}])

    def test_missing_close_fails_without_mutating_state(self):
        strategy = SingleMovingAverage(length=2)
        strategy.on_close(1, intent)
        with self.assertRaises(ValueError):
            strategy.on_close(float("nan"), intent)
        self.assertEqual(strategy.on_close(2, intent), [{"id": "MACrossLE", "action": "entry", "side": 1}])

    def test_length_one_always_equals_close_and_never_signals(self):
        strategy = SingleMovingAverage(length=1)
        self.assertEqual([strategy.on_close(x, intent) for x in [3, 9, 1]], [[], [], []])

    def test_future_prices_do_not_change_past_intents(self):
        prefix = [1, 2, 2, 3, 1]
        short, extended = SingleMovingAverage(2), SingleMovingAverage(2)
        first = [short.on_close(x, intent) for x in prefix]
        all_outputs = [extended.on_close(x, intent) for x in prefix + [100, 0]]
        self.assertEqual(first, all_outputs[:len(prefix)])

    def test_invalid_parameters_are_rejected(self):
        for kwargs in ({"length": 0}, {"confirm_bars": 0}, {"length": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SingleMovingAverage(**kwargs)

    def test_shared_emulator_next_open_and_reversal(self):
        try:
            from research.pine_bar_emulator import Bar, simulate
        except ModuleNotFoundError as exc:
            if exc.name != "research.pine_bar_emulator":
                raise
            self.skipTest("shared emulator has not been integrated")
        closes = [10.0, 12.0, 12.0, 14.0, 8.0, 7.0]
        strategy = SingleMovingAverage(length=2)
        bars = [Bar(i * 600, x, x, x, x) for i, x in enumerate(closes)]
        orders = [strategy.on_close(x) for x in closes]
        result = simulate(bars, orders, default_qty=1, step_seconds=600,
                          fee_bps=10, slippage_bps=0)
        fills = result["fills"]
        self.assertEqual([(f["timestamp"], f["event"], f["side"]) for f in fills],
                         [(1200, "open", 1), (3000, "close", -1), (3000, "open", -1)])
        self.assertTrue(all(f["fee"] > 0 for f in fills))


if __name__ == "__main__":
    unittest.main()
