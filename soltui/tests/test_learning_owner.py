"""Controlled owner gates; fixture clocks never certify production elapsed time."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from botmanager.blind import run_judge
from botmanager.data import load_recording
from botmanager.domain import fingerprint
from botmanager.learning import canonical_scope, comparable_identity
from botmanager.ledger import RuntimeLedger
from botmanager.research import execute
from botmanager.store import ManagerStore

from soltui.experiments import ExperimentStore
from soltui.learning_owner import DAY, LearningOwner, ReadOnlyResearch

from .research_fixtures import grid, recording


class LearningOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "manager"
        self.home.mkdir()
        self.spec = grid("learn")
        ManagerStore(self.home).create_spec(self.spec)
        self.data = load_recording(recording(self.root, 800))
        self.ledger = RuntimeLedger(self.home)
        self.ledger.register(self.spec, self.data)
        self.store = ExperimentStore(self.root / "authority")
        self.registration = {
            "namespace_id": "controlled-fixture",
            "isolation_mode": "registered_clients",
            "coverage": "registered_roots_only",
            "initialization_epoch": 1,
        }
        options = {
            "ranges": {"rungs": [8]},
            "horizon_bars": 1,
            "warmup_bars": 1,
            "blocks": 10,
            "confidence": {
                "method": "block_bootstrap",
                "seed": 0,
                "minimum_blocks": 10,
            },
        }

        def certified_fixture(candidate, snapshot):
            return {
                "metrics": {
                    "net_return": 0.03
                    if candidate.resolved_values["rungs"] == 8
                    else 0.01,
                    "drawdown": 0.01,
                    "turnover": 1.0,
                    "trades": 4,
                    "uncertainty": 0.01,
                },
                "certified": True,
            }

        report = execute(
            self.store,
            self.spec,
            self.data,
            options,
            evaluator=certified_fixture,
            judge=run_judge,
            authority_context={
                **self.registration,
                "roster_revision": fingerprint(self.registration),
            },
        )
        self.run_id = report["run_id"]
        self.owner = LearningOwner(self.store.root, self.registration, self.store)
        self.now = 1800000000
        self.seed_labels()

    def seed_labels(self):
        scope = canonical_scope(self.spec, self.data["identity"])
        run = self.ledger.get(self.spec.bot_id)
        comparable = comparable_identity(run)
        with self.owner.connection(True) as db:
            for i in range(300):
                label = {
                    "id": str(i),
                    "kind": "trade" if i < 30 else "forecast",
                    "resolved": True,
                    "comparable": True,
                    "net_pnl": -1 if i % 2 else 1,
                    "correct": bool(i % 2),
                }
                db.execute(
                    "INSERT INTO learning_labels VALUES (?,?,?,?,?)",
                    (str(i), scope, comparable, json.dumps(label), self.now),
                )

    def propose(self):
        with patch("soltui.learning_owner.time.time", return_value=self.now):
            return self.owner.propose(self.home, self.spec.bot_id, self.run_id)

    def shadow(self, proposal, trades=30):
        proposal = copy.deepcopy(proposal)
        proposal["shadow"] = {"started_at": self.now, "pair_ids": {}, "runs": []}
        with self.owner.connection(True) as db:
            self.owner._save(db, proposal)
        run = self.ledger.get(self.spec.bot_id)

        def state(role):
            row = copy.deepcopy(run)
            row["input"]["prospective"] = {
                "evaluation_ranges": [{"delivery": "prospective_reference"}]
            }
            row["input"]["identity"]["venue_compatibility_verified"] = True
            row["checkpoint"] = {"last_bar_ts": self.now + 7 * DAY}
            return {
                "binding": {"role": role},
                "first_evaluated_at": self.now,
                "first_observed_at": self.now,
                "deliveries": row["input"]["prospective"]["evaluation_ranges"],
                "run": row,
                "trades": trades,
                "health": {"blockers": []},
                "net_pnl": 20 if role == "challenger" else 10,
            }

        return proposal, {
            "complete": True,
            "trades": trades,
            "states": [state("incumbent"), state("challenger")],
        }

    def test_day7_and_trade30_are_both_required(self):
        proposal, progress = self.shadow(self.propose())
        with patch.object(self.owner, "_shadow_progress", return_value=progress):
            with patch(
                "soltui.learning_owner.time.time", return_value=self.now + 7 * DAY - 1
            ):
                self.assertIn(
                    "seven_actual_calendar_days_required",
                    self.owner.inspect(proposal["id"])["gates"],
                )
            with patch(
                "soltui.learning_owner.time.time", return_value=self.now + 7 * DAY
            ):
                self.assertTrue(self.owner.inspect(proposal["id"])["eligible"])
                progress["trades"] = 29
                self.assertIn(
                    "thirty_comparable_shadow_trades_required",
                    self.owner.inspect(proposal["id"])["gates"],
                )

    def test_canonical_daily_quota_and_promotion_cooldown(self):
        proposal, progress = self.shadow(self.propose())
        with (
            patch.object(self.owner, "_shadow_progress", return_value=progress),
            patch("soltui.learning_owner.time.time", return_value=self.now + 7 * DAY),
        ):
            request = str(uuid4())
            receipt = self.owner.authorize(proposal["id"], "promote", request)
            self.assertEqual(
                receipt, self.owner.authorize(proposal["id"], "promote", request)
            )
            with self.assertRaisesRegex(ValueError, "cooldown"):
                self.owner.authorize(proposal["id"], "promote", str(uuid4()))
        # Different opaque proposal identity cannot consume the same scope/day.
        with patch("soltui.learning_owner.time.time", return_value=self.now):
            original = self.owner._evidence(self.run_id)
            changed = copy.deepcopy(original[0])
            changed["request_id"] = str(uuid4())
            with (
                patch.object(
                    self.owner, "_evidence", return_value=(changed, original[1])
                ),
                self.assertRaisesRegex(ValueError, "daily"),
            ):
                self.owner.propose(self.home, self.spec.bot_id, self.run_id)

    def test_uncertified_source_and_history_replay_block(self):
        proposal, progress = self.shadow(self.propose())
        progress["states"][1]["run"]["input"]["identity"][
            "venue_compatibility_verified"
        ] = False
        progress["states"][0]["run"]["input"]["prospective"]["evaluation_ranges"][0][
            "delivery"
        ] = "delayed_replay"
        with (
            patch.object(self.owner, "_shadow_progress", return_value=progress),
            patch("soltui.learning_owner.time.time", return_value=self.now + 7 * DAY),
        ):
            gates = self.owner.inspect(proposal["id"])["gates"]
        self.assertIn("shadow_source_uncertified", gates)
        self.assertIn("historical_or_delayed_shadow_delivery", gates)

    def test_read_only_inspection_does_not_change_canonical_db(self):
        proposal = self.propose()
        before = self.store.path.read_bytes()
        read_only = LearningOwner(
            self.store.root, self.registration, ReadOnlyResearch(self.store.root)
        )
        read_only.inspect(proposal["id"])
        self.assertEqual(before, self.store.path.read_bytes())

    def test_299_labels_or_29_completed_trades_fail(self):
        with self.owner.connection(True) as db:
            db.execute("DELETE FROM learning_labels WHERE id='299'")
        with self.assertRaisesRegex(ValueError, "300"):
            self.propose()

    def test_unknown_receipt_cannot_publish_learned_defaults(self):
        proposal = self.propose()
        with self.assertRaisesRegex(ValueError, "authorization"):
            self.owner.reconcile(
                proposal["id"], str(uuid4()), {"accepted_hash": "forged"}
            )

    def test_owner_manager_publication_and_rollback_preserve_account(self):
        from botmanager.health import HealthStore
        from botmanager.learning import reconcile_transition
        from botmanager.strategies import evaluate

        proposal, progress = self.shadow(self.propose())
        generation = None
        self.ledger.control(self.spec, "start", str(uuid4()))
        generation = self.ledger.claim(self.spec.bot_id, "fixture")
        checkpoint = evaluate(self.spec, self.data, 70, entries_paused=True)
        self.ledger.begin_tick(self.spec.bot_id, generation)
        self.ledger.commit_tick(self.spec.bot_id, generation, 0, checkpoint)
        HealthStore(self.home).pause(
            self.ledger.get(self.spec.bot_id), "pause", str(uuid4())
        )
        self.ledger.control(self.spec, "stop", str(uuid4()))
        self.ledger.stopped(self.spec.bot_id)
        owner = self.owner

        class Client:
            crash = True

            def call(self, operation, params):
                if operation in ("learning-promote", "learning-rollback"):
                    return {
                        "receipt": owner.authorize(
                            params["proposal_id"],
                            operation.removeprefix("learning-"),
                            params["request_id"],
                        )
                    }
                if self.crash:
                    self.crash = False
                    raise OSError("fixture crash after local manager publication")
                return owner.reconcile(
                    params["proposal_id"],
                    params["request_id"],
                    params["manager_receipt"],
                )

        client = Client()
        request = str(uuid4())
        store = ManagerStore(self.home)
        with (
            patch.object(owner, "_shadow_progress", return_value=progress),
            patch("soltui.learning_owner.time.time", return_value=self.now + 7 * DAY),
        ):
            with self.assertRaises(OSError):
                reconcile_transition(store, client, proposal["id"], request_id=request)
            adopted = reconcile_transition(
                store, client, proposal["id"], request_id=request
            )
            self.assertEqual(adopted["accepted_revision"], 2)
            self.assertEqual(
                self.ledger.get(self.spec.bot_id)["checkpoint"]["cash_quote"],
                checkpoint["cash_quote"],
            )
        with (
            patch.object(owner, "_shadow_progress", return_value=progress),
            patch("soltui.learning_owner.time.time", return_value=self.now + 9 * DAY),
        ):
            rolled = reconcile_transition(
                store,
                client,
                proposal["id"],
                operation="rollback",
                request_id=str(uuid4()),
            )
        self.assertEqual(rolled["accepted_revision"], 3)
        self.assertEqual(
            store.get_spec(self.spec.bot_id).resolved_values["rungs"],
            self.spec.resolved_values["rungs"],
        )
        self.assertEqual(
            self.ledger.get(self.spec.bot_id)["checkpoint"]["cash_quote"],
            checkpoint["cash_quote"],
        )
        self.assertEqual(self.ledger.get(self.spec.bot_id)["cursor"], 70)
        with owner.connection() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM learned_defaults").fetchone()[0], 1
            )
            self.assertEqual(
                db.execute(
                    "SELECT count(*) FROM learning_requests WHERE manager_receipt IS NOT NULL"
                ).fetchone()[0],
                2,
            )

    def test_forged_client_clock_rejected_and_absent_schema_read_inert(self):
        import os

        from soltui.research_owner import handle, identity

        # Exact wire shape rejects clocks before attempting any owner mutation.
        request = {
            "version": 2,
            "operation": "learning-inspect",
            "authority": {
                "id": str(uuid4()),
                "root": str(self.store.root),
                "known_clients": [],
                "inventory_complete": True,
            },
            "expected_identity": identity(),
            "params": {"proposal_id": "unused", "now": self.now + 7 * DAY},
        }
        with (
            patch.dict(os.environ, {"SOLTUI_CONFIG_DIR": str(self.root)}),
            self.assertRaises(ValueError),
        ):
            handle(request)
        # A registered owner with no learning schema does not acquire one on read.
        untouched = ExperimentStore(self.root / "untouched-authority")
        learner = LearningOwner(
            untouched.root, self.registration, ReadOnlyResearch(untouched.root)
        )
        before = untouched.path.read_bytes()
        modified = untouched.path.stat().st_mtime_ns
        result = learner.inspect("unused")
        self.assertIsNone(result["proposal"])
        self.assertEqual(before, untouched.path.read_bytes())
        self.assertEqual(modified, untouched.path.stat().st_mtime_ns)

    def test_queued_creation_time_does_not_start_shadow_operation_clock(self):
        proposal, progress = self.shadow(self.propose())
        progress["states"][1]["first_evaluated_at"] = self.now + 7 * DAY - 3600
        progress["states"][1]["first_observed_at"] = self.now + 7 * DAY - 3600
        with (
            patch.object(self.owner, "_shadow_progress", return_value=progress),
            patch("soltui.learning_owner.time.time", return_value=self.now + 7 * DAY),
        ):
            gates = self.owner.inspect(proposal["id"])["gates"]
        self.assertIn("seven_days_since_first_actual_worker_evaluation_required", gates)
        self.assertIn("seven_days_of_prospective_observations_required", gates)

    def test_public_inspect_existing_registered_authority_is_read_only(self):
        import os

        from soltui.research_admission import register_authority
        from soltui.research_owner import handle, identity

        untouched = ExperimentStore(self.root / "inert-canonical")
        config_root = self.root / "inert-config"
        authority = {
            "id": str(uuid4()),
            "root": str(untouched.root),
            "known_clients": [],
            "inventory_complete": True,
        }
        with patch.dict(
            os.environ,
            {
                "SOLTUI_CONFIG_DIR": str(config_root),
                "SOLTUI_RESEARCH_REGISTRY": str(self.root / "inert-registry.json"),
            },
        ):
            register_authority(
                authority, config_root, consent=True, initialize_first=False
            )
            request = {
                "version": 2,
                "operation": "learning-inspect",
                "authority": authority,
                "expected_identity": identity(),
                "params": {"proposal_id": "unused"},
            }
            before = untouched.path.read_bytes()
            modified = untouched.path.stat().st_mtime_ns
            result = handle(request)
        self.assertIsNone(result["proposal"])
        self.assertEqual(before, untouched.path.read_bytes())
        self.assertEqual(modified, untouched.path.stat().st_mtime_ns)
