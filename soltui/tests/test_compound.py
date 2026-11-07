"""Compound five-minute tester: saved config, live reads, forward ledger, and the tab."""

from __future__ import annotations

import io
import json
import math
import os
from contextlib import redirect_stdout
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import numpy as np
from textual.widgets import Button, DataTable, Input, TabbedContent

from backtester.core import scorecard as sc
from backtester.tests.test_scorecard import synthetic
from soltui import commands, compound
from soltui import config as config_mod
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tui import SolTuiApp

T0 = 1_794_000_000  # a 5m boundary


def candles(n: int, last_start: int, seed: int = 1) -> list[list[float]]:
    """Coinbase-shaped rows, newest first: [time, low, high, open, close, volume]."""
    rng = np.random.default_rng(seed)
    close = 90 * np.exp(np.cumsum(rng.normal(0, 1e-3, n)))
    rows = []
    for i in range(n):
        t = last_start - 300 * (n - 1 - i)
        o = close[i - 1] if i else close[0]
        c = close[i]
        rows.append([t, min(o, c) * 0.999, max(o, c) * 1.001, o, c, 100.0 + i])
    return list(reversed(rows))


class Venue:
    """Stub Coinbase/Hyperliquid: candles up to `now`, one context, a book."""

    def __init__(self, now: float) -> None:
        self.now = now
        self.series = {p: candles(900, T0 + 300 * 20, seed=s) for p, s in (("SOL", 1), ("BTC", 2))}
        self.urls: list[str] = []

    def get(self, url: str):
        self.urls.append(url)
        product = url.split("/products/")[1].split("-")[0]
        rows = [r for r in self.series[product] if r[0] <= self.now]  # includes the forming bar
        start = url.split("start=")[1].split("&")[0]
        end = url.split("end=")[1]
        import calendar
        import time as _t
        s = calendar.timegm(_t.strptime(start, "%Y-%m-%dT%H:%M:%SZ"))
        e = calendar.timegm(_t.strptime(end, "%Y-%m-%dT%H:%M:%SZ"))
        return [r for r in rows if s <= r[0] <= e]

    def post(self, url: str, body: dict):
        if body["type"] == "metaAndAssetCtxs":
            return [{"universe": [{"name": "BTC"}, {"name": "SOL"}]},
                    [{"funding": "0.00001"}, {"funding": "0.0000125", "premium": "-0.0004",
                                              "openInterest": "5000000", "markPx": "90", "oraclePx": "90.1"}]]
        return {"levels": [[{"px": "89.99", "sz": "300"}, {"px": "89.9", "sz": "50"}],
                           [{"px": "90.01", "sz": "100"}, {"px": "90.5", "sz": "999"}]]}


class TempConfig(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(config_mod, "CONFIG_DIR", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)


class ConfigTests(TempConfig):
    def test_save_merge_reset_round_trip(self) -> None:
        state = compound.save_state({"components": {"rsi": {"enabled": False, "weight": 2,
                                                            "params": {"period": 9}}},
                                     "aggregate": {"entry": 0.4}})
        self.assertFalse(state["config"]["components"]["rsi"]["enabled"])
        again = compound.load_state()
        self.assertEqual(again["config"]["components"]["rsi"]["params"]["period"], 9)
        self.assertEqual(again["config"]["aggregate"]["entry"], 0.4)
        self.assertEqual(compound.save_state(reset=True)["config"], sc.default_config())

    def test_edit_box_parsing_and_errors(self) -> None:
        self.assertEqual(compound.parse_kv("weight=1.5, period=9"), {"weight": 1.5, "period": 9.0})
        patch = compound.component_patch("rsi", {"weight": 2.0, "enabled": 0.0, "period": 9.0})
        self.assertEqual(patch, {"components": {"rsi": {"weight": 2.0, "enabled": False, "params": {"period": 9.0}}}})
        self.assertEqual(compound.aggregate_patch({"entry": 0.3, "leverage": 10.0}),
                         {"aggregate": {"entry": 0.3}, "execution": {"leverage": 10.0}})
        for bad in (lambda: compound.parse_kv("period"), lambda: compound.parse_kv("period=x"),
                    lambda: compound.aggregate_patch({"bogus": 1.0}),
                    lambda: compound.component_patch("nope", {}),
                    lambda: compound.save_state({"components": {"rsi": {"params": {"period": 0}}}}),
                    lambda: compound.save_state(events=[{"title": "no ts"}])):
            with self.assertRaises(compound.CompoundError):
                bad()

    def test_a_refused_save_leaves_the_file_unchanged(self) -> None:
        compound.save_state({"components": {"rsi": {"weight": 2}}})
        before = compound.config_path().read_text()
        with self.assertRaises(compound.CompoundError):
            compound.save_state({"aggregate": {"entry": 5}})
        self.assertEqual(compound.config_path().read_text(), before)

    def test_bad_asset_symbols_never_become_paths(self) -> None:
        for bad in ("../x", "", "SOL/USD", "a" * 20):
            with self.assertRaises(compound.CompoundError):
                compound.forward_path(bad)


class LiveReadTests(TempConfig):
    def test_the_forming_bar_is_dropped_and_coinbase_order_is_mapped(self) -> None:
        venue = Venue(now=T0 + 300 * 20 + 150)  # mid-way through the bar starting T0+6000
        raw = compound.fetch_closed_candles("SOL", now=venue.now, get=venue.get)
        self.assertEqual(int(raw["ts"][-1]), T0 + 300 * 19)
        row = next(r for r in venue.series["SOL"] if r[0] == T0 + 300 * 19)
        self.assertEqual(raw["low"][-1], row[1])
        self.assertEqual(raw["high"][-1], row[2])
        self.assertEqual(raw["open"][-1], row[3])
        self.assertEqual(raw["close"][-1], row[4])
        self.assertTrue(np.all(np.diff(raw["ts"]) == 300))

    def test_book_imbalance_counts_only_depth_near_mid(self) -> None:
        book = Venue(0).post("", {"type": "l2Book"})
        self.assertAlmostEqual(compound.book_imbalance(book, 10), (300 - 100) / 400)
        self.assertAlmostEqual(compound.book_imbalance(book, 100), (350 - 1099) / 1449)

    def test_headlines_match_names_inside_the_window(self) -> None:
        now = 1_800_000_000
        from email.utils import formatdate
        rss = ("<rss><channel>"
               f"<item><title>Solana validators upgrade</title><pubDate>{formatdate(now - 600)}</pubDate></item>"
               f"<item><title>Solaris is a film</title><pubDate>{formatdate(now - 60)}</pubDate></item>"
               f"<item><title>SOL ETF filed</title><pubDate>{formatdate(now - 7200)}</pubDate></item>"
               "</channel></rss>")
        hits = compound.headline_hits("SOL", 30, now=now, get_text=lambda url: rss)
        self.assertEqual([h["title"] for h in hits], ["Solana validators upgrade"] * len(compound.NEWS_FEEDS))

    def test_one_dead_feed_is_enough_to_fail_closed(self) -> None:
        def half(url: str) -> str:
            if url == compound.NEWS_FEEDS[0]:
                raise urllib.error.URLError("offline")
            return "<rss><channel></channel></rss>"

        with self.assertRaises(compound.CompoundError):
            compound.headline_hits("SOL", 30, now=1_800_000_000, get_text=half)

    def test_reset_keeps_the_event_list(self) -> None:
        compound.save_state({"components": {"rsi": {"weight": 3}}}, events=[{"ts": 1_800_000_000, "title": "CPI"}])
        state = compound.save_state(reset=True)
        self.assertEqual(state["config"], sc.default_config())
        self.assertEqual(state["events"], [{"ts": 1_800_000_000, "title": "CPI"}])

    def test_an_enabled_news_gate_fails_closed_when_feeds_are_down(self) -> None:
        compound.save_state({"components": {"gate_news": {"enabled": True}}})
        venue = Venue(now=T0 + 300 * 20 + 10)

        def down(url: str) -> str:
            raise urllib.error.URLError("offline")

        x = compound.signal("SOL", now=venue.now, get=venue.get, post=venue.post, get_text=down)
        self.assertIn("gate_news", x["blocked_by"])
        self.assertEqual(x["call"], "FLAT")
        self.assertIn("news_error", x["notes"])

    def test_live_signal_explains_every_component(self) -> None:
        compound.save_state({"components": {c: {"enabled": True} for c in ("premium", "book_imbalance")}})
        venue = Venue(now=T0 + 300 * 20 + 10)
        x = compound.signal("SOL", now=venue.now, get=venue.get, post=venue.post)
        rows = {r["id"]: r for r in x["components"]}
        self.assertEqual(set(rows), set(sc.BY_ID))
        self.assertEqual(rows["premium"]["status"], "scored")
        self.assertAlmostEqual(rows["premium"]["score"], round(-math.tanh(-0.0004 / 5e-4), 4))
        self.assertEqual(rows["btc_lead"]["status"], "scored")
        self.assertEqual(x["bar_ts"], T0 + 300 * 19)  # the bar starting T0+6000 is still forming


class ForwardLedgerTests(TempConfig):
    def test_records_once_per_bar_then_resolves_with_the_next_close(self) -> None:
        venue = Venue(now=T0 + 300 * 19 + 10)
        first = compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post)
        again = compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post)
        self.assertTrue(first["recorded"])
        self.assertFalse(again["recorded"])
        venue.now += 300
        second = compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post)
        self.assertTrue(second["recorded"])
        self.assertEqual(second["resolved"], 1)
        ledger = compound.read_ledger("SOL")
        call = next(r for r in ledger if r["type"] == "call" and r["bar_ts"] == first["bar_ts"])
        res = next(r for r in ledger if r["type"] == "resolve" and r["id"] == call["id"])
        nxt = next(r[4] for r in venue.series["SOL"] if r[0] == first["bar_ts"] + 300)
        self.assertAlmostEqual(res["ret_bps"], round(1e4 * math.log(nxt / call["price"]), 4))
        self.assertIn("rsi", call["scores"])
        self.assertTrue(any(r["type"] == "ctx" and r["oi"] == 5_000_000 for r in ledger))

    def test_status_tallies_compound_ungated_and_each_component(self) -> None:
        rows = []
        for i, (call, ungated, rsi, ret) in enumerate([("UP", 1, 0.6, 5.0), ("DOWN", -1, -0.5, 3.0),
                                                       ("FLAT", 1, 0.1, 2.0), ("FLAT", 0, -0.9, -4.0)]):
            cid = f"SOL:{i}:h"
            rows.append({"type": "call", "id": cid, "bar_ts": T0 + 300 * i, "price": 90.0, "call": call,
                         "ungated": ungated, "composite": 0.3, "config_hash": "h", "entry": 0.25,
                         "round_trip_bps": 16.0, "scores": {"rsi": rsi}})
            rows.append({"type": "resolve", "id": cid, "next_close": 90.0, "ret_bps": ret})
        compound._append("SOL", rows)
        s = compound.forward_status("SOL")
        self.assertEqual(s["compound"]["decided"], 2)
        self.assertEqual(s["compound"]["hit_rate"], 0.5)
        self.assertEqual(s["compound_ungated"]["decided"], 3)
        self.assertEqual(s["components"]["rsi"]["decided"], 3)  # |0.1| < entry abstains
        self.assertEqual(s["components"]["rsi"]["hit_rate"], round(2 / 3, 4))
        self.assertEqual(s["compound"]["net_bps_per_call_if_one_bar"], round((5.0 - 3.0) / 2 - 16.0, 3))

    def test_a_call_before_a_feed_gap_still_resolves(self) -> None:
        venue = Venue(now=T0 + 300 * 15 + 10)
        first = compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post)
        # A gap two bars after the call puts the resolving bar in an OLDER contiguous run than
        # the one being scored; resolution must still find it.
        gap = first["bar_ts"] + 600
        venue.series["SOL"] = [r for r in venue.series["SOL"] if r[0] != gap]
        venue.now = T0 + 300 * 19 + 10
        compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post)
        ledger = compound.read_ledger("SOL")
        self.assertTrue(any(r["type"] == "resolve" and r["id"].split(":")[1] == str(first["bar_ts"])
                            for r in ledger))

    def test_ledger_seed_counts_only_earlier_calls_with_matching_parameters(self) -> None:
        cfg = sc.default_config()
        cfg["aggregate"]["adaptive_window"] = 6
        sig = compound.component_sig("rsi", cfg["components"]["rsi"]["params"])
        stale = compound.component_sig("rsi", {**cfg["components"]["rsi"]["params"], "period": 9})
        W = T0 + 3000

        def call(i, bar_ts, score, s=sig):
            return {"type": "call", "id": f"c{i}", "bar_ts": bar_ts, "scores": {"rsi": score}, "sigs": {"rsi": s}}

        ledger = [call(1, W - 300, 0.6), {"type": "resolve", "id": "c1", "ret_bps": 3.0},        # right, k=-1
                  call(2, W - 600, -0.6), {"type": "resolve", "id": "c2", "ret_bps": 2.0},       # wrong, k=-2
                  call(3, W, 0.9), {"type": "resolve", "id": "c3", "ret_bps": 1.0},              # inside the bars
                  call(4, W - 900, 0.9, stale), {"type": "resolve", "id": "c4", "ret_bps": 1.0},  # other settings
                  call(5, W - 1200, 0.1), {"type": "resolve", "id": "c5", "ret_bps": 1.0},       # abstained
                  call(6, W - 1500, 0.8),                                                        # unresolved
                  call(7, W - 3000, 0.8), {"type": "resolve", "id": "c7", "ret_bps": 1.0}]       # past the window
        seed = compound.ledger_seed(ledger, cfg, W)
        self.assertEqual(sorted(seed["rsi"]), [(-2, 0.0, 1.0), (-1, 1.0, 1.0)])

    def test_forward_calls_record_metric_signatures(self) -> None:
        venue = Venue(now=T0 + 300 * 19 + 10)
        compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post)
        call = next(r for r in compound.read_ledger("SOL") if r["type"] == "call")
        self.assertEqual(set(call["sigs"]), set(call["scores"]))
        self.assertTrue(call["adaptive"])

    def test_a_call_appended_twice_counts_once(self) -> None:
        call = {"type": "call", "id": "SOL:1:h", "bar_ts": T0, "price": 90.0, "call": "UP", "ungated": 1,
                "composite": 0.4, "config_hash": "h", "entry": 0.25, "round_trip_bps": 16.0, "scores": {}}
        compound._append("SOL", [call, call, {"type": "resolve", "id": "SOL:1:h", "ret_bps": 4.0}])
        s = compound.forward_status("SOL")
        self.assertEqual((s["calls_recorded"], s["compound"]["decided"]), (1, 1))

    def test_a_torn_last_line_is_skipped(self) -> None:
        compound._append("SOL", [{"type": "call", "id": "x"}])
        with compound.forward_path("SOL").open("a") as fh:
            fh.write('{"type": "resol')
        self.assertEqual(len(compound.read_ledger("SOL")), 1)


ADDR = "EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCE8BenwNYB"


def fake_scan(status="ok", sol_usd=900.0, usdt_usd=None):
    class Scan:
        def to_dict(self):
            return {"status": status, "errors": [] if status == "ok" else [{"source": "rpc", "message": "down"}],
                    "native": {"symbol": "SOL", "amount": 5.0, "usd": sol_usd},
                    "holdings": [
                        {"mint": USDC, "symbol": "USDC", "amount": 100.0, "usd": 100.0, "included": True},
                        {"mint": "FakeMint1111111111111111111111111111111111", "symbol": "USDC", "amount": 1e6,
                         "usd": 1e6, "included": True},
                        {"mint": USDT, "symbol": "USDT", "amount": 50.0, "usd": usdt_usd, "included": True},
                    ]}
    return lambda address, fetch: Scan()


class WalletTests(TempConfig):
    def setUp(self) -> None:
        super().setUp()
        compound._WALLET_CACHE.clear()

    def test_no_address_means_no_size_not_a_guess(self) -> None:
        w = compound.wallet_balances("")
        self.assertFalse(w["available"])
        self.assertIn("Settings", w["reason"])
        s = compound.size_call(w, synthetic(300), sc.default_config(), "UP")
        self.assertFalse(s["available"])

    def test_collateral_is_matched_by_mint_and_unpriced_is_unknown(self) -> None:
        with mock.patch.object(compound.wallet_mod, "scan_solana", fake_scan()):
            w = compound.wallet_balances(ADDR, fetch=lambda *a: None)
        self.assertEqual(w["usable_usd"], 1000.0)               # SOL 900 + real USDC 100; fake USDC ignored
        self.assertEqual(w["parts"], {"SOL": 900.0, "USDC": 100.0})
        self.assertEqual(w["unpriced"], ["USDT"])
        self.assertFalse(w["complete"])
        self.assertEqual(w["label"], "wallet (live)")

    def test_a_failed_scan_is_unavailable(self) -> None:
        def broken(address, fetch):
            class S:
                def to_dict(self):
                    return {"status": "error", "errors": [{"source": "rpc", "message": "connection refused"}],
                            "native": None, "holdings": []}
            return S()
        with mock.patch.object(compound.wallet_mod, "scan_solana", broken):
            w = compound.wallet_balances(ADDR, fetch=lambda *a: None)
        self.assertFalse(w["available"])
        self.assertIn("connection refused", w["reason"])

    def test_size_is_the_smaller_of_risk_and_leverage_limits_with_venue_liquidation(self) -> None:
        bars = synthetic(400)
        cfg = sc.default_config()
        cfg["execution"].update(leverage=5.0, risk_pct=1.0)
        w = {"available": True, "usable_usd": 1000.0, "complete": True}
        s = compound.size_call(w, bars, cfg, "UP")
        atr = float(sc.atr(bars, 14)[-1])
        stop = 1.5 * atr / bars.close[-1]
        cost = 16.0 / 1e4
        self.assertAlmostEqual(s["risk_notional_usd"], round(10.0 / (stop + cost), 2), places=1)
        self.assertEqual(s["notional_usd"], round(min(5000.0, 10.0 / (stop + cost)), 2))
        self.assertAlmostEqual(s["loss_at_stop_usd"], 10.0, places=1)
        self.assertEqual(s["side"], "long")
        self.assertLess(s["liquidation_price"]["long"], bars.close[-1])
        self.assertGreater(s["liquidation_price"]["short"], bars.close[-1])
        cfg["execution"]["risk_pct"] = 100.0
        big = compound.size_call(w, bars, cfg, "DOWN")
        self.assertEqual((big["bound_by"], big["notional_usd"], big["side"]), ("leverage", 5000.0, "short"))

    def test_signal_and_forward_tick_carry_the_wallet_and_paper_dollars(self) -> None:
        venue = Venue(now=T0 + 300 * 19 + 10)
        with mock.patch.object(compound.wallet_mod, "scan_solana", fake_scan(usdt_usd=50.0)):
            x = compound.signal("SOL", now=venue.now, get=venue.get, post=venue.post, wallet_address=ADDR,
                                wallet_fetch=lambda *a: None)
            self.assertTrue(x["wallet"]["available"])
            self.assertEqual(x["wallet"]["usable_usd"], 1050.0)
            self.assertTrue(x["sizing"]["available"])
            self.assertIn("wallet (live)", compound.wallet_line(x["wallet"], x["sizing"]))
            first = compound.forward_tick("SOL", now=venue.now, get=venue.get, post=venue.post,
                                          wallet_address=ADDR, wallet_fetch=lambda *a: None)
            self.assertGreater(first["notional_usd"], 0)

    def test_paper_dollars_use_each_calls_recorded_size(self) -> None:
        compound._append("SOL", [
            {"type": "call", "id": "a", "bar_ts": T0, "price": 90.0, "call": "UP", "notional_usd": 1000.0,
             "round_trip_bps": 16.0, "scores": {}},
            {"type": "resolve", "id": "a", "ret_bps": 30.0},
            {"type": "call", "id": "b", "bar_ts": T0 + 300, "price": 90.0, "call": "DOWN", "notional_usd": 2000.0,
             "round_trip_bps": 16.0, "scores": {}},
            {"type": "resolve", "id": "b", "ret_bps": 5.0},
            {"type": "call", "id": "c", "bar_ts": T0 + 600, "price": 90.0, "call": "UP", "notional_usd": None,
             "round_trip_bps": 16.0, "scores": {}},
            {"type": "resolve", "id": "c", "ret_bps": 50.0}])
        paper = compound.forward_status("SOL")["paper"]
        self.assertEqual(paper["calls"], 2)
        self.assertAlmostEqual(paper["net_usd"], round(1000 * (30 - 16) / 1e4 + 2000 * (-5 - 16) / 1e4, 2))

    def test_the_compound_module_never_touches_key_files(self) -> None:
        src = Path(compound.__file__).read_text()
        for forbidden in (".private", "key_dir(", "key_sources(", "~/.ssh"):
            self.assertNotIn(forbidden, src)


class SummaryTests(unittest.TestCase):
    def row(self, label, hit, z, ret, ranked=True):
        return {"asset": "SOL", "label": label, "oos_hit": hit, "oos_z": z, "oos_calls": 300, "oos_return": ret,
                "ranked": ranked, "oracle_net_bps": -7.5, "round_trip_bps": 16.0, "split_ts": T0,
                "to_ts": T0 + 9 * 86400, "oos_bars": 2678}

    def test_plain_language_verdicts(self) -> None:
        self.assertIn("No backtest yet", compound.run_summary([]))
        none = compound.run_summary([self.row("compound", 0.5, 0.1, -0.3), self.row("only:rsi", 0.51, 1.2, -0.2)], 30)
        self.assertIn("no measurable edge", none)
        self.assertIn("2 configurations tested (30 on this window", none)
        self.assertIn("perfect next-bar call would net -7.5 bps", none)
        eaten = compound.run_summary([self.row("only:rsi", 0.55, 2.5, -0.1)])
        self.assertIn("costs eat it", eaten)
        maybe = compound.run_summary([self.row("only:rsi", 0.55, 2.5, 0.04)])
        self.assertIn("possible edge", maybe)


class UnattendedTests(TempConfig):
    def test_the_loop_ticks_survives_errors_and_stops_on_request(self) -> None:
        calls = []

        def tick(asset, wallet_address=None):
            calls.append(asset)
            if len(calls) == 2:
                raise RuntimeError("network down")
            if len(calls) == 3:
                compound.unattended_paths(asset)["stop"].write_text("stop")
            return {"call": "FLAT"}

        clock = [1_800_000_000.0]

        def sleep(s):
            clock[0] += s

        out = io.StringIO()
        with redirect_stdout(out):
            code = compound.run_unattended("SOL", sleep=sleep, clock=lambda: clock[0], tick=tick)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 3)
        self.assertIn('"error": "RuntimeError: network down"', out.getvalue())
        self.assertIn("stopped after 3 tick(s)", out.getvalue())
        paths = compound.unattended_paths("SOL")
        self.assertFalse(paths["pid"].exists())
        self.assertFalse(compound.unattended_status("SOL")["running"])   # lock released

    def test_status_and_stop_use_the_lock_and_signal_the_pid(self) -> None:
        import subprocess
        paths = compound.unattended_paths("SOL")
        fd = compound._try_lock(paths["lock"])                 # pretend a run holds the lock
        sleeper = subprocess.Popen(["sleep", "30"])
        try:
            paths["pid"].write_text(str(sleeper.pid))
            self.assertTrue(compound.unattended_status("SOL")["running"])
            with self.assertRaises(compound.CompoundError):
                compound.start_unattended("SOL")
            out = compound.stop_unattended("SOL")
            self.assertTrue(out["stopping"])
            self.assertEqual(sleeper.wait(timeout=5), -15)       # SIGTERM delivered
            self.assertTrue(paths["stop"].exists())
        finally:
            os.close(fd)
            if sleeper.poll() is None:
                sleeper.kill()
        self.assertFalse(compound.unattended_status("SOL")["running"])
        self.assertEqual(compound.stop_unattended("SOL")["message"], "not running")


class SweepTests(TempConfig):
    def test_one_failing_configuration_does_not_sink_the_sweep(self) -> None:
        real = compound.cbt.run_compound

        def flaky(asset, cfg, **kw):
            if kw.get("label") == "only:rsi":
                raise RuntimeError("boom")
            return real(asset, cfg, **kw)

        frame = __import__("backtester.tests.test_compound_backtest", fromlist=["frame"]).frame
        from backtester.tests.test_scorecard import synthetic
        prepared = compound.cbt.prepare("SOL", bars=frame(synthetic(900)), source="synthetic")
        with mock.patch.object(compound.cbt, "run_compound", flaky), \
                mock.patch.object(compound, "_prepared", lambda a: prepared), \
                mock.patch.object(compound.cbt, "load_bars_5m", lambda a: (prepared["bars"], "synthetic")):
            out = compound.sweep(["SOL"])
        self.assertEqual([e["label"] for e in out["errors"]], ["only:rsi"])
        self.assertIn("RuntimeError: boom", out["errors"][0]["error"])
        written = compound.read_results()
        self.assertEqual(len(written), out["configurations"])
        latest = compound.latest_results("SOL")
        self.assertEqual(latest["configurations_on_this_oos_window"], out["configurations"] - 1)


class CommandTests(TempConfig):
    def test_save_and_config_round_trip_through_the_registry(self) -> None:
        env = commands.dispatch("compound.save", {"patch": {"components": {"rsi": {"weight": 3}}}}, surface="cli")
        self.assertTrue(env["ok"], env)
        env = commands.dispatch("compound.config", {}, surface="cli")
        self.assertEqual(env["result"]["config"]["components"]["rsi"]["weight"], 3)
        bad = commands.dispatch("compound.save", {"patch": {"components": {"rsi": {"weight": 99}}}}, surface="cli")
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["error"]["code"], "failed")
        self.assertIn("rsi", bad["error"]["message"])

    def test_results_on_an_empty_store(self) -> None:
        env = commands.dispatch("compound.results", {}, surface="cli")
        self.assertEqual(env["result"]["rows"], [])


class CompoundTab(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(config_mod, "CONFIG_DIR", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def cell(self, app, cid: str, column: str) -> str:
        table = app.query_one("#compound-table", DataTable)
        idx = table.get_row_index(cid)
        labels = [str(c.label) for c in table.ordered_columns]
        return str(table.get_row_at(idx)[labels.index(column)])

    async def test_toggle_edit_and_signal_from_the_tab(self) -> None:
        app = SolTuiApp(make_settings())
        fake = {"asset": "SOL", "call": "UP", "composite": 0.41, "coverage": 1.0, "agreement": 0.8,
                "regime": "range", "trend_stage": "early", "cycle_phase": "markup", "blocked_by": [],
                "round_trip_bps": 16.0, "decided_at": T0, "bars_used": 600,
                "components": [{"id": "rsi", "status": "scored", "score": 0.73, "kind": "score", "enabled": True},
                               {"id": "gate_cost", "status": "pass", "kind": "gate", "enabled": True,
                                "blocked": False}]}
        real = commands.COMMANDS["compound.signal"]
        stub = commands.Command("compound.signal", "stub", lambda ctx, p: fake, real.params, True, True, False)
        with mock.patch.dict(commands.COMMANDS, {"compound.signal": stub}):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-compound"
                await pilot.pause()
                table = app.query_one("#compound-table", DataTable)
                self.assertEqual(table.row_count, len(sc.COMPONENTS))
                table.move_cursor(row=table.get_row_index("rsi"))
                await pilot.pause()
                self.assertIn("period=14", app.query_one("#compound-edit", Input).value)
                self.assertIn("RSI", text_of(app, "#compound-detail"))

                app.query_one("#compound-toggle", Button).press()
                await pilot.pause()
                self.assertEqual(self.cell(app, "rsi", "on"), "off")

                app.query_one("#compound-edit", Input).value = "weight=2 period=9"
                app.query_one("#compound-agg", Input).value = "entry=0.3 leverage=10"
                app.query_one("#compound-apply", Button).press()
                await pilot.pause()
                self.assertEqual(self.cell(app, "rsi", "weight"), "2")
                self.assertIn("period=9", self.cell(app, "rsi", "parameters"))

                app.query_one("#compound-edit", Input).value = "period=0"
                app.query_one("#compound-apply", Button).press()
                await pilot.pause()
                self.assertIn("outside", text_of(app, "#compound-status"))

                app.query_one("#compound-signal", Button).press()
                await pilot.pause(0.3)
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertIn("UP", text_of(app, "#compound-call"))
                self.assertEqual(self.cell(app, "rsi", "live score"), "+0.73")
                self.assertEqual(self.cell(app, "gate_cost", "live score"), "pass")
        saved = json.loads(compound.config_path().read_text())["config"]
        self.assertFalse(saved["components"]["rsi"]["enabled"])
        self.assertEqual(saved["components"]["rsi"]["params"]["period"], 9)
        self.assertEqual(saved["aggregate"]["entry"], 0.3)
        self.assertEqual(saved["execution"]["leverage"], 10.0)


    async def test_learned_and_tuned_columns_and_adopt(self) -> None:
        app = SolTuiApp(make_settings())
        tuned = {**sc.BY_ID["rsi"].defaults(), "period": 11}
        fake = {"asset": "SOL", "call": "FLAT", "composite": 0.1, "coverage": 1.0, "agreement": 0.5,
                "regime": "range", "trend_stage": "early", "cycle_phase": "markup", "blocked_by": [],
                "round_trip_bps": 16.0, "decided_at": T0, "bars_used": 2016,
                "components": [{"id": "rsi", "status": "scored", "score": 0.4, "kind": "score", "enabled": True,
                                "learned_hit": 0.534, "learned_calls": 812.0, "adaptive_mult": 0.068,
                                "tuned_params": tuned},
                               {"id": "ema_cross", "status": "scored", "score": -0.5, "kind": "score",
                                "enabled": True, "learned_hit": 0.47, "learned_calls": 900.0, "adaptive_mult": 0.0}]}
        real = commands.COMMANDS["compound.signal"]
        stub = commands.Command("compound.signal", "stub", lambda ctx, p: fake, real.params, True, True, False)
        with mock.patch.dict(commands.COMMANDS, {"compound.signal": stub}):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-compound"
                await pilot.pause()
                app.query_one("#compound-adopt", Button).press()
                await pilot.pause()
                self.assertIn("nothing to adopt", text_of(app, "#compound-status"))
                app.query_one("#compound-signal", Button).press()
                await pilot.pause(0.3)
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertIn("53.4% (812) x+0.07", self.cell(app, "rsi", "learned hit (n)"))
                self.assertEqual(self.cell(app, "rsi", "tuned to"), "period=11")
                self.assertIn("x+0.00", self.cell(app, "ema_cross", "learned hit (n)"))
                app.query_one("#compound-adopt", Button).press()
                await pilot.pause()
                self.assertIn("period=11", self.cell(app, "rsi", "parameters"))
                self.assertEqual(self.cell(app, "rsi", "tuned to"), "")
        saved = json.loads(compound.config_path().read_text())["config"]
        self.assertEqual(saved["components"]["rsi"]["params"]["period"], 11)


class CompoundTabClicks(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(config_mod, "CONFIG_DIR", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def on(self, app, cid: str) -> str:
        table = app.query_one("#compound-table", DataTable)
        return str(table.get_row_at(table.get_row_index(cid))[0])

    async def test_clicking_on_or_name_toggles_and_space_toggles(self) -> None:
        from soltui.tui import CompoundTable
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-compound"
            await pilot.pause()
            table = app.query_one("#compound-table", CompoundTable)
            row = table.get_row_index("rsi")
            self.assertEqual(self.on(app, "rsi"), "on")
            table.post_message(CompoundTable.Toggle(row))          # what a click on "on"/name posts
            await pilot.pause()
            self.assertEqual(self.on(app, "rsi"), "off")
            table.focus()
            table.move_cursor(row=row)
            await pilot.pause()
            await pilot.press("space")
            await pilot.pause()
            self.assertEqual(self.on(app, "rsi"), "on")
            # A real mouse click on the first cell of the macd row.
            mrow = table.get_row_index("macd")
            table.scroll_to(y=0, animate=False)
            await pilot.pause()
            await pilot.click("#compound-table", offset=(2, mrow + 1))
            await pilot.pause()
            self.assertEqual(self.on(app, "macd"), "off")
        saved = json.loads(compound.config_path().read_text())["config"]
        self.assertTrue(saved["components"]["rsi"]["enabled"])
        self.assertFalse(saved["components"]["macd"]["enabled"])


if __name__ == "__main__":
    unittest.main()
