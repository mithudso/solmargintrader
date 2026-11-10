from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
