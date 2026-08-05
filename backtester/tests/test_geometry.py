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

`render()` and `evaluate_geometry()` need a full price series and a strategy build,
so they are exercised by the sweep itself rather than here; these are the pure
parts.
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
    GEOMETRY_TABLE_HEADER,
    geometry_stats,
    markdown_table_rows,
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


if __name__ == "__main__":
    unittest.main()
