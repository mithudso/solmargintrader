"""Closed streak causality, live trade isolation, units and history alignment."""

from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import numpy as np

from backtester.core import indicators as ind
from research import zec_live as live
from research.tests.test_zec_tui_model import candles
from research.zec_tui_chart import MarketChart, plot_text
from research.zec_tui_metrics import IndicatorSession, two_bar_context
from research.zec_tui_model import market_indicators


def sample(count=100, step=60):
    rows = candles(count, step)
    for i, bar in enumerate(rows.values()):
        close = 100 + float(np.sin(i / 3))
        bar.update(open=close - 0.2, high=close + 1, low=close - 1, close=close)
    return rows


class TwoBars(unittest.TestCase):
    def rows(self, colors):
        rows = candles(len(colors), 600)
        for bar, color in zip(rows.values(), colors):
            bar["open"], bar["close"] = 100, 100 + color
        return rows

    def test_up_pair_and_new_streak_use_different_actual_denominators(self):
        result = two_bar_context(self.rows([-1, 1, 1]), "10m", 1800)
        self.assertEqual((result["condition"], result["direction"]), ("UU", "DOWN"))
        self.assertTrue(result["new_streak"])
        self.assertEqual(result["historical"]["reversals"], 19)
        self.assertEqual(result["historical"]["total"], 24)
        self.assertEqual(result["historical"]["exact_reversals"], 14)
        self.assertEqual(result["historical"]["exact_total"], 19)
        self.assertIn("79.2%", result["text"])
        self.assertIn("not live probability", result["text"])
        self.assertFalse(result["qualified"])
        self.assertEqual(result["target_at"], 2400)

    def test_down_pair_keeps_flat_and_does_not_use_complement_as_reversal(self):
        result = two_bar_context(self.rows([1, -1, -1]), "10m", 1800)
        self.assertEqual(result["historical"]["reversals"], 16)
        self.assertEqual(result["historical"]["total"], 29)
        self.assertEqual(result["historical"]["flats"], 1)
        self.assertIn("55.2%", result["text"])
        self.assertIn("6/13 = 46.2%", result["text"])

    def test_rolling_pair_in_longer_run_is_not_exactly_two(self):
        result = two_bar_context(self.rows([1, 1, 1]), "10m", 1800)
        self.assertFalse(result["new_streak"])
        self.assertIn("longer run", result["text"])

    def test_mixed_flat_missing_and_unknown_prefix(self):
        for colors in ([1, 0], [-1, 1], [0, -1]):
            result = two_bar_context(self.rows(colors), "10m", 1200)
            self.assertIsNone(result["direction"])
            self.assertIsNone(result["historical"])
        rows = self.rows([-1, 1, 1])
        del rows[600]
        self.assertIsNone(two_bar_context(rows, "10m", 1800)["direction"])
        del rows[0]
        rows[600] = {"open": 100, "close": 101}
        self.assertIsNone(two_bar_context(rows, "10m", 1800)["new_streak"])

    def test_forming_and_future_bars_cannot_change_closed_pair(self):
        rows = self.rows([-1, 1, 1])
        before = two_bar_context(rows, "10m", 1800)
        rows[1800] = {"open": 100, "close": 1}
        rows[2400] = {"open": 100, "close": 10000}
        self.assertEqual(two_bar_context(rows, "10m", 1800), before)

    def test_no_false_probability_when_reference_cannot_be_verified(self):
        with patch("research.zec_tui_metrics.streak_reference", side_effect=ValueError):
            result = two_bar_context(self.rows([-1, 1, 1]), "10m", 1800)
        self.assertIsNone(result["historical"])
        self.assertIn("reference unavailable", result["text"])
        self.assertNotIn("79.2", result["text"])

    def test_selected_timeframe_reference_and_hourly_sample_warning(self):
        for interval, step in live.STEPS.items():
            rows = candles(3, step)
            r = two_bar_context(rows, interval, 3 * step)
            self.assertEqual(r["target_at"], 4 * step)
            self.assertEqual(r["interval"], interval)
            if interval == "1h":
                self.assertIn("tiny sample", r["text"])


class Metrics(unittest.TestCase):
    def setUp(self):
        self.now = [6005.0]
        self.session = IndicatorSession(clock=lambda: self.now[0])
        self.rows = sample()
        self.request = {
            "rows": self.rows,
            "interval": "1m",
            "end": 6000,
            "lookback": 96,
            "configs": [],
            "context": "view-a",
        }

    def get(self, **patches):
        return self.session({**self.request, **patches}, lambda: False)

    def snapshot(self, close=100.8):
        return {
            "connected": True,
            "partial": True,
            "gap": False,
            "observed_at": self.now[0],
            "event_at": self.now[0],
            "bar": {
                "ts": 6000,
                "open": 100,
                "high": max(101, close),
                "low": min(99, close),
                "close": close,
                "volume": 3,
            },
        }

    def test_histories_use_each_prefix_and_align_with_candle_times(self):
        frame = self.get()
        self.assertEqual(frame["context"], "view-a")
        self.assertEqual(len(frame["chart"]), 96)
        self.assertEqual(frame["times"], list(range(240, 6000, 60)))
        for name, values in frame["series"].items():
            self.assertEqual(len(values), len(frame["times"]), name)
        closes = np.array([x["close"] for x in self.rows.values()])
        for index, value in enumerate(frame["series"]["RSI 14"]):
            n = index + 5
            self.assertEqual(value, ind.rsi(closes[:n]) if n >= 15 else None)

    def test_live_point_changes_with_trades_without_advancing_closed_bars(self):
        before = copy.deepcopy(self.rows)
        low = self.get(live=self.snapshot(99))
        high = self.get(live=self.snapshot(102))
        values = lambda f: {r["name"]: r["value"] for r in f["indicators"]}
        self.assertNotEqual(values(low)["RSI 14"], values(high)["RSI 14"])
        self.assertNotEqual(
            values(low)["Balance of power"], values(high)["Balance of power"]
        )
        self.assertEqual(values(high)["Volume (ZEC)"], 3)
        self.assertEqual(high["times"][-1], 6000)
        self.assertEqual(high["series"]["RSI 14"][-1], values(high)["RSI 14"])
        self.assertTrue(high["live"] and high["partial"])
        self.assertEqual(self.rows, before)
        self.assertEqual(low["two_bar"], high["two_bar"])
        self.assertEqual(self.get(live=self.snapshot(102)), high)

    def test_same_trade_is_not_accumulated_or_fed_back_into_history(self):
        first = self.get(live=self.snapshot())
        second = self.get(live=self.snapshot())
        self.assertEqual(first, second)
        self.assertEqual(len(first["chart"]), 96)
        self.assertEqual(first["two_bar"]["asof"], 6000)

    def test_gap_disconnect_stale_future_or_wrong_bucket_never_append(self):
        for change in [
            {"connected": False},
            {"gap": True},
            {"observed_at": 5900},
            {"observed_at": 6006},
            {"event_at": 5900},
            {"event_at": 6006},
            {"bar": {**self.snapshot()["bar"], "ts": 6060}},
            {"bar": {**self.snapshot()["bar"], "volume": float("nan")}},
        ]:
            with self.subTest(change=change):
                frame = self.get(live={**self.snapshot(), **change})
                self.assertFalse(frame["live"])
                self.assertLess(frame["times"][-1], 6000)
                self.assertIsNotNone(frame["reason"])

    def test_expired_two_bar_target_is_not_rolled_forward_on_paint(self):
        first = self.get()
        self.now[0] = 6065
        expired = self.get()
        self.assertTrue(expired["stale"])
        self.assertTrue(expired["two_bar"]["stale"])
        self.assertEqual(first["two_bar"]["target_at"], expired["two_bar"]["target_at"])
        self.assertIsNone(expired["two_bar"]["direction"])

    def test_real_gap_does_not_create_an_indicator_bridge(self):
        rows = copy.deepcopy(self.rows)
        del rows[96 * 60]
        frame = self.get(rows=rows)
        rsi = next(r for r in frame["indicators"] if r["name"] == "RSI 14")
        self.assertIsNone(rsi["value"])
        self.assertEqual(frame["times"], [5820, 5880, 5940])
        self.assertTrue(all(x is None for x in frame["series"]["RSI 14"]))

    def test_cache_reuses_completed_history_but_recomputes_forming_point(self):
        with patch(
            "research.zec_tui_metrics.market_indicators", wraps=market_indicators
        ) as compute:
            self.get()
            closed_calls = compute.call_count
            self.get(live=self.snapshot())
            self.assertEqual(compute.call_count, closed_calls + 1)
            self.get(live=self.snapshot(102))
            self.assertEqual(compute.call_count, closed_calls + 2)

    def test_future_poison_does_not_change_past_history_or_cache(self):
        expected = self.get()
        rows = copy.deepcopy(self.rows)
        rows[6600] = {"ts": 6600, "close": 1e8}
        self.assertEqual(self.get(rows=rows), expected)

    def test_cancellation_cannot_publish_partial_cache(self):
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            self.session(self.request, lambda: True)
        self.assertIsNone(self.session._closed)


class Charts(unittest.TestCase):
    def frame(self):
        return IndicatorSession(clock=lambda: 6005)(
            {
                "rows": sample(),
                "interval": "1m",
                "end": 6000,
                "lookback": 96,
                "configs": [],
            },
            lambda: False,
        )

    def test_price_metrics_share_usd_while_rsi_and_volume_use_right_scale(self):
        for name, shared in [
            ("EMA20", True),
            ("BB20 upper 2σ", True),
            ("RSI 14", False),
            ("Volume (ZEC)", False),
            ("MACD histogram", False),
        ]:
            text = plot_text(self.frame(), name, width=100).plain
            self.assertIn("shared USD scale" if shared else "independent scale", text)
            self.assertIn("◆", text)

    def test_no_overlay_means_only_price_and_no_unobserved_projection(self):
        text = plot_text(self.frame(), width=80).plain
        self.assertNotIn("◆", text)
        self.assertIn("click an indicator", text)
        self.assertNotIn("forecast", text)

    def test_null_warmup_and_bad_alignment_never_draw_invented_line(self):
        frame = self.frame()
        frame["series"]["RSI 14"] = [None] * len(frame["chart"])
        self.assertIn("unavailable", plot_text(frame, "RSI 14").plain)
        frame["series"]["RSI 14"] = [1]
        self.assertIn("unaligned indicator", plot_text(frame, "RSI 14").plain)

    def test_price_data_compatibility_and_clear(self):
        chart = MarketChart([])
        chart.set_frame(self.frame(), "RSI 14")
        self.assertEqual(list(chart.data), self.frame()["chart"])
        chart.set_frame(None)
        self.assertEqual(list(chart.data), [])
        self.assertIn("waiting", chart.render().plain)


if __name__ == "__main__":
    unittest.main()
