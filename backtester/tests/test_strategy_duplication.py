"""`bb_reversion` and `zscore` are one hypothesis counted twice.

Found by `research/dso_audit.py`'s S4 pass, which flagged them as posting identical
summary scalars on BTC daily, and confirmed by comparing per-bar exposure: on 1,875
BTC daily bars the two strategies took **exactly the same position on every bar**.

The reason is algebra, not coincidence. Writing `mid` for the trailing mean and `sd`
for the trailing standard deviation over the same window:

    bb_reversion enters when   close <  mid - k*sd     exits when  close > mid
    zscore       enters when   (close - mid)/sd <= -k  exits when  (close - mid)/sd >= 0

and `(close - mid)/sd <= -k` is `close <= mid - k*sd`. Same entry, same exit. With
`bb_reversion(num_std=k)` and `zscore(entry_z=-k, exit_z=0)` on one window they are
the same rule, and the cards ship exactly that pairing at every horizon
(`num_std: 2.0` against `entry_z: -2.0`, windows 20/20/60 against 20/20/60).

**One difference survives, and it is a statistical convention rather than a strategy
choice.** `indicators.bollinger` uses the population standard deviation (ddof=0,
Bollinger's own convention and what charting packages draw); `indicators.zscore` uses
the sample standard deviation (ddof=1). At a 20-bar window that makes the z-score's
entry band `sqrt(20/19)` — about 2.6% — wider, so the two disagree only on bars where
the close falls inside that sliver. On real data that was 0 of 1,875 bars for BTC,
30 (1.60%) for SOL and 16 (0.85%) for ETH.

**Why this is worth a test.** Two registry entries computing one rule inflate the
apparent breadth of a search, which inflates the multiple-testing burden while adding
no diversity — and every pair and triple built from both is likewise less independent
than its name suggests. Neither strategy is deleted: a registry that honestly reports
a redundancy is better than one that hides it by removing a row, and removing one
would silently change the denominator of every published PBO.

So these tests pin the relationship. If someone "tidies up" either indicator's ddof,
the pinning test fails and tells them they have just created an *exact* duplicate.

No test here reads `data/` — that directory is a gitignored fetch cache.
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core import indicators as ind
from backtester.core.strategies import build
from backtester.core.types import BarWindow


def exposures(strategy, closes: np.ndarray) -> np.ndarray:
    """Per-bar exposure the strategy would hold over `closes`."""
    c = np.asarray(closes, dtype="float64")
    ts = np.arange(c.size, dtype="int64") * 86_400
    vol = np.full(c.size, 1_000.0)
    out = np.empty(c.size)
    for i in range(c.size):
        out[i] = strategy.on_bar(BarWindow(ts, c, c * 1.01, c * 0.99, c, vol, i))
    return out


def series(seed: int, n: int = 900) -> np.ndarray:
    """A random walk with enough dispersion to trip a 2-sigma band repeatedly."""
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.normal(0, 1.0, n)) + 200.0


class TestTheTwoAreTheSameRule(unittest.TestCase):
    def test_they_agree_on_the_overwhelming_majority_of_bars(self) -> None:
        # The empirical claim, on synthetic data so it needs no fetch cache.
        for seed in (1, 2, 3, 7, 11):
            closes = series(seed)
            a = exposures(build("bb_reversion", window=20, num_std=2.0), closes)
            b = exposures(build("zscore", window=20, entry_z=-2.0, exit_z=0.0), closes)
            agree = float((a == b).mean())
            self.assertGreater(
                agree, 0.95,
                f"seed {seed}: only {agree:.1%} agreement — the two are supposed to be "
                "the same rule up to ddof",
            )

    def test_forcing_a_common_ddof_makes_them_identical(self) -> None:
        # The decisive test. Re-derive bb_reversion's rule using the SAMPLE stdev that
        # zscore uses, and the two become the same sequence exactly — which is what
        # proves the residual disagreement is the ddof convention and nothing else.
        closes = series(5)
        window, k = 20, 2.0

        manual = np.zeros(closes.size)
        holding = False
        for i in range(closes.size):
            w = closes[max(0, i - window + 1) : i + 1]
            if w.size < window:
                continue
            mid = float(np.mean(w))
            sd = float(np.std(w, ddof=1))  # zscore's convention, not bollinger's
            close = float(closes[i])
            if not holding and close <= mid - k * sd:
                holding = True
            elif holding and close >= mid:
                holding = False
            manual[i] = 1.0 if holding else 0.0

        z = exposures(build("zscore", window=window, entry_z=-k, exit_z=0.0), closes)
        np.testing.assert_array_equal(
            manual, z,
            "a Bollinger rule computed with the sample stdev IS the z-score rule",
        )

    def test_the_only_difference_is_the_stdev_convention(self) -> None:
        # Pinning test. If either indicator's ddof is changed to match the other, the
        # two strategies become exact duplicates rather than near ones — which is a
        # registry defect, not a tidy-up. This test is the tripwire for that edit.
        w = np.asarray(series(9)[-20:], dtype="float64")
        pop = float(np.std(w, ddof=0))
        sample = float(np.std(w, ddof=1))
        self.assertLess(pop, sample, "ddof=1 must exceed ddof=0")
        self.assertAlmostEqual(sample / pop, np.sqrt(20 / 19), places=9)

        mid, _, lower, _ = ind.bollinger(w, 20, 2.0)
        self.assertAlmostEqual(lower, mid - 2.0 * pop, places=9,
                               msg="bollinger must keep the population stdev (ddof=0)")
        # zscore's implied band is the wider one.
        implied = mid - 2.0 * sample
        self.assertLess(implied, lower)

    def test_the_relationship_is_documented_in_both_cards(self) -> None:
        # A redundancy nobody wrote down is one the next reader re-discovers by
        # accident, having already counted it as breadth.
        from pathlib import Path

        cards = Path(__file__).resolve().parents[1] / "strategy_cards"
        for a, b in (("bb_reversion", "zscore"), ("zscore", "bb_reversion")):
            text = (cards / f"{a}.md").read_text()
            self.assertIn(
                b, text,
                f"{a}.md must name {b} as its near-duplicate, or the redundancy is "
                "invisible to anyone reading one card",
            )


if __name__ == "__main__":
    unittest.main()
