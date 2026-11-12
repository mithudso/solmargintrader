from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research import backfill_control as control


class BackfillControlTests(unittest.TestCase):
    def test_invalid_and_help_modes_are_inert(self):
        for args in (["--typo"], ["unexpected"], ["start", "extra"], ["--help"]):
            with self.subTest(args=args), patch.object(control, "start") as launch:
                with (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()),
                      self.assertRaises(SystemExit)):
                    control.main(args)
                launch.assert_not_called()

    def test_worker_inherits_singleton_and_stop_is_token_bound(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            home = Path(directory)
            copies = []
            commands = []

            def fake_launch(command, **options):
                commands.append(command)
                copies.append(os.dup(options["pass_fds"][0]))
                return SimpleNamespace(pid=42)

            try:
                self.assertEqual(control.start(home, home, launch=fake_launch)[1], 0)
                self.assertEqual(control.start(home, home, launch=fake_launch)[1], 1)
                self.assertEqual(len(commands), 1)
                logs = home / "data/logs"
                owner = json.loads((logs / "tick_backfill.owner.json").read_text())
                with patch.object(os, "kill", side_effect=AssertionError("must never signal")):
                    self.assertIn("stop requested", control.stop(logs))
                marker = logs / ("tick_backfill.stop-" + owner["run_id"])
                self.assertTrue(marker.is_file())
                self.assertEqual(commands[0][commands[0].index("--stop-file") + 1], str(marker))
            finally:
                for fd in copies:
                    os.close(fd)

    def test_stale_owner_does_not_authorize_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            (logs / "tick_backfill.owner.json").write_text('{"pid":42}')
            self.assertEqual(control.stop(logs), "not running")
            self.assertEqual(len(list(logs.iterdir())), 1)

    def test_legacy_pid_record_cannot_authorize_a_duplicate_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / "data/logs"
            logs.mkdir(parents=True)
            (logs / "tick_backfill.pid").write_text("42")
            with patch.object(control.subprocess, "Popen") as launch:
                self.assertEqual(control.start(root, root, launch=launch)[1], 1)
            launch.assert_not_called()

    def test_hostile_checkpoint_name_remains_literal_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoints = root / "data/checkpoints"
            checkpoints.mkdir(parents=True)
            path = checkpoints / "x');raise RuntimeError('injected.json"
            path.write_text(json.dumps({"trades": 1, "pages": 2, "done": False}))
            output = io.StringIO()
            with patch.dict(os.environ, {"BACKFILL_HOME": directory}, clear=True), contextlib.redirect_stdout(output):
                self.assertEqual(control.main(["--status"]), 0)
            self.assertIn(path.name, output.getvalue())
            self.assertIn("1 trades, 2 pages", output.getvalue())
