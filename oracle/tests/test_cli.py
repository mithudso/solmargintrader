import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path

from oracle.cli import main, owner, snapshot


class CliTests(unittest.TestCase):
    def test_missing_dependencies_are_cli_prerequisites_and_help_remains_available(self):
        root = Path(__file__).resolve().parents[2]
        bootstrap = """
import builtins, runpy, sys
module = sys.argv[1]
sys.argv = [module, *sys.argv[2:]]
original = builtins.__import__
def refused(name, *args, **kwargs):
    if name.split('.')[0] in ('numpy', 'mcp'):
        raise ModuleNotFoundError('private dependency canary', name=name.split('.')[0])
    return original(name, *args, **kwargs)
builtins.__import__ = refused
runpy.run_module(module, run_name='__main__')
"""
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "unused.sqlite3"
            for module, command in [("oracle", ["--archive", str(archive), "status"]),
                                    ("oracle.server", ["--archive", str(archive)])]:
                for arguments, expected in [(command, 3), (["--help"], 0)]:
                    with self.subTest(module=module, arguments=arguments):
                        result = subprocess.run([sys.executable, "-c", bootstrap, module, *arguments],
                                                check=False, cwd=root, capture_output=True, text=True, timeout=5)
                        self.assertEqual(result.returncode, expected, result.stderr)
                        if expected == 3:
                            self.assertIn("uv pip install --python", result.stdout + result.stderr)
                            self.assertNotIn("Traceback", result.stderr)
                            self.assertNotIn("private dependency canary", result.stdout + result.stderr)
                        else:
                            self.assertIn("usage:", result.stdout)
                        self.assertFalse(archive.exists())

    def test_bad_arguments_show_usage_without_echoing_private_values(self):
        root = Path(__file__).resolve().parents[2]
        for module in ["oracle", "oracle.server"]:
            with self.subTest(module=module):
                result = subprocess.run([sys.executable, "-m", module, "--private-input-canary"],
                                        check=False, cwd=root, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)
                self.assertNotIn("private-input-canary", result.stdout + result.stderr)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a POSIX FIFO")
    def test_secret_fifo_is_refused_before_starting_a_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "secret.fifo"
            os.mkfifo(secret, 0o600)
            result = subprocess.run(
                [sys.executable, "-m", "oracle", "--archive", str(root / "archive.sqlite3"),
                 "webhook", "--inbox", str(root / "inbox.sqlite3"), "--secret-file", str(secret)],
                cwd=Path(__file__).resolve().parents[2],
                env={"PATH": os.defpath, "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "ORACLE_WEBHOOK_SECRET": ""},
                capture_output=True, text=True, timeout=1, check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["error"], "oracle_operation_failed")
            self.assertFalse((root / "inbox.sqlite3").exists())

    def test_archive_owner_is_exclusive_and_released(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.sqlite3"
            with (
                owner(path),
                self.assertRaisesRegex(RuntimeError, "already_running"),
                owner(path),
            ):
                pass
            with owner(path):
                pass

    def test_snapshot_is_consistent_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.sqlite3"
            out = Path(root) / "snapshot.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE evidence (value INTEGER)")
                db.execute("INSERT INTO evidence VALUES (42)")
            receipt = snapshot(path, out)
            self.assertEqual(len(receipt["sha256"]), 64)
            with closing(sqlite3.connect(out)) as db:
                self.assertEqual(
                    db.execute("SELECT value FROM evidence").fetchone(), (42,)
                )
            with self.assertRaises(ValueError):
                snapshot(path, out)

    def test_bounded_unavailable_feed_has_nonzero_status(self):
        with tempfile.TemporaryDirectory() as root:
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main(
                    [
                        "--archive",
                        str(Path(root) / "archive.sqlite3"),
                        "run",
                        "--recorder-root",
                        str(Path(root) / "absent"),
                        "--max-ticks",
                        "1",
                    ]
                )
            self.assertEqual(code, 3)
            self.assertEqual(
                json.loads(stream.getvalue())["reason"], "recorder_unavailable"
            )

    def test_bad_run_limits_do_not_echo_submitted_input(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["run", "--interval", "nan"])
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(stream.getvalue())["error"], "oracle_operation_failed"
        )


if __name__ == "__main__":
    unittest.main()
