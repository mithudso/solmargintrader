"""Cross-coin input boundaries, provider responses and fixed causal definitions."""

from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
import urllib.parse
import zlib
from pathlib import Path

from research.crosscoin_reversals import analyze, bar_color_baseline, dense_bars, wilson
from research.reversal_history import (
    canonical,
    coinbase_snapshot,
    epoch,
    pack,
    read_archive,
    unpack,
    validated_rows,
)


def source():
    rows = [[t, 100, 100, 100, 100, 1] for t in range(0, 3600, 60)]
    rows[0] = [0, 99, 100, 99, 100, 1]
    rows[10] = [600, 99, 100, 99, 100, 1]
    rows[20] = [1200, 103, 104, 103, 104, 1]
    rows[21] = [1260, 104, 105, 50, 102, 1]
    return {
        "coin": "TEST",
        "venue": "fixture",
        "quote": "USD",
        "product": "TEST-USD",
        "clock": "exchange UTC 1m bar open",
        "source_url": "https://example.invalid",
        "study_start": 1200,
        "study_end_exclusive": 1800,
        "input_start": 0,
        "input_end_exclusive": 3600,
        "gap_telemetry": "unavailable",
        "rows": rows,
    }


class ArchiveAndValidation(unittest.TestCase):
    def test_text_and_binary_repository_containers_reproduce_exact_values(self):
        data = source()
        raw = canonical(pack(data)).encode()
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory) / "source.json"
            binary = Path(directory) / "source.json.zlib"
            text.write_bytes(raw)
            binary.write_bytes(zlib.compress(raw, 9))
            self.assertEqual(read_archive(text), data)
            self.assertEqual(read_archive(binary), data)
            binary.write_bytes(binary.read_bytes() + b"trailing")
            with self.assertRaisesRegex(ValueError, "invalid_repository_container"):
                read_archive(binary)

    def test_lossless_archive_and_corruption(self):
        data = {"text": "UP → DOWN", "n": [1, 2, 3]}
        encoded = pack(data)
        self.assertEqual(unpack(json.loads(canonical(encoded))), data)
        for key, value in (
            ("decoded_utf8_bytes", 1),
            ("decoded_utf8_sha256", "bad"),
            ("body", encoded["body"] + "garbage"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                unpack({**encoded, key: value})

    def test_boolean_nonfinite_incoherent_and_conflicting_rows_fail(self):
        cases = [
            [True, 1, 1, 1, 1, 0],
            [0, 1, 1, 1, float("nan"), 0],
            [0, 2, 1, 1, 2, 0],
            [1, 1, 1, 1, 1, 0],
            [0, 1, 1, 1, 1, -1],
        ]
        for row in cases:
            with self.subTest(row=row), self.assertRaises(ValueError):
                validated_rows([row])
        with self.assertRaisesRegex(ValueError, "conflicting"):
            validated_rows([[0, 1, 1, 1, 1, 0], [0, 2, 2, 2, 2, 0]])

    def test_no_forward_fill_and_distinct_active_mask(self):
        data = source()
        del data["rows"][5]
        data["rows"][0][-1] = 0
        rows = dense_bars(data)
        self.assertFalse(rows[5]["present"])
        self.assertIsNone(rows[5]["close"])
        self.assertTrue(rows[0]["present"])
        self.assertFalse(rows[0]["active"])

    def test_source_and_study_bounds_fail_closed(self):
        for patch in (
            {"input_start": 1},
            {"input_end_exclusive": 60},
            {"study_start": -60},
            {"study_end_exclusive": 7200},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                analyze({**source(), **patch})


class FixedPattern(unittest.TestCase):
    def test_window_filters_preload_and_tail_events(self):
        result = analyze(source())
        self.assertTrue(result["events"])
        self.assertEqual({e["current_start"] for e in result["events"]}, {1200})
        self.assertEqual(len(result["summaries"]), 72)

    def test_signal_low_excluded_and_future_cannot_change_selection(self):
        result = analyze(source())
        event = next(e for e in result["events"] if e["policy"] == "intrabar")
        self.assertEqual(event["signal_at"], 1320)
        self.assertEqual(event["outcomes"]["10"]["future_low"], 100)
        self.assertEqual(
            event["outcomes"]["10"]["references"]["signal_close"]["down_usd"], 2
        )
        changed = source()
        for row in changed["rows"][22:]:
            row[1:5] = [500, 600, 400, 550]
        later = next(e for e in analyze(changed)["events"] if e["policy"] == "intrabar")
        self.assertEqual(
            {k: v for k, v in event.items() if k != "outcomes"},
            {k: v for k, v in later.items() if k != "outcomes"},
        )

    def test_active_requires_every_prior_and_future_minute(self):
        data = source()
        data["rows"][0][-1] = 0
        result = analyze(data)
        self.assertTrue(any(e["mask"] == "present" for e in result["events"]))
        self.assertFalse(any(e["mask"] == "active" for e in result["events"]))
        data = source()
        data["rows"][30][-1] = 0
        event = next(
            e
            for e in analyze(data)["events"]
            if e["mask"] == "active" and e["policy"] == "intrabar"
        )
        self.assertEqual(event["outcomes"]["10"]["status"], "missing_or_gap_censored")

    def test_color_flats_remain_in_denominator_and_are_not_down(self):
        rows = dense_bars(source())
        for b in rows[20:30]:
            b.update(open=100, high=100, low=100, close=100)
        stats = bar_color_baseline(rows, "present", 1200, 1800)["after_two_up"]
        self.assertEqual(
            (stats["n"], stats["DOWN"], stats["FLAT"], stats["down_rate"]), (1, 0, 1, 0)
        )

    def test_no_down_down_up_setup_and_no_percent_units_confusion(self):
        data = source()
        data["rows"][0] = [0, 101, 101, 100, 100, 1]
        data["rows"][10] = [600, 101, 101, 100, 100, 1]
        self.assertEqual(analyze(data)["events"], [])
        self.assertIsNone(wilson(0, 0))
        low, high = wilson(50, 100)
        self.assertAlmostEqual(low, 1 - high)
        self.assertLess(low, 0.5)


class PublicProvider(unittest.TestCase):
    def test_pages_trim_inclusive_boundaries_and_retain_missing_minutes(self):
        urls = []

        def get(url):
            urls.append(url)
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            left, right = epoch(q["start"][0]), epoch(q["end"][0])
            # Each page includes an early row and its inclusive end. One target
            # minute is intentionally absent. No forward filling is permitted.
            return json.dumps(
                [
                    [t, 1, 4, 2, 3, 5]
                    for t in range(left - 60, right + 1, 60)
                    if t != epoch("2026-11-12T05:01:00Z")
                ][-300:]
            ).encode()

        data = coinbase_snapshot("HYPE", get=get, pause=lambda _: None)
        self.assertEqual(len(urls), 5)
        self.assertTrue(all("HYPE-USD/candles?" in u for u in urls))
        self.assertEqual(len(data["rows"]), 1479)
        self.assertEqual(data["rows"][0][1:], [2, 4, 1, 3, 5])
        self.assertFalse(dense_bars(data)[21]["present"])
        self.assertEqual(len({r[0] for r in data["rows"]}), 1479)

    def test_retries_only_transient_public_reads_and_bounds_attempts(self):
        calls, sleeps = [], []

        def get(url):
            calls.append(url)
            raise urllib.error.HTTPError(url, 429, "rate", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            coinbase_snapshot("BTC", get=get, pause=sleeps.append)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_invalid_success_and_permanent_error_do_not_retry(self):
        for payload in (b"{}", b"[[0,1,2]]", b"[[0,1,1,1,1,0],[0,1,1,1,1,0]]"):
            calls = []

            def get(url, raw=payload, calls=calls):
                calls.append(url)
                return raw

            with self.subTest(raw=payload), self.assertRaises(ValueError):
                coinbase_snapshot("ETH", get=get, pause=lambda _: None)
            self.assertEqual(len(calls), 1)
        calls = []

        def forbidden(url):
            calls.append(url)
            raise urllib.error.HTTPError(url, 403, "denied", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            coinbase_snapshot("ETH", get=forbidden, pause=lambda _: None)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
