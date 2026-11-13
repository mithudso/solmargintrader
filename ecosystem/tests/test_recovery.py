from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem import recovery
from ecosystem.backtests import create_batch
from ecosystem.recovery import ensure_batch
from soltui.config import Settings


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "batches"
        self.settings = Settings(data_dir=str(self.home / "accepted"))
        self.cfg = {
            "coins": ["BTC", "SOL"],
            "intervals": ["1d"],
            "strategies": ["buy_and_hold", "rsi"],
            "horizons": ["medium"],
        }

    def create(self):
        return create_batch(
            self.settings,
            self.cfg["coins"],
            root=self.root,
            intervals=self.cfg["intervals"],
            strategy_ids=self.cfg["strategies"],
            horizons=self.cfg["horizons"],
        )

    def db(self, batch):
        return Path(batch["directory"]) / "batch.sqlite3"

    def mutate(self, batch, sql, params=()):
        with closing(sqlite3.connect(self.db(batch))) as db, db:
            db.execute(sql, params)

    def assert_refuses(self):
        before = set(self.root.iterdir())
        with self.assertRaisesRegex(ValueError, "^batch_recovery_unavailable$"):
            ensure_batch(self.settings, self.cfg, self.root)
        self.assertEqual(
            set(self.root.iterdir()) - before,
            {self.root / "bootstrap-create.lock"} - before,
        )

    def test_create_then_uncheckpointed_restart_adopts_same_identity(self):
        # The owner created a complete ledger, but bootstrap never saved batch_id.
        uncheckpointed = self.create()
        before = hashlib.sha256(self.db(uncheckpointed).read_bytes()).hexdigest()
        with patch("ecosystem.backtests.create_batch") as create:
            resumed = ensure_batch(self.settings, self.cfg, self.root)
        create.assert_not_called()
        self.assertEqual(resumed["run_id"], uncheckpointed["run_id"])
        self.assertEqual(resumed["recovery"], "adopted")
        self.assertEqual(resumed["cells"], 4)
        self.assertEqual(
            hashlib.sha256(self.db(uncheckpointed).read_bytes()).hexdigest(), before
        )
        self.assertEqual(len(list(self.root.glob("*/batch.sqlite3"))), 1)

    def test_fresh_creation_is_idempotent(self):
        first = ensure_batch(self.settings, self.cfg, self.root)
        second = ensure_batch(self.settings, self.cfg, self.root)
        self.assertEqual(first["recovery"], "created")
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(second["recovery"], "adopted")

    def test_fault_after_owner_commit_recovers_without_creating_another_plan(self):
        committed = []

        def create_then_fail(*args, **kwargs):
            committed.append(create_batch(*args, **kwargs))
            raise OSError("checkpoint gap")

        with (
            patch("ecosystem.backtests.create_batch", side_effect=create_then_fail),
            self.assertRaisesRegex(ValueError, "^batch_recovery_unavailable$"),
        ):
            ensure_batch(self.settings, self.cfg, self.root)
        recovered = ensure_batch(self.settings, self.cfg, self.root)
        self.assertEqual(recovered["run_id"], committed[0]["run_id"])
        self.assertEqual(len(list(self.root.glob("*/batch.sqlite3"))), 1)

    def test_partial_directory_is_preserved_and_refused(self):
        (self.root / ("a" * 32)).mkdir(parents=True)
        self.assert_refuses()

    def test_multiple_complete_plans_are_ambiguous(self):
        self.create()
        self.create()
        self.assert_refuses()

    def test_wrong_version_identity_settings_matrix_or_fingerprint_refuses(self):
        batch = self.create()
        changes = (
            ("version", 2),
            ("id", "b" * 32),
            ("phase", "backtesting"),
            ("settings", {"data_dir": "/unverified", "capital": 1}),
            ("code_sources", {}),
            ("code_id", "0" * 64),
            ("assets", ["SOL"]),
            ("longest_contiguous", True),
        )
        for key, value in changes:
            with self.subTest(key=key):
                with closing(sqlite3.connect(self.db(batch))) as db:
                    original = db.execute(
                        "SELECT value FROM meta WHERE key=?", (key,)
                    ).fetchone()[0]
                self.mutate(
                    batch,
                    "UPDATE meta SET value=? WHERE key=?",
                    (json.dumps(value), key),
                )
                self.assert_refuses()
                self.mutate(
                    batch, "UPDATE meta SET value=? WHERE key=?", (original, key)
                )
        self.mutate(batch, "DELETE FROM cell WHERE id=1")
        self.assert_refuses()

    def test_completed_running_or_partly_evaluated_cells_are_refused(self):
        batch = self.create()
        for state in ("running", "completed", "failed"):
            self.mutate(batch, "UPDATE cell SET state=? WHERE id=1", (state,))
            self.assert_refuses()
        self.mutate(batch, "UPDATE cell SET state='pending',score=1 WHERE id=1")
        self.assert_refuses()

    def test_attempt_or_series_evidence_blocks_unstarted_adoption(self):
        batch = self.create()
        self.mutate(batch, "INSERT INTO attempt VALUES(1,'job','failed','{}')")
        self.assert_refuses()
        self.mutate(batch, "DELETE FROM attempt")
        self.mutate(batch, "INSERT INTO series VALUES('SOL','1d','/source','hash')")
        self.assert_refuses()

    def test_prior_worker_artifacts_and_active_lock_are_refused(self):
        batch = self.create()
        directory = Path(batch["directory"])
        token = directory / "worker-token"
        token.write_text("a" * 32)
        self.assert_refuses()
        token.unlink()
        fd = os.open(directory / "worker.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assert_refuses()
        finally:
            os.close(fd)

    def test_symlink_database_or_candidate_is_refused(self):
        batch = self.create()
        original = self.db(batch)
        moved = original.with_suffix(".retained")
        original.rename(moved)
        original.symlink_to(moved)
        self.assert_refuses()

    def test_source_change_after_creation_refuses_recovery(self):
        self.create()
        with patch(
            "soltui.bgworker.evaluation_code_fingerprint",
            return_value={"changed.py": "a" * 64},
        ):
            self.assert_refuses()

    def test_directory_lock_is_not_accepted_as_idle(self):
        self.create()
        (self.root / "f5-worker.lock").mkdir()
        self.assert_refuses()

    def test_fifo_owner_lock_is_refused_without_blocking(self):
        batch = self.create()
        before = hashlib.sha256(self.db(batch).read_bytes()).hexdigest()
        fifo = self.root / "f5-worker.lock"
        os.mkfifo(fifo, 0o600)
        entered, done = threading.Event(), threading.Event()
        errors = []
        opened = os.open

        def inspect_open(path, flags, *args):
            if Path(path) == fifo:
                entered.set()
            return opened(path, flags, *args)

        def inspect():
            try:
                ensure_batch(self.settings, self.cfg, self.root)
            except ValueError as error:
                errors.append(str(error))
            finally:
                done.set()

        with patch.object(recovery.os, "open", side_effect=inspect_open):
            thread = threading.Thread(target=inspect, daemon=True)
            thread.start()
            self.assertTrue(entered.wait(2))
            finished = done.wait(0.2)
            if not finished:
                writer = opened(fifo, os.O_WRONLY | os.O_NONBLOCK)
                os.close(writer)
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertTrue(finished, "recovery blocked before validating the owner lock")
        self.assertEqual(errors, ["batch_recovery_unavailable"])
        self.assertEqual(
            hashlib.sha256(self.db(batch).read_bytes()).hexdigest(), before
        )


if __name__ == "__main__":
    unittest.main()
