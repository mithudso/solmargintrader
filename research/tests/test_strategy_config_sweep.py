from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.strategy_config_sweep import (
    _derived_interval,
    _historical_base_settings,
    _preflight_manifest,
    _read_done,
    _record,
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
            timestamps = list(range(1_609_459_200, 1_609_459_200 + 61 * 60, 60))
            timestamps[0], timestamps[1] = timestamps[1], timestamps[0]
            with source.open("w", encoding="utf-8") as handle:
                handle.write("timestamp,open,high,low,close,volume\n")
                for index, stamp in enumerate(timestamps):
                    handle.write(f"{stamp},1,2,0.5,{1 + index / 1000},3\n")

            derived = _derived_interval(source, "TST", "1h", root / "out")
            import pandas as pd

            rows = pd.read_csv(derived)
            marker = derived.with_suffix(derived.suffix + ".source.json")
            self.assertEqual(json.loads(marker.read_text())["aggregation_version"], 4)
            self.assertEqual(json.loads(marker.read_text())["exact_duplicate_rows_removed"], 0)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows.iloc[0]["timestamp"], 1_609_459_200)
            self.assertAlmostEqual(rows.iloc[0]["close"], 1.059)

    def test_resampling_rejects_duplicate_timestamp_even_when_bucket_row_count_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "TST_1m.csv"
            timestamps = list(range(1_609_459_200, 1_609_459_200 + 60 * 60, 60))
            timestamps[-1] = timestamps[-2]
            with source.open("w", encoding="utf-8") as handle:
                handle.write("timestamp,open,high,low,close,volume\n")
                for index, stamp in enumerate(timestamps):
                    handle.write(f"{stamp},1,2,0.5,{1 + index / 1000},3\n")

            with self.assertRaisesRegex(ValueError, "duplicate timestamp"):
                _derived_interval(source, "TST", "1h", root / "out")

    def test_resampling_removes_only_exact_duplicate_rows_before_completeness_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "TST_1m.csv"
            timestamps = list(range(1_609_459_200, 1_609_459_200 + 60 * 60, 60))
            timestamps[-1] = timestamps[-2]
            with source.open("w", encoding="utf-8") as handle:
                handle.write("timestamp,open,high,low,close,volume\n")
                for stamp in timestamps:
                    handle.write(f"{stamp},1,2,0.5,1.5,3\n")

            with self.assertRaisesRegex(ValueError, "no complete 1h bars"):
                _derived_interval(source, "TST", "1h", root / "out")

    def test_record_recovers_unterminated_tail_before_appending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            _record(path, {"configuration_id": "kept"})
            with path.open("ab") as handle:
                handle.write(b'{"configuration_id":"partial')

            _record(path, {"configuration_id": "new"})

            self.assertEqual(_read_done(path), {"kept", "new"})

    def test_preflight_rejects_changed_sources_before_derived_cache_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "out" / "manifest.json"
            manifest.parent.mkdir()
            manifest.write_text('{"schema_version": 2, "sources": {"old": "hash"}}')

            with self.assertRaisesRegex(ValueError, "does not match"):
                _preflight_manifest(
                    manifest,
                    data_dir=root,
                    sources={"new": "hash"},
                    code={},
                    base_settings={},
                )

    def test_preflight_rejects_orphaned_derived_artifacts_without_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            orphan = root / "out" / "derived" / "TST_1h.csv"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("old derived data")

            with self.assertRaisesRegex(ValueError, "no manifest"):
                _preflight_manifest(
                    root / "out" / "manifest.json",
                    data_dir=root,
                    sources={},
                    code={},
                    base_settings={},
                )


if __name__ == "__main__":
    unittest.main()
