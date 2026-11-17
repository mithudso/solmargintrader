"""Causal and intrabar contracts for the exploratory second-turn study."""

from __future__ import annotations

import math
import unittest

from research.oracle_reversal_inputs import decode_history
from research.reversal_second_turn import (
    aggregate,
    crosses,
    features,
    flags,
    metrics,
    summarize,
)


class SecondTurnTests(unittest.TestCase):
    def test_oracle_zero_volume_is_price_data_and_spot_zero_volume_is_missing_activity(
        self,
    ):
        rows = [[i * 60, 100, 101, 99, 100, 0] for i in range(5)]
        self.assertEqual(len(aggregate(rows, 5, require_volume=False)), 1)
        self.assertEqual(aggregate(rows, 5, require_volume=True), [])
        self.assertEqual(aggregate(rows[:-1], 5, require_volume=False), [])

    def test_history_requires_complete_exact_minutes_but_does_not_assume_volume_semantics(
        self,
    ):
        data = {
            "s": "ok",
            "t": [0, 60],
            "o": [100, 100],
            "h": [101, 101],
            "l": [99, 99],
            "c": [100, 100],
            "v": [0, 2],
        }
        self.assertEqual(len(decode_history(data, 0, 60)), 2)
        with self.assertRaisesRegex(ValueError, "incomplete_or_extra"):
            decode_history(data, 0, 120)

    def test_correct_close_can_still_be_liquidated_and_exact_touch_counts(self):
        short = [0, 100, 100.098, 98, 99, 0]
        long = [0, 100, 102, 99.902, 101, 0]
        self.assertTrue(crosses(short, "DOWN", 9.8))
        self.assertTrue(crosses(long, "UP", 9.8))
        self.assertFalse(crosses(short, "DOWN", 10))
        self.assertFalse(crosses(long, "UP", 10))

    def test_indicators_are_prefix_causal_and_oracle_volume_is_unavailable(self):
        bars = [
            [
                i * 300,
                100 + math.sin(i),
                102 + math.sin(i),
                98 + math.sin(i),
                100 + math.cos(i),
                i + 1,
            ]
            for i in range(80)
        ]
        prefix = features(bars[:60], 5, volume_qualified=False)
        whole = features(bars, 5, volume_qualified=False)
        self.assertEqual(prefix, whole[:60])
        self.assertIsNone(whole[59]["volume_ratio"])
        self.assertIsNotNone(
            features(bars, 5, volume_qualified=True)[59]["volume_ratio"]
        )

    def test_features_restart_at_a_gap(self):
        bars = [[i * 300, 100, 101, 99, 100 + math.sin(i), 10] for i in range(80)]
        bars[60:] = [[r[0] + 300, *r[1:]] for r in bars[60:]]
        self.assertIsNone(features(bars, 5, volume_qualified=True)[60]["rsi"])

    def test_second_turn_rejection_requires_a_completed_shallow_down_bar(self):
        f = {"ema_spread_atr": 1, "lower_wick": 0.5, "volume_ratio": 0.5}
        self.assertTrue(
            flags(f, "trend_up", "second_up", 0.4)["shallow_lower_rejection"]
        )
        self.assertFalse(
            flags(f, "trend_up", "second_up", 0.8)["shallow_lower_rejection"]
        )
        self.assertNotIn("pullback_shallow", flags(f, "trend_up", "first_down", 0))

    def test_joint_success_keeps_correct_liquidations_out_of_the_numerator(self):
        common = {"adverse_bps": 11, "gross_directional_bps": 5}
        events = [
            {
                **common,
                "hit": hit,
                "crossed": {str(b): crossed for b in (5, 7.5, 9.8, 10)},
            }
            for hit, crossed in [(True, True), (True, False), (False, False)]
        ]
        result = metrics(events)
        self.assertEqual(result["hits"], 2)
        self.assertEqual(result["joint"], 1)
        self.assertEqual(result["correct_but_liquidated"], 1)

    def test_selector_never_reranks_using_final_split(self):
        events = []
        for minute, count, wins in [(5, 50, 40), (10, 50, 20)]:
            for split in ("train", "validation", "test"):
                for i in range(count):
                    hit = i < (wins if split != "test" else count - wins)
                    events.append(
                        {
                            "basis": "oracle_signal",
                            "stage": "first_down",
                            "minutes": minute,
                            "split": split,
                            "flags": {"all": True},
                            "hit": hit,
                            "crossed": {str(b): False for b in (5, 7.5, 9.8, 10)},
                            "adverse_bps": 0,
                            "gross_directional_bps": 1,
                        }
                    )
        _, selected = summarize(events)
        self.assertEqual(selected[0]["minutes"], 5)
        for e in events:
            if e["split"] == "test":
                e["hit"] = not e["hit"]
        self.assertEqual(summarize(events)[1][0]["id"], selected[0]["id"])


if __name__ == "__main__":
    unittest.main()
