"""Private state failures and slow history streams use disposable fixtures only."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from soltui import config, wallet
from soltui import prediction_recovery as recovery
from soltui import wallet_activity as activity


class RecoveryTransportResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.enterContext(patch.object(config, "CONFIG_DIR", self.root))
        self.plan = {"assets": ["SOL"]}

    def test_corrupt_or_unreadable_existing_control_denies_even_manual_acquire(self):
        recovery.directory().mkdir()
        control = recovery.directory() / "control.json"
        for raw in ("{broken", "[]", "null"):
            control.write_text(raw)
            for manual in (False, True):
                with (
                    self.subTest(raw=raw, manual=manual),
                    patch.object(recovery, "_acquire") as acquire,
                    patch.object(recovery.subprocess, "Popen") as spawn,
                ):
                    self.assertIsNone(
                        recovery.acquire(self.plan, "fixture", manual=manual)
                    )
                    result = recovery.ensure("SOL", lambda: self.plan, manual=manual)
                    self.assertEqual(result["state"], "failed")
                    self.assertFalse(result["can_start"])
                acquire.assert_not_called()
                spawn.assert_not_called()
        with patch.object(
            Path, "read_text", side_effect=PermissionError("private fixture canary")
        ):
            self.assertIsNone(recovery.acquire(self.plan, "fixture", manual=True))
            result = recovery.ensure("SOL", lambda: self.plan, manual=True)
        self.assertNotIn("private fixture canary", json.dumps(result))

    def test_lost_control_stops_monitor_with_observable_fixed_error(self):
        lease = recovery.acquire(self.plan, "fixture")
        self.assertIsNotNone(lease)
        self.addCleanup(lease.finish)
        recovery._write("control.json", {"paused": False})
        stop = threading.Event()
        lease.watch(stop)
        (recovery.directory() / "control.json").write_text("{broken")
        self.assertTrue(stop.wait(2))
        self.assertEqual(lease.metadata["last_error"], "prediction_control_unavailable")
        lease.finish()
        self.assertEqual(lease.metadata["last_error"], "prediction_control_unavailable")

    def test_initial_absence_and_valid_manual_resume_still_work(self):
        lease = recovery.acquire(self.plan, "fixture")
        self.assertIsNotNone(lease)
        lease.finish()
        recovery.pause()
        self.assertIsNone(recovery.acquire(self.plan, "fixture"))
        lease = recovery.acquire(self.plan, "fixture", manual=True)
        self.assertIsNotNone(lease)
        self.addCleanup(lease.finish)
        self.assertFalse(recovery.paused())

    def slow_server(self):
        class Slow(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.end_headers()
                for _ in range(100):
                    try:
                        self.wfile.write(b" ")
                        self.wfile.flush()
                    except OSError:
                        break
                    time.sleep(0.02)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Slow)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(
            lambda: (server.shutdown(), server.server_close(), thread.join(2))
        )
        return f"http://127.0.0.1:{server.server_port}"

    def test_history_drip_stops_at_absolute_budget(self):
        with patch.object(wallet, "SOLANA_RPC", self.slow_server()):
            before = time.monotonic()
            with self.assertRaises((TimeoutError, ValueError, OSError)):
                activity._rpc("getSignaturesForAddress", ["fixture"], 0.12)
            self.assertLess(time.monotonic() - before, 0.6)

    def test_cancelled_solana_read_retains_independent_base_result(self):
        stop = threading.Event()
        timer = threading.Timer(0.1, stop.set)
        timer.start()
        self.addCleanup(timer.join)
        settings = config.Settings()
        tx = "0x" + "1" * 64

        def query(sql, timeout):
            return (
                [
                    {
                        "transaction_hash": tx,
                        "occurred_at": "2026-11-08T23:00:00Z",
                        "sender": settings.base_address.lower(),
                        "recipient": "0x" + "a" * 40,
                        "chain_action": 1,
                    }
                ]
                if "base.transactions" in sql
                else []
            )

        with patch.object(wallet, "SOLANA_RPC", self.slow_server()):
            before = time.monotonic()
            result = activity.snapshot(settings, query=query, stop=stop)
        self.assertLess(time.monotonic() - before, 0.7)
        self.assertTrue(any(row["chain"] == "base" for row in result["items"]))
        self.assertEqual(
            next(row for row in result["coverage"] if row["chain"] == "solana")[
                "state"
            ],
            "unavailable",
        )
