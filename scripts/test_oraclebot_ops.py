"""Synthetic observer transitions, retry delivery and independent outage checks."""

import contextlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import threading
import time
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


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

        with patch.object(ops, "probe_output", return_value=Completed.stdout):
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


class ObserverBoundaryTests(unittest.TestCase):
    def test_non_object_accepted_json_is_refused_as_delivery_error(self):
        for body in (b"[]", b"null", b"1", b'"accepted"'):
            with self.subTest(body=body):
                response = MagicMock(status=202)
                response.read.return_value = body
                response.__enter__.return_value = response
                opener = MagicMock()
                opener.open.return_value = response
                with (
                    patch.object(
                        ops.urllib.request, "build_opener", return_value=opener
                    ),
                    self.assertRaises(ValueError),
                ):
                    ops.send_alert(
                        "https://alerts.invalid", "synthetic-token", "event", {}
                    )

    def test_non_regular_credentials_refuse_before_open_or_read(self):
        for mode in (stat.S_IFIFO, stat.S_IFCHR, stat.S_IFDIR):
            with self.subTest(mode=mode):
                path = MagicMock()
                info = types.SimpleNamespace(
                    st_uid=ops.os.getuid(), st_mode=mode | 0o600, st_size=50
                )
                path.is_symlink.return_value = False
                path.stat.return_value = info
                path.lstat.return_value = info
                path.read_text.return_value = "ALERTLANE_INGEST_TOKEN=" + "x" * 40
                with (
                    patch.object(
                        ops.os,
                        "open",
                        side_effect=AssertionError("non-regular file opened"),
                    ),
                    self.assertRaises(ValueError),
                ):
                    ops.ingest_token(path)
                path.read_text.assert_not_called()

    def test_health_flood_uses_bounded_stream_and_cleans_owned_process(self):
        child = MagicMock()
        child.stdout.fileno.return_value = 101
        child.stderr.fileno.return_value = 102
        child.poll.return_value = None
        child.wait.return_value = -9
        child.__enter__.return_value = child
        selector = MagicMock()
        selector.__enter__.return_value = selector
        selector.get_map.return_value = {101: object(), 102: object()}
        selector.select.return_value = [
            (types.SimpleNamespace(fd=101, data="stdout"), 1)
        ]
        import selectors

        with (
            patch.object(
                ops.subprocess,
                "run",
                side_effect=AssertionError("unbounded capture forbidden"),
            ),
            patch.object(ops.subprocess, "Popen", return_value=child),
            patch.object(selectors, "DefaultSelector", return_value=selector),
            patch.object(ops.os, "set_blocking"),
            patch.object(
                ops.os, "read", side_effect=[b"x" * 65536, b"x" * 65536, b"x"]
            ),
        ):
            result = ops.probe("/synthetic/solbot")
        self.assertFalse(result["ready"])
        self.assertEqual(result["components"]["suite"]["reason"], "probe_unavailable")
        child.kill.assert_called_once_with()
        child.wait.assert_called()

    def test_oversized_integer_probe_time_refuses_as_unknown(self):
        raw = json.dumps(
            {
                "ok": True,
                "data": {
                    "observed_at": 10**400,
                    "ready": True,
                    "components": {key: {"ready": True} for key in ops.COMPONENTS},
                },
            }
        )
        with patch.object(ops, "probe_output", return_value=raw):
            self.assertFalse(ops.probe("/synthetic/solbot")["ready"])

    def test_missing_install_arguments_refuse_before_database(self):
        with (
            patch.object(
                ops, "database", side_effect=AssertionError("database touched")
            ),
            patch.object(ops.os, "umask"),
            patch("sys.stderr", new_callable=io.StringIO),
            self.assertRaises(SystemExit) as error,
        ):
            ops.main(["install", "--home", "/synthetic/monitor"])
        self.assertEqual(error.exception.code, 2)

    def test_missing_status_is_a_friendly_prerequisite_exit(self):
        with (
            patch.object(
                Path,
                "read_text",
                side_effect=FileNotFoundError("synthetic missing status"),
            ),
            patch.object(ops.os, "umask"),
            patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            result = ops.main(["status", "--home", "/synthetic/monitor"])
        self.assertEqual(result, 3)
        self.assertIn("prerequisite", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class ObserverPositiveControls(unittest.TestCase):
    def test_bounded_probe_accepts_current_valid_health_and_discards_stderr(self):
        valid = {
            "ok": True,
            "data": {
                "observed_at": 1000,
                "ready": True,
                "overall": "up",
                "components": {
                    key: {"ready": True, "state": "up", "reason": "synthetic"}
                    for key in ops.COMPONENTS
                },
            },
        }
        output = {
            101: bytearray(json.dumps(valid).encode()),
            102: bytearray(b"synthetic diagnostics"),
        }
        child = MagicMock()
        child.stdout.fileno.return_value = 101
        child.stderr.fileno.return_value = 102
        child.poll.return_value = 0
        child.wait.return_value = 0
        child.__enter__.return_value = child

        class Selector:
            def __init__(self):
                self.rows = {}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def register(self, pipe, events, name):
                fd = pipe.fileno()
                self.rows[fd] = types.SimpleNamespace(fd=fd, data=name)

            def unregister(self, fd):
                del self.rows[fd]

            def get_map(self):
                return self.rows

            def select(self, timeout):
                return [(key, 1) for key in list(self.rows.values())]

        def read(fd, maximum):
            chunk = bytes(output[fd][:maximum])
            del output[fd][:maximum]
            return chunk

        import selectors

        with (
            patch.object(ops.subprocess, "Popen", return_value=child),
            patch.object(
                ops.subprocess,
                "run",
                side_effect=AssertionError("unbounded capture forbidden"),
            ),
            patch.object(selectors, "DefaultSelector", Selector),
            patch.object(ops.os, "set_blocking"),
            patch.object(ops.os, "read", side_effect=read),
            patch.object(ops.time, "time", return_value=1000),
        ):
            result = ops.probe("/synthetic/solbot")
        self.assertTrue(result["ready"])
        self.assertEqual(result["components"]["suite"]["reason"], "synthetic")
        child.kill.assert_not_called()

    def test_credential_fd_type_race_refuses_and_closes(self):
        path = MagicMock()
        regular = types.SimpleNamespace(
            st_uid=ops.os.getuid(), st_mode=stat.S_IFREG | 0o600, st_size=50
        )
        fifo = types.SimpleNamespace(
            st_uid=ops.os.getuid(), st_mode=stat.S_IFIFO | 0o600, st_size=0
        )
        path.lstat.return_value = regular
        with (
            patch.object(ops.os, "open", return_value=99) as opened,
            patch.object(ops.os, "fstat", return_value=fifo),
            patch.object(ops.os, "close") as closed,
            patch.object(
                ops.os, "fdopen", side_effect=AssertionError("unsafe fd read")
            ),
            self.assertRaises(ValueError),
        ):
            ops.ingest_token(path)
        flags = opened.call_args.args[1]
        self.assertTrue(flags & ops.os.O_NONBLOCK)
        self.assertTrue(flags & ops.os.O_NOFOLLOW)
        closed.assert_called_once_with(99)

    def test_regular_private_bounded_credential_parses(self):
        path = MagicMock()
        raw = (
            b'OTHER=synthetic\nALERTLANE_INGEST_TOKEN="'
            + b"x" * 40
            + b'" # synthetic\n'
        )
        info = types.SimpleNamespace(
            st_uid=ops.os.getuid(), st_mode=stat.S_IFREG | 0o600, st_size=len(raw)
        )
        path.lstat.return_value = info
        with (
            patch.object(ops.os, "open", return_value=99),
            patch.object(ops.os, "fstat", return_value=info),
            patch.object(ops.os, "fdopen", return_value=io.BytesIO(raw)),
            patch.object(ops.os, "close") as close,
        ):
            self.assertEqual(ops.ingest_token(path), "x" * 40)
        close.assert_not_called()

    def test_oversize_credential_refuses_before_open(self):
        path = MagicMock()
        path.lstat.return_value = types.SimpleNamespace(
            st_uid=ops.os.getuid(), st_mode=stat.S_IFREG | 0o600, st_size=65537
        )
        with (
            patch.object(
                ops.os, "open", side_effect=AssertionError("oversize file opened")
            ),
            self.assertRaises(ValueError),
        ):
            ops.ingest_token(path)

    def test_probe_byte_budget_is_shared_by_both_streams(self):
        child = MagicMock()
        child.stdout.fileno.return_value = 101
        child.stderr.fileno.return_value = 102
        child.poll.return_value = None
        child.__enter__.return_value = child
        import selectors

        selector = MagicMock()
        selector.__enter__.return_value = selector
        selector.get_map.return_value = {101: object(), 102: object()}
        selector.select.return_value = [
            (types.SimpleNamespace(fd=101, data="stdout"), 1),
            (types.SimpleNamespace(fd=102, data="stderr"), 1),
        ]
        with (
            patch.object(ops.subprocess, "Popen", return_value=child),
            patch.object(selectors, "DefaultSelector", return_value=selector),
            patch.object(ops.os, "set_blocking"),
            patch.object(ops.os, "read", side_effect=[b"abc", b"xyz"]) as read,
            self.assertRaisesRegex(ValueError, "probe_output_limit"),
        ):
            ops.probe_output("/synthetic/solbot", limit=5)
        self.assertEqual(
            [call.args for call in read.call_args_list], [(101, 6), (102, 3)]
        )
        child.kill.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=1)

    def test_probe_deadline_stops_only_its_child(self):
        child = MagicMock()
        child.stdout.fileno.return_value = 101
        child.stderr.fileno.return_value = 102
        child.poll.return_value = None
        child.__enter__.return_value = child
        import selectors

        selector = MagicMock()
        selector.__enter__.return_value = selector
        selector.get_map.return_value = {101: object()}
        with (
            patch.object(ops.subprocess, "Popen", return_value=child),
            patch.object(selectors, "DefaultSelector", return_value=selector),
            patch.object(ops.os, "set_blocking"),
            patch.object(ops.time, "monotonic", side_effect=[10, 26]),
            self.assertRaisesRegex(ValueError, "probe_timeout"),
        ):
            ops.probe_output("/synthetic/solbot")
        selector.select.assert_not_called()
        child.kill.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=1)


class _WatchdogBoundaryResponse:
    status = 200

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return self.data


class IndependentWatchdogBoundaryTests(unittest.TestCase):
    def call_main(self, argv, environment=None):
        env = (
            {
                "GH_TOKEN": "synthetic-token",
                "GITHUB_REPOSITORY": "synthetic/repo",
                "GITHUB_RUN_ID": "1",
                "GITHUB_STEP_SUMMARY": "/synthetic-summary",
                "ORACLEBOT_HEARTBEAT": json.dumps({"at": time.time(), "ready": True}),
            }
            if environment is None
            else environment
        )
        urls = []

        def response(request, **kwargs):
            url = getattr(request, "full_url", request)
            urls.append(url)
            if url == "https://oraclebot.io/api/health":
                return _WatchdogBoundaryResponse(b'{"status":"ok","storage":true}')
            if url.startswith("https://api.github.com/repos/synthetic/repo/issues?"):
                return _WatchdogBoundaryResponse(b"[]")
            raise AssertionError("unexpected mocked request shape")

        stdout, stderr = (io.StringIO(), io.StringIO())
        opened = mock_open()
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(sys, "argv", ["oraclebot_watchdog.py", *argv]),
            patch.object(watchdog.urllib.request, "urlopen", side_effect=response),
            patch("builtins.open", opened),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            try:
                code = watchdog.main()
            except SystemExit as exc:
                code = exc.code
        return (code, stdout.getvalue(), stderr.getvalue(), urls, opened.call_count)

    def test_nullable_matching_issue_is_ignored(self):
        calls = []

        def request(path, payload=None, method=None):
            calls.append((path, payload, method))
            return (
                {"number": 7}
                if method == "POST"
                else [{"number": 6, "title": watchdog.TITLE, "body": None}]
            )

        result = watchdog.reconcile(
            "synthetic/repo", False, "stale", "https://example.invalid/run", request
        )
        self.assertEqual(result, {"action": "opened", "issue": 7})
        self.assertEqual(len(calls), 2)
        self.assertFalse(any("/6" in row[0] for row in calls))

    def test_huge_integer_time_is_unavailable(self):
        self.assertEqual(
            watchdog.assess(json.dumps({"at": 10**400, "ready": True}), now=1000),
            (False, "heartbeat_unavailable", {}),
        )

    def test_help_has_no_effects(self):
        code, out, _err, urls, opened = self.call_main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("usage:", out)
        self.assertEqual(urls, [])
        self.assertEqual(opened, 0)

    def test_badargs_has_no_effects(self):
        code, _out, err, urls, opened = self.call_main(["--unknown"])
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)
        self.assertEqual(urls, [])
        self.assertEqual(opened, 0)

    def test_missing_ci_environment_preflights_before_effects(self):
        code, _out, err, urls, opened = self.call_main([], {})
        self.assertEqual(code, 3)
        for name in (
            "GH_TOKEN",
            "GITHUB_REPOSITORY",
            "GITHUB_RUN_ID",
            "GITHUB_STEP_SUMMARY",
        ):
            self.assertIn(name, err)
        self.assertIn("gh workflow run", err)
        self.assertEqual(urls, [])
        self.assertEqual(opened, 0)

    def test_invalid_acceptance_mode_precedes_effects(self):
        env = {
            "GH_TOKEN": "synthetic-token",
            "GITHUB_REPOSITORY": "synthetic/repo",
            "GITHUB_RUN_ID": "1",
            "GITHUB_STEP_SUMMARY": "/synthetic-summary",
            "ACCEPTANCE_MODE": "invalid",
        }
        code, _out, err, urls, opened = self.call_main([], env)
        self.assertEqual(code, 2)
        self.assertIn("ACCEPTANCE_MODE", err)
        self.assertEqual(urls, [])
        self.assertEqual(opened, 0)


class RemoteOrderTests(unittest.TestCase):
    def test_delayed_failure_cannot_reopen_after_remote_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            db = ops.database(Path(folder) / "synthetic-observer")
            self.addCleanup(db.close)

            def health(ready):
                return {
                    "ready": ready,
                    "components": {"suite": {"ready": ready, "reason": "synthetic"}},
                }

            ops.record(db, health(False), 10)
            ops.record(db, health(False), 70)
            ops.record(db, health(True), 130)
            ops.record(db, health(True), 190)
            attempts = []
            accepted = []

            def send(url, token, identifier, payload):
                attempts.append(payload["action"])
                if len(attempts) == 1:
                    raise OSError("synthetic retryable refusal")
                accepted.append(payload["action"])

            with (
                patch.object(ops, "notify", return_value=True),
                patch.object(ops, "ingest_token", return_value="synthetic-token"),
                patch.object(ops, "send_alert", side_effect=send),
            ):
                ops.deliver(
                    db,
                    {
                        "alertlane_url": "https://synthetic.invalid",
                        "alertlane_env": "/synthetic/not-read",
                    },
                )
                ops.deliver(
                    db,
                    {
                        "alertlane_url": "https://synthetic.invalid",
                        "alertlane_env": "/synthetic/not-read",
                    },
                )
            self.assertTrue(accepted)
            self.assertEqual(accepted[-1], "resolve", (attempts, accepted))
            stale_id, delivered = db.execute(
                "SELECT id,delivered FROM outbox ORDER BY rowid LIMIT 1"
            ).fetchone()
            self.assertEqual(
                delivered, 0, "superseded does not claim remote acceptance"
            )
            self.assertIsNotNone(
                db.execute(
                    "SELECT 1 FROM metadata WHERE key=?",
                    ("remote_superseded:" + stale_id,),
                ).fetchone()
            )


if __name__ == "__main__":
    unittest.main()
