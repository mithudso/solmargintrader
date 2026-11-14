"""A new reader explains a frozen producer's pending window without changing it."""

from __future__ import annotations

import copy
import hashlib
import sqlite3
import time
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ecosystem import control

BASE = 1_800_000_000
LATE = "Forecast window elapsed during calculation"


class ForwardStatusProjection(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "control"
        self.batch = "a" * 32
        self.directory = self.home / "batches" / self.batch
        self.directory.mkdir(parents=True)
        self.metadata = self.directory / "batch.sqlite3"
        self.native = self.directory / "forward.sqlite3"
        self.target = BASE + 120 + 1440 * 60
        self.checked = BASE + 3604
        self.now = self.checked + 1
        self.label = f"f5:{self.batch}:rsi:1d:medium"
        self.state = {
            "batch_id": self.batch, "supervisor_running": True,
            "batch": {
                "running": True,
                "forward_checks": [{
                    "asset": "SOL", "interval": "1d", "at": self.checked,
                    "recorded": 0, "total_recorded": 1, "trials_expected": 1,
                    "trials_recorded": 1, "error": "", "message": LATE,
                }],
            },
        }
        with closing(sqlite3.connect(self.metadata)) as db, db:
            db.execute("CREATE TABLE cell(asset,interval,strategy,horizon,selected)")
            db.execute("INSERT INTO cell VALUES('SOL','1d','rsi','medium','{}')")
        self.seed()
        self.plane = control.ControlPlane(self.home, Path(temporary.name) / "manager")
        self.addCleanup(self.plane.close)

    def seed(self):
        with closing(sqlite3.connect(self.native)) as db, db:
            db.executescript(
                "DROP TABLE IF EXISTS trial; DROP TABLE IF EXISTS call;"
                "CREATE TABLE trial(id,asset,label,minutes);"
                "CREATE TABLE call(trial,bar,issued,start,finish,outcome,expired);"
            )
            db.execute("INSERT INTO trial VALUES('frozen-trial','SOL',?,1440)", (self.label,))
            db.execute("INSERT INTO call VALUES(?,?,?,?,?,?,?)", (
                "frozen-trial", BASE, BASE + 64, BASE + 120, self.target, None, 0,
            ))

    def project(self):
        with (
            patch.object(control.runner, "status", return_value=self.state) as status,
            patch.object(control.time, "time", return_value=self.now),
        ):
            result = self.plane.pipeline_status()
        status.assert_called_once_with(self.home)
        return result["batch"]["forward_checks"][0]

    def test_pending_window_uses_saved_target_without_writes_or_owner_mutation(self):
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (self.metadata, self.native)}
        original = copy.deepcopy(self.state)
        result = self.project()
        self.assertEqual(result["message"], "Waiting for existing forecast window")
        self.assertEqual(result["owner_message"], LATE)
        timing = result["timing"]
        self.assertEqual(timing["state"], "pending_not_due")
        self.assertTrue(timing["read_only_projection"])
        self.assertEqual(timing["source"], "native_forward_call")
        self.assertEqual(timing["source_path"], str(self.native))
        self.assertEqual(timing["pending_calls"], [{
            "trial_id": "frozen-trial", "issued_at": BASE + 64,
            "opens_at": BASE + 120, "target_at": self.target,
        }])
        self.assertEqual(self.state, original)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in before})
        with closing(sqlite3.connect(self.native)) as db:
            self.assertEqual(db.execute("SELECT count(*),max(outcome) FROM call").fetchone(), (1, None))

    def test_due_stale_failed_or_unavailable_checks_keep_owner_warning(self):
        original = copy.deepcopy(self.state)
        cases = (
            ("target_passed", self.target + 1, self.target, {}, {}),
            ("next_window_due", self.target - 59, self.target - 60, {}, {}),
            ("admission_boundary_crossed", self.target - 56, self.target - 116, {}, {}),
            ("stale_check", self.checked + 121, self.checked, {}, {}),
            ("future_check", self.checked - 1, self.checked, {}, {}),
            ("owner_unavailable", self.now, self.checked, {}, {"running": False}),
            ("failed_check", self.now, self.checked, {"error": "source unavailable"}, {}),
            ("missing_trial", self.now, self.checked, {"trials_expected": 2}, {}),
            ("partial_evidence", self.now, self.checked, {"trials_recorded": 0}, {}),
            ("call_was_recorded", self.now, self.checked, {"recorded": 1}, {}),
        )
        for name, now, checked, changes, batch_changes in cases:
            with self.subTest(name=name):
                self.state = copy.deepcopy(original)
                self.now = now
                self.state["batch"].update(batch_changes)
                self.state["batch"]["forward_checks"][0].update(at=checked, **changes)
                result = self.project()
                self.assertEqual(result["message"], LATE)
                self.assertNotIn("timing", result)

    def test_missing_ambiguous_or_invalid_native_history_keeps_owner_warning(self):
        for statement in (
            "DELETE FROM call",
            "INSERT INTO trial SELECT 'ambiguous',asset,label,minutes FROM trial",
            "UPDATE call SET issued=start",
            "UPDATE call SET issued=bar",
            "UPDATE call SET outcome=1",
            "UPDATE call SET expired=1",
            "UPDATE call SET finish=finish+1",
        ):
            with self.subTest(statement=statement):
                self.seed()
                with closing(sqlite3.connect(self.native)) as db, db:
                    db.execute(statement)
                result = self.project()
                self.assertEqual(result["message"], LATE)
                self.assertNotIn("timing", result)

    def test_one_non_due_trial_cannot_hide_another_due_trial(self):
        self.state["batch"]["forward_checks"][0].update(
            trials_expected=2, trials_recorded=2,
        )
        with closing(sqlite3.connect(self.metadata)) as db, db:
            db.execute("INSERT INTO cell VALUES('SOL','1d','macd','medium','{}')")
        with closing(sqlite3.connect(self.native)) as db, db:
            db.execute("INSERT INTO trial VALUES('other','SOL',?,1440)", (
                f"f5:{self.batch}:macd:1d:medium",
            ))
            db.execute("INSERT INTO call VALUES('other',?,?,?,?,NULL,0)", (
                BASE - 86400, BASE - 86400 + 64, BASE - 86400 + 120, BASE + 120,
            ))
        self.assertEqual(self.project()["message"], LATE)

    def test_missing_source_is_read_only_and_keeps_owner_warning(self):
        self.native.unlink()
        result = self.project()
        self.assertEqual(result["message"], LATE)
        self.assertFalse(self.native.exists())

    def test_locked_native_store_preserves_warning_without_blocking_status(self):
        with closing(sqlite3.connect(self.native)) as held:
            held.execute("BEGIN EXCLUSIVE")
            started = time.monotonic()
            result = self.project()
            elapsed = time.monotonic() - started
            self.assertEqual(result["message"], LATE)
            self.assertNotIn("timing", result)
            self.assertLess(elapsed, 1)

    def test_selected_experiment_controls_the_status_and_evidence_home(self):
        with (
            patch.object(self.plane, "experiment_home", return_value=self.home) as resolve,
            patch.object(control.runner, "status", return_value=self.state) as status,
            patch.object(control.time, "time", return_value=self.now),
        ):
            result = self.plane.pipeline_status("selected-experiment")
        resolve.assert_called_once_with("selected-experiment")
        status.assert_called_once_with(self.home)
        self.assertEqual(result["batch"]["forward_checks"][0]["timing"]["source_path"], str(self.native))


if __name__ == "__main__":
    unittest.main()
