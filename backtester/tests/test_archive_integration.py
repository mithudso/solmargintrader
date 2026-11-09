from __future__ import annotations

import io
import csv
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backtester.core import plotting

from backtester.cli import main
from backtester.core.history_store import import_history
from backtester.core.run_archive import read_run


class ArchiveIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(plotting.charts_available(), "optional matplotlib is unavailable")
    def test_chart_uses_explicit_quote_currency(self):
        import numpy as np
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            result = SimpleNamespace(timestamps=np.array([0, 86400]), equity=np.array([100., 101.]),
                                     exposure=np.array([0., 1.]), strategy_name="fixture", mode="spot")
            with patch("matplotlib.axes.Axes.set_ylabel", autospec=True) as label:
                plotting.plot_comparison([result], temporary, "SOL", quote_currency="USDC")
            self.assertIn("Equity (USDC)", [call.args[1] for call in label.call_args_list])

    def test_snapshot_to_backtest_to_verified_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bars_path = root / "bars.csv"
            start = 1609459200
            bars_path.write_text("timestamp,open,high,low,close,volume\n" + "".join(
                f"{start + i * 86400},10,12,9,11,5\n" for i in range(70)))
            history = root / "history.db"
            snapshot = import_history(history, bars_path, instrument="SOL-USDC", venue="fixture",
                                      source="synthetic fixture", interval_seconds=86400)
            out = root / "results"
            runs = root / "runs.db"
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                status = main(["--asset", "SOL", "--quote", "USDC", "--strategy", "all", "--start", "2021-01-01",
                               "--history-archive", str(history), "--snapshot-id", snapshot,
                               "--out", str(out), "--archive", str(runs), "--no-charts"])
            self.assertEqual(status, 0, stderr.getvalue())
            run_id = next(line.split(": ", 1)[1] for line in stderr.getvalue().splitlines()
                          if line.startswith("Archived run: "))
            manifest, artifacts = read_run(runs, run_id)
            self.assertIn(snapshot.encode(), manifest)
            self.assertEqual(json.loads(manifest)["quote_currency"], "USDC")
            self.assertEqual(json.loads(manifest)["first_bar_ts"], start)
            self.assertEqual(json.loads(manifest)["last_bar_ts"], start + 69 * 86400)
            self.assertIn(b"monetary values are in USDC; no USD conversion", artifacts["report.md"])
            self.assertIn("comparison.csv", artifacts)
            self.assertIn("equity_buy_and_hold.csv", artifacts)
            trades = list(csv.DictReader(io.StringIO(artifacts["trades_buy_and_hold.csv"].decode())))
            # 10,000 USDC buys at 10, paying 8 bps; close at 11 pays 8 bps again.
            expected = (10_000 / 1.0008) * (11 / 10) * (1 - 0.0008)
            self.assertEqual(len(trades), 2)
            self.assertAlmostEqual(float(trades[-1]["equity_after"]), expected, places=8)
            self.assertAlmostEqual(float(trades[-1]["realized_pnl"]), expected - 10_000, places=8)


if __name__ == "__main__":
    unittest.main()
