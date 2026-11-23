import unittest
from dataclasses import replace
from urllib.parse import parse_qs, urlparse

from oracle.zec_volty_signal import (
    GumVoltySource,
    VoltyDataError,
    VoltyObservation,
    VoltySignalEngine,
)

WINDOW = 1_795_020_000


def candle(opened, opening, high=None, low=None, close=None):
    return {
        "t": opened * 1000,
        "T": (opened + 60) * 1000,
        "s": "ZEC",
        "i": "1m",
        "o": opening,
        "h": opening if high is None else high,
        "l": opening if low is None else low,
        "c": opening if close is None else close,
    }


def candles(boundary):
    start = boundary - 3300
    rows = [
        candle(opened, 100 if opened < start + 300 else 110)
        for opened in range(start, boundary, 60)
    ]
    rows[-1] = candle(boundary - 60, 112, high=113, low=108, close=112)
    # Current trade candles must never widen this window's breakout bands.
    rows.append(candle(boundary, 900))
    return rows


class PublicSourceTest(unittest.TestCase):
    def setUp(self):
        self.clock = WINDOW + 10
        self.calls = []
        self.mark = {"symbol": "ZEC", "markPrice": 112, "timestamp": self.clock}
        self.candle_transform = lambda rows: rows
        self.source = GumVoltySource(clock=lambda: self.clock, read_json=self.read)

    def read(self, url):
        self.calls.append(url)
        parsed = urlparse(url)
        self.assertEqual(parsed.netloc, "api.gum.ag")
        if parsed.path == "/app/perps/markets":
            return [{"symbol": "SOL", "markPrice": 248}, self.mark]
        self.assertEqual(parsed.path, "/app/perps/ohlcv/ZEC")
        params = parse_qs(parsed.query)
        boundary = int(params["to"][0])
        self.assertEqual(
            params,
            {"from": [str(boundary - 3300)], "to": [str(boundary)], "interval": ["1m"]},
        )
        return self.candle_transform(candles(boundary))

    def test_exact_true_range_uses_prior_close_and_excludes_current_bar(self):
        # One 10-point gap and one 5-point intrabar range, with ten true ranges total.
        first = self.source.read()
        self.assertEqual(
            first, VoltyObservation(WINDOW, self.clock, 112, 114.25, 109.75)
        )
        self.clock += 2
        self.mark["timestamp"] = self.clock
        self.assertEqual(self.source.read().upper, 114.25)
        self.assertEqual(len(self.calls), 3)

    def test_candle_gaps_and_conflicting_duplicates_fail_closed(self):
        self.candle_transform = lambda rows: rows[:31] + rows[32:]
        with self.assertRaisesRegex(VoltyDataError, "gum_closed_candles_incomplete"):
            self.source.read()
        self.candle_transform = lambda rows: rows + [candle(WINDOW - 60, 500)]
        with self.assertRaisesRegex(VoltyDataError, "gum_conflicting_candles"):
            self.source.read()
        self.assertEqual(len(self.calls), 2)

    def test_out_of_order_exact_duplicates_have_same_bands(self):
        self.candle_transform = lambda rows: list(reversed(rows + [rows[-2]]))
        self.assertEqual(self.source.read().lower, 109.75)

    def test_stale_future_and_foreign_window_marks_fail_closed(self):
        for mark_at in (WINDOW - 1, self.clock + 1, self.clock + 100):
            with self.subTest(mark_at=mark_at):
                self.mark["timestamp"] = mark_at
                with self.assertRaisesRegex(VoltyDataError, "gum_zec_mark_stale"):
                    self.source.read()
        self.clock = WINDOW + 40
        self.mark["timestamp"] = WINDOW + 15
        with self.assertRaisesRegex(VoltyDataError, "gum_zec_mark_stale"):
            self.source.read()

    def test_boundary_waits_for_closed_candle_and_refetches(self):
        self.source.read()
        self.clock = WINDOW + 302
        with self.assertRaisesRegex(VoltyDataError, "gum_waiting_for_closed_candles"):
            self.source.read()
        self.assertEqual(len(self.calls), 2)
        self.clock = WINDOW + 306
        self.mark["timestamp"] = self.clock
        self.assertEqual(self.source.read().window_start, WINDOW + 300)
        self.assertEqual(len(self.calls), 4)

    def test_window_turns_while_source_request_is_in_flight(self):
        before = WINDOW + 299
        next_times = iter((before, before + 2))
        self.mark["timestamp"] = before
        source = GumVoltySource(clock=lambda: next(next_times), read_json=self.read)
        with self.assertRaisesRegex(VoltyDataError, "gum_zec_mark_stale"):
            source.read()

    def test_malformed_prices_and_incorrect_end_time_are_not_candles(self):
        for key, value, error in (
            ("h", float("inf"), "gum_invalid_price"),
            ("c", 200.0, "gum_invalid_candle_range"),
            ("T", WINDOW * 1000 - 1, "gum_invalid_candle"),
            ("s", "ETH", "gum_invalid_candle"),
        ):
            with self.subTest(key=key):
                self.candle_transform = lambda rows, key=key, value=value: (
                    rows[:-2] + [{**rows[-2], key: value}] + rows[-1:]
                )
                with self.assertRaisesRegex(VoltyDataError, error):
                    self.source.read()


class CrossingTest(unittest.TestCase):
    def setUp(self):
        self.engine = VoltySignalEngine()

    def sample(self, offset, price):
        at = WINDOW + offset
        window = at // 300 * 300
        return self.engine.observe(VoltyObservation(window, at, price, 103, 97), now=at)

    def test_each_distinct_up_and_down_touch_emits_deterministic_signal_fields(self):
        self.assertIsNone(self.sample(20, 101))
        signal = self.sample(23, 103)
        self.assertEqual(signal.side, "buy")
        self.assertEqual(signal.mark, 103)
        self.assertEqual(signal.upper, 103)
        self.assertEqual(signal.lower, 97)
        self.assertEqual(signal.at, WINDOW + 23)
        self.assertEqual(
            signal.event_id, f"zec-gum-volty-10-1.5:{WINDOW}:{WINDOW + 23}:buy"
        )
        self.assertIsNone(
            self.sample(23, 103)
        )  # A repeated poll of the same observation.
        self.assertIsNone(self.sample(25, 104))
        self.assertIsNone(self.sample(27, 102))
        self.assertEqual(
            self.sample(30, 103).event_id,
            f"zec-gum-volty-10-1.5:{WINDOW}:{WINDOW + 30}:buy",
        )
        self.assertEqual(self.sample(35, 97).side, "sell")
        self.assertEqual(self.sample(45, 104).side, "buy")
        self.assertEqual(self.sample(50, 96).side, "sell")

    def test_startup_and_new_window_never_imply_a_crossing(self):
        self.assertIsNone(self.sample(245, 104))
        self.assertIsNone(self.sample(250, 105))
        self.assertIsNone(self.sample(283, 101))
        self.assertIsNone(self.sample(305, 104))
        self.assertIsNone(self.sample(315, 102))
        signal = self.sample(320, 103)
        self.assertEqual(
            signal.event_id, f"zec-gum-volty-10-1.5:{WINDOW + 300}:{WINDOW + 320}:buy"
        )

    def test_quote_gap_and_explicit_reset_discard_previous_crossings(self):
        self.assertIsNone(self.sample(10, 100))
        self.assertIsNone(self.sample(56, 110))
        self.assertIsNone(self.sample(57, 101))
        self.assertEqual(self.sample(60, 105).side, "buy")
        self.engine.reset()
        self.assertIsNone(self.sample(65, 96))
        self.assertIsNone(self.sample(69, 101))
        self.assertEqual(self.sample(72, 105).side, "buy")
        self.assertEqual(self.sample(77, 97).side, "sell")

    def test_equal_mark_is_ignored_but_conflicting_or_replayed_mark_resets_baseline(
        self,
    ):
        first = VoltyObservation(WINDOW, WINDOW + 10, 100, 103, 97)
        self.assertIsNone(self.engine.observe(first, now=WINDOW + 10))
        self.assertIsNone(self.engine.observe(first, now=WINDOW + 12))
        with self.assertRaisesRegex(VoltyDataError, "gum_zec_mark_replayed"):
            self.engine.observe(replace(first, mark=105), now=WINDOW + 12)
        self.assertIsNone(self.sample(14, 105))
        with self.assertRaisesRegex(VoltyDataError, "gum_zec_mark_replayed"):
            self.sample(13, 100)
        self.assertIsNone(self.sample(16, 96))

    def test_bands_cannot_change_within_an_eligible_window(self):
        self.assertIsNone(self.sample(20, 101))
        revised = VoltyObservation(WINDOW, WINDOW + 25, 104, 102, 98)
        with self.assertRaisesRegex(VoltyDataError, "gum_volty_bands_changed"):
            self.engine.observe(revised, now=WINDOW + 25)
        self.assertIsNone(self.sample(30, 104))
