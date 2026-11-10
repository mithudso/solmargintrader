from __future__ import annotations

import http.client
import json
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from ecosystem.web import make_server


class ControlHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "control"
        self.server = make_server(
            self.home, manager_home=Path(self.temp.name) / "manager", port=0
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.nonce = self.request("/api/session")[1]["data"]["csrf_nonce"]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def request(self, target, *, method="GET", body=None, headers=None):
        with closing(
            http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        ) as connection:
            connection.request(method, target, body=body, headers=headers or {})
            response = connection.getresponse()
            data = response.read()
            self.assertNotIn("Access-Control-Allow-Origin", dict(response.getheaders()))
            return response.status, json.loads(data)

    def action(
        self, *, action="pnl.recording.set", params=None, identity=None, headers=None
    ):
        body = json.dumps(
            {
                "action": action,
                "request_id": identity or str(uuid4()),
                "params": {"enabled": False, "expected_revision": 0}
                if params is None
                else params,
            }
        )
        auth = {
            "Origin": self.origin,
            "X-Sol-CSRF": self.nonce,
            "Content-Type": "application/json",
        }
        auth.update(headers or {})
        return self.request("/api/actions", method="POST", body=body, headers=auth)

    def test_nonce_and_same_origin_are_both_required(self):
        for changes in (
            {"X-Sol-CSRF": "wrong"},
            {"Origin": "http://attacker.example"},
            {"Origin": "null"},
            {"Origin": ""},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(changes=changes):
                status, data = self.action(headers=changes)
                self.assertEqual(status, 403)
                self.assertFalse(data["ok"])
        self.assertFalse((self.home / "control.sqlite3").exists())

    def test_session_is_local_only_and_nonces_are_per_server(self):
        for headers in (
            {"Host": "attacker.example"},
            {"Origin": "http://attacker.example"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/session", headers=headers)[0], 403)
        other = make_server(
            Path(self.temp.name) / "other",
            manager_home=Path(self.temp.name) / "manager",
            port=0,
        )
        thread = threading.Thread(target=other.serve_forever, daemon=True)
        thread.start()
        try:
            with closing(
                http.client.HTTPConnection("127.0.0.1", other.server_port, timeout=3)
            ) as connection:
                connection.request("GET", "/api/session")
                nonce = json.loads(connection.getresponse().read())["data"][
                    "csrf_nonce"
                ]
                self.assertNotEqual(nonce, self.nonce)
        finally:
            other.shutdown()
            other.server_close()
            thread.join(timeout=3)

    def test_actual_mutation_receipt_polling_and_idempotent_reuse(self):
        identity = str(uuid4())
        status, response = self.action(identity=identity)
        self.assertEqual(status, 202)
        self.assertEqual(response["data"]["id"], identity)
        duplicate, _ = self.action(identity=identity)
        self.assertEqual(duplicate, 200)
        deadline = time.monotonic() + 3
        final = None
        while time.monotonic() < deadline:
            status, response = self.request(f"/api/actions?id={identity}")
            self.assertEqual(status, 200)
            final = response["data"]["action"]
            if final["state"] in ("succeeded", "failed"):
                break
            time.sleep(0.02)
        self.assertEqual(final["state"], "succeeded", final)
        self.assertFalse(final["result"]["enabled"])
        conflict, response = self.action(
            identity=identity, params={"enabled": True, "expected_revision": 0}
        )
        self.assertEqual(conflict, 400)
        self.assertFalse(response["ok"])

    def test_unknown_order_paths_and_actions_are_not_available(self):
        status, data = self.request("/api/order", method="POST", body="{}")
        self.assertEqual(status, 404)
        self.assertFalse(data["ok"])
        self.assertEqual(self.action(action="orders.submit", params={})[0], 400)
        self.assertEqual(
            self.action(action="manager.create", params={"mode": "live"})[0], 400
        )
        rejected, data = self.action(
            action="manager.create", params={"api_key": "do-not-echo"}
        )
        self.assertEqual(rejected, 400)
        self.assertNotIn("do-not-echo", json.dumps(data))

    def test_body_schema_size_encoding_and_content_type_fail_closed(self):
        headers = {
            "Origin": self.origin,
            "X-Sol-CSRF": self.nonce,
            "Content-Type": "application/json",
        }
        for body in (b"\xff", b"[]", b"{}", b"{", b"x" * 65537):
            with self.subTest(size=len(body)):
                self.assertEqual(
                    self.request(
                        "/api/actions", method="POST", body=body, headers=headers
                    )[0],
                    400,
                )
        for replacement in (
            {"Content-Type": "text/plain"},
            {"Content-Length": "invalid"},
            {"Transfer-Encoding": "chunked"},
        ):
            with self.subTest(replacement=replacement):
                self.assertEqual(
                    self.request(
                        "/api/actions",
                        method="POST",
                        body="{}",
                        headers={**headers, **replacement},
                    )[0],
                    400,
                )

    def test_unsupported_mutation_methods_and_traversal_are_refused(self):
        for method in ("PUT", "PATCH", "DELETE", "OPTIONS"):
            with self.subTest(method=method):
                self.assertEqual(self.request("/api/actions", method=method)[0], 405)
        for route in (
            "/api/actions?id=../secret",
            "/api/control?run_id=../secret",
            "/api/analytics?run_id=../secret",
            "/api/wiki/page?id=../secret",
        ):
            with self.subTest(route=route):
                self.assertIn(self.request(route)[0], (400, 404))
