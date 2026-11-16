"""Channel Breakout has a deliberate asymmetrical source guard."""
import unittest

from research.pine_bar_emulator import Bar, simulate
from research.tv_channel_breakout_intents import channel_breakout_intents


class ChannelBreakoutTests(unittest.TestCase):
    def test_short_order_exists_before_long_guard(self):
        orders = channel_breakout_intents([10], [11], [9], .25)
        self.assertEqual([(x.id,x.side,x.stop) for x in orders], [('ChBrkSE',-1,8.75)])

    def test_guard_and_offset_are_distinct_from_price_channel(self):
        orders = channel_breakout_intents([10]*6, [11]*6, [9]*6, .25)
        self.assertEqual([(x.id,x.side,x.stop,x.qty) for x in orders],
                         [('ChBrkLE',1,11.25,None),('ChBrkSE',-1,8.75,None)])

    def test_current_extrema_and_rolling_boundary(self):
        orders = channel_breakout_intents([10]*4,[30,11,12,13],[1,9,8,7],.5,3)
        self.assertEqual([x.stop for x in orders], [13.5,6.5])

    def test_early_short_fills_next_bar(self):
        bars=[Bar(0,10,11,9,10),Bar(60,10,11,8,9)]
        orders=[channel_breakout_intents([b.close for b in bars[:i+1]],
                [b.high for b in bars[:i+1]], [b.low for b in bars[:i+1]], .25)
                for i in range(2)]
        result=simulate(bars,orders,default_qty=1,step_seconds=60)
        self.assertEqual([(x['timestamp'],x['id'],x['price']) for x in result['fills']], [(60,'ChBrkSE',8.75)])

    def test_invalid_length_and_tick_refused(self):
        for length,tick in ((0,.1),(1001,.1),(5,0)):
            with self.subTest(length=length,tick=tick), self.assertRaises(ValueError):
                channel_breakout_intents([10],[11],[9],tick,length)


if __name__ == '__main__':
    unittest.main()
