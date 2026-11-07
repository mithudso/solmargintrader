"""A liquidation hidden inside a coarse bar must not be rescued by its close.

The engine checks a held bar's low/high, but a daily range says only THAT a level
was visited. These tests pin the finer-bar walk (IntrabarLayer) and the cases
where a daily bar and its hourly bars disagree.
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.types import CostConfig, IntrabarLayer, Mode

DAY = 86400
T0 = 1_700_000_000 - (1_700_000_000 % DAY)


class Always:
    """Fully long from the first decision."""
    name = "always"
    params: dict = {}

    def warmup_bars(self) -> int:
        return 0

    def on_bar(self, history) -> float:
        return 1.0


def daily(n=6, price=100.0, lows=None, closes=None):
    ts = T0 + np.arange(n, dtype="int64") * DAY
    close = np.full(n, price) if closes is None else np.asarray(closes, float)
    low = np.minimum(close, price) * 0.995 if lows is None else np.asarray(lows, float)
    return {"ts": ts, "open": np.full(n, price), "high": np.full(n, price * 1.01),
            "low": low, "close": close, "volume": np.full(n, 1.0)}


def hourly_for(d, dip_hour=None, dip_price=None):
    rows = []
    for i, t in enumerate(d["ts"]):
        for h in range(24):
            o = d["open"][i]
            lo, hi, c = o * 0.999, o * 1.001, o
            if dip_hour is not None and i == 2 and h == dip_hour:
                lo = dip_price
            rows.append((t + h * 3600, o, hi, lo, c))
    a = np.array(rows, float)
    return {"ts": a[:, 0].astype("int64"), "open": a[:, 1], "high": a[:, 2],
            "low": a[:, 3], "close": a[:, 4]}


def cfg(layers=(), lev=20.0):
    return EngineConfig(
        mode=Mode.PERP, leverage=lev, interval="1d",
        costs=CostConfig(liquidation_penalty_bps=50.0, liquidation_forfeits_collateral=True),
        intrabar=tuple(layers),
    )


class TestIntrabarLiquidation(unittest.TestCase):
    def test_wick_liquidates_even_though_the_close_recovers(self) -> None:
        # 20x long: liquidation is ~4.7% below entry. Day 2 wicks to 90 and closes at 100.
        d = daily(lows=[99.5, 99.5, 90.0, 99.5, 99.5, 99.5])
        res = run_backtest(Always(), d, cfg())
        self.assertGreaterEqual(res.liquidation_count, 1)
        self.assertEqual([t for t in res.trades if t.reason == "liquidation"][0].bar_index, 2)

    def test_hourly_dip_hidden_in_a_daily_bar_is_found(self) -> None:
        d = daily()  # daily low 99.5 never reaches liquidation
        h = hourly_for(d, dip_hour=13, dip_price=90.0)
        # The daily feed misses the wick; the hourly feed has it.
        without = run_backtest(Always(), d, cfg())
        self.assertEqual(without.liquidation_count, 0)
        with_fine = run_backtest(Always(), d, cfg([IntrabarLayer("1h", h)]))
        self.assertEqual(with_fine.liquidation_count, 1, "hidden liquidation was missed")
        liq = [t for t in with_fine.trades if t.reason == "liquidation"][0]
        self.assertEqual(liq.ts, int(d["ts"][2]) + 13 * 3600, "fill must carry the hour of the touch")

    def test_daily_low_deeper_than_hourly_is_still_honoured(self) -> None:
        d = daily(lows=[99.5, 99.5, 90.0, 99.5, 99.5, 99.5])
        h = hourly_for(d)  # hourly never dips
        res = run_backtest(Always(), d, cfg([IntrabarLayer("1h", h)]))
        self.assertEqual(res.liquidation_count, 1)
        self.assertGreaterEqual(res.bars_range_mismatch, 1)

    def test_penalty_fills_below_the_liquidation_price_and_forfeits(self) -> None:
        d = daily(lows=[99.5, 99.5, 90.0, 99.5, 99.5, 99.5])
        res = run_backtest(Always(), d, cfg())
        liq = [t for t in res.trades if t.reason == "liquidation"][0]
        no_pen = run_backtest(Always(), d, EngineConfig(
            mode=Mode.PERP, leverage=20.0, interval="1d", costs=CostConfig()))
        liq0 = [t for t in no_pen.trades if t.reason == "liquidation"][0]
        self.assertAlmostEqual(liq.price, liq0.price * 0.995, places=6)
        self.assertLess(liq.equity_after, liq0.equity_after + 1e-9)

    def test_consistent_feeds_agree_with_the_coarse_run_when_nothing_liquidates(self) -> None:
        d = daily()
        h = hourly_for(d)
        a = run_backtest(Always(), d, cfg(lev=2.0))
        b = run_backtest(Always(), d, cfg([IntrabarLayer("1h", h)], lev=2.0))
        np.testing.assert_allclose(a.equity, b.equity, rtol=1e-12)
        self.assertGreater(b.bars_refined, 0)

    def test_uncovered_bars_fall_back_and_are_counted(self) -> None:
        d = daily()
        h = hourly_for(d)
        keep = h["ts"] >= d["ts"][3]  # hourly covers only the last 3 days
        h = {k: v[keep] for k, v in h.items()}
        res = run_backtest(Always(), d, cfg([IntrabarLayer("1h", h)], lev=2.0))
        self.assertGreater(res.bars_unrefined, 0)
        self.assertGreater(res.bars_refined, 0)

    def test_layer_must_be_finer_than_the_bar(self) -> None:
        d = daily()
        with self.assertRaises(ValueError):
            EngineConfig(mode=Mode.PERP, leverage=2.0, interval="1h",
                         intrabar=(IntrabarLayer("1d", {k: v for k, v in d.items() if k != "volume"}),))


if __name__ == "__main__":
    unittest.main()


class TestTierNoLeak(unittest.TestCase):
    """Tiers add no signal logic, and the decision at bar t ignores bars after t."""

    def test_tier_signal_matches_base_and_ignores_the_future(self) -> None:
        from backtester.core.strategies import build
        from backtester.core.types import BarWindow

        rng = np.random.default_rng(3)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 300)))
        a = {"ts": T0 + np.arange(300, dtype="int64") * DAY, "open": close, "high": close * 1.01,
             "low": close * 0.99, "close": close, "volume": np.ones(300)}
        base, tier = build("macd"), build("lev_high", base="macd")
        t = 200
        w = BarWindow(a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], t)
        self.assertEqual(base.on_bar(w), tier.on_bar(w))
        poisoned = {k: v.copy() for k, v in a.items()}
        for k in ("open", "high", "low", "close"):
            poisoned[k][t + 1:] *= 7.0
        w2 = BarWindow(poisoned["ts"], poisoned["open"], poisoned["high"], poisoned["low"],
                       poisoned["close"], poisoned["volume"], t)
        self.assertEqual(tier.on_bar(w), tier.on_bar(w2))
        self.assertEqual(tier.engine_leverage, 20.0)
