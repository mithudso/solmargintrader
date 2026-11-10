from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ecosystem.backtests import backtest, batch_cells, create_batch, strategies
from ecosystem.data import acquire

START = "2020-01-01"
END = "2020-02-01"
EPOCH = 1577836800


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [EPOCH + i * 86400 for i in range(32)],
            "open": [10.0 + i / 10 for i in range(32)],
            "high": [11.0 + i / 10 for i in range(32)],
            "low": [9.0 + i / 10 for i in range(32)],
            "close": [10.5 + i / 10 for i in range(32)],
            "volume": [100.0] * 32,
        }
    )


class BacktestTests(unittest.TestCase):
    def test_all_registered_names_are_explicit(self):
        self.assertIn("lev_high", strategies())
        self.assertIn("trigger_trade", strategies())
        self.assertGreaterEqual(len(strategies()), 34)

    def test_costed_default_run_has_frozen_data_and_artifact_evidence(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase", return_value=frame()),
        ):
            receipt = acquire("SOL", Path(root) / "data", start=START, end=END)
            result = backtest("SOL", "buy_and_hold", receipt, Path(root) / "results")
            self.assertEqual(result["status"], "complete", result)
            self.assertEqual(result["fill_delay"], 1)
            self.assertEqual(result["costs"]["fee_bps"], 6)
            self.assertEqual(result["costs"]["slippage_bps"], 2)
            self.assertGreater(result["metrics"]["total_fees"], 0)
            self.assertGreater(result["trades"][0]["ts"], EPOCH)
            raw = Path(result["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), result["sha256"])
            self.assertEqual(json.loads(raw)["data_sha256"], receipt["sha256"])
            repeated = backtest("SOL", "buy_and_hold", receipt, Path(root) / "results")
            self.assertEqual(repeated["sha256"], result["sha256"])

    def test_missing_or_changed_input_cannot_be_a_completed_backtest(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase", return_value=frame()),
        ):
            receipt = acquire("SOL", Path(root) / "data", start=START, end=END)
            changed = {**receipt, "sha256": "0" * 64}
            self.assertEqual(
                backtest("SOL", "rsi", changed, root)["reason"], "data_digest_mismatch"
            )
            self.assertEqual(
                backtest("BTC", "rsi", receipt, root)["reason"], "data_context_mismatch"
            )
            self.assertEqual(
                backtest("SOL", "rsi", {"status": "blocked"}, root)["reason"],
                "verified_data_unavailable",
            )

    def test_batch_adapter_uses_existing_owner_and_preserves_explicit_matrix(self):
        from soltui.config import Settings

        with tempfile.TemporaryDirectory() as root:
            plan = create_batch(
                Settings(data_dir=str(Path(root) / "data")),
                ["BTC", "SOL"],
                root=Path(root) / "batches",
                intervals=("1d",),
                horizons=("medium",),
                strategy_ids=("buy_and_hold", "lev_low"),
            )
            self.assertEqual(plan["cells"], 4)
            cells = batch_cells(plan["run_id"], root=Path(root) / "batches")
            self.assertEqual(
                {(row["asset"], row["strategy"]) for row in cells},
                {
                    ("BTC", "buy_and_hold"),
                    ("SOL", "buy_and_hold"),
                    ("BTC", "lev_low"),
                    ("SOL", "lev_low"),
                },
            )
            self.assertTrue(all(row["state"] == "pending" for row in cells))


if __name__ == "__main__":
    unittest.main()
