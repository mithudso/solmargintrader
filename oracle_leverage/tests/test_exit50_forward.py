"""Prospective paper lifecycle with deterministic public-oracle fixtures."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import mtf_forward as mtf
from oracle_leverage.exit50_forward import Exit50Forward, bar_display, shape_tilts
from oracle_leverage.tests.test_mtf_forward import NOW, bundle


def family_bundle():
    source = bundle()
    return {
        "schema": "exit50-family-model-bundle/v1",
        "models": {
            asset: {
                family: {**copy.deepcopy(model), "entry_family": family}
                for family in ("confirmed_uu", "near_end")
            }
            for asset, model in source["models"].items()
        },
    }


class Public:
    def __init__(self):
        self.calls = []
        self.missing_at = None
        self.source_lag_us = 0
        self.start = None

    def history(self, asset, start, last, *, cancelled):
        self.history_calls = getattr(self, "history_calls", []) + [(asset, start, last)]
        return {
            "rows": [
                [
                    at,
                    100 + (at // 60 % 13) / 100,
                    102,
                    98,
                    100 + (at // 60 % 13) / 100,
                    1,
                ]
                for at in range(start, last + 60, 60)
            ],
            "proof": {"source": "fixture"},
        }

    def path(self, asset, first_at, last_at, *, cancelled):
        first, last = mtf.path_grid(first_at, last_at)
        self.calls.append((first, last))
        assert last - first <= 120_000_000
        if self.start is None:
            self.start = first
        rows = []
        for at in range(first, last + mtf.GRID_US, mtf.GRID_US):
            if at == self.missing_at:
                continue
            price = (
                9_990_000_000
                if self.start + 1_000_000 <= at < self.start + 2_000_000
                else 10_000_000_000
            )
            rows.append(
                {
                    "price_feed_id": mtf.FEEDS[asset],
                    "publish_time": at,
                    "feed_update_timestamp": at - self.source_lag_us,
                    "price": price,
                    "exponent": -8,
                }
            )
        raw = mtf.canonical({"data": rows}).encode()
        return {
            "status": "complete",
            "raw": raw,
            "proof": {
                "first_us": first,
                "last_us": last,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "received_at": last / 1_000_000 + 1,
            },
        }


class Exit50PaperTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = float(NOW)
        self.public = Public()
        self.model_path = Path(self.directory.name) / "model.json"
        self.model_path.write_text(json.dumps(family_bundle()))
        self.worker = Exit50Forward(
            Path(self.directory.name) / "home",
            self.model_path,
            public=self.public,
            clock=lambda: self.now,
        )
        self.patcher = patch(
            "oracle_leverage.exit50_forward.shape_tilts", return_value={}
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.snap = {
            "eligible": True,
            "shape_filter": True,
            "bop_filter": True,
            "context": {"frames": {}},
            "features": {},
            "score": {"score_down": 0.7},
        }

    def commit(self):
        self.assertTrue(
            self.worker.ledger.commit("ZEC", NOW, (NOW * 1_000_000) + 1, self.snap)
        )
        return self.worker.ledger.active()[0]

    def test_frozen_profile_binds_source_and_excludes_prior_decision(self):
        import oracle_leverage.exit50_forward as forward

        profile = {
            "schema": "exit50-paper-profile/v1",
            "model_sha256": self.worker.model_sha,
            "policy_sha256": self.worker.policy_sha,
            "core_sha256": self.worker.binding["core_sha256"],
            "observer_sha256": hashlib.sha256(
                Path(forward.__file__).read_bytes()
            ).hexdigest(),
            "not_before_s": NOW + 1,
        }
        path = Path(self.directory.name) / "profile.json"
        path.write_text(json.dumps(profile))
        worker = Exit50Forward(
            Path(self.directory.name) / "other",
            self.model_path,
            profile=path,
            public=self.public,
            clock=lambda: self.now,
        )
        worker.rows["ZEC"] = [[NOW - 60, 1, 2, 1, 2, 0]]
        with patch("oracle_leverage.exit50_forward.signal_snapshot") as calculate:
            worker.observe_signal("ZEC", NOW)
        calculate.assert_not_called()
        self.assertEqual(
            worker.binding["profile_sha256"],
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        profile["observer_sha256"] = "wrong"
        path.write_text(json.dumps(profile))
        with self.assertRaisesRegex(ValueError, "invalid_paper_profile"):
            Exit50Forward(
                Path(self.directory.name) / "third", self.model_path, profile=path
            )

    def test_target_latches_until_guard_and_delayed_close(self):
        row = self.commit()
        with patch("oracle_leverage.exit50_forward.minute_features", return_value={}):
            self.worker.advance(row, self.now + 2)
            row = self.worker.ledger.active()[0]
            self.worker.advance(row, self.now + 5)
            row = self.worker.ledger.active()[0]
            state = json.loads(row["state_json"])
            self.assertEqual(row["status"], "close_pending")
            self.assertEqual(state["intent"], "target")
            self.assertEqual(state["submit_us"], state["entry_us"] + 15_000_000)
            self.assertEqual(state["deadline_us"], state["submit_us"] + 10_000_000)
            self.worker.advance(row, self.now + 28)
        self.assertEqual(self.worker.ledger.performance()["settled"], 1)
        with self.worker.ledger.connect() as db:
            row = db.execute("SELECT status,state_json FROM decisions").fetchone()
            self.assertEqual(row["status"], "closed_proxy")
            settled = json.loads(row["state_json"])
            self.assertFalse(settled["target_filled"])
            self.assertGreaterEqual(
                settled["intent_detected_at"] * 1_000_000, settled["intent_event_us"]
            )
            self.assertGreaterEqual(
                settled["exit_detected_at"] * 1_000_000, settled["exit_us"]
            )
            self.assertGreaterEqual(settled["exit_detection_lag_s"], 0)
            self.assertGreater(
                db.execute("SELECT count(*) FROM proof").fetchone()[0], 0
            )

    def test_missing_grid_is_unscored_never_settled(self):
        row = self.commit()
        self.worker.advance(row, NOW + 2)
        row = self.worker.ledger.active()[0]
        state = json.loads(row["state_json"])
        self.public.missing_at = state["last_us"] + mtf.GRID_US
        self.worker.advance(row, NOW + 700)
        self.assertEqual(self.worker.ledger.performance()["unscored"], 1)
        self.assertEqual(self.worker.ledger.performance()["settled"], 0)

    def test_long_backlog_requests_bounded_chunks(self):
        row = self.commit()
        self.worker.advance(row, NOW + 2)
        # Flat price until the cap: do not trigger early target or liquidation.
        self.public.start = -1
        with patch(
            "oracle_leverage.exit50_forward.minute_features",
            return_value={NOW + n: {} for n in range(60, 601, 60)},
        ):
            for _ in range(6):
                active = self.worker.ledger.active()
                if not active:
                    break
                self.worker.advance(active[0], NOW + 620)
        self.assertTrue(
            all(last - first <= 120_000_000 for first, last in self.public.calls)
        )
        self.assertGreater(len(self.public.calls), 1)
        self.assertEqual(self.worker.ledger.performance()["settled"], 1)

    def test_signal_requires_supported_shape_negative_bop_and_fresh_jupiter(self):
        self.worker.rows["ZEC"] = [[NOW - 60, 100, 101, 99, 100, 0]]
        with (
            patch(
                "oracle_leverage.exit50_forward.signal_snapshot", return_value=self.snap
            ),
            patch.object(self.worker, "quote", return_value=None),
        ):
            self.worker.observe_signal("ZEC", NOW + 1)
            self.assertFalse(self.worker.ledger.active())
        self.snap["bop_filter"] = False
        with (
            patch(
                "oracle_leverage.exit50_forward.signal_snapshot", return_value=self.snap
            ),
            patch.object(self.worker, "quote", return_value=10),
        ):
            self.worker.observe_signal("ZEC", NOW + 1)
            self.assertFalse(self.worker.ledger.active())
        self.snap["bop_filter"] = True
        with (
            patch(
                "oracle_leverage.exit50_forward.signal_snapshot", return_value=self.snap
            ),
            patch.object(self.worker, "quote", return_value=10),
        ):
            self.worker.observe_signal("ZEC", NOW + 1)
            self.assertEqual(len(self.worker.ledger.active()), 1)

    def test_bar_rollover_baseline_excludes_forming_bar(self):
        start = NOW - 22 * 600
        rows = [[at, 100, 102, 98, 101, 1] for at in range(start, NOW, 60)]
        before = bar_display(rows[:-1], NOW - 1, 101)
        after = bar_display(rows, NOW + 0.5, 102, opening=102)
        self.assertEqual(after["previous"]["start"], NOW - 600)
        self.assertEqual(after["current"]["start"], NOW)
        self.assertEqual(after["current"]["open"], 102)
        self.assertEqual(after["current"]["close"], 102)
        self.assertEqual(after["current"]["baseline_range"], 4)
        self.assertNotEqual(before["previous"]["start"], after["previous"]["start"])
        # Future/forming OHLC cannot affect the trailing reference.
        future = rows + [[NOW, 100, 10000, 1, 5000, 1]]
        self.assertEqual(
            bar_display(future, NOW + 0.5, 102, opening=102)["current"][
                "baseline_range"
            ],
            4,
        )

    def test_shape_tilt_uses_training_counts_not_shape_name(self):
        self.patcher.stop()
        values = [
            {
                "minutes": 5,
                "shape": "any",
                "n": 40,
                "down": 16,
                "base_up": 0.4,
                "supported": True,
            },
            {
                "minutes": 10,
                "shape": "other",
                "n": 2,
                "down": 1,
                "base_up": 0.4,
                "supported": False,
            },
        ]
        with patch(
            "oracle_leverage.exit50_forward.core_shape_tilts", return_value=values
        ):
            result = shape_tilts({}, {})
        self.assertAlmostEqual(result["5"]["uplift_pp"], 20)
        self.assertNotIn("10", result)

    def test_future_gap_after_terminal_does_not_undo_settlement(self):
        row = self.commit()
        self.public.missing_at = row["committed_us"] + 30_000_000
        self.worker.advance(row, NOW + 2)
        with patch("oracle_leverage.exit50_forward.minute_features", return_value={}):
            for _ in range(20):
                active = self.worker.ledger.active()
                if not active:
                    break
                self.worker.advance(active[0], NOW + 700)
        self.assertEqual(self.worker.ledger.performance()["settled"], 1)
        self.assertEqual(self.worker.ledger.performance()["unscored"], 0)

    def test_real_family_core_causal_context_integration(self):
        from oracle_leverage.exit50 import signal_snapshot

        model = self.worker.bundle["models"]["ZEC"]["confirmed_uu"]
        rows = [[at, 100, 102, 99, 101, 1] for at in range(NOW - 1440 * 60, NOW, 60)]
        snapshot = signal_snapshot(rows, NOW, "confirmed_uu", model)
        self.assertEqual(set(snapshot["context"]["frames"]), {"5", "10", "15", "20"})
        self.assertEqual(snapshot["family"], "confirmed_uu")
        future = rows + [[NOW, 100, 10000, 1, 5000, 1]]
        self.assertEqual(snapshot, signal_snapshot(future, NOW, "confirmed_uu", model))
        self.patcher.stop()
        self.assertIsInstance(shape_tilts(model, snapshot["context"]), dict)

    def test_persistent_bootstrap_prefix_and_restart_indicators_match(self):
        from oracle_leverage.exit50 import minute_features

        self.patcher.stop()
        self.worker.refresh_history("ZEC", NOW + 1)
        first = self.worker.rows["ZEC"][0][0]
        self.assertEqual(len(self.worker.rows["ZEC"]), 1440)
        self.worker.refresh_history("ZEC", NOW + 61)
        self.assertEqual(
            self.public.history_calls[-1][2] - self.public.history_calls[-1][1], 0
        )
        restarted = Exit50Forward(
            self.worker.parent.home,
            self.model_path,
            public=self.public,
            clock=lambda: self.now,
        )
        self.assertEqual(restarted.rows["ZEC"], self.worker.rows["ZEC"])
        restarted.refresh_history("ZEC", NOW + 121)
        self.assertEqual(restarted.rows["ZEC"][0][0], first)
        self.assertEqual(len(restarted.rows["ZEC"]), 1442)
        self.assertEqual(
            minute_features(restarted.rows["ZEC"]),
            minute_features(
                self.public.history("ZEC", first, NOW + 60, cancelled=lambda: False)[
                    "rows"
                ]
            ),
        )
        self.assertEqual(restarted.assets["ZEC"]["indicator_seed_s"], first)

    def test_selected_policies_are_hash_bound_and_per_asset(self):
        selected = {
            "schema": "exit50-selected-policy/v1",
            "model_bundle_sha256": self.worker.model_sha,
            "assets": {
                "BTC": {
                    "id": "btc-v",
                    "family": "near_end",
                    "filter": "shape",
                    "policy": "target_momentum",
                    "delay_seconds": 10,
                    "selection_status": "validation-selected",
                    "validation_n": 30,
                    "validation_mean_roe": 0.01,
                },
                "ZEC": {
                    "id": "zec-fallback",
                    "family": "confirmed_uu",
                    "filter": "shape_bop",
                    "policy": "target_momentum",
                    "delay_seconds": 10,
                    "selection_status": "experimental",
                    "validation_n": None,
                    "validation_mean_roe": None,
                },
            },
        }
        policy_path = Path(self.directory.name) / "selected.json"
        policy_path.write_text(json.dumps(selected))
        worker = Exit50Forward(
            Path(self.directory.name) / "selected-home",
            self.model_path,
            policies=policy_path,
            public=self.public,
            clock=lambda: self.now,
        )
        self.assertEqual(worker.selected["assets"]["BTC"]["family"], "near_end")
        self.assertEqual(worker.selected["assets"]["ZEC"]["filter"], "shape_bop")
        self.assertEqual(
            worker.binding["policy_sha256"],
            hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        )
        selected["assets"]["BTC"]["validation_n"] = 29
        policy_path.write_text(json.dumps(selected))
        with self.assertRaisesRegex(ValueError, "unqualified_selected_policy_BTC"):
            Exit50Forward(
                Path(self.directory.name) / "other-home",
                self.model_path,
                policies=policy_path,
                public=self.public,
                clock=lambda: self.now,
            )

    def test_near_end_selected_shape_policy_enters_without_bop_and_uses_correct_cap(
        self,
    ):
        selected = {
            "schema": "exit50-selected-policy/v1",
            "model_bundle_sha256": self.worker.model_sha,
            "assets": {
                asset: {
                    "id": asset + "-near",
                    "family": "near_end",
                    "filter": "shape",
                    "policy": "target_momentum",
                    "delay_seconds": 10,
                    "selection_status": "validation-selected",
                    "validation_n": 31,
                    "validation_mean_roe": 0.01,
                }
                for asset in ("BTC", "ZEC")
            },
        }
        policy_path = Path(self.directory.name) / "near.json"
        policy_path.write_text(json.dumps(selected))
        worker = Exit50Forward(
            Path(self.directory.name) / "near-home",
            self.model_path,
            policies=policy_path,
            public=self.public,
            clock=lambda: NOW - 40,
        )
        worker.rows["ZEC"] = [[NOW - 120, 100, 101, 99, 100, 0]]
        snap = {**self.snap, "family": "near_end", "bop_filter": False}
        with (
            patch("oracle_leverage.exit50_forward.signal_snapshot", return_value=snap),
            patch.object(worker, "quote", return_value=10),
        ):
            worker.observe_signal("ZEC", NOW - 40)
        row = worker.ledger.active()[0]
        self.assertEqual(row["decision_s"], NOW - 60)
        self.assertEqual(row["cap_us"], (NOW + 600) * 1_000_000)
        self.assertEqual(worker.assets["ZEC"]["selected_policy"]["filter"], "shape")

    def test_late_poll_entry_uses_post_durable_commit_plus_200ms(self):
        self.now = NOW + 10.123
        self.assertTrue(
            self.worker.ledger.commit("ZEC", NOW, int((NOW + 1) * 1_000_000), self.snap)
        )
        row = self.worker.ledger.active()[0]
        self.assertGreaterEqual(
            row["commit_observed_us"], int((NOW + 10.123) * 1_000_000)
        )
        self.assertGreaterEqual(
            row["committed_us"], row["commit_observed_us"] + mtf.GRID_US
        )
        self.worker.advance(row, NOW + 12)
        state = json.loads(self.worker.ledger.active()[0]["state_json"])
        self.assertEqual(state["entry_publish_us"], row["committed_us"])
        self.assertGreater(state["entry_feed_update_us"], row["commit_observed_us"])
        self.assertGreaterEqual(
            state["entry_received_at"] * 1_000_000, state["entry_publish_us"]
        )
        self.assertEqual(
            state["decision_to_entry_us"], state["entry_publish_us"] - NOW * 1_000_000
        )
        self.assertGreater(state["decision_to_entry_us"], 10_000_000)

    def test_restart_after_stale_entry_never_backfills(self):
        row = self.commit()
        restarted = Exit50Forward(
            self.worker.parent.home,
            self.model_path,
            public=self.public,
            clock=lambda: NOW + 20,
        )
        restarted.advance(restarted.ledger.active()[0], NOW + 20)
        self.assertEqual(restarted.ledger.performance()["unscored"], 1)
        self.assertFalse(self.public.calls)
        self.assertGreater(row["commit_observed_us"], 0)

    def test_precommit_feed_update_is_never_used_as_entry(self):
        row = self.commit()
        self.public.source_lag_us = mtf.GRID_US * 2
        self.worker.advance(row, NOW + 2)
        self.assertEqual(self.worker.ledger.performance()["unscored"], 1)
        self.assertEqual(self.worker.ledger.performance()["settled"], 0)

    def test_restart_marks_interrupted_commit_unscored(self):
        with self.worker.ledger.connect() as db:
            db.execute(
                "INSERT INTO decisions(id,asset,decision_s,committed_us,cap_us,status,signal_json) VALUES(?,?,?,?,?,'committing',?)",
                ("ZEC:crash", "ZEC", NOW, 0, (NOW + 600) * 1_000_000, "{}"),
            )
        restarted = Exit50Forward(
            self.worker.parent.home,
            self.model_path,
            public=self.public,
            clock=lambda: NOW + 1,
        )
        restarted.start()
        self.addCleanup(restarted._lock.close)
        self.assertEqual(restarted.ledger.performance()["unscored"], 1)
        self.assertFalse(restarted.ledger.active())
        self.assertFalse(self.public.calls)

    def test_late_signal_commit_is_refused(self):
        self.now = NOW + 31
        self.assertFalse(
            self.worker.ledger.commit("ZEC", NOW, NOW * 1_000_000, self.snap)
        )
        self.assertEqual(self.worker.ledger.performance()["unscored"], 1)
        self.assertFalse(self.worker.ledger.active())

    def test_binding_rejects_changed_model(self):
        other = family_bundle()
        other["models"]["BTC"]["confirmed_uu"]["selected"]["id"] = "different"
        self.model_path.write_text(json.dumps(other))
        with self.assertRaisesRegex(ValueError, "paper_binding_changed"):
            Exit50Forward(
                self.worker.parent.home,
                self.model_path,
                public=self.public,
                clock=lambda: self.now,
            )


if __name__ == "__main__":
    unittest.main()
