"""Opening inspection surfaces must not create or recover a trading owner."""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import autotrade


class Inspection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp", prefix="auto-inspect-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "state"
        self.env = patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": str(self.home)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_absent_status_does_not_create_storage_or_spawn(self):
        with (
            patch.object(
                autotrade,
                "_connect",
                side_effect=AssertionError("read initialized journal"),
            ),
            patch("subprocess.Popen", side_effect=AssertionError("read spawned owner")),
        ):
            result = autotrade.status()
        self.assertEqual(result["state"], "unavailable")
        self.assertIn("unknown", result["reason"].lower())
        self.assertEqual(result["defaults"]["base_collateral_usd"], 10.0)
        self.assertFalse(self.home.exists())

    def test_missing_owner_does_not_recover_or_rewrite_a_persisted_session(self):
        self.home.mkdir(mode=0o700)
        journal = self.home / "journal.sqlite3"
        with sqlite3.connect(journal) as db:
            db.execute(
                "CREATE TABLE session (singleton INTEGER PRIMARY KEY, value TEXT)"
            )
            db.execute(
                "INSERT INTO session VALUES (1, ?)",
                (json.dumps({"state": "running", "session_id": "retained"}),),
            )
        journal.chmod(0o600)
        before = journal.read_bytes()
        with patch(
            "subprocess.Popen", side_effect=AssertionError("inspection recovered owner")
        ):
            result = autotrade.status()
        self.assertEqual(result["state"], "unavailable")
        self.assertIsNone(
            result["position"], "absence of an owner cannot establish exposure"
        )
        self.assertEqual(journal.read_bytes(), before)
        self.assertEqual(
            sorted(p.name for p in self.home.iterdir()), ["journal.sqlite3"]
        )

    def test_existing_owner_is_queried_without_initializing_a_journal(self):
        self.home.mkdir(mode=0o700)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(str(self.home / "owner.sock"))
        listener.listen(1)
        expected = {
            "state": "blocked",
            "session_id": "retained",
            "reason": "continuity unknown",
        }
        seen = []

        def respond():
            with listener.accept()[0] as client:
                seen.append(json.loads(client.recv(4096)))
                client.sendall(
                    json.dumps({"ok": True, "result": expected}).encode() + b"\n"
                )

        worker = threading.Thread(target=respond, daemon=True)
        worker.start()
        with (
            patch.object(
                autotrade,
                "_connect",
                side_effect=AssertionError("read initialized journal"),
            ),
            patch("subprocess.Popen", side_effect=AssertionError("read spawned owner")),
        ):
            result = autotrade.status()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result, expected)
        self.assertEqual(seen[0]["action"], "status")
        self.assertFalse((self.home / "journal.sqlite3").exists())

    def test_passive_forecast_does_not_bootstrap_an_absent_owner(self):
        with (
            patch.object(
                autotrade,
                "_connect",
                side_effect=AssertionError("forecast initialized journal"),
            ),
            patch(
                "subprocess.Popen", side_effect=AssertionError("forecast spawned owner")
            ),
            self.assertRaisesRegex(RuntimeError, "unavailable"),
        ):
            autotrade.ingest_forecast("retained-request", {"forecast_id": "fixture"})
        self.assertFalse(self.home.exists())

    def test_saved_choices_survive_inspection_without_recovering_or_exposing_private_state(
        self,
    ):
        self.home.mkdir(mode=0o700)
        journal = self.home / "journal.sqlite3"
        configuration = {
            "mode": "paper",
            "asset": "ZEC",
            "venue": "jupiter-sdk-1000x",
            "base_collateral_usd": 12,
            "max_collateral_usd": 18,
            "max_session_loss_usd": 60,
            "advice_enabled": False,
        }
        saved = {
            "state": "running",
            "session_id": "retained",
            "configuration": configuration,
            "position": {
                "state": "open",
                "plan": {"direction": "short", "weights": [123]},
            },
            "learner": {"samples": 4, "weights": [123]},
            "private_unknown_field": "not public",
        }
        with sqlite3.connect(journal) as db:
            db.execute(
                "CREATE TABLE session (singleton INTEGER PRIMARY KEY, value TEXT)"
            )
            db.execute("INSERT INTO session VALUES (1, ?)", (json.dumps(saved),))
        journal.chmod(0o600)
        before = journal.read_bytes()
        with patch(
            "subprocess.Popen", side_effect=AssertionError("inspection recovered owner")
        ):
            result = autotrade.status()
        self.assertEqual(result["configuration"], configuration)
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["last_known_state"], "running")
        self.assertEqual(result["position"]["state"], "unknown")
        self.assertNotIn("weights", json.dumps(result))
        self.assertNotIn("private_unknown_field", result)
        self.assertEqual(journal.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
