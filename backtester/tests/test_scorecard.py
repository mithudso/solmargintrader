"""Compound five-minute scorecard: no look-ahead, honest aggregation, honest statistics."""

from __future__ import annotations

import json
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

    def test_frontier_metrics_with_other_parameters_stay_prefix_invariant(self) -> None:
        cases = {"mom_skip": {"lookback": 24, "skip": 0}, "vr_regime": {"q": 3, "window": 60},
                 "ou_reversion": {"window": 20, "fit_window": 60, "max_half_life": 1000},
                 "consec_run": {"min_run": 2, "span": 1}, "pairs_spread": {"window": 60},
                 "keltner": {"span": 5, "mult": 0.5}}
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

    def test_frontier_metrics_hold_and_entry_quantile_are_prefix_invariant(self) -> None:
        # The 2026-11-07 frontier: six new metrics, a minimum hold and a trailing-quantile entry.
        cfg = sc.default_config()
        for cid in ("keltner", "mom_skip", "vr_regime", "ou_reversion", "consec_run", "pairs_spread"):
            cfg["components"][cid]["enabled"] = True
        cfg["aggregate"].update(hold=12, entry_quantile=0.9, adaptive_window=200)
        aux = {k: self.aux[k] for k in ("btc_close", "funding", "events")}
        full = sc.evaluate(self.bars, cfg, aux)
        full_target = sc.target_path(full)
        for t in self.CHECKPOINTS:
            part = sc.evaluate(self.bars.slice(t + 1), cfg, slice_aux(aux, t + 1))
            with self.subTest(bar=t):
                self.assertTrue(same(part.composite[-1], full.composite[t]))
                self.assertEqual(int(part.indication[-1]), int(full.indication[t]))
                self.assertEqual(sc.target_path(part)[-1], full_target[t])

    def test_adaptive_weights_are_prefix_invariant(self) -> None:
        for flip in (0, 1):
            cfg = sc.default_config()
            cfg["aggregate"].update(adaptive=1, adaptive_flip=flip, adaptive_window=200, adaptive_halflife=50,
                                    adaptive_prior=5)
            aux = {k: self.aux[k] for k in ("btc_close", "funding", "events")}
            full = sc.evaluate(self.bars, cfg, aux)
            for t in self.CHECKPOINTS:
                part = sc.evaluate(self.bars.slice(t + 1), cfg, slice_aux(aux, t + 1))
                with self.subTest(flip=flip, bar=t):
                    self.assertTrue(same(part.composite[-1], full.composite[t]))
                    for cid, learned in full.adaptive.items():
                        self.assertTrue(same(part.adaptive[cid]["multiplier"][-1], learned["multiplier"][t]), cid)

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
        self.assertEqual((solo["aggregate"]["adaptive"], solo["aggregate"]["tune"]), (0, 0))
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
    cfg["aggregate"]["adaptive"] = 0  # static weights; AdaptiveTests covers the learned ones
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

    def test_liquidation_gate_counts_the_venue_maintenance_margin(self) -> None:
        # At 5x a 5% maintenance margin leaves 15% of room, not 20%: a stop that fits inside half
        # of 20% but not half of 15% must be blocked only when the margin is known.
        g = sc.BY_ID["gate_liquidation"]
        p = dict(g.defaults(), max_fraction=0.5)
        stop = p["stop_atr"] * sc.atr(self.bars, p["atr"]) / self.bars.close
        lev = float(np.nanmedian(0.5 / stop[50:]) * 0.85)  # the stop sits between 0.075 and 0.1 x lev
        without = g.fn(self.bars, p, {"leverage": lev})
        with_margin = g.fn(self.bars, p, {"leverage": lev, "maintenance_fraction": 0.05 / 5.0 * lev})
        self.assertGreater(with_margin[50:].mean(), without[50:].mean())
        self.assertTrue((with_margin[50:] >= without[50:]).all())

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


class AdaptiveTests(unittest.TestCase):
    def test_a_call_is_counted_only_after_the_next_bar_closes(self) -> None:
        close = np.array([10.0, 11.0, 10.0, 12.0, 13.0])
        score = np.array([1.0, 1.0, 1.0, -1.0, 1.0])  # right, wrong, right, wrong, unresolved
        hits, calls = sc.adaptive_counts(score, close, 0.25, window=1000)
        self.assertEqual(list(np.round(calls, 6)), [0, 1, 2, 3, 4])
        self.assertEqual(list(np.round(hits, 6)), [0, 1, 1, 2, 2])

    def test_abstentions_and_flat_bars_are_not_counted(self) -> None:
        close = np.array([10.0, 10.0, 11.0, 12.0])
        score = np.array([1.0, 0.1, np.nan, 1.0])  # flat next bar, below entry, undefined
        hits, calls = sc.adaptive_counts(score, close, 0.25, window=1000)
        self.assertEqual(list(calls), [0.0, 0.0, 0.0, 0.0])

    def test_the_record_is_capped_at_the_window(self) -> None:
        close = 100 + np.cumsum(np.tile([1.0, -1.0], 50))   # every bar moves
        score = np.ones(100)                                 # calls every bar
        hits, calls = sc.adaptive_counts(score, close, 0.25, window=10)
        self.assertEqual(calls[5], 5)
        self.assertTrue(np.all(calls[10:] == 10), calls[10:15])  # never more than the window
        # A miss moves a capped record as much at bar 90 as at bar 15.
        self.assertTrue(np.all(np.abs(np.diff(hits[11:-1])) <= 1))

    def test_ledger_calls_count_until_they_leave_the_window(self) -> None:
        close = np.full(30, 100.0)                           # nothing new resolves in-window
        score = np.zeros(30)
        seed = [(-1, 1.0, 1.0), (-5, 0.0, 1.0), (-40, 1.0, 1.0)]  # the last is already too old
        hits, calls = sc.adaptive_counts(score, close, 0.25, window=10, seed=seed)
        self.assertEqual((hits[0], calls[0]), (1.0, 2.0))
        self.assertEqual(calls[5], 2.0)                      # the call at -5 resolved at -4: 10 bars run to 5
        self.assertEqual(calls[6], 1.0)                      # ... and it has left the window at 6
        self.assertEqual(calls[9], 1.0)
        self.assertEqual(calls[10], 0.0)                     # the call at -1 expires after 10 bars

    def test_halflife_fades_inside_the_window(self) -> None:
        close = np.array([10.0, 11.0] + [11.0] * 10)
        score = np.array([1.0] + [0.0] * 11)
        hits, calls = sc.adaptive_counts(score, close, 0.25, window=100, halflife=2)
        self.assertAlmostEqual(calls[1], 1.0)
        self.assertAlmostEqual(calls[3], 0.5)
        self.assertAlmostEqual(calls[5], 0.25)

    def test_multiplier_is_edge_over_a_coin_flip_shrunk_by_the_prior(self) -> None:
        m = sc.adaptive_multiplier(np.array([55.0, 47.0, 0.0, 550.0]), np.array([100.0, 100.0, 0.0, 1000.0]),
                                   prior=100, flip=False)
        self.assertAlmostEqual(m[0], 2 * (105 / 200) - 1)          # 55% on 100 calls -> shrunk to 52.5%
        self.assertEqual(m[1], 0.0)                                # worse than a coin flip: muted
        self.assertEqual(m[2], 0.0)                                # no evidence: no say
        self.assertAlmostEqual(m[3], 2 * (600 / 1100) - 1)
        flipped = sc.adaptive_multiplier(np.array([47.0]), np.array([100.0]), prior=100, flip=True)
        self.assertLess(flipped[0], 0)

    def test_a_reliably_wrong_metric_loses_its_vote(self) -> None:
        b = synthetic(600)
        r = np.sign(np.diff(b.close))
        cfg = only(rsi=1, ema_cross=1)
        cfg["aggregate"].update(adaptive=1, adaptive_prior=10, adaptive_window=10_000)
        ev = sc.evaluate(b, cfg)
        # Make ema_cross always wrong and rsi always right about the next bar.
        ev2_scores = {"rsi": np.append(r, 0.0), "ema_cross": np.append(-r, 0.0)}
        h_r, c_r = sc.adaptive_counts(ev2_scores["rsi"], b.close, 0.25, 10_000)
        h_e, c_e = sc.adaptive_counts(ev2_scores["ema_cross"], b.close, 0.25, 10_000)
        self.assertGreater(sc.adaptive_multiplier(h_r, c_r, 10, False)[-1], 0.9)
        self.assertEqual(sc.adaptive_multiplier(h_e, c_e, 10, False)[-1], 0.0)
        row = next(x for x in sc.explain(ev)["components"] if x["id"] == "rsi")
        self.assertIn("learned_hit", row)
        self.assertIn("adaptive_mult", row)

    def test_adaptive_off_reproduces_the_static_composite(self) -> None:
        b = synthetic(500)
        cfg = only(rsi=1, ema_cross=2)
        cfg["aggregate"]["adaptive"] = 0
        ev = sc.evaluate(b, cfg)
        self.assertEqual(ev.adaptive, {})
        i = 450
        expect = (ev.scores["rsi"][i] + 2 * ev.scores["ema_cross"][i]) / 3
        self.assertAlmostEqual(ev.composite[i], expect, places=9)


class TuningTests(unittest.TestCase):
    LOOSE = {"tune": 1, "tune_confidence": 0.55, "tune_min_calls": 10, "tune_cooldown": 20,
             "adaptive_prior": 2, "adaptive_window": 200}

    def test_neighbours_are_one_number_away_valid_and_distinct(self) -> None:
        comp = sc.BY_ID["ema_cross"]
        ns = sc.neighbours(comp, {"fast": 9, "slow": 10, "scale": 0.5, "atr": 14}, 0.25)
        for n in ns:
            self.assertLess(n["fast"], n["slow"])
            changed = [k for k in n if n[k] != {"fast": 9, "slow": 10, "scale": 0.5, "atr": 14}[k]]
            self.assertEqual(len(changed), 1)
        self.assertNotIn({"fast": 11, "slow": 10, "scale": 0.5, "atr": 14}, ns)
        self.assertFalse(any("mode" in n and n["mode"] != 0 for n in sc.neighbours(sc.BY_ID["rsi"],
                                                                                sc.BY_ID["rsi"].defaults(), 0.25)))

    def test_tuning_moves_and_stays_prefix_invariant(self) -> None:
        b = synthetic(900, seed=21)
        cfg = only(rsi=1, ema_cross=1, bollinger=1)
        cfg["aggregate"].update(self.LOOSE)
        full = sc.evaluate(b, cfg)
        self.assertTrue(full.tuned, "loose thresholds should produce at least one move")
        for t in (120, 333, 500, 777, 898):
            part = sc.evaluate(b.slice(t + 1), cfg)
            with self.subTest(bar=t):
                self.assertTrue(same(part.composite[-1], full.composite[t]))
                for cid in full.tuned:
                    self.assertTrue(same(part.scores[cid][-1], full.scores[cid][t]), cid)
                    before = [mv for mv in full.tuned[cid] if mv[0] <= t]
                    self.assertEqual(part.tuned.get(cid, []), before)

    def test_a_move_waits_for_the_cooldown(self) -> None:
        b = synthetic(900, seed=21)
        cfg = only(rsi=1, ema_cross=1, bollinger=1)
        cfg["aggregate"].update(self.LOOSE)
        for moves in sc.evaluate(b, cfg).tuned.values():
            gaps = [b2 - a2 for (a2, _), (b2, _) in zip(moves, moves[1:], strict=False)]
            self.assertTrue(all(g >= 20 for g in gaps), gaps)

    def test_the_default_bar_does_not_move_on_noise(self) -> None:
        cfg = only(rsi=1, ema_cross=1)
        cfg["aggregate"]["tune"] = 1
        self.assertEqual(sc.evaluate(synthetic(900), cfg).tuned, {})

    def test_posterior_and_comparison(self) -> None:
        mean, var = sc.beta_posterior(np.array([60.0]), np.array([100.0]), prior=100)
        self.assertAlmostEqual(mean[0], 110 / 200)
        m2, v2 = sc.beta_posterior(np.array([50.0]), np.array([100.0]), prior=100)
        p = sc.p_better_than(mean, var, m2, v2)[0]
        self.assertGreater(p, 0.5)
        self.assertLess(p, 0.99)
        self.assertAlmostEqual(float(sc._phi(np.array([1.96]))[0]), 0.975, places=3)

    def test_explain_reports_tuned_settings_and_posterior(self) -> None:
        b = synthetic(900, seed=21)
        cfg = only(rsi=1, ema_cross=1, bollinger=1)
        cfg["aggregate"].update(self.LOOSE)
        cfg["aggregate"]["adaptive"] = 1
        ev = sc.evaluate(b, cfg)
        rows = {r["id"]: r for r in sc.explain(ev)["components"]}
        moved = next(iter(ev.tuned))
        self.assertIn("tuned_params", rows[moved])
        self.assertIn("p_better_than_coinflip", rows["rsi"])


class NewMetricTests(unittest.TestCase):
    def test_zigzag_confirms_on_the_reversal_bar_and_never_moves_a_pivot(self) -> None:
        close = np.array([100, 101, 102, 101.5, 100.9, 100.2, 100.5, 101.3, 99.0])
        leg, pivot = sc.zigzag_state(close, 0.01)
        # Up leg confirmed at bar 1 (1% above the low 100); the high 102 is confirmed as a pivot only
        # when price is 1% below it (bar 4, 100.9 <= 100.98), not earlier.
        self.assertEqual(list(leg[:4]), [0, 1, 1, 1])
        self.assertEqual(leg[4], -1)
        self.assertEqual(pivot[4], 102.0)
        for t_ in range(len(close)):
            l2, p2 = sc.zigzag_state(close[: t_ + 1], 0.01)
            self.assertEqual(l2[-1], leg[t_])
            self.assertTrue(same(p2[-1], pivot[t_]))

    def test_volume_scores_only_unusual_bars_signed_by_the_candle(self) -> None:
        b = synthetic(200)
        b.volume[:] = 10.0
        b.volume[150] = 30.0
        b.close[150] = b.open[150] * 1.01
        b.high[150] = max(b.high[150], b.close[150])
        out = sc.BY_ID["volume"].fn(b, {"window": 48, "scale": 1.0}, {})
        self.assertEqual(out[150], 1.0)
        self.assertEqual(out[149], 0.0)

    def test_bop_is_minus_one_to_plus_one_and_tracks_who_won(self) -> None:
        b = synthetic(300)
        out = sc.BY_ID["bop"].fn(b, {"window": 1, "scale": 1.0}, {})
        rng = b.high - b.low
        expect = np.where(rng > 0, (b.close - b.open) / rng, 0.0)
        self.assertTrue(np.allclose(out, np.clip(expect, -1, 1)))

    def test_relations_flag_mirrors_and_cross_family_duplicates(self) -> None:
        b = synthetic(600)
        cfg = only(vwap_side=1, vwap_reversion=1, rsi=1, zscore=1, cci=1, bollinger=1)
        ev = sc.evaluate(b, cfg)
        rel = sc.relations(ev, window=600, min_points=100)
        self.assertIn(("vwap_side", "vwap_reversion"), {(r["a"], r["b"]) for r in rel["opposed"]})
        self.assertTrue(all(not r["same_family"] for r in rel["duplicates"]))
        self.assertIn("relations", sc.explain(ev))


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
        ex = sc.default_config()["execution"]
        rt = sc.round_trip_bps(ex["fee_bps"], ex["slippage_bps"])
        self.assertEqual(rt, 13.0)  # Hyperliquid base taker 4.5 bps + 2 bps slippage, per side
        self.assertAlmostEqual(s["oracle_net_bps"], round(float(np.abs(r).mean()) - rt, 3), places=3)
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


class FrontierControlTests(unittest.TestCase):
    """hold and entry_quantile: fewer, longer trades. The point is to pay fewer round trips."""

    def setUp(self) -> None:
        self.bars = synthetic()
        self.cfg = sc.standalone_config(sc.default_config(), "rsi")

    @staticmethod
    def trades(path: np.ndarray) -> int:
        return int(np.count_nonzero(np.diff(np.concatenate(([0.0], path)))))

    def test_hold_one_is_the_old_behaviour_and_longer_holds_trade_less(self) -> None:
        base = sc.target_path(sc.evaluate(self.bars, self.cfg))
        cfg = json.loads(json.dumps(self.cfg))
        cfg["aggregate"]["hold"] = 24
        held = sc.target_path(sc.evaluate(self.bars, cfg))
        self.assertLess(self.trades(held), self.trades(base))
        # Every entry is kept for at least min(hold, bars until a flip or the end).
        starts = np.flatnonzero((held != 0) & (np.concatenate(([0.0], held[:-1])) != held))
        for i in starts:
            run = held[i:i + 24]
            self.assertTrue(np.all(run == held[i]) or np.any(run == -held[i]), f"entry at {i} cut short")

    def test_entry_quantile_only_takes_the_strongest_readings(self) -> None:
        ev = sc.evaluate(self.bars, self.cfg)
        cfg = json.loads(json.dumps(self.cfg))
        cfg["aggregate"].update(entry_quantile=0.9, adaptive_window=200)
        strict = sc.evaluate(self.bars, cfg)
        self.assertLess(int(np.count_nonzero(strict.indication)), int(np.count_nonzero(ev.indication)))
        self.assertTrue(np.all(np.abs(strict.composite[strict.indication != 0]) >= cfg["aggregate"]["entry"]))

    def test_forecast_reports_move_against_cost_by_holding_period(self) -> None:
        ev = sc.evaluate(self.bars, self.cfg)
        stats = sc.forecast_stats([ev])
        bars = [h["bars"] for h in stats["horizons"]]
        self.assertEqual(bars, [h for h in sc.HORIZONS if h < len(self.bars) - 1])
        h1 = stats["horizons"][0]
        self.assertAlmostEqual(h1["net_bps"], h1["gross_bps"] - stats["round_trip_bps"], places=2)


if __name__ == "__main__":
    unittest.main()
