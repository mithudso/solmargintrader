"""Tests for cointegration and peer-relative-value reversion.

The statistics are checked against series whose answer is known by construction —
white noise is stationary, a random walk is not, a synthetic pair is cointegrated
and two independent walks are not. Getting those four right is what makes the ADF
gate trustworthy, and the gate is the entire value of this mechanism: on real data
it turned a -24.7% out-of-sample loss into no position at all.
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.cointegration import (
    AdfResult,
    adf_pvalue,
    adf_test,
    engle_granger,
)
from backtester.core.pairs import PeerSpreadReversion, align_peer
from backtester.core.types import BarWindow


def bars(closes: np.ndarray, start_ts: int = 1_600_000_000) -> dict[str, np.ndarray]:
    c = np.asarray(closes, dtype="float64")
    n = c.size
    return {
        "ts": np.arange(n, dtype="int64") * 86400 + start_ts,
        "open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
        "volume": np.full(n, 1_000.0),
    }


def window_at(closes: np.ndarray, i: int) -> BarWindow:
    c = np.asarray(closes, dtype="float64")
    ts = np.arange(c.size, dtype="int64") * 86400
    return BarWindow(ts, c, c * 1.01, c * 0.99, c, np.full(c.size, 1_000.0), i)


class TestAdf(unittest.TestCase):
    """Four known answers. If these break, nothing downstream is trustworthy."""

    def test_white_noise_is_stationary(self) -> None:
        rng = np.random.default_rng(7)
        result = adf_test(rng.normal(0, 1, 600))
        self.assertTrue(result.stationary_at_5pct, result)
        self.assertLess(result.statistic, result.critical["5%"])

    def test_a_random_walk_is_not_stationary(self) -> None:
        rng = np.random.default_rng(7)
        result = adf_test(np.cumsum(rng.normal(0, 1, 600)))
        self.assertFalse(result.stationary_at_5pct, result)

    def test_a_short_series_is_refused_rather_than_guessed_at(self) -> None:
        with self.assertRaises(ValueError):
            adf_test(np.arange(10, dtype="float64"))

    def test_critical_values_tighten_with_sample_size(self) -> None:
        # The table is interpolated by nobs; a bigger sample must not be given a
        # laxer threshold than a small one.
        small = adf_test(np.random.default_rng(1).normal(0, 1, 60))
        large = adf_test(np.random.default_rng(1).normal(0, 1, 900))
        self.assertGreater(large.critical["5%"], small.critical["5%"])

    def test_pvalue_is_monotone_and_clamped(self) -> None:
        # More negative statistic => smaller p. And it never leaves [0.01, 0.99].
        ps = [adf_pvalue(s, 500) for s in (-6.0, -3.5, -2.9, -2.5, 0.0, 5.0)]
        for earlier, later in zip(ps, ps[1:]):
            self.assertLessEqual(earlier, later)
        self.assertGreaterEqual(min(ps), 0.01)
        self.assertLessEqual(max(ps), 0.99)


class TestEngleGranger(unittest.TestCase):
    def test_a_constructed_pair_is_detected_with_the_right_beta(self) -> None:
        rng = np.random.default_rng(11)
        y = np.cumsum(rng.normal(0, 1, 600)) + 100.0
        x = 2.5 * y + rng.normal(0, 1, 600)
        result = engle_granger(x, y)
        self.assertAlmostEqual(result.beta, 2.5, places=1)
        self.assertTrue(result.cointegrated_at_5pct, result.adf)

    def test_two_independent_walks_are_not_cointegrated(self) -> None:
        rng = np.random.default_rng(3)
        y = np.cumsum(rng.normal(0, 1, 600)) + 100.0
        x = np.cumsum(rng.normal(0, 1, 600)) + 50.0
        self.assertFalse(engle_granger(x, y).cointegrated_at_5pct)

    def test_mismatched_lengths_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            engle_granger(np.arange(50.0), np.arange(40.0))

    def test_the_spread_is_the_residual_the_beta_implies(self) -> None:
        rng = np.random.default_rng(5)
        y = np.cumsum(rng.normal(0, 1, 300)) + 100.0
        x = 1.7 * y + rng.normal(0, 1, 300)
        r = engle_granger(x, y)
        np.testing.assert_allclose(r.spread, x - r.beta * y - r.intercept, atol=1e-9)


class TestAlignPeer(unittest.TestCase):
    def test_a_gap_is_refused_rather_than_filled(self) -> None:
        # Forward-filling a gap would make the spread look calmer than it was,
        # which flatters every reversion statistic computed from it.
        base = np.array([100, 200, 300], dtype="int64")
        with self.assertRaises(ValueError) as ctx:
            align_peer(base, np.array([100, 300], dtype="int64"), np.array([1.0, 3.0]))
        self.assertIn("missing", str(ctx.exception))

    def test_it_reindexes_onto_the_base_timestamps(self) -> None:
        base = np.array([100, 200], dtype="int64")
        got = align_peer(base, np.array([200, 100, 300], dtype="int64"), np.array([2.0, 1.0, 3.0]))
        np.testing.assert_allclose(got, [1.0, 2.0])


class TestPeerSpreadReversion(unittest.TestCase):
    def test_without_a_peer_it_refuses_to_trade(self) -> None:
        # This is why the class is not in the strategy registry: a registered
        # strategy that silently does nothing is a footgun.
        closes = np.cumsum(np.random.default_rng(2).normal(0, 1, 400)) + 200.0
        strat = PeerSpreadReversion()
        self.assertEqual(strat.on_bar(window_at(closes, 399)), 0.0)

    def test_the_cointegration_gate_blocks_an_unrelated_peer(self) -> None:
        rng = np.random.default_rng(4)
        base = np.cumsum(rng.normal(0, 1, 500)) + 200.0
        peer = np.cumsum(rng.normal(0, 1, 500)) + 80.0  # independent walk
        strat = PeerSpreadReversion(peer_closes=peer, fit_window=250)
        windows = 0
        for i in range(300, 500):
            strat.on_bar(window_at(base, i))
            windows += 1
        # A 5% test has a 5% false-positive rate BY CONSTRUCTION, so "never passes"
        # would be the wrong assertion — an occasional spurious window is the test
        # working as specified. What must hold is that rejection dominates, and the
        # residual rate is a live reminder that scanning many windows for
        # cointegration will find some by chance.
        self.assertGreater(strat.bars_screened_out, 0)
        self.assertLess(
            strat.bars_cointegrated,
            0.10 * windows,
            f"unrelated peer passed {strat.bars_cointegrated}/{windows} windows, "
            "far above a 5% false-positive rate",
        )

    def test_disabling_the_gate_lets_the_same_peer_through(self) -> None:
        # The contrast that shows the gate is what binds, not the z-score.
        rng = np.random.default_rng(4)
        base = np.cumsum(rng.normal(0, 1, 500)) + 200.0
        peer = np.cumsum(rng.normal(0, 1, 500)) + 80.0
        strat = PeerSpreadReversion(
            peer_closes=peer, fit_window=250, require_cointegration=False
        )
        for i in range(300, 500):
            strat.on_bar(window_at(base, i))
        self.assertGreater(strat.bars_cointegrated, 0)
        self.assertEqual(strat.bars_screened_out, 0)

    def test_a_genuine_pair_passes_the_gate_and_can_enter(self) -> None:
        rng = np.random.default_rng(9)
        peer = np.cumsum(rng.normal(0, 1, 600)) + 300.0
        base = 0.4 * peer + rng.normal(0, 2.0, 600) + 20.0
        strat = PeerSpreadReversion(peer_closes=peer, fit_window=250)
        taken = [strat.on_bar(window_at(base, i)) for i in range(300, 600)]
        self.assertGreater(strat.bars_cointegrated, 0, "a constructed pair should pass")
        self.assertGreater(max(taken), 0.0, "and should trade at least once")

    def test_a_short_peer_array_is_refused_loudly(self) -> None:
        base = np.cumsum(np.random.default_rng(1).normal(0, 1, 400)) + 100.0
        strat = PeerSpreadReversion(peer_closes=np.ones(100), fit_window=250)
        with self.assertRaises(ValueError) as ctx:
            strat.on_bar(window_at(base, 399))
        self.assertIn("align_peer", str(ctx.exception))

    def test_degenerate_configs_are_refused(self) -> None:
        for kwargs in (
            {"fit_window": 10},
            {"entry_z": 1.0},
            {"entry_z": -2.0, "stop_z": -1.0},
            {"adf_max_p": 0.0},
        ):
            with self.assertRaises(ValueError):
                PeerSpreadReversion(peer_closes=np.ones(400), **kwargs)

    def test_the_stop_outranks_the_profit_target(self) -> None:
        # A spread that keeps diverging is how this loses badly rather than
        # slightly, so the stop must be checked before the exit.
        rng = np.random.default_rng(13)
        peer = np.cumsum(rng.normal(0, 1, 600)) + 300.0
        base = 0.4 * peer + rng.normal(0, 2.0, 600) + 20.0
        strat = PeerSpreadReversion(peer_closes=peer, fit_window=250, stop_z=-2.5)
        strat._holding = True
        # Drive the spread far below the stop by dropping the traded asset hard.
        crashed = base.copy()
        crashed[-1] = base[-1] * 0.5
        self.assertEqual(strat.on_bar(window_at(crashed, 599)), 0.0)
        self.assertFalse(strat._holding)


if __name__ == "__main__":
    unittest.main()
