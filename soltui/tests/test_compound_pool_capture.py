"""Exercise a real spawn under the console's active Textual output capture."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CompoundPoolCapture(unittest.TestCase):
    def test_pool_starts_in_live_textual_capture(self) -> None:
        # A fresh interpreter matters: a tracker started by another test would
        # hide the invalid stderr descriptor on the first pool launch.
        code = '''
import asyncio
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from soltui.tests.test_tui import offline_console_reads
from soltui import config
from soltui.config import Settings
from soltui.tui import SolTuiApp
import sys

config.CONFIG_DIR = Path(sys.argv[1])
app = SolTuiApp(Settings(poll_interval_seconds=60))
def run_pool():
    with ProcessPoolExecutor(max_workers=2) as pool:
        return list(pool.map(abs, [-5, -9]))
async def main():
    async with app.run_test(size=(180, 55)):
        assert await asyncio.to_thread(run_pool) == [5, 9]
with offline_console_reads():
    asyncio.run(main())
'''
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-c", code, tmp], cwd=Path(__file__).resolve().parents[2],
                                    capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
