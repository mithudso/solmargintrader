"""Prospective evidence, horizon isolation, and the roster keyboard workflow."""

from __future__ import annotations

import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

import numpy as np
from textual.widgets import Button, DataTable, Input, Static, TabbedContent

from soltui import commands, config
from soltui import forwardtest as ft
from soltui.roster import Roster
from soltui.tests.test_tui import TEST_SIZE
from soltui.tui import SolTuiApp

BASE = 1_800_000_000


def stop_fixture_runner(ctx):
    """Stop only the fixture's thread even when an earlier assertion raises."""
    ctx.runtime.forward_stop.set()
    thread = ctx.runtime.forward_thread
    if thread is not None:
        thread.join(5)
        if thread.is_alive():
            raise AssertionError("fixture forward runner did not stop")


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

    def test_closed_candles_and_calls_survive_reopening_database(self) -> None:
        self.advance(0)
        db_path = config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
        with sqlite3.connect(db_path) as db:
            self.assertGreater(db.execute("SELECT count(*) FROM candle WHERE asset='SOL'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM call").fetchone()[0], 4)
        self.assertEqual(sum(row["pending"] for row in ft.status("SOL")), 4)

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


class AutoOptimizeAndDefaults(ForwardEvidence):
    """Auto-optimize on adopts and saves the winner as the trial's default; off never moves."""

    def run_probe(self, *, tune: bool) -> dict:
        self.trial = {"label": "probe", "mode": "all", "members": [ft.member("sma_regime", {})]}
        active = self.trial["members"]

        def forecast(spec, mode, bars):
            return -1 if spec == active else 1

        with patch.object(ft, "_predict", side_effect=forecast), patch.dict(
                ft.KNOBS, tune_min_calls=8, adaptive_prior=2.0, tune_cooldown=0):
            self.advance(0, tune=tune)
            for minute in range(1, 13):
                out = self.advance(minute, tune=tune)
        return {r["minutes"]: r for r in out["rows"]}

    def test_off_scores_calls_but_never_changes_a_setting(self) -> None:
        rows = self.run_probe(tune=False)
        self.assertEqual(rows[1]["changes"], 0)
        self.assertGreater(rows[1]["resolved"], 0)
        self.assertEqual(ft.load_defaults(), {})

    def test_an_adoption_is_saved_as_the_default_and_seeds_the_next_trial(self) -> None:
        rows = self.run_probe(tune=True)
        adopted = rows[1]["settings"]
        self.assertTrue(rows[1]["saved_default"])
        self.assertFalse(rows[5]["saved_default"])
        saved = ft.load_defaults()
        self.assertEqual(list(saved), ["SOL|probe|1"])
        self.assertEqual(saved["SOL|probe|1"]["members"], adopted)
        self.assertGreater(saved["SOL|probe|1"]["probability"], ft.KNOBS["tune_confidence"])
        # A new code revision starts new trial rows; the saved default is where the 1-minute one starts.
        out = ft.tick("SOL", [self.trial], (1, 5), 16.0, fetch=lambda *a, **k: candles(20),
                      clock=lambda: BASE + 20 * 60 + 4, code="next-revision")
        fresh = [r for r in out["rows"] if r["changes"] == 0 and r["resolved"] == 0]
        by_minutes = {r["minutes"]: r for r in fresh}
        self.assertEqual(by_minutes[1]["settings"], adopted)
        self.assertEqual(by_minutes[5]["settings"], self.trial["members"])

    def test_a_saved_default_for_other_members_or_unknown_params_is_ignored(self) -> None:
        seed = self.trial["members"]
        self.assertEqual(ft._usable_default([{"name": "sma_regime", "params": {}}], seed, "all"), seed)
        self.assertEqual(ft._usable_default([{"name": "buy_and_hold", "params": {"nope": 1}}], seed, "all"), seed)
        self.assertEqual(ft._usable_default(None, seed, "all"), seed)
        ft.save_default("SOL", "hold", 1, [{"name": "sma_regime", "params": {"window": 5}}], [],
                        probability=0.99, samples=300, bar=0)
        out = self.advance(0)
        row = next(r for r in out["rows"] if r["minutes"] == 1)
        self.assertEqual(row["settings"], seed)


class ForwardPlan(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.enterContext(patch.object(config, "CONFIG_DIR", Path(tmp.name)))

    def test_running_plan_restores_and_stop_clears_it(self) -> None:
        ctx = commands.Context.from_settings(config.Settings(), commands.Runtime())
        self.addCleanup(stop_fixture_runner, ctx)
        commands.dispatch("forwardtest.start", {"scope": "roster", "coins": ["ETH"], "use_leverage": True,
                   "leverage": 5., "allow_short": True, "min_confidence": .9}, ctx=ctx, quiet=True)
        with patch.object(commands, "_forward_runner", lambda rt: rt.forward_stop.wait(5)):
            self.assertTrue(commands.dispatch("forwardtest.run", {}, ctx=ctx, quiet=True)["ok"])
            ctx.runtime.forward_stop.set()
            ctx.runtime.forward_thread.join(5)
            restored = commands.Context.from_settings(config.Settings(), commands.Runtime())
            self.addCleanup(stop_fixture_runner, restored)
            result = commands.dispatch("forwardtest.restore", {}, ctx=restored, quiet=True)
            self.assertEqual(result["result"]["assets"], ["ETH"])
            profile = restored.runtime.forward_plan["execution"]
            self.assertEqual((profile["leverage"], profile["allow_short"], profile["min_confidence"]), (5., True, .9))
            commands.dispatch("forwardtest.stop", {}, ctx=restored, quiet=True)
            restored.runtime.forward_thread.join(5)
            self.assertIsNone(ft.load_session())

    def test_coins_and_optimize_reach_the_plan(self) -> None:
        ctx = commands.Context.from_settings(config.Settings(), commands.Runtime())
        env = commands.dispatch("forwardtest.start", {"scope": "roster", "coins": ["eth", "SOL"], "optimize": False},
                                ctx=ctx, quiet=True)
        self.assertTrue(env["ok"], env)
        plan = ctx.runtime.forward_plan
        self.assertEqual(plan["assets"], ["ETH", "SOL"])
        self.assertIs(plan["tune"], False)
        commands.dispatch("forwardtest.stop", {}, ctx=ctx, quiet=True)
        with patch.object(commands, "forward_coins", return_value=["BTC", "ETH", "SOL"]):
            env = commands.dispatch("forwardtest.start", {"scope": "roster", "coins": "all"}, ctx=ctx, quiet=True)
        self.assertEqual(ctx.runtime.forward_plan["assets"], ["BTC", "ETH", "SOL"])
        self.assertIs(ctx.runtime.forward_plan["tune"], True)
        bad = commands.dispatch("forwardtest.start", {"coins": 5}, ctx=commands.Context.from_settings(
            config.Settings(), commands.Runtime()), quiet=True)
        self.assertEqual(bad["error"]["code"], "bad_params")

    def test_the_runner_checks_every_coin_on_its_own_thread_until_stopped(self) -> None:
        ctx = commands.Context.from_settings(config.Settings(), commands.Runtime())
        self.addCleanup(stop_fixture_runner, ctx)
        seen: list[str] = []

        def fake_tick(asset, trials, horizons, cost, **kw):
            seen.append(asset)
            if asset == "ETH":
                raise ValueError("No ordered closed one-minute candles")
            return {"bar": 1, "recorded": 3, "message": "ok", "rows": []}

        self.assertFalse(commands.dispatch("forwardtest.run", {}, ctx=ctx, quiet=True)["ok"])
        commands.dispatch("forwardtest.start", {"scope": "roster", "coins": ["SOL", "ETH", "BTC"]}, ctx=ctx, quiet=True)
        with patch.object(ft, "tick", side_effect=fake_tick), patch("soltui.commands.time.time", return_value=BASE + 4):
            self.assertTrue(commands.dispatch("forwardtest.run", {}, ctx=ctx, quiet=True)["ok"])
            for _ in range(100):
                if len(seen) >= 3:
                    break
                Event().wait(0.02)
            state = commands.dispatch("forwardtest.state", {}, ctx=ctx, quiet=True)["result"]
            self.assertTrue(state["running"])
            self.assertEqual(state["assets"], ["SOL", "ETH", "BTC"])
            self.assertEqual(state["last"]["SOL"]["recorded"], 3)
            self.assertIn("candles", state["last"]["ETH"]["error"])  # one coin's failure, the others ran
            self.assertEqual(state["last"]["BTC"]["recorded"], 3)
            commands.dispatch("forwardtest.stop", {}, ctx=ctx, quiet=True)
            thread = ctx.runtime.forward_thread
            if thread is not None:
                thread.join(5)
        self.assertEqual(seen, ["SOL", "ETH", "BTC"])  # once per closed minute, not once per loop
        self.assertIsNone(ctx.runtime.forward_thread)
        self.assertFalse(commands.dispatch("forwardtest.state", {}, ctx=ctx, quiet=True)["result"]["running"])


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

    async def test_start_runs_in_the_background_across_tabs_and_stop_drains_it(self) -> None:
        app = SolTuiApp(config.Settings(poll_interval_seconds=60, forwardtest_autostart=False))
        entered, released = Event(), Event()

        def check(asset, trials, horizons, cost, **kw):
            entered.set()
            released.wait(5)
            self.assertTrue(kw["stop"].is_set())
            self.assertEqual(horizons, ft.HORIZONS)
            self.assertIs(kw["tune"], True)
            return {"bar": None, "recorded": 0, "rows": [], "message": "stub"}

        with patch.object(ft, "tick", side_effect=check), patch("soltui.commands.time.time", return_value=BASE + 4):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-forwardtest"
                await pilot.pause()
                await pilot.click("#forward-start")
                self.assertTrue(app._forward_running, str(app.query_one("#forward-status", Static).content))
                # The runner is a thread of its own: leaving the tab does not pause it.
                app.query_one(TabbedContent).active = "tab-backtest"
                for _ in range(40):
                    if entered.is_set():
                        break
                    await pilot.pause(0.05)
                self.assertTrue(entered.is_set())
                self.assertIn("forwardtest running", app.sub_title)
                app.query_one(TabbedContent).active = "tab-forwardtest"
                await pilot.pause()
                await pilot.click("#forward-stop")
                self.assertNotIn("forwardtest running", app.sub_title)
                released.set()
                for _ in range(60):
                    await pilot.pause(0.05)
                    app._forward_schedule()
                    if not app.query_one("#forward-start").disabled:
                        break
                self.assertFalse(app.query_one("#forward-start").disabled)

    async def test_autostart_uses_shared_producer_and_preserves_saved_scope(self) -> None:
        with TemporaryDirectory() as directory, patch.object(config, "CONFIG_DIR", Path(directory)):
            saved = {"asset": "BTC", "assets": ["BTC", "ETH", "SOL"], "horizons": [5, 30],
                     "trials": [{"label": "custom", "mode": "all", "members": [
                         ft.member("ma_crossover", {"fast": 9, "slow": 40})]}],
                     "cost": 17.25, "code": ft.revision(), "tune": False}
            ft.save_session(saved)
            before = ft.load_session()
            app = SolTuiApp(config.Settings(poll_interval_seconds=60, forwardtest_autostart=True),
                            auto_recover=True)
            original = app._call
            calls = []
            shared = {"running": False, "paused": False, "can_start": True, "busy": False,
                      "prepared": False, "assets": saved["assets"], "last": {}, "message": "Stopped"}

            def call(name, params=None, **kw):
                calls.append((name, params))
                if name == "forwardtest.ensure":
                    shared.update(running=True, can_start=False, message="Running")
                elif name == "forwardtest.stop":
                    shared.update(running=False, paused=True, can_start=True, message="Paused")
                elif name not in ("forwardtest.health", "forwardtest.state"):
                    return original(name, params, **kw)
                return {"ok": True, "result": dict(shared)}

            with patch.object(app, "_call", side_effect=call):
                async with app.run_test(size=TEST_SIZE) as pilot:
                    for _ in range(100):
                        if not app._signal_recovery_busy:
                            break
                        await pilot.pause(.01)
                    self.assertFalse(app._signal_recovery_busy)
                    self.assertTrue(app._forward_running)
                    self.assertIn("forwardtest running on 3 coin(s)", app.sub_title)
                    self.assertEqual([p for n, p in calls if n == "forwardtest.ensure"],
                                     [{"asset": "SOL", "manual": False}])
                    self.assertFalse(any(n in ("forwardtest.start", "forwardtest.run", "forwardtest.restore")
                                         for n, _ in calls))
                    self.assertIsNone(app.ctx.runtime.forward_thread)
                    self.assertEqual(ft.load_session(), before)
                    app.query_one(TabbedContent).active = "tab-forwardtest"
                    await pilot.pause()
                    self.assertTrue(app.query_one("#forward-start", Button).disabled)
                    self.assertFalse(app.query_one("#forward-stop", Button).disabled)
                    await pilot.click("#forward-stop")
                    self.assertFalse(app._forward_running)
                    self.assertNotIn("forwardtest running", app.sub_title)
                    self.assertTrue(shared["paused"])

    async def test_autostart_forwardtest_disabled_by_settings(self) -> None:
        app = SolTuiApp(config.Settings(poll_interval_seconds=60, forwardtest_autostart=False))
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            self.assertFalse(app._forward_running)
            self.assertNotIn("forwardtest running", app.sub_title)
            state = commands.dispatch("forwardtest.state", {}, ctx=app.ctx)["result"]
            self.assertFalse(state["running"])
            app.query_one(TabbedContent).active = "tab-forwardtest"
            await pilot.pause()
            self.assertFalse(app.query_one("#forward-start", Button).disabled)
            self.assertTrue(app.query_one("#forward-stop", Button).disabled)
