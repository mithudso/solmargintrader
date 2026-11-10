from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem import votes
from oracle.engine import OracleEngine
from oracle.reader import ReadOnlyOracle
from oracle.store import canonical


class VoteSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def archive(self, *, hit=1, resolved_at=960):
        path = self.home / "oracle/SOL/history.sqlite3"
        engine = OracleEngine(path, instrument="SOL/USD", minimum_resolved=1)
        engine.ingest(
            {
                "source": "fixture",
                "venue": "fixture",
                "kind": "reference",
                "event_id": "current",
                "instrument": "SOL/USD",
                "observed_at": 1000,
                "received_at": 1000,
                "price": 100,
            },
            now=1000,
        )
        entry = engine.strategies()[0]
        with engine.store.connection() as db:
            for key, issued, expiry in (("old", 900, 960), ("current", 1000, 1060)):
                body = {
                    "id": key,
                    "strategy_id": entry["strategy_id"],
                    "version": entry["version"],
                    "parameters": entry["parameters"],
                    "policy_hash": engine.policy_hash,
                    "instrument": "SOL/USD",
                    "issued_at": issued,
                    "expires_at": expiry,
                    "direction": 1,
                }
                db.execute(
                    "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                    (
                        key,
                        entry["strategy_id"],
                        entry["version"],
                        issued,
                        expiry,
                        1,
                        100,
                        canonical(body),
                    ),
                )
            db.execute(
                "INSERT INTO resolutions VALUES(?,?,?,?,?)",
                ("old", 1 if hit else -1, hit, resolved_at, "{}"),
            )
        return path, entry["strategy_id"]

    def test_missing_archive_never_initializes_source_and_default_is_fourteen(self):
        absent = self.home / "absent"
        result = votes.report(absent, "SOL/USD", now=1000)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(result["catalog"]), 14)
        self.assertEqual(len(result["selected_ids"]), 14)
        self.assertFalse(absent.exists())

    def test_selection_is_versioned_and_cannot_overwrite_history(self):
        card = votes.catalog()[0]["strategy_id"]
        first = votes.set_voters(self.home, "SOL/USD", [card], 0)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(votes.settings(self.home, "SOL/USD")["selected_ids"], [card])
        with self.assertRaisesRegex(ValueError, "voter_revision_conflict"):
            votes.set_voters(self.home, "SOL/USD", [], 0)
        second = votes.set_voters(self.home, "SOL/USD", [], 1)
        self.assertEqual(second["revision"], 2)
        with closing(sqlite3.connect(self.home / "voters.sqlite3")) as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM selection").fetchone()[0], 2
            )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM selection")

    def test_only_selected_current_accurate_votes_contribute(self):
        path, card = self.archive()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = votes.report(self.home, "SOL/USD", [card], now=1001)
        self.assertEqual(result["signal"], "Strong Buy")
        self.assertEqual(result["balance_percent"], 100)
        self.assertEqual(result["aggregate"]["expires_at"], 1060)
        self.assertEqual(len(result["aggregate"]["included"]), 1)
        self.assertEqual(len(result["aggregate"]["excluded"]), 13)
        self.assertEqual(result["graph"]["status"], "available")
        self.assertEqual(len(result["graph"]["ticks"]), 1)
        self.assertEqual(len(result["graph"]["ticks"][0]["strategies"]), 14)
        self.assertEqual(
            result["graph"]["aggregate_semantics"],
            "signed_weighted_vote_balance_not_probability",
        )
        self.assertIn("not_probability", result["percentage_semantics"])
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(
            len(ReadOnlyOracle(path, instrument="SOL/USD").strategies()), 14
        )

    def test_empty_selection_abstains_without_changing_forecasts(self):
        path, _ = self.archive()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        result = votes.report(self.home, "SOL/USD", [], now=1001)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "no_selected_voters")
        self.assertIsNone(result["signal"])
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_stale_market_and_below_threshold_abstain(self):
        _, card = self.archive(hit=0)
        result = votes.report(self.home, "SOL/USD", [card], now=1001)
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(
            any(
                row["reason"] == "accuracy_at_or_below_threshold"
                for row in result["aggregate"]["excluded"]
            )
        )
        stale = votes.report(self.home, "SOL/USD", [card], now=1020)
        self.assertEqual(stale["reason"], "stale_market_data")
        self.assertIsNone(stale["balance_percent"])

    def test_future_resolution_is_not_voting_evidence(self):
        _, card = self.archive(resolved_at=1100)
        result = votes.report(self.home, "SOL/USD", [card], now=1001)
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(
            any(
                row["reason"] == "insufficient_evidence"
                for row in result["aggregate"]["excluded"]
            )
        )

    def test_unknown_duplicate_and_traversal_are_rejected(self):
        card = votes.catalog()[0]["strategy_id"]
        for ids in (["unknown"], [card, card], "all"):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                votes.set_voters(self.home, "SOL/USD", ids, 0)
        with self.assertRaises(ValueError):
            votes.report(self.home, "../secret")

    def test_failed_initial_revision_can_retry_without_corrupting_settings(self):
        card = votes.catalog()[0]["strategy_id"]
        with self.assertRaisesRegex(ValueError, "voter_revision_conflict"):
            votes.set_voters(self.home, "SOL/USD", [card], 9)
        self.assertEqual(votes.settings(self.home, "SOL/USD")["revision"], 0)
        self.assertEqual(
            votes.set_voters(self.home, "SOL/USD", [card], 0)["revision"], 1
        )

    def test_foreign_archive_is_unchanged_and_unavailable(self):
        path = self.home / "oracle/SOL/history.sqlite3"
        path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE secret(value)")
            db.execute("INSERT INTO secret VALUES('do not expose')")
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        result = votes.report(self.home, "SOL/USD", now=1001)
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("do not expose", json.dumps(result))
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_recorded_catalog_and_evidence_survive_current_version_drift(self):
        path, card = self.archive()
        recorded = ReadOnlyOracle(path, instrument="SOL/USD").strategies()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with patch(
            "oracle.reader.StrategySet",
            side_effect=AssertionError("no current strategy construction"),
        ):
            result = votes.report(self.home, "SOL/USD", [card], now=1001)
        self.assertEqual(result["signal"], "Strong Buy")
        self.assertTrue(result["legacy_policy"])
        self.assertEqual(result["catalog"][0]["version"], recorded[0]["version"])
        self.assertEqual(result["catalog"][0]["parameters"], recorded[0]["parameters"])
        self.assertEqual(result["catalog"][0]["metadata_source"], "recorded_policy")
        self.assertEqual(result["strategies"][0]["resolved"], 1)
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
