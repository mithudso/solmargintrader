"""The sweep's combination gate, and the measurement it now consults.

No test here loads a price file or runs the engine; the gate is pure set logic
over a CSV, and `OUT_DIR` is redirected into a tempdir wherever a read could
otherwise reach `research/results/` -- which holds published evidence.

What is worth pinning is that the three gates genuinely disagree, and disagree in
BOTH directions. That is the whole reason the choice is a flag rather than a
silent default:

  * `family` drops a same-family pair the measurement says is independent.
  * `measured` drops a cross-family pair the labels call diversifying.

If a refactor ever collapsed the two into one filter, every test below would
still pass except `test_gates_disagree_in_both_directions`, which is therefore
the load-bearing one.

Also pinned: the refusal when a measurement is missing. Falling back to labels
there would reinstate exactly the mislabelling the measurement exists to catch,
and the sweep would print a configuration count that reads as measured.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research import sweep

# Real registry names, so the FAMILY lookups inside the gate are meaningful.
# ma_crossover and macd are both `trend`; rsi is `oscillator-reversion` and
# bb_reversion is `mean-reversion`.
NAMES = ("ma_crossover", "macd", "rsi", "bb_reversion")

CSV = """a,b,family_a,family_b,cross_family,corr,agree_active,agree_all,redundant
rsi,bb_reversion,oscillator-reversion,mean-reversion,True,0.8408,0.7997,0.932,True
ma_crossover,macd,trend,trend,False,0.4100,0.5100,0.610,False
ma_crossover,rsi,trend,oscillator-reversion,True,-0.3050,0.4400,0.520,False
"""


class GateFixture(unittest.TestCase):
    """Redirects OUT_DIR and plants one controlled measurement file."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        (self.out / sweep.redundancy_filename("SOL", "medium")).write_text(CSV)
        patcher = mock.patch.object(sweep, "OUT_DIR", self.out)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)


class TestRedundancyFilename(unittest.TestCase):
    def test_keyed_on_horizon_not_interval(self) -> None:
        """medium and long are the same 1d series with different parameters.

        Keying the filename on the interval would collide two different
        measurements and silently serve whichever ran last.
        """
        self.assertNotEqual(
            sweep.redundancy_filename("SOL", "medium"),
            sweep.redundancy_filename("SOL", "long"),
        )

    def test_asset_is_lowercased(self) -> None:
        self.assertEqual(
            sweep.redundancy_filename("BTC", "medium"),
            "signal_redundancy_btc_medium.csv",
        )


class TestMeasuredRedundantPairs(GateFixture):
    def test_reads_only_the_flagged_rows(self) -> None:
        pairs = sweep.measured_redundant_pairs("medium")
        self.assertEqual(pairs, frozenset({frozenset({"rsi", "bb_reversion"})}))

    def test_pairs_are_unordered(self) -> None:
        """The CSV records one direction; the gate must match either."""
        pairs = sweep.measured_redundant_pairs("medium")
        self.assertIn(frozenset(("bb_reversion", "rsi")), pairs)

    def test_quoted_booleans_do_not_flag_everything(self) -> None:
        """The trap `astype(bool)` would have walked into.

        A `redundant` column that arrives as TEXT makes every non-empty string
        truthy under `astype(bool)` -- including "false" -- so every pair reads
        as redundant and the gate silently drops the whole search. Quoting
        forces pandas to hand back object dtype, which is the shape that used to
        break.
        """
        quoted = CSV.replace(",True\n", ',"false"\n').replace(
            ",False\n", ',"false"\n'
        )
        (self.out / sweep.redundancy_filename("SOL", "long")).write_text(quoted)
        self.assertEqual(sweep.measured_redundant_pairs("long"), frozenset())

    def test_unparseable_flag_column_refuses(self) -> None:
        broken = CSV.replace(",True\n", ",yes-ish\n")
        (self.out / sweep.redundancy_filename("SOL", "long")).write_text(broken)
        with self.assertRaisesRegex(SystemExit, "non-boolean values"):
            sweep.measured_redundant_pairs("long")

    def test_missing_measurement_refuses_and_names_the_command(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            sweep.measured_redundant_pairs("short")
        message = str(caught.exception)
        self.assertIn("signal_redundancy_sol_short.csv", message)
        self.assertIn("--horizon short", message)


class TestIndependentCombos(GateFixture):
    def test_unknown_gate_refuses(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--pair-gate must be one of"):
            sweep.independent_combos(NAMES, 2, "medium", "nonsense")

    def test_family_gate_drops_the_same_family_pair(self) -> None:
        combos = sweep.independent_combos(NAMES, 2, "medium", "family")
        self.assertNotIn(("ma_crossover", "macd"), combos)
        self.assertIn(("rsi", "bb_reversion"), combos)
        self.assertEqual(len(combos), 5)

    def test_measured_gate_drops_the_flagged_pair(self) -> None:
        """6 possible pairs, minus the flagged one, minus its two twins.

        rsi and bb_reversion collapse to one class, so (ma_crossover, rsi) and
        (ma_crossover, bb_reversion) are one experiment, as are the macd pair.
        Three survive.
        """
        combos = sweep.independent_combos(NAMES, 2, "medium", "measured")
        self.assertNotIn(("rsi", "bb_reversion"), combos)
        self.assertIn(("ma_crossover", "macd"), combos)
        self.assertEqual(len(combos), 3)

    def test_gates_disagree_in_both_directions(self) -> None:
        """The load-bearing test: neither gate is a subset of the other.

        `family` admits a measured-redundant pair; `measured` admits a
        same-family pair. Collapsing them into one filter would lose one of the
        two, which is why the choice is exposed as a flag.
        """
        family = set(sweep.independent_combos(NAMES, 2, "medium", "family"))
        measured = set(sweep.independent_combos(NAMES, 2, "medium", "measured"))
        self.assertTrue(family - measured, "family admits nothing measured drops")
        self.assertTrue(measured - family, "measured admits nothing family drops")

    def test_both_gate_is_at_most_the_intersection(self) -> None:
        """`both` cannot admit anything either single gate rejects.

        It is no longer exactly the intersection: canonicalisation picks ONE
        representative combination per class, and which twin survives depends on
        what the family gate already removed, so `both` can keep a different twin
        than `measured` did.
        """
        family = set(sweep.independent_combos(NAMES, 2, "medium", "family"))
        measured = set(sweep.independent_combos(NAMES, 2, "medium", "measured"))
        both = set(sweep.independent_combos(NAMES, 2, "medium", "both"))
        self.assertLessEqual(len(both), min(len(family), len(measured)))
        self.assertTrue(both <= family)

    def test_a_triple_is_dropped_for_one_bad_inner_pair(self) -> None:
        """A triple is only as independent as its worst pair."""
        combos = sweep.independent_combos(NAMES, 3, "medium", "measured")
        self.assertNotIn(("ma_crossover", "rsi", "bb_reversion"), combos)
        self.assertNotIn(("macd", "rsi", "bb_reversion"), combos)

    def test_family_gate_needs_no_measurement_file(self) -> None:
        """`family` must not require the CSV, or an unmeasured horizon cannot
        reproduce a published table."""
        combos = sweep.independent_combos(NAMES, 2, "short", "family")
        self.assertEqual(len(combos), 5)


class TestRedundancyClasses(GateFixture):
    def test_groups_flagged_members_and_picks_first_alphabetically(self) -> None:
        canonical, classes = sweep.redundancy_classes("medium")
        self.assertEqual(canonical["rsi"], "bb_reversion")
        self.assertEqual(canonical["bb_reversion"], "bb_reversion")
        self.assertNotIn("ma_crossover", canonical)  # its pair was not flagged
        self.assertEqual(len(classes), 1)
        members, min_corr = classes[0]
        self.assertEqual(members, ["bb_reversion", "rsi"])
        self.assertAlmostEqual(min_corr, 0.8408)

    def test_transitive_members_join_one_class(self) -> None:
        """a~b and b~c put a, b and c in one group even without an a~c row."""
        chained = (
            "a,b,family_a,family_b,cross_family,corr,agree_active,agree_all,redundant\n"
            "rsi,bb_reversion,oscillator-reversion,mean-reversion,True,0.85,0.8,0.9,True\n"
            "bb_reversion,zscore,mean-reversion,mean-reversion,False,0.86,0.8,0.9,True\n"
        )
        (self.out / sweep.redundancy_filename("SOL", "long")).write_text(chained)
        canonical, classes = sweep.redundancy_classes("long")
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0][0], ["bb_reversion", "rsi", "zscore"])
        self.assertEqual(len({canonical[m] for m in ("rsi", "bb_reversion", "zscore")}), 1)

    def test_chained_class_reports_a_minimum_below_threshold(self) -> None:
        """The chaining guard: a~b and b~c flagged, a~c present but WEAK.

        The reported minimum must expose that the component is looser than any
        flagged pair in it, so an over-merged group is visible rather than
        silently trusted.
        """
        chained = (
            "a,b,family_a,family_b,cross_family,corr,agree_active,agree_all,redundant\n"
            "rsi,bb_reversion,oscillator-reversion,mean-reversion,True,0.85,0.8,0.9,True\n"
            "bb_reversion,zscore,mean-reversion,mean-reversion,False,0.86,0.8,0.9,True\n"
            "rsi,zscore,oscillator-reversion,mean-reversion,True,0.10,0.3,0.4,False\n"
        )
        (self.out / sweep.redundancy_filename("SOL", "long")).write_text(chained)
        _, classes = sweep.redundancy_classes("long")
        members, min_corr = classes[0]
        self.assertEqual(members, ["bb_reversion", "rsi", "zscore"])
        self.assertAlmostEqual(min_corr, 0.10)
        self.assertLess(min_corr, sweep.REDUNDANT_CORR)


class TestCanonicalDeduplication(GateFixture):
    def test_twin_combinations_collapse_to_one(self) -> None:
        """The duplicate-result problem, pinned.

        rsi and bb_reversion are interchangeable here, so (ma_crossover, rsi) and
        (ma_crossover, bb_reversion) are the same experiment. The measured gate
        must keep exactly one of them.
        """
        combos = sweep.independent_combos(NAMES, 2, "medium", "measured")
        with_rsi = ("ma_crossover", "rsi") in combos
        with_bb = ("ma_crossover", "bb_reversion") in combos
        self.assertTrue(with_rsi != with_bb, "expected exactly one of the twins")

    def test_family_gate_keeps_both_twins(self) -> None:
        """Without the measurement there is nothing to canonicalise against."""
        combos = sweep.independent_combos(NAMES, 2, "short", "family")
        self.assertIn(("ma_crossover", "rsi"), combos)
        self.assertIn(("ma_crossover", "bb_reversion"), combos)

    def test_the_representative_combination_is_the_one_kept(self) -> None:
        """Which twin survives must be predictable, not an enumeration artifact.

        bb_reversion is the class representative (alphabetically first among the
        candidates), so the pair built from representatives is the one that
        stands. Keeping whichever twin the candidate list happened to mention
        first would silently retire the label a reader was told to look for --
        which is exactly what broke two documented configurations.
        """
        combos = sweep.independent_combos(NAMES, 2, "medium", "measured")
        self.assertIn(("ma_crossover", "bb_reversion"), combos)
        self.assertNotIn(("ma_crossover", "rsi"), combos)

    def test_representative_preference_does_not_change_the_count(self) -> None:
        """It selects a different survivor, never a different number of them."""
        names_reordered = tuple(reversed(NAMES))
        a = sweep.independent_combos(NAMES, 2, "medium", "measured")
        b = sweep.independent_combos(names_reordered, 2, "medium", "measured")
        self.assertEqual(len(a), len(b))

    def test_deduplication_is_order_stable(self) -> None:
        combos_a = sweep.independent_combos(NAMES, 2, "medium", "measured")
        combos_b = sweep.independent_combos(NAMES, 2, "medium", "measured")
        self.assertEqual(combos_a, combos_b)


class TestGateCounts(GateFixture):
    def test_reports_every_gate(self) -> None:
        line = sweep.gate_counts(NAMES, 2, "medium")
        for gate in sweep.PAIR_GATES:
            self.assertIn(f"{gate}=", line)
        self.assertIn("family=5", line)


if __name__ == "__main__":
    unittest.main()
