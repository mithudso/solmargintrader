import unittest

from research.exit50_backtest import (
    GRID_US,
    fit_family_model,
    replay,
    select_policy,
    sparse_replay,
)


def samples(end_s, changes=()):
    changes = sorted(changes)
    result = []
    price = 100_000_000_000_000
    for stamp in range(GRID_US, end_s * 1_000_000 + 1, GRID_US):
        while changes and changes[0][0] <= stamp:
            _, price = changes.pop(0)
        result.append((stamp, price))
    return result


class ReplayTests(unittest.TestCase):
    def test_latched_early_target_and_delayed_fill_below_target(self):
        entry = 100_000_000_000_000
        path = samples(30, [(1_000_000, entry - 100_000_000_000), (2_000_000, entry)])
        result = replay(0, 20_000_000, path, {}, "target", 10)
        self.assertEqual(result["intent"], "target")
        self.assertEqual(result["target_first_us"], 1_000_000)
        self.assertEqual(result["submit_us"], 15_200_000)
        self.assertEqual(result["exit_us"], 25_200_000)
        self.assertFalse(result["target_filled"])

    def test_liquidation_during_delay_beats_fill(self):
        entry = 100_000_000_000_000
        path = samples(
            30,
            [
                (1_000_000, entry - 100_000_000_000),
                (20_000_000, entry + 98_000_000_000),
            ],
        )
        result = replay(0, 20_000_000, path, {}, "target", 10)
        self.assertEqual(result["status"], "liquidated")
        self.assertTrue(result["delay_liquidation"])

    def test_missing_grid_never_scores(self):
        path = samples(30)
        path.pop(50)
        self.assertEqual(
            replay(0, 20_000_000, path, {}, "fixed", 10)["status"], "unscored"
        )

    def test_sparse_matches_full_path_with_ambiguous_target_and_delay(self):
        entry = 100_000_000_000_000
        full = samples(130, [(1_000_000, entry - 100_000_000_000), (2_000_000, entry)])
        points = [(0, entry)] + full

        def fetch(minute):
            return [
                p
                for p in points
                if minute * 1_000_000 <= p[0] < (minute + 60) * 1_000_000
            ]

        bars = {
            0: [0, 100, 100, 99.9, 100, 0],
            60: [60, 100, 100, 100, 100, 0],
            120: [120, 100, 100, 100, 100, 0],
        }
        sparse = sparse_replay(0, 120_000_000, entry, bars, {}, fetch, "target", 10)
        full_result = replay(0, 120_000_000, full, {}, "target", 10)
        for key in (
            "status",
            "intent",
            "exit_us",
            "payout",
            "target_first_us",
            "target_filled",
        ):
            self.assertEqual(sparse[key], full_result[key])
        self.assertEqual(sparse["intent"], "target")

    def test_sparse_safe_minutes_and_missing_ambiguous_grid(self):
        entry = 100_000_000_000_000
        bars = {
            0: [0, 100, 100, 100, 100, 0],
            60: [60, 100, 100, 100, 100, 0],
            120: [120, 100, 100, 100, 100, 0],
        }
        missing = sparse_replay(
            0, 120_000_000, entry, bars, {}, lambda _: None, "fixed", 10
        )
        self.assertEqual(missing["status"], "unscored")
        self.assertEqual(missing["at_us"], 120_000_000)

    def test_family_fitting_uses_train_only_and_separate_labels(self):
        start = 1791663600
        train_end = 1793163600
        frames = {str(m): {"shape": "range"} for m in (5, 10, 15, 20)}

        def sig(at, family):
            return {
                "eligible": True,
                "family": family,
                "decision_s": at,
                "context": {"frames": frames},
            }

        bars = [[start + 600, 100, 101, 98, 99, 0], [train_end, 100, 102, 99, 101, 0]]
        prepared = {"frames": {"10": (bars, [], [])}}
        events = [
            sig(start + 540, "near_end"),
            sig(start + 600, "confirmed_uu"),
            sig(train_end - 60, "near_end"),
        ]
        near = fit_family_model(prepared, events, "BTC", "near_end")
        confirmed = fit_family_model(prepared, events, "BTC", "confirmed_uu")
        self.assertEqual(near["base_models"]["10"]["n"], 1)
        self.assertEqual(near["base_models"]["10"]["down"], 1)
        self.assertEqual(confirmed["base_models"]["10"]["n"], 1)
        self.assertEqual(near["entry_family"], "near_end")

    def test_future_gap_after_terminal_does_not_invalidate(self):
        entry = 100_000_000_000_000
        path = samples(30, [(1_000_000, entry + 98_000_000_000)])
        full = replay(0, 20_000_000, path, {}, "fixed", 10)
        shortened = replay(0, 20_000_000, path[:5], {}, "fixed", 10)
        self.assertEqual(full, shortened)
        self.assertEqual(full["status"], "liquidated")
        bars = {0: [0, 100, 100.098, 100, 100.098, 0]}
        sparse = sparse_replay(
            0,
            20_000_000,
            entry,
            bars,
            {},
            lambda _: [(0, entry)] + path[:5],
            "fixed",
            10,
        )
        self.assertEqual(sparse["status"], "liquidated")
        self.assertEqual(sparse["exit_us"], 1_000_000)

    def test_selector_uses_validation_and_filters_only_live_policies(self):
        a = {
            "id": "a",
            "family": "confirmed_uu",
            "filter": "shape",
            "exit": "target_momentum",
            "delay_seconds": 10,
            "validation": {"n": 30, "mean_roe": 0.2},
            "test": {"mean_roe": -1},
        }
        b = {
            "id": "b",
            "family": "near_end",
            "filter": "shape_bop",
            "exit": "target_momentum",
            "delay_seconds": 10,
            "validation": {"n": 35, "mean_roe": 0.2},
            "test": {"mean_roe": 1},
        }
        bad = {
            **a,
            "id": "bad",
            "filter": "none",
            "validation": {"n": 100, "mean_roe": 100},
        }
        self.assertEqual(select_policy([a, b, bad])["id"], "b")
        b["test"]["mean_roe"] = -100
        self.assertEqual(select_policy([a, b, bad])["id"], "b")
        self.assertEqual(select_policy([bad])["selection"], "experimental_fallback")

    def test_second_turn_baseline_is_capped_before_a_second_completed_bar(self):
        path = samples(30)
        fixed = replay(0, 20_000_000, path, {}, "fixed", 10)
        second = replay(0, 20_000_000, path, {}, "second_turn", 10)
        self.assertEqual(fixed["exit_us"], second["exit_us"])
        self.assertEqual(fixed["payout"], second["payout"])
        self.assertEqual(second["intent"], "cap")

    def test_momentum_trigger_and_cap(self):
        path = samples(30)
        result = replay(
            0,
            20_000_000,
            path,
            {16_000_000: {"momentum_exit": True}},
            "target_momentum",
            10,
        )
        self.assertEqual(result["intent"], "momentum")
        self.assertEqual(result["exit_us"], 26_000_000)
        result = replay(0, 20_000_000, path, {}, "fixed", 10)
        self.assertEqual(result["intent"], "cap")
        self.assertEqual(result["exit_us"], 30_000_000)


if __name__ == "__main__":
    unittest.main()
