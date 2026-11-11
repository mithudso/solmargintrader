"""Source-unit conversion, missing-bar preservation and duplicate integrity."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.fetch_zec_history import (
    COLUMNS,
    api_tail,
    archive_job,
    combine_frames,
    coverage,
    normalize_frame,
)


def bars(times: list[int]) -> pd.DataFrame:
    return pd.DataFrame([[t, 10, 12, 9, 11, 4] for t in times], columns=COLUMNS)


class HistoryTests(unittest.TestCase):
    def test_millisecond_microsecond_transition_is_exact(self):
        expected = [1735689540, 1735689600]
        result = normalize_frame(bars([expected[0]*1000, expected[1]*1_000_000]), "1m")
        self.assertEqual(result.timestamp.tolist(), expected)
        for bad in (1735689600.5, 1735689600000001, 1735689601):
            with self.assertRaises(ValueError):
                normalize_frame(bars([bad]), "1m")

    def test_duplicates_must_match_all_ohlcv_fields(self):
        frame = bars([1735689600, 1735689660])
        result, removed = combine_frames([frame, frame.copy()], "1m")
        self.assertEqual(len(result), 2)
        self.assertEqual(removed, 2)
        changed = frame.copy()
        changed.loc[0, "volume"] = 5
        with self.assertRaisesRegex(ValueError, "conflicting"):
            combine_frames([frame, changed], "1m")

    def test_gap_ledger_never_synthesizes_candles(self):
        frame = bars([1735689600, 1735689660, 1735689840])
        info, gaps = coverage(frame, "1m")
        self.assertEqual(info["rows"], 3)
        self.assertEqual(info["missing_bars"], 2)
        self.assertEqual(info["longest_contiguous"]["rows"], 2)
        self.assertEqual(gaps.iloc[0].missing_bars, 2)

    def test_api_tail_discards_unclosed_bar(self):
        start, end = 1735689600, 1735689720
        rows = [[t*1000, 10, 12, 9, 11, 4] for t in (start, start+60, end)]
        with tempfile.TemporaryDirectory() as tmp, patch("research.fetch_zec_history.request_bytes", return_value=json.dumps(rows).encode()):
            frames, receipts = api_tail("1m", start, end, Path(tmp))
        self.assertEqual(frames[0].timestamp.tolist(), [start, start+60])
        self.assertEqual(len(receipts), 1)

    def test_checksum_mismatch_cannot_publish_archive(self):
        with tempfile.TemporaryDirectory() as tmp, patch("research.fetch_zec_history.request_bytes", side_effect=[b"0"*64+b" file.zip", b"invalid ZIP bytes"]):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                archive_job(("1m", "monthly", "2026-10"), Path(tmp))
            self.assertEqual(list(Path(tmp).rglob("*.zip")), [])


if __name__ == "__main__":
    unittest.main()
