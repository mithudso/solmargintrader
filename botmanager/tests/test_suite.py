"""Availability ownership, real process recovery and bounded durable alerts."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.worker import lifetime_lock, lock_held

from botmanager import machine_health, suite


class ReadyUi:
    def __init__(self, home, manager_home):
        pass

    def start(self):
        pass

    def current(self):
        return machine_health.component(
            "up", "available", ready=True
        ), "http://127.0.0.1:12345"

    def close(self):
        return True, False


def eventually(predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.025)
    raise AssertionError("Observed state did not arrive within the test deadline")


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home, self.ecosystem = self.root / "manager", self.root / "ecosystem"

    def open_pumped(self, ui_factory=ReadyUi):
        owner = suite.Suite(self.home, self.ecosystem, ui_factory=ui_factory).open()
        done, failures = threading.Event(), []

        def pump():
            try:
                while not done.is_set() and not owner.stopping.is_set():
                    owner.step()
                    done.wait(0.005)
            except BaseException as exc:  # noqa: BLE001 - transfer thread failure to the test
                failures.append(exc)
            finally:
                owner.close()

        thread = threading.Thread(target=pump)
        thread.start()

        def cleanup():
            done.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])

        self.addCleanup(cleanup)
        return owner

    def test_read_operations_never_create_absent_homes(self):
        self.assertEqual(suite.status(self.home, self.ecosystem)["state"], "stopped")
        self.assertEqual(suite.alerts(self.home)["events"], [])
        self.assertFalse(self.home.exists())
        self.assertFalse(self.ecosystem.exists())

    def test_live_suite_and_manager_sockets_singleton_and_safe_stop(self):
        owner = self.open_pumped()
        good = machine_health.component("up", "available", ready=True)
        with patch(
            "botmanager.machine_health.ui_probe",
            return_value=(good, "http://127.0.0.1:12345"),
        ):
            value = machine_health.check(self.home, self.ecosystem)
        self.assertTrue(value["ready"])
        self.assertEqual(value["components"]["manager"]["state"], "up")
        with self.assertRaises(ManagerError) as raised:
            suite.Suite(self.home, self.ecosystem, ui_factory=ReadyUi).open()
        self.assertEqual(raised.exception.code, "suite_owner_conflict")
        with patch(
            "botmanager.suite_service.operation", return_value={"installed": False}
        ):
            stopped = suite.operation("stop", self.home, self.ecosystem)
        self.assertEqual(stopped["state"], "stopped")
        self.assertFalse(stopped["ui_retained"])
        self.assertFalse(lock_held(self.home / "supervisor.lock"))
        self.assertFalse(lock_held(self.home / ".suite/owner.lock"))
        self.assertEqual(owner.supervisor, None)

    def test_alert_journal_failure_prevents_false_green_and_recovers(self):
        owner = self.open_pumped()
        path = self.home / ".suite/alerts.json"
        path.write_text("invalid")
        owner.publish()
        value = machine_health.suite_probe(self.home, time.time())
        self.assertEqual(value["state"], "degraded")
        self.assertFalse(value["ready"])
        self.assertEqual(value["reason"], "component_alert_journal_unavailable")
        path.unlink()
        owner.publish()
        self.assertEqual(
            machine_health.suite_probe(self.home, time.time())["state"], "up"
        )

    def test_reap_supervisor_precedes_optional_ui_close(self):
        calls = []
        owner = suite.Suite(self.home, self.ecosystem)

        class Manager:
            def close(self):
                calls.append("manager_reap_and_close")

        class Ui:
            def close(self):
                calls.append("ui_close")
                return True, True

        owner.supervisor, owner.ui = Manager(), Ui()
        owner.close()
        self.assertEqual(calls, ["manager_reap_and_close", "ui_close"])

    def test_start_refuses_independent_manager_and_source_persistence(self):
        with (
            lifetime_lock(self.home / "supervisor.lock"),
            self.assertRaises(ManagerError) as raised,
        ):
            suite.operation("start", self.home, self.ecosystem)
        self.assertEqual(raised.exception.code, "suite_owner_conflict")
        with (
            patch(
                "botmanager.suite_service.operation", return_value={"installed": False}
            ),
            self.assertRaises(ManagerError) as raised,
        ):
            suite.operation("start", self.home, self.ecosystem)
        self.assertEqual(raised.exception.code, "stable_install_required")

    def launcher(self):
        # A test-only executable launches the real existing Supervisor in a
        # disposable namespace. UI ownership is exercised separately below.
        path = self.root / "solbot-fixture"
        path.write_text(
            "#!" + sys.executable + "\n"
            "from botmanager import suite,machine_health\n"
            "class Ui:\n"
            " def __init__(self,*args): pass\n"
            " def start(self): pass\n"
            " def current(self): return machine_health.component('up','available',ready=True),None\n"
            " def close(self): return True,False\n"
            "suite.Suite(ui_factory=Ui).run()\n"
        )
        path.chmod(0o700)
        return path

    def test_concurrent_start_spawns_one_real_suite_and_crash_can_restart(self):
        launcher = self.launcher()
        real_spawn, children = subprocess.Popen, []
        source_root = str(Path(__file__).resolve().parents[2])
        source = source_root + "/botmanager/src:" + source_root

        def spawn(*args, **kwargs):
            kwargs["env"]["PYTHONPATH"] = source
            process = real_spawn(*args, **kwargs)
            children.append(process)
            return process

        def cleanup():
            for child in children:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)

        self.addCleanup(cleanup)
        with (
            patch(
                "botmanager.suite_service.operation", return_value={"installed": False}
            ),
            patch("botmanager.service.installed_executable", return_value=launcher),
            patch("botmanager.suite.subprocess.Popen", side_effect=spawn),
        ):
            with ThreadPoolExecutor(max_workers=2) as workers:
                results = list(
                    workers.map(
                        lambda _: suite.operation("start", self.home, self.ecosystem),
                        range(2),
                    )
                )
            self.assertEqual(len(children), 1)
            self.assertTrue(
                all(value["state"] in ("running", "pending") for value in results)
            )
            self.assertEqual(machine_health.manager_probe(self.home)["state"], "up")
            children[0].kill()
            children[0].wait(timeout=5)
            self.assertEqual(machine_health.manager_probe(self.home)["state"], "down")
            result = suite.operation("start", self.home, self.ecosystem)
            self.assertEqual(result["state"], "running")
            self.assertEqual(len(children), 2)
            self.assertNotEqual(children[0].pid, children[1].pid)
            self.assertEqual(machine_health.manager_probe(self.home)["state"], "up")
            stopped = suite.operation("stop", self.home, self.ecosystem)
            self.assertEqual(stopped["state"], "stopped")
            children[1].wait(timeout=5)
        events = suite.alerts(self.home)["events"]
        self.assertIn(
            ("suite", "component_failure", "unclean_suite_exit"),
            [(row["component"], row["kind"], row["reason"]) for row in events],
        )
        self.assertEqual(
            [row["kind"] for row in events if row["component"] == "suite"][-2:],
            ["component_failure", "component_recovered"],
        )
        self.assertFalse((self.home / "manager.sqlite3").exists())
        self.assertFalse((self.home / "runtime.sqlite3").exists())

    def test_fast_ui_repair_preserves_failure_and_recovery_between_publishes(self):
        children = []

        def ensure(home, manager_home, *, on_spawn):
            if not children or children[-1].poll() is not None:
                child = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                children.append(child)
                on_spawn(child)
            return {"running": True, "url": None}

        owner = self.open_pumped(
            ui_factory=lambda home, manager: suite.UiMonitor(
                home, manager, ensure=ensure
            )
        )
        eventually(lambda: len(children) == 1)
        owner.publish()
        children[0].kill()
        children[0].wait(timeout=5)
        eventually(lambda: len(children) == 2)
        self.assertEqual(owner.ui.current()[0]["state"], "up")
        owner.publish()
        events = [
            row
            for row in suite.alerts(self.home)["events"]
            if row["component"] == "control_room"
        ]
        self.assertIn("control_process_exited", [row["reason"] for row in events])
        self.assertEqual(
            [row["kind"] for row in events][-2:],
            ["component_failure", "component_recovered"],
        )


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "manager"
        suite._directory(self.home)

    def value(self, now, state="up", reason="available"):
        values = {
            name: machine_health.component("up", "available", ready=True)
            for name in machine_health.COMPONENTS
        }
        values["manager"] = machine_health.component(state, reason, ready=state == "up")
        return {"observed_at": now, "components": values}

    def test_durable_failure_cooldown_recovery_and_bounded_paging(self):
        with contextlib.redirect_stderr(io.StringIO()):
            journal = suite.AlertJournal(self.home)
            journal.observe(self.value(100))
            journal.observe(self.value(101, "down", "manager_exited"))
            suite.AlertJournal(self.home).observe(
                self.value(102, "down", "manager_exited")
            )
            journal.observe(self.value(402, "down", "manager_exited"))
            journal.observe(self.value(403))
        page = suite.alerts(self.home, limit=2)
        self.assertEqual(
            [row["kind"] for row in page["events"]],
            ["component_failure", "component_failure"],
        )
        self.assertTrue(page["has_more"])
        next_page = suite.alerts(self.home, after=page["next_after"])
        self.assertEqual(next_page["events"][0]["kind"], "component_recovered")
        before = (self.home / ".suite/alerts.json").stat().st_mtime_ns
        suite.alerts(self.home)
        self.assertEqual((self.home / ".suite/alerts.json").stat().st_mtime_ns, before)

    def test_rotation_preserves_monotonic_cursor_and_signals_history_loss(self):
        with contextlib.redirect_stderr(io.StringIO()):
            journal = suite.AlertJournal(self.home)
            for index in range(suite.MAX_ALERTS + 5):
                journal.observe(self.value(100 + index, "down" if index % 2 else "up"))
        body = machine_health.private_read(self.home / ".suite/alerts.json")
        self.assertEqual(len(body["events"]), suite.MAX_ALERTS)
        page = suite.alerts(self.home)
        self.assertTrue(page["history_truncated"])
        self.assertGreater(page["oldest_sequence"], 1)
        self.assertLess(
            (self.home / ".suite/alerts.json").stat().st_size, machine_health.MAX_BYTES
        )

    def test_missing_optional_archive_does_not_invent_a_recorder_failure(self):
        value = self.value(100)
        value["components"]["market_data"] = machine_health.component(
            "unknown", "reference_archive_absent"
        )
        suite.AlertJournal(self.home).observe(value)
        self.assertEqual(suite.alerts(self.home)["events"], [])

    def test_previously_available_archive_disappearance_and_recovery_are_alerted(self):
        journal = suite.AlertJournal(self.home)
        journal.observe(self.value(100))
        value = self.value(101)
        value["components"]["market_data"] = machine_health.component(
            "unknown", "reference_archive_absent"
        )
        with contextlib.redirect_stderr(io.StringIO()):
            journal.observe(value)
            journal.observe(self.value(102))
        self.assertEqual(
            [row["kind"] for row in suite.alerts(self.home)["events"]],
            ["component_failure", "component_recovered"],
        )


class UiMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)

    def test_real_owned_process_failure_restarts_and_is_reaped_on_close(self):
        children = []

        def ensure(home, manager_home, *, on_spawn):
            if not children or children[-1].poll() is not None:
                child = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                children.append(child)
                on_spawn(child)
            return {"running": True, "url": "http://127.0.0.1:12345"}

        monitor = suite.UiMonitor(self.home, self.home, ensure=ensure)
        self.addCleanup(monitor.close)
        monitor.start()
        eventually(lambda: len(children) == 1 and monitor.current()[0]["state"] == "up")
        children[0].kill()
        children[0].wait(timeout=5)
        eventually(lambda: len(children) == 2, seconds=5)
        self.assertNotEqual(children[0].pid, children[1].pid)
        self.assertEqual(monitor.current()[0]["ownership"], "owned")
        self.assertEqual(monitor.close(), (True, False))
        self.assertIsNotNone(children[1].returncode)

    def test_adopted_pid_is_never_signaled_and_retained_on_stop(self):
        monitor = suite.UiMonitor(
            self.home,
            self.home,
            ensure=lambda *args, **kwargs: {
                "running": False,
                "occupied": True,
                "pid": os.getpid(),
                "reason": "control_server_health_unverified",
            },
        )
        monitor.start()
        eventually(lambda: monitor.current()[0]["state"] == "unknown")
        with patch("botmanager.suite._terminate") as terminate:
            self.assertEqual(monitor.close(), (True, True))
        terminate.assert_not_called()

    def test_late_spawn_after_stop_is_reaped(self):
        monitor = suite.UiMonitor(self.home, self.home)
        monitor.close()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        monitor._spawned(child)
        self.assertIsNotNone(child.returncode)


if __name__ == "__main__":
    unittest.main()
