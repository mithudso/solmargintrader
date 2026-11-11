"""Future-only decisions, atomic books and current-cost paper comparators."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from ecosystem import meta_forward as m


class MetaForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "cohort"
        self.now = 864000 + 10
        self.last = self.now // m.STEP * m.STEP - m.STEP
        self.seeds = {}
        for asset in m.ASSETS:
            ts = np.arange(self.last - 239 * m.STEP, self.last + m.STEP, m.STEP)
            close = np.full(240, 100.0)
            if asset == "ZEC":
                close[-1] = 200
            self.seeds[asset] = {"ts": ts, "open": np.full(240, 100.0), "high": close + 1,
                                 "low": np.full(240, 99.0), "close": close, "volume": np.ones(240)}

    def initialize(self, **kwargs):
        return m.initialize(self.home, now=self.now, fetcher=lambda asset, *_: self.seeds[asset], clock=lambda: self.now, **kwargs)

    def activate(self):
        return m.activate(self.home, now=self.now, clock=lambda: self.now)

    def new_data(self, asset, number):
        price = 200.0 if asset == "ZEC" else 100.0
        return {"ts": np.array([self.last + number * m.STEP]), "open": np.array([price]),
                "high": np.array([price + 1]), "low": np.array([price - 1]),
                "close": np.array([price]), "volume": np.array([1.0])}

    def tick(self, number, **kwargs):
        now = self.last + (number + 1) * m.STEP + 5
        return m.tick(self.home, now=now, fetcher=lambda asset, *_: self.new_data(asset, number), clock=lambda: now, **kwargs)

    @staticmethod
    def account(value, identity):
        return next(a for a in value["accounts"] if a["id"] == identity)

    def test_initialize_is_prepared_and_historical_rally_is_not_profit(self):
        value = self.initialize()
        self.assertEqual(value["cohort"]["status"], "prepared")
        self.assertEqual(value["counts"]["trades"], 0)
        self.assertTrue(all(a["equity"] == 10000 for a in value["accounts"]))
        self.assertIsNone(value["latest_decision"])
        with patch.object(m, "fetch_closed") as fetch:
            m.tick(self.home, now=self.now, fetcher=fetch)
        fetch.assert_not_called()

    def test_activation_commits_future_decision_and_never_fills_old_candles(self):
        self.initialize()
        value = self.activate()
        decision = value["latest_decision"]
        self.assertGreater(decision["effective"], decision["durable_at"])
        self.assertEqual(decision["document"]["completed_bar_marks"]["ZEC"], 200)
        self.assertTrue(decision["document"]["reference_only"])
        self.assertEqual(value["counts"]["trades"], 0)
        first = self.tick(1)
        self.assertEqual(first["counts"]["trades"], 0)
        self.assertTrue(all(a["equity"] == 10000 for a in first["accounts"]))
        second = self.tick(2)
        self.assertGreater(second["counts"]["trades"], 0)
        with m.connection(self.home) as db:
            trades = [json.loads(r[0]) for r in db.execute("SELECT details FROM trades")]
        self.assertTrue(all(t["ts"] >= decision["effective"] for t in trades))
        self.assertTrue(all(t["side"] == "long" and t["reference_only"] for t in trades))

    def test_actual_taker_fee_known_answer_and_same_clock_cash_benchmark(self):
        self.initialize()
        self.activate()
        self.tick(1)
        value = self.tick(2)
        account = self.account(value, "hold_zec_taker_primary")
        expected = 10000 / 1.0092
        self.assertAlmostEqual(account["equity"], expected, places=8)
        self.assertGreater(account["fees"], 80)
        self.assertGreater(account["slippage"], 0)
        self.assertAlmostEqual(account["estimated_net_liquidation_equity"], expected * (1 - 0.0092), places=8)
        self.assertAlmostEqual(self.account(value, "hold_core_taker_primary")["equity"], expected, places=8)
        self.assertEqual(self.account(value, "cash_taker_primary")["equity"], 10000)
        self.assertGreater(self.account(value, "hold_zec_maker_cost_sensitivity")["equity"], account["equity"])

    def test_risk_scaled_passive_weight_is_frozen_and_preserves_idle_cash(self):
        self.initialize(passive_zec_weight=0.25)
        self.activate()
        self.tick(1)
        value = self.tick(2)
        sized = self.account(value, "sized_hold_zec_taker_primary")
        self.assertAlmostEqual(sized["equity"], 7500 + 2500 / 1.0092, places=8)
        self.assertAlmostEqual(sized["cash"], 7500)
        with m.connection(self.home, write=True) as db, self.assertRaisesRegex(sqlite3.IntegrityError, "immutable_paper_metadata"):
            db.execute("UPDATE metadata SET value='0.5' WHERE key='config'")

    def test_scaled_passive_keeps_initial_units_as_price_drifts(self):
        self.initialize(passive_zec_weight=0.4793342110254035)
        self.activate()
        self.tick(1)
        before = self.tick(2)
        original = self.account(before, "sized_hold_zec_taker_primary")
        for number in (3, 4):
            now = self.last + (number + 1) * m.STEP + 5
            def feed(asset, *_, number=number):
                data = self.new_data(asset, number)
                if asset == "ZEC":
                    data["open"][:] = 200 if number == 3 else 400
                    data["high"][:] = 401
                    data["low"][:] = 199 if number == 3 else 399
                    data["close"][:] = 400
                return data
            after = m.tick(self.home, now=now, clock=lambda now=now: now, fetcher=feed)
        final = self.account(after, "sized_hold_zec_taker_primary")
        self.assertEqual(final["fills"], 1)
        self.assertEqual(final["fees"], original["fees"])
        self.assertAlmostEqual(final["cash"], original["cash"], places=8)
        self.assertAlmostEqual(final["equity"], original["cash"] + 2 * (original["equity"] - original["cash"]), places=8)

    def test_seed_boundary_excludes_protected_values_before_validation_and_features(self):
        boundary = self.last - 50 * m.STEP
        for seed in self.seeds.values():
            old = seed["ts"] < boundary
            for key in m.KEYS[1:]:
                seed[key][old] = np.nan
        requested = []
        def feed(asset, after, now):
            requested.append(after)
            return self.seeds[asset]
        value = m.initialize(self.home, now=self.now, seed_not_before=boundary, fetcher=feed, clock=lambda: self.now)
        self.activate()
        with m.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT min(bar) FROM candles").fetchone()[0], boundary)
            metadata = m._metadata(db)
        self.assertEqual(metadata["seed_not_before"], boundary)
        self.assertEqual(requested, [boundary - m.STEP] * 3)
        self.assertTrue(all(row["bars"] == 51 for row in metadata["seed_bounds"].values()))
        self.assertEqual(value["counts"]["trades"], 0)

    def test_duplicate_ticks_and_restart_do_not_duplicate_trades_or_change_books(self):
        self.initialize()
        self.activate()
        self.tick(1)
        first = self.tick(2)
        now = self.last + 3 * m.STEP + 10
        with patch.object(m, "fetch_closed") as fetch:
            second = m.tick(self.home, now=now, clock=lambda: now, fetcher=fetch)
        fetch.assert_not_called()
        self.assertEqual(first["counts"], second["counts"])
        self.assertEqual(first["accounts"], second["accounts"])
        third = self.tick(3)
        self.assertEqual(first["counts"]["trades"], third["counts"]["trades"])

    def test_crash_after_preparation_cannot_activate_stale_seed(self):
        self.initialize()
        late = self.last + 2 * m.STEP
        with self.assertRaisesRegex(ValueError, "prepared_seed_stale"):
            m.activate(self.home, now=late, clock=lambda: late)
        self.assertEqual(m.report(self.home, now=late)["counts"]["trades"], 0)

    def test_crash_after_activation_commit_cannot_confirm_on_restart(self):
        self.initialize()
        with patch.object(m, "_confirm", side_effect=RuntimeError("crash_after_durable_decision")), self.assertRaisesRegex(RuntimeError, "crash_after_durable_decision"):
            self.activate()
        with patch.object(m, "fetch_closed") as fetch:
            value = m.tick(self.home, now=self.now + 1, clock=lambda: self.now + 1, fetcher=fetch)
        fetch.assert_not_called()
        self.assertEqual(value["cohort"]["reason"], "unconfirmed_decision")
        self.assertEqual(value["counts"]["confirmations"], 0)
        self.assertEqual(value["counts"]["trades"], 0)

    def test_commit_delay_cannot_backdate_confirmation(self):
        self.initialize()
        original = m._confirm
        def delayed(home, effective, _):
            return original(home, effective, effective + 1)
        with patch.object(m, "_confirm", side_effect=delayed):
            value = self.activate()
        self.assertEqual(value["cohort"]["reason"], "missed_decision_window")
        self.assertEqual(value["counts"]["confirmations"], 0)
        self.assertEqual(value["counts"]["trades"], 0)

    def test_real_database_commit_delay_leaves_activation_ineligible(self):
        self.initialize()
        connect = sqlite3.connect
        instant = [self.now]
        delayed = []
        class DelayedCommit(sqlite3.Connection):
            def commit(self):
                result = super().commit()
                if not delayed:
                    delayed.append(True)
                    instant[0] += 2 * m.STEP
                return result
        with patch.object(m.sqlite3, "connect", side_effect=lambda *a, **k: connect(*a, factory=DelayedCommit, **k)):
            value = m.activate(self.home, now=self.now, clock=lambda: instant[0])
        self.assertTrue(delayed)
        self.assertEqual(value["cohort"]["reason"], "missed_decision_window")
        self.assertEqual(value["counts"]["confirmations"], 0)
        self.assertEqual(value["counts"]["trades"], 0)

    def test_lock_wait_crossing_deadline_rolls_back_tick(self):
        self.initialize()
        self.activate()
        self.tick(1)
        before = m.report(self.home, now=self.now)
        connect = sqlite3.connect
        instant = [self.last + 3 * m.STEP + 5]
        delayed = []
        class DelayedLock(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                result = super().execute(sql, *args, **kwargs)
                if sql == "BEGIN IMMEDIATE" and not delayed:
                    delayed.append(True)
                    instant[0] += 2 * m.STEP
                return result
        with patch.object(m.sqlite3, "connect", side_effect=lambda *a, **k: connect(*a, factory=DelayedLock, **k)):
            value = m.tick(self.home, now=instant[0], clock=lambda: instant[0], fetcher=lambda asset, *_: self.new_data(asset, 2))
        self.assertTrue(delayed)
        self.assertEqual(value["cohort"]["reason"], "missed_decision_window")
        self.assertEqual(value["accounts"], before["accounts"])
        self.assertEqual(value["counts"]["trades"], 0)

    def test_crash_after_tick_commit_preserves_book_but_blocks_future_eligibility(self):
        self.initialize()
        self.activate()
        self.tick(1)
        with patch.object(m, "_confirm", side_effect=RuntimeError("crash_after_tick_commit")), self.assertRaisesRegex(RuntimeError, "crash_after_tick_commit"):
            self.tick(2)
        before = m.report(self.home, now=self.last + 3 * m.STEP + 5)
        value = self.tick(3)
        self.assertEqual(value["cohort"]["reason"], "unconfirmed_decision")
        self.assertEqual(before["accounts"], value["accounts"])
        self.assertEqual(before["counts"]["trades"], value["counts"]["trades"])

    def test_missed_window_never_backfills_two_candles(self):
        self.initialize()
        self.activate()
        now = self.last + 3 * m.STEP + 5
        def feed(asset, *_):
            return {k: np.concatenate([self.new_data(asset, n)[k] for n in (1, 2)]) for k in m.KEYS}
        value = m.tick(self.home, now=now, clock=lambda: now, fetcher=feed)
        self.assertEqual(value["cohort"]["reason"], "missed_decision_window")
        self.assertEqual(value["counts"]["trades"], 0)
        with m.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM candles").fetchone()[0], 720)

    def test_source_revision_is_refused_before_accounting(self):
        self.initialize()
        self.activate()
        now = self.last + 2 * m.STEP + 5
        def feed(asset, *_):
            old = {k: x[-1:].copy() for k, x in self.seeds[asset].items()}
            old["volume"][0] += 10
            return {k: np.r_[old[k], self.new_data(asset, 1)[k]] for k in m.KEYS}
        value = m.tick(self.home, now=now, clock=lambda: now, fetcher=feed)
        self.assertEqual(value["cohort"]["reason"], "source_candle_changed")
        self.assertEqual(value["counts"]["trades"], 0)

    def test_implementation_change_blocks_before_feed_or_fills(self):
        self.initialize()
        self.activate()
        with patch.object(m, "implementation", return_value={"changed": "yes"}), patch.object(m, "fetch_closed") as feed:
            value = m.tick(self.home, now=self.now, clock=lambda: self.now, fetcher=feed)
        feed.assert_not_called()
        self.assertEqual(value["cohort"]["reason"], "implementation_changed")

    def test_single_writer_lock_excludes_ticks(self):
        self.initialize()
        self.activate()
        with m.owner(self.home), self.assertRaises(BlockingIOError):
            m.tick(self.home, now=self.now)

    def test_transient_feed_failure_can_retry_only_before_missed_window(self):
        self.initialize()
        self.activate()
        now = self.last + 2 * m.STEP + 5
        value = m.tick(self.home, now=now, clock=lambda: now, fetcher=lambda *_: None)
        self.assertEqual(value["cohort"]["reason"], "feed_temporarily_unavailable")
        self.assertNotEqual(value["cohort"]["status"], "blocked")
        value = self.tick(1)
        self.assertIsNone(value["cohort"]["reason"])
        self.assertEqual(value["counts"]["trades"], 0)

    def test_config_bytes_are_pinned_and_never_overwritten(self):
        config = Path(self.tmp.name) / "config.json"
        raw = json.dumps(m.default_config(), indent=3)
        config.write_text(raw)
        self.initialize(config=config)
        with m.connection(self.home) as db:
            metadata = m._metadata(db)
        self.assertEqual(metadata["config_bytes"], raw)
        with self.assertRaises(FileExistsError):
            self.initialize()
        value = m.default_config()
        value["accounts"][0]["sleeves"][0]["weight"] = 1.1
        with self.assertRaisesRegex(ValueError, "unlevered"):
            m.validate_config(value)

    def test_account_configuration_cannot_drift_from_frozen_bytes(self):
        self.initialize()
        self.activate()
        with m.connection(self.home, write=True) as db, self.assertRaisesRegex(sqlite3.IntegrityError, "immutable_paper_account_spec"):
            db.execute("UPDATE accounts SET spec='{}'")
        with m.connection(self.home, write=True) as db:
            db.execute("DROP TRIGGER immutable_account_spec")
            row = db.execute("SELECT id,spec FROM accounts LIMIT 1").fetchone()
            altered = json.loads(row[1])
            altered["fee_bps"] = 0
            db.execute("UPDATE accounts SET spec=? WHERE id=?", (json.dumps(altered), row[0]))
        value = m.tick(self.home, now=self.now, clock=lambda: self.now)
        self.assertFalse(value["configuration_valid"])
        self.assertEqual(value["cohort"]["reason"], "configuration_changed")
        self.assertEqual(value["counts"]["trades"], 0)


if __name__ == "__main__":
    unittest.main()
