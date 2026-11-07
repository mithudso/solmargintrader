"""Compound five-minute scorecard: no look-ahead, honest aggregation, honest statistics."""

from __future__ import annotations

import math
import unittest
from unittest import mock

import numpy as np

from backtester.core import scorecard as sc


def synthetic(n: int = 900, seed: int = 7, start: int = 1_780_000_200) -> sc.Bars:
    """A random walk with regime changes and volume bursts, on a gap-free 5m grid."""
    rng = np.random.default_rng(seed)
    drift = np.repeat(rng.normal(0, 4e-4, n // 100 + 1), 100)[:n]
    r = drift + rng.normal(0, 1.5e-3, n)
    close = 100 * np.exp(np.cumsum(r))
    open_ = np.concatenate(([close[0]], close[:-1]))
    spread = np.abs(rng.normal(0, 1e-3, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.lognormal(3, 0.6, n) * (1 + 5 * (rng.random(n) < 0.02))
    ts = start + 300 * np.arange(n)
    return sc.Bars(ts, open_, high, low, close, volume)


def aux_for(b: sc.Bars, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    btc = 50_000 * np.exp(np.cumsum(rng.normal(0, 1e-3, len(b))))
    hours = np.arange(int(b.ts[0]) - 3600, int(b.ts[-1]) + 3600, 3600)
    return {
        "btc_close": btc,
        "funding": {"ts": hours, "rate": rng.normal(1.25e-5, 2e-5, hours.size)},
        "events": [{"ts": int(b.ts[400]) + 300, "title": "CPI"}],
    }


def slice_aux(aux: dict, end: int) -> dict:
    out = dict(aux)
    out["btc_close"] = aux["btc_close"][:end]
    return out


def same(a: float, b: float) -> bool:
    if isinstance(a, (bool, np.bool_)) or isinstance(b, (bool, np.bool_)):
        return bool(a) == bool(b)
    if math.isnan(a) and math.isnan(b):
        return True
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


class PrefixInvarianceTests(unittest.TestCase):
    """The score at bar t must not change when bars after t are removed.

    This is the one-bar-leak test CLAUDE.md requires for every signal: any component that
    reads bar t+1 (a negative shift, a centred window, a backward fill) gives a different value
    at t once the future is cut off.
    """

    CHECKPOINTS = (60, 150, 299, 300, 451, 600, 777, 898)

    def setUp(self) -> None:
        self.bars = synthetic()
        self.aux = aux_for(self.bars)
        self.aux["round_trip_bps"] = 16.0
        self.aux["leverage"] = 5.0
        self.aux["blocked_hours"] = (3, 4)

    def assert_prefix_invariant(self, fn, params, label: str) -> None:
        full = np.asarray(fn(self.bars, params, self.aux))
        for t in self.CHECKPOINTS:
            part = np.asarray(fn(self.bars.slice(t + 1), params, slice_aux(self.aux, t + 1)))
            self.assertTrue(same(float(part[-1]), float(full[t])),
                            f"{label}: bar {t} is {part[-1]} on the prefix but {full[t]} on the full series")

    def test_every_historical_component_is_prefix_invariant(self) -> None:
        for comp in sc.COMPONENTS:
            if comp.forward_only:
                continue
            with self.subTest(component=comp.id):
                params = comp.defaults()
                if comp.id == "gate_session":
                    params["weekend"] = 1
                self.assert_prefix_invariant(comp.fn, params, comp.id)

    def test_non_default_parameters_stay_prefix_invariant(self) -> None:
        cases = {
            "vwap_side": {"mode": 1, "window": 30}, "vwap_reversion": {"mode": 1, "window": 30},
            "rsi": {"mode": 1}, "htf_trend": {"tf_minutes": 15}, "donchian": {"hold": 1},
            "squeeze": {"lookback": 100, "squeeze_pct": 40},
        }
        for cid, override in cases.items():
            with self.subTest(component=cid):
                params = {**sc.BY_ID[cid].defaults(), **override}
                self.assert_prefix_invariant(sc.BY_ID[cid].fn, params, cid)

    def test_the_checker_catches_a_one_bar_leak(self) -> None:
        def leaky(b, p, aux):
            nxt = np.full(len(b), np.nan)
            nxt[:-1] = b.close[1:]
            return np.sign(nxt - b.close)

        with self.assertRaises(AssertionError):
            self.assert_prefix_invariant(leaky, {}, "leaky")

    def test_composite_call_and_target_are_prefix_invariant(self) -> None:
        cfg = sc.default_config()
        cfg["components"]["ichimoku"]["enabled"] = True
        cfg["components"]["fib_pullback"]["enabled"] = True
        aux = {k: self.aux[k] for k in ("btc_close", "funding", "events")}
        full = sc.evaluate(self.bars, cfg, aux)
        full_target = sc.target_path(full)
        for t in self.CHECKPOINTS:
            part = sc.evaluate(self.bars.slice(t + 1), cfg, slice_aux(aux, t + 1))
            with self.subTest(bar=t):
                self.assertTrue(same(part.composite[-1], full.composite[t]))
                self.assertEqual(int(part.indication[-1]), int(full.indication[t]))
                self.assertEqual(str(part.regime[-1]), str(full.regime[t]))
                self.assertEqual(bool(part.blocked[-1]), bool(full.blocked[t]))
                self.assertEqual(sc.target_path(part)[-1], full_target[t])

    def test_live_only_components_score_only_the_last_bar(self) -> None:
        aux = {"live": {"premium": 0.0004, "book_imbalance": -0.2,
                        "oi_history": [(1, 100.0), (1000, 101.0), (2000, 103.0)]}}
        b = self.bars.slice(200)
        for cid in ("premium", "book_imbalance"):
            out = sc.BY_ID[cid].fn(b, sc.BY_ID[cid].defaults(), aux)
            self.assertTrue(np.all(np.isnan(out[:-1])))
            self.assertTrue(np.isfinite(out[-1]))
        self.assertTrue(np.all(np.isnan(sc.BY_ID["premium"].fn(b, sc.BY_ID["premium"].defaults(), {}))))

    def test_htf_uses_only_completed_higher_timeframe_bars(self) -> None:
        b = synthetic(200, start=1_780_000_200)
        series = sc._htf_close(b, 60)
        ends = b.ts + 300
        for i in range(len(b)):
            if np.isnan(series[i]):
                continue
            j = max(k for k in range(i + 1) if ends[k] % 3600 == 0)
            self.assertEqual(series[i], b.close[j])


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid_and_hash_is_stable(self) -> None:
        cfg = sc.normalise_config(None)
        self.assertEqual(sc.config_hash(cfg), sc.config_hash(sc.default_config()))
        for comp in sc.COMPONENTS:
            for spec in comp.params:
                self.assertLessEqual(spec.lo, spec.default, f"{comp.id}.{spec.name}")
                self.assertLessEqual(spec.default, spec.hi, f"{comp.id}.{spec.name}")

    def test_bad_values_are_refused_with_the_component_named(self) -> None:
        bad = [
            {"components": {"rsi": {"params": {"period": 0}}}},
            {"components": {"rsi": {"params": {"period": 7.5}}}},
            {"components": {"rsi": {"params": {"nope": 3}}}},
            {"components": {"rsi": {"weight": -1}}},
            {"aggregate": {"entry": 0.1, "exit": 0.2}},
            {"aggregate": {"bogus": 1}},
            {"execution": {"leverage": 0.5}},
            {"blocked_hours": [24]},
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(sc.ScorecardError):
                sc.normalise_config(raw)

    def test_unknown_component_in_an_old_file_is_ignored(self) -> None:
        cfg = sc.normalise_config({"components": {"retired_metric": {"enabled": True}}})
        self.assertNotIn("retired_metric", cfg["components"])

    def test_cross_parameter_rules_are_refused_when_saved(self) -> None:
        for cid, params in (("ema_cross", {"fast": 30, "slow": 20}), ("macd", {"fast": 26, "slow": 26}),
                            ("trend_lifecycle", {"fast": 40}), ("fib_pullback", {"zone_lo": 0.7}),
                            ("htf_trend", {"tf_minutes": 62})):
            with self.subTest(component=cid), self.assertRaises(sc.ScorecardError) as cm:
                sc.normalise_config({"components": {cid: {"params": params}}})
            self.assertIn(cid, str(cm.exception))

    def test_an_errored_score_lowers_coverage_and_an_errored_gate_blocks(self) -> None:
        b = synthetic(400)
        cfg = sc.default_config()
        for cid, entry in cfg["components"].items():
            entry["enabled"] = cid in ("ema_cross", "btc_lead")
        cfg["aggregate"]["min_coverage"] = 0.0
        ev = sc.evaluate(b, cfg, {"btc_close": np.ones(10)})  # misaligned -> btc_lead errors
        self.assertIn("btc_lead", ev.errors)
        self.assertAlmostEqual(float(np.nanmax(ev.coverage)), 1.0 / 1.5)
        broken = sc.Component("gate_broken", "broken", "gate", "gate", "gate", (),
                              lambda bars, p, aux: (_ for _ in ()).throw(sc.ScorecardError("boom")),
                              "", "", "")
        with mock.patch.object(sc, "COMPONENTS", sc.COMPONENTS + (broken,)), \
                mock.patch.dict(sc.BY_ID, {"gate_broken": broken}):
            cfg2 = sc.default_config()
            cfg2["components"]["gate_broken"] = {"enabled": True, "weight": 1.0, "params": {}}
            with mock.patch.object(sc, "normalise_config", lambda c: c):
                ev2 = sc.evaluate(b, cfg2)
        self.assertTrue(ev2.blocked.all())
        self.assertFalse(ev2.indication.any())
        self.assertIn("gate_broken", sc.explain(ev2)["blocked_by"])

    def test_standalone_turns_off_every_other_component_and_gate(self) -> None:
        solo = sc.standalone_config(sc.default_config(), "rsi")
        on = [c for c, e in solo["components"].items() if e["enabled"]]
        self.assertEqual(on, ["rsi"])
        with self.assertRaises(sc.ScorecardError):
            sc.standalone_config(sc.default_config(), "gate_cost")


def only(**enabled: float) -> dict:
    cfg = sc.default_config()
    for cid, entry in cfg["components"].items():
        entry["enabled"] = cid in enabled
        if cid in enabled:
            entry["weight"] = enabled[cid]
    cfg["aggregate"]["regime_weighting"] = 0
    cfg["aggregate"]["min_coverage"] = 0.0
    return cfg


class AggregationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bars = synthetic(600)

    def test_family_dedupe_lets_each_family_vote_once(self) -> None:
        cfg = only(rsi=1, stochastic=1, cci=1, ema_cross=1)
        on = sc.evaluate(self.bars, cfg)
        cfg["aggregate"]["dedupe_families"] = 0
        off = sc.evaluate(self.bars, cfg)
        i = 500
        osc = np.mean([on.scores[c][i] for c in ("rsi", "stochastic", "cci")])
        trend = on.scores["ema_cross"][i]
        self.assertAlmostEqual(on.composite[i], (osc + trend) / 2, places=9)
        self.assertAlmostEqual(off.composite[i], (3 * osc + trend) / 4, places=9)

    def test_regime_weighting_scales_styles(self) -> None:
        cfg = only(rsi=1, ema_cross=1)
        cfg["aggregate"]["regime_weighting"] = 1
        ev = sc.evaluate(self.bars, cfg)
        trend_bars = np.where(ev.regime == "trend")[0]
        self.assertGreater(trend_bars.size, 0)
        i = int(trend_bars[-1])
        rs, es = ev.scores["rsi"][i], ev.scores["ema_cross"][i]
        expect = (0.3 * rs + 1.5 * es) / (0.3 + 1.5)
        self.assertAlmostEqual(ev.composite[i], expect, places=9)

    def test_an_enabled_gate_forces_flat(self) -> None:
        cfg = only(ema_cross=1, gate_cost=1)
        cfg["execution"]["fee_bps"] = 100.0  # 200+ bps round trip: nothing clears it
        ev = sc.evaluate(self.bars, cfg)
        self.assertTrue(ev.blocked[100:].all())
        self.assertFalse(ev.indication.any())
        x = sc.explain(ev)
        self.assertEqual(x["call"], "FLAT")
        self.assertEqual(x["blocked_by"], ["gate_cost"])

    def test_liquidation_gate_tightens_with_leverage(self) -> None:
        g = sc.BY_ID["gate_liquidation"]
        low = g.fn(self.bars, g.defaults(), {"leverage": 2.0})
        high = g.fn(self.bars, g.defaults(), {"leverage": 250.0})
        self.assertGreaterEqual(high[50:].mean(), low[50:].mean())
        self.assertTrue(high[50:].all())

    def test_long_only_never_calls_down(self) -> None:
        cfg = only(ema_cross=1)
        cfg["aggregate"]["allow_short"] = 0
        self.assertGreaterEqual(int(sc.evaluate(self.bars, cfg).indication.min()), 0)

    def test_min_coverage_withholds_a_call_built_on_too_little(self) -> None:
        cfg = only(ema_cross=1, btc_lead=3)  # btc_lead has no aux: 25% coverage
        cfg["aggregate"]["min_coverage"] = 0.5
        ev = sc.evaluate(self.bars, cfg)
        self.assertTrue(np.isnan(ev.composite).all())

    def test_hysteresis_holds_through_weak_same_sign_bars(self) -> None:
        ev = sc.evaluate(self.bars, only(ema_cross=1))
        ev.composite[:] = np.array([0.3, 0.2, 0.12, 0.05, -0.3, -0.2] + [0.0] * (len(self.bars) - 6))
        ev.indication[:] = 0
        ev.indication[0], ev.indication[4] = 1, -1
        ev.blocked[:] = False
        path = sc.target_path(ev)
        self.assertEqual(list(path[:6]), [1.0, 1.0, 1.0, 0.0, -1.0, -1.0])

    def test_explain_reports_every_component_once(self) -> None:
        x = sc.explain(sc.evaluate(self.bars), catalogue=True)
        self.assertEqual([r["id"] for r in x["components"]], [c.id for c in sc.COMPONENTS])
        self.assertIn(x["call"], ("UP", "DOWN", "FLAT"))
        self.assertIn(x["trend_stage"], sc.LIFECYCLE_LABELS)
        self.assertIn(x["cycle_phase"], ("markup", "markdown", "accumulation", "distribution",
                                         "transition", "none"))
        self.assertEqual(x["decided_at"], x["bar_ts"] + 300)


class ForecastStatsTests(unittest.TestCase):
    def test_a_perfect_call_scores_one_and_the_oracle_ceiling_is_net_of_cost(self) -> None:
        b = synthetic(400)
        ev = sc.evaluate(b, only(ema_cross=1))
        nxt = np.sign(np.diff(b.close))
        ev.indication[:] = 0
        ev.indication[:-1] = nxt.astype("int8")
        s = sc.forecast_stats([ev])
        self.assertEqual(s["hit_rate"], 1.0)
        r = np.diff(np.log(b.close)) * 1e4
        self.assertAlmostEqual(s["oracle_net_bps"], round(float(np.abs(r).mean()) - 16.0, 3), places=3)
        self.assertAlmostEqual(s["gross_bps_per_call"], round(float(np.abs(r).mean()), 3), places=3)

    def test_the_time_split_partitions_bars(self) -> None:
        b = synthetic(400)
        ev = sc.evaluate(b, only(ema_cross=1))
        split = float(b.ts[250])
        a, z = sc.forecast_stats([ev], None, split), sc.forecast_stats([ev], split, None)
        self.assertEqual(a["bars"] + z["bars"], sc.forecast_stats([ev])["bars"])
        self.assertEqual(a["bars"], 250)

    def test_contiguous_segments_split_at_gaps(self) -> None:
        ts = np.array([0, 300, 600, 1500, 1800, 2400])
        self.assertEqual(sc.contiguous_segments(ts), [(0, 3), (3, 5), (5, 6)])
        self.assertEqual(sc.contiguous_segments(np.array([], dtype=int)), [])


if __name__ == "__main__":
    unittest.main()
