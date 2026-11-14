from __future__ import annotations

import gzip
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError, canonical, fingerprint
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch

from ecosystem.telemetry import report, sync
from ecosystem.tests import isolated_default_owner


def recording(root):
    path = root / "recording.jsonl.gz"
    start = 1700000040
    with gzip.open(path, "wt") as stream:
        for second in range(180):
            stream.write(
                json.dumps(
                    {
                        "t": start + second,
                        "q": {"SOL-USD": [99.9, 100.1, 100, 10, 10, start + second]},
                    }
                )
                + "\n"
            )
    return {
        "schema_version": 1,
        "installation_id": "fixture-recorder",
        "source": "coinbase_exchange_recorder",
        "paths": [str(path)],
        "product": "SOL-USD",
        "quote_currency": "USD",
        "bar_seconds": 60,
        "start_ts": start,
        "end_ts": start + 180,
        "fee_bps": 6.0,
        "slippage_bps": 2.0,
        "carry_bps_per_hour": 0.0,
        "min_order_quote": 10.0,
        "capital_quote": 1000.0,
    }


class ManagerEditingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(isolated_default_owner())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = self.root / "manager"
        self.home = self.root / "ecosystem"
        self.context = CommandContext(home=self.manager)
        self.bot = self.call("create", strategy="grid", name="fixture")["bot_id"]
        descriptor = self.root / "descriptor.json"
        descriptor.write_text(json.dumps(recording(self.root)))
        self.call("register-input", identity=self.bot, descriptor=str(descriptor))
        self.ledger = RuntimeLedger(self.manager)

    def call(self, command, **params):
        result = dispatch(command, params, self.context)
        self.assertTrue(result["ok"], result)
        return result["data"]

    def test_schemas_and_pagination_survive_two_adoptions(self):
        first = sync(self.home, self.manager)
        for source in first["sources"].values():
            self.assertEqual(source["status"], "available", first)
        initial = self.ledger.events(self.bot)
        old_id = self.ledger.get(self.bot)["runtime_id"]
        for value in (20, 22):
            self.call("edit", identity=self.bot, set=[f"range_pct={value}"])
            self.call("apply", identity=self.bot)
            with patch("ecosystem.telemetry.SOURCE_PAGE", 1):
                for _ in range(10):
                    result = sync(self.home, self.manager)
                    self.assertTrue(
                        all(
                            s["status"] == "available"
                            for s in result["sources"].values()
                        ),
                        result,
                    )
                    if not result["has_more"]:
                        break
        events = self.ledger.events(self.bot)
        self.assertEqual(len(events), len(initial) + 2)
        self.assertEqual(len({e["sequence"] for e in events}), len(events))
        self.assertEqual(events[-1]["runtime_id"], old_id)
        mirrored = report(self.home, self.manager, limit=100)["events"]
        runtime = [e for e in mirrored if e["source"] == "manager_runtime"]
        self.assertEqual(
            [e["source_sequence"] for e in runtime],
            sorted(e["sequence"] for e in events),
        )
        self.assertEqual(
            {e["runtime_id"] for e in runtime},
            {r["runtime_id"] for r in self.ledger.history(self.bot)},
        )
        self.assertIn("spec.edited", {e["kind"] for e in mirrored})
        self.assertIn("revision.applied", {e["kind"] for e in mirrored})
        self.assertEqual(sync(self.home, self.manager)["events_added"], 0)

    def test_spec_schema2_is_readable_without_source_mutation(self):
        before = (self.manager / "manager.sqlite3").read_bytes()
        result = sync(self.home, self.manager)
        self.assertEqual(result["sources"]["manager_spec"]["status"], "available")
        self.assertEqual((self.manager / "manager.sqlite3").read_bytes(), before)

    def test_existing_runtime_source_sequence_never_restarts_after_apply(self):
        self.call("start", identity=self.bot)
        self.call("stop", identity=self.bot)
        before = list(reversed(self.ledger.events(self.bot)))
        sync(self.home, self.manager)
        self.call("edit", identity=self.bot, set=["range_pct=20"])
        self.call("apply", identity=self.bot)
        after = list(reversed(self.ledger.events(self.bot)))
        self.assertEqual(after[: len(before)], before)
        self.assertGreater(after[-1]["sequence"], before[-1]["sequence"])
        mirrored = sync(self.home, self.manager)
        self.assertEqual(
            mirrored["sources"]["manager_runtime"]["status"], "available", mirrored
        )

    def schema3_with_reused_sequence(self):
        """Reproduce the previous release's delete-and-reuse event behavior."""
        start = self.call("start", identity=self.bot)
        stop = self.call("stop", identity=self.bot)
        sync(self.home, self.manager)
        self.call("edit", identity=self.bot, set=["range_pct=20"])
        self.call("apply", identity=self.bot)
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.row_factory = sqlite3.Row
            archive = db.execute("SELECT * FROM archives").fetchone()
            body = json.loads(archive["body"])
            for event in body["events"]:
                for field in ("runtime_id", "origin_sequence", "origin"):
                    event.pop(field)
            archived_body = canonical(body)
            db.execute(
                "UPDATE archives SET body=?,checksum=?",
                (archived_body, fingerprint(body)),
            )
            current = dict(
                db.execute(
                    "SELECT * FROM events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
            )
            db.execute("DELETE FROM events")
            for field in ("runtime_id", "origin_sequence", "origin"):
                db.execute(f"ALTER TABLE events DROP COLUMN {field}")
            db.execute(
                "INSERT INTO events VALUES(?,?,?,?,?,?)",
                (
                    1,
                    current["bot_id"],
                    current["generation"],
                    current["kind"],
                    current["cursor"],
                    current["at"],
                ),
            )
            # A previously unverifiable receipt must remain unverifiable.
            db.execute(
                "UPDATE requests SET acceptance=NULL WHERE request_id=?",
                (start["request_id"],),
            )
            requests = [
                tuple(row)
                for row in db.execute("SELECT * FROM requests ORDER BY request_id")
            ]
            db.execute("PRAGMA user_version=3")
        return archived_body, requests, start, stop

    def test_schema3_import_preserves_archive_requests_and_legacy_provenance(self):
        body, requests, start, stop = self.schema3_with_reused_sequence()
        before = self.ledger.path.read_bytes()
        self.ledger.history(self.bot)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        with self.ledger.connection(True):
            pass
        with closing(sqlite3.connect(self.ledger.path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 5)
            self.assertEqual(
                db.execute("SELECT body FROM archives").fetchone()[0], body
            )
            for request in requests:
                self.assertEqual(
                    db.execute(
                        "SELECT * FROM requests WHERE request_id=?", (request[0],)
                    ).fetchone(),
                    request,
                )
        events = list(reversed(self.ledger.events(self.bot)))
        self.assertEqual(events[0]["sequence"], 1)
        self.assertEqual(events[0]["origin_sequence"], 1)
        self.assertEqual(events[0]["origin"], "legacy_current")
        imported = events[1:]
        self.assertEqual([row["origin_sequence"] for row in imported], [1, 2, 3])
        self.assertTrue(
            all(
                row["sequence"] > 3 and row["origin"] == "legacy_archive"
                for row in imported
            )
        )
        self.assertEqual({row["runtime_id"] for row in imported}, {stop["runtime_id"]})
        result = dispatch(
            "start",
            {"identity": self.bot, "request_id": start["request_id"]},
            self.context,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_receipt")
        self.assertEqual(
            self.call("stop", identity=self.bot, request_id=stop["request_id"]), stop
        )
        fresh = self.root / "new-mirror"
        synced = sync(fresh, self.manager)
        self.assertEqual(synced["sources"]["manager_runtime"]["status"], "available")
        mirrored = [
            e
            for e in report(fresh, self.manager)["events"]
            if e["source"] == "manager_runtime"
        ]
        self.assertEqual(len(mirrored), 4)
        self.assertEqual(
            {e["runtime_id"] for e in mirrored}, {row["runtime_id"] for row in events}
        )
        old_count = len(events)
        self.call("edit", identity=self.bot, set=["range_pct=23"])
        self.call("apply", identity=self.bot)
        self.assertEqual(len(self.ledger.events(self.bot)), old_count + 1)
        self.assertEqual(
            sync(fresh, self.manager)["sources"]["manager_runtime"]["status"],
            "available",
        )

    def test_ambiguous_existing_mirror_cursor_is_never_reset_by_migration(self):
        self.schema3_with_reused_sequence()
        with self.ledger.connection(True):
            pass
        result = sync(self.home, self.manager)
        source = result["sources"]["manager_runtime"]
        self.assertEqual(source["status"], "unavailable")
        self.assertEqual(source["reason"], "source_journal_replaced")
        self.assertEqual(source["cursor"], 3)
        self.assertEqual(
            [
                e["source_sequence"]
                for e in report(self.home, self.manager)["events"]
                if e["source"] == "manager_runtime"
            ],
            [1, 2, 3],
        )

    def test_two_bot_stable_first_event_cannot_hide_reused_legacy_sequence(self):
        anchor = self.bot
        target = self.call("create", strategy="grid", name="target")["bot_id"]
        self.call(
            "register-input",
            identity=target,
            descriptor=str(self.root / "descriptor.json"),
        )
        self.call("start", identity=target)
        self.call("stop", identity=target)
        initial = sync(self.home, self.manager)
        self.assertEqual(initial["sources"]["manager_runtime"]["cursor"], 4)
        self.call("edit", identity=target, set=["range_pct=20"])
        self.call("apply", identity=target)
        current_runtime = self.ledger.get(target)["runtime_id"]
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.row_factory = sqlite3.Row
            archive = db.execute("SELECT * FROM archives").fetchone()
            body = json.loads(archive["body"])
            for event in body["events"]:
                for field in ("runtime_id", "origin_sequence", "origin"):
                    event.pop(field)
            db.execute(
                "UPDATE archives SET body=?,checksum=?",
                (canonical(body), fingerprint(body)),
            )
            latest = dict(
                db.execute(
                    "SELECT * FROM events WHERE bot_id=? ORDER BY sequence DESC LIMIT 1",
                    (target,),
                ).fetchone()
            )
            db.execute("DELETE FROM events WHERE bot_id=?", (target,))
            for field in ("runtime_id", "origin_sequence", "origin"):
                db.execute(f"ALTER TABLE events DROP COLUMN {field}")
            db.execute(
                "INSERT INTO events VALUES(?,?,?,?,?,?)",
                (
                    2,
                    target,
                    latest["generation"],
                    latest["kind"],
                    latest["cursor"],
                    latest["at"],
                ),
            )
            db.execute("PRAGMA user_version=3")
        anchor_event = self.ledger.events(anchor)[0]
        with self.ledger.connection(True):
            pass
        self.assertEqual(self.ledger.events(anchor)[0]["sequence"], 1)
        self.assertEqual(self.ledger.events(anchor)[0]["at"], anchor_event["at"])
        self.assertEqual(max(e["sequence"] for e in self.ledger.events(target)), 7)
        for _ in range(2):
            result = sync(self.home, self.manager)
            source = result["sources"]["manager_runtime"]
            self.assertEqual(source["status"], "unavailable", source)
            self.assertEqual(source["reason"], "source_journal_replaced")
            self.assertEqual(source["cursor"], 4)
            self.assertEqual(source["legacy_reused_sequence_count"], 1)
            self.assertRegex(source["legacy_reuse_fingerprint"], r"^[0-9a-f]{64}$")
        mirrored = [
            e
            for e in report(self.home, self.manager)["events"]
            if e["source"] == "manager_runtime"
        ]
        self.assertEqual([e["source_sequence"] for e in mirrored], [1, 2, 3, 4])
        fresh = self.root / "fresh-mirror"
        result = sync(fresh, self.manager)
        self.assertEqual(result["sources"]["manager_runtime"]["status"], "available")
        fresh_events = [
            e
            for e in report(fresh, self.manager)["events"]
            if e["source"] == "manager_runtime"
        ]
        self.assertIn(current_runtime, {e["runtime_id"] for e in fresh_events})
        self.assertEqual([e["source_sequence"] for e in fresh_events], [1, 2, 5, 6, 7])
        evidence = result["sources"]["manager_runtime"]["legacy_reuse_fingerprint"]
        self.call("start", identity=target)
        self.call("stop", identity=target)
        continued = sync(fresh, self.manager)["sources"]["manager_runtime"]
        self.assertEqual(continued["status"], "available")
        self.assertEqual(continued["legacy_reuse_fingerprint"], evidence)
        self.assertEqual(continued["cursor"], 9)
        old = sync(self.home, self.manager)["sources"]["manager_runtime"]
        self.assertEqual(old["status"], "unavailable")
        self.assertEqual(old["cursor"], 4)

    def test_corrupt_schema3_archive_does_not_block_current_stop(self):
        self.schema3_with_reused_sequence()
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.execute("UPDATE runs SET desired='running'")
            db.execute("UPDATE archives SET body='{}'")
            generation = db.execute("SELECT generation FROM runs").fetchone()[0]
        result = self.call("stop", identity=self.bot)
        self.assertEqual(result["outcome"], "pending")
        with closing(sqlite3.connect(self.ledger.path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(
                db.execute("SELECT desired,generation FROM runs").fetchone(),
                ("stopped", generation + 1),
            )
            self.assertEqual(
                db.execute("SELECT body FROM archives").fetchone()[0], "{}"
            )
        with self.assertRaises(ManagerError), self.ledger.connection(True):
            pass
        with closing(sqlite3.connect(self.ledger.path)) as db:
            self.assertEqual(
                db.execute("SELECT desired FROM runs").fetchone()[0], "stopped"
            )

    def test_schema3_marker_survives_unambiguous_upgrade_without_relabeling_mirror(
        self,
    ):
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            for field in ("runtime_id", "origin_sequence", "origin"):
                db.execute(f"ALTER TABLE events DROP COLUMN {field}")
            db.execute("PRAGMA user_version=3")
        before = self.ledger.path.read_bytes()
        initial = sync(self.home, self.manager)
        self.assertEqual(initial["sources"]["manager_runtime"]["cursor"], 1)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        original = next(
            e
            for e in report(self.home, self.manager)["events"]
            if e["source"] == "manager_runtime"
        )
        self.assertIsNone(original["runtime_id"])
        self.assertEqual(
            original["runtime_reason"], "legacy_event_runtime_not_recorded"
        )
        self.call("start", identity=self.bot)
        result = sync(self.home, self.manager)
        self.assertEqual(result["sources"]["manager_runtime"]["status"], "available")
        self.assertEqual(result["sources"]["manager_runtime"]["cursor"], 2)
        self.assertEqual(
            result["sources"]["manager_runtime"]["legacy_reused_sequence_count"], 0
        )
        self.assertIsNone(
            result["sources"]["manager_runtime"]["legacy_reuse_fingerprint"]
        )
        events = [
            e
            for e in report(self.home, self.manager)["events"]
            if e["source"] == "manager_runtime"
        ]
        self.assertEqual(events[0], original)
        self.assertEqual(
            events[1]["runtime_id"], self.ledger.get(self.bot)["runtime_id"]
        )
        self.assertEqual(events[1]["origin"], "native")


class DefaultOwnerScopeTests(unittest.TestCase):
    def test_default_endpoint_scope_restores_explicit_overrides(self):
        setting = "SOLBOT_SOLTUI_ENDPOINT"
        original = "http://127.0.0.1:1"
        explicit = "http://127.0.0.1:2"
        with patch.dict(os.environ, {setting: original}):
            with isolated_default_owner() as endpoint:
                self.assertTrue(endpoint.startswith("http://127.0.0.1:"))
                self.assertNotEqual(endpoint, original)
                self.assertNotEqual(endpoint, "http://127.0.0.1:8788")
                self.assertEqual(os.environ[setting], endpoint)
                with patch.dict(os.environ, {setting: explicit}):
                    self.assertEqual(os.environ[setting], explicit)
                self.assertEqual(os.environ[setting], endpoint)
            self.assertEqual(os.environ[setting], original)
