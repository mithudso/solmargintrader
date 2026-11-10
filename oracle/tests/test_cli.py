import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path

from oracle.cli import main, owner, snapshot


class CliTests(unittest.TestCase):
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
