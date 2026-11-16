"""Price Channel source intent traces; this does not establish TV parity."""
import unittest

from research.pine_bar_emulator import Bar, simulate
from research.tv_price_channel_intents import price_channel_intents


class PriceChannelTests(unittest.TestCase):
    def test_default_guard_needs_twenty_one_bars(self):
        self.assertEqual(price_channel_intents([5] * 20, [6] * 20, [4] * 20), [])
        intents = price_channel_intents([5] * 21, [6] * 21, [4] * 21)
        self.assertEqual([(x.id, x.side, x.kind, x.stop, x.qty) for x in intents],
                         [("PChLE", 1, "stop", 6, None), ("PChSE", -1, "stop", 4, None)])

    def test_current_extrema_included_oldest_excluded(self):
        orders = price_channel_intents([5, 6, 7, 8], [100, 8, 9, 11], [1, 5, 4, 3], 3)
        self.assertEqual([x.stop for x in orders], [11, 3])

    def test_guard_is_not_cancel(self):
        self.assertEqual(price_channel_intents([float('nan'), 5, 5], [6]*3, [4]*3, 2), [])

    def test_orders_fill_only_after_signal_bar(self):
        bars = [Bar(0,5,6,4,5), Bar(60,5,6,4,5), Bar(120,5,7,4,6), Bar(180,6,8,5,7)]
        groups = [price_channel_intents([x.close for x in bars[:i+1]],
                  [x.high for x in bars[:i+1]], [x.low for x in bars[:i+1]], 2)
                  for i in range(len(bars))]
        result = simulate(bars, groups, default_qty=1, step_seconds=60)
        self.assertEqual(result['fills'][0]['timestamp'], 180)
        self.assertEqual(result['fills'][0]['id'], 'PChLE')

    def test_invalid_fields_rejected(self):
        with self.assertRaises(ValueError):
            price_channel_intents([5,5,5], [6], [4,4,4], 2)


if __name__ == '__main__':
    unittest.main()
