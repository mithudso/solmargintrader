from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from oracle.engine import OracleEngine
from oracle.reader import LEGACY_EVALUATOR_SHA256, ReadOnlyOracle
from oracle.store import canonical


def observation(index: int, price: float) -> dict:
    timestamp = index * 60 + 1
    return {
        "source": "fixture",
        "instrument": "SOL/USDC",
        "venue": "fixture",
        "kind": "reference",
        "event_id": f"graph_{index}",
        "observed_at": timestamp,
        "received_at": timestamp,
        "price": price,
    }


class GraphDBTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.sqlite3"
        self.engine = OracleEngine(self.path, minimum_resolved=1)

    def test_each_evaluated_bar_records_all_strategies_and_aggregate(self):
        for index, price in enumerate((100, 101, 99)):
            item = observation(index, price)
            self.engine.ingest(item, now=item["received_at"])

        graph = self.engine.graph_history()
        self.assertEqual(graph["status"], "available")
        self.assertEqual(graph["count"], 3)
        self.assertEqual(graph["aggregate_semantics"], "signed_weighted_vote_balance_not_probability")
        first, second, latest = graph["ticks"]
        self.assertEqual(latest["price"], 99)
        self.assertEqual(latest["time"], 121)
        self.assertEqual(len(latest["strategies"]), 14)
        self.assertEqual(len({row["strategy_id"] for row in latest["strategies"]}), 14)
        self.assertIn("signal", latest["aggregate"])
        self.assertEqual(first["market_shape"]["lookback_bars"], 0)
        self.assertNotIn("lookback_end", first["market_shape"])
        self.assertIsNone(first["market_shape"]["realized_volatility_bps"])
        self.assertEqual(second["market_shape"]["lookback_bars"], 1)
        self.assertEqual(second["market_shape"]["lookback_end"], 0)
        self.assertTrue(all(row["resolved"] == 0 for row in first["strategies"]))

    def test_history_limit_and_archive_rows_are_immutable(self):
        for index in range(3):
            item = observation(index, 100 + index)
            self.engine.ingest(item, now=item["received_at"])
        self.assertEqual(len(self.engine.graph_history(limit=2)["ticks"]), 2)
        with self.assertRaises(sqlite3.IntegrityError), self.engine.store.connection() as db:
            db.execute("UPDATE graphdb_ticks SET price=1")
        with self.assertRaises(sqlite3.IntegrityError), self.engine.store.connection() as db:
            db.execute("DELETE FROM graphdb_predictions")

    def test_duplicate_and_out_of_order_observations_do_not_add_graph_ticks(self):
        item = observation(1, 100)
        self.engine.ingest(item, now=item["received_at"])
        self.assertEqual(self.engine.ingest(item, now=item["received_at"])["status"], "duplicate")
        stale = observation(0, 99)
        self.engine.ingest(stale, now=stale["received_at"])
        self.assertEqual(self.engine.graph_history()["count"], 1)

    def test_legacy_archive_reports_missing_graph_without_writing(self):
        policy = {**self.engine.policy, "schema_version": 1,
                  "implementation_sha256": LEGACY_EVALUATOR_SHA256}
        policy.pop("minimum_vote_accuracy")
        policy.pop("vote_threshold_semantics")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE metadata SET body=? WHERE key='policy'", (canonical(policy),))
            db.execute("DROP TABLE graphdb_predictions")
            db.execute("DROP TABLE graphdb_ticks")
            db.execute("PRAGMA user_version=1")
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        reader = ReadOnlyOracle(self.path, instrument="SOL/USDC", archived_versions=True)
        graph = reader.graph_history()
        self.assertEqual(graph["status"], "unavailable")
        self.assertEqual(graph["reason"], "graph_history_not_recorded")
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
