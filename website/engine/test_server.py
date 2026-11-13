from __future__ import annotations

import hashlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

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
    main,
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

    def test_huge_integers_are_rejected_as_invalid_input(self):
        for field in ("capital", "leverage"):
            with self.subTest(field=field), self.assertRaisesRegex(RequestError, "invalid_capital_or_leverage"):
                self.analysis.backtest({"coin": "SOL", "strategy": "buy_and_hold", field: 10 ** 1000})

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
        with self.assertLogs("website.engine.server", level="WARNING") as logs:
            self.assertEqual(self.analysis.oracle("SOL")["reason"], "oracle_evidence_unavailable")
        event = json.loads(logs.records[0].getMessage())
        self.assertEqual(event["event"], "analysis_oracle_unavailable")
        self.assertEqual(event["coin"], "SOL")
        self.assertNotIn(str(path), "\n".join(logs.output))

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
        try:
            conn.request(method, path, body=body, headers=merged)
            result = conn.getresponse()
            return result.status, json.loads(result.read())
        finally:
            conn.close()

    def test_auth_before_any_research_or_error(self):
        secret = "secret-not-for-logs"
        with self.assertLogs("website.engine.server", level="INFO") as logs:
            self.assertEqual(self.request(f"/v1/strategies?token={secret}", headers={"Authorization": f"Bearer {secret}"})[0], 401)
            self.assertEqual(self.request("/v1/strategies")[0], 200)
            self.assertEqual(self.request("/v1/strategies", headers={"Origin": f"https://{secret}.invalid"})[0], 403)
        events = [json.loads(record.getMessage()) for record in logs.records]
        self.assertEqual([event["status"] for event in events], [401, 200, 403])
        self.assertTrue(all(event["event"] == "analysis_http_response" for event in events))
        self.assertNotIn(secret, "\n".join(logs.output))
        self.assertNotIn(self.token, "\n".join(logs.output))

    def test_malformed_request_target_has_a_symbolic_error(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            # Bypass the client's own URL parser to exercise the server boundary.
            conn.putrequest("GET", "http://[broken", skip_host=True)
            conn.putheader("Authorization", f"Bearer {self.token}")
            conn.endheaders()
            response = conn.getresponse()
            self.assertEqual((response.status, json.loads(response.read())),
                             (400, {"error": "invalid_request"}))
        finally:
            conn.close()

    def test_unexpected_failure_logs_safe_context_and_keeps_response_symbolic(self):
        detail = "/private/secret-provider-token"
        with mock.patch.object(self.analysis, "oracle", side_effect=RuntimeError(detail)), \
                self.assertLogs("website.engine.server", level="WARNING") as logs:
            status, response = self.request("/v1/oracle?coin=SOL")
        self.assertEqual((status, response), (503, {"error": "analysis_unavailable"}))
        events = [json.loads(record.getMessage()) for record in logs.records]
        failure = next(event for event in events if event["event"] == "analysis_request_failed")
        self.assertEqual(failure["operation"], "oracle")
        self.assertEqual(failure["error_type"], "RuntimeError")
        self.assertNotIn(detail, "\n".join(logs.output))
        self.assertNotIn(self.token, "\n".join(logs.output))

    def test_body_limit_refuses_before_analysis(self):
        with mock.patch.object(self.analysis, "backtest") as backtest:
            status, response = self.request("/v1/backtests", method="POST", body="x" * 4097,
                                            headers={"Content-Type": "application/json"})
        self.assertEqual((status, response), (413, {"error": "invalid_body_size"}))
        backtest.assert_not_called()

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

    def test_cli_invalid_configuration_reports_usage_without_starting(self):
        cases = (({"ENGINE_TOKEN": "short"}, [], "ENGINE_TOKEN"),
                 ({"ENGINE_ORACLE_QUOTE": "EUR"}, [], "unsupported_oracle_quote"),
                 ({}, ["--port", "-1"], "--port"))
        for changes, arguments, message in cases:
            stderr = io.StringIO()
            environment = {"ENGINE_DATA_DIR": self.temp.name, "ENGINE_ORACLE_DIR": self.temp.name,
                           "ENGINE_TOKEN": self.token, "ENGINE_ORACLE_QUOTE": "USD", **changes}
            with self.subTest(message=message):
                with mock.patch.dict("os.environ", environment), \
                        mock.patch("sys.argv", ["analysis-server", *arguments]), redirect_stderr(stderr), \
                        mock.patch("website.engine.server.make_server") as make, \
                        self.assertRaises(SystemExit) as exited:
                    main()
                make.assert_not_called()
                self.assertEqual(exited.exception.code, 2)
                self.assertIn(message, stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_help_explains_environment_and_gives_an_example(self):
        stdout = io.StringIO()
        with mock.patch("sys.argv", ["analysis-server", "--help"]), redirect_stdout(stdout), \
                self.assertRaises(SystemExit) as exited:
            main()
        self.assertEqual(exited.exception.code, 0)
        for text in ("Example:", "ENGINE_DATA_DIR", "ENGINE_ORACLE_DIR", "ENGINE_TOKEN"):
            self.assertIn(text, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
