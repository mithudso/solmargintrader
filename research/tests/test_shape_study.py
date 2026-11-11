"""Known geometry, future poisoning, execution timing and holdout protection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.data import frame_to_arrays
from research.shape_study import (
    Targets,
    complete_resample,
    detect_shapes,
    learn_routes,
    refuse_reserved,
    replay,
)


def bars(prices, seconds=3600):
    p = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": np.arange(len(p)) * seconds + 1_704_067_200,
            "open": p,
            "high": p * 1.001,
            "low": p * 0.999,
            "close": p,
            "volume": np.ones(len(p)),
        }
    )


class ShapeStudyTests(unittest.TestCase):
    def test_known_trend_flat_and_quadratic_turns(self):
        trend = detect_shapes(bars(np.exp(np.linspace(4, 5, 100))))
        self.assertEqual(trend.iloc[-1]["shape"], "trend_up")
        flat = detect_shapes(bars(np.full(100, 100)))
        self.assertEqual(flat.iloc[-1]["shape"], "range")
        x = np.linspace(-1, 1, 48)
        bowl = detect_shapes(bars(100 * np.exp(0.2 * x * x)))
        cap = detect_shapes(bars(100 * np.exp(-0.2 * x * x)))
        self.assertEqual(bowl.iloc[-1]["shape"], "bowl")
        self.assertEqual(cap.iloc[-1]["shape"], "cap")
        self.assertAlmostEqual(bowl.iloc[-1].fitted_turn_bars_ago, 23.5, places=6)

    def test_known_converging_bounds_and_apex(self):
        d = bars(np.full(48, 100))
        d["high"] = 100 * np.exp(np.linspace(0.1, 0.02, 48))
        d["low"] = 100 * np.exp(np.linspace(-0.1, -0.02, 48))
        out = detect_shapes(d).iloc[-1]
        self.assertEqual(out["shape"], "compression")
        self.assertAlmostEqual(out.estimated_apex_bars, 11.75, places=6)
        self.assertAlmostEqual(out.range_position, 0.47502081252, places=6)

    def test_all_tags_are_identical_under_future_poisoning_and_prefix_replay(self):
        rng = np.random.default_rng(572)
        data = bars(100 * np.exp(np.cumsum(rng.normal(0, 0.015, 240))))
        full = detect_shapes(data)
        for end in (60, 100, 171):
            prefix = detect_shapes(data.iloc[:end])
            pd.testing.assert_frame_equal(
                prefix, full.iloc[:end].reset_index(drop=True), atol=1e-8, rtol=1e-8
            )
            poisoned = data.copy()
            poisoned.loc[end:, ["open", "high", "low", "close"]] *= 17
            pd.testing.assert_frame_equal(
                detect_shapes(poisoned).iloc[:end],
                full.iloc[:end],
                atol=1e-8,
                rtol=1e-8,
            )

    def test_resample_requires_all_constituent_bars_and_full_close_time(self):
        data = bars(np.arange(12) + 100, seconds=3600)
        full = complete_resample(data, 3600, "6h")
        self.assertEqual(len(full), 2)
        self.assertEqual(full.iloc[0].open, 100)
        self.assertEqual(full.iloc[0].close, 105)
        missing = complete_resample(data.drop(index=4), 3600, "6h")
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing.iloc[0].timestamp, data.iloc[6].timestamp)

    def test_no_same_bar_fill_and_both_sides_pay_execution_cost(self):
        data = bars([100, 110, 120])
        result = replay(frame_to_arrays(data), [1, 1, 0], "1h", (0, 10))
        expected = 10000 / 1.001 * (120 / 110) * 0.999
        self.assertAlmostEqual(result.equity[-1], expected, places=7)
        self.assertEqual(result.trades[0].bar_index, 1)
        self.assertEqual(result.metrics.total_borrow_fees, 0)

    def test_signal_poisoning_cannot_change_an_earlier_fill(self):
        data = frame_to_arrays(bars([100, 102, 97, 120, 90]))
        first = replay(data, [1, 0, 0, 0, 0], "1h", (0, 2))
        second = replay(data, [1, 1, 1, 1, 1], "1h", (0, 2))
        np.testing.assert_equal(first.equity[:2], second.equity[:2])

    def test_fractional_mixture_retains_cash_and_refuses_margin(self):
        data = frame_to_arrays(bars([100, 100, 110]))
        result = replay(data, [0.5, 0.5, 0.5], "1h", (0, 0))
        self.assertAlmostEqual(result.equity[-1], 10500)
        for bad in ([0, -1], [0, 1.1], [0, np.nan]):
            with self.assertRaises(ValueError):
                Targets(bad)

    def test_routes_cannot_read_future_or_boundary_outcomes_and_sparse_states_fall_back(
        self,
    ):
        logs = np.zeros((2, 100))
        logs[1, 1:48] = 0.01
        keys = np.tile(["range", "bowl"], 50)
        before = learn_routes(logs, keys, ["cash", "edge"], 0, 50, minimum=10)
        logs[:, 49:] = [[100], [-100]]
        self.assertEqual(
            before, learn_routes(logs, keys, ["cash", "edge"], 0, 50, minimum=10)
        )
        self.assertEqual(before[0], "edge")
        self.assertEqual(
            learn_routes(logs, ["rare"] * 100, ["cash", "edge"], 0, 50)[1], {}
        )

    def test_gap_and_protected_holdout_refuse(self):
        data = bars(np.full(100, 100))
        with self.assertRaisesRegex(ValueError, "contiguous"):
            detect_shapes(data.drop(index=60))
        ts = int(data.timestamp.iloc[-1])
        with self.assertRaisesRegex(ValueError, "protected"):
            refuse_reserved(data, "1h", [{"start": ts, "end": ts + 1}])
        refuse_reserved(data, "1h", [{"start": ts + 3600, "end": ts + 7200}])

    def test_small_reproducible_cell_keeps_all_policies_and_three_folds(self):
        from research.shape_study import run_cell

        rng = np.random.default_rng(711)
        data = bars(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 1000))))
        tags = detect_shapes(data)
        candidates = {"cash": np.zeros(1000), "trend": np.ones(1000)}
        with tempfile.TemporaryDirectory() as tmp:
            rows, picks, attribution = run_cell(
                data, tags, "1h", (0, 10), "TEST", "zero_10", Path(tmp), candidates
            )
            self.assertEqual(len(rows), 12)
            self.assertEqual(len(picks), 3)
            self.assertTrue(
                all(p["last_train_outcome"] < p["first_test_open"] for p in picks)
            )
            self.assertEqual({r["test_bars"] for r in rows}, {600})
            self.assertAlmostEqual(
                sum(r["log_return_sum"] for r in attribution if r["policy"] == "cash"),
                0,
            )


if __name__ == "__main__":
    unittest.main()
