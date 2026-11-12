"""Saved-call explanations preserve latest-trial eligibility and candle causality."""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from contextlib import closing
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from soltui import config, forwardtest as ft, vote_explanation as explain

BASE = 1_800_000_000


class SavedVoteExplanation(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.enterContext(patch.object(config, "CONFIG_DIR", Path(temporary.name)))
        self.members = [ft.member("ma_crossover", {"fast": 2, "slow": 3})]
        self.trial = {"label": "probe", "mode": "all", "members": self.members}
        ft.save_session({"assets": ["SOL"], "horizons": (1,), "trials": [self.trial]})
        offsets = np.arange(-200, 1)
        prices = 100 + (offsets + 200) / 100
        arrays = dict(ts=BASE + offsets * 60, open=prices, high=prices + .1, low=prices - .1, close=prices,
                      volume=np.ones(len(prices)))
        ft.tick("SOL", [self.trial], (1,), 16., fetch=lambda *a, **k: arrays,
                clock=lambda: BASE + 4, code=ft.revision(), tune=False)
        self.path = config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
        with closing(sqlite3.connect(self.path)) as db, db:
            self.key = db.execute("SELECT id FROM trial").fetchone()[0]
            for i in range(20):
                bar = BASE - (i + 10) * 60
                db.execute("INSERT INTO call(trial,bar,issued,start,finish,generation,guesses,prediction,outcome) VALUES(?,?,?,?,?,?,?,?,?)",
                           (self.key, bar, bar + 60, bar + 120, bar + 180, 0, ft._json([(self.members, 1)]), 1, 1))

    def result(self, now=BASE + 30):
        return explain.explain("SOL", "probe", now=now)

    def test_CDO_68836a154b_saved_forecast_keeps_eligibility_without_invented_features(self):
        result = self.result()
        self.assertTrue(result["available"])
        self.assertEqual(result["eligible_horizons"], [1])
        call = result["calls"][0]
        self.assertEqual(call["trial_id"], self.key)
        self.assertEqual(call["members"], self.members)
        self.assertEqual(call["direction"], "UP")
        self.assertEqual(call["resolved"], 20)
        self.assertTrue(call["recorded_signal_basis"]["contract_verified"])
        self.assertFalse(call["recorded_signal_basis"]["features_available"])
        self.assertFalse(call["recorded_signal_basis"]["original_input_verified"])
        self.assertIsNone(call["recorded_signal_basis"]["signal_interval"])
        self.assertEqual(call["recorded_signal_basis"]["features"], [])
        self.assertIn("original signal interval", call["recorded_signal_basis"]["reason"])
        self.assertEqual(result["chart_suggestions"][0]["strategy"], "ma_crossover")
        self.assertEqual(result["chart"]["series"], [])
        self.assertFalse(result["chart"]["proof"]["origin_indicator_verified"])

    def test_future_candles_do_not_change_saved_basis_or_chart(self):
        original = self.result()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO candle VALUES('SOL',?,?,?,?,?,?)", (BASE + 3600, 999., 1000., 998., 999., 1.))
        current = self.result()
        self.assertEqual(current["chart"], original["chart"])
        self.assertEqual(current["calls"][0]["recorded_signal_basis"], original["calls"][0]["recorded_signal_basis"])
        self.assertLessEqual(max(c["time"] for c in current["chart"]["candles"]), current["calls"][0]["bar"])

    def test_expired_call_remains_inspectable_but_cannot_vote(self):
        result = self.result(now=BASE + 200)
        self.assertTrue(result["available"])
        self.assertEqual(result["eligible_horizons"], [])
        self.assertFalse(result["calls"][0]["eligible"])
        self.assertIn("Expired", result["calls"][0]["exclusion_reason"])

    def test_eligibility_rounding_matches_the_shared_live_snapshot(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            old = db.execute("SELECT bar FROM call WHERE outcome IS NOT NULL ORDER BY bar LIMIT 3").fetchall()
            db.executemany("UPDATE call SET outcome=-1 WHERE trial=? AND bar=?", [(self.key, r[0]) for r in old])
            db.execute("INSERT INTO call(trial,bar,issued,prediction,outcome) VALUES(?,?,?,?,?)", (self.key, BASE - 999 * 60, BASE - 998 * 60, 1, -1))
        result = explain.explain("SOL", "probe", now=BASE + 30, min_accuracy=81.)
        self.assertEqual(result["calls"][0]["resolved"], 21)
        self.assertEqual(result["calls"][0]["accuracy"], 81.)
        self.assertEqual(result["eligible_horizons"], [1])

    def test_missing_seed_contract_refuses_numeric_feature_assertion(self):
        ft.save_session(None)
        result = self.result()
        basis = result["calls"][0]["recorded_signal_basis"]
        self.assertFalse(basis["contract_verified"])
        self.assertFalse(basis["features_available"])
        self.assertEqual(result["chart"]["series"], [])
        self.assertTrue(result["chart"]["markers"])

    def test_adopted_current_trial_settings_do_not_replace_saved_call_spec(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE trial SET active=?", (ft._json([ft.member("rsi", {})]),))
        self.assertEqual(self.result()["calls"][0]["members"], self.members)

    def test_newer_weak_trial_is_not_replaced_by_historical_winner(self):
        newer = "f" * 64
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO trial(id,asset,label,mode,minutes,cost,active) VALUES(?,'SOL','probe','all',1,16,?)", (newer, ft._json(self.members)))
            db.execute("INSERT INTO call(trial,bar,issued,start,finish,generation,guesses,prediction) VALUES(?,?,?,?,?,?,?,?)",
                       (newer, BASE, BASE + 25, BASE + 60, BASE + 180, 0, ft._json([(self.members, -1)]), -1))
        result = self.result()
        self.assertEqual(result["calls"][0]["trial_id"], newer)
        self.assertEqual(result["calls"][0]["direction"], "DOWN")
        self.assertEqual(result["eligible_horizons"], [])

    def test_input_gap_never_receives_an_invented_sma(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM candle WHERE ts=?", (BASE - 120,))
        result = self.result()
        self.assertFalse(result["calls"][0]["recorded_signal_basis"]["features_available"])
        self.assertEqual(result["chart"]["series"], [])

    def test_unknown_strategy_and_invalid_label_do_not_create_state(self):
        self.assertFalse(explain.explain("SOL", "missing", now=BASE)["available"])
        with self.assertRaises(ValueError):
            explain.explain("SOL", "x" * 257)


if __name__ == "__main__":
    unittest.main()
