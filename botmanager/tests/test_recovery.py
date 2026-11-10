from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from botmanager.data import load_recording
from botmanager.domain import ManagerError
from botmanager.ledger import RuntimeLedger
from botmanager.strategies.grid import evaluate

from tests.test_paper import grid, recording


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.ledger = RuntimeLedger(self.home)
        self.spec = grid()
        self.data = load_recording(recording(self.home))
        self.ledger.register(self.spec, self.data)

    def tearDown(self):
        self.tmp.cleanup()

    def start(self):
        return self.ledger.control(self.spec, "start", str(uuid4()))

    def test_duplicate_request_and_start(self):
        rid = str(uuid4())
        a = self.ledger.control(self.spec, "start", rid)
        self.assertEqual(a, self.ledger.control(self.spec, "start", rid))
        self.start()
        gen = self.ledger.claim(self.spec.bot_id, "supervisor-a")
        self.assertIsNone(self.ledger.claim(self.spec.bot_id, "supervisor-a"))
        with self.assertRaises(ManagerError):
            self.ledger.control(self.spec, "stop", rid)
        self.assertEqual(self.ledger.get(self.spec.bot_id)["generation"], gen)

    def test_atomic_crashes_and_no_duplicate_fills(self):
        self.start()
        gen = self.ledger.claim(self.spec.bot_id, "supervisor-a")
        state = evaluate(self.spec, self.data, 4)

        def crash():
            raise RuntimeError("injected crash")

        with self.assertRaises(RuntimeError):
            self.ledger.commit_tick(
                self.spec.bot_id, gen, 0, state, before_commit=crash
            )
        self.assertEqual(self.ledger.get(self.spec.bot_id)["cursor"], 0)
        self.ledger.commit_tick(self.spec.bot_id, gen, 0, state)
        with self.assertRaises(ManagerError):
            self.ledger.commit_tick(self.spec.bot_id, gen, 0, state)
        self.ledger.recover("supervisor-b")
        newgen = self.ledger.claim(self.spec.bot_id, "supervisor-b")
        with self.assertRaises(ManagerError):
            self.ledger.commit_tick(
                self.spec.bot_id, gen, 4, evaluate(self.spec, self.data, 8)
            )
        final = evaluate(self.spec, self.data, 8)
        self.ledger.commit_tick(self.spec.bot_id, newgen, 4, final)
        self.assertEqual(self.ledger.get(self.spec.bot_id)["checkpoint"], final)
        self.assertEqual(self.ledger.fills(self.spec.bot_id), final["fills"])

    def test_stop_fences_inflight_and_survives_restart(self):
        self.start()
        gen = self.ledger.claim(self.spec.bot_id, "a")
        self.ledger.commit_tick(
            self.spec.bot_id, gen, 0, evaluate(self.spec, self.data, 2)
        )
        saved = self.ledger.get(self.spec.bot_id)["checkpoint"]
        self.ledger.control(self.spec, "stop", str(uuid4()))
        self.ledger.recover("b")
        self.assertIsNone(self.ledger.claim(self.spec.bot_id, "b"))
        self.assertEqual(saved, self.ledger.get(self.spec.bot_id)["checkpoint"])
        with self.assertRaises(ManagerError):
            self.ledger.commit_tick(
                self.spec.bot_id, gen, 2, evaluate(self.spec, self.data, 4)
            )

    def test_corrupt_checkpoint_or_fill_holds(self):
        self.start()
        gen = self.ledger.claim(self.spec.bot_id, "a")
        self.ledger.commit_tick(
            self.spec.bot_id, gen, 0, evaluate(self.spec, self.data, 4)
        )
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.execute("UPDATE fills SET body='{}' WHERE sequence=0")
        with self.assertRaises(ManagerError):
            self.ledger.get(self.spec.bot_id)

    def test_concurrent_commit_fenced(self):
        from concurrent.futures import ThreadPoolExecutor

        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "test")
        state = evaluate(self.spec, self.data, 4)

        def commit():
            try:
                self.ledger.commit_tick(self.spec.bot_id, generation, 0, state)
                return "committed"
            except ManagerError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: commit(), range(2)))
        self.assertEqual(sorted(results), ["committed", "stale_cursor"])
        self.assertEqual(self.ledger.fills(self.spec.bot_id), state["fills"])

    def test_corrupt_checkpoint_and_immutable_input_refused(self):
        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "test")
        state = evaluate(self.spec, self.data, 4)
        self.ledger.commit_tick(self.spec.bot_id, generation, 0, state)
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.execute("UPDATE runs SET checkpoint='{}'")
        with self.assertRaises(ManagerError):
            self.ledger.get(self.spec.bot_id)
        self.ledger.recover("next")
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            self.assertEqual(
                db.execute("SELECT observed FROM runs").fetchone()[0], "blocked"
            )

    def test_corrupt_checkpoint_does_not_prevent_durable_stop(self):
        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "test")
        self.ledger.commit_tick(
            self.spec.bot_id, generation, 0, evaluate(self.spec, self.data, 4)
        )
        with self.ledger.connection(True) as db:
            db.execute("UPDATE runs SET checkpoint='{}'")
        receipt = self.ledger.control(self.spec, "stop", str(uuid4()))
        self.assertEqual(receipt["reason"], "desired_state_saved")
        self.ledger.recover("restart")
        with self.ledger.connection() as db:
            row = db.execute("SELECT desired,observed FROM runs").fetchone()
        self.assertEqual(tuple(row), ("stopped", "blocked"))

    def test_registration_does_not_adopt_new_input_or_costs(self):
        self.assertTrue(self.ledger.register(self.spec, self.data)["registered"])
        data = load_recording({**self.data["descriptor"], "fee_bps": 12.0})
        with self.assertRaises(ManagerError):
            self.ledger.register(self.spec, data)
        self.assertEqual(
            self.ledger.get(self.spec.bot_id)["input"]["snapshot_hash"],
            self.data["snapshot_hash"],
        )

    def test_full_request_journal_reserves_stop_for_every_active_instance(self):
        specs = [self.spec] + [grid("capacity-" + str(i)) for i in range(3)]
        generations = {}
        starts = {}
        for index, spec in enumerate(specs):
            self.ledger.register(spec, self.data)
            request_id = str(uuid4())
            starts[spec.bot_id] = (
                request_id,
                self.ledger.control(spec, "start", request_id),
            )
            # Stop queued/pending intents before the two claimed workers.
            generations[spec.bot_id] = (
                self.ledger.get(spec.bot_id)["generation"]
                if index < 2
                else self.ledger.claim(spec.bot_id, "capacity-owner")
            )
        stopped_specs = [grid("registered-stopped-" + str(i)) for i in range(96)]
        for spec in stopped_specs:
            self.ledger.register(spec, self.data)
        with self.ledger.connection(True) as db:
            db.execute(
                "WITH RECURSIVE n(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM n WHERE i<99996) INSERT INTO requests(request_id,binding,receipt,checksum) SELECT 'capacity-fixture-'||i,'fixture','{}','fixture' FROM n"
            )
            self.assertEqual(
                db.execute("SELECT count(*) FROM requests").fetchone()[0], 100000
            )
        for spec in stopped_specs:
            with self.assertRaises(ManagerError) as refused:
                self.ledger.control(spec, "stop", str(uuid4()))
            self.assertEqual(refused.exception.code, "resource_limit")
            self.assertEqual(self.ledger.get(spec.bot_id)["desired"], "stopped")
        for spec in specs:
            with self.assertRaises(ManagerError) as refused:
                self.ledger.control(spec, "start", str(uuid4()))
            self.assertEqual(refused.exception.code, "resource_limit")
            request_id = str(uuid4())
            receipt = self.ledger.control(spec, "stop", request_id)
            self.assertEqual(receipt, self.ledger.control(spec, "stop", request_id))
            with self.assertRaises(ManagerError):
                self.ledger.commit_tick(
                    spec.bot_id,
                    generations[spec.bot_id],
                    0,
                    evaluate(spec, self.data, 2),
                )
            # A new-ID no-op must not consume another instance's reserved stop.
            with self.assertRaises(ManagerError):
                self.ledger.control(spec, "stop", str(uuid4()))
            with self.assertRaises(ManagerError):
                self.ledger.control(spec, "start", str(uuid4()))
        self.ledger.recover("after-capacity-restart")
        for spec in stopped_specs:
            self.assertEqual(self.ledger.get(spec.bot_id)["desired"], "stopped")
            self.assertIsNone(self.ledger.claim(spec.bot_id, "after-capacity-restart"))
        for spec in specs:
            self.assertEqual(self.ledger.get(spec.bot_id)["desired"], "stopped")
            self.assertIsNone(self.ledger.claim(spec.bot_id, "after-capacity-restart"))
            request_id, receipt = starts[spec.bot_id]
            self.assertEqual(receipt, self.ledger.control(spec, "start", request_id))
        with self.ledger.connection() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM requests").fetchone()[0], 100004
            )

    def test_exhausted_transition_fences_stale_and_incomplete_workers(self):
        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "test")
        with self.assertRaises(ManagerError) as incomplete:
            self.ledger.mark_exhausted(self.spec.bot_id, generation)
        self.assertEqual(incomplete.exception.code, "stale_cursor")
        self.ledger.commit_tick(
            self.spec.bot_id, generation, 0, evaluate(self.spec, self.data, 8)
        )
        self.ledger.control(self.spec, "stop", str(uuid4()))
        with self.assertRaises(ManagerError) as stale:
            self.ledger.mark_exhausted(self.spec.bot_id, generation)
        self.assertEqual(stale.exception.code, "stale_generation")
        self.assertEqual(self.ledger.get(self.spec.bot_id)["desired"], "stopped")

    def test_consistent_read_snapshot_during_valid_concurrent_commit(self):
        from contextlib import closing

        with closing(sqlite3.connect(self.ledger.path)) as db:
            self.assertEqual(db.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "writer")
        state = evaluate(self.spec, self.data, 4)
        observed = []
        reader = InterleavingLedger(
            self.home,
            lambda db: (
                observed.append(db.in_transaction),
                self.ledger.commit_tick(self.spec.bot_id, generation, 0, state),
            ),
        )
        snapshot = reader.get(self.spec.bot_id)
        self.assertEqual(observed, [True])
        self.assertEqual(snapshot["cursor"], 0)
        self.assertIsNone(snapshot["checkpoint"])
        self.assertEqual(self.ledger.get(self.spec.bot_id)["cursor"], 4)

    def test_same_control_receipt_cross_row_transplant_is_refused(self):
        first_id = str(uuid4())
        first = self.ledger.control(self.spec, "start", first_id)
        self.ledger.claim(self.spec.bot_id, "accepted-owner")
        second_id = str(uuid4())
        second = self.ledger.control(self.spec, "start", second_id)
        self.assertNotEqual(first["owner_generation"], second["owner_generation"])
        with self.ledger.connection(True) as db:
            row = db.execute(
                "SELECT receipt,checksum FROM requests WHERE request_id=?", (first_id,)
            ).fetchone()
            db.execute(
                "UPDATE requests SET receipt=?,checksum=? WHERE request_id=?",
                (*row, second_id),
            )
        before = self.ledger.get(self.spec.bot_id)
        with self.assertRaises(ManagerError) as caught:
            self.ledger.control(self.spec, "start", second_id)
        self.assertEqual(caught.exception.code, "invalid_receipt")
        self.assertEqual(self.ledger.get(self.spec.bot_id), before)
        with self.ledger.connection() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM requests").fetchone()[0], 2
            )

    def test_receipt_semantic_bindings_survive_recomputed_checksum(self):
        import json

        from botmanager.domain import canonical, fingerprint

        self.start()
        self.ledger.claim(self.spec.bot_id, "accepted-owner")
        request_id = str(uuid4())
        self.ledger.control(self.spec, "start", request_id)
        with self.ledger.connection() as db:
            original = dict(
                db.execute(
                    "SELECT * FROM requests WHERE request_id=?", (request_id,)
                ).fetchone()
            )
        mutations = {
            "request_id": str(uuid4()),
            "bot_id": str(uuid4()),
            "operation": "stop",
            "config_revision": 7,
            "runtime_id": str(uuid4()),
            "owner_id": "another-owner",
            "owner_generation": 17,
            "metadata": {"config_hash": "0" * 64},
            "outcome": "acknowledged",
            "reason": "desired_state_saved",
        }
        before = self.ledger.get(self.spec.bot_id)
        for key, value in mutations.items():
            with self.subTest(field=key):
                receipt = json.loads(original["receipt"])
                receipt[key] = value
                signed = {"binding": original["binding"], "receipt": receipt}
                if original.get("acceptance") is not None:
                    signed["acceptance"] = json.loads(original["acceptance"])
                with self.ledger.connection(True) as db:
                    db.execute(
                        "UPDATE requests SET receipt=?,checksum=? WHERE request_id=?",
                        (canonical(receipt), fingerprint(signed), request_id),
                    )
                with self.assertRaises(ManagerError) as caught:
                    self.ledger.control(self.spec, "start", request_id)
                self.assertEqual(caught.exception.code, "invalid_receipt")
                self.assertEqual(self.ledger.get(self.spec.bot_id), before)
        with self.ledger.connection(True) as db:
            db.execute(
                "UPDATE requests SET receipt=?,checksum=? WHERE request_id=?",
                (original["receipt"], original["checksum"], request_id),
            )

    def test_historical_receipts_keep_accepted_generation_and_owner(self):
        first_id = str(uuid4())
        first = self.ledger.control(self.spec, "start", first_id)
        self.ledger.claim(self.spec.bot_id, "old-owner")
        second_id = str(uuid4())
        second = self.ledger.control(self.spec, "start", second_id)
        self.ledger.control(self.spec, "stop", str(uuid4()))
        self.ledger.recover("new-owner")
        before = self.ledger.get(self.spec.bot_id)
        self.assertNotEqual(before["generation"], second["owner_generation"])
        self.assertEqual(first, self.ledger.control(self.spec, "start", first_id))
        self.assertEqual(second, self.ledger.control(self.spec, "start", second_id))
        self.assertEqual(before, self.ledger.get(self.spec.bot_id))

    def test_same_config_foreign_checkpoint_commit_is_refused(self):
        other = grid("same-config")
        self.assertEqual(self.spec.config_hash, other.config_hash)
        self.ledger.register(other, self.data)
        self.ledger.control(other, "start", str(uuid4()))
        generation = self.ledger.claim(other.bot_id, "other-worker")
        foreign = evaluate(self.spec, self.data, 4)
        with self.assertRaises(ManagerError) as caught:
            self.ledger.commit_tick(other.bot_id, generation, 0, foreign)
        self.assertEqual(caught.exception.code, "reconciliation_required")
        self.assertEqual(self.ledger.get(other.bot_id)["cursor"], 0)
        correct = evaluate(other, self.data, 4)
        self.ledger.commit_tick(other.bot_id, generation, 0, correct)
        self.assertEqual(self.ledger.get(other.bot_id)["checkpoint"], correct)

    def test_persisted_same_config_checkpoint_transplant_blocks_only_wrong_account(
        self,
    ):
        from botmanager.domain import canonical, fingerprint

        other = grid("same-config")
        self.ledger.register(other, self.data)
        self.ledger.control(other, "start", str(uuid4()))
        generation = self.ledger.claim(other.bot_id, "other-worker")
        own = evaluate(other, self.data, 4)
        self.ledger.commit_tick(other.bot_id, generation, 0, own)
        foreign = evaluate(self.spec, self.data, 4)
        self.assertEqual(foreign["fills"], own["fills"])
        with self.ledger.connection(True) as db:
            db.execute(
                "UPDATE runs SET checkpoint=?,checkpoint_hash=? WHERE bot_id=?",
                (canonical(foreign), fingerprint(foreign), other.bot_id),
            )
        with self.assertRaises(ManagerError) as caught:
            self.ledger.get(other.bot_id)
        self.assertEqual(caught.exception.code, "corrupt_checkpoint")
        self.ledger.recover("restart")
        with self.ledger.connection() as db:
            self.assertEqual(
                db.execute(
                    "SELECT observed FROM runs WHERE bot_id=?", (other.bot_id,)
                ).fetchone()[0],
                "blocked",
            )
        self.assertEqual(self.ledger.get(self.spec.bot_id)["observed"], "stopped")
        self.ledger.control(other, "stop", str(uuid4()))
        with self.ledger.connection() as db:
            self.assertEqual(
                db.execute(
                    "SELECT desired FROM runs WHERE bot_id=?", (other.bot_id,)
                ).fetchone()[0],
                "stopped",
            )

    def test_schema1_migration_preserves_unverifiable_ids_and_allows_fresh_stop(self):
        import json

        from botmanager.domain import fingerprint

        legacy_id = str(uuid4())
        receipt = self.ledger.control(self.spec, "start", legacy_id)
        generation = self.ledger.claim(self.spec.bot_id, "legacy-owner")
        old_binding = fingerprint(
            {
                "bot_id": self.spec.bot_id,
                "config_hash": self.spec.config_hash,
                "operation": "start",
            }
        )
        old_checksum = fingerprint({"binding": old_binding, "receipt": receipt})
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.execute("DROP TABLE archives")
            db.execute("DROP TABLE adoption_requests")
            db.execute("ALTER TABLE requests DROP COLUMN acceptance")
            db.execute(
                "UPDATE requests SET binding=?,checksum=? WHERE request_id=?",
                (old_binding, old_checksum, legacy_id),
            )
            db.execute("PRAGMA user_version=1")
            original = tuple(
                db.execute(
                    "SELECT * FROM requests WHERE request_id=?", (legacy_id,)
                ).fetchone()
            )
        self.assertEqual(self.ledger.get(self.spec.bot_id)["desired"], "running")
        with self.ledger.connection() as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
        with self.assertRaises(ManagerError) as caught:
            self.ledger.control(self.spec, "start", legacy_id)
        self.assertEqual(caught.exception.code, "invalid_receipt")
        self.assertIn("lacks acceptance context", caught.exception.message)
        with self.ledger.connection() as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(
                tuple(
                    db.execute(
                        "SELECT * FROM requests WHERE request_id=?", (legacy_id,)
                    ).fetchone()
                ),
                original,
            )
        stop_id = str(uuid4())
        stop = self.ledger.control(self.spec, "stop", stop_id)
        self.assertEqual(self.ledger.get(self.spec.bot_id)["desired"], "stopped")
        with self.assertRaises(ManagerError):
            self.ledger.commit_tick(
                self.spec.bot_id, generation, 0, evaluate(self.spec, self.data, 2)
            )
        with self.ledger.connection() as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)
            migrated = db.execute(
                "SELECT * FROM requests WHERE request_id=?", (legacy_id,)
            ).fetchone()
            self.assertEqual(tuple(migrated)[:4], original)
            self.assertIsNone(migrated["acceptance"])
            accepted = json.loads(
                db.execute(
                    "SELECT acceptance FROM requests WHERE request_id=?", (stop_id,)
                ).fetchone()[0]
            )
            self.assertEqual(accepted["request_id"], stop_id)
        self.ledger.recover("later-owner")
        self.assertEqual(stop, self.ledger.control(self.spec, "stop", stop_id))
        with self.assertRaises(ManagerError):
            self.ledger.control(self.spec, "start", legacy_id)
        self.assertEqual(self.ledger.get(self.spec.bot_id)["desired"], "stopped")

    def test_complete_checkpoint_identity_is_checked_before_write_and_on_read(self):
        import copy

        from botmanager.domain import canonical, fingerprint

        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "worker")
        original = evaluate(self.spec, self.data, 4)
        mutations = [
            (("identity", "config_revision"), 2),
            (("identity", "strategy_version"), "different-strategy"),
            (("identity", "target", "venue"), "different-venue"),
            (("identity", "reference", "quote_currency"), "USDC"),
            (("identity", "virtual_account"), "shared-wallet"),
            (("identity", "grid", "lower"), 1.0),
            (("identity", "snapshot_hash"), "0" * 64),
            (("run_hash",), "0" * 64),
            (("quote_currency",), "USDC"),
        ]
        for path, value in mutations:
            with self.subTest(path=path):
                checkpoint = copy.deepcopy(original)
                target = checkpoint
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                if path[0] == "identity":
                    checkpoint["run_hash"] = fingerprint(checkpoint["identity"])
                with self.assertRaises(ManagerError):
                    self.ledger.commit_tick(self.spec.bot_id, generation, 0, checkpoint)
                self.assertEqual(self.ledger.get(self.spec.bot_id)["cursor"], 0)
        self.ledger.commit_tick(self.spec.bot_id, generation, 0, original)
        wrong = copy.deepcopy(original)
        wrong["identity"]["target"]["venue"] = "different-venue"
        wrong["run_hash"] = fingerprint(wrong["identity"])
        with self.ledger.connection(True) as db:
            db.execute(
                "UPDATE runs SET checkpoint=?,checkpoint_hash=?",
                (canonical(wrong), fingerprint(wrong)),
            )
        with self.assertRaises(ManagerError):
            self.ledger.get(self.spec.bot_id)

    def test_rollback_journal_reader_releases_snapshot_before_writer_commit(self):
        import threading

        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "writer")
        state = evaluate(self.spec, self.data, 4)
        ready = threading.Event()
        failures = []

        def write():
            try:
                self.ledger.commit_tick(
                    self.spec.bot_id, generation, 0, state, before_commit=ready.set
                )
            except ManagerError as exc:
                failures.append(exc)

        thread = threading.Thread(target=write)

        def interleave(db):
            self.assertTrue(db.in_transaction)
            thread.start()
            self.assertTrue(ready.wait(0.5))

        reader = InterleavingLedger(self.home, interleave)
        try:
            self.assertEqual(reader.get(self.spec.bot_id)["cursor"], 0)
        finally:
            if thread.ident is not None:
                thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(self.ledger.get(self.spec.bot_id)["cursor"], 4)


class InterleavingLedger(RuntimeLedger):
    def __init__(self, home, interleave):
        super().__init__(home)
        self.interleave = interleave

    def _decode(self, db, row):
        if (
            self.interleave is not None
            and db.execute("PRAGMA query_only").fetchone()[0]
        ):
            action, self.interleave = self.interleave, None
            action(db)
        return super()._decode(db, row)
