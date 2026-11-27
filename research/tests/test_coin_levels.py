from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from research import coin_levels as levels

STEP = 300
START = 1_770_249_600


class CoinLevelsTests(unittest.TestCase):
    def test_wilson_interval_brackets_half_for_even_split(self):
        low, high = levels.wilson(50, 100)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        self.assertAlmostEqual((low + high) / 2, 0.5, places=2)

    def test_holm_adjusts_in_step_down_order(self):
        adjusted = levels.holm([0.01, 0.04, 0.03])
        self.assertEqual(adjusted, [0.03, 0.06, 0.06])

    def test_pivots_mark_strict_local_minima(self):
        values = np.array([3, 2, 1, 2, 3, 4, 3, 2, 1, 0, 1], dtype=float)
        self.assertEqual(levels.pivot_indices(values, 1, "low").tolist(), [2, 9])

    def test_hysteresis_holds_until_leave_signal(self):
        enter = np.array([False, True, False, False, False])
        leave = np.array([False, False, False, True, False])
        self.assertEqual(levels.hysteresis(enter, leave).tolist(), [0, 1, 1, 0, 0])

    def test_net_returns_charge_only_the_entry_fill_and_fill_next_open(self):
        opens = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        pos = np.ones(6, dtype=np.int8)
        net, entries, held = levels.net_returns(pos, opens, cost=0.01)
        expected_first = opens[2] / opens[1] - 1 - 0.01
        self.assertAlmostEqual(net[0], expected_first)
        self.assertTrue(np.allclose(net[1:], opens[3:] / opens[2:-1] - 1))
        self.assertEqual(entries.tolist(), [1.0, 0.0, 0.0, 0.0])
        self.assertTrue(np.all(held == 1))

    def test_summary_reports_return_exits_and_drawdown(self):
        summary = levels.summarize(np.array([0.1, -0.5]), np.array([1.0, 0.0]))
        self.assertAlmostEqual(summary["return"], -0.45)
        self.assertEqual(summary["exits"], 1)
        self.assertAlmostEqual(summary["max_drawdown"], -0.5)

    def test_longest_contiguous_run_is_selected_and_gaps_reported(self):
        stamps = [START + i * STEP for i in (0, 1, 2, 5, 6, 7, 8, 9)]
        frame = pd.DataFrame(
            {
                "unix": stamps,
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1.0,
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp)
            frame.to_csv(history / "TST-USD_5m.csv.gz", index=False, compression="gzip")
            sub, info = levels.load_frame(history, "TST", "5m")
        self.assertEqual(info["contiguous_runs"], 2)
        self.assertEqual(info["longest_run_bars"], 5)
        self.assertEqual(info["missing_slots"], 2)
        self.assertEqual(sub.index[0], START + 5 * STEP)


if __name__ == "__main__":
    unittest.main()
