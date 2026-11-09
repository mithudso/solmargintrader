from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import time
import threading
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from backtester.core.kucoin_history import WINDOW, HistoryError, audit_store, collect, open_store, read_range


class Handler(BaseHTTPRequestHandler):
    requests = 0
    mode = "normal"
    active = 0
    max_active = 0
    guard = threading.Lock()
    barrier = None

    def log_message(self, *args):
        pass

    def do_GET(self):
        with type(self).guard:
            type(self).requests += 1
            request_number = type(self).requests
        if type(self).mode in {"race", "race-conflict"}:
            type(self).barrier.wait(timeout=5)
        if type(self).mode == "serialize":
            with type(self).guard:
                type(self).active += 1
                type(self).max_active = max(type(self).max_active, type(self).active)
            time.sleep(0.05)
        if type(self).mode == "retry" and type(self).requests == 1:
            self.send_response(429)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        params = parse_qs(urlparse(self.path).query)
        start, end = int(params["startAt"][0]), int(params["endAt"][0])
        rows = [[str(t), "10", "11", "12", "9", "5", "55"] for t in range(start, end, 60) if type(self).mode == "complete" or t != start + 60]
        if type(self).mode == "race-conflict" and request_number == 2:
            rows[0][2] = "10"
        if type(self).mode == "invalid":
            rows = [[str(start), "10", "11", "8", "9", "5", "55"]]
        body = json.dumps({"code": "200000", "data": rows}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
        if type(self).mode == "serialize":
            with type(self).guard:
                type(self).active -= 1


class KucoinHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/candles"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "data.sqlite"
        Handler.requests = 0; Handler.mode = "normal"; Handler.active = 0; Handler.max_active = 0

    def test_http_collection_and_gap_refusal(self):
        result = collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        self.assertEqual((result["bars"], result["missing_slots"]), (2, 1))
        self.assertEqual(read_range(self.db, "SOL-USDC", 0, 60)[0][4], 11.)
        with self.assertRaisesRegex(HistoryError, "missing candles"):
            read_range(self.db, "SOL-USDC", 0, 180)
        self.assertEqual(collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)["pages_reused"], 1)
        self.assertEqual(Handler.requests, 1)
        ledger = self.db.parent / "gaps.csv"
        audit = audit_store(self.db, "SOL-USDC", 0, 180, ledger)
        self.assertEqual((audit["bars"], audit["unobserved_slots"], audit["unfetched_slots"]), (2, 1, 0))
        self.assertIn("60,120,UNOBSERVED", ledger.read_text())
        original = ledger.read_bytes()
        with self.assertRaisesRegex(HistoryError, "overwrite"):
            audit_store(self.db, "SOL-USDC", 0, 180, ledger)
        self.assertEqual(ledger.read_bytes(), original)

    def test_exclusive_end_includes_last_requested_minute(self):
        Handler.mode = "complete"
        result = collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        self.assertEqual((result["bars"], result["missing_slots"]), (3, 0))
        self.assertEqual([r[0] for r in read_range(self.db, "SOL-USDC", 0, 180)], [0, 60, 120])

    def test_previous_schema_cannot_be_silently_reused(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT INTO metadata VALUES ('schema', '1')")
        self.db.chmod(0o600)
        with self.assertRaisesRegex(HistoryError, "metadata"):
            open_store(self.db, "SOL-USDC")

    def test_unfetched_window_is_distinct_from_omitted_bars(self):
        collect(self.db, "SOL-USDC", 0, WINDOW, base_url=self.url, delay=0)
        ledger = self.db.parent / "gaps.csv"
        result = audit_store(self.db, "SOL-USDC", 0, 2*WINDOW, ledger)
        self.assertEqual(result["pages_unfetched"], 1)
        self.assertEqual(result["unfetched_slots"], 1440)
        self.assertIn(f"{WINDOW},{2*WINDOW},UNFETCHED", ledger.read_text())

    def test_invalid_page_rolls_back(self):
        Handler.mode = "invalid"
        with self.assertRaises(HistoryError):
            collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM pages").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM candles").fetchone()[0], 0)

    def test_overlapping_page_is_not_accepted(self):
        collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        raw = b'{"code":"200000","data":[]}'
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("INSERT INTO pages VALUES (?,?,?,?,?)", (30, 90, 1, hashlib.sha256(raw).hexdigest(), raw))
        with self.assertRaisesRegex(HistoryError, "overlapping"):
            read_range(self.db, "SOL-USDC", 0, 180)
        with self.assertRaisesRegex(HistoryError, "overlapping"):
            audit_store(self.db, "SOL-USDC", 0, 180, self.db.parent / "gaps.csv")

    def test_normalized_tampering_refuses_read_and_resume(self):
        collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE candles SET close=99 WHERE ts=0")
        with self.assertRaisesRegex(HistoryError, "differ"):
            read_range(self.db, "SOL-USDC", 0, 60)
        with self.assertRaisesRegex(HistoryError, "differ"):
            collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)

    def test_concurrent_collectors_reuse_identical_page(self):
        with closing(open_store(self.db, "SOL-USDC")):
            pass
        Handler.mode = "race"; Handler.barrier = threading.Barrier(2)
        results = []; errors = []
        def run():
            try: results.append(collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0))
            except Exception as exc: errors.append(exc)
        with patch.dict(os.environ, {"KUCOIN_HTTP_LOCK": ""}):
            workers = [threading.Thread(target=run) for _ in range(2)]
            for worker in workers: worker.start()
            for worker in workers: worker.join()
        self.assertFalse(errors)
        self.assertEqual(sum(r["pages_fetched"] for r in results), 1)
        self.assertEqual(sum(r["pages_reused"] for r in results), 1)
        self.assertEqual(len(read_range(self.db, "SOL-USDC", 0, 60)), 1)

    def test_concurrent_conflicting_page_is_rejected(self):
        with closing(open_store(self.db, "SOL-USDC")):
            pass
        Handler.mode = "race-conflict"; Handler.barrier = threading.Barrier(2)
        results = []; errors = []
        def run():
            try: results.append(collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0))
            except Exception as exc: errors.append(exc)
        with patch.dict(os.environ, {"KUCOIN_HTTP_LOCK": ""}):
            workers = [threading.Thread(target=run) for _ in range(2)]
            for worker in workers: worker.start()
            for worker in workers: worker.join()
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], HistoryError)
        self.assertIn("conflicts", str(errors[0]))

    def test_shared_http_lock_is_private(self):
        lock = self.db.parent / "limiter.lock"
        with patch.dict(os.environ, {"KUCOIN_HTTP_LOCK": str(lock)}):
            collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        self.assertEqual(lock.stat().st_mode & 0o777, 0o600)

    def test_shared_lock_serializes_parallel_http_requests(self):
        Handler.mode = "serialize"
        lock = self.db.parent / "limiter.lock"
        errors = []
        def run(name):
            try:
                collect(self.db.parent / (name + ".sqlite"), name + "-USDC", 0, 180, base_url=self.url, delay=0)
            except Exception as exc:
                errors.append(exc)
        with patch.dict(os.environ, {"KUCOIN_HTTP_LOCK": str(lock)}):
            workers = [threading.Thread(target=run, args=(name,)) for name in ("SOL", "BTC")]
            for worker in workers: worker.start()
            for worker in workers: worker.join()
        self.assertFalse(errors)
        self.assertEqual(Handler.max_active, 1)

    def test_retry_429_uses_real_http(self):
        Handler.mode = "retry"
        with patch("backtester.core.kucoin_history.time.sleep"):
            collect(self.db, "SOL-USDC", 0, 180, base_url=self.url, delay=0)
        self.assertEqual(Handler.requests, 2)


if __name__ == "__main__":
    unittest.main()
