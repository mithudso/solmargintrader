"""Prospective Council decisions, perps economics and detached paper lifetime."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from soltui import config as app_config, council, simulation

BASE = 1_800_000_000


def rows(score=100, *, expires=BASE + 10000):
    if score is None:
        return []
    directions = ["FLAT"] if score == 0 else ["UP"] * int((score + 100) / 40) + ["DOWN"] * (5 - int((score + 100) / 40))
    return [{"label": str(i), "accuracy": 90., "resolved": 40, "pred_30m": direction,
             "acc_30m": 90., "resolved_30m": 40, "issued_30m": BASE - 60,
             "expires_30m": expires} for i, direction in enumerate(directions)]


def bars(now, overrides=None):
    latest = int(now // 60) * 60 - 60
    ts = np.arange(BASE - 600, latest + 1, 60)
    values = [overrides.get(int(t), (100., 102., 100., 101.)) if overrides else (100., 102., 100., 101.) for t in ts]
    columns = np.asarray(values)
    return dict(ts=ts, open=columns[:, 0], high=columns[:, 1], low=columns[:, 2], close=columns[:, 3], volume=np.ones(len(ts)))


class CouncilPaper(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.enterContext(patch.object(app_config, "CONFIG_DIR", self.directory))
        council.config({"execution": {"min_confidence": 0}})
        self.recovered = []

    def tick(self, minute, score=100, *, overrides=None, expires=BASE + 10000, quote=True):
        now = BASE + minute * 60 + 5
        return council.step(now=now, snapshot={"rows": rows(score, expires=expires)},
                            quote={"source": "jupiter", "price": 100., "fetched_at": now} if quote else {},
                            bars=bars(now, overrides), recover=self.recovered.append)

    def enter(self, direction=1, overrides=None):
        self.tick(0, direction * 100)
        return self.tick(2, direction * 100, overrides=overrides)

    def test_defaults_are_paper_one_times_long_only_and_probability_is_separate(self):
        cfg = council.config({"execution": {"min_confidence": .8}})
        self.assertFalse(cfg["execution"]["allow_short"])
        self.assertFalse(cfg["execution"]["use_leverage"])
        result = self.tick(0, 100)
        self.assertEqual(result["mode"], "paper")
        self.assertIsNone(result["pending"])
        self.assertIsNone(result["confidence"])
        self.assertIn("0/20", result["message"])
        self.assertEqual(result["last_observation"]["aggregate"]["score"], 100)

    def test_status_without_saved_state_creates_no_files(self):
        with TemporaryDirectory() as temporary, patch.object(app_config, "CONFIG_DIR", Path(temporary)):
            result = council.status()
            self.assertFalse(result["running"])
            self.assertEqual(result["state"], "stopped")
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_hysteresis_holds_buy_flat_and_unavailable_and_exits_on_sell(self):
        self.assertEqual(self.enter()["position"]["direction"], 1)
        for minute, score in ((3, 20), (4, 0), (5, None)):
            result = self.tick(minute, score)
            self.assertEqual(result["position"]["direction"], 1)
            self.assertIsNone(result["pending"])
        self.assertEqual(self.recovered, ["SOL"])
        self.tick(6, -20)
        closed = self.tick(8, -20)
        self.assertIsNone(closed["position"])
        self.assertEqual([f["side"] for f in reversed(closed["fills"])], ["buy", "sell"])

    def test_short_mirror_and_strong_reversal_without_pyramiding(self):
        council.config({"execution": {"allow_short": True}})
        self.assertEqual(self.enter(-1)["position"]["direction"], -1)
        self.assertEqual(self.tick(3, -20)["position"]["direction"], -1)
        self.assertEqual(self.tick(4, 0)["position"]["direction"], -1)
        self.tick(5, 100)
        reversed_position = self.tick(7, 100)
        self.assertEqual(reversed_position["position"]["direction"], 1)
        self.assertEqual([f["side"] for f in reversed(reversed_position["fills"])], ["sell_short", "buy_to_cover", "buy"])
        self.assertEqual(len(self.tick(8, 100)["fills"]), 3)

    def test_long_can_reverse_to_short_only_when_explicitly_enabled(self):
        self.enter()
        self.tick(3, -100)
        self.assertIsNone(self.tick(5, -100)["position"])
        self.assertEqual(len(council.status()["fills"]), 2)

    def test_strong_sell_reverses_long_when_shorting_is_enabled(self):
        council.config({"execution": {"allow_short": True}})
        self.enter()
        self.tick(3, -100)
        result = self.tick(5, -100)
        self.assertEqual(result["position"]["direction"], -1)
        self.assertEqual([f["side"] for f in reversed(result["fills"])], ["buy", "sell", "sell_short"])

    def test_policy_thresholds_and_exit_ignore_entry_confidence(self):
        execution = simulation.Execution(allow_short=True, min_confidence=.8)
        for score in (59.9, 20., 0., None, -59.9):
            self.assertEqual(council.target(0, score, execution, .99), 0)
        self.assertEqual(council.target(0, 60, execution, .8), 1)
        self.assertEqual(council.target(0, -60, execution, .8), -1)
        self.assertEqual(council.target(1, -20, execution, None), 0)
        self.assertEqual(council.target(-1, 20, execution, None), 0)
        self.assertEqual(council.target(1, None, execution, .99), 1)

    def test_first_execution_open_is_strictly_after_observation(self):
        first = self.tick(0)
        self.assertEqual(first["pending"]["execute_bar"], BASE + 60)
        self.assertIsNone(self.tick(1)["position"])
        filled = self.tick(2)
        self.assertEqual(filled["position"]["entered_at"], BASE + 60)
        self.assertGreater(filled["position"]["entered_at"], first["last_observation"]["observed_at"])

    def test_expiry_at_fill_prevents_entry_even_when_new_votes_arrive_later(self):
        self.tick(0, 100, expires=BASE + 30)
        result = self.tick(2, 100)
        self.assertIsNone(result["position"])
        self.assertEqual(result["fills"], [])
        self.assertIn("expired", result["last_action"]["reason"])

    def test_new_unavailable_observation_before_fill_prevents_entry(self):
        self.tick(0)
        at = BASE + 30
        council.step(now=at, snapshot={"rows": []}, quote={"source": "jupiter", "price": 100, "fetched_at": at},
                     bars=bars(at), recover=self.recovered.append)
        result = self.tick(2)
        self.assertIsNone(result["position"])
        self.assertIn("unavailable", result["last_action"]["reason"])

    def test_expired_reversal_still_closes_original_position(self):
        council.config({"execution": {"allow_short": True}})
        self.enter()
        self.tick(3, -100, expires=BASE + 3 * 60 + 30)
        result = self.tick(5, None)
        self.assertIsNone(result["position"])
        self.assertEqual(len(result["fills"]), 2)
        self.assertIn("expired", result["last_action"]["reason"])

    def test_same_vote_poll_is_frozen_and_shadow_outcomes_do_not_multiply(self):
        first = self.tick(0)
        for _ in range(15):
            self.tick(0)
        with sqlite3.connect(council.root() / "paper.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM observation").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM shadow").fetchone()[0], 1)
            frozen = json.loads(db.execute("SELECT document FROM observation").fetchone()[0])
        self.assertEqual(frozen, first["last_observation"])
        result = self.tick(2)
        self.assertEqual(len(result["fills"]), 1)
        self.assertEqual(result["confidence_samples"], 1)

    def test_confidence_warms_only_from_prior_recorded_outcomes(self):
        council.config({"execution": {"min_confidence": .8}})
        for minute in range(21):
            result = self.tick(minute)
            self.assertIsNone(result["position"])
            if result["confidence_samples"] < 20:
                self.assertIsNone(result["pending"])
        result = self.tick(21)
        self.assertEqual(result["confidence_samples"], 20)
        self.assertAlmostEqual(result["confidence"], simulation.confidence_score(20, 20))
        self.assertIsNotNone(result["pending"])

    def test_one_minute_votes_train_after_expiry_but_cannot_enter_at_expired_future_open(self):
        council.config({"execution": {"min_confidence": .8}})
        for minute in range(24):
            now = BASE + minute * 60 + 5
            eligible = [{key.replace("30m", "1m"): value for key, value in row.items()}
                        for row in rows(100, expires=BASE + (minute + 1) * 60)]
            for row in eligible:
                row["issued_1m"] = BASE + minute * 60
            result = council.step(now=now, snapshot={"rows": eligible},
                                  quote={"source": "jupiter", "price": 100, "fetched_at": now},
                                  bars=bars(now), recover=self.recovered.append)
            self.assertIsNone(result["position"])
        self.assertGreaterEqual(result["confidence_samples"], 20)
        self.assertGreater(result["confidence"], .8)
        self.assertEqual(result["fills"], [])
        self.assertIn("1m-only", result["last_action"]["reason"])
        with sqlite3.connect(council.root() / "paper.sqlite3") as db:
            original = json.loads(db.execute("SELECT document FROM observation ORDER BY observed LIMIT 1").fetchone()[0])
        self.assertEqual(original["rows"][0]["expires_1m"], BASE + 60)

    def test_fee_slippage_borrow_and_leverage_match_shared_simulation(self):
        cfg = council.config({"execution": {"use_leverage": True, "leverage": 5, "fee_bps": 7,
                                            "slippage_bps": 3, "borrow_long_bps_hour": 2}})
        result = self.enter()
        expected = simulation.settle(simulation.Execution(**cfg["execution"]), 1, [(100., 102., 100., 101.)])
        self.assertAlmostEqual(result["equity"] / cfg["capital"] - 1, expected["net_return"])
        self.assertGreater(result["position"]["notional"], cfg["capital"] * 4.9)
        self.assertGreater(result["position"]["borrow"], 0)
        self.assertGreater(result["fills"][0]["fees"], 0)
        self.assertGreater(result["fills"][0]["slippage"], 0)

    def test_pre_entry_wick_is_ignored_but_entry_bar_wick_liquidates(self):
        council.config({"execution": {"use_leverage": True, "leverage": 100}})
        safe = self.enter(overrides={BASE: (100., 102., 1., 101.), BASE + 60: (100., 100., 100., 100.)})
        self.assertIsNotNone(safe["position"], "A bar before entry cannot liquidate a future position")
        result = self.tick(3, overrides={BASE + 120: (100., 101., 98., 100.)})
        self.assertIsNone(result["position"])
        self.assertEqual(result["equity"], 0)
        self.assertTrue(result["halted"])
        self.assertTrue(result["fills"][0]["liquidated"])
        self.assertIsNone(self.tick(4)["pending"])

    def test_opening_gap_liquidates_before_queued_exit_or_reversal(self):
        council.config({"execution": {"use_leverage": True, "leverage": 10, "allow_short": True}})
        self.enter()
        self.tick(3, -100)
        result = self.tick(5, -100, overrides={BASE + 240: (80., 81., 79., 80.)})
        self.assertTrue(result["halted"])
        self.assertIsNone(result["position"])
        self.assertEqual(len(result["fills"]), 2)
        self.assertEqual(result["fills"][0]["reason"], "Liquidated at opening gap")

    def test_missing_bars_or_jupiter_quote_never_create_guessed_entries(self):
        result = self.tick(0, quote=False)
        self.assertIsNone(result["pending"])
        self.tick(1)
        now = BASE + 3 * 60 + 5
        missing = bars(now)
        missing = {k: v[missing["ts"] != BASE + 120] for k, v in missing.items()}
        result = council.step(now=now, snapshot={"rows": rows()}, quote={"source": "jupiter", "price": 100, "fetched_at": now},
                              bars=missing, recover=self.recovered.append)
        self.assertIsNone(result["position"])
        self.assertEqual(result["fills"], [])
        self.assertIn("missing", result["message"].lower())

    def test_old_unrelated_cache_gap_does_not_block_current_proxy_bar(self):
        now = BASE + 5
        raw = bars(now)
        raw = {k: v[raw["ts"] != BASE - 300] for k, v in raw.items()}
        result = council.step(now=now, snapshot={"rows": rows()}, quote={"source": "jupiter", "price": 100, "fetched_at": now},
                              bars=raw, recover=self.recovered.append)
        self.assertIsNotNone(result["pending"])

    def test_stop_preserves_position_and_cancels_unfilled_decision(self):
        opened = self.enter()
        self.tick(3, -20)
        self.assertIsNotNone(council.status()["pending"])
        stopped = council.stop()
        self.assertEqual(stopped["position"], opened["position"] | {"borrow": stopped["position"]["borrow"]})
        self.assertIsNone(stopped["pending"])
        self.assertEqual(council.status()["position"], stopped["position"])
        with self.assertRaisesRegex(ValueError, "paper position"):
            council.config({"asset": "ETH"})

    def test_cancellation_persists_no_partial_observation_or_fill(self):
        before = self.tick(0)
        stop = threading.Event()
        stop.set()
        now = BASE + 125
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            council.step(now=now, snapshot={"rows": rows()}, quote={}, bars=bars(now), stop=stop, recover=self.recovered.append)
        after = council.status()
        self.assertEqual(after["pending"], before["pending"])
        self.assertEqual(after["fills"], [])

    def test_start_races_have_one_inherited_owner_and_live_mode_is_rejected(self):
        inherited = []
        class Child:
            def wait(self):
                return 0
        def spawn(*args, **kwargs):
            inherited.append(os.dup(kwargs["pass_fds"][0]))
            return Child()
        try:
            with patch.object(council.subprocess, "Popen", side_effect=spawn) as start:
                with ThreadPoolExecutor(max_workers=6) as pool:
                    results = list(pool.map(lambda _: council.start(), range(6)))
            self.assertEqual(start.call_count, 1)
            self.assertTrue(all(r["running"] for r in results))
            with self.assertRaisesRegex(ValueError, "Stop Council"):
                council.config({"capital": 5})
        finally:
            for descriptor in inherited:
                os.close(descriptor)
        with self.assertRaises(ValueError):
            council.config({"mode": "live"})

    def test_actual_detached_paper_process_survives_caller_and_stops(self):
        council.config({"poll_seconds": 1})
        fixture = self.directory / "python-fixture"
        fixture.mkdir()
        (fixture / "sitecustomize.py").write_text('''\
import time
import numpy as np
from soltui import compound, live_price, live_score
def candles(asset, *, now, **kwargs):
    ts = (int(now) // 60 - 200 + np.arange(200)) * 60
    prices = np.full(200, 100.)
    return dict(ts=ts, open=prices, high=prices, low=prices, close=prices, volume=np.ones(200))
compound.fetch_closed_candles = candles
live_price.jupiter = lambda asset: dict(source='jupiter',price=100.,fetched_at=time.time())
def snapshot(asset, **kwargs):
    now = time.time()
    return dict(rows=[dict(label='fixture',accuracy=90.,resolved=40,pred_30m='UP',acc_30m=90.,resolved_30m=40,issued_30m=now-1,expires_30m=now+1800)])
live_score.prediction_snapshot = snapshot
''', encoding="utf-8")
        environment = {**os.environ, "SOLTUI_CONFIG_DIR": str(self.directory),
                       "PYTHONPATH": os.pathsep.join([str(fixture), str(council.REPO)])}
        caller = [sys.executable, "-c", "import json; from soltui import council; print(json.dumps(council.start()))"]
        try:
            result = subprocess.run(caller, env=environment, cwd=council.REPO, capture_output=True, text=True, timeout=10, check=True)
            self.assertTrue(json.loads(result.stdout)["running"])
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                state = council.status()
                if state["running"] and state["last_observation"]:
                    break
                time.sleep(.05)
            else:
                self.fail(f"Detached Council did not record its observation: {council.status()}")
            self.assertNotEqual(state["owner"]["pid"], os.getpid())
            self.assertEqual(state["mode"], "paper")
        finally:
            council.stop()
            deadline = time.monotonic() + 10
            while council.status()["running"] and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(council.status()["running"])
            self.assertIsNone(council.status()["pending"])


if __name__ == "__main__":
    unittest.main()
