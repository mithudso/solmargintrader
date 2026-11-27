from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backtester.core.volty import VoltyConfig
from backtester.core.volty import simulate as volty_simulate
from research.scripts import target_1pct_day as t


def frame(close, spread=0.5, step=300):
    close = np.asarray(close, dtype=float)
    opens = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"open": opens, "high": np.maximum(opens, close) + spread,
                         "low": np.minimum(opens, close) - spread, "close": close,
                         "volume": np.ones(len(close))}, index=np.arange(len(close)) * step)


def random_walk(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))


FREE = t.Costs(fee_bps=0, slip_bps=0, funding_bps_h=0, mmr=0, liq_fee=0)


class TargetOnePercentTests(unittest.TestCase):
    def test_volty_matches_the_backtester_engine_at_1x(self):
        # The study must replay the same rule the repository's own engine replays.
        f = frame(random_walk(), spread=0.3)
        costs = t.Costs(fee_bps=3.5, slip_bps=2, funding_bps_h=0.1, mmr=0, liq_fee=0)
        mine = t.simulate(f, 300, 1.0, costs, stops=t.volty_levels(f))
        bars = {k: f[k].to_numpy() for k in ("open", "high", "low", "close", "volume")}
        bars["timestamp"] = f.index.to_numpy().astype(float)
        theirs = volty_simulate(bars, VoltyConfig(length=10, atr_mult=1.5, fee_bps=3.5, slippage_bps=2,
                                                  carry_bps_hour=0.1, initial_capital=1.0), 300,
                                close_at_end=False)
        self.assertAlmostEqual(mine["equity"][-1], theirs["equity"][-1], places=9)

    def test_leverage_multiplies_a_clean_move_and_costs_cut_it(self):
        f = frame(np.linspace(100, 110, 50), spread=0.0)
        targets = np.ones(len(f))
        one = t.simulate(f, 300, 1, FREE, targets=targets)["equity"][-1]
        three = t.simulate(f, 300, 3, FREE, targets=targets)["equity"][-1]
        self.assertAlmostEqual(three - 1, 3 * (one - 1), places=6)
        costly = t.simulate(f, 300, 3, t.Costs(fee_bps=10, slip_bps=5, funding_bps_h=1, mmr=0, liq_fee=0),
                            targets=targets)
        self.assertLess(costly["equity"][-1], three)
        self.assertGreater(costly["funding"], 0)

    def test_liquidation_on_an_intrabar_wick_not_only_on_closes(self):
        close = np.full(20, 100.0)
        f = frame(close, spread=0.0)
        f.loc[f.index[10], "low"] = 94.0      # a 6% wick that closes flat
        costs = t.Costs(fee_bps=0, slip_bps=0, funding_bps_h=0, mmr=0.01, liq_fee=0.0075)
        run = t.simulate(f, 300, 25, costs, targets=np.ones(len(f)))
        self.assertEqual(run["liquidations"], 1)
        self.assertLess(run["equity"][-1], 0.1)
        survives = t.simulate(f, 300, 10, costs, targets=np.ones(len(f)))
        self.assertEqual(survives["liquidations"], 0)

    def test_signals_never_use_the_bar_they_trade_on(self):
        close = random_walk(400)
        changed = close.copy()
        changed[300:] *= 0.5
        a, b = frame(close), frame(changed)
        np.testing.assert_array_equal(t.rsi_targets(a)[:301], t.rsi_targets(b)[:301])
        np.testing.assert_array_equal(t.ma_cross_targets(a)[:301], t.ma_cross_targets(b)[:301])
        np.testing.assert_array_equal(t.volty_levels(a)[0][:301], t.volty_levels(b)[0][:301])

    def test_stop_loss_flattens_and_caps_the_loss(self):
        close = np.r_[np.full(15, 100.0), 101.0, 99.0, 95.0, np.full(5, 95.0)]
        f = frame(close, spread=0.1)
        run = t.simulate(f, 300, 1, FREE, stops=t.volty_levels(f, length=2, mult=0.5), stop_loss=0.008)
        self.assertGreater(run["trades"], 0)
        self.assertGreater(run["equity"].min(), 0.9)

    def test_daily_returns_and_target_metrics(self):
        ts = np.arange(3 * 288) * 300
        eq = np.repeat([1.01, 1.0201, 1.030301], 288)
        d = t.daily_returns(eq, ts)
        np.testing.assert_allclose(d, [0.01, 0.01, 0.01])
        m = t.metrics({"equity": eq, "timestamps": ts, "trades": 0, "liquidations": 0,
                       "fees": 0, "funding": 0, "ruined": False}, 0.01)
        self.assertTrue(m["hits_target"])
        self.assertAlmostEqual(m["geo_daily"], 0.01)

    def test_bootstrap_is_seeded_and_bounded(self):
        d = np.random.default_rng(1).normal(0.001, 0.02, 200)
        a, b = t.bootstrap(d, 0.01, 300, seed=4), t.bootstrap(d, 0.01, 300, seed=4)
        self.assertEqual(a, b)
        self.assertTrue(0 <= a["p_hit_target"] <= 1 and a["p05_year_multiple"] <= a["p95_year_multiple"])


if __name__ == "__main__":
    unittest.main()
