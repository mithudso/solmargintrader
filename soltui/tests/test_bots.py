"""The Bots tab's engine: configs, data, backtests, forward tests and the auto-optimize gate.

No network and no real price data: bars come from `SyntheticLoader` written to a temporary data
directory, and recorded snapshots are written to a temporary prices directory.
"""

from __future__ import annotations

import gzip
import json
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

import numpy as np

from backtester.core.data import SyntheticLoader
from soltui import bots, config as config_mod, pricefeed
from soltui.config import Settings

DAY = 86_400


def write_hourly(data: Path, asset: str, n: int = 24 * 400, seed: int = 3, start_ts: int = 1_700_000_000 // 3600 * 3600,
                 drop: tuple[int, ...] = ()) -> np.ndarray:
    df = SyntheticLoader(n_bars=n, seed=seed, start_ts=start_ts).load(asset, None, None, "1h")
    if drop:
        df = df.drop(index=list(drop)).reset_index(drop=True)
    df.to_csv(data / f"{asset}_1h.csv", index=False)
    return df["timestamp"].to_numpy()


def write_snapshots(prices: Path, rows: list[tuple[float, dict]]) -> None:
    prices.mkdir(parents=True, exist_ok=True)
    by_day: dict[Path, list[str]] = {}
    for t, q in rows:
        by_day.setdefault(pricefeed.day_path(t, prices), []).append(json.dumps({"t": t, "q": q}))
    for path, lines in by_day.items():
        with gzip.open(path, "at", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def tri_quotes(t: float, cross: float = 0.05) -> dict:
    return {"ETH-USD": [3000.0, 3000.3, 3000.1, 5, 5, t], "BTC-USD": [60000.0, 60006.0, 60003, 1, 1, t],
            "ETH-BTC": [cross, cross * 1.0001, cross, 50, 50, t], "SOL-USD": [100.0, 100.02, 100.01, 10, 10, t]}


class Isolated(unittest.TestCase):
    """A throwaway config dir (bots/, prices/) and data dir per test."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.data = root / "data"
        self.data.mkdir()
        patcher = mock.patch.object(config_mod, "CONFIG_DIR", root / "config")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = Settings(data_dir=str(self.data), fee_bps=6.0, slippage_bps=2.0)
        bots._HOURLY_CACHE.clear()
        bots.runtime().sessions.clear()
        bots.runtime().progress.clear()


class Configs(Isolated):
    def test_defaults_validate_and_unknown_names_are_refused(self) -> None:
        for bot in bots.BOTS:
            self.assertEqual(bots.get_config(bot), bots.DEFAULTS[bot])
        with self.assertRaisesRegex(bots.BotError, "unknown grid setting"):
            bots.save_config("grid", {"rangepct": 10})
        with self.assertRaisesRegex(bots.BotError, "venue minimum"):
            bots.save_config("grid", {"capital_usd": 50, "rungs": 9})
        with self.assertRaisesRegex(bots.BotError, "integer"):
            bots.save_config("dca", {"max_safety_orders": 2.5})
        with self.assertRaises(bots.BotError):
            bots.save_config("triangle", {"latency_s": -1})
        with self.assertRaises(bots.BotError):
            bots.get_config("nope")

    def test_save_coerces_persists_merges_and_resets(self) -> None:
        cfg = bots.save_config("dca", bots.parse_kv("take_profit_pct=3 max_safety_orders=4"))
        self.assertEqual((cfg["take_profit_pct"], cfg["max_safety_orders"]), (3.0, 4))
        self.assertIsInstance(cfg["max_safety_orders"], int)
        cfg = bots.save_config("dca", {"step_scale": "1.5"})
        self.assertEqual((cfg["take_profit_pct"], cfg["step_scale"]), (3.0, 1.5))
        self.assertEqual(bots.get_config("dca")["step_scale"], 1.5)
        self.assertEqual(bots.reset_config("dca"), bots.DEFAULTS["dca"])
        cfg = bots.save_config("triangle", {"use_displayed_size": "false"})
        self.assertIs(cfg["use_displayed_size"], False)

    def test_parse_kv_refuses_a_bare_word(self) -> None:
        with self.assertRaises(bots.BotError):
            bots.parse_kv("rungs 9")

    def test_grid_sets_its_ladder_around_the_start_price(self) -> None:
        g = bots.grid_sim_config({**bots.GRID_DEFAULTS, "range_pct": 10.0, "rungs": 5, "capital_usd": 500.0}, 200.0)
        self.assertAlmostEqual(g.lower, 180.0)
        self.assertAlmostEqual(g.upper, 220.0)
        self.assertAlmostEqual(g.notional_per_rung_usd, 100.0)


class Data(Isolated):
    def test_hourly_resamples_minutes_and_drops_thin_hours(self) -> None:
        start = 1_700_000_000 // 3600 * 3600
        minutes = SyntheticLoader(n_bars=60 * 5, seed=1, start_ts=start).load("ZZZ", None, None, "1m")
        thin = (minutes["timestamp"] >= start + 3600) & (minutes["timestamp"] < start + 7200)
        minutes = minutes[~thin | (minutes["timestamp"] < start + 3600 + 600)]  # hour 2 keeps 10 minutes
        minutes.to_csv(self.data / "ZZZ_1m.csv", index=False)
        h = bots.hourly("ZZZ", self.settings)
        self.assertEqual(h["source"], "1m->1h")
        self.assertEqual(list(h["ts"]), [start, start + 7200, start + 10800, start + 14400])
        first = minutes[minutes["timestamp"] < start + 3600]
        self.assertAlmostEqual(h["high"][0], first["high"].max())
        self.assertAlmostEqual(h["close"][0], first["close"].iloc[-1])
        self.assertEqual(bots.available_coins(self.settings), ["ZZZ"])

    def test_missing_coin_says_how_to_fetch(self) -> None:
        with self.assertRaisesRegex(bots.BotError, "backtester.core.fetch"):
            bots.hourly("NOPE", self.settings)

    def test_contiguous_and_windows_never_span_a_gap(self) -> None:
        ts = write_hourly(self.data, "SOL", n=24 * 100, drop=(24 * 60,))
        h = bots.hourly("SOL", self.settings)
        seg, gap = bots.contiguous(h, 0)
        self.assertEqual(seg["ts"].size, 24 * 60)
        self.assertEqual(gap, int(ts[24 * 60 - 1]))
        wins = bots.windows_for(h, 4, 24 * 15)
        self.assertEqual(len(wins), 4)
        for w in wins:
            self.assertTrue(np.all(np.diff(w["ts"]) == 3600))
        self.assertLess(wins[0]["ts"][0], wins[-1]["ts"][0])  # oldest first


class Backtests(Isolated):
    def test_grid_and_dca_backtest_from_a_chosen_start(self) -> None:
        ts = write_hourly(self.data, "SOL")
        start = int(ts[24 * 100])
        for bot in ("grid", "dca"):
            with self.subTest(bot=bot):
                r = bots.backtest(bot, "sol", self.settings, start=start, days=30)
                self.assertEqual(r["start_ts"], start)
                self.assertEqual(r["end_ts"], start + (30 * 24 - 1) * 3600)
                res = r["results"]
                self.assertIn("total_return", res)
                self.assertAlmostEqual(res["excess_return"], res["total_return"] - res["hold_return"])
                self.assertEqual(r["fee_bps"], 6.0)
        grid = bots.latest_results("grid")[0]
        price = grid["set"]["start_price"]
        self.assertAlmostEqual(grid["set"]["lower"], price * 0.85)
        self.assertEqual(len(grid["set"]["levels"]), 7)
        dca = bots.latest_results("dca")[0]
        self.assertEqual(dca["set"]["orders"][0]["order"], "base")
        self.assertEqual(len(bots.latest_results(None, 10)), 2)

    def test_a_start_past_the_data_or_right_before_a_long_gap_is_refused(self) -> None:
        long_gap = tuple(range(24 * 10 + 5, 24 * 10 + 5 + 60))  # 60 missing hours: too long to bridge
        ts = write_hourly(self.data, "SOL", n=24 * 30, drop=long_gap)
        with self.assertRaisesRegex(bots.BotError, "no cached bar"):
            bots.backtest("grid", "SOL", self.settings, start=int(ts[-1]) + 3600)
        with self.assertRaisesRegex(bots.BotError, "gap longer"):
            bots.backtest("grid", "SOL", self.settings, start=int(ts[24 * 10]))
        with self.assertRaisesRegex(bots.BotError, "UTC date"):
            bots.backtest("grid", "SOL", self.settings, start="last tuesday")

    def test_default_start_is_the_beginning_of_the_usable_data(self) -> None:
        ts = write_hourly(self.data, "SOL", n=24 * 60, drop=(100, 101, 102))  # a 3-hour gap is bridged
        r = bots.backtest("dca", "SOL", self.settings)
        self.assertEqual(r["start_ts"], int(ts[0]))
        self.assertEqual(r["end_ts"], int(ts[-1]))
        self.assertEqual((r["bridged_bars"], r["bridged_gaps"]), (3, 1))
        self.assertIsNone(r["start_note"])
        # After a gap too long to bridge, the default start moves past it and says why.
        long_gap = tuple(range(24 * 5, 24 * 5 + 72))
        ts = write_hourly(self.data, "BTC", n=24 * 40, drop=long_gap)
        r = bots.backtest("grid", "BTC", self.settings)
        self.assertEqual(r["start_ts"], int(ts[24 * 5]))
        self.assertIn("gaps longer than 48 h", r["start_note"])

    def test_bridged_bars_are_flat_at_the_last_close(self) -> None:
        h = {"ts": np.array([0, 3600, 4 * 3600, 5 * 3600]), "open": np.array([1.0, 2, 5, 6]),
             "high": np.array([1.5, 2.5, 5.5, 6.5]), "low": np.array([0.5, 1.5, 4.5, 5.5]),
             "close": np.array([1.2, 2.2, 5.2, 6.2])}
        run = bots.bridged(h, 0)
        self.assertEqual(list(run["bars"]["ts"] // 3600), [0, 1, 2, 3, 4, 5])
        self.assertEqual(list(run["bars"]["close"]), [1.2, 2.2, 2.2, 2.2, 5.2, 6.2])
        self.assertEqual(list(run["bars"]["high"][2:4]), [2.2, 2.2])
        self.assertEqual(run["bridged_bars"], 2)
        self.assertIsNone(run["stopped_at_gap"])
        self.assertEqual(bots.bridged(h, 0, max_bars=3)["bars"]["ts"].size, 3)

    def test_history_splices_minutes_before_the_hourly_file(self) -> None:
        start = 1_700_000_000 // 3600 * 3600
        minutes = SyntheticLoader(n_bars=60 * 48, seed=2, start_ts=start).load("SOL", None, None, "1m")
        minutes.to_csv(self.data / "SOL_1m.csv", index=False)
        write_hourly(self.data, "SOL", n=24, start_ts=start + 24 * 3600)
        h = bots.hourly("SOL", self.settings)
        self.assertEqual(h["source"], "1m->1h, then 1h")
        self.assertEqual(int(h["ts"][0]), start)
        self.assertEqual(h["ts"].size, 48)
        self.assertTrue(np.all(np.diff(h["ts"]) == 3600))

    def test_several_coins_in_one_backtest(self) -> None:
        write_hourly(self.data, "SOL", n=24 * 40, seed=1)
        write_hourly(self.data, "ETH", n=24 * 40, seed=2)
        r = bots.backtest_many("grid", ["SOL", "ETH", "NOPE"], self.settings, days=20)
        self.assertEqual([row["coin"] for row in r["summary"]], ["SOL", "ETH"])
        self.assertIn("NOPE", r["errors"])
        self.assertEqual(r["ran"], 2)
        self.assertEqual(len(bots.latest_results("grid", 10)), 2)
        every = bots.backtest_many("dca", "all", self.settings, days=10)
        self.assertEqual(sorted(every["coins"]), ["ETH", "SOL"])


    def test_triangle_backtest_prefers_recorded_quotes(self) -> None:
        t0 = 1_794_000_000.0
        rows = [(t0 + k, tri_quotes(t0 + k, 0.05 * (1.01 if 30 <= k < 40 else 1.0))) for k in range(120)]
        write_snapshots(pricefeed.prices_dir(), rows)
        with mock.patch.object(bots, "_triangle_products", return_value=["ETH-USD", "BTC-USD", "ETH-BTC", "SOL-USD"]):
            r = bots.backtest("triangle", "ALL", self.settings, start=t0)
        self.assertEqual(r["data_source"], "recorded")
        self.assertEqual(r["set"]["triangles"], ["USD-ETH-BTC"])
        res = r["results"]
        self.assertGreater(res["executed"], 0)
        self.assertGreater(res["pnl_usd"], 0)  # the dislocation lasted ten seconds, longer than the 1 s latency

    def test_candle_proxy_marks_legs_that_never_traded(self) -> None:
        import pandas as pd

        from backtester.core.fetch import FetchError

        def fake_fetch(product, start, end, interval, verbose=False):
            if product == "ETH-BTC":
                raise FetchError("no candles returned for ETH-BTC")
            base = {"ETH-USD": 3000.0, "BTC-USD": 60000.0}[product]
            stamps = list(range(1_794_000_000, 1_794_000_000 + 600, 60))
            return pd.DataFrame({"timestamp": stamps, "open": base, "high": base, "low": base, "close": base,
                                 "volume": 1.0})

        snaps, missing = bots._proxy_snapshots(["BTC-USD", "ETH-BTC", "ETH-USD"], 1_794_000_000, 1_794_000_600,
                                               fetch=fake_fetch)
        self.assertEqual(missing, ["ETH-BTC"])
        self.assertEqual(len(snaps), 10)
        self.assertNotIn("ETH-BTC", snaps[0][1])
        # Cached: a second call does not fetch.
        snaps2, _ = bots._proxy_snapshots(["BTC-USD", "ETH-USD"], 1_794_000_000, 1_794_000_600, fetch=None)
        self.assertEqual(len(snaps2), 10)


class Forward(Isolated):
    def test_cursor_reads_only_new_complete_members(self) -> None:
        prices = pricefeed.prices_dir()
        t0 = 1_794_000_000.0
        write_snapshots(prices, [(t0 + k, tri_quotes(t0 + k)) for k in range(5)])
        cur = bots.SnapshotCursor(t0)
        self.assertEqual(len(cur.read_new()), 5)
        self.assertEqual(cur.read_new(), [])
        path = pricefeed.day_path(t0, prices)
        blob = gzip.compress((json.dumps({"t": t0 + 9, "q": {}}) + "\n").encode())
        with path.open("ab") as fh:
            fh.write(blob[:10])  # the recorder is mid-write
        self.assertEqual(cur.read_new(), [])
        with path.open("ab") as fh:
            fh.write(blob[10:])
        self.assertEqual([t for t, _ in cur.read_new()], [t0 + 9])

    def test_cursor_is_exact_across_many_members_and_chunk_boundaries(self) -> None:
        from backtester.core.trianglesim import read_snapshot_files

        prices = pricefeed.prices_dir()
        t0 = 1_794_000_000.0
        rows = [(t0 + k, tri_quotes(t0 + k, 0.05 + k * 1e-7)) for k in range(3000)]
        for i in range(0, len(rows), 10):  # one gzip member per ten snapshots, as the recorder flushes
            write_snapshots(prices, rows[i:i + 10])
        path = pricefeed.day_path(t0, prices)
        self.assertGreater(path.stat().st_size, 4 * bots.SnapshotCursor.CHUNK)
        cur = bots.SnapshotCursor(t0)
        got = cur.read_new()
        self.assertEqual(got, read_snapshot_files([path]))
        self.assertEqual(len(got), 3000)
        self.assertEqual(cur.offsets[path.name], path.stat().st_size)

    def test_minute_bars_bridge_short_gaps_and_stop_at_long_ones(self) -> None:
        mb = bots.MinuteBars("SOL-USD")
        t0 = 1_794_000_000 // 60 * 60
        for minute in (0, 1, 3, 4, 10):  # minute 2 missing (bridged), 5..9 missing (gap)
            for sec in (0, 30):
                mid = 100.0 + minute
                mb.feed(t0 + minute * 60 + sec, {"SOL-USD": [mid - 0.01, mid + 0.01, mid, 1, 1, 0]})
        arrays, gap, bridged = mb.arrays(before=t0 + 11 * 60)
        self.assertEqual(list((arrays["ts"] - t0) // 60), [0, 1, 2, 3, 4])
        self.assertEqual(bridged, 1)
        self.assertEqual(arrays["close"][2], arrays["close"][1])  # the bridged minute is flat
        self.assertEqual(gap, t0 + 4 * 60)
        incomplete, _, _ = mb.arrays(before=t0 + 30)
        self.assertEqual(incomplete["ts"].size, 0)  # the forming minute is never used

    def test_forward_test_replays_the_recording_and_freezes_on_stop(self) -> None:
        t0 = 1_794_000_000 // 60 * 60
        rng = np.random.default_rng(5)
        rows, price = [], 100.0
        for k in range(30 * 60):
            price *= float(np.exp(rng.normal(0, 0.0008)))
            q = tri_quotes(t0 + k)
            q["SOL-USD"] = [price - 0.01, price + 0.01, price, 10, 10, t0 + k]
            rows.append((float(t0 + k), q))
        write_snapshots(pricefeed.prices_dir(), rows[:600])
        products = ["ETH-USD", "BTC-USD", "ETH-BTC", "SOL-USD"]
        with mock.patch.object(bots, "_triangle_products", return_value=products):
            for bot in ("grid", "dca", "triangle"):
                bots.forward_start(bot, "SOL", self.settings, ensure_recorder=False, now=float(t0))
            first = bots.forward_status("dca", self.settings, now=float(t0 + 600))
            self.assertEqual(first["snapshots"], 600)
            self.assertEqual(first["bars"], 10)
            write_snapshots(pricefeed.prices_dir(), rows[600:])
            later = bots.forward_status("dca", self.settings, now=float(t0 + 1800))
            self.assertEqual(later["snapshots"], 1800)
            self.assertEqual(later["bars"], 30)
            # Incremental equals a fresh replay of the same recording.
            bots.runtime().sessions.clear()
            fresh = bots.forward_status("dca", self.settings, now=float(t0 + 1800))
            self.assertEqual(fresh["results"], later["results"])
            grid = bots.forward_status("grid", self.settings, now=float(t0 + 1800))
            self.assertIn("lower", grid["set"])
            tri = bots.forward_status("triangle", self.settings, now=float(t0 + 1800))
            self.assertEqual(tri["results"]["snapshots"], 1800)
            bots.forward_stop("dca", now=float(t0 + 900))
            stopped = bots.forward_status("dca", self.settings, now=float(t0 + 1800))
            self.assertFalse(stopped["running"])
            self.assertEqual(stopped["bars"], 15)

    def test_forward_needs_a_streamed_usd_market(self) -> None:
        with mock.patch.object(bots, "_triangle_products", return_value=["ETH-USD"]):
            with self.assertRaisesRegex(bots.BotError, "SOL-USD"):
                bots.forward_start("grid", "SOL", self.settings, ensure_recorder=False)
        self.assertFalse(bots.forward_status("grid", self.settings)["running"])
        self.assertFalse(bots.forward_stop("grid")["stopped"])


class Optimize(Isolated):
    def test_sign_test_and_ranks(self) -> None:
        self.assertAlmostEqual(bots.sign_test_p(5, 0), 1 / 32)
        self.assertAlmostEqual(bots.sign_test_p(0, 0), 1.0)
        self.assertAlmostEqual(bots.sign_test_p(1, 1), 0.75)
        self.assertEqual(bots._ranks([3.0, 1.0, 3.0, 0.0]), [1.5, 3.0, 1.5, 4.0])

    def test_candidates_start_with_the_current_config_and_all_validate(self) -> None:
        for bot in bots.BOTS:
            cands = bots.candidates(bot, bots.get_config(bot))
            self.assertEqual(cands[0], bots.get_config(bot))
            self.assertEqual(len({json.dumps(c, sort_keys=True) for c in cands}), len(cands))

    def _fake_run_bars(self, better: dict):
        def run(bot, cfg, seg, interval, costs):
            noise = float(np.sin(seg["ts"][0] / 7919.0)) * 0.01
            edge = 0.02 if all(cfg.get(k) == v for k, v in better.items()) else 0.0
            return {"results": {"total_return": noise + edge}, "set": {}, "equity": []}
        return run

    def test_a_reliable_out_of_sample_winner_is_adopted(self) -> None:
        for coin, seed in (("AAA", 1), ("BBB", 2), ("CCC", 3)):
            write_hourly(self.data, coin, n=24 * 200, seed=seed)
        with mock.patch.object(bots, "run_bars", self._fake_run_bars({"range_pct": 5.0, "rungs": 9})):
            r = bots.optimize("grid", self.settings, windows=8, window_days=20)
        v = r["verdict"]
        self.assertTrue(v["reliable"], v)
        self.assertTrue(v["adopted"])
        self.assertEqual(v["wins"], 12)
        self.assertEqual(bots.get_config("grid")["range_pct"], 5.0)
        self.assertEqual(bots.latest_optimize("grid")["verdict"]["adopted"], True)
        self.assertEqual(bots.runtime().progress["grid"]["fraction"], 1.0)

    def test_noise_is_not_adopted(self) -> None:
        for coin, seed in (("AAA", 1), ("BBB", 2), ("CCC", 3)):
            write_hourly(self.data, coin, n=24 * 200, seed=seed)

        def noisy(bot, cfg, seg, interval, costs):
            # crc32, not hash(): str hashing is salted per process, which made this test flaky.
            key = zlib.crc32(f"{json.dumps(cfg, sort_keys=True)}|{int(seg['ts'][0])}".encode()) % 1000
            return {"results": {"total_return": key / 1e5}, "set": {}, "equity": []}

        with mock.patch.object(bots, "run_bars", noisy):
            r = bots.optimize("dca", self.settings, windows=8, window_days=20)
        self.assertFalse(r["verdict"]["adopted"])
        self.assertEqual(bots.get_config("dca"), bots.DEFAULTS["dca"])

    def test_triangle_needs_recorded_quotes(self) -> None:
        r = bots.optimize("triangle", self.settings)
        self.assertFalse(r["verdict"]["adopted"])
        self.assertIn("recorded", r["skipped"])

    def test_real_simulators_run_end_to_end(self) -> None:
        write_hourly(self.data, "AAA", n=24 * 130, seed=9)
        r = bots.optimize("dca", self.settings, coins=["AAA"], windows=4, window_days=30, adopt=False)
        self.assertEqual(r["train_cells"], 2)
        self.assertEqual(r["test_cells"], 2)
        self.assertFalse(r["verdict"]["reliable"])  # two test cells can never pass the gate


class Overview(Isolated):
    def test_overview_lists_every_bot(self) -> None:
        write_hourly(self.data, "SOL", n=48)
        o = bots.overview(self.settings)
        self.assertEqual([b["bot"] for b in o["bots"]], list(bots.BOTS))
        self.assertEqual(o["coins"], ["SOL"])

    def test_the_module_never_touches_key_files_or_order_paths(self) -> None:
        src = Path(bots.__file__).read_text()
        for needle in ("wallet.private", "solana.private", ".ssh", "load_signer", "place_order", "sign("):
            self.assertNotIn(needle, src)


class OptimizeRuns(Isolated):
    def test_each_run_tests_more_configurations_and_skips_tried_ones(self) -> None:
        for bot in ("grid", "dca", "triangle"):
            cur = bots.get_config(bot)
            tried: list[str] = []
            sizes = []
            for run in (1, 2, 3, 4):
                cands = bots.candidates(bot, cur, run, tried)
                self.assertEqual(cands[0], cur)
                new = [bots._cfg_key(c) for c in cands[1:]]
                if run > 1:
                    self.assertFalse(set(new) & set(tried), f"{bot} run {run} repeated a tried config")
                tried += new
                sizes.append(len(cands))
            with self.subTest(bot=bot):
                self.assertEqual(sizes, sorted(sizes))
                self.assertGreater(sizes[-1], sizes[0])
        # Reproducible: the same run draws the same candidates.
        cur = bots.get_config("dca")
        self.assertEqual(bots.candidates("dca", cur, 3, []), bots.candidates("dca", cur, 3, []))

    def test_later_runs_reach_further_from_the_current_settings(self) -> None:
        cur = bots.get_config("dca")

        def reach(run: int) -> float:
            cands = bots.candidates("dca", cur, run, [])
            return max(abs(c["take_profit_pct"] - cur["take_profit_pct"]) for c in cands)

        self.assertGreater(reach(6), reach(2))

    def test_report_numbers_runs_lists_coins_and_names_the_saved_changes(self) -> None:
        for coin, seed in (("AAA", 1), ("BBB", 2), ("CCC", 3)):
            write_hourly(self.data, coin, n=24 * 200, seed=seed)

        def run_bars(bot, cfg, seg, interval, costs):
            edge = 0.02 if cfg.get("range_pct") == 5.0 and cfg.get("rungs") == 9 else 0.0
            return {"results": {"total_return": float(np.sin(seg["ts"][0] / 7919.0)) * 0.01 + edge}}

        with mock.patch.object(bots, "run_bars", run_bars):
            first = bots.optimize("grid", self.settings, windows=8, window_days=20)
            self.assertEqual(first["run"], 1)
            self.assertTrue(first["verdict"]["saved"])
            self.assertEqual({c["setting"]: (c["before"], c["after"]) for c in first["verdict"]["changes"]},
                             {"range_pct": (15.0, 5.0), "rungs": (7, 9)})
            self.assertEqual(first["coins_used"], ["AAA", "BBB", "CCC"])
            per = {row["coin"]: row for row in first["per_coin"]}
            self.assertEqual(per["AAA"]["test_windows"], 4)
            self.assertEqual(per["AAA"]["pick_wins"], 4)
            second = bots.optimize("grid", self.settings, windows=8, window_days=20)
        self.assertEqual(second["run"], 2)
        self.assertGreater(second["candidates"], first["candidates"])
        self.assertFalse(second["verdict"]["saved"])  # the winner is now the current settings
        self.assertEqual(second["verdict"]["changes"], [])
        hist = bots.optimize_history("grid")
        self.assertEqual(hist["runs"], 2)
        self.assertEqual([e["adopted"] for e in hist["log"]], [True, False])
        progress = bots.runtime().progress["grid"]
        self.assertTrue(progress["done"])
        self.assertEqual(progress["run"], 2)


class BotsTab(unittest.IsolatedAsyncioTestCase):
    """The tab itself: every action goes through the registry and renders its result."""

    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.data = root / "data"
        self.data.mkdir()
        patcher = mock.patch.object(config_mod, "CONFIG_DIR", root / "config")
        patcher.start()
        self.addCleanup(patcher.stop)
        write_hourly(self.data, "SOL")
        bots._HOURLY_CACHE.clear()

    async def test_one_row_of_fields_multi_coin_backtest_and_the_optimize_window(self) -> None:
        from textual.widgets import Button, DataTable, Input, Select, Static, TabbedContent

        from soltui import commands
        from soltui.bots_screens import CoinPickerScreen, OptimizeScreen
        from soltui.tui import SolTuiApp

        write_hourly(self.data, "ETH", seed=7)
        app = SolTuiApp(Settings(data_dir=str(self.data), poll_interval_seconds=60))
        async with app.run_test(size=(170, 50)) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            top = app.query_one("#bots-top")
            for wid in ("#bots-bot", "#bots-coins", "#bots-start", "#bots-days", "#bots-config", "#bots-apply"):
                self.assertIs(app.query_one(wid).parent, top, f"{wid} is not on the top row")
            self.assertEqual(len({app.query_one(w).region.y for w in ("#bots-bot", "#bots-start", "#bots-config")}), 1)
            self.assertFalse(app.query("#bots-rec-stop"), "the recorder has no Stop button")
            self.assertEqual(str(app.query_one("#bots-coins", Button).label), "SOL")

            app.query_one("#bots-coins", Button).press()
            await pilot.pause()
            self.assertIsInstance(app.screen, CoinPickerScreen)
            app.screen.query_one("#coins-all", Button).press()
            await pilot.pause()
            app.screen.query_one("#coins-ok", Button).press()
            await pilot.pause()
            self.assertEqual(str(app.query_one("#bots-coins", Button).label), "all 2")

            app.query_one("#bots-days", Input).value = "20"
            app.query_one("#bots-backtest", Button).press()
            await pilot.pause(0.2)
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(app.query_one("#bots-bt-coins", DataTable).row_count, 2)
            self.assertIn("2 coin(s)", str(app.query_one("#bots-status", Static).render()))
            self.assertGreater(app.query_one("#bots-set", DataTable).row_count, 5)

            app.query_one("#bots-bot", Select).value = "dca"
            await pilot.pause()
            app.query_one("#bots-config", Input).value = "take_profit_pct=3.5"
            app.query_one("#bots-apply", Button).press()
            await pilot.pause(0.2)
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(bots.get_config("dca")["take_profit_pct"], 3.5)

            report = {"bot": "dca", "run": 2, "seconds": 1.0, "universe": "2 coins", "candidates": 49,
                      "train_cells": 6, "test_cells": 6, "skipped": {}, "coins_used": ["ETH", "SOL"],
                      "per_coin": [{"coin": "ETH", "data_source": "1h", "train_windows": 3, "test_windows": 3,
                                    "current_test_median": 0.01, "pick_test_median": 0.02, "pick_wins": 3,
                                    "pick_losses": 0}],
                      "verdict": {"saved": True, "adopted": True, "reason": "won 12 of 12",
                                  "changes": [{"setting": "take_profit_pct", "before": 3.5, "after": 4.0}],
                                  "saved_to": "x"},
                      "table": []}
            real = commands.COMMANDS["bots.optimize"]
            stub = commands.Command("bots.optimize", "stub", lambda ctx, p: report, real.params, False, True, False)
            with mock.patch.dict(commands.COMMANDS, {"bots.optimize": stub}):
                app.query_one("#bots-optimize", Button).press()
                await pilot.pause(0.2)
                await app.workers.wait_for_complete()
                await pilot.pause()
            self.assertIsInstance(app.screen, OptimizeScreen)
            box = str(app.screen.query_one("#opt-result", Static).render())
            self.assertIn("SAVED", box)
            self.assertIn("take_profit_pct: 3.5 -> 4.0", box)
            self.assertIn("ETH, SOL", box)
            self.assertEqual(app.screen.query_one("#opt-coins", DataTable).row_count, 1)
            app.screen.query_one("#opt-close", Button).press()
            await pilot.pause()
            self.assertNotIsInstance(app.screen, OptimizeScreen)
            self.assertIn("SAVED", str(app.query_one("#bots-opt-verdict", Static).render()))


if __name__ == "__main__":
    unittest.main()
