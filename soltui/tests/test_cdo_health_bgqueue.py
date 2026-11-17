"""Corrupt or torn queue files must not hide subsequent valid results."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from soltui import bgqueue


def result(job_id):
    return bgqueue.JobResult(job_id=job_id, strategy="grid", horizon="short", asset="SOL",
        interval="1m", params={}, tier=1, variation="", family="grid", median_sharpe=1,
        iqr=0, frac_positive=1, median_return=1, trades=50, evaluable=True)


class QueueFileIntegrityTests(unittest.TestCase):
    def test_append_after_read_retains_pre_read_timestamp_and_next_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(result("first").to_json() + "\n")
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))
            original_open = Path.open

            class AppendAfterRead:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return self.stream.__exit__(*args)

                def __getattr__(self, name):
                    return getattr(self.stream, name)

                def read(self, size=-1):
                    data = self.stream.read(size)
                    if size == -1:
                        with original_open(path, "ab") as out:
                            out.write((result("second").to_json() + "\n").encode())
                        os.utime(path, ns=(2_000_000_000, 2_000_000_000))
                    return data

            with patch.object(Path, "open", lambda item, *args, **kwargs:
                              AppendAfterRead(original_open(item, *args, **kwargs))):
                rows, cursor, _ = bgqueue.read_results_since(path=path)
            self.assertEqual([row.job_id for row in rows], ["first"])
            self.assertEqual(cursor.mtime, 1.0)
            rows, _, _ = bgqueue.read_results_since(cursor, path)
            self.assertEqual([row.job_id for row in rows], ["second"])

    def test_invalid_asset_cannot_crash_leaderboard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            bad = json.loads(result("bad").to_json())
            bad["asset"] = None
            path.write_text(json.dumps(bad) + "\n" + result("good").to_json() + "\n")
            ranked, _ = bgqueue.leaderboard(bgqueue.read_results(path), "SOL")
            self.assertEqual([row.job_id for row in ranked], ["good"])

    def test_invalid_utf8_does_not_advance_past_future_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_bytes(b"\xff\n")
            _, cursor, _ = bgqueue.read_results_since(path=path)
            self.assertEqual(cursor.offset, 2)
            bgqueue.append_result(result("good"), path)
            rows, _, _ = bgqueue.read_results_since(cursor, path)
            self.assertEqual([row.job_id for row in rows], ["good"])
            old_cursor = bgqueue.ResultsCursor(4, cursor.inode, cursor.device, cursor.mtime)
            rows, _, restarted = bgqueue.read_results_since(old_cursor, path)
            self.assertTrue(restarted)
            self.assertEqual([row.job_id for row in rows], ["good"])

    def test_append_separates_an_unterminated_valid_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(result("first").to_json())
            self.assertEqual([row.job_id for row in bgqueue.read_results(path)], ["first"])
            bgqueue.append_result(result("second"), path)
            self.assertEqual([row.job_id for row in bgqueue.read_results(path)], ["first", "second"])
            path.write_text('{"job_id":')
            bgqueue.append_result(result("after-torn"), path)
            self.assertEqual([row.job_id for row in bgqueue.read_results(path)], ["after-torn"])


if __name__ == "__main__":
    unittest.main()
