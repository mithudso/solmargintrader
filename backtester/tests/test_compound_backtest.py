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

    def test_loader_prefers_the_longest_series_and_names_its_source(self) -> None:
        frame(synthetic(400)).to_csv(self.dir / "SOL_5m_last30d.csv", index=False)
        frame(synthetic(700)).to_csv(self.dir / "SOL_5m.csv", index=False)
        df, source = cbt.load_bars_5m("sol", self.dir)
        self.assertEqual(len(df), 700)
        self.assertIn("SOL_5m.csv", source)
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
            self.assertEqual(r[part]["forecast"]["round_trip_bps"], 16.0)
        self.assertEqual(r["is"]["forecast"]["bars"] + r["oos"]["forecast"]["bars"], 2390 - 2)
        self.assertLess(r["oos"]["forecast"]["oracle_net_bps"], r["oos"]["forecast"]["mean_abs_move_bps"])

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

    def test_leaderboard_never_ranks_thin_rows_above_ranked_ones(self) -> None:
        rows = [{"label": "thin", "ranked": False, "oos": {"pnl": {"sharpe": 9.0}}},
                {"label": "a", "ranked": True, "oos": {"pnl": {"sharpe": -1.0}}},
                {"label": "b", "ranked": True, "oos": {"pnl": {"sharpe": 2.0}}}]
        self.assertEqual([r["label"] for r in cbt.leaderboard(rows)], ["b", "a", "thin"])


if __name__ == "__main__":
    unittest.main()
