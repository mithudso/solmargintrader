from __future__ import annotations

import unittest

from research.oracle_common_window import aggregate, equal_notional_qty


class CommonWindowTests(unittest.TestCase):
    def test_aggregate_preserves_ohlc_and_alignment(self):
        rows = [[i*60, 10+i, 12+i, 9+i, 11+i, 0] for i in range(30)]
        a, b = aggregate(rows, 600), aggregate(rows, 900)
        self.assertEqual((len(a), len(b)), (3, 2))
        self.assertEqual((a[0].open, a[0].high, a[0].low, a[0].close), (10, 21, 9, 20))
        self.assertEqual(b[1].timestamp, 900)

    def test_incomplete_and_gapped_input_fails_closed(self):
        rows = [[i*60, 10, 11, 9, 10, 0] for i in range(30)]
        with self.assertRaises(ValueError):
            aggregate([], 600)
        with self.assertRaises(ValueError):
            aggregate(rows[:-1], 600)
        rows[2][0] += 60
        with self.assertRaises(ValueError):
            aggregate(rows, 600)

    def test_equal_notional_fixed_at_signal_close(self):
        self.assertEqual(equal_notional_qty(250), 4)
        with self.assertRaises(ValueError):
            equal_notional_qty(0)
        with self.assertRaises(ValueError):
            equal_notional_qty(float('nan'))


if __name__ == '__main__':
    unittest.main()
