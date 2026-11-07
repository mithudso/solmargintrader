"""The P&L maths, on fixtures: window edges, costs, realized vs unrealized, drawdown, the no-data case.

No test here reads a price file, a state file or the network. The numbers are small round ones so
each expected value can be checked by hand.
"""

from __future__ import annotations

import sqlite3
import unittest
from datetime import date, datetime, timezone

from soltui import pnl
from soltui.pnl import Curve, Fill, Window

UTC = timezone.utc


def at(day: str, hour: int = 0) -> float:
    y, m, d = (int(x) for x in day.split("-"))
    return datetime(y, m, d, hour, tzinfo=UTC).timestamp()


NOW = at("2026-11-07", 12)


def curve(points, *, initial=1000.0, fills=(), source="backtest", strategy="s", asset="SOL", **kw):
    return Curve(source, strategy, asset, initial, [(at(d, h), v) for d, h, v in points],
                 list(fills), **kw)


class WindowTests(unittest.TestCase):
    def test_presets_reach_back_from_now(self) -> None:
        for name, days in (("24h", 1), ("7d", 7), ("30d", 30), ("90d", 90)):
            w = pnl.resolve_window(name, now=NOW)
            self.assertEqual(w.end, NOW)
            self.assertEqual(NOW - w.start, days * 86400)

    def test_ytd_starts_on_new_year_utc(self) -> None:
        w = pnl.resolve_window("ytd", now=NOW)
        self.assertEqual(w.start, at("2026-01-01"))
        self.assertEqual(w.end, NOW)

    def test_all_is_unbounded_and_default_is_30d(self) -> None:
        w = pnl.resolve_window("all", now=NOW)
        self.assertEqual((w.start, w.end), (None, None))
        self.assertEqual(pnl.resolve_window(None, now=NOW).label, "30d")

    def test_custom_end_date_covers_the_whole_day(self) -> None:
        w = pnl.resolve_window(None, "2026-01-01", "2026-01-31", now=NOW)
        self.assertEqual(w.label, "custom")
        self.assertEqual(w.start, at("2026-01-01"))
        self.assertTrue(w.contains(at("2026-01-31", 23)))
        self.assertFalse(w.contains(at("2026-02-01")))

    def test_custom_wins_over_preset_and_one_side_may_be_open(self) -> None:
        w = pnl.resolve_window("7d", "2026-03-01", None, now=NOW)
        self.assertEqual((w.label, w.start, w.end), ("custom", at("2026-03-01"), None))

    def test_bad_windows_are_refused(self) -> None:
        for args in (("99d", None, None), ("custom", None, None), (None, "2026-02-01", "2026-01-01"),
                     (None, "yesterday", None)):
            with self.subTest(args=args), self.assertRaises(pnl.PnlError):
                pnl.resolve_window(*args, now=NOW)

    def test_source_names(self) -> None:
        self.assertIsNone(pnl.normalise_source("all"))
        self.assertIsNone(pnl.normalise_source(None))
        self.assertEqual(pnl.normalise_source("live-lp"), "live LP")
        self.assertEqual(pnl.normalise_source("Paper"), "paper")
        with self.assertRaises(pnl.PnlError):
            pnl.normalise_source("bank")


class RunStatsTests(unittest.TestCase):
    def setUp(self) -> None:
        # 1000 -> 1100 -> 1050 -> 1200 over four days.
        self.c = curve([("2026-01-01", 0, 1000), ("2026-01-02", 0, 1100), ("2026-01-03", 0, 1050),
                        ("2026-01-04", 0, 1200)])

    def test_all_window_net_is_final_over_initial(self) -> None:
        s = pnl.run_stats(self.c, Window("all"))
        self.assertEqual((s.base, s.final, s.net), (1000, 1200, 200))
        self.assertAlmostEqual(s.net_pct, 0.20)

    def test_window_edges_are_inclusive_and_base_is_the_point_before(self) -> None:
        w = Window("x", at("2026-01-02"), at("2026-01-03"))
        s = pnl.run_stats(self.c, w)
        self.assertEqual(s.base, 1000)      # the 01-01 point, strictly before the start
        self.assertEqual(s.final, 1050)     # the 01-03 point sits exactly on the end edge
        self.assertAlmostEqual(s.net_pct, 0.05)

    def test_a_point_one_second_outside_is_excluded(self) -> None:
        w = Window("x", at("2026-01-02") + 1, at("2026-01-03") - 1)
        self.assertIsNone(pnl.run_stats(self.c, w))

    def test_window_before_the_data_uses_starting_capital_as_base(self) -> None:
        w = Window("x", at("2025-12-01"), at("2026-01-02"))
        s = pnl.run_stats(self.c, w)
        self.assertEqual((s.base, s.final), (1000, 1100))

    def test_no_data_is_none_not_zero(self) -> None:
        self.assertIsNone(pnl.run_stats(self.c, Window("x", at("2027-01-01"), at("2027-02-01"))))
        self.assertIsNone(pnl.run_stats(curve([]), Window("all")))

    def test_net_pct_needs_a_positive_base(self) -> None:
        c = curve([("2026-01-01", 0, 5.0)], initial=0.0)
        s = pnl.run_stats(c, Window("all"))
        self.assertEqual(s.net, 5.0)
        self.assertIsNone(s.net_pct)

    def test_pct_ok_false_withholds_the_percentage(self) -> None:
        s = pnl.run_stats(curve([("2026-01-01", 0, 1100)], pct_ok=False), Window("all"))
        self.assertIsNone(s.net_pct)

    def test_costs_gross_realized_and_unrealized(self) -> None:
        fills = [Fill(at("2026-01-01", 1), fee=2, slippage=1),                    # open, before window
                 Fill(at("2026-01-02", 1), fee=3, slippage=2, realized=40.0),     # close, in window
                 Fill(at("2026-01-03", 1), fee=1, slippage=1, borrow=0.5, realized=-10.0),
                 Fill(at("2026-01-04", 1), fee=9)]                                 # after the end
        c = curve([("2026-01-01", 0, 1000), ("2026-01-03", 12, 1050)], fills=fills)
        s = pnl.run_stats(c, Window("x", at("2026-01-02"), at("2026-01-03", 23)))
        self.assertEqual(s.costs, {"fees": 4, "slippage": 3, "borrow": 0.5})
        self.assertAlmostEqual(s.gross, 50 + 7.5)
        self.assertEqual(s.realized, 30.0)
        self.assertEqual(s.unrealized, 20.0)
        self.assertEqual(s.closes, [40.0, -10.0])

    def test_unwindowed_curve_ignores_the_window(self) -> None:
        c = curve([("2026-01-01", 0, 1100)], windowed=False)
        s = pnl.run_stats(c, Window("x", at("2030-01-01"), at("2030-02-01")))
        self.assertEqual(s.net, 100)


class SeriesTests(unittest.TestCase):
    def test_days_add_up_to_the_window_net_and_gaps_carry_forward(self) -> None:
        c = curve([("2026-01-01", 6, 1010), ("2026-01-01", 18, 1020), ("2026-01-04", 0, 1005)])
        base, days = pnl.combine_daily([c], Window("all"))
        self.assertEqual(base, 1000)
        self.assertEqual([d.date for d in days],
                         [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3), date(2026, 1, 4)])
        self.assertEqual([d.equity for d in days], [1020, 1020, 1020, 1005])  # day's last point wins
        self.assertEqual([d.pnl for d in days], [20, 0, 0, -15])
        self.assertEqual(sum(d.pnl for d in days), pnl.run_stats(c, Window("all")).net)
        self.assertEqual(days[-1].cumulative, 5)

    def test_first_day_is_measured_against_equity_before_the_window(self) -> None:
        c = curve([("2026-01-01", 0, 1000), ("2026-01-02", 12, 1100)])
        base, days = pnl.combine_daily([c], Window("x", at("2026-01-02"), None))
        self.assertEqual(base, 1000)
        self.assertEqual(days[0].pnl, 100)

    def test_combining_two_curves_of_one_source_sums_equity(self) -> None:
        a = curve([("2026-01-01", 0, 1100), ("2026-01-02", 0, 1200)], strategy="a")
        b = curve([("2026-01-02", 0, 800)], strategy="b")   # starts a day later, base 1000
        base, days = pnl.combine_daily([a, b], Window("all"))
        self.assertEqual(base, 2000)
        self.assertEqual([d.equity for d in days], [1100 + 1000, 1200 + 800])
        self.assertEqual([d.pnl for d in days], [100, -100])

    def test_no_points_inside_gives_none(self) -> None:
        self.assertIsNone(pnl.combine_daily([curve([("2026-01-01", 0, 1)])],
                                            Window("x", at("2027-01-01"), None)))


class DrawdownTests(unittest.TestCase):
    def days(self, equities, base=100.0):
        out, prev, peak = [], base, base
        for i, e in enumerate(equities):
            peak = max(peak, e)
            out.append(pnl.Day(date(2026, 1, 1 + i), e, e - prev, e - base, e / peak - 1))
            prev = e
        return base, out

    def test_max_drawdown_and_recovery(self) -> None:
        base, days = self.days([110, 120, 90, 100, 120, 130])
        r = pnl.drawdown_report(base, days)
        self.assertAlmostEqual(r["max_drawdown_pct"], -0.25)      # 120 -> 90
        self.assertEqual(r["max_drawdown_usd"], -30)
        self.assertEqual((r["peak_date"], r["trough_date"]), ("2026-01-02", "2026-01-03"))
        self.assertEqual(r["recovered_date"], "2026-01-05")
        self.assertEqual(r["recovery_days"], 2)
        self.assertTrue(r["recovered"])

    def test_not_recovered(self) -> None:
        base, days = self.days([120, 80, 90])
        r = pnl.drawdown_report(base, days)
        self.assertFalse(r["recovered"])
        self.assertIsNone(r["recovery_days"])
        self.assertAlmostEqual(r["max_drawdown_pct"], -40 / 120)

    def test_starting_value_counts_as_the_opening_peak(self) -> None:
        base, days = self.days([90, 95])
        r = pnl.drawdown_report(base, days)
        self.assertAlmostEqual(r["max_drawdown_pct"], -0.10)
        self.assertEqual(r["peak_date"], "window start")

    def test_only_gains_means_no_drawdown(self) -> None:
        base, days = self.days([101, 102])
        r = pnl.drawdown_report(base, days)
        self.assertEqual(r["max_drawdown_usd"], 0.0)
        self.assertIsNone(r["trough_date"])

    def test_empty(self) -> None:
        self.assertIsNone(pnl.drawdown_report(100, [])["trough_date"])


class BestWorstTests(unittest.TestCase):
    def test_day_week_month(self) -> None:
        # 2026-01-05 is a Monday.
        pnls = [("2026-01-02", 5), ("2026-01-05", -3), ("2026-01-06", 10), ("2026-02-02", -20)]
        days = [pnl.Day(date.fromisoformat(d), 0, v, 0, None) for d, v in pnls]
        r = pnl.best_worst(days)
        self.assertEqual(r["day"]["best"], {"period": "2026-01-06", "pnl": 10})
        self.assertEqual(r["day"]["worst"], {"period": "2026-02-02", "pnl": -20})
        self.assertEqual(r["week"]["best"], {"period": "2026-01-05", "pnl": 7})   # Mon-keyed
        self.assertEqual(r["month"]["best"], {"period": "2026-01", "pnl": 12})
        self.assertEqual(r["month"]["periods"], 2)

    def test_empty(self) -> None:
        self.assertIsNone(pnl.best_worst([])["day"])


class TradeStatsTests(unittest.TestCase):
    def test_win_rate_and_expectancy(self) -> None:
        r = pnl.trade_stats([30, -10, 20, 0, -20])
        self.assertEqual(r["closed_trades"], 5)
        self.assertAlmostEqual(r["win_rate"], 2 / 5)
        self.assertAlmostEqual(r["expectancy_usd"], 4.0)
        self.assertAlmostEqual(r["avg_win"], 25.0)
        self.assertAlmostEqual(r["avg_loss"], -15.0)
        self.assertAlmostEqual(r["profit_factor"], 50 / 30)

    def test_none_closed(self) -> None:
        r = pnl.trade_stats([])
        self.assertEqual(r["closed_trades"], 0)
        self.assertIsNone(r["win_rate"])
        self.assertIsNone(r["expectancy_usd"])

    def test_no_losses_has_no_profit_factor(self) -> None:
        self.assertIsNone(pnl.trade_stats([5, 6])["profit_factor"])


class SectionTests(unittest.TestCase):
    def two(self):
        a = curve([("2026-01-01", 0, 1100)], strategy="a", asset="SOL",
                  fills=[Fill(at("2026-01-01"), fee=1, slippage=1, realized=100.0)])
        b = curve([("2026-01-01", 0, 950)], strategy="b", asset="ETH",
                  fills=[Fill(at("2026-01-01"), fee=2, realized=-50.0)])
        return a, b

    def test_section_totals_and_label(self) -> None:
        sec = pnl.build_section("backtest", self.two(), Window("all"))
        t = sec["totals"]
        self.assertEqual(sec["label"], "backtest (simulated)")
        self.assertEqual((t["initial"], t["final"], t["net_usd"]), (2000, 2050, 50))
        self.assertAlmostEqual(t["net_pct"], 0.025)
        self.assertEqual(t["net_pct_text"], "backtest net +2.5%")
        self.assertEqual((t["fees_usd"], t["slippage_usd"], t["borrow_funding_usd"]), (3, 1, 0))
        self.assertEqual(t["gross_usd"], 54)
        self.assertEqual((t["realized_usd"], t["unrealized_usd"]), (50, 0))
        self.assertEqual(t["closed_trades"], 2)

    def test_contribution_points_sum_to_section_net_pct(self) -> None:
        sec = pnl.build_section("backtest", self.two(), Window("all"))
        pts = [r["contribution_pts"] for r in sec["by_strategy"]]
        self.assertAlmostEqual(sum(pts), sec["totals"]["net_pct"])
        self.assertAlmostEqual(pts[0], 0.05)
        self.assertAlmostEqual(sum(r["contribution_pts"] for r in sec["by_asset"]),
                               sec["totals"]["net_pct"])
        self.assertEqual({r["name"] for r in sec["by_asset"]}, {"SOL", "ETH"})
        self.assertAlmostEqual(sum(r["share_of_net"] for r in sec["by_strategy"]), 1.0)

    def test_no_data_section_says_where_the_data_is(self) -> None:
        sec = pnl.build_section("backtest", self.two(), Window("x", at("2030-01-01"), None))
        self.assertEqual(sec["status"], "no_data")
        self.assertIn("2026-01-01", sec["message"])
        self.assertNotIn("totals", sec)

    def test_no_curves_at_all(self) -> None:
        sec = pnl.build_section("paper", [], Window("all"), ["no paper session is open"])
        self.assertEqual(sec["status"], "no_data")
        self.assertIsNone(sec["data_range"])
        self.assertEqual(sec["notes"], ["no paper session is open"])

    def test_unwindowed_section_is_flagged(self) -> None:
        c = curve([("2026-01-01", 0, 1010)], source="live LP", windowed=False, has_trades=False,
                  fills=[Fill(at("2026-01-01"), fee=1, realized=3.0)])
        sec = pnl.build_section("live LP", [c], Window("x", at("2030-01-01"), None))
        self.assertFalse(sec["windowed"])
        self.assertTrue(any("not windowed" in n for n in sec["notes"]))
        self.assertEqual(sec["totals"]["net_usd"], 10)
        self.assertEqual(sec["totals"]["realized_usd"], 3)
        self.assertEqual(sec["totals"]["closed_trades"], 0)   # cash events are not round trips

    def test_report_never_sums_simulated_with_real(self) -> None:
        sim = curve([("2026-01-01", 0, 1100)], source="backtest")
        real = curve([("2026-01-01", 0, 60)], initial=50.0, source="live LP")
        rep = pnl.build_report([("backtest", [sim], []), ("live LP", [real], [])], Window("all"))
        self.assertEqual(rep["groups"], {"simulated": ["backtest"], "real": ["live LP"]})
        self.assertNotIn("totals", rep)
        self.assertNotIn("net_usd", rep)
        by = {s["source"]: s for s in rep["sections"]}
        self.assertEqual(by["backtest"]["totals"]["net_usd"], 100)
        self.assertEqual(by["live LP"]["totals"]["net_usd"], 10)
        self.assertEqual(by["live LP"]["totals"]["net_pct_text"], "live LP net +20.0%")
        self.assertIn("never summed", rep["notice"])

    def test_unknown_lp_mode_is_not_filed_as_simulated_or_real(self) -> None:
        self.assertEqual(pnl.lp_source("live"), "live LP")
        self.assertEqual(pnl.lp_source("dry-run"), "dry-run LP")
        self.assertEqual(pnl.lp_source(None), "reported LP")
        self.assertEqual(pnl.group_of("reported LP"), "unclassified")
        rep = pnl.build_report([("reported LP", [curve([("2026-01-01", 0, 1)], source="reported LP")],
                                 [])], Window("all"))
        self.assertIn("unclassified", rep["groups"])

    def test_every_percentage_text_names_its_source(self) -> None:
        paper = [Curve("paper", c.strategy, c.asset, c.initial, c.points, c.fills) for c in self.two()]
        sec = pnl.build_section("paper", paper, Window("all"))
        texts = [sec["totals"]["net_pct_text"]]
        texts += [r["net_pct_text"] for r in sec["by_strategy"] + sec["by_asset"]]
        for text in texts:
            self.assertRegex(text, r"^paper net [+-]\d")


class JournalTests(unittest.TestCase):
    def doc(self):
        def fill(i, side, qty, px, fee, t):
            return {"id": i, "side": side, "baseQty": qty, "priceUsd": px, "feeUsd": fee, "tsMs": t * 1000}
        return {"fills": {
            "1": fill("1", "buy", 1.0, 100.0, 0.1, at("2026-01-01")),
            "2": fill("2", "buy", 1.0, 110.0, 0.1, at("2026-01-02")),
            "3": fill("3", "sell", 1.5, 120.0, 0.2, at("2026-01-03"))},
            "carry": {"c": {"tsMs": at("2026-01-03", 5) * 1000, "costUsd": 0.5}}}

    def test_fifo_round_trip_net_of_fees_and_carry(self) -> None:
        (c,) = pnl.curves_from_journal(self.doc())
        self.assertFalse(c.pct_ok)
        # sell 1.5: 1.0 @100 + 0.5 @110 -> gross 20 + 5 = 25; sell fee 0.2; entry fees 0.1 + 0.05
        close = next(f for f in c.fills if f.realized is not None)
        self.assertAlmostEqual(close.realized, 25 - 0.2 - 0.15)
        # equity is running net P&L: -0.1, -0.2, +24.6 (25-0.2 on top of -0.2), then carry -0.5
        self.assertAlmostEqual(c.points[-1][1], -0.1 - 0.1 + 24.8 - 0.5)
        sec = pnl.build_section("dry-run", [c], Window("all"))
        self.assertIsNone(sec["totals"]["net_pct"])
        self.assertEqual(sec["totals"]["closed_trades"], 1)
        self.assertAlmostEqual(sec["totals"]["borrow_funding_usd"], 0.5)

    def test_empty_or_malformed_journals_give_no_curve(self) -> None:
        for doc in (None, [], {}, {"fills": {}}, {"fills": {"x": {"tsMs": "no"}}}):
            self.assertEqual(pnl.curves_from_journal(doc), [])


def ledger() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript("""
    CREATE TABLE flows (id INTEGER PRIMARY KEY, slot TEXT, ts REAL, kind TEXT, amount0 REAL, amount1 REAL, usd REAL);
    CREATE TABLE events (id INTEGER PRIMARY KEY, ts REAL, slot TEXT, kind TEXT, gas_usd REAL, reward_usd REAL, detail TEXT, tx TEXT);
    CREATE TABLE snapshots (id INTEGER PRIMARY KEY, slot TEXT, ts REAL, token_id INTEGER, value_usd REAL, hodl_usd REAL, unclaimed_usd REAL);
    """)
    return c


class LiquidityTests(unittest.TestCase):
    def test_ledger_history_is_pnl_on_constant_basis(self) -> None:
        c = ledger()
        c.execute("INSERT INTO flows(slot,ts,kind,amount0,amount1,usd) VALUES ('1',?, 'deposit',0,0,100)", (at("2026-01-01"),))
        for d, v, u in (("2026-01-01", 100, 0), ("2026-01-02", 104, 1), ("2026-01-03", 101, 0)):
            c.execute("INSERT INTO snapshots(slot,ts,token_id,value_usd,hodl_usd,unclaimed_usd) VALUES ('1',?,1,?,?,?)",
                      (at(d, 1), v, v, u))
        c.execute("INSERT INTO events(ts,slot,kind,gas_usd,reward_usd) VALUES (?, '1','claim',0.5,2)", (at("2026-01-03"),))
        curve_ = pnl.curve_from_lp_ledger(c, "live")
        self.assertEqual(curve_.source, "live LP")
        self.assertEqual(curve_.initial, 100)
        # pnl: 0, 5, then 101 - 100 + 2 claimed - 0.5 gas = 2.5
        self.assertEqual([round(v - 100, 6) for _, v in curve_.points], [0, 5, 2.5])
        sec = pnl.build_section("live LP", [curve_], Window("x", at("2026-01-02"), None))
        self.assertTrue(sec["windowed"])
        self.assertAlmostEqual(sec["totals"]["net_usd"], 2.5)       # from the 01-01 point at 100
        self.assertAlmostEqual(sec["totals"]["realized_usd"], 1.5)  # 2 reward - 0.5 gas
        self.assertAlmostEqual(sec["totals"]["unrealized_usd"], 1.0)
        self.assertEqual(sec["totals"]["fees_usd"], 0.5)

    def test_empty_ledger_has_no_history(self) -> None:
        self.assertIsNone(pnl.curve_from_lp_ledger(ledger(), "live"))

    def test_status_figure_is_cumulative_and_unwindowed(self) -> None:
        status = {"mode": "dry-run", "generated_at": at("2026-01-05"),
                  "positions": [{"pnl_usd": -2.0, "deposited_usd": 40.0, "gas_usd": 0.3, "rewards_usd": 0.1},
                                {"pnl_usd": 1.0, "deposited_usd": 10.0, "gas_usd": 0.1, "rewards_usd": 0.0}]}
        c = pnl.curve_from_lp_status(status)
        self.assertEqual(c.source, "dry-run LP")
        self.assertFalse(c.windowed)
        sec = pnl.build_section("dry-run LP", [c], Window("7d", NOW - 7 * 86400, NOW))
        self.assertAlmostEqual(sec["totals"]["net_usd"], -1.0)
        self.assertAlmostEqual(sec["totals"]["net_pct"], -1 / 50)
        self.assertEqual(sec["group"], "simulated")

    def test_no_positions_gives_no_curve(self) -> None:
        self.assertIsNone(pnl.curve_from_lp_status({"mode": "live", "positions": []}))


if __name__ == "__main__":
    unittest.main()
