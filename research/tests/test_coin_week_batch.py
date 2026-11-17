"""Native quote identity, full combination census, gaps and explicit reports."""

from __future__ import annotations

import copy
import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research import coin_week
from research import coin_week_batch as batch
from research import coin_week_correlations as corr
from research.coin_week_data import (
    analysis_window,
    candle_url,
    download,
    load,
    save,
    verify_snapshot,
)
from research.coin_week_reports import MODE_LABELS, policy_details, resolved_policy
from research.tests.test_coin_week import candles


def catalogue():
    return [
        {
            "id": product,
            "base_currency": base,
            "quote_currency": quote,
            "status": status,
            "trading_disabled": status != "online",
        }
        for base, quote, product, status in (
            ("ETH", "USD", "ETH-USD", "online"),
            ("BTC", "USD", "BTC-USD", "online"),
            ("ZEC", "USD", "ZEC-USD", "online"),
            ("ETH", "BTC", "ETH-BTC", "online"),
            ("ZEC", "BTC", "ZEC-BTC", "delisted"),
        )
    ]


def options(**updates):
    value = {
        "coins": ["ETH,BTC,ZEC"],
        "coin": None,
        "quote": "USD",
        "venue": "coinbase",
        "gap_policy": None,
        "phase": "fetch",
        "resume": False,
        "workers": 1,
        "replicates": 199,
        "candidate_limit": 1,
        "days": 7,
        "end": "2026-11-16T00:00:00Z",
    }
    return SimpleNamespace(**{**value, **updates})


class NativeMarketTests(unittest.TestCase):
    def test_quote_changes_actual_url_and_raw_snapshot_identity(self):
        self.assertIn("/ETH-USD/candles", candle_url("ETH", 0, 60, quote="USD"))
        self.assertIn("/ETH-BTC/candles", candle_url("ETH", 0, 60, quote="BTC"))
        self.assertIn("symbol=ETHBTC", candle_url("ETH", 0, 60, "binance", "BTC"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ETH.json.zlib"
            source = download(
                "ETH",
                0,
                60,
                path,
                quote="BTC",
                get=lambda _: b"[[0,9,12,10,11,2]]",
                pause=lambda _: None,
            )
            self.assertEqual(source["product"], "ETH-BTC")
            verify_snapshot(source, "ETH", 0, 60, "BTC")
            with self.assertRaisesRegex(ValueError, "quote mismatch"):
                verify_snapshot(source, "ETH", 0, 60, "USD")
            with self.assertRaisesRegex(ValueError, "quote mismatch"):
                download("ETH", 0, 60, path, quote="USD")

    def test_no_self_pairs_or_ticker_injection(self):
        for quote in ("ETH", "../USD", "USD?token=1"):
            with self.assertRaises(ValueError):
                candle_url("ETH", 0, 60, quote=quote)

    def test_coin_list_accepts_commas_spaces_and_deduplicates(self):
        self.assertEqual(
            batch.coin_list(["eth,btc", "ZEC", "ETH"]), ["ETH", "BTC", "ZEC"]
        )
        for tokens in ([], [""], ["ETH/USD"], [f"C{i}" for i in range(13)]):
            with self.assertRaises(ValueError):
                batch.coin_list(tokens)

    def test_all_combinations_include_cash_and_real_reverse_orientation(self):
        products = batch.catalogue_rows(json.dumps(catalogue()).encode(), "coinbase")
        rows = batch.combinations(["ETH", "BTC", "ZEC"], "USD", products)
        self.assertEqual(len(rows), 6)
        by_pair = {r["requested_pair"]: r for r in rows}
        self.assertEqual(by_pair["ETH/BTC"]["product"], "ETH-BTC")
        self.assertEqual(by_pair["BTC/ZEC"]["product"], "ZEC-BTC")
        self.assertEqual(by_pair["BTC/ZEC"]["status"], "inactive")
        self.assertEqual(by_pair["ETH/ZEC"]["status"], "not_listed")
        self.assertEqual(sum(r["status"] == "planned" for r in rows), 4)
        self.assertEqual(
            batch.combinations(["USD", "BTC", "ETH", "BTC"], "USD", products)[2][
                "product"
            ],
            "ETH-BTC",
        )

    def test_active_reverse_listing_wins_over_inactive_forward(self):
        products = [
            {
                "base": "ETH",
                "quote": "BTC",
                "product": "ETH-BTC",
                "active": False,
                "venue_status": "delisted",
            },
            {
                "base": "BTC",
                "quote": "ETH",
                "product": "BTC-ETH",
                "active": True,
                "venue_status": "online",
            },
        ]
        rows = batch.combinations(["ETH", "BTC"], "USD", products)
        self.assertEqual(rows[0]["product"], "BTC-ETH")
        self.assertEqual(rows[0]["status"], "planned")

    def test_binance_requires_an_active_spot_listing(self):
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "baseAsset": "ETH",
                        "quoteAsset": "BTC",
                        "symbol": "ETHBTC",
                        "status": "TRADING",
                        "isSpotTradingAllowed": True,
                    },
                    {
                        "baseAsset": "ZEC",
                        "quoteAsset": "BTC",
                        "symbol": "ZECBTC",
                        "status": "BREAK",
                        "isSpotTradingAllowed": False,
                    },
                ]
            }
        ).encode()
        rows = batch.catalogue_rows(raw, "binance")
        self.assertEqual([r["active"] for r in rows], [True, False])

    def test_catalogue_provenance_and_duplicates_are_checked(self):
        body = json.dumps(catalogue()).encode()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(batch, "read_url", return_value=body),
        ):
            source = batch.acquire_catalogue(
                "coinbase", Path(directory) / "catalogue.json.zlib"
            )
        bad = copy.deepcopy(source)
        bad["raw"] += " "
        with self.assertRaisesRegex(ValueError, "integrity"):
            batch.verify_catalogue(bad, "coinbase")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            batch.catalogue_rows(
                json.dumps(catalogue() + catalogue()[:1]).encode(), "coinbase"
            )


class BatchAcquisitionTests(unittest.TestCase):
    def test_child_market_lock_prevents_standalone_cli_write_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / "markets" / "ETH-USD"
            child.mkdir(parents=True)
            with (child / "run.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    batch.study_market(root, {}, {"base": "ETH", "quote": "USD"}, [], 1)
            self.assertFalse((child / "run-plan.json.zlib").exists())

    def test_downloads_each_native_market_once_and_freezes_all_six_pairs(self):
        acquired = []

        def fetch(base, start, stop, path, *, provider, quote):
            acquired.append((base, quote, provider))
            save(path, {"coin": base, "quote": quote})

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                batch, "read_url", return_value=json.dumps(catalogue()).encode()
            ),
            patch.object(batch, "download", side_effect=fetch),
            patch.object(coin_week, "identity", return_value={"test": "identity"}),
            patch.object(
                coin_week.expanded, "catalogue", return_value={"candidates": []}
            ),
        ):
            root = Path(directory)
            self.assertEqual(batch.run_batch(options(), root), 0)
            plan = load(root / "batch-plan.json.zlib")
            self.assertEqual(len(plan["markets"]), 6)
            self.assertEqual(len(acquired), 4)
            self.assertEqual(len(set(acquired)), 4)
            self.assertIn(("ETH", "USD", "coinbase"), acquired)
            self.assertIn(("ETH", "BTC", "coinbase"), acquired)
            self.assertFalse((root / "batch-manifest.json").exists())
            self.assertIn("not_listed", (root / "report.md").read_text())

    def test_network_failure_is_partial_failure_not_absent_listing(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                batch, "read_url", return_value=json.dumps(catalogue()).encode()
            ),
            patch.object(batch, "download", side_effect=OSError("HTTP 503")),
            patch.object(coin_week, "identity", return_value={"test": "identity"}),
            patch.object(
                coin_week.expanded, "catalogue", return_value={"candidates": []}
            ),
        ):
            root = Path(directory)
            self.assertEqual(batch.run_batch(options(), root), 1)
            summary = load(root / "batch-summary.json")
            self.assertEqual(summary["failed_markets"], 4)
            self.assertEqual(summary["status"], "partial")
            self.assertFalse((root / "batch-manifest.json").exists())
            with self.assertRaisesRegex(ValueError, "coins do not match"):
                batch.run_batch(options(coins=["ETH", "SOL"], resume=True), root)

    def test_frozen_batch_detects_replaced_acquisition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root / "batch-plan.json.zlib", {"plan": "fixed"})
            save(root / "market-catalogue.json.zlib", {"catalogue": "fixed"})
            market = root / "shared-inputs" / "ETH-USD.json.zlib"
            save(market, {"candles": "first"})
            batch.frozen_ledger(root)
            save(market, {"candles": "replacement"})
            with self.assertRaisesRegex(ValueError, "batch inputs changed"):
                batch.frozen_ledger(root)


class GapAndInferenceTests(unittest.TestCase):
    def test_sparse_reference_cannot_disable_target_only_tests(self):
        frame = candles(5000)
        target = corr.analyze(frame, {}, 19)
        thin = corr.analyze(frame, {"THIN": frame.iloc[:1]}, 19)
        own = [r for r in thin["rows"] if not r["feature"].startswith("THIN_")]
        by_key = lambda rows: {
            (r["split"], r["feature"], r["horizon_minutes"]): r for r in rows
        }
        original = by_key(target["rows"])
        for key, row in by_key(own).items():
            self.assertEqual(row["pearson"], original[key]["pearson"])
            self.assertEqual(row["n"], original[key]["n"])
            self.assertEqual(row["status"], original[key]["status"])
            if "p_maxT_validation_and_test" in row:
                self.assertGreaterEqual(
                    row["p_maxT_validation_and_test"], row["p_block_permutation"]
                )
        self.assertTrue(
            all(
                r["status"].startswith("insufficient")
                for r in thin["rows"]
                if r["feature"].startswith("THIN_")
            )
        )
        self.assertTrue(thin["training_only_shortlist"])
        json.dumps(thin, allow_nan=False)

    def test_longest_window_never_bridges_missing_minutes_and_ties_use_clock(self):
        frame = candles(12).drop(index=[4, 9, 10, 11])
        actual, window = analysis_window(frame, 0, 12 * 60, "longest")
        self.assertEqual(actual.timestamp.tolist(), [0, 60, 120, 180])
        self.assertEqual(window["excluded_observed_minutes"], 4)
        self.assertFalse(window["complete_requested_window"])
        poison = frame.copy()
        poison.loc[poison.timestamp >= 300, "close"] *= 100
        self.assertEqual(analysis_window(poison, 0, 720, "longest")[1], window)
        with self.assertRaisesRegex(ValueError, "missing minutes"):
            analysis_window(frame, 0, 720, "strict")

    def test_batch_correction_covers_every_planned_pair_without_changing_effects(self):
        frame = candles(3000)
        one = corr.analyze(frame, {}, 19)
        many = corr.analyze(frame, {}, 19, family_multiplier=6)
        for a, b in zip(one["rows"], many["rows"]):
            self.assertEqual(a["pearson"], b["pearson"])
            if "p_familywise" in a:
                self.assertEqual(
                    b["p_familywise"], min(1, 6 * a["p_maxT_validation_and_test"])
                )
        with self.assertRaises(ValueError):
            corr.analyze(frame, {}, 19, family_multiplier=0)


class ExplicitReportTests(unittest.TestCase):
    def test_report_names_market_dates_strategy_parameters_and_linear_filter(self):
        config = {
            "mode": "single",
            "members": [{"strategy": "rsi", "params": {"period": 7}}],
            "persistence": 2,
            "rebalance_threshold": 0.05,
        }
        resolved = resolved_policy(config, 60)
        row = {
            "interval": "1m",
            "fee_bps_per_fill": 10,
            "candidate_id": "rsi-test",
            "mode": "linear_control",
            "config": config,
            "resolved_config": resolved,
            "splits": {
                s: {"total_return": 0.01, "trade_count": 11}
                for s in ("validation", "test")
            },
        }
        summary = {
            "version": "2.0.0",
            "plan": {
                "coin": "ETH",
                "quote": "USD",
                "venue": "Coinbase Exchange spot",
                "start": 0,
                "end_exclusive": 180000,
                "templates": 1,
                "candidate_limit": 1,
                "replicates": 199,
            },
            "market": {"product": "ETH-USD", "initial_reference_equity_quote": 10000},
            "analysis_window": {
                "requested_minutes": 3000,
                "observed_minutes": 2999,
                "analyzed_minutes": 2000,
                "analysis_start": 60000,
                "analysis_end_exclusive": 180000,
                "complete_requested_window": False,
                "excluded_observed_minutes": 999,
                "policy": "longest",
            },
            "correlations": {
                "features": ["return_1m"],
                "corrected_test_findings": 0,
                "family_multiplier": 6,
                "contemporaneous": [],
                "training_only_shortlist": [],
            },
            "strategies": [{"selected": [row]}],
            "strategy_rows": 100,
            "strategy_completed": 90,
            "special_rows": 40,
            "cycle_tests": 100,
            "minimum_cycle_p_holm": 1,
            "cycle_resolution_floor": 0.5,
        }
        text = coin_week.text_report(summary)
        for phrase in (
            "ETH/USD",
            "ETH-USD",
            "REDUCED WINDOW",
            "INCOMPLETE SMOKE TEST",
            "rsi",
            '"period": 7',
            "regression slope filter",
            "64",
            "16",
            "persistence=2",
            "0.05",
            "6 planned market combinations",
            "10,000 USD",
            "separate from market backtests",
        ):
            self.assertIn(phrase, text)
        self.assertEqual(len(MODE_LABELS), 6)
        old = copy.deepcopy(summary)
        old["version"] = "1.0.0"
        old["minutes"] = 2000
        self.assertEqual(coin_week.text_report(old), coin_week.legacy_text_report(old))
        self.assertIn("Version: 1.0.0", coin_week.text_report(old))

    def test_defaults_and_volatility_scaling_are_resolved_for_report(self):
        config = {
            "mode": "single",
            "members": [{"strategy": "voltarget", "params": {}}],
            "persistence": 1,
            "rebalance_threshold": 0,
        }
        one = resolved_policy(config, 60)["members"][0]["params"]
        hour = resolved_policy(config, 3600)["members"][0]["params"]
        self.assertAlmostEqual(hour["target_vol"] / one["target_vol"], 60**0.5)
        self.assertEqual(config["members"][0]["params"], {})
        self.assertIn("target_vol", policy_details(resolved_policy(config, 60)))


if __name__ == "__main__":
    unittest.main()
