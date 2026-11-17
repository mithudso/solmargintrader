"""Regressions for safe reporting in the command bridge."""

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from soltui import commands


class BacktestFallbackTests(unittest.TestCase):
    def test_empty_or_multiline_load_error_returns_a_note(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = SimpleNamespace(
                asset="SOL", interval="1m", start="", end="", capital=1,
                fee_bps=0, slippage_bps=0, fill_delay=0, data_dir=directory,
                fee_schedule=None, use_leverage=False, leverage=1, allow_short=False,
                min_confidence=0, borrow_long_bps_hour=0, borrow_short_bps_hour=0,
            )
            for error, expected in ((ValueError(), "no backtest data: ValueError"),
                                    (ValueError("bad data\nprivate detail"),
                                     "no backtest data: ValueError: bad data")):
                with self.subTest(error=str(error)):
                    ctx = SimpleNamespace(settings=settings,
                                          roster=SimpleNamespace(to_list=lambda: []),
                                          runtime=SimpleNamespace(pnl_cache={}))
                    with patch.object(commands, "load_arrays", side_effect=error):
                        curves, notes = commands._backtest_curves(ctx)
                    self.assertEqual(curves, [])
                    self.assertEqual(notes, [expected])

    def test_corrupt_daemon_ledger_is_reported_without_disclosing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ledger.sqlite").write_bytes(b"not sqlite private fixture")
            with patch.object(commands.liq, "state_dir", return_value=root), \
                 patch.object(commands.liq, "load_status", return_value=SimpleNamespace(data={})), \
                 self.assertLogs(commands._LOGGER, level="WARNING") as logs:
                context = commands._daemon_context()
            self.assertEqual(context["tokens"], {})
            self.assertIn("daemon token ledger", logs.output[0])
            self.assertNotIn("private fixture", logs.output[0])


if __name__ == "__main__":
    unittest.main()
