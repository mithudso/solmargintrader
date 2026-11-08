"""Manual Coinbase order UI: review, explicit arm, one submit, and reconciliation."""
from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Button, Checkbox, DataTable, Input, Select, Static, TabbedContent

from soltui import config
from soltui.tests.test_tui import TEST_SIZE, make_settings
from soltui.tui import SolTuiApp


def envelope(value):
    return {"ok": True, "result": value, "error": None}


def preview(expires=None):
    return {"preview_id": "preview-1", "product_id": "SOL-USDC", "side": "BUY", "size": "1.10",
            "size_currency": "quote", "expires_at": expires or time.time() + 60,
            "estimate": {"fee": "0.01", "total": "1.10"}, "notice": "Estimate only"}


class CoinbaseManualUiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addAsyncCleanup(self._clean)
        self.patch = mock.patch.object(config, "CONFIG_DIR", Path(self.tmp.name))
        self.patch.start()

    async def _clean(self):
        self.patch.stop()
        self.tmp.cleanup()

    async def test_session_quick_order_requires_arm_and_blocks_on_unknown(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            skip = app.query_one("#coinbase-order-skip-review", Checkbox)
            self.assertFalse(skip.value)
            self.assertFalse(app.query_one("#coinbase-order-quick", Button).display)
            app.query_one("#coinbase-order-size", Input).value = "1.10"
            skip.value = True
            await pilot.pause()
            self.assertTrue(app.query_one("#coinbase-order-quick", Button).disabled)
            calls = []
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_quick":
                    calls.append((name, params))
                    return {"ok": False, "error": {"message": "Outcome unknown"}}
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._coinbase_order_quick_pressed()
                self.assertEqual(calls, [])
                app.query_one("#coinbase-order-armed", Checkbox).value = True
                await pilot.pause()
                self.assertFalse(app.query_one("#coinbase-order-quick", Button).disabled)
                app._coinbase_order_quick_pressed()
                app._coinbase_order_quick_pressed()
                await pilot.pause(.25)
                self.assertEqual(calls, [("coinbase.order_quick", {"product_id": "SOL-USDC", "side": "BUY",
                                  "size": "1.10", "size_currency": "quote", "skip_confirm": True})])
                self.assertTrue(app._coinbase_order_unknown)
                self.assertFalse(app.query_one("#coinbase-order-armed", Checkbox).value)
                self.assertTrue(app.query_one("#coinbase-order-quick", Button).disabled)
                self.assertIn("Do not resubmit", str(app.query_one("#coinbase-order-message", Static).render()))

    async def test_quick_sell_filled_shows_receipt_and_remains_armed(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            app.query_one("#coinbase-order-size", Input).value = "0.01"
            app.query_one("#coinbase-order-side", Select).value = "SELL"
            app.query_one("#coinbase-order-skip-review", Checkbox).value = True
            app.query_one("#coinbase-order-armed", Checkbox).value = True
            await pilot.pause()
            original = app._call
            calls = []
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_quick":
                    calls.append(params)
                    return envelope({"order_id": "sell-1", "status": "FILLED" if len(calls) == 1 else "OPEN"})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._coinbase_order_quick_pressed()
                await pilot.pause(.25)
                self.assertEqual(calls[0]["size_currency"], "base")
                self.assertEqual(calls[0]["side"], "SELL")
                self.assertTrue(app.query_one("#coinbase-order-armed", Checkbox).value)
                self.assertTrue(app.query_one("#coinbase-order-skip-review", Checkbox).value)
                self.assertFalse(app.query_one("#coinbase-order-quick", Button).disabled)
                self.assertFalse(app._coinbase_order_unknown)
                self.assertIn("sell-1", str(app.query_one("#coinbase-order-receipt", Static).render()))
                app._coinbase_order_quick_pressed()
                await pilot.pause(.25)
                self.assertEqual(len(calls), 2)
                self.assertFalse(app.query_one("#coinbase-order-armed", Checkbox).value)
                self.assertTrue(app._coinbase_order_unknown)
                self.assertTrue(app.query_one("#coinbase-order-quick", Button).disabled)

    async def test_review_is_disarmed_then_explicit_submit_occurs_once(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-wallet"
            app.query_one("#coinbase-order-size", Input).value = "1.10"
            await pilot.pause()
            calls = []
            original = app._call
            def call(name, params=None, **kwargs):
                if not name.startswith("coinbase.order_"):
                    return original(name, params, **kwargs)
                calls.append((name, params))
                if name == "coinbase.order_preview":
                    return envelope(preview())
                if name == "coinbase.order_submit":
                    return envelope({"order_id": "order-1", "status": "FILLED"})
                return envelope({})
            with mock.patch.object(app, "_call", side_effect=call):
                app._coinbase_order_preview_pressed()
                await pilot.pause(.25)
                self.assertEqual(calls[0][1], {"product_id":"SOL-USDC", "side":"BUY", "size":"1.10", "size_currency":"quote"})
                self.assertTrue(app.query_one("#coinbase-order-submit", Button).disabled)
                self.assertIn("Estimate only", str(app.query_one("#coinbase-order-review", Static).render()))
                app.query_one("#coinbase-order-armed", Checkbox).value = True
                await pilot.pause()
                self.assertFalse(app.query_one("#coinbase-order-submit", Button).disabled)
                app._coinbase_order_submit_pressed()
                app._coinbase_order_submit_pressed()
                await pilot.pause(.25)
                self.assertEqual([n for n, _ in calls].count("coinbase.order_submit"), 1)
                self.assertEqual(calls[-1][1], {"preview_id":"preview-1", "confirm":True})
                self.assertEqual(app.query_one("#coinbase-order-id", Input).value, "order-1")
                self.assertFalse(app.query_one("#coinbase-order-armed", Checkbox).value)
                self.assertIn("FILLED", str(app.query_one("#coinbase-order-receipt", Static).render()))

    async def test_refreshing_safety_state_disarms_and_clears_review(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            app.query_one("#coinbase-order-size", Input).value = "1.10"
            await pilot.pause()
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_preview":
                    return envelope(preview())
                if name == "coinbase.order_state":
                    return envelope({"unresolved":False, "orders":[]})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._coinbase_order_preview_pressed()
                await pilot.pause(.25)
                app.query_one("#coinbase-order-armed", Checkbox).value = True
                await pilot.pause()
                self.assertFalse(app.query_one("#coinbase-order-submit", Button).disabled)
                app._coinbase_order_state_start()
                await pilot.pause(.25)
                self.assertFalse(app.query_one("#coinbase-order-armed", Checkbox).value)
                self.assertIsNone(app._coinbase_order_preview_data)
                self.assertTrue(app.query_one("#coinbase-order-submit", Button).disabled)

    async def test_changed_input_discards_delayed_preview_and_ui_remains_responsive(self):
        app = SolTuiApp(make_settings())
        entered, release = threading.Event(), threading.Event()
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            app.query_one("#coinbase-order-size", Input).value = "1.10"
            await pilot.pause()
            original = app._call
            def call(name, params=None, **kwargs):
                if name != "coinbase.order_preview":
                    return original(name, params, **kwargs)
                entered.set()
                release.wait(3)
                return envelope(preview())
            try:
                with mock.patch.object(app, "_call", side_effect=call):
                    app._coinbase_order_preview_pressed()
                    for _ in range(20):
                        if entered.is_set():
                            break
                        await pilot.pause(.03)
                    self.assertTrue(entered.is_set())
                    app.query_one("#coinbase-order-armed", Checkbox).value = True
                    app._coinbase_order_state_start()
                    self.assertFalse(app.query_one("#coinbase-order-armed", Checkbox).value)
                    app.query_one("#coinbase-order-size", Input).value = "2.00"
                    await pilot.pause()
                    release.set()
                    await pilot.pause(.25)
                    self.assertIsNone(app._coinbase_order_preview_data)
                    self.assertTrue(app.query_one("#coinbase-order-submit", Button).disabled)
            finally:
                release.set()

    async def test_unknown_submit_blocks_another_attempt_and_supports_status_check(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            app.query_one("#coinbase-order-size", Input).value = "1.10"
            app.query_one("#coinbase-order-armed", Checkbox).value = True
            await pilot.pause()
            calls = []
            original = app._call
            unrelated = True
            def call(name, params=None, **kwargs):
                if not name.startswith("coinbase.order_"):
                    return original(name, params, **kwargs)
                calls.append(name)
                if name == "coinbase.order_preview":
                    return envelope(preview())
                if name == "coinbase.order_submit":
                    return {"ok": False, "error": {"message":"Outcome unknown"}}
                return envelope({"order_id":"order-2", "status":"FILLED", **({} if unrelated else {"unresolved":False})})
            with mock.patch.object(app, "_call", side_effect=call):
                app._coinbase_order_preview_pressed()
                await pilot.pause(.25)
                app._coinbase_order_submit_pressed()
                await pilot.pause(.25)
                self.assertTrue(app._coinbase_order_unknown)
                self.assertTrue(app.query_one("#coinbase-order-preview", Button).disabled)
                self.assertIn("Do not resubmit", str(app.query_one("#coinbase-order-message", Static).render()))
                app._coinbase_order_preview_pressed()
                self.assertEqual(calls.count("coinbase.order_preview"), 1)
                app.query_one("#coinbase-order-id", Input).value = "order-2"
                app._coinbase_order_check_pressed()
                await pilot.pause(.25)
                self.assertTrue(app._coinbase_order_unknown)
                unrelated = False
                app._coinbase_order_check_pressed()
                await pilot.pause(.25)
                self.assertFalse(app._coinbase_order_unknown)
                self.assertEqual(calls.count("coinbase.order_submit"), 1)

    async def test_sell_preview_uses_base_size_and_expired_review_is_refused(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            app.query_one("#coinbase-order-side", Select).value = "SELL"
            app.query_one("#coinbase-order-size", Input).value = "0.02"
            await pilot.pause()
            observed = []
            original = app._call
            def call(name, params=None, **kwargs):
                if name != "coinbase.order_preview":
                    return original(name, params, **kwargs)
                observed.append(params)
                return envelope({"preview_id":"x", "product_id":"SOL-USDC", "side":"SELL", "size":"0.02",
                                 "size_currency":"base", "expires_at":time.time()-1, "estimate":{}})
            with mock.patch.object(app, "_call", side_effect=call):
                app._coinbase_order_preview_pressed()
                await pilot.pause(.25)
            self.assertEqual(observed[0]["size_currency"], "base")
            self.assertIsNone(app._coinbase_order_preview_data)
            self.assertTrue(app.query_one("#coinbase-order-submit", Button).disabled)

    async def test_manual_order_fields_fit_a_narrow_terminal(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=(100, 45)) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause()
            for name in ("#coinbase-order-product", "#coinbase-order-side", "#coinbase-order-size",
                         "#coinbase-order-armed", "#coinbase-order-preview", "#coinbase-order-submit",
                         "#coinbase-order-id", "#coinbase-order-check", "#coinbase-order-state"):
                widget = app.query_one(name)
                self.assertGreater(widget.region.width, 0, name)
                self.assertLessEqual(widget.region.right, 100, name)

    async def test_restart_shows_unresolved_order_before_review(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            self.assertTrue(app.query_one("#coinbase-order-preview", Button).disabled)
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_state":
                    return envelope({"unresolved":True, "orders":[{"order_id":"pending-1", "state":"unknown"}]})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app.query_one(TabbedContent).active = "tab-wallet"
                await pilot.pause(.3)
            self.assertTrue(app._coinbase_order_unknown)
            self.assertTrue(app.query_one("#coinbase-order-preview", Button).disabled)
            self.assertIn("pending-1", str(app.query_one("#coinbase-order-receipt", Static).render()))

    async def test_filter_and_select_spot_pair_only_fills_disarmed_form(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            original = app._call
            calls = []
            def call(name, params=None, **kwargs):
                if name != "coinbase.pairs":
                    return original(name, params, **kwargs)
                calls.append(name)
                pairs = ["SOL-USDC", "BTC-USD"]
                needle = (params or {}).get("query", "").upper()
                return envelope({"scope":"SPOT", "complete":True, "count":2,
                                 "pairs":[p for p in pairs if needle in p]})
            with mock.patch.object(app, "_call", side_effect=call):
                app.query_one("#coinbase-pairs-query", Input).value = "btc"
                app._coinbase_pairs_filter()
                await pilot.pause(.3)
                table = app.query_one("#coinbase-pairs-table", DataTable)
                self.assertEqual(table.row_count, 1)
                app.query_one("#coinbase-order-armed", Checkbox).value = True
                table.focus()
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(app.query_one("#coinbase-order-product", Input).value, "BTC-USD")
                self.assertFalse(app.query_one("#coinbase-order-armed", Checkbox).value)
                self.assertTrue(app.query_one("#coinbase-order-submit", Button).disabled)
                self.assertEqual(calls, ["coinbase.pairs"])

    async def test_older_filter_result_cannot_replace_newer_result(self):
        app = SolTuiApp(make_settings())
        started, release = threading.Event(), threading.Event()
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.3)
            original = app._call
            def call(name, params=None, **kwargs):
                if name != "coinbase.pairs":
                    return original(name, params, **kwargs)
                query = (params or {}).get("query", "")
                if query == "SOL":
                    started.set()
                    release.wait(3)
                return envelope({"scope":"SPOT", "complete":True, "count":2,
                                 "pairs":["SOL-USDC" if query == "SOL" else "BTC-USD"]})
            try:
                with mock.patch.object(app, "_call", side_effect=call):
                    app.query_one("#coinbase-pairs-query", Input).value = "SOL"
                    app._coinbase_pairs_start()
                    for _ in range(20):
                        if started.is_set():
                            break
                        await pilot.pause(.03)
                    self.assertTrue(started.is_set())
                    app.query_one("#coinbase-pairs-query", Input).value = "BTC"
                    app._coinbase_pairs_start()
                    await pilot.pause(.25)
                    release.set()
                    await pilot.pause(.3)
                    table = app.query_one("#coinbase-pairs-table", DataTable)
                    self.assertEqual(table.row_count, 1)
                    self.assertEqual(str(next(iter(table.rows)).value), "BTC-USD")
            finally:
                release.set()


if __name__ == "__main__":
    unittest.main()
