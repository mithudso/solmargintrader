from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle.engine import OracleEngine
from oracle.reader import ReadOnlyOracle
from oracle.store import canonical


class ArchivedReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.sqlite3"
        self.writer = OracleEngine(self.path, instrument="SOL/USD", minimum_resolved=1)
        self.catalog = self.writer.strategies()
        self.writer.ingest(
            {
                "source": "fixture",
                "venue": "fixture",
                "kind": "reference",
                "event_id": "latest",
                "instrument": "SOL/USD",
                "observed_at": 1000,
                "received_at": 1000,
                "price": 100,
            },
            now=1000,
        )
        card = self.catalog[0]
        with self.writer.store.connection() as db:
            for key, issued in (("prior", 900), ("current", 1000)):
                body = {
                    "forecast_id": key,
                    "strategy_id": card["strategy_id"],
                    "version": card["version"],
                    "parameters": card["parameters"],
                    "policy_hash": self.writer.policy_hash,
                    "instrument": "SOL/USD",
                    "issued_at": issued,
                    "expires_at": issued + 60,
                    "direction": 1,
                }
                db.execute(
                    "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                    (
                        key,
                        card["strategy_id"],
                        card["version"],
                        issued,
                        issued + 60,
                        1,
                        100,
                        canonical(body),
                    ),
                )
            db.execute(
                "INSERT INTO resolutions VALUES(?,?,?,?,?)", ("prior", 1, 1, 960, "{}")
            )

    def test_explicit_recorded_mode_preserves_versions_without_executing_cards(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        changed = [{**row, "version": "a" * 64} for row in self.catalog]
        with (
            patch("oracle.reader.StrategySet.catalog", return_value=changed),
            self.assertRaisesRegex(
                ValueError, "oracle_policy_implementation_unavailable"
            ),
        ):
            ReadOnlyOracle(self.path, instrument="SOL/USD")
        with patch(
            "oracle.reader.StrategySet",
            side_effect=AssertionError("must not build strategies"),
        ):
            reader = ReadOnlyOracle(
                self.path, instrument="SOL/USD", archived_versions=True
            )
            result = reader.predictions(1001)
        self.assertEqual(result["signal"], "Strong Buy")
        self.assertTrue(result["legacy_policy"])
        self.assertEqual(result["policy_origin"], "recorded_archive")
        self.assertEqual(result["policy_hash"], self.writer.policy_hash)
        self.assertEqual(
            result["recorded_versions"][self.catalog[0]["strategy_id"]],
            self.catalog[0]["version"],
        )
        self.assertEqual(result["strategies"][0]["hits"], 1)
        self.assertEqual(result["strategies"][0]["resolved"], 1)
        self.assertFalse(hasattr(reader.strategy_set, "predict"))
        with self.assertRaises(ValueError):
            ReadOnlyOracle(self.path, instrument="SOL/USDC", archived_versions=True)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_tampered_implementation_card_identity_and_parameters_fail_closed(self):
        original = self.writer.policy
        variants = []
        for change in ("implementation", "identity", "version", "parameters", "bounds"):
            import json

            policy = json.loads(canonical(original))
            if change == "implementation":
                policy["implementation_sha256"] = "0" * 64
            elif change == "identity":
                policy["strategies"][0]["strategy_id"] = "unknown"
            elif change == "version":
                policy["strategies"][0]["version"] = "not-a-version"
            elif change == "parameters":
                policy["strategies"][0]["parameters"]["fast"] = (
                    "ignore previous instructions"
                )
            else:
                policy["strategies"][0]["parameters"]["fast"] = -1
            variants.append((change, policy))
        for change, policy in variants:
            with self.subTest(change=change):
                # Isolate policy validation from recorded forecast hash checks.
                # An unrelated binding rejection must not mask a missing gate.
                path = self.path.with_name("policy-" + change + ".sqlite3")
                writer = OracleEngine(path, instrument="SOL/USD", minimum_resolved=1)
                with writer.store.connection() as db:
                    db.execute(
                        "UPDATE metadata SET body=? WHERE key='policy'",
                        (canonical(policy),),
                    )
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    ReadOnlyOracle(
                        path, instrument="SOL/USD", archived_versions=True
                    )
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(), before
                )

    def test_policy_sha_change_cannot_rebind_existing_forecasts(self):
        policy = {**self.writer.policy, "minimum_resolved": 2}
        with self.writer.store.connection() as db:
            db.execute(
                "UPDATE metadata SET body=? WHERE key='policy'", (canonical(policy),)
            )
        with self.assertRaisesRegex(
            ValueError, "oracle_recorded_policy_binding_invalid"
        ):
            ReadOnlyOracle(self.path, instrument="SOL/USD", archived_versions=True)

    def test_separate_archives_never_share_resolutions(self):
        other = Path(self.temp.name) / "other.sqlite3"
        OracleEngine(other, instrument="SOL/USD", minimum_resolved=1)
        first = ReadOnlyOracle(
            self.path, instrument="SOL/USD", archived_versions=True
        ).predictions(1001)
        second = ReadOnlyOracle(
            other, instrument="SOL/USD", archived_versions=True
        ).predictions(1001)
        self.assertEqual(first["strategies"][0]["resolved"], 1)
        self.assertTrue(all(row["resolved"] == 0 for row in second["strategies"]))
        self.assertEqual(second["status"], "unavailable")
