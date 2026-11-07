"""research/full_suite.py: the plan, and stopping before the sweeps when a fetch fails."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

from pathlib import Path

from research import full_suite


class FullSuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        # resolve_data_dir shells out to git; pin it so subprocess.run counts only suite steps.
        patcher = mock.patch.object(full_suite, "resolve_data_dir", lambda: Path("/nonexistent/data"))
        patcher.start()
        self.addCleanup(patcher.stop)
    def test_plan_lists_fetch_then_both_sweeps_and_runs_nothing(self) -> None:
        out = io.StringIO()
        with mock.patch.object(full_suite.subprocess, "run") as run, redirect_stdout(out):
            code = full_suite.main(["--plan", "--assets", "SOL,BTC"])
        self.assertEqual(code, 0)
        run.assert_not_called()
        text = out.getvalue()
        self.assertLess(text.index("fetch 1m candles from Coinbase for 2 coins"), text.index("registry sweep SOL"))
        self.assertIn("backtester.core.fetch_minutes --years 7 --workers 8 --assets SOL,BTC", text)
        self.assertIn("soltui.compound sweep --assets SOL,BTC --perturb --aggregate-grid", text)

    def test_default_universe_is_the_top_50_record_split_by_venue(self) -> None:
        out = io.StringIO()
        with mock.patch.object(full_suite.subprocess, "run") as run, redirect_stdout(out):
            self.assertEqual(full_suite.main(["--plan"]), 0)
        run.assert_not_called()
        text = out.getvalue()
        self.assertIn("fetch 1m candles from Coinbase for 36 coins", text)
        self.assertIn("backtester.core.fetch_minutes_alt --assets TRX,XMR,WBT", text)
        # Coinbase candles are asked for only the coins Coinbase lists.
        universe = next(line for line in text.splitlines() if "backtester.core.universe" in line)
        self.assertNotIn("TRX", universe)
        self.assertIn("ETC", universe)

    def test_a_failed_fetch_stops_before_any_sweep_or_archive(self) -> None:
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return SimpleNamespace(returncode=1 if "backtester.core.fetch_minutes" in cmd else 0)

        with mock.patch.object(full_suite.subprocess, "run", fake_run), \
                mock.patch.object(full_suite, "listed_only", lambda a: a), \
                mock.patch.object(full_suite, "archive_registry_results") as archive, \
                redirect_stdout(io.StringIO()):
            code = full_suite.main(["--assets", "SOL"])
        self.assertEqual(code, 1)
        archive.assert_not_called()
        self.assertFalse(any("soltui.bgworker" in c or "soltui.compound" in c for c in calls))

    def test_contradictory_flags_are_refused(self) -> None:
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), \
                mock.patch("sys.stderr", io.StringIO()):
            full_suite.main(["--skip-fetch", "--fetch-only"])


if __name__ == "__main__":
    unittest.main()
