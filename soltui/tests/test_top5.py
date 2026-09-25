"""Tests for the Top 5 tab's pure module.

The load-bearing assertions: the module reads the committed evidence file
faithfully (ranks, home rows, transfers), never turns absent evidence into a
zero, and recovers composite members from labels without a duplicated
name-to-members table that could drift from research/cross_asset_cpcv.py.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from soltui import top5

HEADER = ("asset,rank,label,horizon,sol_median_sharpe,median_sharpe,"
          "delta_vs_sol,q1_sharpe,q3_sharpe,frac_paths_positive,"
          "median_return,total_trades,n_paths,usable_blocks\n")


def write_csv(root: Path, body: str) -> Path:
    p = root / "top5.csv"
    p.write_text(HEADER + body, encoding="utf-8")
    return p


class ParseMembersTests(unittest.TestCase):
    def test_all_composite(self) -> None:
        self.assertEqual(top5.parse_members("all(dual_momentum+vol_regime)"),
                         (("dual_momentum", "vol_regime"), "all"))

    def test_any_composite(self) -> None:
        self.assertEqual(top5.parse_members("any(hurst_switch+ou_reversion)"),
                         (("hurst_switch", "ou_reversion"), "any"))

    def test_single_with_params_strips_trailing_numbers(self) -> None:
        self.assertEqual(top5.parse_members("obv_trend_60"),
                         (("obv_trend",), "single"))
        self.assertEqual(top5.parse_members("vol_regime_60_0.5"),
                         (("vol_regime",), "single"))

    def test_single_without_params(self) -> None:
        self.assertEqual(top5.parse_members("buy_and_hold"),
                         (("buy_and_hold",), "single"))

    def test_unparseable_label_yields_no_members_not_a_guess(self) -> None:
        self.assertEqual(top5.parse_members("all()"), ((), ""))
        self.assertEqual(top5.parse_members("60_0.5"), ((), ""))


class LoadTop5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_missing_file_names_the_regeneration_command(self) -> None:
        with self.assertRaises(top5.EvidenceUnavailable) as ctx:
            top5.load_top5(self.root / "absent.csv")
        self.assertIn("--top5", str(ctx.exception))

    def test_header_only_file_is_reported_not_shown_empty(self) -> None:
        """An evidence file with no rows is broken evidence, not a repo with
        no recommendations -- those must read differently."""
        p = write_csv(self.root, "")
        with self.assertRaises(top5.EvidenceUnavailable) as ctx:
            top5.load_top5(p)
        self.assertIn("no configuration rows", str(ctx.exception))

    def test_groups_asset_rows_under_one_rank(self) -> None:
        p = write_csv(self.root, (
            "SOL,1,obv_trend_60,long,0.774,0.774,0.0,0.005,1.577,0.81,0.446,98,21,7\n"
            "DOGE,1,obv_trend_60,long,0.774,0.575,-0.199,0.025,1.073,0.76,0.194,96,21,7\n"
            "ZEC,1,obv_trend_60,long,0.774,0.150,-0.624,-0.319,1.769,0.57,-0.229,134,21,7\n"
        ))
        configs = top5.load_top5(p)
        self.assertEqual(len(configs), 1)
        cfg = configs[0]
        self.assertEqual(cfg.label, "obv_trend_60")
        self.assertEqual(cfg.home.asset, "SOL")
        self.assertEqual([t.asset for t in cfg.transfers], ["DOGE", "ZEC"])
        self.assertAlmostEqual(cfg.home.iqr, 1.577 - 0.005)

    def test_nan_stat_surfaces_as_none_never_zero(self) -> None:
        """0.0 renders as "measured at zero"; NaN means "not measured". The
        two must never be conflated -- the module's whole reason to exist."""
        p = write_csv(self.root, (
            "SOL,1,obv_trend_60,long,0.774,0.774,0.0,nan,1.577,0.81,nan,98,21,7\n"
        ))
        cfg = top5.load_top5(p)[0]
        self.assertIsNone(cfg.home.iqr)
        self.assertIsNone(cfg.home.median_return)

    def test_row_without_median_sharpe_is_dropped(self) -> None:
        p = write_csv(self.root, (
            "SOL,1,obv_trend_60,long,0.774,nan,0.0,0.0,1.0,0.8,0.4,98,21,7\n"
            "SOL,2,vol_regime_60_0.5,long,0.696,0.696,0.0,0.186,1.009,0.8,0.361,54,15,6\n"
        ))
        configs = top5.load_top5(p)
        self.assertEqual([c.rank for c in configs], [2])

    def test_real_committed_file_parses_to_five_ranked_configs(self) -> None:
        """The actual evidence file: 5 configs, each with SOL + 2 transfers,
        and rank-1's published Sharpe (+1.345) recovered exactly."""
        configs = top5.load_top5()
        self.assertEqual([c.rank for c in configs], [1, 2, 3, 4, 5])
        for cfg in configs:
            self.assertIsNotNone(cfg.home)
            self.assertEqual(len(cfg.transfers), 2)
        self.assertAlmostEqual(configs[0].home.median_sharpe, 1.345, places=3)
        self.assertEqual(configs[0].members, ("dual_momentum", "vol_regime"))
        self.assertEqual(configs[0].mode, "all")


class RosterCandidatesTests(unittest.TestCase):
    def test_distinct_members_first_seen_order(self) -> None:
        configs = top5.load_top5()
        names = top5.roster_candidates(configs)
        self.assertEqual(names, ["dual_momentum", "vol_regime", "hurst_switch",
                                 "ou_reversion", "obv_trend"])

    def test_every_candidate_is_a_registry_strategy(self) -> None:
        """The names the tab offers to add to the roster must resolve, or the
        Add button manufactures a RosterError at click time."""
        from backtester.core.strategies import REGISTRY
        for name in top5.roster_candidates(top5.load_top5()):
            self.assertIn(name, REGISTRY)


if __name__ == "__main__":
    unittest.main()
