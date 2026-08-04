"""Tests for the self-explaining sweep output.

`interpret()` turns four numbers into the reading a person should take from them.
Its most important job is catching the two dangerous misreadings:

  * a high positive-count with a high PBO ("lots of strategies work!")
  * a LOW PBO with a low positive-count ("great, rank generalises!")

The second is the subtle one, so it gets the most coverage here.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.cpcv_sweep import (  # noqa: E402
    LOW_POSITIVE_SHARE,
    PBO_INFORMATIVE,
    PBO_NOISE,
    interpret,
)


def joined(*args) -> str:
    """All annotation lines as one lowercase string, for substring assertions."""
    return " ".join(interpret(*args)).lower()


class TestAntiInformative(unittest.TestCase):
    """PBO above the noise line must be called out as worse than random."""

    def test_flags_above_noise_line(self) -> None:
        """The medium-pairs case from the real sweep."""
        text = joined(123, 140, 83, 0.857)
        self.assertIn("anti-informative", text)
        self.assertIn("worse than picking at random", text)

    def test_flags_the_overfit_signature(self) -> None:
        """Many positives plus failed rank is named explicitly."""
        text = joined(123, 140, 83, 0.857)
        self.assertIn("overfit signature", text)
        self.assertIn("67%", text)

    def test_no_overfit_note_when_few_positives(self) -> None:
        """High PBO with few positives is bad, but not the overfit signature."""
        text = joined(100, 100, 5, 0.80)
        self.assertIn("anti-informative", text)
        self.assertNotIn("overfit signature", text)


class TestLowPboTrap(unittest.TestCase):
    """The dangerous case: low PBO is only good news if things are positive."""

    def test_flags_trap_on_real_short_triples_case(self) -> None:
        """PBO 0.086 with 6/61 positive is a trap, not a win."""
        text = joined(61, 70, 6, 0.086)
        self.assertIn("trap", text)
        self.assertIn("generalises reliably as a loser", text)

    def test_low_pbo_with_many_positives_is_not_a_trap(self) -> None:
        """Low PBO plus a healthy positive share is genuinely encouraging."""
        text = joined(60, 60, 40, 0.10)
        self.assertNotIn("trap", text)
        self.assertIn("carries some signal", text)

    def test_low_pbo_good_case_still_demands_verification(self) -> None:
        """Even the good case must not read as a green light."""
        text = joined(60, 60, 40, 0.10)
        self.assertIn("parameter-perturbation", text)

    def test_trap_boundary_is_the_named_threshold(self) -> None:
        """Just under LOW_POSITIVE_SHARE traps; just over does not."""
        n = 100
        just_under = int(n * LOW_POSITIVE_SHARE) - 1
        just_over = int(n * LOW_POSITIVE_SHARE) + 1
        self.assertIn("trap", joined(n, n, just_under, 0.10))
        self.assertNotIn("trap", joined(n, n, just_over, 0.10))


class TestNearNoise(unittest.TestCase):
    """Between the informative and noise lines, say so plainly."""

    def test_flags_near_noise(self) -> None:
        """The short-pairs case: 0.371 is between the two thresholds."""
        text = joined(129, 140, 2, 0.371)
        self.assertIn("close to uninformative", text)

    def test_near_noise_is_not_called_a_trap(self) -> None:
        """0.371 is above PBO_INFORMATIVE, so the trap branch must not fire."""
        self.assertNotIn("trap", joined(129, 140, 2, 0.371))


class TestDroppedAndEdges(unittest.TestCase):
    """Dropped configurations and degenerate inputs."""

    def test_reports_dropped_count_and_that_it_is_not_zero(self) -> None:
        """Dropping must never read as a zero score."""
        text = joined(129, 140, 2, 0.371)
        self.assertIn("11 dropped", text)
        self.assertIn("not counted as zero", text)

    def test_silent_when_nothing_dropped(self) -> None:
        """No dropped line when all configurations evaluated."""
        self.assertNotIn("dropped", joined(70, 70, 10, 0.4))

    def test_zero_evaluable_does_not_divide_by_zero(self) -> None:
        """An all-dropped sweep reports the cause rather than crashing."""
        lines = interpret(0, 70, 0, float("nan"))
        self.assertEqual(len(lines), 1)
        self.assertIn("nothing evaluable", lines[0].lower())

    def test_nan_pbo_is_reported_not_compared(self) -> None:
        """NaN must not silently fall through a numeric branch."""
        text = joined(50, 50, 10, float("nan"))
        self.assertIn("pbo unavailable", text)
        self.assertNotIn("noise line", text)

    def test_thresholds_are_ordered(self) -> None:
        """The named constants must stay in a sane relationship."""
        self.assertLess(PBO_INFORMATIVE, PBO_NOISE)
        self.assertGreater(LOW_POSITIVE_SHARE, 0.0)
        self.assertLess(LOW_POSITIVE_SHARE, 1.0)

    def test_always_returns_at_least_one_line(self) -> None:
        """Every input produces some reading."""
        for ev, tot, pos, pbo in (
            (1, 1, 0, 0.0), (1, 1, 1, 1.0), (10, 20, 5, 0.5),
            (10, 10, 10, float("nan")), (0, 5, 0, 0.3),
        ):
            with self.subTest(pbo=pbo):
                self.assertTrue(interpret(ev, tot, pos, pbo))

    def test_pbo_exactly_at_noise_line_is_not_anti_informative(self) -> None:
        """0.50 is the noise line itself, not above it."""
        self.assertNotIn("anti-informative", joined(50, 50, 25, PBO_NOISE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
