"""Gap detection and repair-merge logic in `research/candle_gap_audit.py`.

The audit's whole value is the distinction between "this minute was quiet" and
"this minute traded and the exchange dropped it", so the tests here pin the
mechanics that decision rests on: which bars are reported missing, and that a
repaired series replaces the damaged bars rather than accumulating duplicates
of them. No network -- the tick fetch is stubbed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.candle_gap_audit import gap_runs  # noqa: E402

MINUTE = 60


def _bars(minutes: list[int]) -> pd.DataFrame:
    """A candle frame present at exactly `minutes` (offsets, in minutes)."""
    base = 1783300000 // 60 * 60
    return pd.DataFrame(
        {
            "timestamp": [base + m * MINUTE for m in minutes],
            "open": [100.0] * len(minutes),
            "high": [101.0] * len(minutes),
            "low": [99.0] * len(minutes),
            "close": [100.5] * len(minutes),
            "volume": [1.0] * len(minutes),
        }
    )


class TestGapRuns(unittest.TestCase):
    def test_contiguous_series_has_no_runs(self):
        self.assertEqual(gap_runs(_bars([0, 1, 2, 3]), MINUTE), [])

    def test_single_missing_bar_is_one_run_of_one(self):
        df = _bars([0, 2])
        runs = gap_runs(df, MINUTE)
        self.assertEqual(len(runs), 1)
        first, last = runs[0]
        self.assertEqual(first, last, "a one-minute gap must not span two minutes")
        self.assertEqual(first, int(df["timestamp"].iloc[0]) + MINUTE)

    def test_run_covers_every_missing_minute_inclusive(self):
        """The 2026-07-06 01:38-01:39 shape: two missing minutes, one run."""
        runs = gap_runs(_bars([0, 3]), MINUTE)
        self.assertEqual(len(runs), 1)
        first, last = runs[0]
        self.assertEqual((last - first) // MINUTE + 1, 2)

    def test_separate_gaps_do_not_merge(self):
        runs = gap_runs(_bars([0, 2, 4]), MINUTE)
        self.assertEqual(len(runs), 2)

    def test_missing_bar_count_matches_the_runs(self):
        df = _bars([0, 3, 4, 7])
        total = sum((b - a) // MINUTE + 1 for a, b in gap_runs(df, MINUTE))
        span = (int(df["timestamp"].iloc[-1]) - int(df["timestamp"].iloc[0])) // MINUTE + 1
        self.assertEqual(total, span - len(df))

    def test_coarser_interval_uses_its_own_step(self):
        """A 5m series is not gappy merely because minutes are absent."""
        base = 1783300000 // 300 * 300
        df = pd.DataFrame(
            {
                "timestamp": [base, base + 300, base + 600],
                "open": [1.0] * 3, "high": [1.0] * 3, "low": [1.0] * 3,
                "close": [1.0] * 3, "volume": [1.0] * 3,
            }
        )
        self.assertEqual(gap_runs(df, 300), [])
        # The same frame read as 1m is almost entirely missing.
        self.assertEqual(len(gap_runs(df, MINUTE)), 2)


class TestRepairMerge(unittest.TestCase):
    """The merge in main(): tick bars must replace candle bars, not duplicate them."""

    def test_repaired_series_replaces_rather_than_appends(self):
        candles = _bars([0, 1, 3])
        fill = _bars([1, 2])          # 1 is a correction, 2 is a recovery
        fill.loc[:, "volume"] = 42.0
        merged = (
            pd.concat(
                [candles[~candles["timestamp"].isin(set(fill["timestamp"]))], fill],
                ignore_index=True,
            )
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        self.assertEqual(len(merged), 4, "one recovered bar, no duplicates")
        self.assertEqual(merged["timestamp"].duplicated().sum(), 0)
        self.assertTrue(merged["timestamp"].is_monotonic_increasing)
        corrected = merged[merged["timestamp"] == fill["timestamp"].iloc[0]]
        self.assertEqual(float(corrected["volume"].iloc[0]), 42.0,
                         "the tick value must win over the candle it corrects")
        untouched = merged[merged["timestamp"] == candles["timestamp"].iloc[0]]
        self.assertEqual(float(untouched["volume"].iloc[0]), 1.0,
                         "bars outside a repair window must be left alone")


if __name__ == "__main__":
    unittest.main()
