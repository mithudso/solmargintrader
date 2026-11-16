from __future__ import annotations

import unittest

from research.oracle_compare import compare, size_at_close
from research.pine_bar_emulator import Bar, Intent


class CommonComparisonTests(unittest.TestCase):
    def test_equal_notional_is_fixed_before_next_open(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 20, 21, 19, 20), Bar(1800, 22, 23, 21, 22)]
        orders = [[Intent('L', 'entry', 1, qty=3)], [Intent('L', 'close', 1)], []]
        self.assertEqual(size_at_close(bars, orders)[0][0].qty, 100)
        result = compare(bars, orders, step_seconds=900, default_qty=1)
        equal = result[0]
        source = result[2]
        self.assertEqual(equal['closed_trades'], 1)
        self.assertEqual(equal['final_equity'], 100200)
        self.assertEqual(source['final_equity'], 100006)
        self.assertLess(result[1]['final_equity'], equal['final_equity'])

    def test_hooks_guard_each_individual_scenario(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 10, 11, 9, 10)]
        calls = []
        compare(bars, [[], []], step_seconds=900, default_qty=1,
                before_run=lambda: calls.append('before'), after_run=lambda: calls.append('after'))
        self.assertEqual(calls, ['before', 'after'] * 4)

    def test_mismatched_rows_rejected(self):
        with self.assertRaises(ValueError):
            size_at_close([Bar(0, 10, 11, 9, 10)], [])


if __name__ == '__main__':
    unittest.main()
