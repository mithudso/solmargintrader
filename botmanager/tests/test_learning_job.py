"""Nonblocking daily scheduling and owned helper lifecycle fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from botmanager.data import load_recording
from botmanager.learning_job import DailyLearningJob, schedule_snapshot
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore
from botmanager.supervisor import Supervisor

from tests.test_paper import grid, recording


class DailyLearningJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.descriptor = {
            "version": 2,
            "interpreter": sys.executable,
            "repository": str(self.home),
            "config_root": str(self.home / "owner-config"),
            "authority": {
                "id": str(uuid4()),
                "root": str(self.home / "authority"),
                "known_clients": [],
                "inventory_complete": True,
            },
            "expected_identity": {"version": "fixture"},
        }
        self.real_popen = subprocess.Popen

    def descriptor_file(self):
        (self.home / "research-owner.json").write_text(json.dumps(self.descriptor))

    def spawn(self, delay=0, output=None):
        def launch(argv, **kwargs):
            script = (
                "import sys,json,time; req=json.load(sys.stdin); time.sleep("
                + str(delay)
                + "); "
            )
            script += (
                "print(json.dumps({'ok':True,'command':'research.protocol','result':{'identity':req['expected_identity'],'schedule':{'scopes':[]},'reason':'fixture_completed'}}))"
                if output is None
                else "print(" + repr(output) + ")"
            )
            return self.real_popen([sys.executable, "-I", "-B", "-c", script], **kwargs)

        return launch

    def finish(self, job):
        deadline = time.monotonic() + 5
        while job.process is not None and time.monotonic() < deadline:
            job.step()
            time.sleep(0.01)
        self.assertIsNone(job.process)

    def test_absent_descriptor_and_reads_start_nothing(self):
        missing = self.home / "absent"
        self.assertEqual(schedule_snapshot(missing)["state"], "unavailable")
        job = DailyLearningJob(missing)
        with patch("botmanager.learning_job.subprocess.Popen") as spawn:
            job.step()
            spawn.assert_not_called()
        self.assertFalse(missing.exists())

    def test_due_clock_once_per_day_and_restart_dedup(self):
        self.descriptor_file()
        with (
            patch(
                "botmanager.learning_job.subprocess.Popen", side_effect=self.spawn()
            ) as spawn,
            patch("botmanager.learning_job.time.time", return_value=1800000000),
        ):
            job = DailyLearningJob(self.home)
            job.step()
            self.finish(job)
            self.assertEqual(job.receipt["state"], "completed")
            self.assertEqual(spawn.call_count, 1)
            restarted = DailyLearningJob(self.home)
            restarted.step()
            self.assertEqual(spawn.call_count, 1)
            with patch(
                "botmanager.learning_job.time.time", return_value=1800000000 + 86400
            ):
                restarted._checked_at = 0
                restarted.step()
                self.finish(restarted)
            self.assertEqual(spawn.call_count, 2)

    def test_slow_helper_does_not_block_and_close_reaps(self):
        self.descriptor_file()
        with patch(
            "botmanager.learning_job.subprocess.Popen", side_effect=self.spawn(delay=60)
        ):
            job = DailyLearningJob(self.home)
            started = time.monotonic()
            job.step()
            self.assertLess(time.monotonic() - started, 0.5)
            process = job.process
            for _ in range(10):
                started = time.monotonic()
                job.step()
                self.assertLess(time.monotonic() - started, 0.05)
            job.close()
            self.assertIsNotNone(process.poll())
            self.assertEqual(job.receipt["state"], "cancelled")
            self.assertTrue(process.stdout.closed)
            self.assertTrue(process.stderr.closed)

    def test_timeout_and_output_limit_are_bounded_and_reaped(self):
        self.descriptor_file()
        with patch(
            "botmanager.learning_job.subprocess.Popen", side_effect=self.spawn(delay=60)
        ):
            job = DailyLearningJob(self.home)
            job.step()
            process = job.process
            job.started -= 121
            job.step()
            self.assertIsNone(job.process)
            self.assertIsNotNone(process.poll())
            self.assertEqual(job.receipt["state"], "failed")
        (self.home / "learning-job.json").unlink()
        with patch(
            "botmanager.learning_job.subprocess.Popen",
            side_effect=self.spawn(output="x" * 300000),
        ):
            job = DailyLearningJob(self.home)
            job.step()
            self.finish(job)
            self.assertEqual(job.receipt["state"], "failed")
            self.assertLess((self.home / "learning-job.json").stat().st_size, 2000)

    def test_supervisor_controls_and_status_remain_responsive(self):
        self.descriptor_file()
        spec = grid("scheduler-controls")
        ManagerStore(self.home).create_spec(spec)
        ledger = RuntimeLedger(self.home)
        ledger.register(spec, load_recording(recording(self.home)))
        with patch(
            "botmanager.learning_job.subprocess.Popen", side_effect=self.spawn(delay=60)
        ):
            supervisor = Supervisor(self.home).open()
            try:
                started = time.monotonic()
                supervisor.step()
                self.assertLess(time.monotonic() - started, 0.5)
                self.assertIsNotNone(supervisor.learning_job.process)
                started = time.monotonic()
                status = dispatch(
                    "status", {"identity": spec.bot_id}, CommandContext(home=self.home)
                )
                self.assertTrue(status["ok"], status)
                self.assertLess(time.monotonic() - started, 1)
                started = time.monotonic()
                stop = ledger.control(spec, "stop", str(uuid4()))
                self.assertIsNotNone(stop)
                self.assertLess(time.monotonic() - started, 2)
                process = supervisor.learning_job.process
            finally:
                supervisor.close()
            self.assertIsNotNone(process.poll())
            self.assertIsNone(supervisor.learning_job.process)

    def test_malformed_json_shapes_cannot_break_actual_supervisor_boundary(self):
        invalid = [
            [],
            None,
            1,
            "text",
            {"state": []},
            {"state": "running", "reason": "x", "day": []},
            {"state": "running", "reason": "x", "last_attempt": float("nan")},
            {"state": "completed", "reason": "x", "result": []},
            {"state": "completed", "reason": "x", "result": {"scopes": [{}]}},
        ]
        for index, body in enumerate(invalid):
            with self.subTest(body=body):
                home = self.home / ("invalid-shape-" + str(index))
                home.mkdir()
                path = home / "learning-job.json"
                path.write_text(json.dumps(body))
                before = path.read_bytes()
                self.assertEqual(schedule_snapshot(home)["state"], "unavailable")
                supervisor = Supervisor(home).open()
                try:
                    supervisor.step()
                    self.assertIsNone(supervisor.learning_job.process)
                    result = dispatch("status", {}, CommandContext(home=home))
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(before, path.read_bytes())
                finally:
                    supervisor.close()

    def test_malformed_helper_envelope_and_fields_fail_without_orphan(self):
        self.descriptor_file()
        outputs = [
            "[]",
            "null",
            "1",
            '"text"',
            '{"ok":true,"command":"research.protocol","result":[]}',
            '{"ok":true,"command":"research.protocol","result":{"identity":{"version":"fixture"},"schedule":[],"reason":"bad"}}',
            '{"ok":true,"command":"research.protocol","result":{"identity":{"version":"fixture"},"schedule":{},"reason":[]}}',
        ]
        outputs.append(
            '{"ok":true,"command":"research.protocol","result":{"identity":{"version":"fixture"},"schedule":{"scopes":[{}]},"reason":"bad-scope"}}'
        )
        for output in outputs:
            with self.subTest(output=output):
                status = self.home / "learning-job.json"
                if status.exists():
                    status.unlink()
                with patch(
                    "botmanager.learning_job.subprocess.Popen",
                    side_effect=self.spawn(output=output),
                ):
                    supervisor = Supervisor(self.home).open()
                    try:
                        supervisor.step()
                        process = supervisor.learning_job.process
                        self.finish(supervisor.learning_job)
                        supervisor.step()
                        self.assertEqual(
                            supervisor.learning_job.receipt["state"], "failed"
                        )
                        self.assertIsNotNone(process.poll())
                        self.assertTrue(
                            dispatch("status", {}, CommandContext(home=self.home))["ok"]
                        )
                    finally:
                        supervisor.close()
