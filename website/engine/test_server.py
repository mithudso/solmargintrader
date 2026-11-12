from __future__ import annotations

import hashlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from backtester.core.data import frame_to_arrays
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import build
from backtester.core.types import Mode
from oracle.engine import OracleEngine
from oracle.tests.test_core import observation
from website.engine.server import (
    Analysis,
    DeadlineReader,
    RequestError,
    Server,
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
        response = self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold", "interval": "1d", "capital": 25000, "leverage": 2})
        expected = run_backtest(build("buy_and_hold"), frame_to_arrays(frame), EngineConfig(interval="1d", initial_capital=25000, leverage=2, mode=Mode.PERP, allow_short=True))
        self.assertEqual(response["metrics"]["final_equity"], expected.metrics.final_equity)
        self.assertGreater(response["metrics"]["total_fees"], 0)
        self.assertEqual(response["provenance"]["bars"], 100)
        self.assertEqual(response["provenance"]["fillDelay"], 1)
        self.assertNotEqual(response["metrics"]["final_equity"], run_backtest(build("buy_and_hold"), frame_to_arrays(frame), EngineConfig(interval="1d")).metrics.final_equity)

    def test_future_csv_tail_does_not_displace_completed_bars(self):
        frame = self.bars()
        cutoff = int(frame.timestamp.iloc[-1]) + 86400
        with mock.patch("website.engine.server.time.time", return_value=cutoff), mock.patch("website.engine.server.MAX_BARS", 100):
            before = self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold", "interval": "1d"})
            future = frame.copy()
            future.timestamp += 100 * 86400
            pd.concat([frame, future]).to_csv(self.analysis.data_dir / "SOL_1d.csv", index=False)
            after = self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold", "interval": "1d"})
        self.assertEqual(before["metrics"], after["metrics"])
        self.assertEqual(before["provenance"]["barsSha256"], after["provenance"]["barsSha256"])

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

        with mock.patch("website.engine.server.catalogue") as dispatch:
            for credentials in ("Bearer wrong", "Basic " + self.token, "Bearer", self.token):
                self.assertEqual(self.request("/v1/strategies", headers={"Authorization": credentials})[0], 401)
            dispatch.assert_not_called()

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


class OfflineBoundaryTests(unittest.TestCase):
    def test_drip_header_and_body_share_an_absolute_deadline(self):
        clock = iter(range(20))
        connection = mock.Mock()
        reader = DeadlineReader(io.BytesIO(b"x" * 100), connection, clock=lambda: next(clock))
        with self.assertRaises(TimeoutError):
            reader.readline(100)
        self.assertEqual(connection.settimeout.call_args_list[0].args, (9,))
        self.assertEqual(connection.settimeout.call_args_list[-1].args, (1,))

    def test_handler_slots_are_acquired_before_thread_creation_and_released(self):
        server = Server.__new__(Server)
        server.handler_slots = threading.BoundedSemaphore(1)
        server.shutdown_request = mock.Mock()
        with mock.patch("http.server.ThreadingHTTPServer.process_request") as spawn:
            server.process_request("first", ("synthetic", 1))
            server.process_request("second", ("synthetic", 2))
            spawn.assert_called_once_with("first", ("synthetic", 1))
            server.shutdown_request.assert_called_once_with("second")
        with (mock.patch("http.server.ThreadingHTTPServer.process_request_thread", side_effect=RuntimeError),
              self.assertRaises(RuntimeError)):
            server.process_request_thread("first", ("synthetic", 1))
        self.assertTrue(server.handler_slots.acquire(blocking=False))

    def test_present_but_wrong_credentials_never_dispatch(self):
        # Capture the actual Handler without constructing a socket/listener.
        with mock.patch("website.engine.server.Server") as constructor:
            make_server(mock.Mock(), "x" * 32)
        handler_type = constructor.call_args.args[1]
        handler = handler_type.__new__(handler_type)
        handler.command, handler.path = "GET", "/v1/strategies"
        handler.respond = mock.Mock()
        with mock.patch("website.engine.server.catalogue") as dispatch:
            for credentials in ("Bearer wrong", "Basic " + "x" * 32, "Bearer", "x" * 32, ""):
                handler.headers = {"Authorization": credentials}
                handler.handle_request()
                self.assertEqual(handler.respond.call_args.args[0], 401)
            dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
