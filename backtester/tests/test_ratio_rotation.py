"""Tests for research/ratio_rotation.py.

The module's self-test is the fast gate a human runs; this is the suite CI runs.
They overlap deliberately on the two invariants that matter most -- the one-bar
leak and the cost path -- because CLAUDE.md requires a test that would catch a
leak for anything touching signal generation or fill timing, and a self-test that
someone can forget to run does not satisfy that.

The emphasis here is on properties rather than numbers. A test asserting that the
strategy returns 12.9%/month would encode one panel's history as a requirement and
break on the next data refetch, which is the opposite of useful.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.types import CostConfig  # noqa: E402
from research.ratio_rotation import (  # noqa: E402
    Panel,
    control_weights,
    demo_chain,
    holding_attribution,
    rolling_zscore_of_relative_log_price,
    simulate,
    target_weights,
    turnover_table,
)


def make_panel(T: int = 300, N: int = 4, seed: int = 3) -> Panel:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.02, size=(T, N)), axis=0))
    ts = np.arange(T, dtype=np.int64) * 86400 + 1_600_000_000
    return Panel(tuple(f"A{i}" for i in range(N)), ts, closes, "1d")


class TestNoLookahead(unittest.TestCase):
    """The one-bar leak, tested by perturbation rather than by inspection."""

    def test_weights_are_invariant_to_all_future_data(self):
        panel = make_panel()
        rng = np.random.default_rng(0)
        for cut in (60, 120, 200):
            base = target_weights(panel.closes, window=30, top_k=1)
            future_corrupted = panel.closes.copy()
            tail = future_corrupted[cut + 1 :]
            future_corrupted[cut + 1 :] = tail * rng.uniform(3.0, 9.0, size=tail.shape)
            perturbed = target_weights(future_corrupted, window=30, top_k=1)
            np.testing.assert_array_equal(
                base[: cut + 1],
                perturbed[: cut + 1],
                err_msg=f"weights through bar {cut} moved when only later bars changed",
            )

    def test_a_deliberate_one_bar_leak_is_caught(self):
        """Guard the guard: if the test cannot fail, it is not testing anything.

        Shifts the weight matrix one bar earlier -- the canonical off-by-one that
        lets a strategy act on a bar it has not seen -- and asserts the
        perturbation check rejects it.
        """
        panel = make_panel()
        cut = 120
        leaked = np.roll(target_weights(panel.closes, window=30, top_k=1), -1, axis=0)

        # The perturbation must differ PER ASSET. The signal ranks each asset's
        # log price against the cross-sectional mean, so scaling every asset by
        # one common factor cancels exactly and corrupts nothing -- an inert
        # perturbation would make this guard silently vacuous.
        corrupted = panel.closes.copy()
        rng = np.random.default_rng(11)
        tail = corrupted[cut + 1 :]
        corrupted[cut + 1 :] = tail * rng.uniform(3.0, 9.0, size=tail.shape)
        leaked_perturbed = np.roll(target_weights(corrupted, window=30, top_k=1), -1, axis=0)

        self.assertFalse(
            np.array_equal(leaked[: cut + 1], leaked_perturbed[: cut + 1]),
            "a one-bar-shifted signal was NOT detected; the leak test is inert",
        )

    def test_zscore_row_uses_only_prior_rows(self):
        panel = make_panel()
        z_full = rolling_zscore_of_relative_log_price(panel.closes, 30)
        truncated = panel.closes[:150]
        z_trunc = rolling_zscore_of_relative_log_price(truncated, 30)
        np.testing.assert_allclose(z_full[:150], z_trunc, rtol=1e-12, equal_nan=True)


class TestCosts(unittest.TestCase):
    """Costs stay in the P&L path -- a backtester non-negotiable."""

    def test_costs_cannot_be_skipped(self):
        panel = make_panel()
        w = target_weights(panel.closes, 30, 1)
        priced = simulate(panel, w)
        free = simulate(panel, w, costs=CostConfig(fee_bps=0.0, slippage_bps=0.0))
        self.assertLess(priced.total_return(), free.total_return())

    def test_cost_is_monotonic_in_fee(self):
        panel = make_panel()
        w = target_weights(panel.closes, 30, 1)
        returns = [
            simulate(panel, w, costs=CostConfig(fee_bps=f, slippage_bps=0.0)).total_return()
            for f in (0.0, 5.0, 20.0, 100.0)
        ]
        self.assertEqual(returns, sorted(returns, reverse=True))

    def test_turnover_matches_weight_movement(self):
        panel = make_panel()
        w = target_weights(panel.closes, 30, 1)
        res = simulate(panel, w)
        expected = np.abs(np.diff(w, axis=0, prepend=np.zeros((1, w.shape[1])))).sum(axis=1)
        np.testing.assert_allclose(res.turnover[:-1], expected[:-1], atol=1e-12)

    def test_no_position_means_no_cost(self):
        panel = make_panel()
        flat = np.zeros_like(panel.closes)
        res = simulate(panel, flat)
        self.assertEqual(res.n_rotations, 0)
        self.assertAlmostEqual(float(res.net_returns.sum()), 0.0, places=12)


class TestChainIsNotFree(unittest.TestCase):
    """The module's central claim, as an executable assertion."""

    def test_chained_and_direct_routes_are_grossly_identical(self):
        panel = Panel(
            ("BTC", "ETH", "SOL"),
            np.arange(50, dtype=np.int64) * 86400,
            np.column_stack(
                [
                    np.linspace(60000, 70000, 50),
                    np.linspace(3000, 3600, 50),
                    np.linspace(150, 200, 50),
                ]
            ),
            "1d",
        )
        frame = demo_chain(panel)
        chained = frame[frame["legs"] == 2].iloc[0]
        direct = frame[frame["legs"] == 1].iloc[0]
        self.assertAlmostEqual(chained["sol_gross"], direct["sol_gross"], places=9)
        self.assertLess(chained["sol_net"], direct["sol_net"])
        self.assertAlmostEqual(chained["cost_bps"], 2 * direct["cost_bps"], delta=0.05)


class TestWeights(unittest.TestCase):
    def test_warmup_holds_nothing(self):
        panel = make_panel()
        w = target_weights(panel.closes, window=45, top_k=1)
        self.assertTrue(np.all(w[:45] == 0.0))

    def test_invested_rows_are_a_portfolio(self):
        panel = make_panel()
        for top_k in (1, 2, 3):
            w = target_weights(panel.closes, 30, top_k)
            active = w[np.any(w != 0.0, axis=1)]
            np.testing.assert_allclose(active.sum(axis=1), 1.0, atol=1e-12)
            self.assertTrue(np.all(np.count_nonzero(active, axis=1) == top_k))

    def test_margin_never_increases_turnover(self):
        panel = make_panel()
        counts = [
            simulate(panel, target_weights(panel.closes, 30, 1, "reversion", m)).n_rotations
            for m in (0.0, 0.5, 1.0, 2.0)
        ]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_signal_is_invariant_to_a_common_scale_factor(self):
        """Scaling every asset by the same factor must not change the selection.

        This is what makes the rule *relative* rather than directional: it has an
        opinion about which coin is cheap against the others, and none at all
        about whether the whole board went up. Discovered while writing the leak
        guard, where a common-factor perturbation turned out to corrupt nothing.
        """
        panel = make_panel()
        base = target_weights(panel.closes, 30, 1)
        for factor in (0.1, 3.0, 100.0):
            scaled = target_weights(panel.closes * factor, 30, 1)
            np.testing.assert_array_equal(base, scaled)

    def test_direction_flips_the_selection(self):
        panel = make_panel()
        rev = target_weights(panel.closes, 30, 1, "reversion")
        mom = target_weights(panel.closes, 30, 1, "momentum")
        self.assertFalse(np.array_equal(rev, mom))

    def test_rejects_bad_parameters(self):
        panel = make_panel()
        for kwargs in ({"window": 1}, {"window": 30, "top_k": 0}, {"window": 30, "margin": -1.0}):
            with self.assertRaises(ValueError):
                target_weights(panel.closes, **kwargs)
        with self.assertRaises(ValueError):
            target_weights(panel.closes, 30, 1, "sideways")

    def test_rejects_non_positive_prices(self):
        panel = make_panel()
        bad = panel.closes.copy()
        bad[10, 0] = 0.0
        with self.assertRaises(ValueError):
            target_weights(bad, 30, 1)


class TestControlsAndAttribution(unittest.TestCase):
    def test_single_asset_rotation_degenerates_to_buy_and_hold(self):
        panel = make_panel(N=1)
        rot = simulate(panel, target_weights(panel.closes, 30, 1))
        hold = simulate(panel, control_weights(panel, "hold_A0", window=30))
        np.testing.assert_allclose(rot.equity, hold.equity, rtol=1e-12)

    def test_random_control_frequency_is_matched(self):
        panel = make_panel()
        fast = simulate(panel, control_weights(panel, "random", seed=1, window=0, hold_bars=5))
        slow = simulate(panel, control_weights(panel, "random", seed=1, window=0, hold_bars=50))
        self.assertGreater(fast.n_rotations, slow.n_rotations)

    def test_attribution_shares_sum_to_one(self):
        panel = make_panel()
        frame = holding_attribution(panel, 30, 1, "momentum", 0.0)
        self.assertAlmostEqual(float(frame["share_of_invested_bars"].sum()), 1.0, places=9)


class TestRuin(unittest.TestCase):
    def test_metrics_stop_at_ruin(self):
        panel = make_panel()
        prices = panel.closes.copy()
        prices[80:] *= np.linspace(1.0, 0.005, prices[80:].shape[0])[:, None]
        doomed = Panel(panel.assets, panel.timestamps, prices, "1d")
        res = simulate(doomed, target_weights(prices, 30, 1), leverage=25.0)
        self.assertTrue(res.ruined, "fixture failed to produce ruin")
        self.assertLessEqual(res.live_returns.size, res.ruin_index + 1)
        self.assertTrue(np.all(res.equity[res.ruin_index :] == 0.0))

    def test_equity_never_goes_negative(self):
        panel = make_panel()
        res = simulate(panel, target_weights(panel.closes, 30, 1), leverage=50.0)
        self.assertTrue(np.all(res.equity >= 0.0))


class TestTurnoverArithmetic(unittest.TestCase):
    def test_drag_rises_as_holding_period_shortens(self):
        frame = turnover_table()
        drags = frame.sort_values("avg_hold_bars")["annual_drag_pct"].tolist()
        self.assertEqual(drags, sorted(drags, reverse=True))

    def test_a_rotation_costs_two_one_way_legs(self):
        costs = CostConfig(fee_bps=6.0, slippage_bps=2.0)
        frame = turnover_table(costs)
        self.assertAlmostEqual(float(frame["cost_bps_per_rotation"].iloc[0]), 16.0, places=9)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
