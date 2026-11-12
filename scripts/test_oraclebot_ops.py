"""Synthetic observer transitions, retry delivery and independent outage checks."""

import importlib.util
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ops = load("oraclebot_ops")
watchdog = load("oraclebot_watchdog")


def health(ready=True):
    return {
        "ready": ready,
        "overall": "up" if ready else "down",
        "components": {
            key: {
                "ready": ready,
                "state": "up" if ready else "down",
                "reason": "available" if ready else "missing",
            }
            for key in ops.COMPONENTS
        },
    }


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "operations"
        self.db = ops.database(self.home)
        self.addCleanup(self.db.close)

    def test_debounce_and_recovery_are_durable(self):
        ops.record(self.db, health(False), 10)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 0
        )
        self.db.close()
        self.db = ops.database(self.home)
        self.addCleanup(self.db.close)
        ops.record(self.db, health(False), 70)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 4
        )
        ops.record(self.db, health(False), 130)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 4
        )
        ops.record(self.db, health(), 190)
        ops.record(self.db, health(), 250)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 8
        )
        actions = [
            json.loads(row[0])["action"]
            for row in self.db.execute("SELECT payload FROM outbox")
        ]
        self.assertEqual(actions.count("resolve"), 4)

    def test_authenticated_delivery_retries_same_id_after_http_failure(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                requests.append(
                    (
                        self.headers["Idempotency-Key"],
                        self.headers["Authorization"],
                        raw,
                    )
                )
                self.send_response(503 if len(requests) == 1 else 202)
                self.end_headers()
                self.wfile.write(b'{"accepted":true}')

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        credential = self.home / "service.env"
        credential.write_text("ALERTLANE_INGEST_TOKEN=" + "x" * 40 + "\n")
        credential.chmod(0o600)
        config = {
            "alertlane_url": f"http://127.0.0.1:{server.server_port}",
            "alertlane_env": str(credential),
        }
        payload = {
            "key": "oraclebot:suite",
            "action": "trigger",
            "title": "Synthetic",
            "body": "Synthetic",
            "severity": "critical",
        }
        with self.db:
            self.db.execute(
                "INSERT INTO outbox(id,payload) VALUES(?,?)",
                ("test-episode", json.dumps(payload)),
            )
        with patch.object(ops, "notify", return_value=True) as notify:
            self.assertEqual(ops.deliver(self.db, config)["pending"], 1)
            self.assertEqual(ops.deliver(self.db, config)["pending"], 0)
            self.assertEqual(notify.call_count, 1)
        self.assertEqual(requests[0], requests[1])
        self.assertTrue(requests[0][1].startswith("Bearer "))

    def test_late_local_failure_banner_cannot_follow_recovery(self):
        ops.record(self.db, health(False), 10)
        ops.record(self.db, health(False), 70)
        config = {
            "alertlane_url": "http://127.0.0.1:1",
            "alertlane_env": "/synthetic/env",
        }
        with (
            patch.object(ops, "notify", return_value=False),
            patch.object(ops, "send_alert"),
            patch.object(ops, "ingest_token", return_value="synthetic"),
        ):
            self.assertEqual(ops.deliver(self.db, config)["notification_pending"], 4)
        ops.record(self.db, health(), 130)
        ops.record(self.db, health(), 190)
        with (
            patch.object(ops, "notify", return_value=True) as notify,
            patch.object(ops, "send_alert") as remote,
            patch.object(ops, "ingest_token", return_value="synthetic"),
        ):
            result = ops.deliver(self.db, config)
        self.assertEqual(result["pending"], 0)
        self.assertEqual(remote.call_count, 4)
        self.assertEqual(notify.call_count, 4)
        self.assertTrue(
            all("recovered" in call.args[0] for call in notify.call_args_list)
        )

    def test_reports_do_not_claim_full_window_uptime(self):
        now = time.time()
        ops.record(self.db, health(), now)
        with patch.object(ops, "notify"):
            ops.reports(self.db, self.home, health(), {"pending": 0}, now)
        report = json.loads((self.home / "reports/latest.json").read_text())
        self.assertEqual(report["observed_checks"], 1)
        self.assertEqual(report["ready_checks"], 1)
        self.assertIsNone(report["max_gap_seconds"])
        self.assertNotIn("uptime_percent", report)
        self.assertIn("not continuous uptime", report["limits"][0])

    def test_secret_file_requires_private_permissions(self):
        credential = self.home / "service.env"
        credential.write_text("ALERTLANE_INGEST_TOKEN=" + "x" * 40)
        credential.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "private_credential"):
            ops.ingest_token(credential)

    def test_probe_refuses_stale_or_invalid_output(self):
        output = {"ok": True, "data": {**health(), "observed_at": time.time() - 120}}

        class Completed:
            returncode = 0
            stdout = json.dumps(output)

        with patch.object(ops.subprocess, "run", return_value=Completed()):
            self.assertFalse(ops.probe("/synthetic/solbot")["ready"])

    def test_symlink_database_is_refused(self):
        other = self.home / "other"
        other.write_text("untouched")
        self.db.close()
        (self.home / "state.sqlite3").unlink()
        (self.home / "state.sqlite3").symlink_to(other)
        with self.assertRaisesRegex(ValueError, "unsafe_monitor_file"):
            ops.database(self.home)
        self.assertEqual(other.read_text(), "untouched")


class IndependentWatchdogTests(unittest.TestCase):
    def test_missing_future_nonfinite_and_old_heartbeats_fail(self):
        for raw in (
            "",
            "{}",
            "null",
            "[]",
            '{"at":NaN}',
            '{"at":1200,"ready":true}',
            '{"at":0,"ready":true}',
            '{"at":1000,"ready":1}',
        ):
            with self.subTest(raw=raw):
                self.assertFalse(watchdog.assess(raw, now=1000)[0])
        self.assertTrue(watchdog.assess('{"at":999,"ready":true}', now=1000)[0])

    def test_website_storage_failure_does_not_report_healthy(self):
        with patch.object(watchdog.urllib.request, "urlopen") as opener:
            response = opener.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b'{"status":"ok","storage":false}'
            self.assertEqual(watchdog.website_health()["status"], "unavailable")

    def test_unconfigured_engine_remains_separate_from_website_liveness(self):
        with patch.object(watchdog.urllib.request, "urlopen") as opener:
            response = opener.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = (
                b'{"status":"ok","storage":true,"engine":false}'
            )
            result = watchdog.website_health()
            self.assertEqual(result["status"], "ok")
            self.assertFalse(result["engine"])
            request = opener.call_args.args[0]
            self.assertEqual(
                request.get_header("User-agent"), "Oraclebot-Operations/1.0"
            )
            self.assertFalse(request.has_header("Authorization"))

    def test_incident_deduplicates_and_resolves_only_owned_issue(self):
        calls = []
        owned = {
            "number": 5,
            "title": watchdog.TITLE,
            "body": watchdog.MARKER + "\nreason",
        }
        unrelated = {"number": 6, "title": watchdog.TITLE, "body": "manual note"}
        rows = []

        def api(path, payload=None, method=None):
            calls.append((path, payload, method))
            return (
                {"number": 5} if method == "POST" and path.endswith("/issues") else rows
            )

        self.assertEqual(
            watchdog.reconcile(
                "owner/repo", False, "stale", "https://example.test/run", api
            )["action"],
            "opened",
        )
        rows[:] = [owned, unrelated]
        self.assertEqual(
            watchdog.reconcile(
                "owner/repo", False, "stale", "https://example.test/run", api
            )["action"],
            "unchanged",
        )
        self.assertEqual(
            watchdog.reconcile(
                "owner/repo", True, "ok", "https://example.test/run", api
            )["issues"],
            [5],
        )
        self.assertFalse(any("/6" in call[0] for call in calls))

    def test_acceptance_incident_is_isolated_from_real_incident(self):
        calls = []

        def api(path, payload=None, method=None):
            calls.append((path, payload, method))
            return (
                {"number": 7}
                if method == "POST"
                else [{"number": 5, "title": watchdog.TITLE, "body": watchdog.MARKER}]
            )

        result = watchdog.reconcile(
            "owner/repo",
            False,
            "synthetic",
            "https://example.test",
            api,
            acceptance=True,
        )
        self.assertEqual(result["issue"], 7)
        self.assertIn("acceptance test", calls[-1][1]["title"])


if __name__ == "__main__":
    unittest.main()
