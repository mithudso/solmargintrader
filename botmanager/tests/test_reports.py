from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.reports import (
    compare_reports,
    event_page,
    history_page,
    render_report,
    report_page,
    run_history_page,
)
from botmanager.store import ManagerStore

from tests.test_paper import recording


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "manager"
        self.context = CommandContext(home=self.home)
        result = dispatch(
            "create",
            {"strategy": "grid", "name": "report-test", "set": ["rungs=8"]},
            self.context,
        )
        self.assertTrue(result["ok"], result)
        self.bot = result["data"]["bot_id"]
        self.store = ManagerStore(self.home)
        descriptor = self.root / "descriptor.json"
        descriptor.write_text(json.dumps(recording(self.root)))
        result = dispatch(
            "register-input",
            {"identity": self.bot, "descriptor": str(descriptor)},
            self.context,
        )
        self.assertTrue(result["ok"], result)
        self.ledger = RuntimeLedger(self.home)

    def test_report_is_attributed_and_read_does_not_write(self):
        before = {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
        page = report_page(self.store, self.bot, limit=1)
        run = self.ledger.get(self.bot)
        self.assertEqual(page["report"]["runtime_id"], run["runtime_id"])
        self.assertEqual(page["report"]["configuration"], run["spec"])
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
        )
        self.assertEqual(json.loads(render_report(page, "json")), page)
        self.assertIn("report.runtime_id", render_report(page, "csv"))
        self.assertIn(run["runtime_id"], render_report(page, "human"))

    def test_events_use_sequences_not_count_and_append_replays(self):
        with self.ledger.connection(True) as db:
            for sequence in (10, 30):
                row = db.execute(
                    "SELECT * FROM runs WHERE bot_id=?", (self.bot,)
                ).fetchone()
                db.execute(
                    "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        sequence,
                        self.bot,
                        row["generation"],
                        "test",
                        0,
                        1.0,
                        row["runtime_id"],
                        None,
                        "native",
                    ),
                )
        first = event_page(self.ledger, self.bot, after=1, limit=1)
        self.assertEqual(first["next_after"], 10)
        self.assertTrue(first["has_more"])
        self.assertEqual(first, event_page(self.ledger, self.bot, after=1, limit=1))
        with self.ledger.connection(True) as db:
            self.ledger._event(db, dict(row), "appended")
        second = event_page(self.ledger, self.bot, after=first["next_after"], limit=10)
        self.assertEqual([r["sequence"] for r in second["items"]], [30, 31])

    def test_history_is_revision_bounded(self):
        page = history_page(self.store, self.bot, limit=1)
        self.assertEqual(page["next_after"], 1)
        self.assertEqual(history_page(self.store, self.bot, after=1)["items"], [])
        self.assertEqual(
            run_history_page(self.store, self.bot)["current_runtime_id"],
            self.ledger.get(self.bot)["runtime_id"],
        )
        for name in ("history-page", "run-history", "events"):
            result = dispatch(
                name, {"identity": self.bot, "after": 0, "limit": 1}, self.context
            )
            self.assertTrue(result["ok"], result)
            self.assertIn("next_after", result["data"])

    def test_missing_home_read_does_not_initialize(self):
        missing = self.root / "absent"
        self.assertEqual(event_page(RuntimeLedger(missing), self.bot)["items"], [])
        self.assertFalse(missing.exists())

    def test_incompatible_benchmarks_are_explicit(self):
        a = report_page(self.store, self.bot)["report"]
        b = json.loads(json.dumps(a))
        b["mode"] = "live"
        b["accounting"]["currency"] = "USDC"
        a["accounting"]["currency"] = "USD"
        result = compare_reports(a, b)
        self.assertFalse(result["compatible"])
        self.assertIn("mode", result["mismatches"])
        self.assertIn("currency", result["mismatches"])

    def test_archived_run_keeps_original_configuration_after_edit(self):
        old = self.ledger.get(self.bot)
        edit = dispatch(
            "edit", {"identity": self.bot, "set": ["range_pct=20"]}, self.context
        )
        self.assertTrue(edit["ok"], edit)
        applied = dispatch("apply", {"identity": self.bot}, self.context)
        self.assertTrue(applied["ok"], applied)
        archived = report_page(self.store, self.bot, run_id=old["runtime_id"])["report"]
        self.assertTrue(archived["archived"])
        self.assertEqual(archived["configuration"], old["spec"])
        self.assertNotEqual(
            archived["configuration"]["config_hash"],
            self.store.get_spec(self.bot).config_hash,
        )
        self.assertEqual(
            run_history_page(self.store, self.bot, limit=1)["items"][0]["runtime_id"],
            old["runtime_id"],
        )

    def test_many_segments_refused_before_unbounded_decoder(self):
        from botmanager.reports import REPORT_MAX_SEGMENTS

        run = self.ledger.get(self.bot)
        with self.ledger.connection(True) as db:
            db.executemany(
                "INSERT INTO segments VALUES (?,?,?,?)",
                [
                    (run["runtime_id"], str(i), "{}", 0)
                    for i in range(REPORT_MAX_SEGMENTS + 500)
                ],
            )
        with (
            patch.object(
                RuntimeLedger,
                "_decode",
                side_effect=AssertionError("decoder must not run"),
            ),
            self.assertRaises(ManagerError) as caught,
        ):
            report_page(self.store, self.bot, limit=1)
        self.assertEqual(caught.exception.code, "report_budget_exceeded")

    def test_large_archive_refused_before_body_decode(self):
        from botmanager.reports import REPORT_MAX_BYTES

        runtime_id = "00000000-0000-4000-8000-000000000001"
        with self.ledger.connection(True) as db:
            db.execute(
                "INSERT INTO archives VALUES (?,?,?,?)",
                (runtime_id, self.bot, " " * (REPORT_MAX_BYTES + 1), "invalid"),
            )
        with (
            patch.object(
                RuntimeLedger,
                "_decode_archive",
                side_effect=AssertionError("decoder must not run"),
            ),
            self.assertRaises(ManagerError) as caught,
        ):
            report_page(self.store, self.bot, run_id=runtime_id, limit=1)
        self.assertEqual(caught.exception.code, "report_budget_exceeded")

    def test_oversized_fill_history_refused_before_decode(self):
        from botmanager.reports import REPORT_MAX_ROWS

        with self.ledger.connection(True) as db:
            db.executemany(
                "INSERT INTO fills VALUES (?,?,?)",
                [(self.bot, i, "{}") for i in range(REPORT_MAX_ROWS + 1)],
            )
        with (
            patch.object(
                RuntimeLedger,
                "_decode",
                side_effect=AssertionError("decoder must not run"),
            ),
            self.assertRaises(ManagerError) as caught,
        ):
            report_page(self.store, self.bot, limit=1)
        self.assertEqual(caught.exception.code, "report_budget_exceeded")

    def test_bounded_report_retains_integrity_validation(self):
        with self.ledger.connection(True) as db:
            db.execute("UPDATE runs SET cursor=100 WHERE bot_id=?", (self.bot,))
        with self.assertRaises(ManagerError) as caught:
            report_page(self.store, self.bot, limit=1)
        self.assertEqual(caught.exception.code, "corrupt_checkpoint")

    def test_sql_work_budget_refuses_unindexed_event_scan(self):
        run = self.ledger.get(self.bot)
        with self.ledger.connection(True) as db:
            db.executemany(
                "INSERT INTO events(bot_id,generation,kind,cursor,at,runtime_id,origin) VALUES (?,0,'test',0,1,?,'native')",
                [(self.bot, "another-runtime") for _ in range(2000)],
            )
        with (
            patch("botmanager.reports.REPORT_SQL_STEPS", 1000),
            self.assertRaises(ManagerError) as caught,
        ):
            report_page(
                self.store, self.bot, run_id=run["runtime_id"], after=1, limit=1
            )
        self.assertEqual(caught.exception.code, "report_budget_exceeded")

    def test_oversized_learning_pointer_keeps_report_and_status_bounded(self):
        with closing(sqlite3.connect(self.home / "manager.sqlite3")) as db, db:
            db.execute(
                "CREATE TABLE learning_links(proposal_id TEXT PRIMARY KEY,bot_id TEXT,body TEXT)"
            )
            db.execute(
                "INSERT INTO learning_links VALUES ('huge',?,?)",
                (
                    self.bot,
                    json.dumps(
                        {
                            "bot_id": self.bot,
                            "state": "proposed",
                            "payload": "PRIVATE_MARKER" * 700000,
                        }
                    ),
                ),
            )
        before = {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
        page = report_page(self.store, self.bot, limit=1)
        self.assertEqual(page["report"]["learning"]["state"], "unavailable")
        status = dispatch("status", {"identity": self.bot}, self.context)
        self.assertTrue(status["ok"], status)
        for projection in (page, status):
            output = json.dumps(projection)
            self.assertNotIn("PRIVATE_MARKER", output)
            self.assertLess(len(output), 65536)
            self.assertIn("local_learning_metadata_unavailable", output)
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
        )

    def test_unrelated_adoption_history_is_not_json_scanned(self):
        with self.ledger.connection(True) as db:
            db.execute(
                "CREATE TABLE learning_adoptions(request_id TEXT PRIMARY KEY,owner_digest TEXT,body TEXT)"
            )
            db.executemany(
                "INSERT INTO learning_adoptions VALUES (?, 'digest', ?)",
                [
                    (str(i), json.dumps({"bot_id": "unrelated", "state": "published"}))
                    for i in range(10000)
                ],
            )
        before = {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
        page = report_page(self.store, self.bot, limit=1)
        self.assertEqual(page["report"]["learning"]["state"], "unavailable")
        self.assertEqual(page["report"]["learning"]["adoptions"], [])
        status = dispatch("status", {"identity": self.bot}, self.context)
        self.assertTrue(status["ok"], status)
        self.assertIn("local_learning_metadata_unavailable", json.dumps(status))
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in self.home.glob("*.sqlite3")}
        )
