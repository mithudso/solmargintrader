from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from oracle import webhook
from oracle.webhook import accept_signal, serve


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "inbox.sqlite"
        self.secret = "s" * 32
        self.event = {
            "secret": self.secret,
            "event_id": "alert-1",
            "symbol": "SOLUSDC",
            "side": "buy",
            "timestamp": 1000,
        }

    def send(self, **changes):
        return accept_signal(
            self.db,
            json.dumps({**self.event, **changes}).encode(),
            self.secret,
            now=1000,
        )

    def test_durable_dedup_and_conflict(self):
        self.assertEqual(self.send(), "received")
        self.assertEqual(self.send(), "duplicate")
        with self.assertRaises(ValueError):
            self.send(side="sell")
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(
                db.execute("SELECT side, status FROM signals").fetchall(),
                [("buy", "received")],
            )
        self.assertNotIn(self.secret.encode(), self.db.read_bytes())

    def test_tradingview_iso_timestamp(self):
        self.assertEqual(self.send(timestamp="1970-01-01T00:16:40Z"), "received")
        with self.assertRaises(ValueError):
            self.send(event_id="other", timestamp="1970-01-01T00:16:40")

    def test_http_listener_records_without_order_submission(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "ORACLE_WEBHOOK_SECRET": self.secret}
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "oracle",
                "webhook",
                "--port",
                str(port),
                "--inbox",
                str(self.db),
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            payload = {**self.event, "timestamp": int(time.time())}
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/tradingview",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            for attempt in range(50):
                try:
                    with urllib.request.urlopen(request, timeout=1) as response:
                        result = json.load(response)
                    break
                except OSError:
                    if attempt == 49:
                        raise
                    time.sleep(0.02)
            self.assertEqual(result, {"status": "received", "execution": "unavailable"})
            with closing(sqlite3.connect(self.db)) as db:
                self.assertEqual(
                    db.execute("SELECT status FROM signals").fetchall(), [("received",)]
                )
        finally:
            proc.terminate()
            shutdown_timeout = False
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                shutdown_timeout = True
                proc.kill()
                out, err = proc.communicate(timeout=5)
            self.assertNotIn(self.secret.encode(), out + err)
            self.assertFalse(shutdown_timeout, "listener did not terminate within its grace period")

    @contextmanager
    def bounded_listener(self, *, gate=None):
        ready, stop = threading.Event(), threading.Event()
        condition = threading.Condition()
        servers, failures = [], []
        base = getattr(webhook, "_WebhookHTTPServer", webhook.ThreadingHTTPServer)

        class ObservedServer(base):
            active = peak = 0

            def __init__(inner, *args, **kwargs):
                super().__init__(*args, **kwargs)
                servers.append(inner)
                ready.set()

            def finish_request(inner, request, address):
                with condition:
                    inner.active += 1
                    inner.peak = max(inner.peak, inner.active)
                    condition.notify_all()
                try:
                    if gate is not None:
                        gate.wait(3)
                    return super().finish_request(request, address)
                finally:
                    with condition:
                        inner.active -= 1
                        condition.notify_all()

        def processor(*args, **kwargs):
            stop.wait(5)
            raise RuntimeError("stop isolated test listener")

        def run():
            try:
                serve(self.db, self.secret, port, venue=object(),
                      portfolio_id="test-account", processor=processor)
            except RuntimeError as exc:
                if str(exc) != "venue_worker_failed":
                    failures.append(exc)
            except Exception as exc:  # noqa: BLE001 - report isolated server thread failures
                failures.append(exc)

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with (
            patch.object(webhook, "HTTP_TIMEOUT", 0.15, create=True),
            patch.object(webhook, "MAX_HTTP_WORKERS", 2, create=True),
            patch.object(webhook, "ThreadingHTTPServer", ObservedServer),
            patch.object(webhook, "_WebhookHTTPServer", ObservedServer, create=True),
        ):
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            try:
                self.assertTrue(ready.wait(2), failures)
                yield port, servers[0], condition
            finally:
                if gate is not None:
                    gate.set()
                stop.set()
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertFalse(failures)

    def test_idle_and_incomplete_headers_have_a_socket_deadline(self):
        for payload in (b"", b"POST /tradingview HTTP/1.1\r\nHost: "):
            with (
                self.subTest(payload=payload),
                self.bounded_listener() as (port, _, _),
                socket.create_connection(("127.0.0.1", port), timeout=1) as client,
            ):
                if payload:
                    client.sendall(payload)
                self.assertEqual(client.recv(1), b"")
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM signals").fetchone()[0], 0)

    def test_saturation_refuses_extra_connection_and_releases_capacity(self):
        gate = threading.Event()
        with self.bounded_listener(gate=gate) as (port, server, condition):
            clients = [socket.create_connection(("127.0.0.1", port), timeout=1)
                       for _ in range(2)]
            try:
                with condition:
                    self.assertTrue(condition.wait_for(lambda: server.active == 2, timeout=2))
                with socket.create_connection(("127.0.0.1", port), timeout=1) as extra:
                    try:
                        self.assertEqual(extra.recv(1), b"")
                    except ConnectionResetError:
                        pass  # Saturation may reset or close the unparsed socket.
                self.assertEqual(server.peak, 2)
            finally:
                gate.set()
                for client in clients:
                    client.close()
            with condition:
                self.assertTrue(condition.wait_for(lambda: server.active == 0, timeout=2))
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/tradingview",
                data=json.dumps({**self.event, "timestamp": int(time.time())}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=1) as response:
                self.assertEqual(response.status, 202)
                self.assertEqual(json.load(response)["status"], "received")
            self.assertLessEqual(server.peak, 2)

    def test_rejects_bad_secret_stale_and_unknown_fields(self):
        for change in (
            {"secret": "wrong"},
            {"timestamp": 699},
            {"timestamp": 1031},
            {"side": "short"},
            {"extra": 1},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.send(**change)
        self.assertFalse(self.db.exists())

    def test_unexpected_worker_failure_stops_receiver_and_surfaces_failure(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]

        def malformed_upstream(*args, **kwargs):
            raise AttributeError("untrusted upstream payload with private data")

        with self.assertRaisesRegex(RuntimeError, "^venue_worker_failed$"):
            serve(
                self.db,
                self.secret,
                port,
                venue=object(),
                portfolio_id="test-account",
                processor=malformed_upstream,
            )


if __name__ == "__main__":
    unittest.main()
