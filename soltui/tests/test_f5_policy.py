"""The frozen paper policy reaches the worker without changing safe defaults."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd

from backtester.core.engine import run_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from soltui import config, f5_batch, simulation
from soltui.runner import engine_config


class FrozenPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()

    def plan(self, settings):
        return f5_batch.create(
            settings,
            ["SOL"],
            root=self.root / "batches",
            intervals=["1d"],
            strategies=["buy_and_hold"],
            horizons=["medium"],
        )

    def frozen(self, plan):
        with closing(sqlite3.connect(Path(plan["directory"]) / "batch.sqlite3")) as db:
            return json.loads(
                db.execute("SELECT value FROM meta WHERE key='settings'").fetchone()[0]
            )

    def test_explicit_execution_and_scoring_settings_survive_create_and_restore(self):
        settings = config.Settings(
            data_dir=str(self.data),
            capital=3210.0,
            fee_bps=7.5,
            slippage_bps=1.2,
            fill_delay=2,
            cpcv_groups=6,
            cpcv_k=3,
            fee_schedule="jupiter-perps",
            use_leverage=True,
            leverage=3.0,
            allow_short=True,
            min_confidence=0.65,
            borrow_long_bps_hour=0.11,
            borrow_short_bps_hour=0.06,
        )
        frozen = self.frozen(self.plan(settings))
        restored = f5_batch._settings(frozen)
        self.assertEqual(
            simulation.from_settings(restored), simulation.from_settings(settings)
        )
        for name in ("capital", "fill_delay", "cpcv_groups", "cpcv_k"):
            self.assertEqual(getattr(restored, name), getattr(settings, name))
        self.assertEqual(restored.data_dir, str(self.data.resolve()))
        self.assertNotIn("armed", frozen)
        self.assertNotIn("solana_address", frozen)
        self.assertNotIn("btc_xpub", frozen)

    def test_legacy_frozen_settings_still_use_original_eighty_percent_policy(self):
        defaults = config.Settings(data_dir=str(self.data))
        legacy = {
            name: getattr(defaults, name)
            for name in (
                "capital",
                "fee_bps",
                "slippage_bps",
                "fill_delay",
                "cpcv_groups",
                "cpcv_k",
                "data_dir",
            )
        }
        legacy.update(start="", end="")
        restored = f5_batch._settings(legacy)
        self.assertEqual(restored.min_confidence, 0.80)
        self.assertEqual(simulation.from_settings(restored), simulation.Execution())
        self.assertEqual(config.Settings().min_confidence, 0.80)
        self.assertFalse(restored.armed)
        self.assertEqual(restored.mode, "dry-run")

    def test_real_f5_costed_raw_baseline_trades_while_eighty_percent_abstains(self):
        # Flat synthetic bars deliberately produce no successful cost-adjusted
        # confidence samples. Raw buy-and-hold loses costs; it is not a good bot.
        count = 320
        arrays = {
            "ts": np.arange(count, dtype="int64") * 86400 + 1577836800,
            **{
                name: np.full(count, 100.0) for name in ("open", "high", "low", "close")
            },
            "volume": np.full(count, 1000.0),
        }
        pd.DataFrame(
            {
                "timestamp": arrays["ts"],
                **{key: value for key, value in arrays.items() if key != "ts"},
            }
        ).to_csv(self.data / "SOL_1d.csv", index=False)
        raw = config.Settings(data_dir=str(self.data), min_confidence=0.0)
        gated = replace(raw, min_confidence=0.80)
        observed = {}
        for name, settings in (("raw", raw), ("gated", gated)):
            plan = self.plan(settings)
            tick = Mock(
                return_value={"recorded": 0, "rows": [], "message": "isolated test"}
            )
            f5_batch.run(
                plan["run_id"], root=self.root / "batches", tick=tick, forward_cycles=1
            )
            cells = f5_batch.cells(plan["run_id"], root=self.root / "batches")
            attempts = f5_batch.attempts(
                plan["run_id"], cells[0]["id"], root=self.root / "batches"
            )
            observed[name] = (cells[0], attempts)
        raw_cell, raw_attempts = observed["raw"]
        gated_cell, gated_attempts = observed["gated"]
        self.assertEqual(raw_cell["state"], "completed")
        self.assertTrue(all(item["result"]["evaluable"] for item in raw_attempts))
        self.assertTrue(all(item["result"]["trades"] >= 10 for item in raw_attempts))
        self.assertTrue(
            all(item["result"]["median_return"] < 0 for item in raw_attempts)
        )
        self.assertEqual(gated_cell["state"], "failed")
        self.assertTrue(
            all(item["state"] == "not_evaluable" for item in gated_attempts)
        )
        self.assertTrue(all(item["result"]["trades"] == 0 for item in gated_attempts))
        # Independently verify that the same policy charges actual paper fees.
        result = run_backtest(
            simulation.gate(BuyAndHold(), raw), arrays, engine_config(raw)
        )
        self.assertGreater(result.metrics.total_fees, 0)
        self.assertGreater(result.metrics.total_borrow_fees, 0)
        self.assertLess(result.metrics.total_return, 0)


if __name__ == "__main__":
    unittest.main()
