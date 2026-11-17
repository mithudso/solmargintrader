"""Weekly acquisition, temporal isolation and broad-search inference contracts."""

from __future__ import annotations

import copy
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

from research import coin_week_correlations as corr
from research.coin_week import (
    bind_files,
    coverage,
    cycle_study,
    evaluation_windows,
    frozen_inputs,
    scalar_spot_check,
    special_models,
    verify_binding,
)
from research.coin_week_data import (
    COLUMNS,
    arrays,
    coin_symbol,
    download,
    page_rows,
    read_url,
    resample,
    save,
    verify_snapshot,
    week_bounds,
)
from research.zec_ensembles import batch_spot


def candles(n=720, seed=47):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    opening = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {
            "timestamp": np.arange(n) * 60,
            "open": opening,
            "high": np.maximum(opening, close) * 1.0002,
            "low": np.minimum(opening, close) * 0.9998,
            "close": close,
            "volume": rng.uniform(1, 100, n),
        }
    )


class AcquisitionTests(unittest.TestCase):
    def test_binance_open_and_close_time_contract_and_quote_identity(self):
        raw = (
            b'[[0,"10","12","9","11","2",59999],[60000,"11","13","10","12","3",119999]]'
        )
        self.assertEqual(
            page_rows(raw, 0, 60, "binance"), [[0, 10.0, 12.0, 9.0, 11.0, 2.0]]
        )
        with self.assertRaisesRegex(ValueError, "closed-minute"):
            page_rows(raw.replace(b"59999", b"60000"), 0, 60, "binance")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ETH.json.zlib"
            result = download(
                "ETH",
                0,
                120,
                path,
                get=lambda _: raw,
                pause=lambda _: None,
                provider="binance",
            )
            self.assertEqual(
                (result["venue"], result["quote"], result["product"]),
                ("Binance spot", "USDT", "ETHUSDT"),
            )
            self.assertEqual(len(verify_snapshot(result, "ETH", 0, 120)), 2)
            with self.assertRaisesRegex(ValueError, "never mix venues"):
                download("ETH", 0, 120, path, provider="coinbase")

    def test_real_http_429_retry_normalizes_response_and_records_attempts(self):
        statuses = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status = 429 if not statuses else 200
                statuses.append(status)
                self.send_response(status)
                self.end_headers()
                self.wfile.write(b"[[0,9,12,10,11,2]]")

            def log_message(self, *_):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with tempfile.TemporaryDirectory() as directory:
                    result = download(
                        "ETH",
                        0,
                        60,
                        Path(directory) / "ETH.json.zlib",
                        get=lambda _: read_url(
                            f"http://127.0.0.1:{server.server_port}/candles"
                        ),
                        pause=lambda _: None,
                    )
            finally:
                server.shutdown()
                worker.join(3)
        self.assertEqual(statuses, [429, 200])
        self.assertEqual(result["rows"], [[0, 10.0, 12.0, 9.0, 11.0, 2.0]])

    def test_coinbase_layout_is_mapped_by_name_and_bounds_are_exclusive(self):
        raw = json.dumps(
            [[120, 98, 105, 101, 103, 4], [60, 90, 108, 100, 102, 5]]
        ).encode()
        self.assertEqual(
            page_rows(raw, 60, 120), [[60, 100.0, 108.0, 90.0, 102.0, 5.0]]
        )

    def test_bad_rows_and_conflicting_duplicates_refuse(self):
        for rows in (
            [[[0, 1, 4, 2, 3]]],
            [[0, 1, 4, 2, 3, -1]],
            [[0, 1, 4, 2, 3, 1], [0, 1, 4, 2, 3, 2]],
            [[1, 1, 4, 2, 3, 1]],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                page_rows(json.dumps(rows).encode(), 0, 120)

    def test_week_uses_only_completed_minutes_and_utc_aware_end(self):
        now = datetime(2026, 11, 17, 17, 2, 41, tzinfo=UTC)
        start, stop = week_bounds(now=now)
        self.assertEqual(stop - start, 10080 * 60)
        self.assertEqual(stop, int(now.timestamp()) // 60 * 60)
        for end in (
            "2026-11-17T17:03:00Z",
            "2026-11-17T17:02:01Z",
            "2026-11-17T17:00:00",
        ):
            with self.assertRaises(ValueError):
                week_bounds(end, now=now)

    def test_completed_snapshot_revalidates_raw_pages_without_network(self):
        raw = json.dumps([[60, 9, 12, 10, 11, 2], [0, 9, 12, 10, 11, 3]]).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ETH.json.zlib"
            first = download(
                "ETH", 0, 120, path, get=lambda _: raw, pause=lambda _: None
            )
            second = download(
                "ETH", 0, 120, path, get=lambda _: self.fail("unexpected network")
            )
            self.assertEqual(first, second)
            bad = copy.deepcopy(second)
            bad["rows"][0][4] = 10.5
            with self.assertRaisesRegex(ValueError, "normalized candles"):
                verify_snapshot(bad, "ETH", 0, 120)
            bad = copy.deepcopy(second)
            bad["pages"][0]["raw"] += " "
            with self.assertRaisesRegex(ValueError, "integrity"):
                verify_snapshot(bad, "ETH", 0, 120)

    def test_empty_minutes_are_recorded_and_never_filled(self):
        raw = json.dumps([[0, 9, 12, 10, 11, 0]]).encode()
        with tempfile.TemporaryDirectory() as directory:
            result = download(
                "ETH",
                0,
                120,
                Path(directory) / "ETH.json.zlib",
                get=lambda _: raw,
                pause=lambda _: None,
            )
        self.assertEqual(result["coverage"]["missing_minutes"], [60])
        self.assertEqual(result["coverage"]["zero_volume_minutes"], 1)
        self.assertEqual(len(result["rows"]), 1)

    def test_429_retry_is_bounded_and_keeps_attempts(self):
        attempts = []

        def get(url):
            attempts.append(url)
            if len(attempts) == 1:
                raise urllib.error.HTTPError(url, 429, "rate limit", {}, None)
            return b"[[0,9,12,10,11,2]]"

        with tempfile.TemporaryDirectory() as directory:
            result = download(
                "ETH",
                0,
                60,
                Path(directory) / "ETH.json.zlib",
                get=get,
                pause=lambda _: None,
            )
        self.assertEqual([r["status"] for r in result["attempts"]], ["429", "200"])

    def test_interrupted_acquisition_resumes_only_unfetched_pages(self):
        raw = b"[[0,9,12,10,11,2]]"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ETH.json.zlib"

            def fail_second(url):
                if urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["start"] == [
                    "1970-01-01T04:59:00Z"
                ]:
                    raise urllib.error.HTTPError(url, 404, "unavailable", {}, None)
                return raw

            with self.assertRaises(urllib.error.HTTPError):
                download(
                    "ETH", 0, 300 * 60, path, get=fail_second, pause=lambda _: None
                )
            calls = []

            def last(url):
                calls.append(url)
                return b"[[17940,9,12,10,11,2]]"

            result = download("ETH", 0, 300 * 60, path, get=last, pause=lambda _: None)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(result["pages"]), 2)
            self.assertFalse(path.with_name(path.name + ".partial").exists())

    def test_ticker_cannot_inject_a_product_path(self):
        self.assertEqual(coin_symbol("eth"), "ETH")
        for value in ("ETH-USD", "../ETH", "ETH?x=1"):
            with self.assertRaises(ValueError):
                coin_symbol(value)


class TemporalTests(unittest.TestCase):
    def test_trigger_absolute_entry_index_survives_long_research_prefix(self):
        from backtester.core.strategies import build
        from backtester.core.types import BarWindow
        from backtester.core.zec_ensemble import _Member

        frame = candles(6600)
        data = arrays(frame)
        spec = {
            "strategy": "trigger_trade",
            "params": {"conditions": "consec_dn3", "horizon": 2},
        }
        member, reference = (
            _Member(spec, interval="1m"),
            build("trigger_trade", **spec["params"]),
        )
        triggered_after_limit = False
        for i in range(len(frame)):
            window = BarWindow(
                *(data[k] for k in ("ts", "open", "high", "low", "close", "volume")), i
            )
            actual = member.step(window)
            expected = reference.on_bar(window) if i >= reference.warmup_bars() else 0.0
            self.assertEqual(actual, expected)
            triggered_after_limit |= i > member.limit and expected > 0
        self.assertTrue(triggered_after_limit)

    def test_resampling_drops_partial_and_missing_buckets(self):
        frame = candles(17).drop(index=7)
        out = resample(frame, 300)
        self.assertEqual(list(out.timestamp), [0, 600])
        self.assertAlmostEqual(out.iloc[1].volume, frame.loc[10:14, "volume"].sum())
        self.assertEqual(list(out.columns), list(COLUMNS))

    def test_features_are_unchanged_by_poisoned_future_prices_or_volume(self):
        frame = candles(500)
        before = corr.features(frame, {"BTC": frame})
        poison = frame.copy()
        poison.loc[301:, ["open", "high", "low", "close", "volume"]] *= 100
        after = corr.features(poison, {"BTC": poison})
        pd.testing.assert_frame_equal(before.iloc[:301], after.iloc[:301])

    def test_missing_reference_minute_invalidates_full_lag(self):
        frame = candles(300)
        out = corr.features(frame, {"BTC": frame.drop(index=100)})
        self.assertTrue(out["BTC_return_15m"].iloc[100:116].isna().all())
        self.assertTrue(np.isfinite(out["BTC_return_15m"].iloc[116]))

    def test_forward_returns_cannot_cross_split_end_and_do_not_overlap(self):
        for left, right in corr.split_indices(10080).values():
            for horizon in corr.HORIZONS:
                i = corr.sample_indices(10080, horizon, left, right)
                self.assertTrue(np.all(i + horizon < right))
                self.assertTrue(np.all(np.diff(i) == horizon))

    def test_aggregate_candles_cannot_cross_evaluation_boundaries(self):
        frame = resample(candles(1000), 600)
        plan = {"start": 0, "end_exclusive": 1000 * 60}
        lo, hi = evaluation_windows(frame, plan, 600)["validation"]
        self.assertGreaterEqual(frame.timestamp.iloc[lo], 600 * 60)
        self.assertLessEqual(frame.timestamp.iloc[hi - 1] + 600, 800 * 60)

    def test_spot_accounting_matches_canonical_at_every_cost_on_custom_cadence(self):
        frame = resample(candles(600), 600)
        data = arrays(frame)
        target = (np.arange(len(frame)) % 3 == 0).astype(float)
        for fee in (10, 15, 25, 60):
            batch = batch_spot(target, data, "1m", cost_multiplier=(fee + 2) / 12)[0]
            scalar = scalar_spot_check(
                target, data, "10m", threshold=0, multiplier=(fee + 2) / 12
            )
            self.assertAlmostEqual(
                batch["total_return"], scalar["total_return"], places=10
            )
            self.assertLess(batch["total_return"], 0)


class CorrelationTests(unittest.TestCase):
    def test_planted_lead_is_found_after_full_search_correction(self):
        n = 4800
        rng = np.random.default_rng(235)
        returns = rng.normal(0, 0.001, n)
        reference = candles(n)
        reference["close"] = 100 * np.exp(np.cumsum(returns))
        primary = candles(n, 14)
        primary["close"] = 100 * np.exp(
            np.cumsum(np.r_[0, returns[:-1]] + rng.normal(0, 0.0001, n))
        )
        result = corr.analyze(primary, {"BTC": reference}, 199)
        row = next(
            r
            for r in result["rows"]
            if r["feature"] == "BTC_return_1m"
            and r["horizon_minutes"] == 1
            and r["split"] == "test"
        )
        self.assertGreater(row["pearson"], 0.98)
        self.assertLessEqual(row["p_maxT_validation_and_test"], 0.05)
        self.assertGreaterEqual(
            row["p_maxT_validation_and_test"], row["p_block_permutation"]
        )

    def test_holdout_poison_cannot_change_training_shortlist(self):
        primary = candles(3000)
        first = corr.analyze(primary, {}, 19)
        poison = primary.copy()
        poison.loc[2400:, "close"] *= np.exp(np.linspace(0, 0.2, 600))
        second = corr.analyze(poison, {}, 19)
        extract = lambda r: [
            (x["feature"], x["horizon_minutes"], x["splits"]["train"])
            for x in r["training_only_shortlist"]
        ]
        self.assertEqual(extract(first), extract(second))

    def test_block_permutation_preserves_values_and_within_block_order(self):
        values = np.arange(20)
        shuffled = corr.permute_blocks(values, 5, np.random.default_rng(2))
        np.testing.assert_array_equal(np.sort(shuffled), values)
        self.assertTrue(all(np.all(np.diff(x) == 1) for x in shuffled.reshape(4, 5)))


class StudyTransferTests(unittest.TestCase):
    def test_input_replacement_during_computation_cannot_be_bound_as_old_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root / "run-plan.json.zlib", {"coin": "ETH"})
            snapshot = root / "inputs" / "ETH.json.zlib"
            save(snapshot, {"version": "initial"})
            frozen_inputs(root)
            save(snapshot, {"version": "replacement during computation"})
            (root / "result").write_text("computed from initial")
            with self.assertRaisesRegex(ValueError, "snapshot changed"):
                bind_files(root, root / "binding.json", [root / "result"])

    def test_resume_binding_detects_changed_cache_or_frozen_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root / "run-plan.json.zlib", {"coin": "ETH"})
            (root / "cache.npz").write_bytes(b"stand-in cache bytes")
            marker = root / "binding.json"
            bind_files(root, marker, [root / "cache.npz"])
            self.assertTrue(verify_binding(root, marker))
            (root / "cache.npz").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checkpoint artifact changed"):
                verify_binding(root, marker)
            save(root / "run-plan.json.zlib", {"coin": "BTC"})
            with self.assertRaisesRegex(ValueError, "another frozen plan"):
                verify_binding(root, marker)

    def test_short_cadence_history_reports_insufficient_cycle_data(self):
        result = cycle_study(candles(24), "1h", {"replicates": 19})
        self.assertEqual(result["status"], "insufficient_history")
        self.assertEqual(result["tests"], [])

    def test_coverage_names_unavailable_execution_and_short_history(self):
        rows = {r["study"]: r for r in coverage()}
        for name in ("captured_book", "oracle_second_turn", "exit50"):
            self.assertEqual(rows[name]["status"], "unavailable_input")
        self.assertEqual(rows["daily_cpcv"]["status"], "insufficient_history")
        self.assertTrue(all(len(r["source_sha256"]) == 64 for r in rows.values()))

    def test_cycle_transfer_emits_only_forecast_predictions_as_metrics(self):
        result = cycle_study(candles(240), "1m", {"replicates": 19})
        self.assertEqual(
            set(result["frozen_forecast"]["metrics"]),
            {"cycle", "linear", "persistence"},
        )
        self.assertGreater(result["frozen_forecast"]["period_seconds"], 0)

    def test_special_models_run_real_engines_on_complete_short_history(self):
        frame = candles(90)
        plan = {"start": 0, "end_exclusive": 90 * 60}
        result = special_models(frame, "1m", plan)
        families = {r["family"] for r in result["rows"]}
        self.assertEqual(
            families,
            {
                "volty_ohlc_synthetic_1x",
                "ladder_grid_reference_ohlc",
                "dca_safety_reference_ohlc",
            },
        )
        self.assertTrue(all(np.isfinite(r["return"]) for r in result["rows"]))


if __name__ == "__main__":
    unittest.main()
