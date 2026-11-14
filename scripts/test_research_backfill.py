"""Launcher contracts use isolated shell stubs; never start or signal a collector."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "research/run_backfill.sh"


class BackfillLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "owner's archive"
        self.events = self.root / "events"
        self.stubs = self.root / "stubs.sh"
        self.stubs.write_text('''
nohup() { printf 'launch\\n' >> "$BACKFILL_TEST_EVENTS"; }
kill() { printf 'signal %s\\n' "$*" >> "$BACKFILL_TEST_EVENTS"; }
ps() {
    if [[ -n "${BACKFILL_TEST_REWRITE_PID:-}" ]]; then
        printf '%s\\n' "$BACKFILL_TEST_REWRITE_PID" > "$BACKFILL_HOME/data/logs/tick_backfill.pid"
    fi
    printf '%s\\n' "$BACKFILL_TEST_COMMAND"
}
''')

    def run_script(self, *arguments, command="", python=None, rewrite_pid=""):
        # BASH_ENV replaces all process-control/launch operations in this child.
        # The only real external tools used are filesystem/stdlib utilities.
        env = {**os.environ, "BACKFILL_HOME": str(self.home),
               "BACKFILL_PYTHON": python or sys.executable, "BASH_ENV": str(self.stubs),
               "BACKFILL_TEST_EVENTS": str(self.events), "BACKFILL_TEST_COMMAND": command,
               "BACKFILL_TEST_REWRITE_PID": rewrite_pid}
        return subprocess.run(["bash", str(SCRIPT), *arguments], env=env,
                              check=False, capture_output=True, text=True, timeout=5)

    def pid_record(self):
        path = self.home / "data/logs/tick_backfill.pid"
        path.parent.mkdir(parents=True)
        path.write_text("424242\n")
        return path

    def test_help_and_invalid_options_cannot_launch_or_create_state(self):
        for index, (arguments, code) in enumerate([(('--help',), 0), (('--unexpected',), 2),
                                                  (('start', '--unexpected'), 2)]):
            with self.subTest(arguments=arguments):
                self.home = self.root / f"help-case-{index}"
                self.events.unlink(missing_ok=True)
                result = self.run_script(*arguments)
                self.assertFalse(self.events.exists(), "Argument handling launched a collector")
                self.assertFalse(self.home.exists(), "Argument handling created owner state")
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertIn("Usage:", result.stdout + result.stderr)

    def test_status_checkpoint_paths_are_data_even_with_apostrophes(self):
        checkpoint = self.home / "data/checkpoints/coin's.json"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text(json.dumps({"trades": 7, "pages": 2, "done": True}))
        result = self.run_script('--status')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("coin's.json: 7 trades, 2 pages, done=True", result.stdout)
        self.assertFalse(self.events.exists())

    def test_unknown_pid_is_never_signalled_or_replaced(self):
        pid = self.pid_record()
        original = pid.read_bytes()
        for arguments in [('--stop',), ('start',)]:
            with self.subTest(arguments=arguments):
                self.events.unlink(missing_ok=True)
                result = self.run_script(*arguments, command='/usr/bin/python /tmp/unrelated.py')
                self.assertFalse(self.events.exists(), "Unknown process received signal or launch")
                self.assertEqual(pid.read_bytes(), original)
                self.assertIn("unverified", result.stdout + result.stderr)

    def test_only_matching_absolute_collector_and_owner_may_receive_stop(self):
        pid = self.pid_record()
        result = self.run_script('--stop', command=self.owned_command())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.events.read_text(), 'signal -TERM 424242\n')
        self.assertEqual(pid.read_text(), '424242\n')

    def owned_command(self):
        command = shlex.join([sys.executable, '-u', str(SCRIPT.with_name('tick_backfill.py')),
                              '--data-dir', str(self.home / 'data'),
                              '--out-dir', str(self.home / 'data/authoritative'),
                              '--checkpoint-dir', str(self.home / 'data/checkpoints'),
                              '--report', str(self.home / 'research/TICK-BACKFILL-AUDIT.md')])
        return command

    def test_pid_file_change_cannot_redirect_the_verified_stop(self):
        self.pid_record()
        result = self.run_script('--stop', command=self.owned_command(), rewrite_pid='434343')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.events.read_text(), 'signal -TERM 424242\n')

    def test_missing_environment_and_pandas_fail_before_owner_state(self):
        for arguments, expected in [(('--help',), 0), (('start',), 3)]:
            result = self.run_script(*arguments, python=str(self.root / 'missing-python'))
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertFalse(self.events.exists())
            self.assertFalse(self.home.exists())
        fake = self.root / 'python-without-pandas'
        fake.write_text('#!/bin/sh\nexit 1\n')
        fake.chmod(0o700)
        result = self.run_script('start', python=str(fake))
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('Missing pandas', result.stderr)
        self.assertIn('uv pip install --python', result.stderr)
        self.assertFalse(self.events.exists())
        self.assertFalse(self.home.exists())


if __name__ == '__main__':
    unittest.main()
