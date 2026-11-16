import unittest

from oracle_leverage.exit50 import (
    advance_proven,
    graph_snapshot,
    minute_features,
    quote_position,
    shape_tilts,
    signal_snapshot,
    start_position,
    step_position,
)


class ExitEconomicsTests(unittest.TestCase):
    def quote(self, mark, side="LONG", **kwargs):
        return quote_position(
            5_000_000, 5_000_000_000, 100_000_000_000_000, mark, side, **kwargs
        )

    def test_saved_official_examples_and_touch(self):
        entry = 100_000_000_000_000
        delta = 98_000_000_000
        for side, mark in (("LONG", entry - delta), ("SHORT", entry + delta)):
            q = self.quote(mark, side)
            self.assertTrue(q["liquidatable"])
            self.assertEqual(q["loss"], 4_900_000)
            self.assertEqual(q["payout"], 0)
        self.assertFalse(self.quote(entry - delta + 1)["liquidatable"])
        q = self.quote(entry + 100_000_000_000)
        self.assertEqual(q["gross_profit"], 3_448_371)
        self.assertEqual(q["win_fee"], 103_451)
        self.assertEqual(q["win_net"], 3_344_920)
        self.assertTrue(q["target_50"])

    def test_deadzone_and_fee_aware_target(self):
        entry = 100_000_000_000_000
        self.assertEqual(self.quote(entry + 2_000_000_000)["win_net"], 0)
        self.assertFalse(self.quote(entry)["target_50"])
        self.assertEqual(self.quote(entry)["payout"], 4_900_000)
        self.assertEqual(
            self.quote(entry + 100_000_000_000, "LONG")["payout"],
            self.quote(entry - 100_000_000_000, "SHORT")["payout"],
        )

    def test_target_equality_and_profit_cap(self):
        entry = 100_000_000_000_000
        lo, hi = entry, entry * 2
        while lo < hi:
            mid = (lo + hi) // 2
            if self.quote(mid)["target_50"]:
                hi = mid
            else:
                lo = mid + 1
        self.assertTrue(self.quote(lo)["target_50"])
        self.assertFalse(self.quote(lo - 1)["target_50"])
        limited = self.quote(entry * 2, max_win_multiple=0)
        self.assertEqual(limited["win_net"], 0)
        self.assertFalse(limited["target_50"])

    def test_features_and_signal_prefix_causality_with_gap(self):
        rows = [
            [
                i * 60,
                100 + i * 0.01,
                100.02 + i * 0.01,
                99.99 + i * 0.01,
                100.01 + i * 0.01,
                0,
            ]
            for i in range(1200)
        ]
        model = {
            "alpha": 20,
            "min_cell_n": 20,
            "min_components": 2,
            "base_models": {
                "10": {
                    "n": 100,
                    "down": 50,
                    "contexts": {str(m): {} for m in (5, 10, 15, 20)},
                }
            },
        }
        at = 1100 * 60
        self.assertEqual(
            signal_snapshot(rows, at, "confirmed_uu", model),
            signal_snapshot(rows[:1100], at, "confirmed_uu", model),
        )
        features = minute_features(rows[:100] + rows[101:])
        self.assertNotIn(110 * 60, features)
        self.assertIn(181 * 60, features)
        self.assertIn("macd_signal", features[181 * 60])

    def test_proven_interval_matches_constant_ticks(self):
        entry = 100_000_000_000_000
        state = start_position(200_000, entry, 20_000_000, "target", 10)
        tick_state = state
        for stamp in range(200_000, 10_000_001, 200_000):
            tick_state = step_position(tick_state, stamp, entry)
        bounded = advance_proven(state, 10_000_000, entry, entry)
        self.assertEqual(tick_state, bounded)
        with self.assertRaises(ValueError):
            advance_proven(state, 10_000_000, entry - 100_000_000_000, entry)
        with self.assertRaises(ValueError):
            advance_proven(state, 20_000_000, entry, entry)

    def test_graph_and_tilts_are_causal_and_supported(self):
        rows = [[i * 60, 100, 101, 99, 100.5, 0] for i in range(400)]
        at = 399 * 60
        graph = graph_snapshot(rows, at, lookback=3)
        self.assertEqual(graph, graph_snapshot(rows[:399], at, lookback=3))
        self.assertEqual(graph["mean_range"], 2)
        self.assertEqual(graph["developing"][4], 100.5)
        model = {
            "alpha": 20,
            "min_cell_n": 20,
            "min_components": 2,
            "base_models": {
                "10": {
                    "n": 100,
                    "down": 50,
                    "contexts": {
                        str(m): {"range": {"n": 20, "down": 0}} for m in (5, 10, 15, 20)
                    },
                }
            },
        }
        context = {"frames": {str(m): {"shape": "range"} for m in (5, 10, 15, 20)}}
        tilts = shape_tilts(model, context)
        self.assertEqual(len(tilts), 4)
        self.assertTrue(all(x["supported"] and x["up_tilt"] > 0 for x in tilts))

    def test_exact_78_completed_minute_warmup(self):
        rows = [[i * 60, 100, 101, 99, 100.5, 0] for i in range(78)]
        self.assertNotIn(77 * 60, minute_features(rows))
        self.assertIn(78 * 60, minute_features(rows))

    def test_zero_reserve_and_validation(self):
        entry = 100_000_000_000_000
        self.assertFalse(self.quote(entry, close_fee_ppm=1000)["liquidatable"])
        self.assertTrue(self.quote(entry - 1, close_fee_ppm=1000)["liquidatable"])
        with self.assertRaises(ValueError):
            self.quote(entry, side="bad")
        with self.assertRaises(ValueError):
            quote_position(True, 1, 1, 1, "LONG")


if __name__ == "__main__":
    unittest.main()
