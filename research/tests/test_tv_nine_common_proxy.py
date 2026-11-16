"""The combined entry point must not create output when input guards fail."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.tv_nine_common_proxy import main


class CombinedRunnerTests(unittest.TestCase):
    def test_missing_source_does_not_create_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "result.json"
            argv = [
                "runner",
                "--source",
                str(root / "missing"),
                "--ledger",
                str(root / "ledger"),
                "--output",
                str(output),
            ]
            with patch("sys.argv", argv), self.assertRaises(FileNotFoundError):
                main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
