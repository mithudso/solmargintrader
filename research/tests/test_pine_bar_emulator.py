from __future__ import annotations

import unittest

from research.pine_bar_emulator import Bar, Intent, simulate


class PineBarEmulatorTests(unittest.TestCase):
    def test_next_open_and_reversal_fees(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 12, 13, 11, 12), Bar(1800, 11, 12, 10, 11)]
        intents = [[Intent('L', 'entry', 1)], [Intent('S', 'entry', -1)], []]
        result = simulate(bars, intents, default_qty=2, step_seconds=900, fee_bps=100)
        self.assertEqual([f['price'] for f in result['fills']], [12, 11, 11])
        self.assertEqual([f['quantity'] for f in result['fills']], [2, 2, 2])
        self.assertAlmostEqual(result['final_equity'], 100000 - 2 - .68)
        self.assertEqual(result['open_quantity'], -2)

    def test_stop_replacement_cancel_and_gap_at_open(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 10, 11, 9, 10),
                Bar(1800, 13, 14, 12, 13), Bar(2700, 13, 14, 12, 13)]
        intents = [[Intent('L', 'entry', 1, 'stop', 12)],
                   [Intent('L', 'entry', 1, 'stop', 12.5)],
                   [Intent('L', 'cancel', 1)], []]
        result = simulate(bars, intents, default_qty=1, step_seconds=900)
        self.assertEqual(result['fills'][0]['price'], 13)
        self.assertEqual(result['fills'][0]['timestamp'], 1800)
        self.assertEqual(result['pending_stops'], [])

    def test_already_better_stop_activates_before_adverse_gap(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 8, 8.5, 7, 8)]
        orders = [[Intent('L', 'entry', 1, 'stop', 9)], []]
        result = simulate(bars, orders, default_qty=1, step_seconds=900)
        self.assertEqual(result['fills'][0]['price'], 8)

    def test_two_sided_stop_follows_path_and_equal_tie_policy(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 10, 12, 8, 10)]
        orders = [[Intent('L', 'entry', 1, 'stop', 11), Intent('S', 'entry', -1, 'stop', 9)], []]
        high = simulate(bars, orders, default_qty=1, step_seconds=900, tie_policy='high-first')
        low = simulate(bars, orders, default_qty=1, step_seconds=900, tie_policy='low-first')
        self.assertEqual([x['side'] for x in high['fills']], [1, -1, -1])
        self.assertEqual([x['side'] for x in low['fills']], [-1, 1, 1])

    def test_noncausal_close_and_bad_inputs_fail_closed(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 10, 11, 9, 10)]
        intents = [[Intent('L', 'entry', 1), Intent('L', 'close', 1)], []]
        result = simulate(bars, intents, default_qty=1, step_seconds=900)
        self.assertEqual(result['open_quantity'], 1)
        with self.assertRaises(ValueError):
            simulate(bars, intents, default_qty=0, step_seconds=900)
        with self.assertRaises(ValueError):
            simulate([bars[0], Bar(1800, 10, 11, 9, 10)], intents, default_qty=1, step_seconds=900)
        with self.assertRaises(ValueError):
            Intent('L', 'entry', 1, 'stop')


if __name__ == '__main__':
    unittest.main()
