"""Prospective evidence, horizon isolation, and the roster keyboard workflow."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

import numpy as np
from textual.widgets import DataTable, Input, Static, TabbedContent

from soltui import commands, config
from soltui import forwardtest as ft
from soltui.roster import Roster
from soltui.tests.test_tui import TEST_SIZE
from soltui.tui import SolTuiApp

BASE = 1_800_000_000


def candles(minute: int, *, gap: int | None = None) -> dict:
    offsets = np.arange(-200, minute + 1)
    offsets = offsets[offsets != gap]
    ts = BASE + offsets * 60
    op = np.full(len(ts), 100.0)
    close = np.where(offsets == 1, 95.0, 102.0)
    return {"ts": ts, "open": op, "close": close, "low": np.minimum(op, close),
            "high": np.maximum(op, close), "volume": np.ones(len(ts))}


class ForwardEvidence(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.enterContext(patch.object(config, "CONFIG_DIR", Path(tmp.name)))
        self.trial = {"label": "hold", "mode": "all", "members": [ft.member("buy_and_hold", {})]}

    def advance(self, minute: int, *, gap: int | None = None, **kwargs) -> dict:
        return ft.tick("SOL", [self.trial], ft.HORIZONS, 16.0,
                       fetch=lambda *a, **k: candles(minute, gap=gap),
                       clock=lambda: BASE + minute * 60 + 4, code="fixture", **kwargs)

    def test_all_horizons_settle_independently_and_cannot_overlap(self) -> None:
        self.assertEqual(self.advance(0)["recorded"], 4)
        self.assertEqual(self.advance(0)["recorded"], 0)
        self.assertEqual(self.advance(1)["recorded"], 1)
        rows = {r["minutes"]: r for r in self.advance(2)["rows"]}
        self.assertEqual(rows[1]["resolved"], 1)
        self.assertEqual(rows[1]["correct"], 0)
        self.assertEqual(rows[1]["last_outcome"], -1)
        self.assertTrue(all(rows[h]["resolved"] == 0 for h in (5, 10, 30)))
        rows = {r["minutes"]: r for r in self.advance(31)["rows"]}
        self.assertEqual(rows[30]["resolved"], 1)
        self.assertEqual(rows[30]["correct"], 1)

    def test_missing_target_candle_is_not_filled_by_a_later_close(self) -> None:
        self.advance(0)
        rows = {r["minutes"]: r for r in self.advance(8, gap=1)["rows"]}
        self.assertEqual(rows[5]["resolved"], 0)
        self.assertEqual(rows[5]["pending"], 2)
        rows = {r["minutes"]: r for r in self.advance(8)["rows"]}
        self.assertEqual(rows[5]["resolved"], 1)

    def test_neither_forming_prices_nor_a_late_computation_can_create_a_call(self) -> None:
        stamp = BASE + 4
        clock = iter([stamp, BASE + 60])
        out = ft.tick("SOL", [self.trial], (1,), 16.0,
                      fetch=lambda *a, **k: candles(2), clock=lambda: next(clock), code="fixture")
        self.assertEqual(out["recorded"], 0)
        self.assertIsNone(out["bar"])
        self.assertEqual(out["rows"][0]["pending"], 0)

    def test_predictions_ignore_the_forming_candle(self) -> None:
        with patch.object(ft, "_predict", wraps=ft._predict) as predict:
            self.advance(0)
        used = predict.call_args.args[2]["ts"]
        self.assertEqual(used[-1], BASE - 60)

    def test_stop_during_fetch_does_not_persist_a_prediction(self) -> None:
        stop = Event()

        def fetch(*args, **kwargs):
            stop.set()
            return candles(0)

        with self.assertRaisesRegex(RuntimeError, "stopped"):
            ft.tick("SOL", [self.trial], (1,), 16.0, fetch=fetch, stop=stop, code="fixture")
        self.assertEqual(ft.status("SOL"), [])

    def test_adoption_requires_resolved_evidence_and_stays_local_to_the_horizon(self) -> None:
        self.trial = {"label": "probe", "mode": "all", "members": [ft.member("sma_regime", {})]}
        active = self.trial["members"]
        candidate = ft.neighbours(active, "all")[1]
        # Controlled shadow calls make the evidence path deterministic; the real tick still
        # records, settles, gates, persists, and consumes each prediction.
        def forecast(spec, mode, bars):
            return -1 if spec == active else 1

        with patch.object(ft, "_predict", side_effect=forecast), patch.dict(
                ft.KNOBS, tune_min_calls=8, adaptive_prior=2.0, tune_cooldown=0):
            self.assertEqual(self.advance(0)["recorded"], 4)
            for minute in range(1, 13):
                out = self.advance(minute)
        rows = {r["minutes"]: r for r in out["rows"]}
        self.assertEqual(rows[1]["settings"], candidate)
        self.assertEqual(rows[1]["changes"], 1)
        self.assertEqual(rows[5]["settings"], active)
        self.assertEqual(rows[30]["changes"], 0)
        self.assertGreater(rows[1]["correct"], 0)


class ForwardPlan(unittest.TestCase):
    def test_custom_combination_at_one_horizon_uses_the_roster_parameters(self) -> None:
        ctx = commands.Context.from_settings(config.Settings(), commands.Runtime())
        ctx.roster = Roster()
        entry = ctx.roster.add("ma_crossover", fast=9, slow=40)
        args = {"scope": "combinations", "mode": "vote", "horizons": [10],
                "combinations": [[entry.label, "rsi"]]}
        env = commands.dispatch("forwardtest.start", args, ctx=ctx, quiet=True)
        self.assertTrue(env["ok"], env)
        plan = ctx.runtime.forward_plan
        self.assertEqual(plan["horizons"], (10,))
        self.assertEqual(len(plan["trials"]), 1)
        trial = plan["trials"][0]
        self.assertEqual(trial["mode"], "vote")
        self.assertEqual(trial["members"][0]["params"]["fast"], 9)
        ctx.roster.clear()
        self.assertEqual(len(trial["members"]), 2)
        self.assertFalse(commands.dispatch("forwardtest.start", args, ctx=ctx, quiet=True)["ok"])


class RosterForwardUI(unittest.IsolatedAsyncioTestCase):
    async def test_space_adds_and_removes_and_bulk_add_keeps_custom_parameters(self) -> None:
        app = SolTuiApp(config.Settings(poll_interval_seconds=60))
        app.ctx.roster = Roster()
        with patch.object(commands, "save_settings"):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-strategies"
                table = app.query_one("#available-table", DataTable)
                table.move_cursor(row=table.get_row_index("ma_crossover"))
                app.query_one("#strategy-params", Input).value = "fast=9 slow=40"
                table.focus()
                await pilot.press("space")
                self.assertEqual(app.roster.entries[0].params["fast"], 9)
                await pilot.press("space")
                self.assertEqual(len(app.roster), 0)
                await pilot.press("space")
                await pilot.click("#btn-roster-all")
                self.assertEqual(len(app.roster), len(commands.available_strategies()))
                self.assertEqual(app.roster.entries[0].params["fast"], 9)

    async def test_start_passes_all_horizons_and_stop_drains_a_running_worker(self) -> None:
        app = SolTuiApp(config.Settings(poll_interval_seconds=60))
        entered, released = Event(), Event()

        def check(**plan):
            entered.set()
            released.wait(5)
            self.assertTrue(plan["stop"].is_set())
            return {"bar": None, "recorded": 0, "rows": [], "message": "stub"}

        with patch.object(ft, "tick", side_effect=check) as tick:
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-forwardtest"
                await pilot.pause()
                await pilot.click("#forward-start")
                self.assertTrue(app._forward_running, str(app.query_one("#forward-status", Static).content))
                # Schedule deterministically if the click landed inside the publication grace period.
                with patch("soltui.tui.time.time", return_value=BASE + 4):
                    app._forward_schedule()
                for _ in range(20):
                    if entered.is_set():
                        break
                    await pilot.pause(0.05)
                self.assertTrue(entered.is_set())
                self.assertEqual(tick.call_args.kwargs["horizons"], ft.HORIZONS)
                await pilot.click("#forward-stop")
                self.assertTrue(app.query_one("#forward-start").disabled)
                released.set()
                for _ in range(20):
                    await pilot.pause(0.05)
                    if not app.query_one("#forward-start").disabled:
                        break
                self.assertFalse(app.query_one("#forward-start").disabled)
