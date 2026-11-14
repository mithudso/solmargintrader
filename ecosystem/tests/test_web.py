"""Actual loopback HTTP checks; synthetic owner records are test fixtures only."""

from __future__ import annotations

import http.client
import json
import socket
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem.web import make_server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "absent"
        self.server = make_server(self.home, port=0)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True
        )
        self.thread.start()
        self.addCleanup(self.close_server)
        self.host = f"127.0.0.1:{self.server.server_port}"

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def request(self, path, *, method="GET", headers=None):
        with closing(
            http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        ) as connection:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def body(self, path, **kwargs):
        status, headers, raw = self.request(path, **kwargs)
        return status, headers, json.loads(raw)

    def test_binds_loopback_before_health_and_real_server_responds(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.body("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["status"], "listening")
        self.assertEqual(body["data"]["port"], self.server.server_port)
        self.assertFalse(body["data"]["read_only"])
        self.assertFalse(body["data"]["orders_available"])
        self.assertEqual(body["data"]["scope"], "paper_controls")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn(
            "style-src-attr 'unsafe-inline'", headers["Content-Security-Policy"]
        )
        self.assertIn(
            "sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY=",
            headers["Content-Security-Policy"],
        )
        self.assertNotIn(
            "script-src 'self' 'unsafe-inline'", headers["Content-Security-Policy"]
        )
        self.assertFalse(self.home.exists())

    def test_missing_owners_are_explicit_without_starting_anything(self):
        _, _, status = self.body("/api/status")
        self.assertEqual(status["data"]["phase"], "not_initialized")
        self.assertFalse(status["data"]["supervisor_running"])
        _, _, registrations = self.body("/api/registrations")
        self.assertEqual(registrations["data"]["status"], "unavailable")
        _, _, telemetry = self.body("/api/telemetry")
        self.assertEqual(telemetry["data"]["status"], "unavailable")
        self.assertFalse(self.home.exists())

    def test_status_route_uses_readonly_forward_timing_projection(self):
        observation = {
            "phase": "running",
            "batch": {"forward_checks": [{
                "message": "Waiting for existing forecast window",
                "owner_message": "Forecast window elapsed during calculation",
                "timing": {"state": "pending_not_due", "read_only_projection": True},
            }]},
        }
        with patch("ecosystem.control.ControlPlane.pipeline_status", return_value=observation) as owner:
            status, _, body = self.body("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"], observation)
        owner.assert_called_once_with(None)
        self.assertFalse(self.home.exists())

    def test_static_assets_are_local_and_have_no_operational_fixture_data(self):
        status, _, raw = self.request("/")
        self.assertEqual(status, 200)
        html = raw.decode()
        self.assertIn("Your bots, in motion.", html)
        self.assertIn("Unavailable", html)
        self.assertNotIn("$10,000", html)
        self.assertNotIn("equity-line", html)
        self.assertIn("https://www.tradingview.com/chart/qV1poosp/", html)
        self.assertNotIn("s3.tradingview.com", html)
        self.assertIn("/oracle-chart.js", html)
        self.assertIn("TradingView Lightweight Charts", html)
        status, _, raw = self.request("/app.js")
        self.assertEqual(status, 200)
        self.assertNotIn("innerHTML", raw.decode())
        self.assertIn("textContent", raw.decode())
        self.assertIn("state.eventCursor", raw.decode())
        status, _, chart = self.request("/oracle-chart.js")
        self.assertEqual(status, 200)
        self.assertIn("createSeriesMarkers", chart.decode())
        status, headers, chartlib = self.request("/lightweight-charts.mjs")
        self.assertEqual(status, 200)
        self.assertIn("text/javascript", headers["Content-Type"])
        self.assertIn('"5.2.1"', chartlib.decode())
        status, _, css = self.request("/styles.css")
        self.assertEqual(status, 200)
        source = Path(__file__).parents[2] / "docs/design/bot-control-room/mockup.css"
        self.assertTrue(css.startswith(source.read_bytes()))

    def test_tradingview_origin_is_allowed_only_for_an_isolated_frame(self):
        _, headers, _ = self.request("/")
        csp = headers["Content-Security-Policy"]
        self.assertIn("script-src 'self';", csp)
        self.assertIn("connect-src 'self';", csp)
        self.assertIn(
            "frame-src http://127.0.0.1:* https://www.tradingview-widget.com", csp
        )
        self.assertNotIn("https://*.tradingview", csp)
        status, _, script = self.request("/tradingview-chart.js")
        self.assertEqual(status, 200)
        self.assertNotIn("/api/", script.decode())
        self.assertNotIn("fetch(", script.decode())

    def test_static_traversal_and_raw_logs_are_not_routes(self):
        for target in (
            "/../state.json",
            "/%2e%2e/state.json",
            "/web/../runner.py",
            "/api/order",
        ):
            with self.subTest(target=target):
                self.assertEqual(self.body(target)[0], 404)

    def test_log_reader_rejects_arbitrary_paths(self):
        self.assertEqual(self.body("/api/logs?path=/tmp/private")[0], 400)

    def test_rejects_rebinding_cross_origin_and_cross_site(self):
        for headers in (
            {"Host": "attacker.example"},
            {"Origin": "http://attacker.example"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(headers=headers):
                status, _, body = self.body("/health", headers=headers)
                self.assertEqual(status, 403)
                self.assertEqual(body["error"], "local_origin_required")
        self.assertEqual(
            self.body("/health", headers={"Origin": f"http://{self.host}"})[0], 200
        )

    def test_rejects_duplicate_host_headers(self):
        with closing(
            http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        ) as connection:
            connection.putrequest("GET", "/health")
            connection.putheader("Host", self.host)
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()

    def test_mutating_methods_never_call_owners(self):
        with patch("ecosystem.control.runner.status") as owner:
            for method in ("PUT", "PATCH", "DELETE", "OPTIONS"):
                self.assertEqual(self.body("/api/status", method=method)[0], 405)
            self.assertEqual(self.body("/api/status", method="POST")[0], 404)
            owner.assert_not_called()

    def test_query_validation_is_bounded_and_strict(self):
        invalid = (
            "/api/registrations?limit=0",
            "/api/registrations?limit=1001",
            "/api/registrations?limit=1&limit=2",
            "/api/registrations?after=not-a-uuid",
            "/api/registrations?unknown=value",
            "/api/telemetry?after=-1",
            "/api/telemetry?after=1.5",
            "/api/telemetry?limit=0",
            "/api/telemetry?after=1&after=2",
            "/api/telemetry?raw=true",
            "/api/status?raw=true",
            "/health?x",
        )
        for target in invalid:
            with self.subTest(target=target):
                self.assertEqual(self.body(target)[0], 400)

    def test_oracle_display_query_routes_only_to_readonly_report(self):
        with patch(
            "ecosystem.votes.report", return_value={"status": "unavailable"}
        ) as owner:
            self.assertEqual(
                self.body(
                    "/api/oracle?instrument=ZEC%2FUSDT&interval=1h&strategy=macd"
                )[0],
                200,
            )
            owner.assert_called_once_with(
                self.home,
                "ZEC/USDT",
                interval="1h",
                strategy="macd",
                forecast_home=self.home,
            )
        self.assertEqual(self.body("/api/oracle?interval=1m&interval=1h")[0], 400)
        self.assertEqual(self.body("/api/oracle?strategy=rsi&unknown=x")[0], 400)

    def test_selected_research_oracle_keeps_primary_forecast_owner(self):
        from ecosystem.control import database

        run_id = "selected-research"
        selected_home = self.home / "research" / run_id
        selected_home.mkdir(parents=True)
        with database(self.home) as db:
            db.execute(
                "INSERT INTO experiment VALUES(?,?,?,?)",
                (run_id, "Selected research fixture", str(selected_home), 1000),
            )
        self.assertEqual(self.server.controls.experiment_home(run_id), selected_home)
        self.assertNotEqual(selected_home, self.server.controls.home)

        with patch(
            "ecosystem.votes.report", return_value={"status": "unavailable"}
        ) as owner:
            status, _, body = self.body(
                f"/api/oracle?run_id={run_id}&instrument=ZEC%2FUSDT"
                "&interval=17s&strategy=macd"
            )
            self.assertEqual(status, 200)
            self.assertTrue(body["ok"])
            owner.assert_called_once_with(
                selected_home,
                "ZEC/USDT",
                interval="17s",
                strategy="macd",
                forecast_home=self.home,
            )

    def test_passes_registration_and_event_cursors_to_existing_owners(self):
        cursor = "00000000-0000-0000-0000-000000000001"
        with patch(
            "ecosystem.web.registration.read_registrations", return_value={"bots": []}
        ) as owner:
            self.assertEqual(
                self.body(f"/api/registrations?limit=17&after={cursor}")[0], 200
            )
            owner.assert_called_once_with(self.home, limit=17, after=cursor)
        with patch("ecosystem.web._telemetry", return_value={"events": []}) as owner:
            self.assertEqual(self.body("/api/telemetry?after=101&limit=13")[0], 200)
            owner.assert_called_once_with(self.home, None, after=101, limit=13)

    def test_secret_redaction_adversarial_content_and_fixed_owner_errors(self):
        record = {
            "phase": "backtesting",
            "api_key": "test-secret-value",
            "nested": [{"private_key": "test-private-value"}],
            "strategy": "<img src=x onerror=alert(1)>",
        }
        with patch("ecosystem.control.runner.status", return_value=record):
            status, _, body = self.body("/api/status")
        self.assertEqual(status, 200)
        raw = json.dumps(body)
        self.assertNotIn("test-secret-value", raw)
        self.assertNotIn("test-private-value", raw)
        self.assertEqual(body["data"]["strategy"], record["strategy"])
        with (
            patch(
                "ecosystem.control.runner.status", side_effect=RuntimeError("secret error")
            ),
            self.assertLogs("ecosystem.web", level="WARNING") as logged,
        ):
            status, _, body = self.body("/api/status")
        self.assertEqual(status, 503)
        self.assertNotIn("secret error", json.dumps(body))
        record = json.loads(logged.records[0].getMessage())
        self.assertEqual(record["event"], "ecosystem_owner_unavailable")
        self.assertEqual(record["operation"], "read_owner_data")
        self.assertEqual(record["error_type"], "RuntimeError")
        self.assertEqual(logged.records[0].levelname, "WARNING")
        self.assertNotIn("secret error", " ".join(logged.output))

    def test_disconnect_head_and_restart(self):
        connection = socket.create_connection(("127.0.0.1", self.server.server_port))
        connection.sendall(b"GET /health HTTP/1.1\r\n")
        connection.close()
        status, headers, raw = self.request("/health", method="HEAD")
        self.assertEqual(status, 200)
        self.assertGreater(int(headers["Content-Length"]), 0)
        self.assertEqual(raw, b"")
        second = make_server(self.home, port=0)
        with second:
            self.assertEqual(second.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
