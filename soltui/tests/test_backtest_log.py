from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from soltui.backtest_log import BacktestLog


class BacktestLogTests(unittest.TestCase):
    def test_follows_only_new_output_and_preserves_split_utf8(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "worker.log"
            path.write_bytes(b"old run\n")
            log = BacktestLog(path)
            with path.open("ab") as f:
                f.write(b"new \xe2\x80")
            self.assertEqual(log.poll(), "new ")
            with path.open("ab") as f:
                f.write(b"\xa6\n")
            self.assertEqual(log.poll(), "…\n")
            self.assertEqual(log.poll(), "")

    def test_new_file_rotation_and_truncation(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "worker.log"
            log = BacktestLog(path)
            self.assertEqual(log.poll(), "")
            path.write_text("first run\n")
            self.assertEqual(log.poll(), "first run\n")
            path.rename(Path(tmp) / "previous.log")
            path.write_text("rotated\n")
            self.assertEqual(log.poll(), "rotated\n")
            path.write_text("new")
            self.assertEqual(log.poll(), "new")

    def test_large_burst_is_bounded(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "worker.log"
            log = BacktestLog(path, max_bytes=4)
            path.write_text("123456789")
            self.assertEqual(log.poll(), "6789")
            self.assertEqual(log.poll(), "")


if __name__ == "__main__":
    unittest.main()
