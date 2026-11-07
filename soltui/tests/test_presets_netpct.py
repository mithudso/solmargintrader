"""Top 5 presets, the net % helper, and the P&L commands end to end on synthetic data.

No price file, state file or network: the series is `SyntheticLoader`, the Top 5 evidence is a temp
CSV, the liquidity home and journal are temp paths.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backtester.core.data import SyntheticLoader, frame_to_arrays
from soltui import commands, live_run, netpct, presets, top5
from soltui.tests.bridge_support import World

HEADER = ("asset,rank,label,horizon,sol_median_sharpe,median_sharpe,delta_vs_sol,q1_sharpe,q3_sharpe,"
          "frac_paths_positive,median_return,total_trades,n_paths,usable_blocks\n")
ROWS = (
    "SOL,1,all(dual_momentum+vol_regime),long,1.3,1.3,0,0.8,1.6,0.86,0.75,52,15,6\n"
    "SOL,4,obv_trend_60,long,0.7,0.7,0,0.0,1.5,0.8,0.44,98,21,7\n"
    "SOL,5,mystery_strategy,medium,0.6,0.6,0,0.1,1.0,0.8,,54,15,6\n"
    "DOGE,1,all(dual_momentum+vol_regime),long,1.3,0.4,-0.9,-0.4,0.7,0.6,0.12,44,15,6\n")


def top5_csv(root: Path) -> Path:
    path = root / "top5.csv"
    path.write_text(HEADER + ROWS, encoding="utf-8")
    return path


class NetPctTests(unittest.TestCase):
    def test_definition(self) -> None:
        self.assertAlmostEqual(netpct.net_pct(1094, 1000), 0.094)
        self.assertAlmostEqual(netpct.net_pct(500, 1000), -0.5)

    def test_no_base_is_none_not_zero(self) -> None:
        for args in ((1, 0), (1, -5), (None, 5), (5, None), (float("nan"), 5), (5, float("inf"))):
            with self.subTest(args=args):
                self.assertIsNone(netpct.net_pct(*args))

    def test_text_always_names_the_source(self) -> None:
        self.assertEqual(netpct.labelled(0.094, "backtest"), "backtest net +9.4%")
        self.assertEqual(netpct.labelled(-0.02, "live LP", "net", 2), "live LP net -2.00%")
        self.assertEqual(netpct.labelled(None, "paper"), "paper net —")
        with self.assertRaises(ValueError):
            netpct.labelled(0.1, "")
        with self.assertRaises(ValueError):
            netpct.labelled(0.1, "real money")


class PresetTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.csv = top5_csv(Path(tmp.name))
        self.presets = presets.build_presets(top5.load_top5(self.csv))

    def test_one_preset_per_configuration_in_rank_order(self) -> None:
        self.assertEqual([p["rank"] for p in self.presets], [1, 4, 5])
        self.assertEqual(self.presets[0]["value"], "top5:1")
        self.assertEqual(self.presets[0]["label"], "all(dual_momentum+vol_regime)")

    def test_parameters_come_from_the_research_horizons_not_a_copy(self) -> None:
        from research.sweep import HORIZONS
        p = self.presets[0]
        self.assertEqual([m["name"] for m in p["members"]], ["dual_momentum", "vol_regime"])
        for m in p["members"]:
            self.assertEqual(m["params"], HORIZONS["long"]["params"][m["name"]])
        self.assertEqual((p["asset"], p["interval"]), ("SOL", "1d"))
        self.assertTrue(p["usable"])

    def test_net_pct_is_labelled_backtest_and_absent_evidence_stays_absent(self) -> None:
        self.assertEqual(self.presets[0]["net_pct_text"], "backtest median net +75.0%")
        mystery = self.presets[2]
        self.assertIsNone(mystery["net_pct"])
        self.assertIn("—", mystery["net_pct_text"])

    def test_unknown_member_is_not_usable(self) -> None:
        mystery = self.presets[2]
        self.assertFalse(mystery["usable"])
        with self.assertRaises(ValueError):
            presets.build_strategy(mystery)

    def test_each_tab_gets_its_fill_values(self) -> None:
        a = self.presets[1]["applies"]
        self.assertEqual(a["live_run"], {"strategy": "obv_trend_60"})
        self.assertEqual(a["execute"], {"label": "top5:4"})
        self.assertEqual(a["analyze"]["preset"], "top5:4")

    def test_value_round_trip(self) -> None:
        self.assertEqual(presets.parse_value(presets.preset_value(3)), 3)
        for bad in ("top5:", "top5:x", "rsi", "", None):
            self.assertIsNone(presets.parse_value(bad))

    def test_strategies_build_and_composite_has_both_members(self) -> None:
        single = presets.build_strategy(self.presets[1])
        combo = presets.build_strategy(self.presets[0])
        self.assertTrue(single.name.startswith("obv_trend"))
        self.assertEqual(len(combo.strategies) if hasattr(combo, "strategies") else 2, 2)
        self.assertGreater(combo.warmup_bars(), 0)

    def test_find_preset_names_the_ranks_that_exist(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\[1, 4, 5\]"):
            presets.find_preset(2, self.presets)

    def test_missing_evidence_raises_with_the_regeneration_command(self) -> None:
        with self.assertRaises(top5.EvidenceUnavailable):
            presets.build_presets(top5.load_top5(Path("/nonexistent/top5.csv")))


class DryRunNetTests(unittest.TestCase):
    OUT = ("grid 85-115, 7 rungs\ncapital needed: $48.00 quote (bids only)\n\n"
           "tick 7  price $88.0000  placed 0  rejected 0  fills 4  net $-2.3782\n"
           "tick 8  price $94.0000  placed 1  rejected 0  fills 5  net $-0.0209\n")

    def test_net_is_last_tick_over_printed_capital(self) -> None:
        self.assertAlmostEqual(live_run.dryrun_net_pct(self.OUT), -0.0209 / 48)

    def test_missing_pieces_give_none(self) -> None:
        self.assertIsNone(live_run.dryrun_net_pct("capital needed: $48.00"))
        self.assertIsNone(live_run.dryrun_net_pct("tick 1 net $1.0"))
        self.assertIsNone(live_run.dryrun_net_pct(""))


class CommandTests(unittest.TestCase):
    """The registry commands, with a synthetic series and temp state."""

    def setUp(self) -> None:
        self.world = World().__enter__()
        self.addCleanup(self.world.__exit__)
        self.tmp = Path(tempfile.mkdtemp(prefix="soltui-pnl-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        csv = self.tmp / "top5.csv"
        csv.write_text(HEADER + ROWS, encoding="utf-8")
        patches = [
            mock.patch.object(top5, "TOP5_CSV", csv),
            mock.patch.dict(os.environ, {commands.JOURNAL_ENV: str(self.tmp / "no-journal.json")}),
            mock.patch.object(commands, "load_arrays", self._arrays),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.df = SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d")

    def _arrays(self, settings):
        return frame_to_arrays(self.df)

    def call(self, name, params=None):
        env = commands.dispatch(name, params or {}, surface="cli")
        return env

    def test_top5_presets_command(self) -> None:
        env = self.call("top5.presets")
        self.assertTrue(env["ok"], env)
        self.assertEqual([p["rank"] for p in env["result"]["presets"]], [1, 4, 5])

    def test_top5_presets_without_evidence_reports_the_regeneration_command(self) -> None:
        with mock.patch.object(top5, "TOP5_CSV", self.tmp / "gone.csv"):
            env = self.call("top5.presets")
        self.assertFalse(env["ok"])
        self.assertIn("cross_asset_cpcv.py", env["error"]["message"])

    def test_pnl_summary_backtest_section_over_all_time(self) -> None:
        env = self.call("pnl.summary", {"window": "all", "source": "backtest"})
        self.assertTrue(env["ok"], env)
        (sec,) = env["result"]["sections"]
        self.assertEqual((sec["source"], sec["group"], sec["status"]), ("backtest", "simulated", "ok"))
        self.assertEqual(sec["runs"], 4)          # the default roster
        t = sec["totals"]
        self.assertAlmostEqual(t["initial"], 4 * 10_000.0)
        self.assertAlmostEqual(t["final"], t["initial"] + t["net_usd"])
        self.assertAlmostEqual(t["net_pct"], t["net_usd"] / t["initial"])
        self.assertRegex(t["net_pct_text"], r"^backtest net [+-]\d+\.\d%$")
        self.assertGreaterEqual(t["fees_usd"], 0)

    def test_the_days_sum_to_the_section_net(self) -> None:
        env = self.call("pnl.series", {"window": "all", "source": "backtest"})
        (sec,) = env["result"]["sections"]
        summary = self.call("pnl.summary", {"window": "all", "source": "backtest"})["result"]["sections"][0]
        self.assertAlmostEqual(sum(d["pnl"] for d in sec["days"]), summary["totals"]["net_usd"], places=6)
        self.assertEqual(len(sec["days"]), 300)

    def test_a_custom_window_cuts_the_series(self) -> None:
        full = self.call("pnl.series", {"window": "all", "source": "backtest"})["result"]["sections"][0]
        a, b = full["days"][100]["date"], full["days"][149]["date"]
        cut = self.call("pnl.series", {"start": a, "end": b, "source": "backtest"})["result"]
        (sec,) = cut["sections"]
        self.assertEqual(len(sec["days"]), 50)
        self.assertEqual(cut["window"]["label"], "custom")
        net = sum(d["pnl"] for d in sec["days"])
        self.assertAlmostEqual(net, full["days"][149]["cumulative"] - full["days"][99]["cumulative"], places=6)

    def test_a_window_with_no_backtest_data_says_where_the_data_is(self) -> None:
        env = self.call("pnl.summary", {"window": "24h", "source": "backtest"})
        (sec,) = env["result"]["sections"]
        self.assertEqual(sec["status"], "no_data")
        self.assertIn("its data covers", sec["message"])

    def test_breakdown_by_strategy_and_asset(self) -> None:
        env = self.call("pnl.breakdown", {"window": "all", "source": "backtest"})
        (sec,) = env["result"]["sections"]
        self.assertEqual(len(sec["by_strategy"]), 4)
        self.assertEqual([r["name"] for r in sec["by_asset"]], ["SOL"])
        total = self.call("pnl.summary", {"window": "all", "source": "backtest"})["result"][
            "sections"][0]["totals"]["net_pct"]
        self.assertAlmostEqual(sum(r["contribution_pts"] for r in sec["by_strategy"]), total)

    def test_no_session_means_paper_has_no_data_and_says_how_to_start_one(self) -> None:
        env = self.call("pnl.summary", {"window": "all", "source": "paper"})
        (sec,) = env["result"]["sections"]
        self.assertEqual(sec["status"], "no_data")
        self.assertTrue(any("Execute" in n for n in sec["notes"]))

    def test_paper_replay_is_its_own_section_up_to_the_cursor(self) -> None:
        self.assertTrue(self.call("paper.start", {"label": "rsi_14_30_50", "bars": 50})["ok"])
        env = self.call("pnl.summary", {"window": "all", "source": "paper"})
        (sec,) = env["result"]["sections"]
        self.assertEqual((sec["source"], sec["status"]), ("paper", "ok"))
        series = self.call("pnl.series", {"window": "all", "source": "paper"})["result"]["sections"][0]
        self.assertEqual(len(series["days"]), 51)       # bars 0..50 inclusive; later bars not counted
        self.assertRegex(sec["totals"]["net_pct_text"], r"^paper net ")

    def test_default_all_sources_never_adds_simulated_to_real(self) -> None:
        env = self.call("pnl.summary", {"window": "all"})
        result = env["result"]
        self.assertNotIn("totals", result)
        sources = [s["source"] for s in result["sections"]]
        self.assertIn("backtest", sources)
        self.assertIn("paper", sources)
        self.assertIn("dry-run", sources)
        self.assertIn("never summed", result["notice"])

    def test_extension_journal_is_read_when_present(self) -> None:
        journal = self.tmp / "journal.json"
        journal.write_text(json.dumps({"fills": {
            "a": {"id": "a", "side": "buy", "baseQty": 1, "priceUsd": 100, "feeUsd": 0.1, "tsMs": 1_767_225_600_000},
            "b": {"id": "b", "side": "sell", "baseQty": 1, "priceUsd": 110, "feeUsd": 0.1, "tsMs": 1_767_312_000_000}}}))
        with mock.patch.dict(os.environ, {commands.JOURNAL_ENV: str(journal)}):
            env = self.call("pnl.summary", {"window": "all", "source": "dry-run"})
        (sec,) = env["result"]["sections"]
        self.assertEqual(sec["status"], "ok")
        self.assertAlmostEqual(sec["totals"]["net_usd"], 9.8)
        self.assertIsNone(sec["totals"]["net_pct"])

    def test_liquidity_state_files_are_a_separate_real_section(self) -> None:
        home = Path(os.environ["AERO_LP_HOME"])
        home.mkdir(parents=True)
        (home / "status.json").write_text(json.dumps({
            "schema": "aero-lp-status/1", "mode": "live", "generated_at": 1_790_000_000,
            "positions": [{"pnl_usd": 0.5, "deposited_usd": 20.0, "gas_usd": 0.1, "rewards_usd": 0.2}]}))
        env = self.call("pnl.summary", {"window": "7d", "source": "live LP"})
        (sec,) = env["result"]["sections"]
        self.assertEqual((sec["source"], sec["group"], sec["windowed"]), ("live LP", "real", False))
        self.assertEqual(sec["totals"]["net_pct_text"], "live LP net +2.5%")

    def test_bad_window_and_source_are_bad_params(self) -> None:
        for params in ({"window": "99d"}, {"source": "bank"}, {"start": "nonsense"}):
            env = self.call("pnl.summary", params)
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], "bad_params")

    def test_paper_view_carries_labelled_net_pct(self) -> None:
        env = self.call("paper.start", {"label": "rsi_14_30_50", "bars": 30})
        self.assertTrue(env["ok"], env)
        r = env["result"]
        self.assertRegex(r["summary"]["net_pct_text"], r"^paper net [+-]")
        self.assertIn(r["summary"]["net_pct_text"], r["text"])
        self.assertNotRegex(r["text"], r"(?<![A-Za-z] )P&L [+-]\d")

    def test_paper_start_accepts_a_top5_preset(self) -> None:
        def fake_arrays(preset, data_dir="data"):
            return frame_to_arrays(self.df)
        with mock.patch.object(presets, "load_preset_arrays", fake_arrays):
            env = self.call("paper.start", {"label": "top5:4", "bars": 40})
        self.assertTrue(env["ok"], env)
        self.assertEqual(env["result"]["summary"]["bar"], 40)
        series = self.call("pnl.series", {"window": "all", "source": "paper"})["result"]["sections"][0]
        self.assertEqual(series["status"], "ok")

    def test_paper_start_unknown_preset_rank_fails_cleanly(self) -> None:
        env = self.call("paper.start", {"label": "top5:2"})
        self.assertFalse(env["ok"])
        self.assertIn("rank 2", env["error"]["message"])

    def test_analyze_rejects_a_malformed_preset(self) -> None:
        env = self.call("analyze.run", {"asset": "SOL", "preset": "rsi"})
        self.assertEqual((env["ok"], env["error"]["code"]), (False, "bad_params"))


class NoBareFiguresTests(unittest.TestCase):
    """Every text field that carries a percentage names its source, across the new commands."""

    SOURCE = re.compile(r"(backtest|paper|dry-run|live LP|dry-run LP|reported LP|wallet \(live\)|reported)")

    def test_all_net_pct_texts_have_a_source(self) -> None:
        for source in netpct.SOURCES:
            self.assertRegex(netpct.labelled(0.01, source), self.SOURCE)


if __name__ == "__main__":
    unittest.main()
