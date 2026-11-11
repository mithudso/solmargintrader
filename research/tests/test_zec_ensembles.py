"""Causality, batch economics and resumable signal-state parity."""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.strategies import build
from backtester.core.types import BarWindow
from backtester.core.zec_ensemble import (
    build_ensemble,
    component_signal_series,
    signal_series,
    spec_id,
)
from research.zec_ensembles import (
    COSTS,
    batch_spot,
    canonical_replay,
    catalog,
    spec,
    targets,
    verify_batch_parity,
)


def candles(n=900, interval=3600):
    rng = np.random.default_rng(774)
    op = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    close = op * np.exp(rng.normal(0, 0.004, n))
    return {
        "ts": np.arange(n) * interval + 1_700_000_000,
        "open": op,
        "close": close,
        "high": np.maximum(op, close) * 1.005,
        "low": np.minimum(op, close) * 0.995,
        "volume": rng.uniform(1, 100, n),
    }


def window(a, i):
    return BarWindow(
        a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], i
    )


class ZecEnsembleTests(unittest.TestCase):
    def test_batch_accounting_matches_canonical_next_open_costs_and_deadbands(self):
        verify_batch_parity()
        data = candles()
        target = np.tile([0, 1, 1, 0.5, 0, 0.25], 150)
        for multiplier in (1, 2):
            batch = batch_spot(target, data, "1h", [0], multiplier)[0]
            ref = canonical_replay(target, data, "1h", cost_multiplier=multiplier)
            self.assertAlmostEqual(batch["final_equity"], ref["final_equity"], places=7)
            self.assertAlmostEqual(batch["total_fees"], ref["total_fees"], places=7)
            self.assertGreater(batch["total_fees"], 0)
            self.assertEqual(COSTS["fill_delay"], 1)

    def test_cached_stateful_mismatched_warmups_match_shared_builder(self):
        data = candles()
        cfg = {
            "interval": "1h",
            "mode": "switch",
            "members": [spec("swing_confluence")],
            "gate": spec("vol_regime"),
            "fallback": spec("rsi"),
            "persistence": 3,
        }
        builder = build_ensemble(cfg)
        specs = [*cfg["members"], cfg["gate"], cfg["fallback"]]
        signals = {spec_id(s): component_signal_series(s, data) for s in specs}
        warmups = {
            spec_id(s): build(s["strategy"], **s["params"]).warmup_bars() for s in specs
        }
        expected, _ = targets(builder.params, signals, warmups, 400)
        actual = signal_series(cfg, data)
        np.testing.assert_array_equal(actual, expected)

    def test_future_mutation_cannot_change_prefix_or_checkpoint_restore(self):
        data = candles()
        cfg = {
            "interval": "1h",
            "mode": "all",
            "members": [spec("rsi"), spec("ts_momentum")],
            "persistence": 2,
        }
        original = signal_series(cfg, data)
        changed = {k: v.copy() for k, v in data.items()}
        for key in ("open", "high", "low", "close"):
            changed[key][500:] *= 10
        np.testing.assert_array_equal(signal_series(cfg, changed)[:500], original[:500])
        first = build_ensemble(cfg)
        first.on_bar(window(data, 499))
        restored = build_ensemble(cfg)
        restored.restore_state(first.checkpoint_state())
        self.assertEqual(restored.on_bar(window(data, 899)), original[-1])
        truncated = {k: v[450:] for k, v in data.items()}
        with self.assertRaisesRegex(ValueError, "origin changed"):
            restored.on_bar(window(truncated, len(truncated["ts"]) - 1))

    def test_incremental_members_match_canonical_prefix_recurrences(self):
        data = candles(1000)
        for name in ("rsi", "obv_trend", "swing_confluence", "garch_voltarget"):
            member = build(name)
            if name == "garch_voltarget":
                member.target_vol *= np.sqrt(365 / 8760)
            expected = np.zeros(1000)
            for i in range(member.warmup_bars(), 1000):
                expected[i] = member.on_bar(window(data, i))
            np.testing.assert_allclose(
                component_signal_series(spec(name), data),
                expected,
                atol=1e-12,
                rtol=1e-12,
            )

    def test_majority_and_supermajority_are_distinct_for_five_members(self):
        from backtester.core.zec_ensemble import combine

        values = [1, 1, 1, 0, 0]
        self.assertEqual(combine({"mode": "majority"}, values), 1)
        self.assertEqual(combine({"mode": "supermajority"}, values), 0)

    def test_catalog_is_unique_and_includes_guide_and_canonical_controls(self):
        for interval in ("1m", "1h"):
            rows = catalog(interval)
            self.assertEqual(len(rows), len({r["candidate_id"] for r in rows}))
            self.assertGreater(len(rows), 800)
            singles = {
                r["config"]["members"][0]["strategy"]
                for r in rows
                if r["family"] == "canonical-single"
            }
            self.assertIn("buy_and_hold", singles)
            self.assertIn("rsi", singles)
            self.assertTrue(
                any(r["family"] == "train-correlation-weighted" for r in rows)
            )
            self.assertTrue(
                any(r["family"] == "regime-routes-trend-or-reversion" for r in rows)
            )


if __name__ == "__main__":
    unittest.main()
