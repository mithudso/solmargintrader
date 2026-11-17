from __future__ import annotations

import copy
import math
import unittest

from research.reversal_shapes import (
    candles,
    color,
    events,
    metrics,
    rules,
    select,
    shape_labels,
)


def minute_bars(count=4000):
    rows = []
    previous = 100.0
    for i in range(count):
        close = 100 * math.exp(0.012 * math.sin(i / 23) + i / 100000)
        rows.append(
            [
                i * 60,
                previous,
                max(previous, close) + 0.01,
                min(previous, close) - 0.01,
                close,
                1,
            ]
        )
        previous = close
    return rows


class ReversalTests(unittest.TestCase):
    def test_missing_or_zero_volume_minute_is_not_a_complete_bucket(self):
        rows = minute_bars(30)
        self.assertEqual(len(candles(rows, 5)), 6)
        self.assertEqual(len(candles(rows[:7] + rows[8:], 5)), 5)
        rows[7][5] = 0
        self.assertEqual(len(candles(rows, 5)), 5)

    def test_causal_shape_prefix_and_gap_warmup(self):
        full = candles(minute_bars(), 5)
        labels = shape_labels(full, 5)
        self.assertEqual(shape_labels(full[:99], 5), labels[:99])
        after = shape_labels(full[:100] + full[101:], 5)
        self.assertTrue(all(x == "unknown" for x in after[100:147]))

    def test_color_uses_own_open_not_previous_close(self):
        self.assertEqual(color([0, 200, 210, 190, 195, 1]), "DOWN")
        self.assertEqual(color([0, 200, 210, 190, 200, 1]), "FLAT")

    def test_signal_precedes_target_and_split_never_crosses(self):
        events_found, _ = events(minute_bars(), 5, 0, 4000 * 60)
        self.assertTrue(events_found)
        for row in events_found:
            self.assertEqual(row["signal_available_at"], row["target_start"])
            self.assertEqual(row["target_end"] - row["target_start"], 300)

    def test_selection_cannot_read_final_test_metrics(self):
        candidates = []
        for i, rule in enumerate(rules()):
            candidates.append(
                {
                    "rule": rule,
                    "train": {"n": 100},
                    "validation": {
                        "n": 30,
                        "wilson95_descriptive": [0.51 + i / 10000, 0.8],
                        "mean_gross_bps": 1,
                    },
                    "test": {"hit_rate": i / 100, "mean_gross_bps": i * 1000},
                }
            )
        before, _ = select(candidates)
        changed = copy.deepcopy(candidates)
        for row in changed:
            row["test"] = {"n": 1000000, "hit_rate": -5000, "mean_gross_bps": -1e20}
        after, _ = select(changed)
        self.assertEqual(before["rule"], after["rule"])
        self.assertEqual(len(candidates), 64)

    def test_cost_units_and_flat_outcomes_are_explicit(self):
        result = metrics([{"target_color": "UP", "up_bps": 35}], "UP")
        self.assertEqual(result["mean_net_bps_by_roundtrip_cost"]["16"], 19)
        self.assertAlmostEqual(result["arithmetic_10x_mean_net_percent"], 1.9)
        flat = metrics([{"target_color": "FLAT", "up_bps": 0}], "UP")
        self.assertEqual((flat["n"], flat["correct"], flat["flat"]), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()
