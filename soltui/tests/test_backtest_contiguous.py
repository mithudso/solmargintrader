"""Gap recovery must be explicit and preserve the real measured candles."""
import unittest

import numpy as np

from soltui.runner import select_contiguous


def bars(ts):
    ts = np.asarray(ts, dtype=np.int64)
    n = len(ts)
    return {"ts": ts, "open": np.full(n, 10.), "high": np.full(n, 11.),
            "low": np.full(n, 9.), "close": np.full(n, 10.), "volume": np.ones(n)}


class ContiguousSelectionTest(unittest.TestCase):
    def test_gap_refuses_by_default_and_reports_window(self):
        with self.assertRaisesRegex(ValueError, '1 gaps.*longest continuous window'):
            select_contiguous(bars([0, 60, 180, 240, 300]), '1m', longest=False)

    def test_explicit_window_uses_only_original_bars(self):
        source = bars([0, 60, 180, 240, 300])
        selected, proof = select_contiguous(source, '1m', longest=True)
        np.testing.assert_array_equal(selected['ts'], [180, 240, 300])
        self.assertEqual(proof['source_bars'], 5)
        self.assertEqual(proof['selected_bars'], 3)
        self.assertEqual(proof['gaps_excluded'], 1)
        self.assertEqual(len(source['ts']), 5)

    def test_mismatched_cadence_is_not_misrepresented_as_gaps(self):
        for timestamps in ([0, 30, 90], [0, 60, 60], [120, 60]):
            with self.subTest(timestamps=timestamps), self.assertRaises(ValueError):
                select_contiguous(bars(timestamps), '1m', longest=True)

    def test_contiguous_window_stays_unchanged(self):
        source = bars([0, 60, 120])
        selected, proof = select_contiguous(source, '1m', longest=True)
        self.assertIs(selected, source)
        self.assertIsNone(proof)
