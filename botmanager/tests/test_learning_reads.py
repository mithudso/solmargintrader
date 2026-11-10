"""Resource and corruption boundaries for inert shared learning pointers."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from botmanager.learning import learning_snapshot


class LearningReadBudgetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.path = self.home / "manager.sqlite3"
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "CREATE TABLE learning_links(proposal_id TEXT PRIMARY KEY,bot_id TEXT,body TEXT)"
            )

    def insert(self, bodies):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany(
                "INSERT INTO learning_links VALUES (?, 'bot', ?)",
                [(str(i), body) for i, body in enumerate(bodies)],
            )

    def test_valid_pointer_state_survives_and_unknown_fields_are_not_exported(self):
        self.insert(
            [
                json.dumps(
                    {
                        "bot_id": "bot",
                        "state": "proposed",
                        "proposal_id": "proposal",
                        "payload": "private",
                    }
                )
            ]
        )
        result = learning_snapshot(self.home, "bot")
        self.assertEqual(result["state"], "proposed")
        self.assertEqual(result["proposals"][0]["proposal_id"], "proposal")
        self.assertNotIn("payload", result["proposals"][0])

    def test_invalid_pointer_shapes_are_unavailable(self):
        for body in (
            "[]",
            "{}",
            '{"bot_id":"bot","state":null}',
            "{broken",
            "[" * 2000,
        ):
            with self.subTest(body=body[:30]):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("DELETE FROM learning_links")
                self.insert([body])
                result = learning_snapshot(self.home, "bot")
                self.assertEqual(result["state"], "unavailable")
                self.assertEqual(result["proposals"], [])

    def test_per_record_and_aggregate_budgets(self):
        for bodies in (
            [
                json.dumps(
                    {"bot_id": "bot", "state": "proposed", "payload": "X" * 17000}
                )
            ],
            [json.dumps({"bot_id": "bot", "state": "proposed", "payload": "X" * 15000})]
            * 20,
        ):
            with self.subTest(count=len(bodies)):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("DELETE FROM learning_links")
                self.insert(bodies)
                result = learning_snapshot(self.home, "bot")
                self.assertEqual(result["state"], "unavailable")
                self.assertEqual(result["proposals"], [])

    def test_unindexed_unrelated_proposal_scan_has_work_budget(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany(
                "INSERT INTO learning_links VALUES (?, 'unrelated', '{}')",
                [(str(i),) for i in range(50000)],
            )
        result = learning_snapshot(self.home, "bot")
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["proposals"], [])

    def test_valid_adoption_state_is_retained(self):
        with closing(sqlite3.connect(self.home / "runtime.sqlite3")) as db, db:
            db.execute(
                "CREATE TABLE learning_adoptions(request_id TEXT PRIMARY KEY,owner_digest TEXT,body TEXT)"
            )
            db.execute(
                "INSERT INTO learning_adoptions VALUES ('request','digest',?)",
                (
                    json.dumps(
                        {
                            "bot_id": "bot",
                            "state": "published",
                            "request_id": "request",
                            "accepted_revision": 2,
                            "account_preserved": True,
                        }
                    ),
                ),
            )
        result = learning_snapshot(self.home, "bot")
        self.assertEqual(result["state"], "published")
        self.assertTrue(result["adoptions"][0]["account_preserved"])

    def test_schedule_remains_separately_byte_bounded(self):
        (self.home / "learning-job.json").write_text('"' + "X" * 65536 + '"')
        result = learning_snapshot(self.home, "bot")
        self.assertEqual(result["schedule"]["state"], "unavailable")
        self.assertLess(len(json.dumps(result)), 1024)
