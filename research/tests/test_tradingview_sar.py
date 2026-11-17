from __future__ import annotations

import unittest

from research.pine_bar_emulator import Bar
from research.tradingview_sar import sar_intents


class TradingViewSARTests(unittest.TestCase):
    def setUp(self):
        self.bars = [Bar(0, 10, 11, 9, 10), Bar(900, 10, 13, 10, 12),
                     Bar(1800, 12, 14, 11, 13), Bar(2700, 12, 12, 8, 9)]

    def test_initialization_extreme_acceleration_and_reversal(self):
        out = sar_intents(self.bars, step_seconds=900)
        self.assertEqual(out[0], [])
        self.assertEqual((out[1][0].id, out[1][1].id), ('ParSE', 'ParLE'))
        self.assertAlmostEqual(out[1][0].stop, 9.08)
        self.assertAlmostEqual(out[2][0].stop, 9.2)
        self.assertEqual((out[3][0].id, out[3][1].id), ('ParLE', 'ParSE'))
        self.assertAlmostEqual(out[3][0].stop, 13.88)

    def test_prefix_invariant_and_gap_rejected(self):
        whole = sar_intents(self.bars, step_seconds=900)
        for end in range(1, len(self.bars)+1):
            self.assertEqual(sar_intents(self.bars[:end], step_seconds=900), whole[:end])
        with self.assertRaises(ValueError):
            sar_intents(self.bars[:1] + self.bars[2:], step_seconds=900)
        with self.assertRaises(ValueError):
            sar_intents(self.bars, step_seconds=900, start=.3, maximum=.2)


if __name__ == '__main__':
    unittest.main()
