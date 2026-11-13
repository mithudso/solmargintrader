"""Real isolated HTTP checks; no third-party SDK, wallet or order is executed."""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from contextlib import closing
from pathlib import Path

from ecosystem.swap_web import make_server


class SwapWebTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server(port=0)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True
        )
        self.thread.start()
        self.addCleanup(self.close_server)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

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

    def test_public_health_has_no_owner_or_execution_capability(self):
        status, headers, raw = self.request("/health")
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertTrue(body["data"]["isolated_origin"])
        self.assertTrue(body["data"]["public_configuration_only"])
        self.assertFalse(body["data"]["owner_controls"])
        self.assertFalse(body["data"]["server_can_sign_or_submit"])
        self.assertNotIn("Set-Cookie", headers)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertIn(
            "connect-src 'self' https: wss:", headers["Content-Security-Policy"]
        )
        self.assertIn(
            "frame-ancestors http://127.0.0.1:*", headers["Content-Security-Policy"]
        )

    def test_page_contains_only_local_script_until_manual_action(self):
        status, _, raw = self.request("/")
        self.assertEqual(status, 200)
        html = raw.decode()
        self.assertIn('src="/swap.js"', html)
        self.assertNotIn('src="https://', html)
        self.assertIn("Powered by", html)
        self.assertIn('min="50" max="255" step="1" value="50"', html)
        self.assertIn("50 bps = 0.5%", html)
        _, _, raw = self.request("/swap.js")
        js = raw.decode()
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("window.parent", js)
        self.assertNotIn("signTransaction(", js)
        self.assertNotIn("sendRawTransaction(", js)
        self.assertIn('addEventListener("click", loadManually)', js)
        self.assertIn("autoConnect: false", js)

    def test_public_config_does_not_read_headers_or_environment_values(self):
        status, _, raw = self.request(
            "/config",
            headers={
                "Authorization": "secret-canary",
                "Cookie": "control_session=private-canary",
            },
        )
        self.assertEqual(status, 200)
        self.assertNotIn(b"secret-canary", raw)
        self.assertNotIn(b"private-canary", raw)
        self.assertNotIn(b"supervisor_token", raw)
        self.assertNotIn(b"manager_home", raw)
        body = json.loads(raw)["data"]
        self.assertEqual(body["default_referral_fee_bps"], 50)
        self.assertTrue(body["default_fee_supported"])
        self.assertEqual(body["integration_status"], "available")
        self.assertIsNone(body["integration_reason"])
        self.assertFalse(body["live_ready"])
        status, _, raw = self.request("/config?asset=BTC")
        self.assertEqual(status, 200)
        self.assertIsNone(json.loads(raw)["data"]["initial_input_mint"])

    def test_no_owner_or_order_paths_or_write_methods(self):
        for path in (
            "/api/status",
            "/api/actions",
            "/api/order",
            "/api/session",
            "/state.json",
            "/../state.json",
            "/%2e%2e/state.json",
            "/app.js",
            "/styles.css",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"):
            with self.subTest(method=method):
                self.assertEqual(self.request("/", method=method)[0], 405)

    def test_rebinding_foreign_origins_and_invalid_queries_are_refused(self):
        for headers in (
            {"Host": "attacker.example"},
            {"Origin": "http://127.0.0.1:9999"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/config", headers=headers)[0], 403)
        self.assertEqual(
            self.request("/config", headers={"Origin": self.origin})[0], 200
        )
        for path in (
            "/?asset=../SOL",
            "/config?secret=abc",
            "/config?asset=SOL&asset=USDC",
            "/swap.js?asset=SOL",
            "/config?asset=SOL%00",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 400)

    def test_head_and_missing_assets_are_bounded(self):
        status, _, raw = self.request("/", method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(raw, b"")
        self.assertEqual(self.request("/favicon.ico")[0], 204)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertTrue((Path(__file__).parents[1] / "web/swap.html").is_file())


if __name__ == "__main__":
    unittest.main()
