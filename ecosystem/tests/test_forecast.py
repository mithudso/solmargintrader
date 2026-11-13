from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem import forecast
from ecosystem.forecast_preferences import set_seconds, settings


class Strategies:
    def predict(self, bars):
        if len(bars) < 3:
            return []
        return [
            {
                "strategy_id": key,
                "version": "a" * 64,
                "parameters": {},
                "direction": direction,
            }
            for key, direction in (("ma_crossover", 1), ("rsi", -1))
        ]


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.prices = self.home / "prices"
        self.prices.mkdir()
        self.worker = forecast.Worker(self.home, self.prices, strategies=Strategies())

    def quote(self, at, price=100):
        return {"at": at, "observed_at": at, "price": price}

    def seed(self, at=1000):
        for i in range(12):
            self.worker.bars.add(
                "SOL/USD", self.quote(at - 120 + 10 * i, 100 * 1.01**i)
            )
        self.worker.bars.add("SOL/USD", self.quote(at, 120))
        return {"SOL/USD": self.quote(at, 120)}

    def test_price_target_uses_chosen_strategy_and_observed_move_not_probability(self):
        self.worker.evaluate(self.seed(), 1000)
        up = forecast.report(self.home, "SOL/USD", strategy="ma_crossover", now=1001)
        down = forecast.report(self.home, "SOL/USD", strategy="rsi", now=1001)
        self.assertEqual(up["status"], "fresh")
        self.assertAlmostEqual(up["selected"]["predicted_price"], 121.2)
        self.assertAlmostEqual(down["selected"]["predicted_price"], 120 / 1.01)
        self.assertEqual(
            (up["issued_at"], up["target_at"], up["horizon_seconds"]), (1000, 1010, 10)
        )
        self.assertEqual(up["input_bar_seconds"], 10)
        self.assertIsNone(up["selected"]["accuracy_percent"])
        self.assertFalse(up["selected"]["qualified"])
        self.assertEqual(up["execution_authority"], "none")

    def test_only_timely_future_outcomes_rank_and_resolved_accuracy_is_separate(self):
        self.worker.evaluate(self.seed(), 1000)
        (self.prices / "latest.json").write_text(
            json.dumps({"t": 1010.5, "q": {"SOL-USD": [118, 118, 118, 1, 1, 1010.5]}})
        )
        quotes = self.worker.sample(1010.5)
        self.worker.evaluate(quotes, 1010.5)
        view = forecast.report(self.home, "SOL/USD", now=1011)
        self.assertEqual(view["selected"]["strategy_id"], "rsi")
        self.assertEqual(
            (view["selected"]["hits"], view["selected"]["resolved"]), (1, 1)
        )
        self.assertFalse(view["selected"]["qualified"])
        self.assertEqual(view["selected"]["ranking_basis"], "recent_prospective_calls")
        # A quote twenty seconds after another target cannot credit an outcome.
        (self.prices / "latest.json").write_text(
            json.dumps({"t": 1040, "q": {"SOL-USD": [119, 119, 119, 1, 1, 1040]}})
        )
        self.worker.sample(1040)
        with closing(forecast.connect(self.worker.path, readonly=True)) as db:
            self.assertTrue(
                db.execute(
                    "SELECT count(*) FROM calls WHERE settled=1040 AND hit IS NULL"
                ).fetchone()[0]
            )

    def test_outage_restart_and_warmup_preserve_exact_last_selected_forecast(self):
        self.worker.evaluate(self.seed(), 1000)
        before = forecast.report(self.home, "SOL/USD", strategy="rsi", now=1001)
        restarted = forecast.Worker(self.home, self.prices, strategies=Strategies())
        self.assertEqual(restarted.sample(1100), {})
        restarted.evaluate({}, 1100)
        after = forecast.report(self.home, "SOL/USD", strategy="rsi", now=1100)
        self.assertEqual(after["status"], "retained")
        self.assertEqual(after["age_seconds"], 100)
        self.assertEqual(after["selected"], before["selected"])
        self.assertEqual(after["issued_at"], before["issued_at"])
        self.assertEqual(
            forecast.report(self.home, "ZEC/USD", now=1100)["status"], "waiting"
        )
        self.assertEqual(
            forecast.report(self.home, "SOL/USDT", now=1100)["status"], "waiting"
        )

    def test_policy_and_instrument_bindings_and_same_slot_deduplication(self):
        self.worker.evaluate(self.seed(), 1000)
        before = forecast.report(self.home, "SOL/USD", now=1001)
        self.worker.evaluate({"SOL/USD": self.quote(1005, 200)}, 1005)
        self.assertEqual(
            forecast.report(self.home, "SOL/USD", now=1006)["reference_price"],
            before["reference_price"],
        )
        with closing(forecast.connect(self.worker.path)) as db, db:
            row = json.loads(
                db.execute("SELECT body FROM frames WHERE horizon=10").fetchone()[0]
            )
            row["instrument"] = "ZEC/USD"
            db.execute("UPDATE frames SET body=? WHERE horizon=10", (json.dumps(row),))
        self.assertEqual(
            forecast.report(self.home, "SOL/USD", now=1007)["status"], "waiting"
        )

    def test_selected_long_warmup_strategy_survives_other_strategies_restarting(self):
        self.worker.evaluate(self.seed(), 1000)
        before = forecast.report(self.home, "SOL/USD", strategy="rsi", now=1001)

        class OnlyMa:
            def predict(self, bars):
                return [Strategies().predict(bars)[0]]

        self.worker.strategies = OnlyMa()
        self.worker.bars.add("SOL/USD", self.quote(1010, 121))
        self.worker.evaluate({"SOL/USD": self.quote(1010, 121)}, 1010)
        after = forecast.report(self.home, "SOL/USD", strategy="rsi", now=1030)
        self.assertEqual(after["status"], "retained")
        self.assertEqual(after["issued_at"], before["issued_at"])
        self.assertEqual(
            after["selected"]["predicted_price"], before["selected"]["predicted_price"]
        )

    def test_no_recent_move_is_flat_and_the_exact_numeric_projection_is_recorded(self):
        for at in range(880, 1001, 10):
            self.worker.bars.add("SOL/USD", self.quote(at, 100))
        self.worker.evaluate({"SOL/USD": self.quote(1000)}, 1000)
        view = forecast.report(self.home, "SOL/USD", now=1001)
        self.assertEqual(view["selected"]["strategy_direction"], 1)
        self.assertEqual(view["selected"]["direction"], 0)
        self.assertEqual(view["selected"]["predicted_price"], 100)
        with closing(forecast.connect(self.worker.path, readonly=True)) as db:
            saved = db.execute(
                "SELECT direction,projected FROM calls WHERE instrument='SOL/USD' AND horizon=10 AND strategy='ma_crossover'"
            ).fetchone()
        self.assertEqual(tuple(saved), (0, 100))

    def test_readonly_missing_view_never_creates_storage(self):
        missing = self.home / "missing"
        self.assertEqual(forecast.report(missing, "SOL/USD")["status"], "waiting")
        self.assertFalse(missing.exists())

    def variable_seed(self):
        for second in range(400, 1001):
            self.worker.bars.add(
                "SOL/USD", self.quote(second, 100 * 1.001 ** (second - 400))
            )
        return {"SOL/USD": self.quote(1000, 120)}

    def test_arbitrary_seconds_are_persistent_revisioned_and_have_exact_inputs(self):
        self.assertEqual(settings(self.home, "SOL/USD")["seconds"], 10)
        saved = set_seconds(self.home, "SOL/USD", 17, 0)
        self.assertEqual(saved["revision"], 1)
        with self.assertRaisesRegex(ValueError, "revision_conflict"):
            set_seconds(self.home, "SOL/USD", 25, 0)
        self.worker.evaluate(self.variable_seed(), 1000)
        view = forecast.report(self.home, "SOL/USD", horizon=17, now=1001)
        self.assertEqual(
            (view["horizon_seconds"], view["refresh_seconds"], view["target_at"]),
            (17, 17, 1017),
        )
        self.assertAlmostEqual(view["selected"]["predicted_price"], 120 * 1.001**17)
        trace = forecast.read_trace(self.home, view["input_trace_id"])
        self.assertEqual(len(trace["bars"]), view["input_bars"])
        self.assertTrue(
            all(
                pair["to_second"] - pair["from_second"] == 17
                for pair in trace["move_pairs"]
            )
        )
        self.assertEqual(
            hashlib.sha256(forecast.canonical(trace).encode()).hexdigest(),
            view["input_trace_id"],
        )
        before = view["issued_at"]
        self.worker.evaluate({"SOL/USD": self.quote(1016, 121)}, 1016)
        self.assertEqual(
            forecast.report(self.home, "SOL/USD", horizon=17, now=1016)["issued_at"],
            before,
        )
        self.worker.bars.add("SOL/USD", self.quote(1017, 121))
        self.worker.evaluate({"SOL/USD": self.quote(1017, 121)}, 1017)
        self.assertEqual(
            forecast.report(self.home, "SOL/USD", horizon=17, now=1017)["issued_at"],
            1017,
        )
        self.assertEqual(settings(self.home, "SOL/USD")["seconds"], 17)
        self.assertEqual(settings(self.home, "ZEC/USD")["seconds"], 10)

    def test_long_interval_is_current_with_live_source_and_retained_on_source_loss(
        self,
    ):
        set_seconds(self.home, "SOL/USD", 300, 0)
        self.worker.evaluate(self.variable_seed(), 1000)
        (self.prices / "latest.json").write_text(
            json.dumps({"t": 1200, "q": {"SOL-USD": [120, 120, 120, 1, 1, 1200]}})
        )
        with patch("ecosystem.forecast.os.getpid", return_value=45678):
            self.worker.sample(1200)
        current = forecast.report(self.home, "SOL/USD", horizon=300, now=1201)
        self.assertEqual(current["status"], "fresh")
        self.assertEqual(current["issued_at"], 1000)
        self.assertTrue(current["source_current"])
        self.assertEqual(current["owner_pid"], 45678)
        self.assertNotEqual(current["issuer_pid"], 45678)
        retained = forecast.report(self.home, "SOL/USD", horizon=300, now=1220)
        self.assertEqual(retained["status"], "retained")
        self.assertIsNone(retained["owner_pid"])
        self.assertEqual(
            retained["selected"]["predicted_price"],
            current["selected"]["predicted_price"],
        )

    def test_invalid_seconds_never_write_settings(self):
        for value in (True, 4, 301, 10.5, "17", None):
            with self.assertRaises(ValueError):
                set_seconds(self.home, "SOL/USD", value, 0)
        self.assertFalse((self.home / "forecast-preferences.sqlite3").exists())

    def test_snapshot_rejects_stale_future_crossed_and_nonfinite_inputs(self):
        raw = {"t": 1000, "q": {"SOL-USD": [99, 101, 100, 1, 1, 1000]}}
        self.assertEqual(forecast.snapshot(raw, 1001)["SOL/USD"]["price"], 100)
        self.assertEqual(forecast.snapshot(raw, 1020), {})
        self.assertEqual(forecast.snapshot(raw, 999), {})
        for quote in (
            [101, 99, 100, 1, 1, 1000],
            [99, 101, 100, 1, 1, 900],
            [False, 101, 100, 1, 1, 1000],
            [99, float("nan"), 100, 1, 1, 1000],
        ):
            self.assertEqual(
                forecast.snapshot({"t": 1000, "q": {"SOL-USD": quote}}, 1000), {}
            )
        self.assertFalse(forecast.finite(10**400))

    def test_recorder_tail_keeps_only_crc_valid_complete_members_and_never_edits(self):
        path = self.prices / "sample.gz"
        first = gzip.compress(b'{"t":1}\n')
        second = gzip.compress(b'{"t":2}\n')
        tail = gzip.compress(b'{"t":3}\n')[:-4]
        raw = b"unrelated-prefix" + first + second + tail
        path.write_bytes(raw)
        before = hashlib.sha256(raw).hexdigest()
        self.assertEqual(list(forecast.history_tail(path)), [{"t": 1}, {"t": 2}])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_fixed_deadline_does_not_add_work_duration_or_catch_up_bursts(self):
        self.assertEqual(forecast.next_deadline(100, 101.5), 110)
        self.assertEqual(forecast.next_deadline(110, 111.8), 120)
        self.assertEqual(forecast.next_deadline(120, 143), 150)

    def test_missing_bucket_resets_strategy_inputs_instead_of_forward_filling(self):
        for at in (900, 910, 930, 940):
            self.worker.bars.add("SOL/USD", self.quote(at))
        self.assertEqual(
            [row["ts"] for row in self.worker.bars.completed("SOL/USD", 950)],
            [930, 940],
        )


if __name__ == "__main__":
    unittest.main()
