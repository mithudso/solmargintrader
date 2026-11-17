from __future__ import annotations

import unittest

from research.pine_bar_emulator import Bar
from research.tradingview_pivot_reversal import pivot_intents


def candles(highs):
    return [Bar(i*900, 9, high, 8, 9) for i, high in enumerate(highs)]


class TradingViewPivotTests(unittest.TestCase):
    def test_confirmation_is_delayed_and_source_has_no_implicit_cancel(self):
        bars = candles([10, 11, 12, 13, 20, 18, 17, 21])
        out = pivot_intents(bars, step_seconds=900, tick_size=.01)
        self.assertTrue(all(not out[i] for i in range(6)))
        self.assertEqual(out[6][0].id, 'PivRevLE')
        self.assertAlmostEqual(out[6][0].stop, 20.01)
        self.assertEqual(out[7], [])
        for end in range(1, len(bars)+1):
            self.assertEqual(pivot_intents(bars[:end], step_seconds=900, tick_size=.01), out[:end])

    def test_equal_highs_are_explicit_sensitivity(self):
        bars = candles([10, 11, 12, 13, 20, 20, 17, 16])
        strict = pivot_intents(bars, step_seconds=900, tick_size=.01, ties='strict')
        latest = pivot_intents(bars, step_seconds=900, tick_size=.01, ties='latest')
        self.assertFalse(strict[7])
        self.assertEqual(latest[7][0].id, 'PivRevLE')
        self.assertAlmostEqual(latest[7][0].stop, 20.01)

    def test_missing_bars_and_unusable_tick_fail_closed(self):
        bars = candles([10, 11, 12, 13, 20, 18, 17])
        with self.assertRaises(ValueError):
            pivot_intents(bars[:2]+bars[3:], step_seconds=900, tick_size=.01)
        with self.assertRaises(ValueError):
            pivot_intents(bars, step_seconds=900, tick_size=0)


if __name__ == '__main__':
    unittest.main()
