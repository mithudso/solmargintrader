from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from botmanager.config import resolve_config
from botmanager.domain import BotSpec, ManagerError
from botmanager.store import ManagerStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "new-home"
        self.store = ManagerStore(self.home)

    def spec(self, name="range-one", overrides=None):
        return BotSpec.create(
            name, "grid", resolve_config("grid", {}, overrides or {}, None)
        )

    def test_reads_do_not_create_home(self):
        self.assertEqual(self.store.list_specs(), [])
        self.assertIsNone(self.store.get_spec("missing"))
        self.assertFalse(self.home.exists())

    def test_persists_snapshot_and_atomic_initial_event(self):
        spec = self.store.create_spec(self.spec(overrides={"range_pct": 9.0}))
        self.assertEqual(
            ManagerStore(self.home).get_spec(spec.bot_id).to_dict(), spec.to_dict()
        )
        self.assertEqual(self.store.get_spec("RANGE-ONE").config_hash, spec.config_hash)
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0], 1)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(self.store.backup_descriptor()["schema_version"], 1)

    def test_identity_and_name_uniqueness_leave_no_orphan_events(self):
        first = self.store.create_spec(self.spec())
        for spec in (self.spec("RANGE-ONE"), first):
            with self.assertRaises(ManagerError):
                self.store.create_spec(spec)
        self.assertEqual(len(self.store.list_specs()), 1)
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0], 1)

    def test_initial_event_failure_rolls_back_spec(self):
        self.store.create_spec(self.spec())
        with sqlite3.connect(self.store.path) as db:
            db.execute(
                "CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'fixture'); END"
            )
        with self.assertRaises(ManagerError):
            self.store.create_spec(self.spec("range-two"))
        self.assertEqual(len(self.store.list_specs()), 1)

    def test_event_validation_and_duplicate_event(self):
        spec = self.store.create_spec(self.spec())
        event = {"event_id": "req-1", "bot_id": spec.bot_id, "event_type": "inspected"}
        self.store.append_event(event)
        with self.assertRaises(ManagerError):
            self.store.append_event(event)
        with self.assertRaises(ManagerError):
            self.store.append_event(
                dict(event, event_id="req-2", api_key="canary-secret")
            )
        with self.assertRaises(ManagerError):
            self.store.append_event(dict(event, event_id="req-3", bot_id="missing"))
        self.assertNotIn(
            "canary-secret", self.store.path.read_bytes().decode(errors="replace")
        )

    def test_future_schema_and_tampered_snapshot_fail_closed(self):
        spec = self.store.create_spec(self.spec())
        with sqlite3.connect(self.store.path) as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaises(ManagerError):
            self.store.list_specs()
        with sqlite3.connect(self.store.path) as db:
            db.execute("PRAGMA user_version=1")
            raw = spec.to_dict()
            raw["resolved_values"]["range_pct"] = 80
            db.execute("UPDATE specs SET body=?", (json.dumps(raw),))
        with self.assertRaises(ManagerError):
            self.store.get_spec(spec.bot_id)

    def test_existing_reads_leave_all_files_unchanged(self):
        spec = self.store.create_spec(self.spec())
        before = {
            path.name: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.home.iterdir()
        }
        self.store.list_specs()
        self.store.get_spec(spec.bot_id)
        self.store.backup_descriptor()
        after = {
            path.name: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.home.iterdir()
        }
        self.assertEqual(before, after)
