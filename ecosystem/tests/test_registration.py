from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem.registration import read_registrations, sync_registrations

BATCH = "a" * 32


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "ecosystem"
        self.batch_root = self.root / "batches"
        self.directory = self.batch_root / BATCH
        self.directory.mkdir(parents=True)
        self.path = self.directory / "batch.sqlite3"
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript("""
              CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
              CREATE TABLE cell(id INTEGER PRIMARY KEY,asset TEXT,interval TEXT,strategy TEXT,horizon TEXT,state TEXT,selected TEXT,score REAL);
            """)
            db.executemany(
                "INSERT INTO meta VALUES(?,?)",
                [("id", json.dumps(BATCH)), ("code_id", json.dumps("b" * 64))],
            )
            db.execute(
                "INSERT INTO cell VALUES(1,'SOL','1m','rsi','short','pending',NULL,NULL)"
            )
            db.execute(
                "INSERT INTO cell VALUES(2,'BTC','5m','lev_high','medium','unsupported',NULL,NULL)"
            )

    def sync(self):
        return sync_registrations(self.home, BATCH, self.batch_root)

    def _select(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE cell SET state='completed',selected=?,score=.2 WHERE id=1",
                (json.dumps({"name": "rsi", "params": {"period": 14}}),),
            )

    def _forward(self, *, calls=True, issued=1000):
        with closing(sqlite3.connect(self.directory / "forward.sqlite3")) as db, db:
            db.executescript(
                "CREATE TABLE trial(id TEXT PRIMARY KEY,asset TEXT,label TEXT,minutes INTEGER); CREATE TABLE call(trial TEXT,bar INTEGER,issued REAL,finish INTEGER,outcome INTEGER,prediction INTEGER);"
            )
            db.execute(
                "INSERT INTO trial VALUES('trial','SOL',?,1)",
                (f"f5:{BATCH}:rsi:1m:short",),
            )
            if calls:
                db.execute(
                    "INSERT INTO call VALUES('trial',1,?,1060,NULL,1)", (issued,)
                )

    def test_idempotent_registration_preserves_identity(self):
        first = self.sync()
        bots = read_registrations(self.home)["bots"]
        identities = {row["bot_id"] for row in bots}
        self.assertEqual(first["added"], 2)
        self.assertEqual(self.sync()["added"], 0)
        self.assertEqual(
            {row["bot_id"] for row in read_registrations(self.home)["bots"]}, identities
        )
        self.assertTrue(
            all(row["mode"] == "paper" and row["armed"] is False for row in bots)
        )
        self.assertTrue(all(row["owner"] == "soltui.f5_batch" for row in bots))

    def test_backtest_selection_does_not_fake_forward_activity(self):
        self._select()
        self.sync()
        row = next(
            row for row in read_registrations(self.home)["bots"] if row["cell_id"] == 1
        )
        self.assertEqual(row["lifecycle"], "backtest")
        self.assertEqual(row["reason"], "forward_evidence_missing")
        self.assertIsNone(row["runtime_running"])
        self.assertFalse(row["live_ready"])

    def test_trial_without_calls_is_not_forward_testing(self):
        self._select()
        self._forward(calls=False)
        self.sync()
        row = next(
            row for row in read_registrations(self.home)["bots"] if row["cell_id"] == 1
        )
        self.assertEqual(row["reason"], "forward_trial_has_no_calls")
        self.assertEqual(row["lifecycle"], "backtest")

    def test_real_call_marks_forward_stage_without_claiming_worker_liveness(self):
        self._select()
        self._forward()
        with patch("ecosystem.registration.time.time", return_value=1010):
            self.sync()
            row = next(
                row
                for row in read_registrations(self.home)["bots"]
                if row["cell_id"] == 1
            )
        self.assertEqual(row["lifecycle"], "forward")
        self.assertEqual(row["observed_state"], "forecast_recorded")
        self.assertEqual(row["forward"]["calls"], 1)
        self.assertEqual(row["forward"]["resolved"], 0)
        self.assertIsNone(row["forward"]["accuracy_percent"])
        self.assertIsNone(row["runtime_running"])
        self.assertFalse(row["automatic_promotion"])

    def test_missing_and_unsupported_evidence_remain_blocked(self):
        self.sync()
        row = next(
            row for row in read_registrations(self.home)["bots"] if row["cell_id"] == 2
        )
        self.assertEqual(row["observed_state"], "blocked")
        self.assertEqual(row["reason"], "backtest_unsupported")

    def test_mutated_frozen_identity_refuses_transaction(self):
        self.sync()
        before = read_registrations(self.home)["bots"]
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE cell SET asset='ETH' WHERE id=1")
        with self.assertRaisesRegex(ValueError, "identity_conflict"):
            self.sync()
        after = read_registrations(self.home)["bots"]
        for row in before + after:
            row.pop("observation_age_seconds")
        self.assertEqual(after, before)

    def test_missing_store_read_is_inert_and_pages_are_bounded(self):
        self.assertEqual(read_registrations(self.home)["status"], "unavailable")
        self.assertFalse(self.home.exists())
        self.sync()
        page = read_registrations(self.home, limit=1)
        next_page = read_registrations(self.home, limit=1, after=page["next_after"])
        self.assertNotEqual(page["bots"][0]["bot_id"], next_page["bots"][0]["bot_id"])
        self.assertIsNone(next_page["next_after"])
        with self.assertRaises(ValueError):
            read_registrations(self.home, limit=1001)

    def test_missing_batch_does_not_initialize_registration(self):
        with self.assertRaises(ValueError):
            sync_registrations(self.home, "c" * 32, self.batch_root)
        self.assertFalse(self.home.exists())

    def test_stale_and_future_call_are_not_running_or_promoted(self):
        self._select()
        self._forward(issued=2000)
        with patch("ecosystem.registration.time.time", return_value=1010):
            self.sync()
            row = next(
                row
                for row in read_registrations(self.home)["bots"]
                if row["cell_id"] == 1
            )
        self.assertEqual(row["reason"], "forward_evidence_invalid_clock")
        self.assertEqual(row["observed_state"], "blocked")
        with patch("ecosystem.registration.time.time", return_value=10000):
            self.sync()
            row = next(
                row
                for row in read_registrations(self.home)["bots"]
                if row["cell_id"] == 1
            )
        self.assertEqual(row["observed_state"], "stale_forward_evidence")
        self.assertFalse(row["live_ready"])


if __name__ == "__main__":
    unittest.main()
