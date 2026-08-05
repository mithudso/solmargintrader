"""The redundancy script's pure parts.

Following `test_cross_asset_cpcv.py`: no test here opens a price file, steps the
engine, or writes anywhere under `research/results/`. `data/` is gitignored, so a
test reading `data/SOL_1d.csv` passes on a development machine and fails in CI
for a reason unrelated to the code; and `research/results/` holds published
evidence, so any test that can reach a write redirects `OUT` into a tempdir
first. `exposure_matrix` is the expensive half and stays integration-only --
running the script is what exercises it.

What is worth pinning here is the arithmetic that decides the verdict, plus the
two places this measurement can silently mislead:

  * **Joint flatness inflating agreement.** These strategies are long-only and
    flat most of the time, so a raw agreement rate mostly measures how often
    both were doing nothing. Two rules that take OPPOSITE positions whenever
    either is active score 0.90 raw and 0.00 active. If those two numbers are
    ever computed the same way, the diagnostic has stopped working.
  * **A constant column is excluded, not independent.** A strategy that never
    trades cannot be standardised (zero variance) and carries no redundancy
    information. Dropping it silently would let "not measurable" read as "not
    redundant", which is the opposite conclusion.

Also pinned: a perfectly anti-correlated pair is ONE bet, not two. Inverting a
signal does not diversify it, and the spectrum has to say so.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from research import signal_redundancy as sr


def frame(**columns: np.ndarray) -> pd.DataFrame:
    """An exposure frame keyed by real registry names, so FAMILY lookups work."""
    return pd.DataFrame(columns)


class TestRedundancy(unittest.TestCase):
    def test_identical_signals_are_one_bet(self) -> None:
        wave = np.tile([1.0, 1.0, 0.0, 0.0], 50)
        result = sr.redundancy(frame(sma_regime=wave, voltarget=wave.copy()))
        self.assertEqual(result["nominal"], 2)
        self.assertEqual(result["effective"], 1)
        self.assertAlmostEqual(result["corr"].loc["sma_regime", "voltarget"], 1.0)

    def test_inverted_signal_is_still_one_bet(self) -> None:
        """Anti-correlation is not diversification -- the spectrum must agree."""
        wave = np.tile([1.0, 1.0, 0.0, 0.0], 50)
        result = sr.redundancy(frame(sma_regime=wave, voltarget=-wave))
        self.assertAlmostEqual(result["corr"].loc["sma_regime", "voltarget"], -1.0)
        self.assertEqual(result["effective"], 1)

    def test_independent_signals_stay_two_bets(self) -> None:
        rng = np.random.default_rng(20260805)
        a = rng.choice([-1.0, 0.0, 1.0], size=600)
        b = rng.choice([-1.0, 0.0, 1.0], size=600)
        result = sr.redundancy(frame(sma_regime=a, voltarget=b))
        self.assertEqual(result["effective"], 2)
        self.assertLess(abs(result["corr"].loc["sma_regime", "voltarget"]), 0.2)

    def test_joint_flatness_inflates_raw_agreement_only(self) -> None:
        """The headline methodological trap, pinned as a number.

        Both rules are flat on 90 of 100 bars and take OPPOSITE positions on the
        other 10. Raw agreement calls that 90% aligned; active agreement calls it
        0%. Active is the one that describes the bet.
        """
        a, b = np.zeros(100), np.zeros(100)
        a[:10], b[:10] = 1.0, -1.0
        result = sr.redundancy(frame(sma_regime=a, voltarget=b))
        self.assertAlmostEqual(result["agree_all"].loc["sma_regime", "voltarget"], 0.90)
        self.assertAlmostEqual(result["agree_active"].loc["sma_regime", "voltarget"], 0.0)

    def test_agreement_ignores_position_size(self) -> None:
        """A fractional sleeve and a full-size one hold the same STATE.

        This is what makes the volatility-targeted strategies comparable with the
        binary ones: sizing differs, the long/flat decision does not.
        """
        state = np.tile([1.0, 0.0], 50)
        result = sr.redundancy(frame(sma_regime=state, voltarget=state * 0.03))
        self.assertAlmostEqual(result["agree_active"].loc["sma_regime", "voltarget"], 1.0)

    def test_constant_column_is_named_not_silently_dropped(self) -> None:
        wave = np.tile([1.0, 0.0], 50)
        result = sr.redundancy(
            frame(sma_regime=wave, voltarget=-wave, buy_and_hold=np.ones(100))
        )
        self.assertEqual(result["constant"], ["buy_and_hold"])
        self.assertEqual(result["nominal"], 2)
        self.assertNotIn("buy_and_hold", result["corr"].columns)

    def test_fewer_than_two_varying_refuses(self) -> None:
        result_args = frame(sma_regime=np.ones(50), voltarget=np.zeros(50))
        with self.assertRaisesRegex(ValueError, "need >=2 varying"):
            sr.redundancy(result_args)

    def test_nan_rows_are_counted_and_attributed(self) -> None:
        """A single NaN drops the row for every column; say which column did it."""
        a = np.tile([1.0, 0.0], 50)
        b = -a.copy()
        b[7] = np.nan
        result = sr.redundancy(frame(sma_regime=a, voltarget=b))
        self.assertEqual(result["dropped_rows"], 1)
        self.assertEqual(result["nan_columns"], ["voltarget"])
        self.assertEqual(result["bars"], 99)

    def test_no_nan_reports_zero_dropped(self) -> None:
        a = np.tile([1.0, 0.0], 50)
        result = sr.redundancy(frame(sma_regime=a, voltarget=-a))
        self.assertEqual(result["dropped_rows"], 0)
        self.assertEqual(result["nan_columns"], [])


class TestPairTable(unittest.TestCase):
    def test_cross_family_redundancy_is_flagged(self) -> None:
        """The finding the script exists to surface.

        `sma_regime` is asserted regime-filter and `voltarget` risk-overlay, so
        FAMILY treats the pair as diversifying. Identical exposures must be
        reported as redundant AND cross-family.
        """
        wave = np.tile([1.0, 1.0, 0.0, 0.0], 50)
        pairs = sr.pair_table(sr.redundancy(frame(sma_regime=wave, voltarget=wave.copy())))
        self.assertEqual(len(pairs), 1)
        row = pairs.iloc[0]
        self.assertTrue(bool(row["redundant"]))
        self.assertTrue(bool(row["cross_family"]))
        self.assertEqual(row["family_a"], "regime-filter")
        self.assertEqual(row["family_b"], "risk-overlay")

    def test_opposed_pair_is_not_redundant(self) -> None:
        a, b = np.zeros(100), np.zeros(100)
        a[:10], b[:10] = 1.0, -1.0
        pairs = sr.pair_table(sr.redundancy(frame(sma_regime=a, voltarget=b)))
        self.assertFalse(bool(pairs.iloc[0]["redundant"]))

    def test_rows_are_ordered_most_redundant_first(self) -> None:
        wave = np.tile([1.0, 1.0, 0.0, 0.0], 50)
        rng = np.random.default_rng(7)
        noise = rng.choice([0.0, 1.0], size=200)
        pairs = sr.pair_table(
            sr.redundancy(
                frame(sma_regime=wave, voltarget=wave.copy(), obv_trend=noise)
            )
        )
        self.assertEqual(len(pairs), 3)
        self.assertTrue(pairs["corr"].is_monotonic_decreasing)


class TestFamilyVerdict(unittest.TestCase):
    def test_single_row_frame_does_not_break(self) -> None:
        """A two-strategy cohort yields one pair -- a shape a row-axis apply
        handles inconsistently across pandas versions, which is why it is not
        used."""
        wave = np.tile([1.0, 0.0], 50)
        pairs = sr.pair_table(sr.redundancy(frame(sma_regime=wave, voltarget=-wave)))
        verdict = sr.family_verdict(pairs)
        self.assertEqual(len(verdict), 1)
        self.assertEqual(verdict.iloc[0]["families"], "regime-filter + risk-overlay")
        self.assertEqual(verdict.iloc[0]["pairs"], 1)

    def test_family_key_is_order_independent(self) -> None:
        """`a + b` and `b + a` must land in the same bucket, or the grouping
        double-counts every pairing."""
        pairs = pd.DataFrame(
            [
                {"family_a": "trend", "family_b": "breakout", "corr": 0.5, "redundant": False},
                {"family_a": "breakout", "family_b": "trend", "corr": 0.7, "redundant": True},
            ]
        )
        verdict = sr.family_verdict(pairs)
        self.assertEqual(len(verdict), 1)
        self.assertEqual(verdict.iloc[0]["pairs"], 2)
        self.assertEqual(verdict.iloc[0]["families"], "breakout + trend")


class TestResolveOutputPath(unittest.TestCase):
    def test_rejects_anything_but_a_bare_filename(self) -> None:
        for bad in ("../escape.csv", "nested/file.csv", "/tmp/abs.csv"):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    sr.resolve_output_path(bad, force=False)

    def test_refuses_to_clobber_existing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "taken.csv").write_text("published,evidence\n")
            with mock.patch.object(sr, "OUT", out):
                with self.assertRaisesRegex(SystemExit, "refusing to overwrite"):
                    sr.resolve_output_path("taken.csv", force=False)
                self.assertEqual(
                    sr.resolve_output_path("taken.csv", force=True), out / "taken.csv"
                )
                self.assertEqual(
                    sr.resolve_output_path("fresh.csv", force=False), out / "fresh.csv"
                )

    def test_the_guard_is_asserted_against_the_real_results_dir(self) -> None:
        """`resolve_output_path` never writes, so this can name the real path."""
        self.assertEqual(sr.OUT.name, "results")
        self.assertEqual(sr.OUT.parent.name, "research")


class TestPerStrategyTable(unittest.TestCase):
    def test_reports_state_changes_and_time_in_market(self) -> None:
        # long for two bars, flat for two, repeated: one state change per switch.
        wave = np.tile([1.0, 1.0, 0.0, 0.0], 25)
        table = sr.per_strategy_table(
            frame(sma_regime=wave), {"sma_regime": 100}, constant=[]
        )
        row = table.iloc[0]
        self.assertAlmostEqual(row["time_in_market"], 0.5)
        self.assertEqual(row["warmup_bars"], 100)
        self.assertFalse(bool(row["constant"]))
        # 25 blocks, entering and leaving each: 49 transitions after the first bar.
        self.assertEqual(row["state_changes"], 49)

    def test_marks_a_constant_strategy(self) -> None:
        table = sr.per_strategy_table(
            frame(buy_and_hold=np.ones(20)), {"buy_and_hold": 0}, constant=["buy_and_hold"]
        )
        self.assertTrue(bool(table.iloc[0]["constant"]))
        self.assertAlmostEqual(table.iloc[0]["time_in_market"], 1.0)


if __name__ == "__main__":
    unittest.main()
