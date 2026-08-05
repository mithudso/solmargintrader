"""Tests for the block-count geometry sweep.

`geometry.py` answers whether the CPCV leaderboard is a property of the strategies
or of the block count. Two pieces carry the whole conclusion and are covered here:

  * **the comparability intersection.** Larger N means smaller blocks means more
    strategies fail their warm-up. If the ranking were computed over a shrinking
    population, disagreement between geometries would be manufactured out of
    differing membership rather than measured.
  * **the verdict thresholds.** They decide whether a reader is told to trust the
    leaderboard, so an off-by-one on the boundary is a wrong instruction, not a
    cosmetic slip.

`render()` and `evaluate_geometry()` need a full price series and a strategy build and
are **untested** -- being executed by a sweep is not coverage, since nothing asserts
what they produce.

The classes at the end cover the functions whose job is *to fail*. That distinction
earned its place: the pure arithmetic here was well covered while `_check_geometry_pbo`
had no tests, and a missing non-finite guard survived in it for exactly that reason,
two functions away from a comment calling the guard load-bearing.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.geometry import GeometryRun, spearman, tidy_frame, verdict  # noqa: E402
from research.verify_numbers import (  # noqa: E402
    EXPECTED_FIGURES,
    GEOMETRY_TABLE_HEADER,
    _check_geometry_pbo,
    census_failures,
    check_geometry,
    geometry_stats,
    markdown_table_rows,
    verdict_label,
)


class SpearmanTests(unittest.TestCase):
    """The scipy-free rank correlation."""

    def test_identical_orderings_correlate_perfectly(self) -> None:
        a = [0.1, 0.5, -0.2, 0.9]
        self.assertAlmostEqual(spearman(a, a), 1.0, places=12)

    def test_reversed_ordering_is_minus_one(self) -> None:
        a = [0.1, 0.5, -0.2, 0.9]
        self.assertAlmostEqual(spearman(a, [-x for x in a]), -1.0, places=12)

    def test_it_ranks_rather_than_correlating_raw_values(self) -> None:
        """A monotone but wildly non-linear remap must not change the answer.

        This is the whole reason for using Spearman here: block Sharpes are not
        comparable in magnitude across geometries, only in order.
        """
        a = [0.1, 0.2, 0.3, 0.4, 0.5]
        b = [1.0, 100.0, 10_000.0, 1e6, 1e9]
        self.assertAlmostEqual(spearman(a, b), 1.0, places=12)

    def test_ties_are_averaged_not_broken_arbitrarily(self) -> None:
        # pandas' default 'average' method; an arbitrary tie-break would make the
        # result depend on input order, which would be silently unstable.
        self.assertAlmostEqual(spearman([1.0, 1.0, 2.0], [5.0, 5.0, 9.0]), 1.0, places=12)

    def test_too_few_points_is_nan_not_a_confident_number(self) -> None:
        self.assertTrue(np.isnan(spearman([1.0, 2.0], [2.0, 1.0])))


class RankingTests(unittest.TestCase):
    """`GeometryRun.ranking` orders best-first, which every movement figure depends on."""

    def test_best_median_sharpe_comes_first(self) -> None:
        run = GeometryRun(blocks=8, k=2, medians={"a": -0.1, "b": 0.9, "c": 0.3})
        self.assertEqual(run.ranking(["a", "b", "c"]), ["b", "c", "a"])

    def test_ranking_is_restricted_to_the_names_it_is_given(self) -> None:
        """The comparable set is passed in; a run may hold medians for more than that."""
        run = GeometryRun(blocks=8, k=2, medians={"a": 0.1, "b": 0.9, "dropped": 5.0})
        self.assertEqual(run.ranking(["a", "b"]), ["b", "a"])


class VerdictTests(unittest.TestCase):
    """The reading handed to a person, including its boundaries."""

    def test_stable_requires_both_high_correlation_and_a_single_winner(self) -> None:
        self.assertIn("GEOMETRY-STABLE", verdict(0.95, ["one"], np.array([1, 0]), 25))

    def test_high_correlation_with_a_moving_top_spot_is_not_stable(self) -> None:
        """Mean correlation can be high while the #1 still changes.

        That is the case a reader acts on wrongly, so it must not be called stable.
        """
        out = verdict(0.95, ["one", "two"], np.array([1, 0]), 25)
        self.assertIn("MOSTLY STABLE", out)
        self.assertNotIn("GEOMETRY-STABLE", out)

    def test_the_dependent_boundary(self) -> None:
        self.assertIn("MOSTLY STABLE", verdict(0.70, ["a", "b"], np.array([9]), 25))
        self.assertIn("GEOMETRY-DEPENDENT", verdict(0.6999, ["a", "b"], np.array([9]), 25))

    def test_negative_correlation_is_geometry_dependent(self) -> None:
        self.assertIn("GEOMETRY-DEPENDENT", verdict(-0.4, ["a"], np.array([20]), 25))

    def test_nan_is_inconclusive_rather_than_a_verdict(self) -> None:
        # Fewer than three comparable strategies cannot support any claim; saying
        # "stable" there would be the worst possible failure of this script.
        self.assertIn("INCONCLUSIVE", verdict(float("nan"), [], np.array([0]), 2))

    def test_the_supporting_numbers_are_reported_alongside_the_verdict(self) -> None:
        out = verdict(0.566, ["a", "b", "c"], np.array([12, 4, 20]), 25)
        self.assertIn("+0.566", out)
        self.assertIn("12 of 25", out)
        self.assertIn("3 distinct strategies", out)


def frame(by_block: dict[int, dict[str, float]], horizon: str = "t") -> pd.DataFrame:
    """A geometry results frame in the shape geometry.py writes."""
    return pd.DataFrame([
        {"horizon": horizon, "blocks": b, "k": 2, "strategy": s,
         "median_sharpe": m, "frac_positive": 0.5, "trades": 10}
        for b, medians in by_block.items() for s, m in medians.items()
    ])


class GeometryStatsTests(unittest.TestCase):
    """`geometry_stats` recomputes every published finding-1f figure.

    It is the arithmetic behind the numbers in the document, and it is reached only
    through verify_numbers, so nothing else would catch a sign slip or a broken
    comparability rule here.
    """

    def test_a_stable_ordering_scores_perfect_correlation_and_no_movement(self) -> None:
        s = geometry_stats(frame({
            6: {"a": 1.0, "b": 0.5, "c": 0.1},
            8: {"a": 0.9, "b": 0.6, "c": 0.2},
            10: {"a": 0.8, "b": 0.7, "c": 0.3},
        }))
        self.assertEqual(s["n"], 3)
        self.assertAlmostEqual(s["mean_rho"], 1.0, places=12)
        self.assertEqual(s["median_movement"], 0.0)
        self.assertEqual(s["winners"], {"a"})

    def test_a_reversal_scores_minus_one(self) -> None:
        """A sign slip in the descending sort would read this as +1.0."""
        s = geometry_stats(frame({
            6: {"a": 3.0, "b": 2.0, "c": 1.0},
            8: {"a": 1.0, "b": 2.0, "c": 3.0},
        }))
        self.assertAlmostEqual(s["mean_rho"], -1.0, places=12)
        self.assertEqual(int(s["movement"]["a"]), 2)
        self.assertEqual(int(s["movement"]["b"]), 0)
        self.assertEqual(s["winners"], {"a", "c"})

    def test_rank_one_is_the_highest_sharpe_not_the_lowest(self) -> None:
        # The single assumption every movement figure rests on.
        s = geometry_stats(frame({6: {"best": 2.0, "worst": -2.0},
                                  8: {"best": 2.0, "worst": -2.0}}))
        self.assertEqual(s["winners"], {"best"})

    def test_a_strategy_absent_at_any_block_count_is_dropped(self) -> None:
        """Comparability: ranking it anyway invents movement out of absence."""
        s = geometry_stats(frame({
            6: {"a": 3.0, "b": 2.0, "c": 1.0, "partial": 9.0},
            8: {"a": 1.0, "b": 2.0, "c": 3.0},
        }))
        self.assertEqual(s["n"], 3)
        self.assertNotIn("partial", s["median"].index)

    def test_median_and_spread_are_taken_across_block_counts(self) -> None:
        s = geometry_stats(frame({
            6: {"a": 3.0, "b": 2.0, "c": 1.0},
            8: {"a": 1.0, "b": 2.0, "c": 3.0},
        }))
        self.assertAlmostEqual(s["median"]["a"], 2.0, places=12)
        self.assertAlmostEqual(s["spread"]["a"], 2.0, places=12)

    def test_movement_is_split_between_strategies_that_led_and_the_rest(self) -> None:
        # "a" and "b" each top a block; "c" never does.
        s = geometry_stats(frame({
            6: {"a": 1.0, "b": 0.5, "c": 0.1},
            8: {"a": 1.0, "b": 0.5, "c": 0.1},
            10: {"a": 0.1, "b": 1.0, "c": 0.5},
        }))
        self.assertEqual(s["winners"], {"a", "b"})
        self.assertAlmostEqual(s["mean_move_winners"], 1.5, places=12)
        self.assertAlmostEqual(s["mean_move_others"], 1.0, places=12)

    def test_duplicate_cells_are_refused_rather_than_averaged(self) -> None:
        """pivot_table's default aggfunc would silently average them.

        That produces a plausible wrong number, which is worse than an error.
        """
        dup = pd.concat([frame({6: {"a": 1.0, "b": 0.5}, 8: {"a": 1.0, "b": 0.5}}),
                         frame({6: {"a": 9.0}})], ignore_index=True)
        with self.assertRaises(SystemExit):
            geometry_stats(dup)


class TidyFrameTests(unittest.TestCase):
    """The CSV verify_numbers recomputes from."""

    def test_one_row_per_strategy_and_block_count(self) -> None:
        runs = [
            GeometryRun(blocks=6, k=2, medians={"a": 0.5, "b": 0.1},
                        frac_positive={"a": 0.8, "b": 0.4}, trades={"a": 20, "b": 10}),
            GeometryRun(blocks=8, k=2, medians={"a": 0.4, "b": 0.2},
                        frac_positive={"a": 0.7, "b": 0.5}, trades={"a": 22, "b": 11}),
        ]
        out = tidy_frame("long", runs, ["a", "b"])
        self.assertEqual(len(out), 4)
        self.assertEqual(set(out.columns), {
            "horizon", "blocks", "k", "strategy", "median_sharpe",
            "frac_positive", "trades",
        })
        # Round-trips through the stats recomputation the verifier performs.
        self.assertEqual(geometry_stats(out)["n"], 2)

    def test_it_emits_only_the_comparable_names_it_is_given(self) -> None:
        runs = [GeometryRun(blocks=6, k=2, medians={"a": 0.5, "dropped": 9.0},
                            frac_positive={"a": 0.8, "dropped": 1.0},
                            trades={"a": 20, "dropped": 3})]
        self.assertEqual(list(tidy_frame("long", runs, ["a"]).strategy), ["a"])


class MarkdownTableRowsTests(unittest.TestCase):
    """Structural row count: a row that stops matching must show up as a shortfall."""

    TABLE = (
        "prose above\n\n"
        f"{GEOMETRY_TABLE_HEADER} 6-12 | spread | rank movement | top-3 in |\n"
        "|---|---|---|---|---|\n"
        "| `a` | +0.5 | 0.2 | 3 | 1/7 |\n"
        "| `b` | +0.4 | 0.3 | 4 | 2/7 |\n"
        "\nprose below\n"
    )

    def test_it_counts_data_rows_and_skips_the_separator(self) -> None:
        self.assertEqual(markdown_table_rows(self.TABLE, GEOMETRY_TABLE_HEADER), 2)

    def test_it_stops_at_the_end_of_the_table(self) -> None:
        extended = self.TABLE + "| not | part | of | the | table |\n"
        self.assertEqual(markdown_table_rows(extended, GEOMETRY_TABLE_HEADER), 2)

    def test_a_missing_header_is_none_not_zero(self) -> None:
        # None and 0 mean different things: header gone vs table present but empty.
        self.assertIsNone(markdown_table_rows("no table here", GEOMETRY_TABLE_HEADER))


class CensusTests(unittest.TestCase):
    """The floor on how many figures must be recognised.

    Every other check is regex-driven, so a table whose format drifts stops matching
    and the run prints a pass having verified fewer numbers than before. Deleting six
    CPCV rows measurably took the count 923 -> 893 and still exited 0 before this.
    """

    def test_the_expected_count_is_a_pass(self) -> None:
        self.assertEqual(census_failures(dict(EXPECTED_FIGURES)), [])

    def test_a_shortfall_names_how_many_went_unchecked(self) -> None:
        out = census_failures({"RANKED_LISTS.md": EXPECTED_FIGURES["RANKED_LISTS.md"] - 5})
        self.assertEqual(len(out), 1)
        self.assertIn("5 went unchecked", out[0])

    def test_a_surplus_asks_for_the_constant_to_be_raised(self) -> None:
        # Silently accepting more would let the floor rot until it stopped biting.
        n = EXPECTED_FIGURES["STRATEGIES.md"] + 3
        out = census_failures({"STRATEGIES.md": n})
        self.assertEqual(len(out), 1)
        self.assertIn(f"raise EXPECTED_FIGURES to {n}", out[0])

    def test_an_unknown_document_is_not_policed(self) -> None:
        self.assertEqual(census_failures({"SOMETHING_ELSE.md": 4}), [])


class VerdictLabelTests(unittest.TestCase):
    """The reader-facing word, re-derived so it can disagree with the table."""

    def test_it_matches_the_thresholds_in_geometry(self) -> None:
        # Kept deliberately in step with research.geometry.verdict; if those move,
        # this must fail rather than quietly agree with whatever was printed.
        for rho, winners, want in [
            (0.95, 1, "geometry-stable"),
            (0.95, 2, "mostly stable"),
            (0.70, 3, "mostly stable"),
            (0.6999, 3, "geometry-dependent"),
            (-0.4, 6, "geometry-dependent"),
        ]:
            with self.subTest(rho=rho, winners=winners):
                self.assertEqual(verdict_label(rho, winners), want)

    def test_it_agrees_with_the_real_verdict_function_on_the_published_case(self) -> None:
        out = verdict(0.566, ["a"] * 6, np.array([12]), 25)
        self.assertIn(verdict_label(0.566, 6).upper(), out)


class PboCheckTests(unittest.TestCase):
    """`_check_geometry_pbo`: the delegate that skipped the non-finite guard."""

    PARA = ("PBO is not geometry-invariant either. At the long horizon it runs "
            "0.800 (6 blocks) to 0.700 (8); at medium, 0.445 (12).\n\ntail\n")

    def setUp(self) -> None:
        self.failures: list[str] = []

    def test_the_real_paragraph_checks_out(self) -> None:
        n = _check_geometry_pbo(self.PARA, self.failures)
        self.assertEqual(n, 3)
        self.assertEqual(self.failures, [])

    def test_a_figure_quoted_under_the_wrong_horizon_is_caught(self) -> None:
        # long@8 and medium@8 are both 0.700 in the real data, so matching on block
        # count alone would pass this.
        para = self.PARA.replace("at medium, 0.445 (12)", "at medium, 0.830 (12)")
        _check_geometry_pbo(para, self.failures)
        self.assertTrue(any("medium 12" in f for f in self.failures), self.failures)

    def test_a_non_finite_sidecar_value_fails_rather_than_passing(self) -> None:
        """`abs(nan - x) > tol` is False, so the naive comparison passed anything."""
        import research.verify_numbers as vn
        real = vn.load_geometry_pbo
        vn.load_geometry_pbo = lambda: {("long", 6): float("nan"), ("long", 8): 0.7,
                                        ("medium", 12): 0.445}
        try:
            n = _check_geometry_pbo(self.PARA, self.failures)
        finally:
            vn.load_geometry_pbo = real
        self.assertEqual(n, 3)
        self.assertTrue(any("not a number" in f for f in self.failures), self.failures)

    def test_a_missing_marker_is_a_failure_not_a_skip(self) -> None:
        n = _check_geometry_pbo("no PBO paragraph here", self.failures)
        self.assertEqual(n, 0)
        self.assertTrue(any("unchecked" in f for f in self.failures))

    def test_a_figure_quoted_before_any_horizon_cannot_be_attributed(self) -> None:
        para = "PBO is not geometry-invariant either: 0.800 (6 blocks).\n\n"
        _check_geometry_pbo(para, self.failures)
        self.assertTrue(any("cannot be attributed" in f for f in self.failures))


class CheckGeometryFailureTests(unittest.TestCase):
    """The guards that make check_geometry trustworthy, exercised as failures."""

    @staticmethod
    def _geometry() -> dict[str, pd.DataFrame]:
        return {"long": frame({6: {"a": 1.0, "b": 0.5, "c": 0.1},
                               8: {"a": 0.9, "b": 0.6, "c": 0.2}}, horizon="long")}

    def test_a_horizon_with_results_but_no_table_row_is_reported(self) -> None:
        _, failures = check_geometry("### 1f.\n\nno tables at all\n", self._geometry())
        self.assertTrue(any("no row for the 'long' horizon" in f for f in failures),
                        failures)

    def test_a_row_that_stops_matching_shows_up_as_a_shortfall(self) -> None:
        section = (
            "### 1f.\n\n"
            f"{GEOMETRY_TABLE_HEADER} 6-12 | spread | rank movement | top-3 in |\n"
            "|---|---|---|---|---|\n"
            "| `a` | +0.95 | 0.10 | 0 | 2/2 |\n"
            "| b-without-backticks | +0.55 | 0.10 | 0 | 2/2 |\n\n"
        )
        _, failures = check_geometry(section, self._geometry())
        self.assertTrue(any("only 1 matched" in f for f in failures), failures)


if __name__ == "__main__":
    unittest.main()
