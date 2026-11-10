from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from oracle.engine import OracleEngine


def observation(i: int, price: float = 100, **extra) -> dict:
    return {
        "source": "fixture",
        "instrument": "SOL/USDC",
        "venue": "jupiter",
        "kind": "reference_ratio",
        "event_id": f"tick_{i}",
        "observed_at": i * 60 + 1,
        "received_at": i * 60 + 1,
        "price": price,
        **extra,
    }


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "oracle.sqlite3"
        self.engine = OracleEngine(self.path, minimum_resolved=1)

    def tearDown(self):
        self.temp.cleanup()

    def seed(self, count=70):
        for i in range(count):
            item = observation(i, 100 + i * 0.1)
            self.engine.ingest(item, now=item["received_at"])

    def test_no_data_never_becomes_flat(self):
        self.assertEqual(self.engine.market(now=1)["status"], "unavailable")
        self.assertEqual(self.engine.predictions(now=1)["aggregate"]["signal"], None)
        self.assertEqual(len(self.engine.strategies()), 14)

    def test_prospective_forecasts_survive_restart_without_reissue(self):
        self.seed()
        before = self.engine.status()["counts"]
        saved = [
            e
            for e in self.engine.history(limit=1000)["events"]
            if e["type"] == "prediction"
        ]
        self.assertTrue(saved)
        for event in saved:
            self.assertLessEqual(
                event["data"]["feature_cutoff"], event["data"]["issued_at"]
            )
            self.assertGreater(event["data"]["expires_at"], event["data"]["issued_at"])
        engine = OracleEngine(self.path, minimum_resolved=1)
        self.assertEqual(
            engine.ingest(observation(69, 106.9), now=4141)["status"], "duplicate"
        )
        self.assertEqual(before, engine.status()["counts"])

    def test_bad_source_duplicate_identity_and_numbers_refused(self):
        self.engine.ingest(observation(0), now=1)
        for candidate in (
            observation(0, 101),
            observation(1, source="other"),
            observation(2, price=float("nan")),
            observation(3, price=True),
            observation(4, instrument="SOL/USD"),
        ):
            with self.assertRaises(ValueError):
                self.engine.ingest(candidate, now=1000)

    def test_duplicate_delivery_ignores_receipt_clock_preserves_first(self):
        self.engine.ingest(observation(0), now=1)
        again = observation(0, received_at=2)
        self.assertEqual(self.engine.ingest(again, now=2)["status"], "duplicate")
        events = self.engine.history()["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["data"]["received_at"], 1)

    def test_past_query_cannot_count_future_resolution(self):
        self.seed(25)
        before = self.engine.predictions(now=1441)
        self.engine.ingest(observation(25), now=1501)
        after = self.engine.predictions(now=1441)
        self.assertEqual(
            [(s["hits"], s["resolved"]) for s in before["strategies"]],
            [(s["hits"], s["resolved"]) for s in after["strategies"]],
        )

    def test_out_of_order_archived_without_rewriting_market(self):
        self.engine.ingest(observation(1, 105), now=61)
        self.assertEqual(
            self.engine.ingest(observation(0), now=61)["status"],
            "out_of_order_archived",
        )
        self.assertEqual(self.engine.market(now=61)["observation"]["price"], 105)
        self.assertEqual(self.engine.status()["counts"]["events"], 2)

    def test_stale_feed_suppresses_aggregate_and_marks_reference(self):
        self.seed()
        output = self.engine.predictions(now=4141)
        self.assertIn("upstream_event_time_unknown", output["limitations"])
        self.assertFalse(output["tradable"])
        self.assertEqual(
            self.engine.predictions(now=4200)["aggregate"]["status"], "unavailable"
        )

    def test_falling_feed_can_publish_genuine_sell_and_flag_bad_rules(self):
        for i in range(80):
            self.engine.ingest(observation(i, 500 - i), now=i * 60 + 1)
        output = self.engine.predictions(now=4741)
        strategies = {row["strategy_id"]: row for row in output["strategies"]}
        self.assertEqual(strategies["ma_crossover"]["direction"], -1)
        self.assertEqual(output["aggregate"]["signal"], "Strong Sell")
        self.assertTrue(strategies["bb_breakout"]["needs_review"])
        self.assertEqual(
            strategies["bb_breakout"]["suggested_next_step"],
            "versioned_shadow_challenger",
        )

    def test_resolution_gap_does_not_add_hits_or_misses(self):
        self.seed(25)
        before = self.engine.predictions(now=1441)
        before_count = sum(s["resolved"] for s in before["strategies"])
        item = observation(30)
        self.engine.ingest(item, now=item["received_at"])
        after = self.engine.predictions(now=item["received_at"])
        self.assertEqual(before_count, sum(s["resolved"] for s in after["strategies"]))
        resolutions = [
            e
            for e in self.engine.history(limit=1000)["events"]
            if e["type"] == "resolution"
        ]
        self.assertTrue(
            any(e["data"]["reason"] == "resolution_gap" for e in resolutions)
        )

    def test_expired_local_replay_cannot_forge_forecasts(self):
        for i in range(100):
            self.engine.ingest(observation(i), now=10000)
        self.assertEqual(self.engine.status()["counts"]["forecasts"], 0)

    def test_changing_policy_requires_new_archive(self):
        with self.assertRaisesRegex(ValueError, "policy_mismatch"):
            OracleEngine(self.path, minimum_resolved=2)

    def test_raw_metadata_roundtrip_and_no_arbitrary_payload(self):
        item = observation(
            0,
            provider="https://api.jup.ag/price/v3",
            provider_block_ids={"SOL": 123},
            base_usd_price=100,
            quote_usd_price=1,
            key="must-not-persist",
        )
        self.engine.ingest(item, now=1)
        text = json.dumps(self.engine.history())
        self.assertIn("provider_block_ids", text)
        self.assertNotIn("must-not-persist", text)

    def test_archived_records_cannot_update_or_delete(self):
        self.engine.ingest(observation(0), now=1)
        with (
            self.engine.store.connection() as db,
            self.assertRaises(sqlite3.IntegrityError),
        ):
            db.execute("DELETE FROM events")


if __name__ == "__main__":
    unittest.main()
