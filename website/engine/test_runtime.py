from __future__ import annotations

import datetime as dt
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from website.engine.public_data import DataError, PublicData
from website.engine.runtime import Runtime
from website.engine.server import RequestError, make_server
from website.engine.state import StateError
from website.engine.test_jobs import REQUEST, cache
from website.engine.test_state import MemoryState


class PublicDataTests(unittest.TestCase):
    def test_inclusive_provider_end_is_below_closed_boundary_and_pages_remain_contiguous(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            now = 1_800_000_005
            requested = []

            def inclusive_provider(path):
                query = parse_qs(urlsplit(path).query)
                start = int(dt.datetime.fromisoformat(query["start"][0]).timestamp())
                end = int(dt.datetime.fromisoformat(query["end"][0]).timestamp())
                requested.append((start, end))
                # Controlled HTTP-contract stand-in for the actual Exchange
                # inclusive endpoint: aligned endpoints produce301 rows.
                return [
                    [stamp, 99, 102, 100, 101, 10]
                    for stamp in range(start, end + 1, 300)
                ]

            public = PublicData(temp, transport=inclusive_provider, clock=lambda: now)
            first = public.refresh("SOL", "5m")
            self.assertEqual(first["bars"], 300)
            self.assertEqual(requested[0][1], now // 300 * 300 - 1)
            self.assertEqual(first["lastBar"], now // 300 * 300 - 300)
            self.assertTrue(first["contiguous"])
            second = public.refresh("SOL", "5m")
            self.assertEqual(second["bars"], 600)
            self.assertEqual(second["lastBar"], first["lastBar"])
            self.assertTrue(second["contiguous"])

    def test_mapping_closed_bar_filter_and_gaps_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            now = 1_700_000_040
            rows = [
                [now - 180, 90, 110, 95, 100, 10],
                [now - 60, 190, 210, 195, 200, 0],
                [now, 200, 220, 205, 210, 20],
            ]
            source = PublicData(temp, transport=lambda _: rows, clock=lambda: now + 10)
            output = source.refresh("SOL", "1m")
            self.assertEqual(output["bars"], 2)
            self.assertFalse(output["contiguous"])
            raw = (Path(temp) / "SOL_1m.csv").read_bytes()
            self.assertIn(b",95.0,110.0,90.0,100.0,10.0", raw)
            self.assertEqual(output["sha256"], hashlib.sha256(raw).hexdigest())

    def test_ticker_preserves_provider_clock_and_rejects_future(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = {
                "time": "2026-01-01T00:00:00Z",
                "price": "100.25",
                "trade_id": 123,
            }
            observed = dt.datetime(2026, 1, 1, tzinfo=dt.UTC).timestamp()
            data = PublicData(
                temp, transport=lambda _: payload, clock=lambda: observed + 1
            )
            tick = data.ticker("ZEC")
            self.assertEqual(tick["observed_at"], observed)
            self.assertEqual(tick["received_at"], observed + 1)
            self.assertEqual(tick["instrument"], "ZEC/USD")
            self.assertEqual(tick["kind"], "public_reference")
            data.clock = lambda: observed - 1
            with self.assertRaisesRegex(DataError, "time"):
                data.ticker("ZEC")


class RuntimeTests(unittest.TestCase):
    def test_legacy_http_defaults_match_explicit_economics_without_weakening_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Runtime(temp, MemoryState())
            runtime.initialize()
            path = cache(temp, interval="1h")
            rows = path.read_text().splitlines()
            for i in range(1, len(rows)):
                rows[i] = (
                    str(1609459200 + (i - 1) * 3600) + "," + rows[i].split(",", 1)[1]
                )
            raw = ("\n".join(rows) + "\n").encode()
            path.write_bytes(raw)
            metadata = json.loads(path.with_suffix(".json").read_text())
            metadata.update(
                sha256=hashlib.sha256(raw).hexdigest(), lastBar=1609459200 + 99 * 3600
            )
            path.with_suffix(".json").write_text(json.dumps(metadata))
            server = make_server(runtime.analysis, "x" * 32, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def post(body, endpoint="/v1/backtests"):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", server.server_port, timeout=20
                )
                connection.request(
                    "POST",
                    endpoint,
                    json.dumps(body),
                    {
                        "Authorization": "Bearer " + "x" * 32,
                        "Content-Type": "application/json",
                    },
                )
                response = connection.getresponse()
                result = response.status, json.loads(response.read())
                connection.close()
                return result

            try:
                partial = {"coin": "SOL", "strategy": "buy_and_hold"}
                default_status, defaults = post(partial)
                self.assertEqual(default_status, 200)
                explicit = {
                    **partial,
                    "interval": "1h",
                    "capital": 10000,
                    "leverage": 1,
                }
                explicit_status, explicit_result = post(explicit)
                self.assertEqual(explicit_status, 200)
                self.assertEqual(defaults, explicit_result)
                self.assertEqual(defaults["status"], "complete")
                for invalid in (
                    {**partial, "wallet": "forbidden"},
                    {"coin": "SOL"},
                    {**partial, "capital": True},
                    {**partial, "strategy": "unsupported"},
                ):
                    self.assertEqual(post(invalid)[0], 400)
                self.assertEqual(
                    post({"id": str(uuid.uuid4()), "request": partial}, "/v1/jobs")[0],
                    400,
                )
                with runtime.jobs.connection() as db:
                    hashes = [
                        row[0]
                        for row in db.execute(
                            "SELECT request_hash FROM jobs WHERE status='complete'"
                        )
                    ]
                self.assertEqual(len(hashes), 2)
                self.assertEqual(hashes[0], hashes[1])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_terminal_validation_receipt_is_not_exposed_before_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            runtime = Runtime(temp, remote)
            runtime.initialize()
            identifier = str(uuid.uuid4())
            remote.fail = True
            with self.assertRaises(StateError):
                runtime.enqueue({"id": identifier, "request": REQUEST})
            with self.assertRaisesRegex(RequestError, "not_ready"):
                runtime.get_job(identifier)
            remote.fail = False
            runtime.save()
            rejected = runtime.get_job(identifier)
            self.assertEqual(rejected["status"], "failed")
            self.assertEqual(rejected["error"], "cached_history_unavailable")
            remote.epoch = 2
            recovered = Runtime(Path(temp) / "recovered", remote)
            recovered.initialize()
            self.assertEqual(recovered.get_job(identifier), rejected)

    def test_http_unknown_strategy_is_durable_failure_and_next_valid_job_completes(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Runtime(temp, MemoryState())
            runtime.initialize()
            cache(temp)
            server = make_server(runtime.analysis, "x" * 32, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def call(method, path, body=None):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", server.server_port, timeout=5
                )
                connection.request(
                    method,
                    path,
                    json.dumps(body) if body else None,
                    {
                        "Authorization": "Bearer " + "x" * 32,
                        "Content-Type": "application/json",
                    },
                )
                response = connection.getresponse()
                result = response.status, json.loads(response.read())
                connection.close()
                return result

            try:
                rejected_id = str(uuid.uuid4())
                request = {**REQUEST, "strategy": "not_in_registry"}
                status, rejected = call(
                    "POST", "/v1/jobs", {"id": rejected_id, "request": request}
                )
                self.assertEqual(status, 200)
                self.assertEqual(rejected["status"], "failed")
                self.assertEqual(rejected["id"], rejected_id)
                self.assertEqual(rejected["error"], "unsupported_market_or_strategy")
                self.assertEqual(
                    call("GET", "/v1/jobs/" + rejected_id), (200, rejected)
                )
                self.assertEqual(
                    call("POST", "/v1/jobs", {"id": rejected_id, "request": request}),
                    (200, rejected),
                )
                accepted_id = str(uuid.uuid4())
                self.assertEqual(
                    call("POST", "/v1/jobs", {"id": accepted_id, "request": REQUEST})[
                        0
                    ],
                    202,
                )
                self.assertEqual(runtime.process(accepted_id)["status"], "complete")
                completed_status, completed = call("GET", "/v1/jobs/" + accepted_id)
                self.assertEqual(completed_status, 200)
                self.assertEqual(completed["status"], "complete")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)
            runtime.checkpoint.remote.epoch = 2
            restarted = Runtime(Path(temp) / "restored", runtime.checkpoint.remote)
            restarted.initialize()
            self.assertEqual(restarted.get_job(rejected_id), rejected)

    def test_initial_checkpoint_failure_retries_owned_state_without_fresh_history(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            remote.fail = True
            runtime = Runtime(temp, remote)
            with mock.patch.object(remote, "head", wraps=remote.head) as read:
                with self.assertRaises(StateError):
                    runtime.initialize()
                self.assertFalse(runtime.health()["ready"])
                remote.fail = False
                runtime.initialize()
                self.assertEqual(read.call_count, 1)
            self.assertTrue(runtime.health()["ready"])
            self.assertIsNone(runtime.health()["error"])
            self.assertEqual(runtime.engines["ZEC"].status()["counts"]["forecasts"], 0)

    def test_real_historical_feature_prime_never_creates_historical_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            now = 1_700_000_040
            rows = [
                [now - (300 - i) * 60, 99 + i, 103 + i, 100 + i, 101 + i, 10]
                for i in range(300)
            ]
            public = PublicData(
                Path(temp) / "data", transport=lambda _: rows, clock=lambda: now
            )
            runtime = Runtime(temp, MemoryState(), public=public, clock=lambda: now)
            runtime.initialize()
            runtime.refresh_cache("ZEC", "1m")
            engine = runtime.engines["ZEC"]
            before = engine.status()["counts"]
            self.assertGreater(before["observations"], 200)
            self.assertEqual(before["forecasts"], 0)
            self.assertEqual(before["resolutions"], 0)
            self.assertEqual(runtime.bootstrap["ZEC"]["historicalForecasts"], 0)
            engine.ingest(
                {
                    "source": "coinbase_exchange_public",
                    "instrument": "ZEC/USD",
                    "venue": "coinbase",
                    "kind": "public_reference",
                    "event_id": "ZEC:trade:123",
                    "observed_at": now,
                    "received_at": now,
                    "price": 405,
                    "timestamp_semantics": "exchange_trade_time",
                    "provider": "api.exchange.coinbase.com",
                    "upstream_recency_verified": True,
                },
                now=now,
            )
            after = engine.status()["counts"]
            self.assertGreater(after["forecasts"], 0)
            self.assertEqual(after["resolutions"], 0)
            runtime.save()
            value = runtime.analysis.oracle("ZEC", now=now)
            self.assertEqual(value["status"], "unavailable")
            self.assertIsNone(value["topStrategy"])
            self.assertEqual(
                value["durability"]["sequence"], runtime.checkpoint.sequence
            )

    def test_completed_job_is_hidden_until_remote_commit_and_survives_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            runtime = Runtime(Path(temp) / "original", remote)
            runtime.initialize()
            cache(runtime.root)
            identifier = str(uuid.uuid4())
            runtime.enqueue({"id": identifier, "request": REQUEST})
            original_save = runtime.save
            calls = 0

            def fail_second():
                nonlocal calls
                calls += 1
                if calls == 2:
                    remote.fail = True
                return original_save()

            with (
                mock.patch.object(runtime, "save", side_effect=fail_second),
                mock.patch.object(
                    runtime.jobs,
                    "calculate",
                    return_value={"result": {"status": "complete", "metrics": {}}},
                ),
                self.assertRaises(StateError),
            ):
                runtime.process(identifier)
            with self.assertRaisesRegex(RequestError, "not_ready"):
                runtime.get_job(identifier)
            # A cold owner sees only the last durable running state, then safely
            # requeues the pure calculation with the exact pinned input.
            remote.fail, remote.epoch = False, 2
            restored = Runtime(Path(temp) / "restored", remote)
            restored.initialize()
            self.assertEqual(restored.get_job(identifier)["status"], "queued")
            self.assertEqual(
                restored.get_job(identifier)["inputHash"],
                runtime.jobs.get(identifier)["inputHash"],
            )
            self.assertEqual(restored.process(identifier)["status"], "complete")

    def test_actual_http_async_health_auth_and_idempotency_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Runtime(temp, MemoryState())
            runtime.initialize()
            cache(temp)
            server = make_server(runtime.analysis, "x" * 32, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def call(method, path, body=None, origin=False):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", server.server_port, timeout=5
                )
                headers = {
                    "Authorization": "Bearer " + "x" * 32,
                    "Content-Type": "application/json",
                }
                if origin:
                    headers["Origin"] = "https://oraclebot.io"
                connection.request(
                    method, path, json.dumps(body) if body else None, headers
                )
                result = connection.getresponse()
                output = result.status, json.loads(result.read())
                connection.close()
                return output

            try:
                status, health = call("GET", "/health")
                self.assertEqual(status, 200)
                self.assertTrue(health["ready"])
                self.assertEqual(len(health["sourceIdentity"]["sha256"]), 64)
                self.assertEqual(call("GET", "/health", origin=True)[0], 403)
                identifier = str(uuid.uuid4())
                body = {"id": identifier, "request": REQUEST}
                self.assertEqual(call("POST", "/v1/jobs", body)[0], 202)
                self.assertEqual(call("POST", "/v1/jobs", body)[1]["status"], "queued")
                self.assertEqual(
                    call(
                        "POST",
                        "/v1/jobs",
                        {**body, "request": {**REQUEST, "capital": 20000}},
                    )[0],
                    409,
                )
                self.assertEqual(
                    call("GET", "/v1/jobs/" + identifier)[1]["id"], identifier
                )
                self.assertEqual(call("GET", "/v1/jobs/" + str(uuid.uuid4()))[0], 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)
