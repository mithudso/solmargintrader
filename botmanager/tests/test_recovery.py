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
                "WITH RECURSIVE n(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM n WHERE i<99996) INSERT INTO requests SELECT 'capacity-fixture-'||i,'fixture','{}','fixture' FROM n"
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
