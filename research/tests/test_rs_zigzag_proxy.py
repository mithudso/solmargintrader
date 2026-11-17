from __future__ import annotations

import unittest

from research.rs_zigzag_proxy import aggregate


class ProxyAggregationTests(unittest.TestCase):
    def test_exact_ohlc_and_both_periods(self):
        rows = [[i*60, 10+i, 12+i, 9+i, 11+i, 0] for i in range(30)]
        ten, fifteen = aggregate(rows, 600), aggregate(rows, 900)
        self.assertEqual(len(ten), 3)
        self.assertEqual(len(fifteen), 2)
        self.assertEqual((ten[0].timestamp, ten[0].open, ten[0].high, ten[0].low, ten[0].close),
                         (0, 10, 21, 9, 20))
        self.assertEqual(fifteen[1].timestamp, 900)

    def test_missing_and_partial_groups_fail_closed(self):
        rows = [[i*60, 10, 11, 9, 10, 0] for i in range(30)]
        with self.assertRaises(ValueError):
            aggregate(rows[:-1], 600)
        rows[11][0] += 60
        with self.assertRaises(ValueError):
            aggregate(rows, 600)


if __name__ == '__main__':
    unittest.main()
