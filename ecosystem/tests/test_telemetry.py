from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from ecosystem.telemetry import report, sanitize, sync


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "ecosystem"
        self.manager = self.root / "manager"
        self.manager.mkdir()
        self.bot = str(uuid4())
        self.manager_db = self.manager / "manager.sqlite3"
        with closing(sqlite3.connect(self.manager_db)) as db, db:
            db.execute(
                "CREATE TABLE events(sequence INTEGER PRIMARY KEY,event_id TEXT,bot_id TEXT,body TEXT)"
            )
            db.execute("PRAGMA user_version=1")
        self.runtime_db = self.manager / "runtime.sqlite3"
        with closing(sqlite3.connect(self.runtime_db)) as db, db:
            db.execute(
                "CREATE TABLE events(sequence INTEGER PRIMARY KEY,bot_id TEXT,generation INTEGER,kind TEXT,cursor INTEGER,at REAL)"
            )
            db.execute("PRAGMA user_version=2")

    def event(self, sequence, *, source="runtime", kind="tick.committed", extra=None):
        if source == "runtime":
            with closing(sqlite3.connect(self.runtime_db)) as db, db:
                db.execute(
                    "INSERT INTO events VALUES(?,?,?,?,?,?)",
                    (sequence, self.bot, 1, kind, sequence * 10, 1000.0 + sequence),
                )
        else:
            body = {
                "schema_version": 1,
                "event_id": str(uuid4()),
                "bot_id": self.bot,
                "event_type": kind,
                "occurred_at": "2026-11-10T02:00:00+00:00",
                **(extra or {}),
            }
            with closing(sqlite3.connect(self.manager_db)) as db, db:
                db.execute(
                    "INSERT INTO events VALUES(?,?,?,?)",
                    (sequence, body["event_id"], self.bot, json.dumps(body)),
                )

    def test_bounded_incremental_mirror_cursor_is_idempotent_and_paginated(self):
        for sequence in range(1, 6):
            self.event(sequence)
        with patch("ecosystem.telemetry.SOURCE_PAGE", 2):
            first = sync(self.home, self.manager)
            self.assertTrue(first["has_more"])
            self.assertEqual(first["sources"]["manager_runtime"]["cursor"], 2)
            self.assertEqual(sync(self.home, self.manager)["events_added"], 2)
            self.assertEqual(sync(self.home, self.manager)["events_added"], 1)
            self.assertEqual(sync(self.home, self.manager)["events_added"], 0)
        page = report(self.home, self.manager, limit=2)
        self.assertEqual([row["source_sequence"] for row in page["events"]], [1, 2])
        self.assertTrue(page["has_more"])
        page2 = report(self.home, self.manager, after=page["next_after"], limit=2)
        self.assertEqual([row["source_sequence"] for row in page2["events"]], [3, 4])
        self.assertEqual(page2["next_after"], 4)

    def test_filtered_events_advance_cursor_without_exposing_freeform_secrets(self):
        self.event(1, kind="API_KEY=sk-secret-literal")
        self.event(2)
        self.event(
            1,
            source="spec",
            kind="spec.created",
            extra={
                "api_key": "sk-private-key-value",
                "password": "hunter2",
                "wallet_private_key": "wallet-secret",
                "nested": {"authorization": "Bearer token-value"},
                "message": "password=hunter2",
            },
        )
        result = sync(self.home, self.manager)
        self.assertEqual(result["filtered_events"], 1)
        self.assertEqual(result["sources"]["manager_runtime"]["cursor"], 2)
        text = json.dumps(report(self.home, self.manager))
        for secret in (
            "sk-secret-literal",
            "sk-private-key-value",
            "hunter2",
            "wallet-secret",
            "token-value",
        ):
            self.assertNotIn(secret, text)
        self.assertIn("event.filtered", text)
        self.assertEqual(result["events_added"], 3)

    def test_recursive_redaction_omits_human_log_strings(self):
        private = {
            "api_key": "literal-key",
            "nested": [
                {"walletPrivateKey": "raw-wallet", "password": "secret-password"}
            ],
            "message": "Authorization: Bearer human-token password=do-not-show",
        }
        text = json.dumps(sanitize(private))
        for secret in (
            "literal-key",
            "raw-wallet",
            "secret-password",
            "human-token",
            "do-not-show",
        ):
            self.assertNotIn(secret, text)
        self.assertIn("REDACTED", text)
        self.assertIn("OMITTED_TEXT", text)

    def test_source_journals_unchanged_and_mirror_is_append_only(self):
        self.event(1)
        before = hashlib.sha256(self.runtime_db.read_bytes()).hexdigest()
        sync(self.home, self.manager)
        self.assertEqual(
            hashlib.sha256(self.runtime_db.read_bytes()).hexdigest(), before
        )
        with (
            closing(sqlite3.connect(self.home / "telemetry.sqlite3")) as db,
            self.assertRaises(sqlite3.IntegrityError),
        ):
            db.execute("DELETE FROM events")

    def test_missing_sources_differ_from_available_no_events(self):
        empty = sync(self.home, self.manager)
        self.assertEqual(empty["sources"]["manager_runtime"]["reason"], "no_events")
        missing_home = self.root / "absent-manager"
        unavailable = sync(self.root / "other-ecosystem", missing_home)
        self.assertEqual(
            unavailable["sources"]["manager_runtime"]["reason"],
            "source_journal_missing",
        )
        self.assertFalse(missing_home.exists())
        missing = report(self.root / "never-created", missing_home)
        self.assertEqual(missing["status"], "unavailable")
        self.assertEqual(missing["manager"]["reason"], "manager_not_initialized")
        self.assertFalse((self.root / "never-created").exists())

    def test_source_replacement_does_not_reset_cursor_or_hide_loss(self):
        self.event(1)
        sync(self.home, self.manager)
        with closing(sqlite3.connect(self.runtime_db)) as db, db:
            db.execute("UPDATE events SET at=99 WHERE sequence=1")
        self.event(2)
        result = sync(self.home, self.manager)
        self.assertEqual(
            result["sources"]["manager_runtime"]["reason"], "source_journal_replaced"
        )
        self.assertEqual(result["sources"]["manager_runtime"]["cursor"], 1)
        self.assertEqual(result["events_added"], 0)

    def test_regressed_source_sequence_is_unavailable_without_resetting_cursor(self):
        self.event(1)
        self.event(2)
        sync(self.home, self.manager)
        with closing(sqlite3.connect(self.runtime_db)) as db, db:
            db.execute("DELETE FROM events WHERE sequence=2")
        result = sync(self.home, self.manager)
        source = result["sources"]["manager_runtime"]
        self.assertEqual(source["reason"], "source_sequence_regressed")
        self.assertEqual(source["cursor"], 2)
        self.assertEqual(result["events_added"], 0)

    def test_report_revalidates_mirror_rows_and_metadata_before_publishing(self):
        self.event(1)
        sync(self.home, self.manager)
        secret = "api_key=forged-mirror-secret password=private-wallet"
        with closing(sqlite3.connect(self.home / "telemetry.sqlite3")) as db, db:
            body = {
                "kind": "tick.committed",
                "bot_id": self.bot,
                "occurred_at": 1002.0,
                "filtered": False,
                "password": secret,
                "message": secret,
            }
            db.execute(
                "INSERT INTO events(source,source_sequence,body) VALUES(?,?,?)",
                (secret, 2, json.dumps(body)),
            )
            db.execute(
                "UPDATE meta SET body=? WHERE key='sources'",
                (
                    json.dumps(
                        {
                            "manager_runtime": {
                                "status": "available",
                                "reason": secret,
                                "message": secret,
                            }
                        }
                    ),
                ),
            )
        observed = report(self.home, self.manager)
        self.assertEqual(observed["events"][-1]["kind"], "event.filtered")
        self.assertEqual(observed["events"][-1]["source"], "unknown")
        self.assertNotIn(secret, json.dumps(observed))

    def test_default_home_comes_from_owner_api_and_foreign_binding_refuses(self):
        self.event(1)
        with patch("botmanager.store.data_home", return_value=self.manager):
            self.assertEqual(sync(self.home)["events_added"], 1)
        other = self.root / "other-manager"
        self.assertEqual(sync(self.home, other)["status"], "unavailable")
        self.assertEqual(report(self.home, other)["status"], "unavailable")

    def test_logs_publish_only_scoped_bounded_metadata(self):
        log = self.manager / "supervisor.log"
        secret = "api_key=sk-log-secret password=hunter2 wallet_private_key=wallet-key"
        log.write_text("x" * 70000 + secret)
        definition = self.root / "service.plist"
        import plistlib

        definition.write_bytes(plistlib.dumps({"StandardOutPath": str(log)}))
        state = {"definition_present": True, "plist_path": str(definition)}
        with patch("botmanager.service.service", return_value=state):
            result = report(self.home, self.manager)
        self.assertEqual(result["logs"]["status"], "available")
        self.assertLessEqual(result["logs"]["files"][0]["tail_bytes"], 65536)
        self.assertFalse(result["logs"]["raw_content_mirrored"])
        self.assertNotIn(secret, json.dumps(result))
        self.assertIn("OMITTED_PRIVATE_LOG_TEXT", json.dumps(result))

    def test_manager_status_uses_owner_api_and_preserves_unknown_financials(self):
        from botmanager.registry import dispatch

        owner = {
            "ok": True,
            "data": {
                "initialized": True,
                "bots": [
                    {
                        "bot_id": self.bot,
                        "strategy_id": "grid",
                        "mode": "paper",
                        "armed": False,
                        "lifecycle": "draft",
                        "observed_state": "not_running",
                        "financials": {
                            "realized_net_pnl_usd": {"value": -3.5, "reason": None}
                        },
                        "api_key": "secret-status",
                        "configured_virtual_capital": {"value": 1000.0},
                    }
                ],
            },
        }
        with patch("botmanager.registry.dispatch", return_value=owner) as observed:
            result = report(self.home, self.manager)
        observed.assert_called_once()
        self.assertEqual(observed.call_args.args[0], "status")
        self.assertIsNotNone(dispatch)
        bot = result["manager"]["bots"][0]
        self.assertEqual(bot["financials"]["realized_net_pnl_usd"]["value"], -3.5)
        self.assertIsNone(bot["financials"]["unrealized_net_pnl_usd"]["value"])
        self.assertFalse(bot["configured_virtual_capital"]["reserved"])
        self.assertNotIn("secret-status", json.dumps(result))

    def test_invalid_page_limits_refuse(self):
        with self.assertRaises(ValueError):
            report(self.home, self.manager, after=-1)
        with self.assertRaises(ValueError):
            report(self.home, self.manager, limit=1001)


if __name__ == "__main__":
    unittest.main()
