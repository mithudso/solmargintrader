from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ecosystem.data import acquire, universe

START = "2020-01-01"
END = "2020-01-05"
EPOCH = 1577836800


def frame(days: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [EPOCH + i * 86400 for i in range(days)],
            "open": [10.0 + i for i in range(days)],
            "high": [11.0 + i for i in range(days)],
            "low": [9.0 + i for i in range(days)],
            "close": [10.5 + i for i in range(days)],
            "volume": [100.0] * days,
        }
    )


class DataTests(unittest.TestCase):
    def test_universe_preserves_thirteen_owner_assets_and_removes_requested_symbols(self):
        self.assertEqual(len(universe()), 13)
        self.assertEqual(len(set(universe())), 13)
        self.assertTrue({"JITOSOL", "KMNO", "USDC"}.issubset(universe()))
        self.assertTrue({"RAIN", "WBT", "HTX", "JST", "MNT", "XMR"}.isdisjoint(universe()))

    def test_acquisition_has_exact_pair_proof_and_excludes_end_bar(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase", return_value=frame()) as fetch,
        ):
            result = acquire("sol", root, start=START, end=END)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["instrument"], "SOL/USD")
            self.assertEqual(result["venue"], "coinbase_exchange")
            self.assertEqual(result["coverage"]["bars"], 4)
            self.assertEqual(
                result["coverage"]["last_ts"] + 86400, result["requested_end_exclusive"]
            )
            fetch.assert_called_once_with("SOL-USD", START, END, "1d", verbose=False)
            receipt_path = Path(root) / "SOL_1d.receipt.json"
            self.assertEqual(
                json.loads(receipt_path.read_text())["sha256"], result["sha256"]
            )
            self.assertEqual(Path(result["path"]).stat().st_mode & 0o077, 0)

    def test_removed_asset_cannot_be_acquired(self):
        result = acquire("XMR", tempfile.gettempdir(), start=START, end=END)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "removed_asset")

    def test_offline_reuses_only_proven_identical_input(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase", return_value=frame()) as fetch,
        ):
            first = acquire("SOL", root, start=START, end=END)
            second = acquire("SOL", root, start=START, end=END, offline=True)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertTrue(second["cache_reused"])
            Path(first["path"]).write_text("corrupt")
            third = acquire("SOL", root, start=START, end=END, offline=True)
            self.assertEqual(third["status"], "blocked")
            self.assertEqual(
                third["reason"], "cache_receipt_mismatch_use_new_directory"
            )

    def test_unknown_raw_cache_is_not_relabelled(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase") as fetch,
        ):
            path = Path(root) / "BTC_1d.csv"
            frame().to_csv(path, index=False)
            before = path.read_bytes()
            result = acquire("BTC", root, start=START, end=END, offline=True)
            self.assertEqual(result["reason"], "verified_cache_unavailable")
            self.assertEqual(path.read_bytes(), before)
            fetch.assert_not_called()

    def test_missing_interior_or_boundary_bars_are_not_published(self):
        for data in (frame().drop(index=2), frame().iloc[1:]):
            with (
                self.subTest(),
                tempfile.TemporaryDirectory() as root,
                patch("ecosystem.data.fetch_coinbase", return_value=data),
            ):
                result = acquire("BTC", root, start=START, end=END)
                self.assertEqual(result["status"], "blocked")
                self.assertFalse((Path(root) / "BTC_1d.csv").exists())

    def test_changed_window_needs_new_directory(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase", return_value=frame()),
        ):
            first = acquire("SOL", root, start=START, end=END)
            before = Path(first["path"]).read_bytes()
            result = acquire("SOL", root, start="2020-01-02", end=END)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(Path(first["path"]).read_bytes(), before)

    def test_network_error_is_sanitized(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch(
                "ecosystem.data.fetch_coinbase", side_effect=ValueError("secret-token")
            ),
        ):
            result = acquire("SOL", root, start=START, end=END)
            self.assertEqual(result["status"], "blocked")
            self.assertNotIn("secret-token", json.dumps(result))

    def test_unsafe_symbol_and_unfinished_window_refuse_before_fetch(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("ecosystem.data.fetch_coinbase") as fetch,
        ):
            self.assertEqual(
                acquire("../../secret", root, start=START, end=END)["status"], "blocked"
            )
            self.assertEqual(
                acquire("SOL", root, start=START, end="2099-01-01")["status"], "blocked"
            )
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
