"""The issuance deadline cannot turn a non-due poll into a missed forecast."""

from __future__ import annotations

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from soltui import config
from soltui import forwardtest as ft
from soltui.tests.test_forwardtest import BASE, candles


class ForwardIssuanceTiming(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.enterContext(patch.object(config, "CONFIG_DIR", Path(temporary.name)))
        self.path = Path(temporary.name) / "forward.sqlite3"
        self.trial = {"label": "hold", "mode": "all", "members": [ft.member("buy_and_hold", {})]}

    def tick(self, minute, horizon, *, completed=None):
        observed = BASE + minute * 60 + 4
        times = iter((observed, observed if completed is None else completed))
        return ft.tick("SOL", [self.trial], (horizon,), 16., tune=False,
                       fetch=lambda *a, **k: candles(minute), clock=lambda: next(times),
                       code="timing-fixture", db_path=self.path)

    def calls(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT * FROM call ORDER BY bar").fetchall()

    def test_pending_daily_window_crossing_minute_does_not_miss_a_call(self):
        self.assertEqual(self.tick(0, 1440)["recorded"], 1)
        before = self.calls()
        with patch.object(ft, "_predict", side_effect=AssertionError("no forecast is due")):
            checked = self.tick(60, 1440, completed=BASE + 61 * 60)
        self.assertEqual(checked["recorded"], 0)
        self.assertEqual(checked["message"], "Waiting for existing forecast window")
        self.assertEqual(self.calls(), before)
        self.assertEqual((checked["rows"][0]["pending"], checked["rows"][0]["resolved"]), (1, 0))

    def test_due_call_finishing_after_issuance_deadline_is_never_backdated(self):
        checked = self.tick(0, 1440, completed=BASE + 60)
        self.assertEqual(checked["recorded"], 0)
        self.assertEqual(checked["message"], "Forecast window elapsed during calculation")
        self.assertIsNone(checked["bar"])
        self.assertEqual(self.calls(), [])

    def test_timely_call_settles_only_after_its_target_is_observed(self):
        issued = self.tick(0, 5)
        self.assertEqual(issued["recorded"], 1)
        original = self.calls()[0]
        self.assertLess(original[2], original[3] - 1)
        before_target = self.tick(5, 5)
        self.assertEqual(before_target["rows"][0]["resolved"], 0)
        after_target = self.tick(6, 5)
        self.assertEqual(after_target["rows"][0]["resolved"], 1)
        self.assertEqual(self.calls()[0][:8], original[:8])


if __name__ == "__main__":
    unittest.main()
