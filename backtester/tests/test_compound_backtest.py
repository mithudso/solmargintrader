"""Compound backtest runner: data loading, gap handling, engine wiring, IS/OOS honesty."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core import compound as cbt
from backtester.core import scorecard as sc
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.types import Mode

from .test_scorecard import synthetic


def frame(b: sc.Bars) -> pd.DataFrame:
    return pd.DataFrame({"timestamp": b.ts.astype("int64"), "open": b.open, "high": b.high,
                         "low": b.low, "close": b.close, "volume": b.volume})


class DataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="compound-bt-"))

    def test_resample_builds_buckets_from_traded_minutes_and_leaves_empty_ones_as_gaps(self) -> None:
        ts = 1_780_000_200 + 60 * np.arange(15)
        df = pd.DataFrame({"timestamp": ts, "open": np.arange(15) + 1.0, "high": np.arange(15) + 2.0,
                           "low": np.arange(15) + 0.5, "close": np.arange(15) + 1.5, "volume": np.ones(15)})
        df = df.drop(index=[7, 10, 11, 12, 13, 14]).reset_index(drop=True)  # bucket 2 thin, bucket 3 empty
        out = cbt.resample_complete(df)
        self.assertEqual(list(out["timestamp"]), [1_780_000_200, 1_780_000_500])
        first, second = out.iloc[0], out.iloc[1]
        self.assertEqual((first.open, first.high, first.low, first.close, first.volume), (1.0, 6.0, 0.5, 5.5, 5.0))
        self.assertEqual((second.open, second.high, second.close, second.volume), (6.0, 11.0, 10.5, 4.0))
        self.assertEqual(list(out["minutes"]), [5, 4])
        self.assertEqual(cbt.incomplete_pct(out), 50.0)
        self.assertIsNone(cbt.incomplete_pct(out.drop(columns="minutes")))

    def test_loader_prefers_the_longest_series_and_names_its_source(self) -> None:
        frame(synthetic(400)).to_csv(self.dir / "SOL_5m_last30d.csv", index=False)
        frame(synthetic(700)).to_csv(self.dir / "SOL_5m.csv", index=False)
        df, source = cbt.load_bars_5m("sol", self.dir)
        self.assertEqual(len(df), 700)
        self.assertIn("SOL_5m.csv", source)
        self.assertEqual(cbt.available_assets(self.dir), ["SOL"])

    def test_available_asset_list_omits_removed_symbols_even_when_cached(self) -> None:
        for asset in ("SOL", "RAIN", "WBT", "HTX", "JST", "MNT", "XMR"):
            (self.dir / f"{asset}_1m.csv").touch()
        self.assertEqual(cbt.available_assets(self.dir), ["SOL"])

    def test_missing_data_names_the_fetch_command(self) -> None:
        with self.assertRaises(cbt.CompoundDataError) as cm:
            cbt.load_bars_5m("ZZZ", self.dir)
        self.assertIn("backtester.core.fetch --asset ZZZ --interval 5m", str(cm.exception))

    def test_stale_funding_is_not_carried_forward(self) -> None:
        b = synthetic(50)
        aux = {"funding": {"ts": np.array([int(b.ts[0]) - 30 * 86400]), "rate": np.array([5e-4])}}
        out = sc.BY_ID["funding"].fn(b, sc.BY_ID["funding"].defaults(), aux)
        self.assertTrue(np.isnan(out).all())


class EngineWiringTests(unittest.TestCase):
    def test_a_target_decided_at_bar_i_fills_at_bar_i_plus_one_open(self) -> None:
        b = synthetic(20)
        arrays = {"ts": b.ts.astype("int64"), "open": b.open, "high": b.high, "low": b.low,
                  "close": b.close, "volume": b.volume}
        targets = np.zeros(20)
        targets[5:] = 1.0
        res = run_backtest(cbt.PrecomputedTargets(targets), arrays,
                           EngineConfig(mode=Mode.PERP, leverage=2.0, interval="5m", allow_short=True))
        first = res.trades[0]
        self.assertEqual(first.bar_index, 6)
        self.assertEqual(int(first.ts), int(b.ts[6]))
        self.assertAlmostEqual(first.price, b.open[6], places=9)
        self.assertGreater(first.fee, 0.0)


class HyperliquidMarginTests(unittest.TestCase):
    def test_maintenance_is_half_the_initial_margin_at_max_leverage(self) -> None:
        self.assertAlmostEqual(cbt.maintenance_fraction("BTC"), 1 / 80)
        self.assertAlmostEqual(cbt.maintenance_fraction("near"), 0.05)
        self.assertIsNone(cbt.maintenance_fraction("TRX"))
        self.assertAlmostEqual(cbt.engine_config(sc.default_config(), "SUI").costs.maintenance_margin_fraction, 0.05)
        self.assertAlmostEqual(cbt.engine_config(sc.default_config()).costs.maintenance_margin_fraction, 0.002)

    def test_table_matches_the_dated_screen(self) -> None:
        import json

        root = Path(__file__).resolve().parents[2]
        screen = json.loads((root / "research/results/top50-screen-2026-11-07.json").read_text())
        rows = {r["symbol"]: r for r in screen["coins"]}
        for coin, max_lev in cbt.HYPERLIQUID_MAX_LEVERAGE.items():
            with self.subTest(coin=coin):
                self.assertEqual(rows[coin]["hyperliquid_perp_max_leverage"], max_lev)

    def test_a_higher_maintenance_margin_liquidates_sooner(self) -> None:
        # At 5x the liquidation buffer is 1/5 - close fee - maintenance: about 19.7% with Jupiter's
        # 0.2% margin, about 15% with a 10x-max Hyperliquid coin's 5%. A 16% drop separates them.
        n = 40
        close = np.full(n, 100.0)
        close[20:] = 84.0
        arrays = {"ts": (np.arange(n) * 300 + 1_700_000_000).astype("int64"), "open": close.copy(),
                  "high": close.copy(), "low": close.copy(), "close": close, "volume": np.ones(n)}
        targets = np.ones(n)
        cfg = sc.default_config()
        cfg["execution"]["leverage"] = 5.0
        jup = run_backtest(cbt.PrecomputedTargets(targets), arrays, cbt.engine_config(cfg))
        hl = run_backtest(cbt.PrecomputedTargets(targets), arrays, cbt.engine_config(cfg, "NEAR"))
        self.assertEqual(jup.liquidation_count, 0)
        self.assertEqual(hl.liquidation_count, 1)


class RunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="compound-run-"))
        b = synthetic(2400, seed=11)
        df = frame(b)
        df = df.drop(index=range(1200, 1210)).reset_index(drop=True)  # a 50-minute hole
        df.to_csv(self.dir / "SOL_5m.csv", index=False)
        frame(synthetic(2400, seed=12)).to_csv(self.dir / "BTC_5m.csv", index=False)

    def test_report_shape_split_and_gap_handling(self) -> None:
        r = cbt.run_compound("SOL", None, data_dir=self.dir)
        self.assertEqual(r["segments"], 2)
        self.assertEqual(r["bars"], 2390)
        self.assertLess(r["from_ts"], r["split_ts"])
        self.assertLess(r["split_ts"], r["to_ts"])
        for part in ("is", "oos"):
            self.assertIn("hit_rate", r[part]["forecast"])
            self.assertIn("total_return", r[part]["pnl"])
            self.assertEqual(r[part]["forecast"]["round_trip_bps"], 13.0)
        # Two segment ends and the label crossing the IS/OOS boundary are excluded.
        self.assertEqual(r["is"]["forecast"]["bars"] + r["oos"]["forecast"]["bars"], 2390 - 3)
        self.assertLess(r["oos"]["forecast"]["oracle_net_bps"], r["oos"]["forecast"]["mean_abs_move_bps"])

    def test_the_report_carries_the_incomplete_bar_share(self) -> None:
        native = cbt.run_compound("SOL", None, data_dir=self.dir)
        self.assertIsNone(native["data_incomplete_pct"])            # native 5m: nothing to count
        minutes = frame(synthetic(2400 * 5, seed=13))
        minutes["timestamp"] = 1_780_000_200 + 60 * np.arange(len(minutes))
        minutes = minutes.drop(index=range(0, len(minutes), 50)).reset_index(drop=True)  # 1 in 10 bars short
        minutes.to_csv(self.dir / "ETH_1m.csv", index=False)
        r = cbt.run_compound("ETH", None, data_dir=self.dir)
        self.assertAlmostEqual(r["data_incomplete_pct"], 10.0, delta=0.1)

    def test_costs_are_in_the_pnl(self) -> None:
        cfg = sc.default_config()
        for g in (c.id for c in sc.COMPONENTS if c.kind == "gate"):
            cfg["components"][g]["enabled"] = False
        cheap = cbt.run_compound("SOL", cfg, data_dir=self.dir)
        cfg["execution"]["fee_bps"] = 30.0
        dear = cbt.run_compound("SOL", cfg, data_dir=self.dir)
        self.assertGreater(cheap["oos"]["pnl"]["trades"], 0)
        self.assertEqual(cheap["oos"]["pnl"]["trades"], dear["oos"]["pnl"]["trades"])
        self.assertLess(dear["oos"]["pnl"]["total_return"], cheap["oos"]["pnl"]["total_return"])
        self.assertGreater(dear["oos"]["pnl"]["fees_pct"], cheap["oos"]["pnl"]["fees_pct"])

    def test_variants_are_unique_and_counted(self) -> None:
        vs = cbt.variants(sc.default_config(), standalone=True, perturb=True, aggregate_grid=True)
        labels = [label for label, _ in vs]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels[0], "compound")
        self.assertIn("only:rsi", labels)
        self.assertIn("compound no-gates", labels)
        self.assertTrue(any(label.startswith("only:rsi period=") for label in labels))
        hashes = {sc.config_hash(c) for _, c in vs}
        self.assertEqual(len(hashes), len(vs))
        forward_only = {c.id for c in sc.COMPONENTS if c.forward_only}
        self.assertFalse(any(label == f"only:{f}" for f in forward_only for label in labels))

    def test_frontier_covers_every_historical_metric_unlevered(self) -> None:
        vs = dict(cbt.variants(sc.default_config(), standalone=False, frontier=True))
        historical = [c.id for c in sc.COMPONENTS if c.kind == "score" and not c.forward_only]
        for cid in historical:                       # including metrics that are switched off
            for hold in cbt.FRONTIER_HOLDS:
                label = f"frontier:{cid} hold={hold} top2% 1x"
                self.assertIn(label, vs)
                agg, ex = vs[label]["aggregate"], vs[label]["execution"]
                self.assertEqual((agg["hold"], agg["entry_quantile"], ex["leverage"]),
                                 (hold, cbt.FRONTIER_QUANTILE, 1.0))
                self.assertEqual([k for k, e in vs[label]["components"].items() if e["enabled"]], [cid])

    def test_report_has_buy_and_hold_and_move_by_holding_period(self) -> None:
        r = cbt.run_compound("SOL", None, data_dir=self.dir)
        df = pd.read_csv(self.dir / "SOL_5m.csv")
        ts, close = df["timestamp"].to_numpy(), df["close"].to_numpy()
        cut = int(np.searchsorted(ts, r["split_ts"]))
        self.assertAlmostEqual(r["oos"]["buy_hold_return"], close[-1] / close[cut] - 1, places=5)
        self.assertAlmostEqual(r["is"]["buy_hold_return"], close[cut - 1] / close[0] - 1, places=5)
        self.assertEqual([h["bars"] for h in r["oos"]["forecast"]["horizons"]],
                         [h for h in sc.HORIZONS if h < 1000])

    def test_positions_are_not_relevered_every_bar(self) -> None:
        cfg = sc.default_config()
        self.assertEqual(cbt.engine_config(cfg).rebalance_threshold, 0.1 * cfg["execution"]["leverage"])

    def test_leaderboard_never_ranks_thin_rows_above_ranked_ones(self) -> None:
        rows = [{"label": "thin", "ranked": False, "oos": {"pnl": {"sharpe": 9.0}}},
                {"label": "a", "ranked": True, "oos": {"pnl": {"sharpe": -1.0}}},
                {"label": "b", "ranked": True, "oos": {"pnl": {"sharpe": 2.0}}}]
        self.assertEqual([r["label"] for r in cbt.leaderboard(rows)], ["b", "a", "thin"])


if __name__ == "__main__":
    unittest.main()
