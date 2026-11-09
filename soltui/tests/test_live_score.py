"""Live display votes are prospective, evidence-gated and independent of trainer revisions."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from soltui import config, forwardtest, live_score


class LiveScoreTests(unittest.TestCase):
    def test_shared_browser_and_tui_vectors(self) -> None:
        fixtures = json.loads(Path(__file__).with_name("fixtures").joinpath("live-score.json").read_text())
        for case in fixtures:
            with self.subTest(case=case["name"]):
                actual = live_score.aggregate_predictions(case["rows"], now=case["now"], **case["policy"])
                self.assertEqual({key: actual[key] for key in case["expected"]}, case["expected"])

    def test_non_finite_or_malformed_evidence_cannot_vote(self) -> None:
        for value in (None, True, float("nan"), float("inf"), "90"):
            row = {"label": "bad", "accuracy": value, "resolved": 30}
            self.assertIsNone(live_score.aggregate_predictions([row], now=150)["score"])
        self.assertIsNone(live_score.aggregate_predictions([None], now=150)["score"])
        self.assertIsNone(live_score.aggregate_predictions([], min_accuracy=float("nan"))["score"])

    def test_latest_call_direction_and_expiry_stay_bound_across_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.sqlite3"
            db = forwardtest._db(path)
            with db:
                for key, direction, issued in (("old", 1, 100), ("new", -1, 110)):
                    db.execute("INSERT INTO trial(id,asset,label,mode,minutes,cost,active) VALUES(?, 'SOL','same','all',1,1,'[]')", (key,))
                    for bar in range(20):
                        db.execute("INSERT INTO call(trial,bar,issued,start,finish,prediction,outcome) VALUES(?,?,?,?,?,?,?)",
                                   (key, bar, bar, bar, bar+1, direction, direction))
                    db.execute("INSERT INTO call(trial,bar,issued,start,finish,prediction) VALUES(?,?,?,?,?,?)",
                               (key, issued, issued, issued+1, issued+100, direction))
            db.close()
            out = live_score.prediction_snapshot("SOL", now=150, db_path=path)
            self.assertEqual(len(out["rows"]), 1)
            self.assertEqual(out["rows"][0]["pred_1m"], "DOWN")
            self.assertEqual(out["rows"][0]["issued_1m"], 110)
            self.assertEqual(out["rows"][0]["expires_1m"], 210)
            self.assertEqual(out["aggregate"]["score"], -100)

    def test_score_tape_scrolls_without_rewriting_the_previous_tick(self) -> None:
        history = [(1, 100), (2, 101)]
        scores = {1: 80, 2: -40}
        before = live_score.tick_window(history[:1], scores, 24)
        after = live_score.tick_window(history, scores, 24)
        self.assertEqual(before["padding"], after["padding"] + after["slot"])
        self.assertEqual(after["scores"], [80, -40])
        self.assertEqual(live_score.tick_window(history, {}, 8)["scores"], [None])

    def test_vote_settings_reject_non_finite_and_fractional_values(self) -> None:
        for kwargs in ({"live_vote_min_accuracy": float("nan")}, {"live_vote_min_accuracy": 101},
                       {"live_vote_min_accuracy": True}, {"live_vote_min_resolved": 0},
                       {"live_vote_min_resolved": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(config.ConfigError):
                config.validate(config.Settings(**kwargs))
        self.assertEqual(config.validate(config.Settings()).live_vote_min_accuracy, 60)

    def test_missing_database_is_unavailable_not_a_zero_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = live_score.prediction_snapshot("SOL", db_path=Path(tmp) / "missing.sqlite3")
        self.assertEqual(out["rows"], [])
        self.assertIsNone(out["aggregate"]["score"])
        self.assertEqual(out["aggregate"]["label"], "Flat")
