from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from website.engine.jobs import Jobs
from website.engine.server import RequestError


def cache(root, coin="SOL", interval="1d", *, offset=0):
    path = Path(root) / "data" / f"{coin}_{interval}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("timestamp", "open", "high", "low", "close", "volume"))
    for i in range(100):
        price = 100 + i + offset
        writer.writerow(
            (1609459200 + i * 86400, price, price + 2, price - 1, price + 1, 1000)
        )
    raw = buffer.getvalue().encode()
    path.write_bytes(raw)
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "provider": "https://api.exchange.coinbase.com",
                "product": coin + "-USD",
                "interval": interval,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bars": 100,
                "lastBar": 1609459200 + 99 * 86400,
                "contiguous": True,
            }
        )
    )
    return path


REQUEST = {
    "coin": "SOL",
    "strategy": "buy_and_hold",
    "interval": "1d",
    "capital": 10000,
    "leverage": 1,
}


class JobsTests(unittest.TestCase):
    def test_semantic_refusal_remains_failed_after_registry_or_capacity_changes(self):
        from backtester.core.strategies import REGISTRY

        with tempfile.TemporaryDirectory() as temp:
            cache(temp)
            jobs = Jobs(temp)
            identifier = str(uuid.uuid4())
            request = {**REQUEST, "strategy": "future_strategy"}
            rejected, _ = jobs.enqueue({"id": identifier, "request": request})
            self.assertEqual(rejected["error"], "unsupported_market_or_strategy")
            with mock.patch.dict(
                REGISTRY, {"future_strategy": REGISTRY["buy_and_hold"]}
            ):
                self.assertEqual(
                    jobs.enqueue({"id": identifier, "request": request}),
                    (rejected, False),
                )
            capacity_id = str(uuid.uuid4())
            with mock.patch("website.engine.jobs.MAX_PENDING", 0):
                capacity, _ = jobs.enqueue({"id": capacity_id, "request": REQUEST})
            self.assertEqual(capacity["error"], "job_capacity_reached")
            self.assertEqual(
                jobs.enqueue({"id": capacity_id, "request": REQUEST}), (capacity, False)
            )

    def test_malformed_request_has_no_accepted_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs = Jobs(temp)
            for body in (
                {"id": "bad", "request": REQUEST},
                {"id": str(uuid.uuid4()), "request": []},
                {"id": str(uuid.uuid4()), "request": {**REQUEST, "capital": True}},
                {"id": str(uuid.uuid4()), "request": {**REQUEST, "path": "/private"}},
            ):
                with self.subTest(body=body), self.assertRaises(RequestError):
                    jobs.enqueue(body)
            with jobs.connection() as db:
                self.assertEqual(
                    db.execute("SELECT count(*) FROM jobs").fetchone()[0], 0
                )

    def test_input_freeze_io_failure_is_a_sanitized_terminal_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            cache(temp)
            jobs = Jobs(temp)
            with mock.patch(
                "website.engine.jobs.atomic",
                side_effect=OSError("never_publish_private_diagnostics"),
            ):
                rejected, _ = jobs.enqueue(
                    {"id": str(uuid.uuid4()), "request": REQUEST}
                )
            self.assertEqual(rejected["status"], "failed")
            self.assertEqual(rejected["error"], "input_freeze_unavailable")
            self.assertNotIn("never_publish", json.dumps(rejected))

    def test_input_refusal_is_terminal_idempotent_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs = Jobs(temp)
            identifier = str(uuid.uuid4())
            rejected, created = jobs.enqueue({"id": identifier, "request": REQUEST})
            self.assertTrue(created)
            self.assertEqual(rejected["status"], "failed")
            self.assertEqual(rejected["error"], "cached_history_unavailable")
            self.assertIsNone(rejected["inputHash"])
            cache(temp)
            self.assertEqual(
                jobs.enqueue({"id": identifier, "request": REQUEST}), (rejected, False)
            )
            restarted = Jobs(temp)
            self.assertEqual(restarted.get(identifier), rejected)
            self.assertEqual(
                restarted.enqueue({"id": identifier, "request": REQUEST}),
                (rejected, False),
            )
            accepted, _ = restarted.enqueue(
                {"id": str(uuid.uuid4()), "request": REQUEST}
            )
            self.assertEqual(accepted["status"], "queued")
            self.assertEqual(restarted.next()["id"], accepted["id"])

    def test_idempotency_and_caller_hash_are_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            cache(temp)
            jobs = Jobs(temp)
            identifier = str(uuid.uuid4())
            job, created = jobs.enqueue({"id": identifier, "request": REQUEST})
            self.assertTrue(created)
            expected = hashlib.sha256(
                json.dumps(
                    REQUEST,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                ).encode()
            ).hexdigest()
            self.assertEqual(job["requestHash"], expected)
            self.assertEqual(
                jobs.enqueue(
                    {"id": identifier, "request": dict(reversed(list(REQUEST.items())))}
                ),
                (job, False),
            )
            with self.assertRaisesRegex(RequestError, "idempotency"):
                jobs.enqueue(
                    {"id": identifier, "request": {**REQUEST, "capital": 20000}}
                )

    def test_restart_retries_frozen_input_and_completes_real_canonical_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            cache(temp)
            jobs = Jobs(temp)
            identifier = str(uuid.uuid4())
            initial, _ = jobs.enqueue({"id": identifier, "request": REQUEST})
            jobs.next()
            cache(temp, offset=1000)
            restarted = Jobs(temp)
            self.assertEqual(restarted.recover(), 1)
            row = restarted.next()
            outcome = restarted.calculate(row)
            completed = restarted.finish(identifier, outcome)
            self.assertEqual(completed["status"], "complete")
            self.assertEqual(completed["inputHash"], initial["inputHash"])
            self.assertEqual(
                completed["result"]["provenance"]["sourceSha256"], initial["inputHash"]
            )
            self.assertGreater(completed["result"]["metrics"]["total_fees"], 0)
            self.assertEqual(
                restarted.enqueue({"id": identifier, "request": REQUEST}),
                (completed, False),
            )

    def test_timeout_releases_owned_calculation_child(self):
        with tempfile.TemporaryDirectory() as temp:
            cache(temp)
            jobs = Jobs(temp)
            jobs.enqueue({"id": str(uuid.uuid4()), "request": REQUEST})
            output = jobs.calculate(jobs.next(), timeout=0)
            self.assertEqual(output, {"error": "calculation_timeout"})
            self.assertFalse(list(Path(temp).glob(".result-*.json")))

    def test_missing_provenance_is_failed_and_never_scheduled(self):
        with tempfile.TemporaryDirectory() as temp:
            path = cache(temp)
            path.with_suffix(".json").unlink()
            jobs = Jobs(temp)
            rejected, _ = jobs.enqueue({"id": str(uuid.uuid4()), "request": REQUEST})
            self.assertEqual(rejected["status"], "failed")
            self.assertEqual(rejected["error"], "public_provenance_unavailable")
            self.assertIsNone(jobs.next())
            with jobs.connection() as db:
                self.assertEqual(
                    db.execute(
                        "SELECT count(*) FROM jobs WHERE status='failed'"
                    ).fetchone()[0],
                    1,
                )
