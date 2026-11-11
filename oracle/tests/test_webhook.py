from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from contextlib import closing
from pathlib import Path

from oracle.webhook import accept_signal


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
            out, err = proc.communicate(timeout=5)
            self.assertNotIn(self.secret.encode(), out + err)

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


if __name__ == "__main__":
    unittest.main()
