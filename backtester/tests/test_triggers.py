"""The trigger miner and trigger_trade: causality, statistics, gates and timing."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import build
from backtester.core.trigger_conditions import BASE_CONDITIONS, compute_conditions
from backtester.core.types import BarWindow, Mode

REPO = Path(__file__).resolve().parent.parent.parent
DAY = 86400
T0 = 1_600_000_000 - (1_600_000_000 % DAY)


def _load_triggers():
    name = "_triggers_for_tests"
    spec = importlib.util.spec_from_file_location(name, REPO / "research" / "triggers.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(name, None)
    return mod


T = _load_triggers()


def walk(n=900, seed=1, spikes=None, jump=0.0):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 0.02, n)
    vol = rng.uniform(900, 1100, n)
    for s in spikes or []:
        vol[s] = 20_000.0
        if s + 1 < n:
            r[s + 1] += jump
    close = 100 * np.exp(np.cumsum(r))
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * 1.004
    low = np.minimum(open_, close) * 0.996
    return {"ts": T0 + np.arange(n, dtype="int64") * DAY, "open": open_, "high": high, "low": low,
            "close": close, "volume": vol}


class TestConditionsAreCausal(unittest.TestCase):
    def test_changing_the_future_never_changes_a_past_condition(self) -> None:
        """The one-bar-leak test for every condition in the library."""
        a = walk(500)
        base = compute_conditions(a["open"], a["high"], a["low"], a["close"], a["volume"])
        cut = 300
        b = {k: v.copy() for k, v in a.items()}
        for k in ("open", "high", "low", "close", "volume"):
            b[k][cut + 1:] *= 5.0
        poisoned = compute_conditions(b["open"], b["high"], b["low"], b["close"], b["volume"])
        for name in BASE_CONDITIONS:
            if name in base:
                with self.subTest(name):
                    np.testing.assert_array_equal(base[name][: cut + 1], poisoned[name][: cut + 1])

    def test_strategy_window_agrees_with_full_history(self) -> None:
        a = walk(900, spikes=list(range(150, 880, 40)))
        names = "vol_10x&z_lt_m2"
        full = compute_conditions(a["open"], a["high"], a["low"], a["close"], a["volume"])
        strat = build("trigger_trade", conditions="macd_hist_pos&rsi_gt70", horizon=1)
        fires_full = full["macd_hist_pos"] & full["rsi_gt70"]
        mismatches = 0
        for t in range(700, 899):
            w = BarWindow(a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], t)
            mismatches += int(strat._fires(w) != bool(fires_full[t]))
        self.assertEqual(mismatches, 0)


class TestStatistics(unittest.TestCase):
    def test_binomial_tail_matches_known_values(self) -> None:
        self.assertAlmostEqual(T.binom_sf(8, 10, 0.5), 56 / 1024, places=9)
        self.assertAlmostEqual(T.binom_sf(0, 10, 0.5), 1.0)
        self.assertAlmostEqual(T.binom_sf(10, 10, 0.5), 1 / 1024, places=9)

    def test_wilson_interval_is_inside_the_unit_interval_and_contains_the_rate(self) -> None:
        lo, hi = T.wilson(36, 40)
        self.assertTrue(0 < lo < 36 / 40 < hi < 1)
        self.assertAlmostEqual(lo, 0.7695, places=3)  # hand-computed: centre 0.8650, half-width 0.0955

    def test_benjamini_hochberg_step_up(self) -> None:
        p = np.array([0.001, 0.008, 0.039, 0.041, 0.6])
        self.assertEqual(T.bh_reject(p, 0.05).tolist(), [True, True, False, False, False])
        self.assertEqual(T.bh_reject(np.array([0.2, 0.5]), 0.05).tolist(), [False, False])

    def test_dedup_counts_overlapping_windows_once(self) -> None:
        self.assertEqual(T.dedup(np.array([1, 2, 3, 6, 7, 20]), 5).tolist(), [1, 6, 20])


class TestForwardOutcomes(unittest.TestCase):
    def test_entry_is_next_open_and_exit_is_close_h_later(self) -> None:
        a = walk(60)
        fw = T.forward_outcomes(a["ts"], a["open"], a["high"], a["low"], a["close"], DAY)
        t, h = 10, 3
        self.assertAlmostEqual(fw.ret[h][t], a["close"][t + h] / a["open"][t + 1] - 1)
        self.assertTrue(np.isnan(fw.ret[h][-1]))

    def test_a_time_gap_inside_the_window_invalidates_the_event(self) -> None:
        a = walk(60)
        ts = a["ts"].copy(); ts[30:] += 3 * DAY
        fw = T.forward_outcomes(ts, a["open"], a["high"], a["low"], a["close"], DAY)
        self.assertTrue(np.isnan(fw.ret[3][28]))
        self.assertFalse(np.isnan(fw.ret[3][10]))


class TestMiningGates(unittest.TestCase):
    def _mine_dir(self, arrays, name="TEST"):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        pd.DataFrame({"timestamp": arrays["ts"], "open": arrays["open"], "high": arrays["high"],
                      "low": arrays["low"], "close": arrays["close"], "volume": arrays["volume"]}
                     ).to_csv(Path(d.name) / f"{name}_1d.csv", index=False)
        return Path(d.name)

    def test_pure_noise_produces_no_reliable_trigger(self) -> None:
        df, meta, _ = T.mine("TEST", "1d", data_dir=self._mine_dir(walk(1500, seed=5)))
        self.assertEqual(meta["reliable"], 0)
        self.assertGreater(meta["hypotheses_tested"], 0)

    def test_a_planted_edge_survives_discovery_but_cannot_skip_replication(self) -> None:
        spikes = list(range(100, 1480, 17))
        a = walk(1500, seed=9, spikes=spikes, jump=0.04)
        df, meta, _ = T.mine("TEST", "1d", data_dir=self._mine_dir(a))
        self.assertGreater(meta["bh_discovery_survivors"], 0)
        top = df[df["is_p"].notna()].sort_values("is_p").iloc[0]
        self.assertIn("vol_", top["conditions"])
        self.assertEqual(top["direction"], "long")
        # no other coins are present, so replication is untestable and nothing is "reliable"
        self.assertEqual(meta["reliable"], 0)
        self.assertIn("replicates", top["failed_gates"])

    def test_discovery_and_validation_do_not_overlap(self) -> None:
        a = walk(300)
        disc, val = T.period_masks(300, 180)
        self.assertFalse((disc & val).any())
        self.assertLess(np.nonzero(disc)[0].max() + T.H_MAX, 180)
        self.assertGreaterEqual(np.nonzero(val)[0].min(), 180 + T.H_MAX)


class TestTriggerTradeTiming(unittest.TestCase):
    def test_enters_next_open_and_exits_after_the_horizon(self) -> None:
        a = walk(400, seed=3)
        strat = build("trigger_trade", conditions="consec_dn3", direction=1, horizon=2)
        cfg = EngineConfig(mode=Mode.PERP, leverage=1.0, interval="1d", allow_short=True)
        res = run_backtest(strat, a, cfg)
        opens = [t for t in res.trades if t.reason == "open"]
        self.assertGreater(len(opens), 0)
        full = compute_conditions(a["open"], a["high"], a["low"], a["close"], a["volume"])
        first_fire = int(np.nonzero(full["consec_dn3"])[0][np.nonzero(full["consec_dn3"])[0] >= 120][0])
        self.assertEqual(opens[0].bar_index, first_fire + 1)
        self.assertAlmostEqual(opens[0].price, a["open"][first_fire + 1])
        closes = [t for t in res.trades if t.side == "close"]
        self.assertEqual(closes[0].bar_index, first_fire + 1 + 2)  # decided at close t+2, filled at open t+3

    def test_funding_conditions_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            build("trigger_trade", conditions="funding_hi&rsi_lt30")

    def test_stop_exits_early(self) -> None:
        a = walk(400, seed=3)
        free = run_backtest(build("trigger_trade", conditions="consec_dn3", horizon=10, stop=0.0), a,
                            EngineConfig(mode=Mode.PERP, leverage=1.0, interval="1d", allow_short=True))
        tight = run_backtest(build("trigger_trade", conditions="consec_dn3", horizon=10, stop=0.001), a,
                             EngineConfig(mode=Mode.PERP, leverage=1.0, interval="1d", allow_short=True))
        held = lambda r: sum(1 for x in r.exposure if abs(x) > 0)
        self.assertLess(held(tight), held(free))


if __name__ == "__main__":
    unittest.main()
