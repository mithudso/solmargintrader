from __future__ import annotations

import asyncio
import io
import json
import sqlite3
import subprocess
import tempfile
import threading
import unittest
import urllib.error
from contextlib import asynccontextmanager, closing
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from oracle import quotes, server, webhook
from oracle.http_limits import DeadlineReader
from oracle.store import Store
from oracle.tests import test_multi_instrument as protocol_fixtures
from oracle.tests import test_quotes as fixtures
from oracle.tests import test_webhook as webhook_fixtures


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "history.sqlite3"
        Store(self.archive)
        self.request = {"inputMint": fixtures.SOL, "outputMint": fixtures.USDC,
                        "amount": 100000000, "slippageBps": 50}

    def collect(self, **kwargs):
        return quotes.collect_quote(self.archive, self.request, enabled=True,
                                    api_key="synthetic-key", endpoint="http://127.0.0.1:1/quote",
                                    _test_endpoint=True, _test_budget_path=self.root / "budget.sqlite3", **kwargs)

    def response(self, raw=None):
        response = mock.MagicMock()
        response.status = 200
        response.headers = Message()
        response.headers["Content-Type"] = "application/json"
        source = io.BytesIO(json.dumps(fixtures.fixture()).encode() if raw is None else raw)
        response.read1.side_effect = source.read1
        response.read.side_effect = source.read
        response.__enter__.return_value = response
        return response

    def test_enabled_success_binds_request_and_imports_only_validated_evidence(self):
        opener = mock.Mock()
        opener.open.return_value = self.response()
        with mock.patch.object(quotes.urllib.request, "build_opener", return_value=opener) as transport:
            observation = self.collect()
        transport.assert_called_once_with(quotes._NoRedirect)
        self.assertEqual(len(quotes.read_quotes(self.archive)), 1)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "synthetic-key")
        self.assertIn("onlyDirectRoutes=true", request.full_url)
        self.assertFalse(observation["certified"])

    def test_redirects_refuse_and_rate_budget_precedes_transport(self):
        with self.assertRaisesRegex(quotes.QuoteError, "quote_redirect_refused"):
            quotes._NoRedirect().redirect_request(None, None, 302, "", {}, "https://outside.invalid")
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.HTTPError("synthetic", 429, "secret-provider-body", {}, None)
        with mock.patch.object(quotes.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(quotes.QuoteError, "^quote_rate_limited$"):
                self.collect()
            with closing(sqlite3.connect(self.root / "budget.sqlite3")) as db:
                db.executemany("INSERT INTO requests(at) VALUES(?)", [(quotes.time.time(),)] * 59)
                db.commit()
            with self.assertRaisesRegex(quotes.QuoteError, "aggregate_rate_budget_exhausted"):
                self.collect()
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(quotes.read_quotes(self.archive), [])

    def test_oversize_and_drip_body_cannot_import(self):
        for oversized in (True, False):
            response = self.response(b"x" * (quotes.MAX_RESPONSE + 1)) if oversized else self.response()
            opener = mock.Mock(); opener.open.return_value = response
            clock = mock.patch.object(quotes.time, "monotonic", side_effect=range(100)) if not oversized else mock.patch.object(quotes.time, "monotonic", return_value=0)
            with (mock.patch.object(quotes.urllib.request, "build_opener", return_value=opener), clock,
                  self.assertRaisesRegex(quotes.QuoteError, "quote_response_too_large" if oversized else "quote_deadline_exceeded")):
                self.collect(timeout=2)
            self.assertEqual(quotes.read_quotes(self.archive), [])

    def test_webhook_header_and_body_share_deadline(self):
        clock = iter(range(20))
        reader = DeadlineReader(io.BytesIO(b"x" * 100), mock.Mock(), 5, clock=lambda: next(clock))
        with self.assertRaises(TimeoutError):
            reader.readline(100)

    def test_actual_webhook_handler_installs_deadline_before_header_parsing(self):
        with (mock.patch.object(webhook, "_WebhookHTTPServer", side_effect=RuntimeError("capture")) as constructor,
              self.assertRaisesRegex(RuntimeError, "capture")):
            webhook.serve(self.root / "unused.sqlite3", "x" * 32, 1, recover=lambda path: None)
        handler_type = constructor.call_args.args[1]
        handler = handler_type.__new__(handler_type)
        def setup(instance):
            instance.connection = mock.Mock()
            instance.rfile = io.BytesIO(b"x" * 100)
        with mock.patch("http.server.BaseHTTPRequestHandler.setup", setup):
            handler.setup()
        self.assertIsInstance(handler.rfile, DeadlineReader)
        clock = iter(range(20))
        handler.rfile.clock = lambda: next(clock)
        handler.rfile.deadline = 5
        with self.assertRaises(TimeoutError):
            handler.rfile.readline(100)

    def test_listener_fixture_kills_and_reaps_a_child_that_ignores_terminate(self):
        fixture = webhook_fixtures.WebhookTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        process = mock.Mock()
        process.communicate.side_effect = [subprocess.TimeoutExpired("synthetic", 5), (b"", b"")]
        connection = mock.Mock()
        connection.execute.return_value.fetchall.return_value = [("received",)]
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(b'{"status":"received","execution":"unavailable"}')
        with (mock.patch.object(webhook_fixtures.socket, "socket"),
              mock.patch.object(webhook_fixtures.subprocess, "Popen", return_value=process),
              mock.patch.object(webhook_fixtures.urllib.request, "urlopen", return_value=response),
              mock.patch.object(webhook_fixtures.sqlite3, "connect", return_value=connection),
              self.assertRaisesRegex(AssertionError, "listener did not terminate")):
            fixture.test_http_listener_records_without_order_submission()
        process.kill.assert_called_once()
        self.assertEqual(process.communicate.call_count, 2)
        self.assertTrue(all(call.kwargs == {"timeout": 5} for call in process.communicate.call_args_list))


class ProtocolSchedulingTests(unittest.IsolatedAsyncioTestCase):
    async def test_instrument_fixture_bounds_initialization_and_market_calls(self):
        @asynccontextmanager
        async def stdio(parameters):
            yield object(), object()

        original_wait = asyncio.wait_for
        for stuck in ("initialize", "oracle_market"):
            seen = []
            class Client:
                def __init__(self, *args): pass
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
                async def initialize(self, stuck=stuck):
                    if stuck == "initialize": await asyncio.Event().wait()
                async def call_tool(self, name, arguments, stuck=stuck):
                    if name == stuck: await asyncio.Event().wait()
                    return SimpleNamespace(model_dump=lambda **kwargs: {"structuredContent": {"ok": True, "data": {"instrument": "ETH/USD", "status": "unavailable"}}})

            async def short_wait(awaitable, timeout, seen=seen):
                seen.append(timeout)
                return await original_wait(awaitable, 0.002)

            fixture = protocol_fixtures.MultiInstrumentProtocolTests()
            with (mock.patch.object(protocol_fixtures, "stdio_client", stdio),
                  mock.patch.object(protocol_fixtures, "ClientSession", Client),
                  mock.patch.object(protocol_fixtures.asyncio, "wait_for", short_wait),
                  self.assertRaises(TimeoutError)):
                await original_wait(fixture.test_stdio_reader_uses_explicit_archive_instrument(), 0.1)
            self.assertEqual(seen, [10] if stuck == "initialize" else [10, 5, 10])

    async def test_eviction_has_sanitized_reason_without_session_or_exception(self):
        class Session:
            async def send_resource_updated(self, uri):
                raise RuntimeError("synthetic-sensitive-detail")
        session = Session()
        hub = server.SubscriptionHub()
        await hub.subscribe(session, "oracle://market")
        with self.assertLogs("oracle.server", level="WARNING") as output:
            await hub.publish({"oracle://market": "{}"})
        self.assertNotIn(session, hub._sessions)
        self.assertIn("transport_failure", str(output.output))
        self.assertNotIn("synthetic-sensitive-detail", str(output.output))

    async def test_archive_watch_yields_to_protocol_while_reader_is_blocked(self):
        entered, released = threading.Event(), threading.Event()
        class Engine:
            def market(self):
                entered.set(); released.wait(0.5); return {}
            def status(self): return {}
            def predictions(self): return {}
        class FakeServer:
            def __init__(self, *args, lifespan, **kwargs): self.lifespan = lifespan
            def __getattr__(self, name): return lambda *args, **kwargs: lambda method: method
        timer = threading.Timer(0.3, released.set)
        timer.start()
        try:
            server._load_sdk()
            with mock.patch.object(server, "Server", FakeServer), mock.patch.object(server, "_SDK_V2", False):
                protocol, _hub = server.build_server(Engine())
            async with protocol.lifespan(protocol):
                self.assertTrue(await asyncio.to_thread(entered.wait, 0.5))
                await asyncio.sleep(0)
                self.assertFalse(released.is_set(), "archive I/O blocked protocol loop")
        finally:
            released.set(); timer.cancel(); timer.join()
