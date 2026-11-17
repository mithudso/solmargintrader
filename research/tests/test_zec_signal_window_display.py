"""Ended signal windows distinguish elapsed and observed time."""

import unittest

from research.zec_tui import ended_signal_window_text


class EndedSignalWindowDisplayTest(unittest.TestCase):
    def test_elapsed_time_does_not_imply_sustained_observations(self):
        text = ended_signal_window_text({"reason": "stale", "start_ms": 1000,
                                         "last_ms": 15000, "duration_ms": 16000,
                                         "sustained": False})
        self.assertIn("elapsed 16.0s", text)
        self.assertIn("observed 14.0s", text)
        self.assertIn("not sustained 15s", text)

    def test_missing_evidence_is_unavailable(self):
        text = ended_signal_window_text({"reason": "stale", "duration_ms": 16000})
        self.assertIn("observed unavailable", text)
        self.assertIn("sustained status unavailable", text)
