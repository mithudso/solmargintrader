"""Real loopback HTTP fixtures verify transport and authority, not live trading."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.registry import CommandContext, dispatch


@contextmanager
def owner(
    *,
    old=False,
    health="soltui",
    malformed=False,
    delay=0,
    ambiguous=False,
    mutate=None,
    redirect=False,
    oversized=False,
    slow_headers=False,
):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def handle(self):
            try:
                super().handle()
            except ConnectionResetError:
                pass

        def do_GET(self):
            calls.append(("GET", self.path, self.headers.get("Authorization")))
            time.sleep(delay)
            if self.path == "/v1/health":
                body = {"ok": True, "service": health}
            elif self.path == "/v1/commands":

                def command(name, readonly, params=()):
                    return {
                        "name": name,
                        "read_only": readonly,
                        "params": [
                            {"name": n, "type": t, "required": required}
                            for n, t, required in params
                        ],
                    }

                body = {
                    "ok": True,
                    "command": "list",
                    "result": [
                        command("bots.overview", True),
                        command("council.status", True),
                        command("bots.config", True),
                        command("bots.forward_start", False),
                        command("bots.forward_stop", False),
                        command("bots.forward_status", True),
                    ]
                    + (
                        []
                        if old
                        else [
                            command("bots.manager_snapshot", True),
                            command(
                                "bots.manager_control",
                                False,
                                [
                                    ("bot", "string", True),
                                    ("operation", "string", True),
                                    ("asset", "string", True),
                                    ("request_id", "string", True),
                                    ("expected_session", "string", False),
                                    ("expected_config_hash", "string", True),
                                ],
                            ),
                        ]
                    ),
                    "error": None,
                }
            elif self.path == "/v1/bots.overview":
                body = {
                    "ok": True,
                    "command": "bots.overview",
                    "result": {
                        "bots": [
                            {
                                "bot": "grid",
                                "config": {"range_pct": 15},
                                "forward": {
                                    "id": "oldsession",
                                    "asset": "SOL",
                                    "stopped_at": None,
                                },
                            }
                        ],
                        "coins": ["SOL"],
                    },
                    "error": None,
                }
            elif self.path == "/v1/bots.manager_snapshot":
                body = {
                    "ok": True,
                    "command": "bots.manager_snapshot",
                    "result": {
                        "protocol_version": 1,
                        "source_hash": "a" * 64,
                        "bots": [
                            {
                                "bot": "grid",
                                "asset": "SOL",
                                "config_hash": "b" * 64,
                                "session_config_hash": "d" * 64,
                                "source_hash": "a" * 64,
                                "session_id": "session123",
                                "requested_state": "running",
                                "heartbeat_available": False,
                                "venue": "coinbase",
                                "mode": "paper",
                                "armed": False,
                                "bar_seconds": 60,
                                "execution_model": "recorded_1m_ohlc_replay",
                            }
                        ],
                    },
                    "error": None,
                }
            elif self.path == "/v1/council.status":
                body = {
                    "ok": True,
                    "command": "council.status",
                    "result": {
                        "running": True,
                        "state": "waiting",
                        "config": {"asset": "SOL"},
                        "owner": {"pid": 123, "started_at": 10},
                    },
                    "error": None,
                }
            else:
                body = {"unknown": True}
            self.send(body)

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            params = json.loads(self.rfile.read(length))
            calls.append(("POST", self.path, params))
            if ambiguous:
                self.close_connection = True
                return
            result = {
                "protocol_version": 1,
                "request_id": params["request_id"],
                "bot": params["bot"],
                "operation": params["operation"],
                "outcome": "acknowledged",
                "reason": "stop_recorded_exposure_unknown",
                "session_id": "session123",
                "config_hash": params["expected_config_hash"],
                "source_hash": "a" * 64,
            }
            self.send(
                {
                    "ok": True,
                    "command": "bots.manager_control",
                    "result": result,
                    "error": None,
                }
            )

        def send(self, body):
            if slow_headers:
                try:
                    for byte in b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n":
                        self.connection.sendall(bytes([byte]))
                        time.sleep(0.01)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                self.close_connection = True
                return
            if mutate is not None:
                body = mutate(self.path, body)
            payload = (
                b'{"credential":"CANARY"}' if malformed else json.dumps(body).encode()
            )
            if oversized:
                payload = b" " * 2048
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header("Location", "http://127.0.0.1:1/credential-sink")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except BrokenPipeError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class Legacy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def adapter(self, url, **kw):
        from botmanager.adapters.soltui import Installation, LegacyAdapter

        descriptor = Installation(
            installation_id="fixture-owner",
            source="soltui",
            endpoint=url,
            working_directory=Path("/fixture/repo"),
            interpreter=Path("/fixture/python3.13"),
            pinned_revision="c" * 40,
            config_root=self.root / "owner",
        )
        return LegacyAdapter(
            descriptor,
            home=self.root / "manager",
            token_resolver=lambda: "fixture-token",
            **kw,
        )

    def test_available_inventory_is_honest_and_readonly(self):
        with owner() as (url, calls):
            snapshot = self.adapter(url).discover().to_dict()
        self.assertEqual(snapshot["state"], "available")
        rows = snapshot["bots"]
        grid = next(r for r in rows if r["strategy_id"] == "grid")
        council = next(r for r in rows if r["strategy_id"] == "council")
        self.assertEqual(grid["desired_state"], "running")
        self.assertEqual(grid["active_config_hash"], "d" * 64)
        self.assertEqual(grid["config_hash_scope"], "saved_effective_configuration")
        self.assertEqual(grid["evidence_identity"]["config_hash"], "d" * 64)
        self.assertEqual(grid["observed_state"], "unknown")
        self.assertIsNone(grid["heartbeat_age_seconds"]["value"])
        self.assertEqual(council["observed_state"], "running")
        self.assertIsNone(grid["financials"]["exposure_usd"]["value"])
        self.assertFalse(grid["evidence"]["paper"]["venue_compatibility_verified"])
        self.assertTrue(grid["action_capabilities"]["stop"]["available"])
        self.assertFalse(grid["action_capabilities"]["close_position"]["available"])
        self.assertTrue(all(method == "GET" for method, *_ in calls))
        self.assertNotIn("/v1/council.config", [c[1] for c in calls])
        self.assertFalse((self.root / "manager").exists())

    def test_wrong_service_never_resolves_or_sends_credentials(self):
        with owner(health="global-ai-hub") as (url, calls):
            adapter = self.adapter(url)
            with patch.object(
                adapter, "_token", side_effect=AssertionError("must not resolve")
            ):
                snapshot = adapter.discover().to_dict()
        self.assertEqual(snapshot["state"], "incompatible_owner")
        self.assertEqual(calls, [("GET", "/v1/health", None)])

    def test_unreachable_not_zero_bots_and_timeout_is_bounded(self):
        # Bind then close an ephemeral port; no process is started on the unavailable endpoint.
        server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        url = f"http://127.0.0.1:{server.server_port}"
        server.server_close()
        snapshot = self.adapter(url, timeout=0.05).discover().to_dict()
        self.assertEqual(
            (snapshot["state"], snapshot["bots"]), ("owner_unreachable", None)
        )
        with owner(delay=0.1) as (url, _):
            snapshot = self.adapter(url, timeout=0.01).discover().to_dict()
        self.assertEqual(snapshot["state"], "owner_unreachable")

    def test_old_owner_inspection_refuses_controls(self):
        with owner(old=True) as (url, calls):
            adapter = self.adapter(url)
            snapshot = adapter.discover().to_dict()
            grid = next(r for r in snapshot["bots"] if r["strategy_id"] == "grid")
            self.assertEqual(grid["observed_state"], "unknown")
            receipt = adapter.control("grid", "stop", str(uuid.uuid4()), None)
            self.assertEqual(receipt.reason, "capability_unavailable")
            self.assertFalse(any(c[0] == "POST" for c in calls))

    def test_control_dedup_is_durable_and_conflict_never_posts(self):
        with owner() as (url, calls):
            adapter = self.adapter(url)
            adapter.discover()
            request = str(uuid.uuid4())
            receipt = adapter.control("grid", "stop", request, None)
            self.assertEqual(receipt.outcome, "acknowledged")
            again = self.adapter(url)
            self.assertEqual(
                again.control("grid", "stop", request, None).to_dict(),
                receipt.to_dict(),
            )
            self.assertEqual(
                again.control("grid", "start", request, None).reason,
                "request_id_conflict",
            )
            self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_ack_session_relationships_and_responding_revision_are_bound(self):
        cases = (
            (
                "stop",
                "acknowledged",
                "stop_recorded_exposure_unknown",
                "different_session",
                "unknown",
            ),
            ("stop", "acknowledged", "stop_recorded_exposure_unknown", None, "unknown"),
            (
                "start",
                "acknowledged",
                "forward_requested_heartbeat_unknown",
                None,
                "unknown",
            ),
            ("start", "skipped", "already_running", "different_session", "unknown"),
            ("stop", "skipped", "already_stopped", "different_session", "unknown"),
            (
                "stop",
                "acknowledged",
                "stop_recorded_exposure_unknown",
                "session123",
                "acknowledged",
            ),
            (
                "start",
                "acknowledged",
                "forward_requested_heartbeat_unknown",
                "new_session",
                "acknowledged",
            ),
        )
        for operation, outcome, reason, session, expected in cases:
            with self.subTest(operation=operation, outcome=outcome, session=session):

                def mutate(
                    path,
                    body,
                    operation=operation,
                    outcome=outcome,
                    reason=reason,
                    session=session,
                ):
                    if path == "/v1/bots.manager_control":
                        body["result"].update(
                            operation=operation,
                            outcome=outcome,
                            reason=reason,
                            session_id=session,
                            source_hash="f" * 64,
                        )
                    return body

                with owner(mutate=mutate) as (url, calls):
                    adapter = self.adapter(url)
                    adapter.discover()
                    request_id = str(uuid.uuid4())
                    receipt = adapter.control("grid", operation, request_id, None)
                    self.assertEqual(receipt.outcome, expected)
                    self.assertEqual(receipt.metadata["owner_revision"], "f" * 64)
                    replay = self.adapter(url).control(
                        "grid", operation, request_id, None
                    )
                    self.assertEqual(replay.metadata["owner_revision"], "f" * 64)
                    if expected == "unknown":
                        self.assertTrue(receipt.reconciliation_required)
                        self.assertEqual(replay.outcome, "unknown")
                    else:
                        self.assertEqual(replay.to_dict(), receipt.to_dict())
                    self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_corrupt_persisted_receipt_is_not_replayed_as_another_request_or_operation(
        self,
    ):
        import sqlite3
        from contextlib import closing

        mutations = (
            {"request_id": str(uuid.uuid4())},
            {"operation": "start"},
            {"bot_id": str(uuid.uuid4())},
            {"owner_id": "other-owner"},
            {"runtime_id": "other_session"},
            {"outcome": "skipped"},
            {"reason": "already_stopped"},
            {"metadata": {"config_hash": "e" * 64}},
        )
        for changes in mutations:
            with self.subTest(changes=changes), owner() as (url, calls):
                adapter = self.adapter(url)
                adapter.discover()
                request_id = str(uuid.uuid4())
                receipt = adapter.control("grid", "stop", request_id, None)
                with (
                    closing(
                        sqlite3.connect(self.root / "manager" / "controls.sqlite3")
                    ) as db,
                    db,
                ):
                    forged = {**receipt.to_dict(), **changes}
                    db.execute(
                        "UPDATE requests SET body=? WHERE request_id=?",
                        (json.dumps(forged), request_id),
                    )
                with self.assertRaises(ManagerError) as caught:
                    self.adapter(url).control("grid", "stop", request_id, None)
                self.assertEqual(caught.exception.code, "invalid_receipt")
                self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_self_consistent_checksum_cannot_change_the_bound_stop_session(self):
        import hashlib
        import sqlite3
        from contextlib import closing

        from botmanager.domain import canonical

        with owner() as (url, calls):
            adapter = self.adapter(url)
            adapter.discover()
            request_id = str(uuid.uuid4())
            receipt = adapter.control("grid", "stop", request_id, None)
            forged = {**receipt.to_dict(), "runtime_id": "different_session"}
            with (
                closing(
                    sqlite3.connect(self.root / "manager" / "controls.sqlite3")
                ) as db,
                db,
            ):
                binding = json.loads(
                    db.execute(
                        "SELECT binding FROM requests WHERE request_id=?", (request_id,)
                    ).fetchone()[0]
                )
                binding["receipt_hash"] = hashlib.sha256(
                    canonical(forged).encode()
                ).hexdigest()
                db.execute(
                    "UPDATE requests SET body=?,binding=? WHERE request_id=?",
                    (canonical(forged), canonical(binding), request_id),
                )
            with self.assertRaises(ManagerError) as caught:
                self.adapter(url).control("grid", "stop", request_id, None)
            self.assertEqual(caught.exception.code, "invalid_receipt")
            self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_old_unbound_manager_receipts_are_preserved_but_never_replayed(self):
        import sqlite3
        from contextlib import closing

        with owner() as (url, calls):
            adapter = self.adapter(url)
            adapter.discover()
            request_id = str(uuid.uuid4())
            receipt = adapter.control("grid", "stop", request_id, None)
            path = self.root / "manager" / "controls.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("ALTER TABLE requests RENAME TO bound_requests")
                db.execute(
                    "CREATE TABLE requests (request_id TEXT PRIMARY KEY, identity_hash TEXT NOT NULL, fingerprint TEXT NOT NULL, body TEXT NOT NULL)"
                )
                db.execute(
                    "INSERT INTO requests SELECT request_id,identity_hash,fingerprint,body FROM bound_requests"
                )
                db.execute("DROP TABLE bound_requests")
                db.execute("PRAGMA user_version=1")
            with self.assertRaises(ManagerError) as caught:
                self.adapter(url).control("grid", "stop", request_id, None)
            self.assertEqual(caught.exception.code, "invalid_receipt")
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)
                body, binding = db.execute(
                    "SELECT body,binding FROM requests WHERE request_id=?",
                    (request_id,),
                ).fetchone()
            self.assertEqual(json.loads(body), receipt.to_dict())
            self.assertIsNone(binding)
            self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_lost_ack_replay_reconciles_reads_and_never_reposts(self):
        with owner(ambiguous=True) as (url, calls):
            adapter = self.adapter(url)
            adapter.discover()
            request = str(uuid.uuid4())
            first = adapter.control("grid", "stop", request, None)
            self.assertEqual(
                (first.outcome, first.reason), ("unknown", "outcome_unknown")
            )
            second = self.adapter(url).control("grid", "stop", request, None)
            self.assertEqual(second.outcome, "unknown")
            self.assertTrue(second.reconciliation_required)
            self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_malformed_future_and_unsafe_endpoints_are_sanitized(self):
        with owner(malformed=True) as (url, _):
            result = self.adapter(url).discover().to_dict()
            self.assertEqual(result["state"], "incompatible_owner")
            self.assertNotIn("CANARY", json.dumps(result))
        for url in (
            "http://example.com:80",
            "https://127.0.0.1:80",
            "http://localhost:80",
            "http://127.0.0.1:80/path",
        ):
            with self.subTest(url=url), self.assertRaises(ManagerError):
                self.adapter(url)

    def test_future_protocol_missing_param_and_wrong_receipt_outcome_refuse(self):
        def future(path, body):
            if path == "/v1/bots.manager_snapshot":
                body["result"]["protocol_version"] = 2
            return body

        with owner(mutate=future) as (url, calls):
            self.assertEqual(self.adapter(url).discover().state, "incompatible_owner")
            self.assertFalse(any(c[0] == "POST" for c in calls))

        def missing(path, body):
            if path == "/v1/commands":
                next(c for c in body["result"] if c["name"] == "bots.manager_control")[
                    "params"
                ].pop()
            return body

        with owner(mutate=missing) as (url, calls):
            adapter = self.adapter(url)
            self.assertEqual(adapter.discover().state, "available")
            self.assertEqual(
                adapter.control("grid", "stop", str(uuid.uuid4()), None).reason,
                "capability_unavailable",
            )
            self.assertFalse(any(c[0] == "POST" for c in calls))

        def wrong(path, body):
            if path == "/v1/bots.manager_control":
                body["result"].update(outcome="acknowledged", reason="outcome_unknown")
            return body

        with owner(mutate=wrong) as (url, _):
            adapter = self.adapter(url)
            adapter.discover()
            receipt = adapter.control("grid", "stop", str(uuid.uuid4()), None)
            self.assertEqual(
                (receipt.outcome, receipt.reason), ("unknown", "outcome_unknown")
            )

    def test_redirect_and_oversized_response_never_authenticate(self):
        for options in ({"redirect": True}, {"oversized": True}):
            with self.subTest(options=options), owner(**options) as (url, calls):
                adapter = self.adapter(url, max_bytes=1024)
                with patch.object(
                    adapter, "_token", side_effect=AssertionError("must not resolve")
                ):
                    self.assertEqual(adapter.discover().state, "incompatible_owner")
                self.assertTrue(all(c[2] is None for c in calls))

    def test_node_filestore_and_browser_are_separate_explicit_unavailable_sources(self):
        from botmanager.adapters import discover_installations

        records = discover_installations((), home=self.root).to_dict()
        sources = {r["source"]: r for r in records["installations"]}
        self.assertEqual(sources["browser"]["state"], "registration_required")
        self.assertEqual(sources["node_filestore"]["state"], "discovery_unavailable")
        self.assertNotEqual(
            sources["browser"]["installation_id"],
            sources["node_filestore"]["installation_id"],
        )
        self.assertFalse(self.root.joinpath("manager.sqlite3").exists())

    def test_trickled_headers_cannot_extend_the_total_transport_deadline(self):
        with owner(slow_headers=True) as (url, _):
            started = time.monotonic()
            snapshot = self.adapter(url, timeout=0.04).discover()
            elapsed = time.monotonic() - started
            self.assertEqual(snapshot.state, "owner_unreachable")
            self.assertLess(elapsed, 0.2)

    def test_legacy_context_preserves_tick_semantics_and_council_proxy(self):
        def triangle(path, body):
            if path == "/v1/bots.manager_snapshot":
                row = body["result"]["bots"][0]
                row.update(
                    bot="triangle",
                    asset="ALL",
                    venue="coinbase",
                    mode="paper",
                    armed=False,
                    bar_seconds=None,
                    execution_model="recorded_bid_ask",
                )
            elif path == "/v1/council.status":
                body["result"]["price_source"] = "Jupiter USD reference"
                body["result"]["fill_model"] = (
                    "Paper: next-minute-open Coinbase OHLC proxy; Jupiter USD quote is reference only."
                )
            return body

        with owner(mutate=triangle) as (url, _):
            snapshot = self.adapter(url).discover().to_dict()
        triangle = next(r for r in snapshot["bots"] if r["strategy_id"] == "triangle")
        council = next(r for r in snapshot["bots"] if r["strategy_id"] == "council")
        self.assertIsNone(triangle["bar_seconds"])
        self.assertEqual(triangle["bar_seconds_reason"], "event_driven_recorded_quotes")
        self.assertEqual(triangle["execution_model"], "recorded_bid_ask")
        self.assertEqual(council["venue"], "coinbase_proxy")
        self.assertEqual(
            council["execution_model"], "council_next_minute_open_coinbase_proxy"
        )
        self.assertEqual(triangle["instance_scope"], "one_instance_per_family")
        self.assertEqual(
            council["data_sources"]["reference_price"]["value"], "jupiter_usd_reference"
        )
        self.assertEqual(
            council["data_sources"]["simulation_fills"]["value"],
            "coinbase_next_minute_open_ohlc_proxy",
        )
        self.assertIsNone(council["data_sources"]["signal_inputs"]["value"])

    def test_registered_node_descriptor_is_not_browser_inventory(self):
        from dataclasses import replace

        from botmanager.adapters import discover_installations

        descriptor = replace(
            self.adapter("http://127.0.0.1:1").installation,
            source="node_filestore",
            installation_id="fixture-node",
        )
        result = discover_installations((descriptor,), home=self.root).to_dict()
        node = next(
            r for r in result["installations"] if r["source"] == "node_filestore"
        )
        browser = next(r for r in result["installations"] if r["source"] == "browser")
        self.assertEqual(node["descriptor"]["source"], "node_filestore")
        self.assertEqual(node["state"], "discovery_unavailable")
        self.assertEqual(browser["state"], "registration_required")
        self.assertIsNone(node["bots"])
        self.assertFalse((self.root / "owner").exists())

    def test_real_cli_reads_and_guarded_control_use_fixture_without_initializing_status(
        self,
    ):
        import os
        import subprocess
        import sys

        support = self.root / "support"
        support.mkdir()
        token = support / "api-token"
        token.write_text("fixture-token")
        token.chmod(0o600)
        with owner() as (url, calls):
            env = {
                **os.environ,
                "SOLBOT_HOME": str(self.root / "cli-manager"),
                "SOLTUI_SUPPORT_DIR": str(support),
                "SOLBOT_SOLTUI_ENDPOINT": url,
            }

            def run(*args):
                process = subprocess.run(
                    [sys.executable, "-m", "botmanager", *args],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                self.assertNotIn("fixture-token", process.stdout + process.stderr)
                return json.loads(process.stdout)

            self.assertTrue(run("discover")["ok"])
            self.assertTrue(run("status", "soltui-local:grid")["ok"])
            self.assertFalse((self.root / "cli-manager").exists())
            receipt = run(
                "stop",
                "soltui-local:grid",
                "--expected-session",
                "session123",
                "--expected-config-hash",
                "b" * 64,
                "--request-id",
                str(uuid.uuid4()),
            )["data"]
            self.assertEqual(receipt["outcome"], "acknowledged")
            self.assertEqual(sum(c[0] == "POST" for c in calls), 1)

    def test_registry_discovery_status_and_explicit_guarded_controls(self):
        with owner() as (url, calls):
            adapter = self.adapter(url)
            ctx = CommandContext(
                home=self.root / "manager",
                installations=(adapter.installation,),
                owner_adapters={"fixture-owner": adapter},
            )
            result = dispatch("discover", {}, ctx)
            self.assertTrue(result["ok"])
            status = dispatch("status", {"identity": "fixture-owner:grid"}, ctx)
            self.assertTrue(status["ok"])
            self.assertEqual(status["data"]["strategy_id"], "grid")
            missing = dispatch("stop", {"identity": "fixture-owner:grid"}, ctx)
            self.assertEqual(missing["error"]["code"], "expected_observation_required")
            stop = dispatch(
                "stop",
                {
                    "identity": "fixture-owner:grid",
                    "expected_session": "session123",
                    "expected_config_hash": "b" * 64,
                    "request_id": str(uuid.uuid4()),
                },
                ctx,
            )
            self.assertTrue(stop["ok"])
            self.assertEqual(stop["data"]["outcome"], "acknowledged")
            self.assertEqual(sum(c[0] == "POST" for c in calls), 1)
