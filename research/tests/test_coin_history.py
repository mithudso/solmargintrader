from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research import coin_history as history

HOUR = 3600
START = 1_770_249_600  # 2026-02-05T00:00:00Z, aligned to the hour


def candle(stamp: int, volume: float = 1.0) -> list:
    return [stamp, 9.0, 11.0, 9.5, 10.5, volume]


class CoinHistoryTests(unittest.TestCase):
    def test_naive_timestamps_are_rejected(self):
        with self.assertRaises(ValueError):
            history.parse_utc("2026-02-05T00:00:00")
        self.assertEqual(history.parse_utc("2026-02-05T00:00:00Z"), START)

    def test_overlapping_pages_are_deduplicated_and_complete(self):
        # Coinbase returns candles in [left, right] inclusive, so with a two-hour
        # page every boundary candle arrives twice. fetch must keep each bar once.
        universe = [START + i * HOUR for i in range(6)]
        end = START + 6 * HOUR
        calls: list[tuple[int, int]] = []

        def fake_page(product, granularity, left, right):
            calls.append((left, right))
            return [candle(s) for s in universe if left <= s <= right]

        with patch.object(history, "page", side_effect=fake_page), patch.object(history, "PAGE", 2):
            bars = history.fetch("HYPE-USD", HOUR, START, end)

        self.assertGreater(len(calls), 1)
        self.assertEqual([bar[0] for bar in bars], universe)
        self.assertEqual(len({bar[0] for bar in bars}), len(bars))

    def test_audit_reports_missing_slots_without_interpolating(self):
        bars = [
            (START, 1.0, 1.0, 1.0, 1.0, 0.0),
            (START + 2 * HOUR, 1.0, 1.0, 1.0, 1.0, 2.0),
        ]
        report = history.audit(bars, HOUR, START, START + 4 * HOUR)
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["expected_slots"], 4)
        self.assertEqual(report["missing_slots"], 2)
        self.assertEqual(report["zero_volume_bars"], 1)
        self.assertEqual(report["first_missing_slots"][0], "2026-02-05T01:00:00Z")

    def test_run_writes_gzip_with_matching_sha_and_manifest(self):
        def fake_fetch(product, granularity, start, end):
            return [(start, 1.0, 1.0, 1.0, 1.0, 1.0), (start + granularity, 1.0, 1.0, 1.0, 1.0, 1.0)]

        with tempfile.TemporaryDirectory() as tmp, patch.object(history, "fetch", side_effect=fake_fetch):
            manifest = history.run(["hype"], [HOUR], START, START + 2 * HOUR, Path(tmp))
            entry = manifest["files"]["HYPE-USD_1h.csv.gz"]
            raw = (Path(tmp) / "HYPE-USD_1h.csv.gz").read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
            text = gzip.decompress(raw).decode()
            self.assertTrue(text.startswith("unix,timestamp_utc,open,high,low,close,volume\n"))
            self.assertEqual(entry["rows"], 2)
            self.assertEqual(entry["missing_slots"], 0)
            self.assertTrue((Path(tmp) / "manifest.json").exists())

    def test_failed_pages_are_logged_on_every_attempt_then_raised(self):
        stderr = io.StringIO()
        with (
            patch.object(history, "read_url", side_effect=OSError("HTTP 429")),
            patch.object(history.time, "sleep"),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(RuntimeError),
        ):
            history.page("HYPE-USD", HOUR, START, START + HOUR)
        self.assertEqual(stderr.getvalue().count("attempt"), 4)
        self.assertIn("HTTP 429", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
