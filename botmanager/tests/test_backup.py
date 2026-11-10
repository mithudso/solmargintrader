from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from botmanager.backup import create_backup, restore_backup
from botmanager.domain import ManagerError
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore

from tests.test_paper import recording


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "manager"
        self.context = CommandContext(home=self.home)
        result = dispatch(
            "create",
            {"strategy": "grid", "name": "backup", "set": ["rungs=8"]},
            self.context,
        )
        self.assertTrue(result["ok"], result)
        self.bot = result["data"]["bot_id"]
        descriptor = self.root / "input.json"
        descriptor.write_text(json.dumps(recording(self.root)))
        result = dispatch(
            "register-input",
            {"identity": self.bot, "descriptor": str(descriptor)},
            self.context,
        )
        self.assertTrue(result["ok"], result)
        self.backup = self.root / "snapshot"
        self.restored = self.root / "restored"

    def test_sqlite_restore_retains_identity_and_starts_nothing(self):
        result = create_backup(self.home, self.backup)
        original = RuntimeLedger(self.home).get(self.bot)
        restored = restore_backup(self.backup, self.restored)
        self.assertFalse(restored["starts_workers"])
        self.assertEqual(original, RuntimeLedger(self.restored).get(self.bot))
        self.assertEqual(
            ManagerStore(self.home).get_spec(self.bot),
            ManagerStore(self.restored).get_spec(self.bot),
        )
        self.assertEqual(
            result["manifest"]["databases"]["runtime.sqlite3"]["cutoff"]["tables"][
                "runs"
            ]["rows"],
            1,
        )
        self.assertFalse((self.restored / "supervisor.lock").exists())
        self.assertFalse((self.restored / "experiments.sqlite3").exists())

    def test_corruption_refuses_before_creating_home(self):
        create_backup(self.home, self.backup)
        with (self.backup / "runtime.sqlite3").open("ab") as stream:
            stream.write(b"corrupt")
        with self.assertRaises(ManagerError):
            restore_backup(self.backup, self.restored)
        self.assertFalse(self.restored.exists())

    def test_missing_input_dependency_refuses(self):
        result = create_backup(self.home, self.backup)
        Path(result["manifest"]["dependencies"][0]).unlink()
        with self.assertRaises(ManagerError):
            restore_backup(self.backup, self.restored)
        self.assertFalse(self.restored.exists())

    def test_running_or_unresolved_owner_refuses(self):
        ledger = RuntimeLedger(self.home)
        with ledger.connection(True) as db:
            db.execute("UPDATE runs SET desired='running'")
        with self.assertRaises(ManagerError):
            create_backup(self.home, self.backup)
        self.assertFalse(self.backup.exists())

    def test_restore_never_overwrites_home(self):
        create_backup(self.home, self.backup)
        with self.assertRaises(ManagerError):
            restore_backup(self.backup, self.home)

    def authority(self):
        authority = self.root / "canonical"
        authority.mkdir()
        config_root = self.root / "owner-config"
        config_root.mkdir()
        identifier = str(uuid4())
        binding = {"version": 2, "id": identifier, "root": str(authority)}
        (config_root / "research-authority.json").write_text(json.dumps(binding))
        registry = self.root / "registry.json"
        registry.write_text(
            json.dumps(
                {
                    **binding,
                    "namespace_id": "test-namespace",
                    "config_roots": [str(config_root)],
                }
            )
        )
        dbpath = authority / "experiments.sqlite3"
        with closing(sqlite3.connect(dbpath)) as db, db:
            for table in ("holdouts", "exposures"):
                db.execute(
                    f"CREATE TABLE {table} (bot TEXT, coin TEXT, start REAL, end REAL, run_id TEXT)"
                )
                db.execute(
                    f"INSERT INTO {table} VALUES ('bot','SOL',10,20,'spent-run')"
                )
        descriptor = {
            "version": 2,
            "interpreter": sys.executable,
            "repository": str(self.root),
            "config_root": str(config_root),
            "authority": {
                "id": identifier,
                "root": str(authority),
                "known_clients": [],
                "inventory_complete": True,
            },
            "expected_identity": {"version": "fixture"},
        }
        (self.home / "research-owner.json").write_text(json.dumps(descriptor))
        return registry, dbpath, descriptor

    def test_restore_preserves_research_authority(self):
        registry, dbpath, descriptor = self.authority()
        described = {
            "identity": descriptor["expected_identity"],
            "canonical_authority": {
                "id": descriptor["authority"]["id"],
                "root": descriptor["authority"]["root"],
            },
        }
        with (
            patch.dict(os.environ, {"SOLTUI_RESEARCH_REGISTRY": str(registry)}),
            patch("botmanager.research_owner.OwnerClient.call", return_value=described),
        ):
            create_backup(self.home, self.backup)
            before = dbpath.read_bytes()
            restore_backup(self.backup, self.restored)
            self.assertEqual(before, dbpath.read_bytes())
            self.assertEqual(
                json.loads((self.restored / "research-owner.json").read_text()),
                descriptor,
            )
            self.assertFalse((self.restored / "canonical").exists())
            with closing(sqlite3.connect(dbpath)) as db, db:
                db.execute("DELETE FROM exposures")
            with self.assertRaises(ManagerError):
                restore_backup(self.backup, self.root / "rollback-restore")

    def test_missing_research_dependency_and_changed_owner_refuse(self):
        registry, dbpath, descriptor = self.authority()
        described = {
            "identity": descriptor["expected_identity"],
            "canonical_authority": {
                "id": descriptor["authority"]["id"],
                "root": descriptor["authority"]["root"],
            },
        }
        with (
            patch.dict(os.environ, {"SOLTUI_RESEARCH_REGISTRY": str(registry)}),
            patch("botmanager.research_owner.OwnerClient.call", return_value=described),
        ):
            create_backup(self.home, self.backup)
            dbpath.unlink()
            with self.assertRaises(ManagerError):
                restore_backup(self.backup, self.restored)
        self.assertFalse(self.restored.exists())

    def test_unresolved_delegated_controls_refuse(self):
        for outcome in ("pending", "unknown"):
            path = self.home / "controls.sqlite3"
            if path.exists():
                path.unlink()
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE requests (body TEXT)")
                db.execute("PRAGMA user_version=2")
                db.execute(
                    "INSERT INTO requests VALUES (?)",
                    (json.dumps({"outcome": outcome}),),
                )
            with self.assertRaises(ManagerError):
                create_backup(self.home, self.backup)
            self.assertFalse(self.backup.exists())

    def test_control_journal_is_included_and_browser_unknown_refuses(self):
        path = self.home / "controls.sqlite3"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE requests (body TEXT)")
            db.execute("PRAGMA user_version=2")
        result = create_backup(self.home, self.backup)
        self.assertIn("controls.sqlite3", result["manifest"]["databases"])
        restore_backup(self.backup, self.restored)
        self.assertTrue((self.restored / "controls.sqlite3").is_file())
        with closing(sqlite3.connect(self.home / "browser.sqlite3")) as db, db:
            db.execute("CREATE TABLE fixture (id INTEGER)")
        with self.assertRaises(ManagerError):
            create_backup(self.home, self.root / "browser-snapshot")

    def test_owner_identity_change_refuses_restore(self):
        registry, _, descriptor = self.authority()
        described = {
            "identity": descriptor["expected_identity"],
            "canonical_authority": {
                "id": descriptor["authority"]["id"],
                "root": descriptor["authority"]["root"],
            },
        }
        with (
            patch.dict(os.environ, {"SOLTUI_RESEARCH_REGISTRY": str(registry)}),
            patch(
                "botmanager.research_owner.OwnerClient.call", return_value=described
            ) as owner,
        ):
            create_backup(self.home, self.backup)
            owner.return_value = {**described, "identity": {"version": "changed"}}
            with self.assertRaises(ManagerError):
                restore_backup(self.backup, self.restored)
        self.assertFalse(self.restored.exists())

    def test_backup_includes_plan_but_not_logs_or_secrets(self):
        plan = self.home / ("research-plan-" + self.bot + ".json")
        plan.write_text(json.dumps({"version": 1, "bound_bot": self.bot}))
        (self.home / "diagnostics.log").write_text("diagnostic")
        (self.home / "credentials.secret").write_text("private-fixture")
        create_backup(self.home, self.backup)
        self.assertTrue((self.backup / plan.name).is_file())
        self.assertFalse((self.backup / "diagnostics.log").exists())
        self.assertFalse((self.backup / "credentials.secret").exists())
