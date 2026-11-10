"""Collector endpoints preserve compact, inert and origin-bound contracts."""

from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem.web import make_server


class MachineHealthHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "ecosystem"
        self.manager = Path(self.temp.name) / "manager"
        self.server = make_server(self.home, self.manager, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def request(self, path, *, method="GET", headers=None):
        with closing(http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )) as connection:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def test_component_health_is_read_only_and_distinct_from_status(self):
        status, _, raw = self.request("/api/health")
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["schema_version"], 1)
        self.assertIn("components", body["data"])
        self.assertNotIn("bots", body["data"])
        self.assertFalse(self.home.exists())
        self.assertFalse(self.manager.exists())
        status, headers, raw = self.request("/metrics")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", headers["Content-Type"])
        self.assertIn(b"# HELP", raw)
        self.assertNotIn(b"NaN", raw)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.manager.exists())

    def test_process_liveness_does_not_claim_component_readiness(self):
        status, _, raw = self.request("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["data"]["scope"], "control_room_process")
        status, _, raw = self.request("/readyz")
        self.assertEqual(status, 503)
        body = json.loads(raw)
        self.assertFalse(body["ok"])
        self.assertFalse(body["data"]["availability_ready"])

    def test_readiness_excludes_market_quality_and_unknown_owners_refuse(self):
        snapshot = {
            "schema_version": 1, "observed_at": 1, "overall": "degraded",
            "components": {
                **{name: {"state": "up", "ready": True} for name in
                   ("suite", "manager", "control_room")},
                "market_data": {"state": "unknown", "ready": None},
            },
        }
        with patch("ecosystem.web._component_health", return_value=snapshot):
            status, _, raw = self.request("/readyz")
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(raw)["data"]["availability_ready"])
            snapshot["components"]["manager"] = {"state": "unknown", "ready": None}
            self.assertEqual(self.request("/readyz")[0], 503)

    def test_collector_routes_keep_origin_and_query_guards(self):
        for route in ("/api/health", "/metrics", "/readyz", "/healthz"):
            with self.subTest(route=route):
                self.assertEqual(self.request(route, headers={"Origin": "null"})[0], 403)
                self.assertEqual(self.request(route + "?path=/private")[0], 400)
                self.assertEqual(self.request(route, method="POST")[0], 404)

    def test_head_metrics_has_no_body_and_owner_failure_never_leaks(self):
        status, headers, raw = self.request("/metrics", method="HEAD")
        self.assertEqual(status, 200)
        self.assertTrue(int(headers["Content-Length"]) > 0)
        self.assertEqual(raw, b"")
        with patch("ecosystem.web._component_health", side_effect=RuntimeError("secret-canary")):
            status, _, raw = self.request("/api/health")
            self.assertEqual(status, 503)
            self.assertNotIn(b"secret-canary", raw)


if __name__ == "__main__":
    unittest.main()
