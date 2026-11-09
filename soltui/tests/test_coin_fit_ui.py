"""Suitability command parity and real Textual worker/cancellation behavior; no network."""
from __future__ import annotations

import copy
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Button, DataTable, Select, Sparkline, Static, TabbedContent

import soltui
from soltui import bots, commands
from soltui import config as config_mod
from soltui.config import Settings
from soltui.tui import SolTuiApp


def row(coin="SOL", *, fit="PROVISIONAL_FIT", score=2.0):
    metrics = {"total_return": 0.1, "hold_return": 0.08, "excess_return": 0.02,
               "max_drawdown": 0.04, "cycles": 5, "costs_usd": 4.0}
    curve = [[1700000000, 1000, 1000], [1700003600, 1100, 1080]]
    return {"coin": coin, "fit": fit, "score": score, "reason": "costed full-equity screen",
            "reasons": ["costed full-equity screen"], "missing_evidence": ["future execution"],
            "data_sha256": "a" * 64, "metrics": metrics, "equity": curve,
            "windows": [{"label": "holdout", "start": 1700000000, "end": 1700003600,
                         "stress": 1.0, "metrics": metrics, "equity": curve}], "template": []}


def report(bot="grid", mode="quick", rows=None, cancelled=False):
    return {"schema": "coin-fit/v1", "bot": bot, "mode": mode, "rows": [row()] if rows is None else rows,
            "errors": {}, "cancelled": cancelled, "config": {"range_pct": 10, "rungs": 9},
            "selection_id": "selection-fixture", "common_start": 1700000000, "common_end": 1700086400,
            "fee_bps": 6.0, "slippage_bps": 2.0, "capital_usd": 1000,
            "policy": {"max_drawdown": .25}, "notes": ["Provisional historical simulation only"]}


class BackendFixture:
    def patch_backend(self, fn):
        module = types.ModuleType("soltui.coin_fit")
        module.rank_coins = fn
        self.enterContext(mock.patch.dict(sys.modules, {"soltui.coin_fit": module}))
        self.enterContext(mock.patch.object(soltui, "coin_fit", module, create=True))


class CommandTests(BackendFixture, unittest.TestCase):
    def setUp(self):
        self.ctx = commands.Context.from_settings(Settings(), commands.Runtime())

    def dispatch(self, name, params=None):
        return commands.dispatch(name, params or {}, surface="test", ctx=self.ctx, quiet=True)

    def test_quick_and_audit_share_the_backend_and_frozen_parameters(self):
        seen = []
        def fake(bot, coins, settings, **kwargs):
            seen.append((bot, coins, settings, kwargs))
            kwargs["progress"](0.5, "halfway")
            return report(bot, kwargs["mode"])
        self.patch_backend(fake)
        self.assertTrue(self.dispatch("bots.rank_coins", {"bot": "grid"})["ok"])
        frozen = {"bot": "dca", "asset": "ETH", "config": {"base_order_usd": 10},
                  "reference_end": 1700086400, "fee_bps": 8, "slippage_bps": 3,
                  "selection_id": "selection-fixture", "expected_data_sha256": "a" * 64,
                  "policy": {"max_drawdown": .2}, "capital": 2000}
        self.assertTrue(self.dispatch("bots.audit_coin", frozen)["ok"])
        self.assertEqual((seen[0][0:2], seen[0][3]["mode"]), (("grid", "ALL"), "quick"))
        self.assertEqual((seen[1][0:2], seen[1][3]["mode"]), (("dca", ["ETH"]), "audit"))
        for key in ("config", "reference_end", "fee_bps", "slippage_bps", "selection_id", "expected_data_sha256", "policy", "capital"):
            self.assertEqual(seen[1][3][key], frozen[key])
        self.assertEqual(self.dispatch("bots.fit_status")["result"]["status"], "completed")

    def test_invalid_or_unsupported_inputs_never_run_the_engine(self):
        fake = mock.Mock()
        self.patch_backend(fake)
        cases = [("bots.rank_coins", {"bot": "triangle"}),
                 ("bots.rank_coins", {"bot": "grid", "coins": []}),
                 ("bots.rank_coins", {"bot": "grid", "coins": [False]}),
                 ("bots.rank_coins", {"bot": "grid", "days": float("nan")}),
                 ("bots.audit_coin", {"bot": "grid", "asset": "SOL", "config": []}),
                 ("bots.audit_coin", {"bot": "grid", "asset": "SOL", "policy": []}),
                 ("bots.audit_coin", {"bot": "grid", "asset": "SOL", "capital": 0}),
                 ("bots.audit_coin", {"bot": "grid", "asset": "SOL", "expected_data_sha256": "bad"})]
        for name, params in cases:
            with self.subTest(params=params):
                self.assertFalse(self.dispatch(name, params)["ok"])
        fake.assert_not_called()

    def test_cancel_before_thread_claim_is_not_lost(self):
        fake = mock.Mock()
        self.patch_backend(fake)
        self.dispatch("bots.fit_cancel", {"request_id": "early"})
        out = self.dispatch("bots.rank_coins", {"bot": "grid", "request_id": "early"})
        self.assertTrue(out["ok"])
        self.assertTrue(out["result"]["cancelled"])
        self.assertEqual(self.dispatch("bots.fit_status")["result"]["status"], "cancelled")
        fake.assert_not_called()

    def test_busy_failed_and_cancelled_are_distinct(self):
        entered, finished = threading.Event(), threading.Event()
        def fake(bot, coins, settings, **kwargs):
            entered.set()
            while not kwargs["cancelled"]():
                finished.wait(0.01)
            return report(cancelled=True)
        self.patch_backend(fake)
        out = []
        thread = threading.Thread(target=lambda: out.append(self.dispatch("bots.rank_coins", {"bot": "grid"})))
        thread.start()
        self.assertTrue(entered.wait(2))
        try:
            self.assertFalse(self.dispatch("bots.rank_coins", {"bot": "dca"})["ok"])
            self.assertEqual(self.dispatch("bots.fit_cancel")["result"]["status"], "cancelling")
        finally:
            self.ctx.runtime.coin_fit_stop.set()
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertTrue(out[0]["result"]["cancelled"])
        self.assertEqual(self.dispatch("bots.fit_status")["result"]["status"], "cancelled")
        with mock.patch.object(sys.modules["soltui.coin_fit"], "rank_coins", side_effect=ValueError("broken sample")):
            failed = self.dispatch("bots.rank_coins", {"bot": "grid"})
        self.assertFalse(failed["ok"])
        self.assertIn("broken sample", failed["error"]["message"])
        self.assertEqual(self.dispatch("bots.fit_status")["result"]["status"], "failed")


class FitHarness(SolTuiApp):
    """Mount the actual Bots pane and actual command worker without unrelated tabs."""
    def compose(self):
        yield from self._bots_pane()

    def on_mount(self, event):
        event.prevent_default()
        self._bots_fit_alive.set()
        self._bots_load()
        self._bots_loaded = True

    def _bots_forward_refresh(self):
        pass


def visible(app, selector):
    return str(app.query_one(selector, Static).content)


class UITests(BackendFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.enterContext(mock.patch.object(config_mod, "CONFIG_DIR", root / "config"))
        self.enterContext(mock.patch.object(bots, "available_coins", return_value=["ETH", "SOL"]))
        self.app = FitHarness(Settings(data_dir=str(root / "data"), poll_interval_seconds=60))

    async def wait_done(self, pilot):
        await pilot.pause(0.05)
        await self.app.workers.wait_for_complete()
        await pilot.pause()

    async def test_full_v2_research_and_classic_bots_navigation_can_rank_and_audit(self):
        def fake(bot, coins, settings, **kwargs):
            return report(bot, kwargs["mode"], [row(fit="GOOD_FIT" if kwargs["mode"] == "audit"
                                                    else "PROVISIONAL_FIT")])
        self.patch_backend(fake)
        for classic in (False, True):
            with self.subTest(classic=classic):
                self.app = SolTuiApp(self.app.settings, start="tab-now" if not classic else "tab-backtest",
                                     classic=classic)
                async with self.app.run_test(size=(180, 60)) as pilot:
                    tabs = self.app.query_one("#main-tabs", TabbedContent)
                    if classic:
                        tabs.active = "tab-bots"
                    else:
                        await pilot.press("3")
                        research = self.app._v2_destination("research")
                        bots_index = next(i for i, view in enumerate(research.views) if view.tab == "tab-bots")
                        for _ in range(bots_index):
                            await pilot.press("right_square_bracket")
                    await pilot.pause()
                    self.assertEqual(tabs.active, "tab-bots")
                    self.assertEqual(self.app.query_one("#main-tabs > ContentTabs").display, classic)
                    clicked = False
                    for _ in range(10):
                        if await pilot.click("#bots-fit-rank"):
                            clicked = True
                            break
                        await pilot.pause(0.1)
                    self.assertTrue(clicked)
                    await self.wait_done(pilot)
                    self.assertEqual(self.app.query_one("#bots-sections", TabbedContent).active, "bots-sec-fit")
                    self.assertEqual(self.app.query_one("#bots-fit-table", DataTable).row_count, 1)
                    self.assertTrue(await pilot.click("#bots-fit-audit"))
                    await self.wait_done(pilot)
                    self.assertIn("GOOD_FIT", visible(self.app, "#bots-fit-detail"))

    async def test_rank_selection_audit_binding_and_equity_render(self):
        seen = []
        def fake(bot, coins, settings, **kwargs):
            seen.append((bot, coins, copy.deepcopy({k: v for k, v in kwargs.items()
                                                  if k not in ("progress", "cancelled")})))
            return report(bot, kwargs["mode"], [row("ETH", score=3), row("SOL")]) if kwargs["mode"] == "quick" else (
                report(bot, "audit", [row("SOL", fit="GOOD_FIT", score=99)]))
        self.patch_backend(fake)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await self.wait_done(pilot)
            table = self.app.query_one("#bots-fit-table", DataTable)
            self.assertEqual(table.row_count, 2)
            self.assertEqual([str(table.get_row_at(i)[0]) for i in range(2)], ["ETH", "SOL"])
            table.move_cursor(row=1)
            table.action_select_cursor()
            await pilot.pause()
            self.assertEqual(self.app._bots_fit_coin, "SOL")
            self.assertEqual(list(self.app.query_one("#bots-fit-equity", Sparkline).data), [1000, 1100])
            self.app.query_one("#bots-fit-audit", Button).press()
            await self.wait_done(pilot)
            self.assertEqual([str(table.get_row_at(i)[0]) for i in range(2)], ["ETH", "SOL"])
            self.assertEqual(str(table.get_row_at(1)[1]), "PROVISIONAL_FIT")
            self.assertEqual(str(table.get_row_at(1)[2]), "GOOD_FIT")
            self.assertIn("GOOD_FIT", visible(self.app, "#bots-fit-detail"))
            self.assertEqual(self.app.query_one("#bots-fit-windows", DataTable).row_count, 1)
            audit = seen[1][2]
            self.assertEqual(audit["reference_end"], 1700086400)
            self.assertEqual(audit["expected_data_sha256"], "a" * 64)
            self.assertEqual((audit["fee_bps"], audit["slippage_bps"]), (6.0, 2.0))
            self.assertEqual(audit["selection_id"], "selection-fixture")
            self.assertEqual(audit["policy"], {"max_drawdown": .25})
            self.assertEqual(audit["capital"], 1000)
            self.assertEqual(seen[0][1], "ALL")

    async def test_cancel_keeps_ui_responsive_and_waits_for_backend(self):
        entered, release = threading.Event(), threading.Event()
        def fake(bot, coins, settings, **kwargs):
            entered.set()
            while not kwargs["cancelled"]():
                release.wait(0.01)
            return report(cancelled=True)
        self.patch_backend(fake)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await pilot.pause(0.1)
            self.assertTrue(entered.is_set())
            self.assertTrue(self.app._bots_fit_busy)
            self.app.query_one("#bots-fit-cancel", Button).press()
            await self.wait_done(pilot)
            self.assertFalse(self.app._bots_fit_busy)
            self.assertIn("Cancelled", visible(self.app, "#bots-fit-status"))
            self.assertFalse(self.app.query_one("#bots-fit-rank", Button).disabled)

    async def test_actual_cached_backend_quick_then_audit_populates_windows(self):
        from textual.widgets import Input

        from backtester.core.data import SyntheticLoader

        data = Path(self.tmp.name) / "data"
        data.mkdir()
        for coin, seed in (("ETH", 2), ("SOL", 3)):
            SyntheticLoader(n_bars=24 * 30, seed=seed,
                            start_ts=1700000000 // 3600 * 3600).load(coin, None, None, "1h").to_csv(
                                data / f"{coin}_1h.csv", index=False)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-days", Input).value = "30"
            self.app.query_one("#bots-fit-rank", Button).press()
            await self.wait_done(pilot)
            self.assertEqual(self.app.query_one("#bots-fit-table", DataTable).row_count, 2)
            self.assertTrue(all(row.get("data_sha256") for row in self.app._bots_fit_rows.values()))
            self.assertEqual(len(self.app._bots_fit_rows[self.app._bots_fit_coin]["template"]), 22)
            quick_order = list(self.app._bots_fit_rows)
            self.app.query_one("#bots-fit-audit", Button).press()
            await self.wait_done(pilot)
            self.assertEqual(list(self.app._bots_fit_rows), quick_order)
            self.assertEqual(self.app.query_one("#bots-fit-windows", DataTable).row_count, 10,
                             visible(self.app, "#bots-fit-status"))
            self.assertIn("open_inventory_before_exit", visible(self.app, "#bots-fit-detail"))
            windows = self.app.query_one("#bots-fit-windows", DataTable)
            windows.move_cursor(row=5)
            windows.action_select_cursor()
            await pilot.pause()
            self.assertIn("2x costs", visible(self.app, "#bots-fit-curve-context"))

    async def test_actual_poor_fit_shows_failures_before_successful_checks(self):
        import numpy as np
        from textual.widgets import Input

        from backtester.core.data import SyntheticLoader

        data = Path(self.tmp.name) / "data"
        data.mkdir()
        bars = SyntheticLoader(n_bars=24 * 30, seed=3,
                               start_ts=1700000000 // 3600 * 3600).load("SOL", None, None, "1h")
        prices = 100 * np.exp(-np.linspace(0, 1.2, len(bars)))
        for field in ("open", "close"):
            bars[field] = prices
        bars["high"], bars["low"], bars["volume"] = prices * 1.001, prices * .999, 1.0
        bars.to_csv(data / "FALL_1h.csv", index=False)
        with mock.patch.object(bots, "available_coins", return_value=["FALL"]):
            async with self.app.run_test(size=(180, 60)) as pilot:
                self.app.query_one("#bots-days", Input).value = "30"
                self.app.query_one("#bots-fit-rank", Button).press()
                await self.wait_done(pilot)
                poor = self.app._bots_fit_rows["FALL"]
                self.assertEqual(poor["fit"], "POOR_FIT")
                self.assertTrue(poor["failures"])
                detail = visible(self.app, "#bots-fit-detail")
                for failed in poor["failures"]:
                    self.assertIn(failed, detail)
                self.assertIn(poor["failures"][0][:180], visible(self.app, "#bots-fit-selection-summary"))
                self.assertLess(detail.index("Failed checks:"), detail.index("Supporting checks:"))

    async def test_bot_switch_discards_a_late_result(self):
        entered, release = threading.Event(), threading.Event()
        def fake(bot, coins, settings, **kwargs):
            entered.set()
            release.wait(2)
            return report(bot, rows=[row("OLD")])
        self.patch_backend(fake)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await pilot.pause(0.1)
            self.assertTrue(entered.is_set())
            self.app.query_one("#bots-bot", Select).value = "dca"
            await pilot.pause()
            release.set()
            await self.wait_done(pilot)
            self.assertEqual(self.app.query_one("#bots-fit-table", DataTable).row_count, 0)
            self.assertIn("discarded", visible(self.app, "#bots-fit-status"))

    async def test_error_rows_failures_and_triangle_state_are_visible(self):
        def fake(bot, coins, settings, **kwargs):
            r = report(rows=[row("SOL")])
            r["errors"] = {"ETH": "missing cached history"}
            return r
        self.patch_backend(fake)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await self.wait_done(pilot)
            self.assertEqual(self.app.query_one("#bots-fit-table", DataTable).row_count, 2)
            self.assertIn("ETH", self.app._bots_fit_rows)
            self.app.query_one("#bots-bot", Select).value = "triangle"
            await pilot.pause()
            self.assertTrue(self.app.query_one("#bots-fit-rank", Button).disabled)
            self.assertIn("not a per-coin", visible(self.app, "#bots-fit-status"))

    async def test_changed_settings_discard_result_and_worker_keeps_snapshot(self):
        entered, release = threading.Event(), threading.Event()
        captured = []
        def fake(bot, coins, settings, **kwargs):
            entered.set()
            release.wait(2)
            captured.append(settings.fee_bps)
            return report(bot)
        self.patch_backend(fake)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await pilot.pause(0.1)
            self.assertTrue(entered.is_set())
            original_fee = self.app.settings.fee_bps
            self.app.settings.fee_bps = 25
            release.set()
            await self.wait_done(pilot)
            self.assertEqual(captured, [original_fee])
            self.assertEqual(self.app.query_one("#bots-fit-table", DataTable).row_count, 0)
            self.assertIn("discarded", visible(self.app, "#bots-fit-status"))

    async def test_malformed_report_and_engine_error_do_not_crash_app(self):
        self.patch_backend(lambda *a, **k: {"rows": "invalid"})
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await self.wait_done(pilot)
            self.assertIn("invalid report", visible(self.app, "#bots-fit-status"))
            with mock.patch.object(sys.modules["soltui.coin_fit"], "rank_coins", side_effect=ValueError("bad candles")):
                self.app.query_one("#bots-fit-rank", Button).press()
                await self.wait_done(pilot)
            self.assertIn("bad candles", visible(self.app, "#bots-fit-status"))
            self.assertFalse(self.app._bots_fit_busy)

    async def test_unmount_requests_stop_and_drains_its_owned_thread(self):
        entered, ended = threading.Event(), threading.Event()
        def fake(bot, coins, settings, **kwargs):
            entered.set()
            while not kwargs["cancelled"]():
                ended.wait(0.01)
            ended.set()
            return report(cancelled=True)
        self.patch_backend(fake)
        async with self.app.run_test(size=(180, 60)) as pilot:
            self.app.query_one("#bots-fit-rank", Button).press()
            await pilot.pause(0.1)
            self.assertTrue(entered.is_set())
        self.assertTrue(ended.is_set())
        self.assertTrue(self.app._bots_fit_drained.is_set())
        self.assertTrue(self.app._bots_fit_shutdown_drained)
        self.assertIsNone(self.app._bots_fit_timer)
        self.assertEqual(self.app.ctx.runtime.coin_fit_job["status"], "interrupted")


if __name__ == "__main__":
    unittest.main()
