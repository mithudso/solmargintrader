"""Source-trace tests for the isolated TradingView Momentum intent adapter."""
import unittest

from research.pine_bar_emulator import Bar, simulate
from research.tv_momentum_intents import momentum_intents


class MomentumIntentTests(unittest.TestCase):
    def test_default_warmup_and_source_order(self):
        actions = momentum_intents(list(range(13)), 13, 11, 0.1)
        self.assertEqual([(a.id, a.action) for a in actions], [("MomLE", "cancel"), ("MomSE", "cancel")])

    def test_long_and_short_stops_then_opposite_cancel(self):
        long, short = momentum_intents([10, 10, 11, 12], 12.5, 11.5, 0.25, length=2)
        self.assertEqual((long.id, long.action, long.side, long.kind, long.stop, long.qty),
                         ("MomLE", "entry", 1, "stop", 12.75, None))
        self.assertEqual((short.id, short.action), ("MomSE", "cancel"))
        long, short = momentum_intents([12, 12, 11, 10], 10.5, 9.5, 0.25, length=2)
        self.assertEqual((long.id, long.action), ("MomLE", "cancel"))
        self.assertEqual((short.id, short.action, short.side, short.kind, short.stop, short.qty),
                         ("MomSE", "entry", -1, "stop", 9.25, None))

    def test_zero_change_or_zero_momentum_cancels_both(self):
        for closes in ([10, 11, 12, 13], [10, 9, 10, 9]):
            self.assertEqual([x.action for x in momentum_intents(closes, 13, 9, 0.1, 2)],
                             ["cancel", "cancel"])

    def test_nan_history_does_not_emit_entry(self):
        self.assertEqual([x.action for x in momentum_intents([float("nan"), 10, 11, 12], 12, 10, 0.1, 2)],
                         ["cancel", "cancel"])

    def test_prefix_is_unaffected_by_future_bar(self):
        prices = [10, 10, 11, 12, 1]
        before = momentum_intents(prices[:4], 12, 11, 0.1, 2)
        prices[-1] = 1000
        self.assertEqual(before, momentum_intents(prices[:4], 12, 11, 0.1, 2))

    def test_invalid_contract_rejected(self):
        for length, high, low, tick in [(0, 2, 1, .1), (2, 1, 2, .1), (2, 2, 1, 0)]:
            with self.subTest(length=length, high=high, low=low, tick=tick), self.assertRaises(ValueError):
                momentum_intents([1, 2, 3, 4], high, low, tick, length)

    def test_stop_is_eligible_on_following_bar(self):
        bars = [Bar(0, 10, 10, 10, 10), Bar(60, 10, 10, 10, 10),
                Bar(120, 10, 11, 10, 11), Bar(180, 11, 12, 11, 12),
                Bar(240, 12, 13, 12, 13)]
        closes = [bar.close for bar in bars]
        intents = [momentum_intents(closes[:i + 1], bar.high, bar.low, .25, 2)
                   for i, bar in enumerate(bars)]
        result = simulate(bars, intents, default_qty=1, step_seconds=60)
        self.assertEqual([(f["timestamp"], f["price"]) for f in result["fills"]], [(240, 12.25)])


if __name__ == "__main__":
    unittest.main()
