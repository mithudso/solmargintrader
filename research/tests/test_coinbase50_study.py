"""Known answers and adversarial controls for the top50 research contract."""

from __future__ import annotations

import itertools
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester.core.gridsim import GridConfig, run_grid_backtest
from backtester.core.types import CostConfig
from research.coinbase50_data import sha, universe
from research.coinbase50_grid import (
    causal_hour_features,
    hourly_from_quarters,
    normalized_arrays,
    passive,
    permissions,
    persistent_h1,
    simulate,
)
from research.coinbase50_stats import (
    clock_test,
    daily_profiles,
    market_calendar_residual,
    wavelength_windows,
)
from research.coinbase50_study import STUDY_END, bootstrap_differences, portfolios, read


def candles(n=600, step=900, start=1700002800):
    t = np.arange(n)
    close = 100 * np.exp(0.06 * np.sin(t / 9) + 0.01 * np.cos(t / 3))
    return pd.DataFrame({"timestamp": start + t * step, "open": np.r_[close[0], close[:-1]], "high": np.maximum(close, np.r_[close[0], close[:-1]]) * 1.005, "low": np.minimum(close, np.r_[close[0], close[:-1]]) * 0.995, "close": close, "volume": np.ones(n) * 100})


def independent_h1(cloud):
    """Tiny exact Z2 boundary reduction includes vertices, edges and triangles."""
    distances = np.linalg.norm(cloud[:, None] - cloud[None, :], axis=2)
    simplices = []
    for size in (1, 2, 3):
        for vertices in itertools.combinations(range(len(cloud)), size):
            radius = max((distances[a, b] for a, b in itertools.combinations(vertices, 2)), default=0)
            simplices.append((radius, size - 1, vertices))
    simplices.sort()
    index = {s[2]: i for i, s in enumerate(simplices)}
    reduced, pairs = {}, []
    for i, (_, dim, vertices) in enumerate(simplices):
        column = {index[face] for face in itertools.combinations(vertices, len(vertices) - 1)} if dim else set()
        while column and max(column) in reduced:
            column ^= reduced[max(column)]
        if column:
            pivot = max(column)
            reduced[pivot] = column
            if simplices[pivot][1] == 1:
                pairs.append(simplices[i][0] - simplices[pivot][0])
    return max(pairs, default=0) / distances.max()


class CoinbaseStudyTests(unittest.TestCase):
    def test_h1_square_ring_and_filled_simplexes(self):
        square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
        self.assertAlmostEqual(persistent_h1(square), 1 - 1 / np.sqrt(2), places=6)
        for cloud in (square, np.eye(3), np.eye(4), np.random.default_rng(1).normal(size=(7, 3))):
            self.assertAlmostEqual(persistent_h1(cloud), independent_h1(cloud), places=6)
        self.assertEqual(persistent_h1(np.eye(3)), 0)
        self.assertEqual(persistent_h1(np.eye(4)), 0)
        for scale in (1e-9, 1e9):
            self.assertAlmostEqual(persistent_h1(square * scale), persistent_h1(square), places=6)

    def test_grid_vector_permission_equals_continuation_and_keeps_exits(self):
        f = candles(180)
        arrays = normalized_arrays(f, 1)
        cfg = GridConfig(lower=90, upper=110, rungs=7, notional_per_rung_usd=20, min_order_usd=1)
        allowed = np.r_[np.ones(70, bool), np.zeros(60, bool), np.ones(50, bool)]
        costs = CostConfig(fee_bps=10, slippage_bps=25)
        full = run_grid_backtest(cfg, arrays, interval="15m", initial_capital=200, costs=costs, entry_allowed=allowed)
        curves, state = [], None
        all_trades = []
        for left, right in ((0, 70), (70, 130), (130, 180)):
            result = run_grid_backtest(cfg, {k: v[left:right] for k, v in arrays.items()}, interval="15m", initial_capital=200, costs=costs, entries_paused=not allowed[left], continuation=state, close_at_end=right == 180)
            curves.extend(result.equity)
            all_trades.extend(result.trades)
            state = result.continuation
        np.testing.assert_allclose(full.equity, curves, rtol=1e-12)
        self.assertEqual([(x.ts, x.side, x.reason) for x in full.trades], [(x.ts, x.side, x.reason) for x in all_trades])
        self.assertTrue(any(x.side == "sell" and 70 <= x.bar_index < 130 for x in full.trades))
        self.assertFalse(any(x.side == "buy" and 70 <= x.bar_index < 130 for x in full.trades))
        for bad in (np.ones(180), np.ones(179, bool)):
            with self.assertRaisesRegex(ValueError, "boolean vector"):
                run_grid_backtest(cfg, arrays, interval="15m", entry_allowed=bad)

    def test_unit_normalization_invariant_with_fees_pauses_and_cash_shortage(self):
        f = candles(600)
        allowed = np.arange(300) % 20 < 11
        for capital in (2, 200):
            for fee, slip in ((0, 0), (10, 25)):
                costs = CostConfig(fee_bps=fee, slippage_bps=slip)
                reference = simulate(f[:300], f[300:], allowed, capital, costs, minimum=0.001)
                for multiplier in (1e-10, 1e8):
                    scaled = f.copy()
                    scaled[["open", "high", "low", "close"]] *= multiplier
                    scaled.volume /= multiplier
                    result = simulate(scaled[:300], scaled[300:], allowed, capital, costs, minimum=0.001)
                    np.testing.assert_allclose(reference[0], result[0], rtol=1e-10)
                    self.assertEqual(reference[2]["round_trips"], result[2]["round_trips"])
                    self.assertEqual([(x.ts, x.side) for x in reference[3].trades], [(x.ts, x.side) for x in result[3].trades])
                    self.assertAlmostEqual(reference[2]["forced_native_qty"], result[2]["forced_native_qty"] * multiplier, places=8)

    def test_passive_pays_both_sides_and_idle_cash_is_preserved(self):
        f = candles(24)
        f[["open", "close"]] = 100
        c = CostConfig(fee_bps=10, slippage_bps=20)
        result = passive(f, 200, c)
        expected = 200 / 1.001 / 1.002 * 0.998 * 0.999
        self.assertAlmostEqual(result[-1], expected)
        np.testing.assert_allclose(passive(f, 200, c, 0), 200)

    def test_hour_features_and_permissions_are_prefix_causal(self):
        f = candles(1200, start=1700002800 // 3600 * 3600)
        hourly = hourly_from_quarters(f)
        market = hourly.copy()
        market.close *= np.exp(np.random.default_rng(12).normal(0, 0.01, len(market)))
        original = causal_hour_features(hourly, market)
        poisoned = hourly.copy()
        poisoned.loc[240:, ["open", "high", "low", "close"]] *= 10
        later = causal_hour_features(poisoned, market)
        pd.testing.assert_frame_equal(original.iloc[:240], later.iloc[:240])
        with_gap = hourly.drop(index=200).reset_index(drop=True)
        result = causal_hour_features(with_gap, with_gap)
        self.assertTrue(result.H1.iloc[201:250].isna().all())
        train_end = int(f.timestamp.iloc[800])
        a, settings = permissions(f, original, train_end)
        changed = f.copy()
        changed.loc[1000:, ["open", "high", "low", "close"]] *= 4
        b, changed_settings = permissions(changed, later, train_end)
        np.testing.assert_array_equal(a[:950], b[:950])
        self.assertEqual(settings, changed_settings)

    def test_exact_market_explanation_has_no_artificial_clock_or_topology(self):
        f = candles(24 * 28, 3600)
        features = causal_hour_features(f, f)
        self.assertTrue(features.H1.isna().all())
        self.assertTrue(features.cycle_allowed.isna().all())
        rows = wavelength_windows(f, f, 3600, 7)
        self.assertFalse(any(x["mode"] == "market_calendar_residual" for x in rows))

    def test_nuisance_fit_never_uses_future_and_removes_market_calendar(self):
        ts = np.arange(500) * 3600
        market = np.random.default_rng(3).normal(size=500)
        hours = pd.to_datetime(ts, unit="s", utc=True).hour.to_numpy()
        y = 0.01 + 2 * market + np.sin(hours / 24 * 2 * np.pi)
        train = np.arange(500) < 300
        result = market_calendar_residual(ts, y, market, train)
        np.testing.assert_allclose(result, 0, atol=1e-12)
        y[300:] += 100
        changed = market_calendar_residual(ts, y, market, train)
        np.testing.assert_allclose(result[:300], changed[:300], atol=1e-12)

    def test_known_wavelength_recovers_and_frozen_wave_beats_persistence(self):
        f = candles(24 * 28, 3600)
        f["close"] = np.exp(4 + 0.05 * np.sin(np.arange(len(f)) * 2 * np.pi / 12))
        f["open"] = np.r_[f.close.iloc[0], f.close.to_numpy()[:-1]]
        rows = [x for x in wavelength_windows(f, f, 3600, 7) if x["mode"] == "raw"]
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertAlmostEqual(row["period_hours"], 12)
            self.assertTrue(row["forecast_win"])

    def test_calendar_null_changes_hour_means_and_distinguishes_direction(self):
        dates = pd.date_range("2025-01-01", periods=180).strftime("%Y-%m-%d")
        rng = np.random.default_rng(8)
        profile = np.tile(np.sin(np.arange(24) * 2 * np.pi / 24), (180, 1)) + rng.normal(0, 0.3, (180, 24))
        table = pd.DataFrame(profile, index=dates)
        self.assertLess(clock_test(table, "absolute_return", 199)["p"], 0.01)
        self.assertLess(clock_test(table, "direction", 199)["p"], 0.01)
        table[:] = 1
        self.assertEqual(clock_test(table, "direction", 199)["p"], 1)

    def test_DST_days_are_excluded_without_filling_or_averaging(self):
        start = int(pd.Timestamp("2026-10-30T00:00:00Z").timestamp())
        f = candles(24 * 5, 3600, start)
        profiles, excluded = daily_profiles(f, "America/New_York", "direction")
        self.assertNotIn("2026-11-01", profiles.index)
        self.assertGreater(excluded, 0)

    def test_source_read_clips_before_reserved_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            f = candles(10, 900, STUDY_END - 5 * 900)
            p = root / "BTC_15m.csv"
            f.to_csv(p, index=False)
            (root / "BTC_15m.json").write_text(json.dumps({"csv": str(p), "sha256": sha(p)}))
            with patch("research.coinbase50_study.protected_intervals", return_value=[{"start": STUDY_END, "end": STUDY_END + 3600}]):
                self.assertEqual(len(read(root, "BTC", "15m")), 5)

    def test_identity_join_uses_venue_coin_id_not_symbol(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            product = {"base_currency_id": "AERO", "quote_currency_id": "USD", "status": "online"}
            (p / "coinbase-products-mcp.json").write_text(json.dumps({"products": [product]}))
            markets = [{"id": "wrong-aero", "name": "Wrong", "symbol": "aero", "market_cap": 999, "market_cap_rank": 1}, {"id": "aerodrome-finance", "name": "Aerodrome", "symbol": "aero", "market_cap": 10, "market_cap_rank": 196}]
            (p / "coingecko-markets-page1.json").write_text(json.dumps(markets))
            for page in (1, 2, 3):
                (p / f"coingecko-gdax-tickers-{page}.json").write_text(json.dumps({"tickers": [{"base": "AERO", "target": "USD", "coin_id": "aerodrome-finance"}]}))
            self.assertEqual(universe(p)["assets"][0]["rank"], 196)

    def test_paired_bootstrap_uses_same_blocks_for_identical_policies(self):
        y = np.random.default_rng(1).normal(size=90)
        p, intervals = bootstrap_differences(np.column_stack([y, y, np.zeros(90)]), 199)
        self.assertEqual(p[0], p[1])
        np.testing.assert_array_equal(intervals[:, 0], intervals[:, 1])
        self.assertEqual(p[2], 1)

    def test_portfolio_budgets_compound_and_missing_coins_stay_cash_in_all50(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results, assets = [], []
            scenarios = ("zero_2", "zero_10", "zero_25", "fee10_2")
            for symbol in ("A", "B"):
                assets.append({"symbol": symbol})
                folds = []
                for fold in range(3):
                    cells = []
                    for scenario in scenarios:
                        path = root / f"{symbol}_{fold}_{scenario}.npz"
                        unit = np.linspace(1, 1.1, 2880)
                        np.savez_compressed(path, equity=np.tile(unit, (16, 1)), exposure=np.full((16, 2880), 0.5), passive=unit, exposure_matched_passive=np.tile(unit, (16, 1)))
                        cells.append({"scenario": scenario, "curves": str(path), "sha256": sha(path), "gates": [{"round_trips": 3}] * 16})
                    folds.append({"screen": {"score": 1}, "scenarios": cells})
                results.append({"symbol": symbol, "eligible": True, "folds": folds})
            with patch("research.coinbase50_study.bootstrap_differences", return_value=(np.ones(128), np.zeros((2, 128)))):
                rows = portfolios(root, assets, results)
            self.assertEqual(len(rows), 128)
            for row in rows:
                self.assertAlmostEqual(row["return_pct"], (1.02**3 - 1) * 100)
            baselines = json.loads((root / "baselines.json").read_text())
            all50 = next(x for x in baselines if x["baseline"] == "all50_grid")
            self.assertAlmostEqual(all50["return_pct"], (1.004**3 - 1) * 100)
            eligible = next(x for x in baselines if x["baseline"] == "eligible_grid")
            self.assertAlmostEqual(eligible["return_pct"], (1.1**3 - 1) * 100)


if __name__ == "__main__":
    unittest.main()
