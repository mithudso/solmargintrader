"""Source traces for the simple-mean true-range Volty close strategy."""
import unittest

import numpy as np

from backtester.core.volty import VoltyConfig, stop_levels
from research.pine_bar_emulator import Bar, simulate
from research.tv_volty_close_intents import volty_close_intents


class VoltyCloseTests(unittest.TestCase):
    def test_default_guard_requires_six_closes(self):
        self.assertEqual(volty_close_intents([10]*5,[11]*5,[9]*5),[])
        a=volty_close_intents([10]*6,[11]*6,[9]*6)
        self.assertEqual([(x.id,x.stop,x.qty) for x in a], [('VltClsLE',11.5,None),('VltClsSE',8.5,None)])

    def test_true_range_includes_gap_and_simple_average(self):
        a=volty_close_intents([10,10,15],[11,11,16],[9,9,14],length=2,multiplier=.5)
        self.assertEqual([x.stop for x in a],[17,13])

    def test_missing_guard_is_no_order_not_cancel(self):
        self.assertEqual(volty_close_intents([float('nan'),10,10],[11]*3,[9]*3,2),[])

    def test_stops_fill_after_not_on_signal_bar(self):
        bars=[Bar(0,10,11,9,10),Bar(60,10,11,9,10),Bar(120,10,11,9,10),Bar(180,10,12,9.5,11)]
        groups=[volty_close_intents([b.close for b in bars[:i+1]],[b.high for b in bars[:i+1]],
                                    [b.low for b in bars[:i+1]],2,.5) for i in range(len(bars))]
        result=simulate(bars,groups,default_qty=1,step_seconds=60)
        self.assertEqual([(x['timestamp'],x['id'],x['price']) for x in result['fills']], [(180,'VltClsLE',11)])

    def test_invalid_length_is_refused(self):
        with self.assertRaises(ValueError):volty_close_intents([10],[11],[9],0)

    def test_existing_runner_agrees_on_next_bar_levels(self):
        closes = [10, 11, 9, 12, 11, 13, 12, 14]
        highs = [x + 1 for x in closes]
        lows = [x - 1 for x in closes]
        upper, lower = stop_levels({"close": np.array(closes), "high": np.array(highs),
                                    "low": np.array(lows)}, VoltyConfig())
        for i in range(5, len(closes) - 1):
            intents = volty_close_intents(closes[:i+1], highs[:i+1], lows[:i+1])
            self.assertAlmostEqual(intents[0].stop, upper[i+1])
            self.assertAlmostEqual(intents[1].stop, lower[i+1])


if __name__ == '__main__':
    unittest.main()
