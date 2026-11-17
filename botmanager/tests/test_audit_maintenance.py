"""Bounded protocol and lifecycle regressions use inert subprocess/owner seams."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from botmanager.adapters import executor
from botmanager.domain import ManagerError

from botmanager import (
    blind,
    blind_judge,
    config,
    learning_job,
    research_owner,
    transport,
    worker,
)
from tests import test_blind as blind_fixtures
from tests import test_config as config_fixtures


class ProtocolMaintenanceTests(unittest.TestCase):
    def test_malformed_executor_error_becomes_unknown_without_retry(self):
        adapter = executor.ExecutorAdapter.__new__(executor.ExecutorAdapter)
        adapter.descriptor = {"home": "/synthetic", "interpreter": sys.executable}
        for error in ("bad", ["bad"], 7):
            reply = {
                "ok": False,
                "command": "manager.swap",
                "result": None,
                "error": error,
            }
            with (
                self.subTest(error=error),
                patch.object(
                    executor,
                    "bounded_process",
                    return_value=(1, json.dumps(reply).encode(), b""),
                ) as call,
            ):
                with self.assertRaises(ManagerError) as raised:
                    adapter._call("manager.swap", {})
                self.assertEqual(raised.exception.code, "executor_outcome_unknown")
                self.assertEqual(call.call_count, 1)

    def test_nonmapping_owner_result_is_a_controlled_protocol_failure(self):
        client = research_owner.OwnerClient.__new__(research_owner.OwnerClient)
        client.descriptor = {
            "interpreter": sys.executable,
            "repository": "/",
            "config_root": "/synthetic",
            "authority": {},
            "expected_identity": {},
        }
        for result in (None, [], 7):
            reply = {
                "ok": True,
                "command": "research.protocol",
                "result": result,
                "error": None,
            }
            with (
                self.subTest(result=result),
                patch.object(
                    research_owner,
                    "bounded_process",
                    return_value=(0, json.dumps(reply).encode(), b""),
                ),
            ):
                with self.assertRaises(ManagerError) as raised:
                    client.call("learning-daily", {})
                self.assertEqual(raised.exception.code, "research_unavailable")

    def test_deep_frame_is_a_bounded_malformed_frame(self):
        connection = Mock()
        payload = b"[" * 10000 + b"0" + b"]" * 10000 + b"\n"
        connection.recv.side_effect = [
            payload[i : i + 4096] for i in range(0, len(payload), 4096)
        ]
        with (
            patch.object(transport.time, "monotonic", return_value=0),
            self.assertRaises(ValueError),
        ):
            transport._read(connection, transport.MAX_REQUEST, 10)

    def test_deep_learning_descriptor_never_starts_a_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "research-owner.json").write_text("[" * 10000 + "0" + "]" * 10000)
            job = learning_job.DailyLearningJob(home)
            with patch.object(
                learning_job.subprocess,
                "Popen",
                side_effect=AssertionError("helper escaped"),
            ) as launch:
                job.step()
                launch.assert_not_called()
            self.assertIsNone(job.process)
            self.assertEqual(job.receipt["reason"], "reviewed_owner_unavailable")

    def test_manual_override_can_complete_valid_shared_cross_field_values(self):
        shared = config_fixtures.learned(
            strategy_id="trend",
            strategy_version=config.STRATEGY_VERSIONS["trend"],
            context=dict(config.DEFAULT_CONTEXT, execution_model="next_open"),
            values={"fast_period": 40},
        )
        resolved = config.resolve_config("trend", {}, {"slow_period": 50}, shared)
        self.assertEqual(resolved.values["fast_period"], 40)
        self.assertEqual(resolved.values["slow_period"], 50)
        self.assertEqual(resolved.provenance["fast_period"]["source"], "shared")
        with self.assertRaises(ManagerError):
            config.resolve_config(
                "trend",
                {},
                {"slow_period": 50},
                {**shared, "values": {"fast_period": -1}},
            )

    def test_finite_large_returns_do_not_become_an_infinite_tie(self):
        packet = blind_fixtures.packet()
        for candidate, value in zip(packet["candidates"], (1e308, 1.5e308)):
            for cell in candidate["cells"]:
                cell["net_return"] = value
        decision = blind_judge.decide(packet)
        self.assertEqual(decision["tied_ids"], ["b" * 32])

    def test_special_owner_locks_are_opened_nonblocking_and_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "owner.lock"
            os.mkfifo(path)
            original = worker.os.open
            flags_seen = []

            def opened(name, flags, *args, **kwargs):
                flags_seen.append(flags)
                if not flags & os.O_NONBLOCK:
                    raise AssertionError("FIFO open would block")
                return original(name, flags, *args, **kwargs)

            with (
                patch.object(worker.os, "open", side_effect=opened),
                self.assertRaises(OSError),
            ):
                worker.lock_held(path)
            self.assertTrue(flags_seen)

    def test_owned_group_is_reaped_even_after_its_leader_exits(self):
        process = SimpleNamespace(
            pid=98765432,
            stdout=io.BytesIO(),
            stderr=io.BytesIO(),
            poll=Mock(return_value=0),
            wait=Mock(return_value=0),
        )
        selector = Mock()
        selector.get_map.return_value = {1: 1}
        with (
            patch.object(blind.subprocess, "Popen", return_value=process),
            patch.object(blind.selectors, "DefaultSelector") as factory,
            patch.object(blind.time, "monotonic", side_effect=[0, 2]),
            patch.object(blind.os, "killpg") as kill,
        ):
            factory.return_value.__enter__.return_value = selector
            with self.assertRaisesRegex(ValueError, "deadline"):
                blind.bounded_process([sys.executable], b"", cwd="/", env={}, timeout=1)
            kill.assert_called_once()
            self.assertEqual(kill.call_args.args[0], process.pid)

    def test_tilde_descriptor_repeated_setup_is_idempotent(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {"HOME": tmp}),
            patch.object(
                research_owner.OwnerClient,
                "call",
                return_value={
                    "canonical_authority": None,
                    "identity": {"version": "fixture"},
                },
            ),
        ):
            params = {
                "output": "~/descriptor.json",
                "config_root": tmp,
                "repository": tmp,
            }
            first = research_owner.prepare_descriptor(params, Path(tmp))
            second = research_owner.prepare_descriptor(params, Path(tmp))
            self.assertEqual(first["descriptor"], second["descriptor"])
            self.assertEqual(
                first["descriptor_path"], str(Path(tmp) / "descriptor.json")
            )

    def test_malformed_service_xml_is_a_controlled_refusal(self):
        import hashlib

        from botmanager import service

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            label = (
                "com.solmargintrader.solbot."
                + hashlib.sha256(str(root).encode()).hexdigest()[:12]
            )
            path = root / (label + ".plist")
            path.write_bytes(b'<?xml version="1.0"?><plist><dict>')
            with (
                patch.object(service.sys, "platform", "darwin"),
                patch.object(
                    service.subprocess,
                    "run",
                    side_effect=AssertionError("service boundary escaped"),
                ),
                self.assertRaises(ManagerError) as raised,
            ):
                service.service("uninstall", root, agents_dir=root)
            self.assertEqual(raised.exception.code, "service_unavailable")
            self.assertTrue(path.exists())

    def test_failed_alert_commit_does_not_consume_observation(self):
        from botmanager import suite

        with tempfile.TemporaryDirectory() as tmp:
            journal = suite.AlertJournal(Path(tmp))
            snapshot = {"observed_at": 100, "components": {"fixture": {}}}
            with patch.object(
                journal,
                "_observe_locked",
                side_effect=[OSError("synthetic full disk"), None],
            ) as write:
                with self.assertRaises(OSError):
                    journal.observe(snapshot)
                journal.observe(snapshot)
            self.assertEqual(write.call_count, 2)
            self.assertEqual(write.call_args.args[1], set())

    def test_explicit_failed_child_release_prevents_stopped_acknowledgement(self):
        from botmanager import suite, suite_service

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            failed = {
                "instance": "a" * 32,
                "state": "release_unconfirmed",
                "release_confirmed": False,
            }
            with (
                patch.object(suite, "_checkpoint", return_value=failed),
                patch.object(suite, "lock_held", return_value=False),
                patch.object(
                    suite_service, "operation", return_value={"installed": False}
                ),
            ):
                with self.assertRaises(ManagerError) as raised:
                    suite._stop(root, root / "ecosystem")
                self.assertEqual(raised.exception.code, "suite_unavailable")

    def test_healthy_journal_does_not_disable_the_monotonic_watchdog(self):
        from botmanager.supervisor import Supervisor

        with tempfile.TemporaryDirectory() as tmp:
            supervisor = Supervisor(Path(tmp))
            process = Mock()
            supervisor.children["fixture"] = (process, 7)
            supervisor._watchdogs["fixture"] = (process, 7, 10, "tick_stalled")
            with (
                patch("botmanager.supervisor.time.monotonic", return_value=11),
                patch.object(supervisor, "_journal_blocked", return_value=False),
                patch.object(supervisor, "_terminate", return_value=True) as terminate,
            ):
                supervisor._reap_blocked_owners()
            terminate.assert_called_once_with(process)
            self.assertNotIn("fixture", supervisor.children)
            self.assertEqual(
                supervisor._pending_failures["fixture"], (7, "tick_stalled")
            )

    def test_systemd_execstart_preserves_literal_dollar_paths(self):
        from botmanager import suite_service

        body = suite_service.definition(
            Path("/fixture/${HOME}/manager"),
            Path("/fixture/$DATA/ecosystem"),
            Path("/fixture/${HOME}/bin/solbot"),
            "linux",
        ).decode()
        line = next(line for line in body.splitlines() if line.startswith("ExecStart="))
        self.assertIn("$${HOME}", line)
        self.assertIn("$$DATA", line)
        environment = next(
            line
            for line in body.splitlines()
            if line.startswith('Environment="SOLBOT_HOME=')
        )
        self.assertIn("${HOME}", environment)
        self.assertNotIn("$${HOME}", environment)

    def test_stopping_registered_service_does_not_require_its_removed_launcher(self):
        from botmanager import suite_service
        from tests import test_suite_service as fixture_module

        fixture = fixture_module.SuiteServiceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.operation("install")
        with patch.object(
            suite_service,
            "installed_executable",
            side_effect=ManagerError("stable_install_required", "synthetic"),
        ):
            result = fixture.operation("stop")
        self.assertFalse(result["registered"])
        self.assertFalse(fixture.fixture.active)

    def test_prior_control_receipt_remains_valid_after_learning_adoption(self):
        from uuid import uuid4

        from tests import test_learning as fixture_module

        fixture = fixture_module.LearningTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request_id = str(uuid4())
        prior = fixture.ledger.control(fixture.spec, "stop", request_id)
        owner = fixture.receipt()
        fixture.ledger.learning_adopt(fixture.store, owner)
        self.assertEqual(
            fixture.ledger.control(fixture.spec, "stop", request_id), prior
        )
        self.assertTrue(fixture.ledger.history(fixture.spec.bot_id))

    def test_refused_browser_stop_cannot_revoke_a_pending_start(self):
        from tests import test_extension_adapter as fixture_module

        fixture = fixture_module.BrowserTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.poll()
        started = fixture.control()
        from uuid import uuid4

        stopped = fixture.store.control(
            fixture.owner["installation_id"],
            "stop",
            str(uuid4()),
            expected_generation=1,
            expected_config_hash=fixture.owner["config_hash"],
            now=100,
        )
        self.assertEqual(stopped["outcome"], "failed")
        self.assertEqual(
            fixture.store.receipt(started["request_id"])["outcome"], "pending"
        )

    def test_deep_legacy_reply_is_a_controlled_incompatible_owner(self):
        from botmanager.adapters import soltui

        from tests import test_legacy as fixture_module

        fixture = fixture_module.Legacy()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        adapter = fixture.adapter("http://127.0.0.1:1")
        connection = Mock()
        response = connection.getresponse.return_value
        response.status = 200
        response.read1.side_effect = [b"[" * 10000 + b"0" + b"]" * 10000, b""]
        with (
            patch.object(soltui.http.client, "HTTPConnection", return_value=connection),
            patch.object(soltui.threading, "Timer"),
            self.assertRaises(ManagerError) as raised,
        ):
            adapter._http("GET", "/v1/health")
        self.assertEqual(raised.exception.code, "incompatible_owner")
        connection.close.assert_called_once()

    def test_optimizer_cleanup_survives_supervisor_close_failure(self):
        from tests import test_load

        supervisor = Mock()
        supervisor.close.side_effect = RuntimeError("synthetic close failure")
        stop, optimizer = Mock(), Mock()
        optimizer.is_alive.return_value = True
        optimizer.exitcode = 0
        with self.assertRaisesRegex(RuntimeError, "close failure"):
            test_load._close_supervisor_and_optimizer(supervisor, stop, optimizer)
        stop.set.assert_called_once()
        optimizer.kill.assert_called_once()
        optimizer.close.assert_called_once()

    def test_cli_fixture_timeout_cleanup_kills_waits_and_closes_pipes(self):
        import subprocess

        from tests import test_editing

        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("fixture", 2), 0]
        test_editing._reap_edit_child(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)
        process.stdout.close.assert_called_once()
        process.stderr.close.assert_called_once()

    def test_crash_fixture_cleanup_reaps_stubborn_child_after_timeout(self):
        from tests import test_supervisor

        child = Mock()
        child.is_alive.side_effect = [True, True]
        test_supervisor._reap_crash_child(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.join.call_count, 2)
        child.close.assert_called_once()
