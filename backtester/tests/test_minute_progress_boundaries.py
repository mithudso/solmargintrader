"""Progress cache fallbacks and long-plan coverage must remain bounded."""

from contextlib import redirect_stderr
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from backtester.core import fetch_minutes as fm


class ProgressBoundariesTests(unittest.TestCase):
    def test_invalid_retry_after_cannot_produce_invalid_sleep(self):
        for value in ["-1", "-inf", "nan"]:
            error = type("RateLimit", (Exception,), {"headers": {"Retry-After": value}})()
            with self.subTest(value=value):
                self.assertEqual(fm._retry_after(error, 0), 0.5)

    def test_nonobject_json_sidecar_uses_existing_refetch_fallback(self):
        for content in ["[]", "null", '"invalid"', "3"]:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temp:
                with patch.object(fm, "DATA", Path(temp)), redirect_stderr(io.StringIO()):
                    fm.progress_path("BTC").write_text(content)
                    self.assertIsNone(fm.load_probe("BTC"))
                    self.assertIsNone(fm.load_planned_end("BTC"))
                    self.assertEqual(fm.load_progress("BTC"), set())

    def test_large_plan_coverage_does_not_rehash_all_windows_per_row(self):
        code = '''from unittest.mock import patch
import pandas as pd
from backtester.core import fetch_minutes as fm
windows=list(range(50000))
with patch.object(fm,"plan_windows",return_value=windows), patch.object(fm,"load_progress",return_value=set(windows)), patch.object(fm,"load_probe",return_value=None), patch.object(fm,"load_planned_end",return_value=0):
 result=fm.coverage("BTC",pd.DataFrame(),1)
 assert result.windows_done==50000
 assert result.windows_total==50000
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
