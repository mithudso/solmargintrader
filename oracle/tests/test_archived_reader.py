from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle.engine import OracleEngine
from oracle.reader import ReadOnlyOracle
from oracle.store import canonical

ARCHIVED_SCHEMA2_EVALUATOR_SHA256 = (
    "8d3311760e2d61f160b7e3877d753a7805dbfcff5f511a171d2435cccf551a98"
)


class ArchivedReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.sqlite3"
        self.writer = OracleEngine(self.path, instrument="SOL/USD", minimum_resolved=1)
        self.catalog = self.writer.strategies()
        self._seed_archive(self.writer.policy_hash, self.catalog)

    def _seed_archive(self, policy_hash, catalog):
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
        card = catalog[0]
        with self.writer.store.connection() as db:
            for key, issued in (("prior", 900), ("current", 1000)):
                body = {
                    "forecast_id": key,
                    "strategy_id": card["strategy_id"],
                    "version": card["version"],
                    "parameters": card["parameters"],
                    "policy_hash": policy_hash,
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

    def _record_schema2_archive(self):
        """Give this synthetic archive a recorded evaluator and card identities."""
        self.path = Path(self.temp.name) / "recorded-schema2.sqlite3"
        self.writer = OracleEngine(self.path, instrument="SOL/USD", minimum_resolved=1)
        policy = json.loads(canonical(self.writer.policy))
        policy["implementation_sha256"] = ARCHIVED_SCHEMA2_EVALUATOR_SHA256
        for row in policy["strategies"]:
            row["version"] = hashlib.sha256(
                f"recorded:{row['strategy_id']}".encode()
            ).hexdigest()
        policy_hash = hashlib.sha256(canonical(policy).encode()).hexdigest()
        with self.writer.store.connection() as db:
            db.execute(
                "UPDATE metadata SET body=? WHERE key='policy'", (canonical(policy),)
            )
        self._seed_archive(policy_hash, policy["strategies"])
        return policy, policy_hash

    def test_known_schema2_archive_preserves_recorded_versions_without_construction(self):
        policy, policy_hash = self._record_schema2_archive()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with (
            patch(
                "oracle.engine.OracleEngine.__init__",
                side_effect=AssertionError("must not construct an engine"),
            ),
            patch(
                "oracle.reader.StrategySet",
                side_effect=AssertionError("must not construct strategies"),
            ),
        ):
            reader = ReadOnlyOracle(
                self.path, instrument="SOL/USD", archived_versions=True
            )
            result = reader.predictions(1001)
            status = reader.status()
        self.assertEqual(result["signal"], "Strong Buy")
        self.assertEqual(result["policy_hash"], policy_hash)
        self.assertEqual(result["policy_origin"], "recorded_archive")
        self.assertEqual(result["strategy_code_compatibility"], "not_asserted")
        self.assertEqual(
            result["recorded_versions"],
            {row["strategy_id"]: row["version"] for row in policy["strategies"]},
        )
        self.assertNotEqual(
            result["recorded_versions"][self.catalog[0]["strategy_id"]],
            self.catalog[0]["version"],
        )
        self.assertEqual(result["strategies"][0]["hits"], 1)
        self.assertEqual(result["strategies"][0]["resolved"], 1)
        self.assertEqual(status["policy"], policy)
        self.assertFalse(hasattr(reader.strategy_set, "predict"))
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_known_schema2_archive_does_not_enable_current_reader_or_writer(self):
        self._record_schema2_archive()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
            ValueError, "oracle_policy_implementation_unavailable"
        ):
            ReadOnlyOracle(self.path, instrument="SOL/USD")
        with self.assertRaisesRegex(
            ValueError, "archive_policy_mismatch_use_new_archive"
        ):
            OracleEngine(self.path, instrument="SOL/USD", minimum_resolved=1)
        with self.assertRaisesRegex(ValueError, "oracle_policy_incompatible"):
            ReadOnlyOracle(self.path, instrument="SOL/USDC", archived_versions=True)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_known_schema2_archive_still_rejects_unknown_or_tampered_policy(self):
        original, _ = self._record_schema2_archive()
        for change, error in (
            ("implementation", "oracle_policy_implementation_unavailable"),
            ("schema", "oracle_policy_implementation_unavailable"),
            ("vote_accuracy", "oracle_policy_incompatible"),
            ("vote_semantics", "oracle_policy_incompatible"),
            ("identity", "oracle_recorded_catalog_invalid"),
            ("version", "oracle_recorded_catalog_invalid"),
            ("parameters", "oracle_recorded_parameters_invalid"),
            ("policy_binding", "oracle_recorded_policy_binding_invalid"),
        ):
            with self.subTest(change=change):
                policy = json.loads(canonical(original))
                if change == "implementation":
                    policy["implementation_sha256"] = "0" * 64
                elif change == "schema":
                    policy["schema_version"] = 1
                elif change == "vote_accuracy":
                    policy["minimum_vote_accuracy"] = 0
                elif change == "vote_semantics":
                    policy["vote_threshold_semantics"] = "greater_than_or_equal"
                elif change == "identity":
                    policy["strategies"][0]["strategy_id"] = "unknown"
                elif change == "version":
                    policy["strategies"][0]["version"] = "not-a-version"
                elif change == "parameters":
                    policy["strategies"][0]["parameters"]["fast"] = -1
                else:
                    policy["minimum_resolved"] = 2
                with self.writer.store.connection() as db:
                    db.execute(
                        "UPDATE metadata SET body=? WHERE key='policy'",
                        (canonical(policy),),
                    )
                before = hashlib.sha256(self.path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(ValueError, error):
                    ReadOnlyOracle(
                        self.path, instrument="SOL/USD", archived_versions=True
                    )
                self.assertEqual(
                    hashlib.sha256(self.path.read_bytes()).hexdigest(), before
                )

    def test_known_schema2_archive_still_checks_forecast_relational_identity(self):
        self._record_schema2_archive()
        with self.writer.store.connection() as db:
            row = db.execute("SELECT * FROM forecasts WHERE id='current'").fetchone()
            body = json.loads(row["body"])
            body["version"] = "f" * 64
            db.execute(
                "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                ("tampered", *tuple(row)[1:-1], canonical(body)),
            )
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
            ValueError, "oracle_recorded_policy_binding_invalid"
        ):
            ReadOnlyOracle(self.path, instrument="SOL/USD", archived_versions=True)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

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
