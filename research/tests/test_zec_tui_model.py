"""Evidence isolation, indicator math, source windows and editable preferences."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from research import zec_live as live
from research.zec_tui_model import WorkingSet, market_details, row_key, validate_config
from research.zec_tui_source import Cancelled, DataSession, live_view


def original(interval="1m", candidate="rsi-test"):
    return {
        "interval": interval,
        "candidate_id": candidate,
        "mode": "baseline",
        "family": "rsi",
        "market": "spot_reference",
        "config": {
            "members": [
                {
                    "strategy": "rsi",
                    "params": {"period": 3, "oversold": 30, "exit_level": 60},
                }
            ],
            "mode": "single",
            "persistence": 1,
            "rebalance_threshold": 0.0,
        },
        "historical": {"15": {"return_pct": 2.0, "fills": 4}},
        "winning_fee_bps": [15],
    }


def candles(count=100, step=60):
    return {
        i * step: {
            "ts": i * step,
            "open": 100.0 + i,
            "high": 102.0 + i,
            "low": 99.0 + i,
            "close": 100.6 + i,
            "volume": 10.0 + i,
        }
        for i in range(count)
    }


class Editing(unittest.TestCase):
    def test_default_is_focused_but_full_universe_is_selectable(self):
        state = WorkingSet()
        self.assertEqual((state.interval, state.mode), ("1m", "baseline"))
        self.assertEqual(len(state.visible()), 6)
        self.assertEqual(len(state.originals), 908)
        state.interval = "5m"
        self.assertEqual(len(state.visible()), 6)

    def test_each_original_configuration_can_be_saved_without_becoming_a_variant(self):
        state = WorkingSet()
        for identity in state.originals:
            state.edit(identity, live.canonical(state.editor_config(identity)))
        self.assertFalse(state.overrides)

    def test_edit_isolated_parameters_never_inherit_winning_return(self):
        baseline = original()
        state = WorkingSet([baseline])
        identity = row_key(baseline)
        config = state.editor_config(identity)
        config["members"][0]["params"]["period"] = 5
        state.edit(identity, json.dumps(config))
        edited = state.effective(identity)
        self.assertTrue(edited["edited"])
        self.assertEqual(edited["historical"], {})
        self.assertEqual(edited["winning_fee_bps"], [])
        self.assertNotEqual(edited["candidate_id"], baseline["candidate_id"])
        self.assertEqual(state.originals[identity], baseline)
        self.assertEqual(baseline["config"]["members"][0]["params"]["period"], 3)
        state.overrides.pop(identity)
        self.assertEqual(state.effective(identity), baseline)

    def test_bad_edit_preserves_last_valid_variant(self):
        state = WorkingSet([original()])
        identity = next(iter(state.originals))
        good = state.editor_config(identity)
        good["members"][0]["params"]["period"] = 6
        state.edit(identity, json.dumps(good))
        saved = copy.deepcopy(state.overrides)
        for value in (
            "{bad",
            '{"members":[],"mode":"single"}',
            '{"members":[{"strategy":"rsi","params":{"period":0}}],"mode":"single"}',
            '{"members":[{"strategy":"rsi","params":{"period":NaN}}],"mode":"single"}',
        ):
            with (
                self.subTest(value=value),
                self.assertRaises((ValueError, TypeError, KeyError)),
            ):
                state.edit(identity, value)
            self.assertEqual(state.overrides, saved)

    def test_valid_boolean_parameter_is_not_rejected_as_a_number(self):
        cfg = {
            "members": [
                {"strategy": "ma_crossover", "params": {"short_when_below": False}}
            ],
            "mode": "single",
        }
        self.assertFalse(
            validate_config(cfg)["members"][0]["params"]["short_when_below"]
        )

    def test_private_preferences_roundtrip_keeps_manual_empty_selection(self):
        state = WorkingSet([original()])
        state.interval, state.refresh, state.lookback = "5m", 2.0, 192
        state.selected.clear()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.json"
            state.save(path)
            loaded = WorkingSet([original()])
            loaded.load(path)
            self.assertEqual(
                (loaded.interval, loaded.refresh, loaded.lookback), ("5m", 2.0, 192)
            )
            self.assertFalse(loaded.selected)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_corrupt_preferences_and_symlink_do_not_replace_user_data(self):
        state = WorkingSet([original()])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.json"
            path.write_text('{"version":1,"study_csv_sha256":"wrong"}')
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                state.load(path)
            self.assertEqual(path.read_bytes(), before)
            target = Path(directory) / "other.json"
            target.write_text("preserve")
            linked = Path(directory) / "linked.json"
            linked.symlink_to(target)
            with self.assertRaises(ValueError):
                state.save(linked)
            self.assertEqual(target.read_text(), "preserve")


class MarketDetails(unittest.TestCase):
    def test_balance_of_power_and_roc_have_correct_units(self):
        details = market_details(candles(100), "1m", 6000)
        values = {r["name"]: r["value"] for r in details["indicators"]}
        self.assertAlmostEqual(values["Balance of power"], 0.2)
        self.assertAlmostEqual(values["ROC20 %"], 100 * (199.6 / 179.6 - 1))
        self.assertEqual(values["RSI 14"], 100)
        self.assertTrue(0 <= details["shape"]["range_position"] <= 1)
        self.assertGreaterEqual(details["shape"]["episode_age_bars"], 1)

    def test_gap_resets_indicators_instead_of_emitting_neutral_defaults(self):
        rows = candles(100)
        del rows[96 * 60]
        details = market_details(rows, "1m", 6000)
        values = {r["name"]: r["value"] for r in details["indicators"]}
        self.assertIsNone(values["RSI 14"])
        self.assertIsNone(values["MACD histogram"])
        self.assertEqual(details["contiguous_bars"], 3)
        self.assertEqual(len(details["chart"]), 3)
        self.assertEqual(details["shape"]["shape"], "unknown")

    def test_future_prices_cannot_change_current_indicators_or_shape(self):
        rows = candles(120)
        before = market_details(rows, "1m", 6000)
        for stamp, bar in rows.items():
            if stamp >= 6000:
                bar.update(close=99999, low=1, high=999999, volume=999999)
        self.assertEqual(market_details(rows, "1m", 6000), before)

    def test_chart_lookback_never_changes_indicator_input(self):
        rows = candles(320)
        short = market_details(rows, "1m", 320 * 60, 48)
        longer = market_details(rows, "1m", 320 * 60, 300)
        self.assertEqual(short["indicators"], longer["indicators"])
        self.assertEqual(short["shape"], longer["shape"])
        self.assertEqual((len(short["chart"]), len(longer["chart"])), (48, 300))

    def test_selected_rsi_period_is_displayed_with_its_actual_number(self):
        cfg = original()["config"]
        details = market_details(candles(100), "1m", 6000, configs=[cfg])
        values = {r["name"]: r["value"] for r in details["indicators"]}
        self.assertEqual(values["RSI 3"], 100)

    def test_selected_bollinger_uses_its_own_window_and_band_width(self):
        cfg = {
            "members": [
                {"strategy": "bb_reversion", "params": {"window": 3, "num_std": 1.0}}
            ],
            "mode": "single",
        }
        details = market_details(candles(100), "1m", 6000, configs=[cfg])
        values = {r["name"]: r["value"] for r in details["indicators"]}
        self.assertAlmostEqual(values["BB 3/1σ mid"], 198.6)
        self.assertAlmostEqual(values["BB 3/1σ upper"], 198.6 + (2 / 3) ** 0.5)
        self.assertNotEqual(values["BB 3/1σ mid"], values["BB20 middle"])

    def test_live_position_can_be_above_observed_range_without_claiming_completion(
        self,
    ):
        frame = {
            "interval": "1m",
            "rows": [{"status": "ready", "direction": "UP", "target_at": 6060}],
            "details": market_details(candles(100), "1m", 6000),
        }
        updated = live_view(
            frame, {"quote": {"price": 300, "observed_at": 6001}, "error": None}, 6001
        )
        self.assertGreater(updated["details"]["shape"]["live_range_position"], 1)
        expired = live_view(
            frame, {"quote": {"price": 200, "observed_at": 6060}, "error": None}, 6060
        )
        self.assertIsNone(expired["rows"][0]["direction"])
        self.assertTrue(expired["details"]["stale"])
        self.assertEqual(frame["rows"][0]["status"], "ready")


class Source(unittest.TestCase):
    def test_cancelled_bootstrap_does_not_throttle_its_replacement(self):
        class Client:
            calls = 0

            def fetch(self, step, start, end):
                self.calls += 1
                return {
                    t: {
                        "ts": t,
                        "open": 100,
                        "high": 102,
                        "low": 99,
                        "close": 101,
                        "volume": 1,
                    }
                    for t in range(start, end, step)
                }

        client = Client()
        session = DataSession(client, clock=lambda: 100_005)
        request = {"interval": "1m", "rows": [original()], "lookback": 48}
        with self.assertRaises(Cancelled):
            session(request, lambda: client.calls >= 1)
        result = session(request, lambda: False)
        self.assertGreater(client.calls, 1)
        self.assertIsNone(result["error"])

    def test_cached_source_recomputes_edits_without_refetch_or_chart_reseeding(self):
        class Client:
            calls = 0

            def fetch(self, step, start, end):
                self.calls += 1
                return {
                    t: {
                        "ts": t,
                        "open": 100,
                        "high": 102,
                        "low": 99,
                        "close": 101,
                        "volume": 1,
                    }
                    for t in range(start, end, step)
                }

        client = Client()
        session = DataSession(client, clock=lambda: 100_005)
        state = WorkingSet([original()])
        request = {"interval": "1m", "rows": state.visible(), "lookback": 48}
        first = session(request, lambda: False)
        calls = client.calls
        cfg = state.editor_config(row_key(original()))
        cfg["members"][0]["params"]["period"] = 5
        state.edit(row_key(original()), json.dumps(cfg))
        next_frame = session(
            {**request, "rows": state.visible(), "lookback": 300}, lambda: False
        )
        self.assertEqual(client.calls, calls)
        self.assertEqual(
            first["rows"][0]["input_start_at"], next_frame["rows"][0]["input_start_at"]
        )
        self.assertEqual(
            next_frame["rows"][0]["config"]["members"][0]["params"]["period"], 5
        )
        self.assertFalse(next_frame["rows"][0]["historical"])

    def test_cancel_is_checked_between_candle_pages(self):
        class Client:
            calls = 0

            def fetch(self, step, start, end):
                self.calls += 1
                return {}

        client = Client()
        session = DataSession(client)
        with self.assertRaises(Cancelled):
            session.fetch(60, 0, 60 * 600, lambda: client.calls >= 1)
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
