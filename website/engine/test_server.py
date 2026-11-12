from __future__ import annotations

import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

import pandas as pd

from backtester.core.data import frame_to_arrays
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import build
from oracle.engine import OracleEngine
from oracle.tests.test_core import observation
from website.engine.server import (
    Analysis,
    RequestError,
    catalogue,
    choose_top,
    make_server,
)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.analysis = Analysis(self.root / "data", self.root / "oracle", oracle_quote="USDC")
        self.analysis.data_dir.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def bars(self):
        rows = [{"timestamp": 1600000000 + i * 86400, "open": 100 + i, "high": 102 + i,
                 "low": 99 + i, "close": 101 + i, "volume": 1000} for i in range(100)]
        frame = pd.DataFrame(rows)
        frame.to_csv(self.analysis.data_dir / "SOL_1d.csv", index=False)
        return frame

    def test_backtest_exactly_matches_canonical_costed_engine(self):
        frame = self.bars()
        response = self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold", "interval": "1d", "capital": 10000, "leverage": 1})
        expected = run_backtest(build("buy_and_hold"), frame_to_arrays(frame), EngineConfig(interval="1d"))
        self.assertEqual(response["metrics"]["final_equity"], expected.metrics.final_equity)
        self.assertGreater(response["metrics"]["total_fees"], 0)
        self.assertEqual(response["provenance"]["bars"], 100)
        self.assertEqual(response["provenance"]["fillDelay"], 1)

    def test_missing_cache_does_not_invent_data(self):
        with self.assertRaisesRegex(RequestError, "cached_history_unavailable"):
            self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold"})

    def test_gap_refuses_instead_of_compressing_time(self):
        frame = self.bars().drop(index=50)
        frame.to_csv(self.analysis.data_dir / "SOL_1d.csv", index=False)
        with self.assertRaisesRegex(RequestError, "history_or_strategy_not_usable"):
            self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold", "interval": "1d"})

    def test_path_and_numeric_injection_refused(self):
        for body in ({"coin": "../../private", "strategy": "buy_and_hold"},
                     {"coin": "SOL", "strategy": "buy_and_hold", "capital": float("nan")},
                     {"coin": "SOL", "strategy": "buy_and_hold", "leverage": True},
                     {"coin": "SOL", "strategy": "buy_and_hold", "path": "/private"}):
            with self.subTest(body=body), self.assertRaises(RequestError):
                self.analysis.backtest(body)

    def test_concurrent_backtest_refused(self):
        self.analysis.slot.acquire()
        try:
            with self.assertRaisesRegex(RequestError, "engine_busy"):
                self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold"})
        finally:
            self.analysis.slot.release()

    def test_oracle_reader_current_and_stale_archive_immutable(self):
        path = self.analysis.oracle_dir / "SOL/history.sqlite3"
        engine = OracleEngine(path, minimum_resolved=1)
        for i in range(65):
            engine.ingest(observation(i, price=100 + i), now=i * 60 + 1)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        current = self.analysis.oracle("SOL", now=64 * 60 + 1)
        self.assertEqual(current["status"], "available")
        self.assertEqual(current["topStrategy"]["direction"], "up")
        self.assertGreater(current["topStrategy"]["score"], 50)
        self.assertEqual(current["instrument"], "SOL/USDC")
        stale = self.analysis.oracle("SOL", now=65 * 60)
        self.assertEqual(stale["status"], "unavailable")
        self.assertIsNone(stale["topStrategy"])
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_and_wrong_instrument_archive_unavailable(self):
        self.assertIsNone(self.analysis.oracle("BTC")["topStrategy"])
        path = self.analysis.oracle_dir / "SOL/history.sqlite3"
        OracleEngine(path, instrument="SOL/USD")
        self.assertEqual(self.analysis.oracle("SOL")["reason"], "oracle_evidence_unavailable")

    def test_ranking_is_eligible_deterministic_and_not_ineligible_high_score(self):
        snap = {"status": "available", "aggregate": {"included": [{"strategy_id": "b"}, {"strategy_id": "a"}]},
                "strategies": [{"strategy_id": "b", "direction": -1, "confidence_percent": 60, "resolved": 30},
                               {"strategy_id": "a", "direction": 1, "confidence_percent": 60, "resolved": 30},
                               {"strategy_id": "unqualified", "direction": 1, "confidence_percent": 100, "resolved": 1}]}
        self.assertEqual(choose_top(snap, "SOL")["topStrategy"]["id"], "a")

    def test_catalog_exact_registry_and_readable_names(self):
        from backtester.core.strategies import REGISTRY
        result = catalogue()
        self.assertEqual({r["id"] for r in result["strategies"]}, set(REGISTRY))
        self.assertTrue(all(r["name"] and r["summary"] for r in result["strategies"]))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.analysis = Analysis(Path(cls.temp.name) / "data", Path(cls.temp.name) / "oracle")
        cls.token = "test-token-" + "x" * 32
        cls.server = make_server(cls.analysis, cls.token, port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, *, token=True, headers=None, method="GET", body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        merged = {"Authorization": f"Bearer {self.token}"} if token else {}
        merged.update(headers or {})
        conn.request(method, path, body=body, headers=merged)
        result = conn.getresponse()
        status, response = result.status, json.loads(result.read())
        conn.close()
        return status, response

    def test_auth_before_any_research_or_error(self):
        self.assertEqual(self.request("/v1/strategies", token=False)[0], 401)
        self.assertEqual(self.request("/v1/strategies")[0], 200)
        self.assertEqual(self.request("/v1/strategies", headers={"Origin": "https://malicious.invalid"})[0], 403)

    def test_no_execution_endpoint(self):
        self.assertEqual(self.request("/v1/orders", method="POST", body="{}")[0], 404)

    def test_missing_history_public_error_has_no_path(self):
        status, response = self.request("/v1/backtests", method="POST", headers={"Content-Type": "application/json"},
                                        body=json.dumps({"coin": "SOL", "strategy": "buy_and_hold"}))
        self.assertEqual(status, 503)
        self.assertEqual(response, {"error": "cached_history_unavailable"})

    def test_duplicate_oracle_query_refused(self):
        self.assertEqual(self.request("/v1/oracle?coin=SOL&coin=BTC")[0], 400)

    def test_short_token_cannot_start(self):
        with self.assertRaises(ValueError):
            make_server(self.analysis, "short", port=0)


if __name__ == "__main__":
    unittest.main()
