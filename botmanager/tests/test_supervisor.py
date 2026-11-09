from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from botmanager.config import resolve_config
from botmanager.data import load_recording
from botmanager.domain import BotSpec, ManagerError
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore
from botmanager.supervisor import Supervisor
from botmanager.transport import request
from botmanager.worker import lifetime_lock, lock_held

from tests.test_paper import grid, recording


def stalled_worker(home, bot_id, generation, parent_pid):
    ledger = RuntimeLedger(Path(home))
    with lifetime_lock(Path(home) / "locks" / (bot_id + ".lock")):
        ledger.heartbeat(bot_id, generation, os.getpid())
        ledger.begin_tick(bot_id, generation)
        time.sleep(60)


def hard_crash(home, bot_id, generation, state, after):
    ledger = RuntimeLedger(Path(home))
    ledger.commit_tick(
        bot_id,
        generation,
        0,
        state,
        before_commit=None if after else lambda: os._exit(9),
    )
    os._exit(9)


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="solbot-test-")
        self.home = Path(self.tmp.name)
        self.ledger = RuntimeLedger(self.home)
        self.data = load_recording(recording(self.home))
        self.spec = grid("one")
        ManagerStore(self.home).create_spec(self.spec)
        self.ledger.register(self.spec, self.data)
        self.supervisor = None

    def tearDown(self):
        if self.supervisor:
            self.supervisor.close()
        self.tmp.cleanup()

    def start(self, spec=None):
        spec = spec or self.spec
        self.ledger.control(spec, "start", str(uuid4()))

    def spin(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.supervisor.step()
            if predicate():
                return
            time.sleep(0.03)
        self.fail("supervisor condition timed out")

    def test_two_instances_duplicate_start_and_stop_recovery(self):
        two = BotSpec.create(
            "two", "grid", resolve_config("grid", {}, {"range_pct": 25.0}, None)
        )
        ManagerStore(self.home).create_spec(two)
        self.ledger.register(two, self.data)
        self.start()
        self.start(two)
        self.supervisor = Supervisor(self.home).open()
        with self.assertRaises(ManagerError):
            Supervisor(self.home).open()
        self.spin(
            lambda: all(
                self.ledger.get(s.bot_id)["cursor"] == 8 for s in (self.spec, two)
            )
        )
        a = self.ledger.get(self.spec.bot_id)
        b = self.ledger.get(two.bot_id)
        self.assertNotEqual(a["runtime_id"], b["runtime_id"])
        self.assertNotEqual(a["checkpoint"]["lots"], b["checkpoint"]["lots"])
        pid = self.supervisor.children[self.spec.bot_id][0].pid
        self.start()
        self.supervisor.step()
        self.assertEqual(pid, self.supervisor.children[self.spec.bot_id][0].pid)
        status = dispatch(
            "status", {"identity": "one"}, CommandContext(home=self.home)
        )["data"]
        self.assertEqual(status["reason"], "reference_input_exhausted")
        self.assertTrue(status["process_health"]["worker_lock_held"])
        self.assertEqual(status["input_quality"]["state"], "reference_snapshot")
        self.ledger.control(self.spec, "stop", str(uuid4()))
        self.supervisor.step()
        self.assertEqual(self.ledger.get(self.spec.bot_id)["observed"], "stopped")
        self.supervisor.close()
        self.supervisor = Supervisor(self.home).open()
        self.spin(lambda: two.bot_id in self.supervisor.children)
        self.assertNotIn(self.spec.bot_id, self.supervisor.children)
        self.assertEqual(
            a["checkpoint"], self.ledger.get(self.spec.bot_id)["checkpoint"]
        )

    def test_dead_worker_restarts_without_duplicate_fills(self):
        self.start()
        self.supervisor = Supervisor(self.home).open()
        self.spin(lambda: self.ledger.get(self.spec.bot_id)["cursor"] == 8)
        before = self.ledger.get(self.spec.bot_id)
        process = self.supervisor.children[self.spec.bot_id][0]
        process.kill()
        process.join(2)
        self.supervisor.step()
        self.assertEqual(self.ledger.get(self.spec.bot_id)["reason"], "worker_exited")
        self.spin(
            lambda: (
                self.ledger.get(self.spec.bot_id)["generation"] > before["generation"]
                and self.ledger.get(self.spec.bot_id)["pid"] is not None
            )
        )
        self.spin(
            lambda: (
                self.ledger.get(self.spec.bot_id)["reason"]
                == "reference_input_exhausted"
            )
        )
        after = self.ledger.get(self.spec.bot_id)
        self.assertEqual(after["observed"], "waiting")
        self.assertLess(time.time() - after["heartbeat"], 2.0)
        self.assertEqual(after["checkpoint"], before["checkpoint"])
        self.assertEqual(after["evaluated"], before["evaluated"])
        self.assertEqual(
            self.ledger.fills(self.spec.bot_id), before["checkpoint"]["fills"]
        )

    def test_hung_tick_is_not_healthy_heartbeat(self):
        self.start()
        self.supervisor = Supervisor(self.home, worker_target=stalled_worker).open()
        self.spin(lambda: self.ledger.get(self.spec.bot_id)["tick_started"] is not None)
        with self.ledger.connection(True) as db:
            db.execute(
                "UPDATE runs SET tick_started=?,heartbeat=?",
                (time.time() - 16, time.time()),
            )
        status = dispatch(
            "status", {"identity": "one"}, CommandContext(home=self.home)
        )["data"]
        self.assertEqual(status["reason"], "tick_stalled")
        self.assertTrue(status["process_health"]["worker_lock_held"])
        self.supervisor.step()
        self.assertEqual(self.ledger.get(self.spec.bot_id)["reason"], "tick_stalled")
        self.assertEqual(self.ledger.get(self.spec.bot_id)["cursor"], 0)

    def test_three_failures_hold_and_resource_admission(self):
        self.start()
        for i in range(3):
            gen = self.ledger.claim(self.spec.bot_id, "test")
            self.ledger.failed(self.spec.bot_id, gen, "worker_exited")
            with self.ledger.connection(True) as db:
                db.execute("UPDATE runs SET retry_at=0")
        self.assertEqual(self.ledger.get(self.spec.bot_id)["observed"], "failed")
        with self.assertRaises(ManagerError):
            self.start()
        # Failed desired-running accounts still consume their admitted slot.
        for i in range(3):
            spec = grid("more" + str(i))
            self.ledger.register(spec, self.data)
            self.start(spec)
        fifth = grid("fifth")
        self.ledger.register(fifth, self.data)
        with self.assertRaises(ManagerError):
            self.start(fifth)

    def test_local_socket_dispatch_and_inert_service_status(self):
        self.supervisor = Supervisor(self.home).open()
        result = []
        thread = threading.Thread(
            target=lambda: result.append(
                request(
                    self.home, "start", {"identity": "one", "request_id": str(uuid4())}
                )
            )
        )
        thread.start()
        self.spin(lambda: bool(result))
        thread.join(2)
        self.assertTrue(result[0]["ok"])
        self.assertEqual(
            set(result[0]), {"schema_version", "request_id", "ok", "data", "error"}
        )
        self.assertEqual((self.home / "supervisor.sock").stat().st_mode & 0o777, 0o600)
        from botmanager.service import installed_executable, service

        absent = self.home / "absent"
        with patch("botmanager.service.subprocess.run") as run:
            status = service("status", absent, agents_dir=self.home / "agents")
            run.assert_not_called()
        self.assertFalse(status["installed"])
        self.assertFalse(absent.exists())
        with self.assertRaises(ManagerError):
            installed_executable()

    def test_process_crash_before_and_after_commit(self):
        import multiprocessing

        from botmanager.strategies.grid import evaluate

        self.start()
        generation = self.ledger.claim(self.spec.bot_id, "test")
        state = evaluate(self.spec, self.data, 4)
        context = multiprocessing.get_context("spawn")
        for after in (False, True):
            child = context.Process(
                target=hard_crash,
                args=(str(self.home), self.spec.bot_id, generation, state, after),
            )
            child.start()
            child.join(5)
            self.assertEqual(child.exitcode, 9)
            child.close()
            self.assertEqual(
                self.ledger.get(self.spec.bot_id)["cursor"], 4 if after else 0
            )
        self.ledger.recover("restart")
        generation = self.ledger.claim(self.spec.bot_id, "restart")
        final = evaluate(self.spec, self.data, 8)
        self.ledger.commit_tick(self.spec.bot_id, generation, 4, final)
        self.assertEqual(self.ledger.get(self.spec.bot_id)["checkpoint"], final)

    def test_supervisor_sigkill_orphan_fenced_and_stopped_intent(self):
        self.start()
        env = {**os.environ, "SOLBOT_HOME": str(self.home)}
        process = subprocess.Popen(
            [sys.executable, "-m", "botmanager", "daemon"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def wait_for(predicate, timeout=8):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(0.05)
            self.fail("daemon condition timed out")

        try:
            wait_for(lambda: self.ledger.get(self.spec.bot_id)["cursor"] == 8)
            saved = self.ledger.get(self.spec.bot_id)["checkpoint"]
            process.kill()
            process.wait(5)
            self.ledger.control(self.spec, "stop", str(uuid4()))
            self.supervisor = Supervisor(self.home).open()
            self.spin(
                lambda: (
                    not lock_held(self.home / "locks" / (self.spec.bot_id + ".lock"))
                ),
                timeout=8,
            )
            self.assertEqual(self.ledger.get(self.spec.bot_id)["desired"], "stopped")
            self.assertEqual(self.ledger.get(self.spec.bot_id)["checkpoint"], saved)
            self.assertNotIn(self.spec.bot_id, self.supervisor.children)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(5)

    def test_explicit_service_install_uninstall_in_isolated_directory(self):
        import plistlib

        from botmanager.service import service

        agents = self.home / "agents"
        executable = self.home / "stable" / "bin" / "solbot"
        executable.parent.mkdir(parents=True)
        executable.write_text("fixture")
        with (
            patch("botmanager.service.sys.platform", "darwin"),
            patch("botmanager.service.installed_executable", return_value=executable),
            patch(
                "botmanager.service.subprocess.run", side_effect=LaunchctlFixture()
            ) as launch,
        ):
            result = service("install", self.home, agents_dir=agents)
            self.assertTrue(result["installed"])
            path = next(agents.glob("*.plist"))
            definition = plistlib.loads(path.read_bytes())
            self.assertEqual(
                definition["ProgramArguments"], [str(executable), "daemon"]
            )
            self.assertEqual(
                definition["EnvironmentVariables"]["SOLBOT_HOME"], str(self.home)
            )
            self.assertTrue(definition["KeepAlive"])
            self.assertIn(
                "bootstrap", [call.args[0][1] for call in launch.call_args_list]
            )
            self.assertEqual(launch.call_args.args[0][1], "print")
            service("uninstall", self.home, agents_dir=agents)
            self.assertIn(
                "bootout", [call.args[0][1] for call in launch.call_args_list]
            )
            self.assertEqual(launch.call_args.args[0][1], "print")
            self.assertFalse(path.exists())

    def test_slow_fragmented_request_cannot_suspend_supervisor_poll(self):
        import socket

        self.supervisor = Supervisor(self.home).open()
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(str(self.home / "supervisor.sock"))
        done = threading.Event()

        def fragment():
            try:
                for part in (
                    b"{",
                    b'"command"',
                    b":",
                    b'"help"',
                    b",",
                    b'"params"',
                    b":",
                    b"{",
                    b"}",
                    b"}\n",
                ):
                    client.sendall(part)
                    if done.wait(0.08):
                        break
            except OSError:
                pass

        thread = threading.Thread(target=fragment)
        thread.start()
        try:
            started = time.monotonic()
            self.supervisor.step()
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 0.45)
        finally:
            done.set()
            client.close()
            thread.join(1)

    def test_failed_service_bootstrap_is_reconciled_on_retry(self):
        from botmanager.service import service

        fixture = LaunchctlFixture(fail_bootstrap=1)
        agents = self.home / "retry-agents"
        with (
            patch("botmanager.service.sys.platform", "darwin"),
            patch(
                "botmanager.service.installed_executable",
                return_value=self.home / "stable-solbot",
            ),
            patch("botmanager.service.subprocess.run", side_effect=fixture) as launch,
        ):
            with self.assertRaises(ManagerError):
                service("install", self.home, agents_dir=agents)
            path = next(agents.glob("*.plist"))
            self.assertTrue(path.exists())
            result = service("install", self.home, agents_dir=agents)
            self.assertTrue(fixture.loaded)
            self.assertTrue(result["registered"])
            self.assertEqual(
                [call.args[0][1] for call in launch.call_args_list].count("bootstrap"),
                2,
            )
            result = service("install", self.home, agents_dir=agents)
            self.assertTrue(result["already_registered"])
            self.assertEqual(
                [call.args[0][1] for call in launch.call_args_list].count("bootstrap"),
                2,
            )

    def test_uninstall_cleans_retained_definition_only_after_confirmed_absence(self):
        from botmanager.service import service

        fixture = LaunchctlFixture(fail_bootstrap=1)
        agents = self.home / "absent-agents"
        with (
            patch("botmanager.service.sys.platform", "darwin"),
            patch(
                "botmanager.service.installed_executable",
                return_value=self.home / "stable-solbot",
            ),
            patch("botmanager.service.subprocess.run", side_effect=fixture) as launch,
        ):
            with self.assertRaises(ManagerError):
                service("install", self.home, agents_dir=agents)
            path = next(agents.glob("*.plist"))
            fixture.unknown_probe = True
            with self.assertRaises(ManagerError):
                service("uninstall", self.home, agents_dir=agents)
            self.assertTrue(path.exists())
            fixture.unknown_probe = False
            result = service("uninstall", self.home, agents_dir=agents)
            self.assertFalse(path.exists())
            self.assertFalse(result["registered"])
            self.assertNotIn(
                "bootout", [call.args[0][1] for call in launch.call_args_list]
            )

    def test_exhausted_replay_restarts_restore_waiting_without_new_evaluation(self):
        self.start()
        self.supervisor = Supervisor(self.home).open()
        self.spin(lambda: self.ledger.get(self.spec.bot_id)["cursor"] == 8)
        before = self.ledger.get(self.spec.bot_id)
        self.supervisor.close()
        self.supervisor = Supervisor(self.home).open()
        for restart in ("daemon", "explicit-stop-start"):
            if restart == "explicit-stop-start":
                self.ledger.control(self.spec, "stop", str(uuid4()))
                self.supervisor.step()
                self.start()
            self.spin(lambda: self.ledger.get(self.spec.bot_id)["pid"] is not None)
            self.spin(
                lambda: (
                    self.ledger.get(self.spec.bot_id)["reason"]
                    == "reference_input_exhausted"
                ),
                timeout=1.0,
            )
            after = self.ledger.get(self.spec.bot_id)
            self.assertEqual(after["observed"], "waiting")
            self.assertLess(time.time() - after["heartbeat"], 2.0)
            self.assertEqual(after["checkpoint"], before["checkpoint"])
            self.assertEqual(after["cursor"], before["cursor"])
            self.assertEqual(after["evaluated"], before["evaluated"])
            self.assertEqual(
                self.ledger.fills(self.spec.bot_id), before["checkpoint"]["fills"]
            )

    def test_client_deadline_spans_fragmented_response(self):
        import socket

        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        path = self.home / "supervisor.sock"
        listener.bind(str(path))
        path.chmod(0o600)
        listener.listen(1)
        listener.settimeout(2.0)
        done = threading.Event()

        def fragment():
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(1.0)
                    connection.recv(65536)
                    for part in b'{"ok":true}\n':
                        connection.sendall(bytes([part]))
                        if done.wait(0.08):
                            break
            except OSError:
                pass

        thread = threading.Thread(target=fragment)
        thread.start()
        try:
            started = time.monotonic()
            with (
                patch("botmanager.transport.CLIENT_REQUEST_SECONDS", 0.2),
                self.assertRaises(ManagerError) as caught,
            ):
                request(self.home, "help", {})
            self.assertEqual(caught.exception.code, "supervisor_unreachable")
            self.assertLess(time.monotonic() - started, 0.5)
        finally:
            done.set()
            listener.close()
            thread.join(2.0)

    def test_service_command_success_requires_observed_registration_change(self):
        from botmanager.service import service

        fixture = LaunchctlFixture()
        ignored = {"bootstrap"}

        def launch(args, **kwargs):
            if args[1] in ignored:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            return fixture(args, **kwargs)

        agents = self.home / "unconfirmed-agents"
        with (
            patch("botmanager.service.sys.platform", "darwin"),
            patch(
                "botmanager.service.installed_executable",
                return_value=self.home / "stable-solbot",
            ),
            patch("botmanager.service.subprocess.run", side_effect=launch),
        ):
            with self.assertRaises(ManagerError):
                service("install", self.home, agents_dir=agents)
            path = next(agents.glob("*.plist"))
            self.assertTrue(path.exists())
            ignored.clear()
            self.assertTrue(
                service("install", self.home, agents_dir=agents)["registered"]
            )
            ignored.add("bootout")
            with self.assertRaises(ManagerError):
                service("uninstall", self.home, agents_dir=agents)
            self.assertTrue(path.exists())
            self.assertTrue(fixture.loaded)
            ignored.clear()
            self.assertFalse(
                service("uninstall", self.home, agents_dir=agents)["registered"]
            )
            self.assertFalse(path.exists())


class LaunchctlFixture:
    def __init__(self, fail_bootstrap=0):
        self.loaded = False
        self.fail_bootstrap = fail_bootstrap
        self.unknown_probe = False

    def __call__(self, args, **kwargs):
        command = args[1]
        if command == "bootstrap":
            if self.fail_bootstrap:
                self.fail_bootstrap -= 1
                raise subprocess.CalledProcessError(5, args)
            self.loaded = True
        elif command == "bootout":
            if not self.loaded:
                raise subprocess.CalledProcessError(113, args)
            self.loaded = False
        elif command == "print":
            code = 5 if self.unknown_probe else 0 if self.loaded else 113
            return subprocess.CompletedProcess(args, code, stdout="", stderr="")
        else:
            raise AssertionError("unexpected fixture launchctl command")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
