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

    def test_daily_job_stages_once_across_restart_and_new_home(self):
        with patch("soltui.learning_owner.time.time", return_value=self.now):
            first = self.owner.daily(self.home)
            self.assertEqual(first["scopes"][0]["state"], "proposal_pending_shadow")
            self.assertFalse(first["new_optimizer"])
            restarted = LearningOwner(self.store.root, self.registration, self.store)
            repeated = restarted.daily(self.home)
            self.assertEqual(
                repeated["scopes"][0]["reason"],
                "canonical_daily_attempt_already_recorded",
            )
            second_home = self.root / "other-manager"
            other_spec = grid("new-uuid-same-scope")
            ManagerStore(second_home).create_spec(other_spec)
            RuntimeLedger(second_home).register(other_spec, self.data)
            other = restarted.daily(second_home)
            self.assertEqual(
                other["scopes"][0]["reason"], "canonical_daily_attempt_already_recorded"
            )
        with self.owner.connection() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM learning_schedule").fetchone()[0], 1
            )
            self.assertEqual(
                db.execute("SELECT count(*) FROM learning_proposals").fetchone()[0], 1
            )
        from botmanager.learning import learning_snapshot

        self.assertEqual(
            learning_snapshot(self.home, self.spec.bot_id)["state"], "pending_shadow"
        )

    def test_daily_job_retains_incumbent_without_accepted_evidence(self):
        before = ManagerStore(self.home).get_spec(self.spec.bot_id)
        with (
            patch("soltui.learning_owner.time.time", return_value=self.now),
            patch.object(
                self.owner, "_evidence", side_effect=ValueError("unavailable")
            ),
        ):
            result = self.owner.daily(self.home)
        self.assertEqual(result["scopes"][0]["state"], "retained_incumbent")
        self.assertEqual(
            result["scopes"][0]["reason"],
            "accepted_compatible_research_proposal_unavailable",
        )
        self.assertEqual(before, ManagerStore(self.home).get_spec(self.spec.bot_id))

    def test_daily_job_minimum_counts_and_next_utc_day(self):
        with self.owner.connection(True) as db:
            db.execute("DELETE FROM learning_labels WHERE id='299'")
        with patch("soltui.learning_owner.time.time", return_value=self.now):
            result = self.owner.daily(self.home)
        self.assertEqual(
            result["scopes"][0]["reason"],
            "minimum_300_labels_and_30_completed_trades_pending",
        )
        with patch("soltui.learning_owner.time.time", return_value=self.now + DAY):
            result = self.owner.daily(self.home)
        with self.owner.connection() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM learning_schedule").fetchone()[0], 2
            )
        self.assertEqual(result["scopes"][0]["state"], "retained_incumbent")

    def test_real_owner_proposal_pointer_roundtrip_has_bounded_counter_schema(self):
        from botmanager.learning import learning_snapshot, record_owner_view

        proposal = self.propose()
        self.assertIsInstance(proposal["counts"]["scope"], str)
        self.assertIsInstance(proposal["counts"]["cohorts"], dict)
        record_owner_view(ManagerStore(self.home), {"proposal": proposal})
        snapshot = learning_snapshot(self.home, self.spec.bot_id)
        self.assertEqual(snapshot["state"], "pending_shadow")
        self.assertEqual(snapshot["local_metadata"]["proposals"]["state"], "available")
        pointer = snapshot["proposals"][0]
        self.assertEqual(pointer["counts"]["resolved_comparable_labels"], 300)
        self.assertEqual(pointer["counts"]["completed_trades"], 30)
        self.assertEqual(pointer["cohorts"], proposal["counts"]["cohorts"])
        self.assertTrue(all(type(value) is int for value in pointer["counts"].values()))
        legacy = dict(pointer, counts=proposal["counts"])
        legacy.pop("cohorts")
        with ManagerStore(self.home)._connection(write=True) as db:
            db.execute(
                "UPDATE learning_links SET body=? WHERE proposal_id=?",
                (json.dumps(legacy), proposal["id"]),
            )
        before = ManagerStore(self.home).path.read_bytes()
        again = learning_snapshot(self.home, self.spec.bot_id)
        self.assertEqual(again["state"], "pending_shadow")
        self.assertEqual(
            again["proposals"][0]["cohorts"], proposal["counts"]["cohorts"]
        )
        self.assertEqual(before, ManagerStore(self.home).path.read_bytes())


class OracleForecastIngestionTests(unittest.TestCase):
    def setUp(self):
        import math

        from botmanager.oracle_data import capture, prepare_descriptor

        from oracle.engine import OracleEngine

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.archive = self.root / "oracle.sqlite3"
        self.engine = OracleEngine(self.archive, instrument="SOL/USD")
        self.start = 1700000040
        for index in range(90):
            self.ingest(index, 100 + 10 * math.sin(index / 3))
        self.home = self.root / "manager"
        self.spec = grid("oracle-exclusion")
        ManagerStore(self.home).create_spec(self.spec)
        now = self.start + 89 * 60 + 1
        descriptor = prepare_descriptor(
            self.archive, capital_quote=1000, strategy_id="grid", now=now
        )
        RuntimeLedger(self.home).register(self.spec, capture(descriptor, now=now))
        store = ExperimentStore(self.root / "authority")
        self.owner = LearningOwner(store.root, {"namespace_id": "fixture"}, store)

    def ingest(self, index, price):
        now = self.start + index * 60
        self.engine.ingest(
            {
                "event_id": "actual-" + str(index),
                "source": "coinbase_recorder",
                "venue": "coinbase_exchange",
                "instrument": "SOL/USD",
                "kind": "stream_snapshot_mid",
                "observed_at": now,
                "received_at": now,
                "price": price,
                "timestamp_semantics": "recorder_quote_clock",
            },
            now=now,
        )

    def test_actual_oracle_correct_wrong_resolutions_retained_ineligible_with_provenance(
        self,
    ):
        import sqlite3
        from contextlib import closing

        result = self.owner.collect(self.home, self.spec.bot_id)
        self.assertTrue(result["counts_complete"])
        self.assertEqual(result["forecast_ingestion"]["state"], "ineligible")
        self.assertGreater(result["cohorts"]["forecast_correct"], 0)
        self.assertGreater(result["cohorts"]["forecast_wrong"], 0)
        self.assertEqual(result["resolved_comparable_labels"], 0)
        with closing(sqlite3.connect(self.archive)) as db:
            expected = db.execute("SELECT count(*) FROM resolutions").fetchone()[0]
        self.assertEqual(result["ineligible_forecasts"], expected)
        with self.owner.connection() as db:
            rows = list(db.execute("SELECT comparable,body FROM learning_labels"))
        self.assertEqual(len(rows), expected)
        for key, raw in rows:
            label = json.loads(raw)
            self.assertTrue(key.startswith("oracle_excluded:"))
            self.assertFalse(label["eligible"])
            self.assertEqual(label["eligibility"], "ineligible")
            self.assertIn(
                "manager_oracle_model_parameter_contract_unverified",
                label["exclusion_reasons"],
            )
            self.assertIn(
                "manager_trade_horizon_not_oracle_fixed_horizon",
                label["exclusion_reasons"],
            )
            original = label["oracle_provenance"]
            self.assertIn("parameters", original)
            self.assertIn("version", original)
            self.assertEqual(original["horizon_seconds"], 60)
            self.assertEqual(original["policy_hash"], self.engine.policy_hash)
            self.assertNotIn(
                original["strategy_id"], ("grid", "dca", "trend", "momentum")
            )

    def test_forecast_budget_refuses_incomplete_totals_and_later_wrong_rows_are_seen(
        self,
    ):
        import sqlite3
        from contextlib import closing

        first = self.owner.collect(self.home, self.spec.bot_id)
        with patch("soltui.learning_owner.FORECAST_MAX_ROWS", 2):
            rejected = self.owner.collect(self.home, self.spec.bot_id)
        self.assertFalse(rejected["counts_complete"])
        self.assertEqual(rejected["reason"], "forecast_resolution_scan_budget_exceeded")
        self.assertIsNone(rejected["resolved_comparable_labels"])
        with (
            patch("soltui.learning_owner.FORECAST_MAX_ROWS", 2),
            self.assertRaisesRegex(
                ValueError, "forecast_resolution_scan_budget_exceeded"
            ),
        ):
            self.owner.propose(self.home, self.spec.bot_id, "unused")
        with closing(sqlite3.connect(self.archive)) as db:
            pending = db.execute(
                "SELECT f.direction,f.reference FROM forecasts f LEFT JOIN resolutions r ON r.forecast=f.id WHERE r.forecast IS NULL ORDER BY f.issued DESC LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(pending)
        self.ingest(90, pending[1] - 20 if pending[0] > 0 else pending[1] + 20)
        second = self.owner.collect(self.home, self.spec.bot_id)
        self.assertTrue(second["counts_complete"])
        self.assertGreater(
            second["ineligible_forecasts"], first["ineligible_forecasts"]
        )
        self.assertGreater(
            second["cohorts"]["forecast_wrong"], first["cohorts"]["forecast_wrong"]
        )
        self.assertEqual(second["resolved_comparable_labels"], 0)

    def test_invalid_original_forecast_provenance_has_explicit_exclusion_reason(self):
        from soltui.learning_owner import excluded_oracle_forecast

        key, label = excluded_oracle_forecast(
            "scope",
            (
                1,
                "original",
                0,
                100,
                '{"forecast_id":"original","hit":0,"resolved_at":100}',
                "ma_crossover",
                "v1",
                40,
                100,
                "[]",
            ),
        )
        self.assertTrue(key.startswith("oracle_excluded:"))
        self.assertFalse(label["comparable"])
        self.assertIn("oracle_forecast_provenance_invalid", label["exclusion_reasons"])
        self.assertIn(
            "oracle_forecast_source_policy_unbound", label["exclusion_reasons"]
        )
