from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from botmanager.data import load_recording
from botmanager.domain import ManagerError, fingerprint
from botmanager.health import HealthStore
from botmanager.learning import (
    canonical_scope,
    classify_outcome,
    learned_spec,
    outcome_summary,
    reconcile_transition,
)
from botmanager.ledger import RuntimeLedger
from botmanager.store import ManagerStore
from botmanager.strategies import evaluate

from tests.test_paper import grid, recording


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.spec = grid("incumbent")
        self.store = ManagerStore(self.home)
        self.store.create_spec(self.spec)
        self.data = load_recording(recording(self.home, 80))
        for bar in self.data["bars"]:
            bar.update(open=100, high=100, low=100, close=100)
        self.data["snapshot_hash"] = fingerprint(
            {k: v for k, v in self.data.items() if k != "snapshot_hash"}
        )
        self.ledger = RuntimeLedger(self.home)
        self.ledger.register(self.spec, self.data)
        self.ledger.control(self.spec, "start", str(uuid4()))
        generation = self.ledger.claim(self.spec.bot_id, "fixture-owner")
        self.cp = evaluate(self.spec, self.data, 70, entries_paused=True)
        self.ledger.begin_tick(self.spec.bot_id, generation)
        self.ledger.commit_tick(self.spec.bot_id, generation, 0, self.cp)
        row = self.ledger.get(self.spec.bot_id)
        HealthStore(self.home).pause(row, "pause", str(uuid4()))
        self.ledger.control(self.spec, "stop", str(uuid4()))
        self.ledger.stopped(self.spec.bot_id)

    def receipt(self, request_id=None, changes=None):
        changes = changes or {"rungs": 8}
        proposed = learned_spec(self.spec, changes, "e" * 64)
        run = self.ledger.get(self.spec.bot_id)
        receipt = {
            "version": 1,
            "request_id": request_id or str(uuid4()),
            "proposal_id": str(uuid4()),
            "operation": "promote",
            "scope": "scope",
            "bot_id": self.spec.bot_id,
            "runtime_id": run["runtime_id"],
            "expected_revision": self.spec.config_revision,
            "expected_hash": self.spec.config_hash,
            "pins": dict(self.spec.user_overrides),
            "changes": changes,
            "accepted_spec": proposed.to_dict(),
            "evidence_digest": "e" * 64,
            "authority": {"root": "/controlled-fixture", "namespace_id": "fixture"},
            "authorized_at": 100,
            "manager_home": str(self.store.home.resolve()),
            "state": "authorized_pending_manager",
            "safe_to_retry": False,
        }
        receipt["digest"] = fingerprint(receipt)
        return receipt

    def test_learning_uses_all_eligible_outcomes(self):
        outcomes = [
            {
                "kind": "forecast",
                "correct": correct,
                "resolved": True,
                "comparable": True,
            }
            for correct in (True, False)
        ]
        outcomes += [
            {"kind": "trade", "net_pnl": pnl, "resolved": True, "comparable": True}
            for pnl in (10, -5)
        ]
        outcomes += [
            {"kind": kind, "resolved": False, "comparable": False}
            for kind in ("execution_fault", "data_fault", "inventory")
        ]
        result = outcome_summary(outcomes)
        self.assertEqual(result["outcomes"], 7)
        self.assertEqual(result["resolved_comparable_labels"], 4)
        self.assertEqual(result["completed_trades"], 2)
        self.assertEqual(
            set(result["cohorts"]),
            {
                "forecast_correct",
                "forecast_wrong",
                "trade_loss",
                "trade_nonloss",
                "data_fault",
                "execution_fault",
                "unresolved",
            },
        )

    def test_normal_loss_does_not_mutate_config(self):
        original = self.store.get_spec(self.spec.bot_id)
        self.assertEqual(
            classify_outcome(
                {"kind": "trade", "net_pnl": -10, "resolved": True, "comparable": True}
            )["cohort"],
            "trade_loss",
        )
        self.assertEqual(self.store.get_spec(self.spec.bot_id), original)

    def test_pins_and_cas_retain_incumbent(self):
        pinned = self.spec.edited({"rungs": 9})
        with self.assertRaises(ManagerError):
            learned_spec(pinned, {"rungs": 8}, "e")
        for field in (
            "capital_usd",
            "armed",
            "mode",
            "stop_loss_pct",
            "base_order_usd",
        ):
            with self.assertRaises(ManagerError):
                learned_spec(self.spec, {field: 1}, "e")
        receipt = self.receipt()
        self.store.edit(self.spec.bot_id, {"range_pct": 12}, expected_revision=1)
        incumbent = self.store.get_spec(self.spec.bot_id)
        with self.assertRaises(ManagerError):
            self.ledger.learning_adopt(self.store, receipt)
        self.assertEqual(incumbent, self.store.get_spec(self.spec.bot_id))

    def test_account_preserved_and_replay_once(self):
        receipt = self.receipt()
        before = self.ledger.get(self.spec.bot_id)
        result = self.ledger.learning_adopt(self.store, receipt)
        after = self.ledger.get(self.spec.bot_id)
        self.assertEqual(after["runtime_id"], before["runtime_id"])
        self.assertEqual(after["cursor"], before["cursor"])
        for key in (
            "cash_quote",
            "equity_quote",
            "realized_net_pnl_quote",
            "unrealized_net_pnl_quote",
            "fees_quote",
            "slippage_quote",
            "carry_paid_quote",
            "carry_accrued_quote",
            "fills",
            "lots",
        ):
            self.assertEqual(after["checkpoint"][key], before["checkpoint"][key])
        self.assertEqual(result, self.ledger.learning_adopt(self.store, receipt))
        self.assertEqual(len(self.store.history(self.spec.bot_id)), 2)
        self.assertEqual(
            self.store.get_spec(self.spec.bot_id).user_overrides,
            before["spec"]["user_overrides"],
        )
        advanced = evaluate(
            self.store.get_spec(self.spec.bot_id),
            after["input"],
            80,
            previous=after["checkpoint"],
            entries_paused=True,
        )
        self.assertEqual(advanced["cash_quote"], self.cp["cash_quote"])

    def test_adoption_crash_reconciles_once(self):
        receipt = self.receipt()

        class Owner:
            fail = True

            def call(self, operation, params):
                if operation == "learning-promote":
                    return {"receipt": receipt}
                if self.fail:
                    self.fail = False
                    raise OSError("fixture crash after manager publication")
                return {"state": "adopted", "receipt": params["manager_receipt"]}

        owner = Owner()
        with self.assertRaises(OSError):
            reconcile_transition(
                self.store,
                owner,
                receipt["proposal_id"],
                request_id=receipt["request_id"],
            )
        result = reconcile_transition(
            self.store, owner, receipt["proposal_id"], request_id=receipt["request_id"]
        )
        self.assertEqual(result["accepted_revision"], 2)
        self.assertEqual(len(self.store.history(self.spec.bot_id)), 2)
        self.assertEqual(
            len(
                [
                    e
                    for e in self.ledger.events(self.spec.bot_id)
                    if e["kind"] == "learning.promote"
                ]
            ),
            1,
        )

    def test_new_uuid_does_not_change_scope(self):
        other = grid("other")
        self.assertEqual(
            canonical_scope(self.spec, self.data["identity"]),
            canonical_scope(other, self.data["identity"]),
        )

    def test_promotion_retains_real_closed_losses_and_fees(self):
        self.home = self.home / "loss-account"
        self.home.mkdir()
        self.spec = grid("loss-account")
        self.store = ManagerStore(self.home)
        self.store.create_spec(self.spec)
        data = load_recording(recording(self.home, 80))
        data["descriptor"]["fee_bps"] = 1000
        data["identity"]["costs"]["fee_bps"] = 1000
        for index, bar in enumerate(data["bars"]):
            price = 100 if index == 0 else 90 if index < 3 else 120
            bar.update(open=price, high=price, low=price, close=price)
        data["snapshot_hash"] = fingerprint(
            {k: v for k, v in data.items() if k != "snapshot_hash"}
        )
        self.ledger = RuntimeLedger(self.home)
        self.ledger.register(self.spec, data)
        self.ledger.control(self.spec, "start", str(uuid4()))
        generation = self.ledger.claim(self.spec.bot_id, "fixture")
        first = evaluate(self.spec, data, 3)
        self.ledger.begin_tick(self.spec.bot_id, generation)
        self.ledger.commit_tick(self.spec.bot_id, generation, 0, first)
        HealthStore(self.home).pause(
            self.ledger.get(self.spec.bot_id), "pause", str(uuid4())
        )
        row = self.ledger.get(self.spec.bot_id)
        closed = evaluate(self.spec, data, 70, previous=first, entries_paused=True)
        self.ledger.begin_tick(self.spec.bot_id, row["generation"])
        self.ledger.commit_tick(self.spec.bot_id, row["generation"], 3, closed)
        self.ledger.control(self.spec, "stop", str(uuid4()))
        self.ledger.stopped(self.spec.bot_id)
        self.assertLess(closed["realized_net_pnl_quote"], 0)
        self.assertLess(closed["cash_quote"], 1000)
        self.assertEqual(closed["lots"], [])
        self.ledger.learning_adopt(self.store, self.receipt())
        after = self.ledger.get(self.spec.bot_id)["checkpoint"]
        for key in ("cash_quote", "realized_net_pnl_quote", "fees_quote", "fills"):
            self.assertEqual(after[key], closed[key])

    def test_unbound_and_copied_home_authorizations_refuse_before_mutation_even_replay(
        self,
    ):
        import shutil

        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory).resolve() / "clone"
            receipt = self.receipt()
            self.ledger.learning_adopt(self.store, receipt)
            shutil.copytree(self.home, clone)
            original = {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
            copied = {p.name: p.read_bytes() for p in clone.glob("*.sqlite3")}
            with self.assertRaises(ManagerError) as wrong:
                RuntimeLedger(clone).learning_adopt(ManagerStore(clone), receipt)
            self.assertEqual(wrong.exception.code, "identity_conflict")
            self.assertEqual(
                original, {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
            )
            self.assertEqual(
                copied, {p.name: p.read_bytes() for p in clone.glob("*.sqlite3")}
            )
            legacy = dict(receipt)
            legacy.pop("manager_home")
            legacy.pop("digest")
            legacy["digest"] = fingerprint(legacy)
            absent = Path(directory) / "absent"
            with self.assertRaises(ManagerError) as unbound:
                RuntimeLedger(absent).learning_adopt(ManagerStore(absent), legacy)
            self.assertEqual(unbound.exception.code, "invalid_receipt")
            self.assertFalse(absent.exists())


def controlled_shadow_worker(home, bot_id, generation, parent_pid):
    from botmanager.worker import prospective_tick, run_worker

    from tests.test_oracle_data import START

    def tick(ledger, row, generation):
        return prospective_tick(ledger, row, generation, now=START + 601)

    with patch("botmanager.worker.prospective_tick", side_effect=tick):
        run_worker(home, bot_id, generation, parent_pid)


class RealShadowWorkerTests(unittest.TestCase):
    def test_shadow_uses_real_prospective_workers_and_is_idempotent(self):
        import time

        from botmanager.learning import comparable_identity
        from botmanager.oracle_data import capture, prepare_descriptor
        from botmanager.supervisor import Supervisor

        from soltui.experiments import ExperimentStore
        from soltui.learning_owner import LearningOwner
        from tests.test_oracle_data import START, append, archive

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = archive(root / "history.sqlite3", 120)
            home = root / "manager"
            spec = grid("incumbent")
            store = ManagerStore(home)
            store.create_spec(spec)
            ledger = RuntimeLedger(home)
            data = capture(
                prepare_descriptor(
                    root / "history.sqlite3",
                    capital_quote=1000,
                    strategy_id="grid",
                    now=START + 120,
                ),
                now=START + 120,
            )
            ledger.register(spec, data)
            authority = ExperimentStore(root / "authority")
            owner = LearningOwner(
                authority.root, {"namespace_id": "fixture"}, authority
            )
            proposal = {
                "version": 1,
                "id": str(uuid4()),
                "scope": canonical_scope(spec, data["identity"]),
                "day": "fixture",
                "home": str(home),
                "bot_id": spec.bot_id,
                "runtime_id": ledger.get(spec.bot_id)["runtime_id"],
                "baseline": spec.to_dict(),
                "changes": {"rungs": 8},
                "pins": {},
                "evidence": {"evidence_digest": "f" * 64},
                "comparability": comparable_identity(ledger.get(spec.bot_id)),
                "counts": {"resolved_comparable_labels": 300, "completed_trades": 30},
                "shadow": None,
                "state": "pending_shadow",
            }
            with owner.connection(True) as db:
                db.execute(
                    "INSERT INTO learning_proposals VALUES (?,?,?,?)",
                    (
                        proposal["id"],
                        proposal["scope"],
                        "fixture",
                        json.dumps(proposal),
                    ),
                )
            with patch("soltui.learning_owner.time.time", return_value=START + 120):
                started = owner.start_shadow(proposal["id"])
                replay = owner.start_shadow(proposal["id"])
            self.assertEqual(started, replay)
            self.assertEqual(len(store.list_specs()), 3)
            self.assertEqual(len(started["shadow"]["runs"]), 2)
            # Keep accounts flat so the test can exercise a legal same-runtime
            # configuration adoption after actual prospective worker progress.
            for binding in started["shadow"]["runs"]:
                HealthStore(home).pause(
                    ledger.get(binding["bot_id"]), "pause", str(uuid4())
                )
            append(source, 120, 601)
            supervisor = Supervisor(home, worker_target=controlled_shadow_worker).open()
            try:
                deadline = time.monotonic() + 8
                identifiers = [
                    binding["bot_id"] for binding in started["shadow"]["runs"]
                ]
                while time.monotonic() < deadline:
                    supervisor.step()
                    if all(ledger.get(bot)["cursor"] == 8 for bot in identifiers):
                        break
                    time.sleep(0.03)
                self.assertTrue(
                    all(ledger.get(bot)["cursor"] == 8 for bot in identifiers)
                )
                self.assertTrue(
                    all(
                        ledger.get(bot)["checkpoint"]["continuation"]
                        for bot in identifiers
                    )
                )
                self.assertTrue(
                    all(
                        ledger.get(bot)["input"]["prospective"] is not None
                        for bot in identifiers
                    )
                )
                self.assertNotEqual(
                    ledger.get(identifiers[0])["runtime_id"],
                    ledger.get(identifiers[1])["runtime_id"],
                )
                progress = owner._shadow_progress(started)
                self.assertTrue(progress["complete"])
                self.assertFalse(
                    progress["states"][0]["run"]["input"]["identity"][
                        "venue_compatibility_verified"
                    ]
                )
                for binding in started["shadow"]["runs"]:
                    self.assertNotEqual(
                        binding["input_hash"],
                        ledger.get(binding["bot_id"])["input"]["snapshot_hash"],
                    )
                # A legal safe-boundary adoption keeps runtime identity but must
                # invalidate the parent proposal's exact paired configuration.
                from botmanager.domain import BotSpec

                challenger_id = next(
                    binding["bot_id"]
                    for binding in started["shadow"]["runs"]
                    if binding["role"] == "challenger"
                )
                active = ledger.get(challenger_id)
                shadow_spec = BotSpec.from_dict(active["spec"])
                ledger.control(shadow_spec, "stop", str(uuid4()))
                supervisor.step()
                active = ledger.get(challenger_id)
                updated = learned_spec(shadow_spec, {"range_pct": 10}, "e" * 64)
                receipt = {
                    "version": 1,
                    "request_id": str(uuid4()),
                    "proposal_id": proposal["id"],
                    "operation": "promote",
                    "scope": proposal["scope"],
                    "bot_id": challenger_id,
                    "runtime_id": active["runtime_id"],
                    "expected_revision": shadow_spec.config_revision,
                    "expected_hash": shadow_spec.config_hash,
                    "pins": dict(shadow_spec.user_overrides),
                    "changes": {"range_pct": 10},
                    "accepted_spec": updated.to_dict(),
                    "evidence_digest": "e" * 64,
                    "authority": {
                        "root": str(authority.root),
                        "namespace_id": "fixture",
                    },
                    "authorized_at": START + 601,
                    "manager_home": str(store.home.resolve()),
                    "state": "authorized_pending_manager",
                    "safe_to_retry": False,
                }
                receipt["digest"] = fingerprint(receipt)
                ledger.learning_adopt(store, receipt)
                self.assertEqual(
                    active["runtime_id"], ledger.get(challenger_id)["runtime_id"]
                )
                invalid = owner._shadow_progress(started)
                self.assertFalse(invalid["complete"])
                self.assertEqual(invalid["reason"], "shadow_binding_changed")
            finally:
                supervisor.close()


class LearningLocalReadTests(unittest.TestCase):
    def test_snapshot_no_home_initialization(self):
        from botmanager.learning import learning_snapshot

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "missing"
            result = learning_snapshot(home, "unused")
            self.assertEqual(result["owner_eligibility"], "unknown")
            self.assertFalse(home.exists())


class ShadowActivationRecoveryTests(unittest.TestCase):
    def test_owner_retry_recovers_first_member_activation_after_peer_crash(self):
        from botmanager.learning import comparable_identity
        from botmanager.oracle_data import capture, prepare_descriptor

        from soltui.experiments import ExperimentStore
        from soltui.learning_owner import LearningOwner
        from tests.test_oracle_data import START, append, archive

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source_path = root / "history.sqlite3"
            source = archive(source_path, 120)
            home = root / "manager"
            store, ledger = ManagerStore(home), RuntimeLedger(home)
            baseline = grid("crash-retry-source")
            store.create_spec(baseline)
            data = capture(
                prepare_descriptor(
                    source_path, capital_quote=1000, strategy_id="grid", now=START + 120
                ),
                now=START + 120,
            )
            ledger.register(baseline, data)
            authority = ExperimentStore(root / "authority")
            owner = LearningOwner(
                authority.root, {"namespace_id": "fixture"}, authority
            )
            proposal = {
                "version": 1,
                "id": str(uuid4()),
                "scope": canonical_scope(baseline, data["identity"]),
                "day": "fixture",
                "home": str(home),
                "bot_id": baseline.bot_id,
                "runtime_id": ledger.get(baseline.bot_id)["runtime_id"],
                "baseline": baseline.to_dict(),
                "changes": {"rungs": 8},
                "pins": {},
                "evidence": {"evidence_digest": "e" * 64},
                "comparability": comparable_identity(ledger.get(baseline.bot_id)),
                "counts": {"resolved_comparable_labels": 300, "completed_trades": 30},
                "shadow": None,
                "state": "pending_shadow",
            }
            with owner.connection(True) as db:
                db.execute(
                    "INSERT INTO learning_proposals VALUES (?,?,?,?)",
                    (
                        proposal["id"],
                        proposal["scope"],
                        "fixture",
                        json.dumps(proposal),
                    ),
                )
            register = RuntimeLedger.register

            def crash_on_challenger(target, spec, snapshot):
                if spec.resolved_values["rungs"] == 8:
                    raise RuntimeError("fixture crash after incumbent activation")
                return register(target, spec, snapshot)

            with (
                patch("soltui.learning_owner.time.time", return_value=START + 120),
                patch.object(
                    RuntimeLedger,
                    "register",
                    autospec=True,
                    side_effect=crash_on_challenger,
                ),
                self.assertRaisesRegex(RuntimeError, "after incumbent"),
            ):
                owner.start_shadow(proposal["id"])
            with owner.connection() as db:
                reserved = owner._read_proposal(db, proposal["id"])
            pair_ids = reserved["shadow"]["pair_ids"]
            self.assertIsNone(reserved["shadow"]["runs"])
            incumbent = ledger.get(pair_ids["incumbent"])
            self.assertEqual(incumbent["desired"], "running")
            self.assertIsNone(ledger.get(pair_ids["challenger"]))
            # New source observations and a later owner clock cannot select a
            # different activation contract for the missing peer.
            append(source, 120, 123)
            with (
                patch("soltui.learning_owner.time.time", return_value=START + 123),
                patch(
                    "botmanager.oracle_data.prepare_descriptor",
                    side_effect=AssertionError("retry recaptured source"),
                ),
            ):
                recovered = owner.start_shadow(proposal["id"])
            self.assertEqual(recovered["id"], proposal["id"])
            self.assertEqual(recovered["shadow"]["pair_ids"], pair_ids)
            bindings = recovered["shadow"]["runs"]
            self.assertEqual(
                len({binding["immutable_input"] for binding in bindings}), 1
            )
            self.assertEqual(len({binding["input_hash"] for binding in bindings}), 1)
            for identity in pair_ids.values():
                member = ledger.get(identity)
                self.assertEqual(
                    member["input"]["descriptor"], incumbent["input"]["descriptor"]
                )
                self.assertEqual(
                    member["input"]["descriptor"]["activation_at"], START + 120
                )
                self.assertEqual(member["desired"], "running")
            self.assertEqual(
                ledger.get(pair_ids["incumbent"])["runtime_id"], incumbent["runtime_id"]
            )
            with patch("soltui.learning_owner.time.time", return_value=START + 124):
                self.assertEqual(owner.start_shadow(proposal["id"]), recovered)
            self.assertEqual(len(store.list_specs()), 3)
            self.assertEqual(len(ledger.ids()), 3)
