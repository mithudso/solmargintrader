from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.strategy_config_sweep import (
    _derived_interval,
    _historical_base_settings,
    build_jobs,
    discover_assets,
)


class StrategyConfigSweepTests(unittest.TestCase):
    def test_historical_cpcv_disables_only_the_history_dependent_confidence_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = _historical_base_settings(Path(directory))

        self.assertEqual(settings["min_confidence"], 0.0)
        self.assertEqual(settings["fee_bps"], 6.0)
        self.assertEqual(settings["fill_delay"], 1)

    def test_all_buildable_cards_reach_ten_configs_on_daily_only_coin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candle = root / "SOL_1d.csv"
            candle.touch()
            jobs, coverage = build_jobs({"SOL": {"1d": candle}}, root / "out", derive=False)

            strategies = coverage["SOL"]["strategies"]
            self.assertEqual(len(strategies), 34)
            self.assertTrue(all(row["configurations"] >= 10 for row in strategies.values()))
            self.assertTrue(all(row["state"] == "ready" for row in strategies.values()))
            self.assertGreaterEqual(len(jobs), 34 * 10)
            self.assertTrue(any(job["profile"].startswith("engine-sensitivity:") for job in jobs))

    def test_asset_discovery_ignores_funding_files_and_unrelated_csvs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("SOL_1m.csv", "SOL_funding_1h.csv", "notes.csv", "XMR_1d.csv"):
                (root / name).touch()

            assets = discover_assets(root)

            self.assertEqual(set(assets), {"SOL", "XMR"})
            self.assertEqual(set(assets["SOL"]), {"1m"})

    def test_resampling_uses_epoch_seconds_and_drops_incomplete_buckets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "TST_1m.csv"
            timestamps = range(1_609_459_200, 1_609_459_200 + 61 * 60, 60)
            with source.open("w", encoding="utf-8") as handle:
                handle.write("timestamp,open,high,low,close,volume\n")
                for index, stamp in enumerate(timestamps):
                    handle.write(f"{stamp},1,2,0.5,{1 + index / 1000},3\n")

            derived = _derived_interval(source, "TST", "1h", root / "out")
            import pandas as pd

            rows = pd.read_csv(derived)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows.iloc[0]["timestamp"], 1_609_459_200)
            self.assertAlmostEqual(rows.iloc[0]["close"], 1.059)


if __name__ == "__main__":
    unittest.main()
