"""Advanced order ticket: fail closed and dispatch only mocked Coinbase requests."""
import time
import unittest
from unittest import mock

from textual.widgets import Button, Checkbox, Input, Select, TabbedContent

from soltui.tests.test_tui import TEST_SIZE, make_settings
from soltui.tui import SolTuiApp


def env(result):
    return {"ok": True, "result": result, "error": None}


class AdvancedOrderUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_token_search_displays_full_mint_without_arming(self):
        from textual.widgets import Static
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.3)
            query = app.query_one("#advanced-token-query", Input)
            query.value = "SOL"
            mint = "So11111111111111111111111111111111111111112"
            app._advanced_token_search_done("SOL", env({"tokens": [{"symbol": "SOL", "name": "Solana",
                "mint": mint, "decimals": 9, "verified": True}]}))
            self.assertIn(mint, str(app.query_one("#advanced-token-results", Static).render()))
            self.assertFalse(app.query_one("#advanced-armed", Checkbox).value)
            app._advanced_token_search_done("STALE", env({"tokens": []}))
            self.assertIn(mint, str(app.query_one("#advanced-token-results", Static).render()))

    async def test_unsupported_choices_block_live_actions_and_preserve_manual_text(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.4)
            app._coinbase_order_unknown = False
            app.query_one("#coinbase-order-size", Input).value = "12.34"
            app.query_one("#advanced-size", Input).value = "1"
            app.query_one("#advanced-armed", Checkbox).value = True
            await pilot.pause()
            for field, value in (("#advanced-venue", "jupiter"), ("#advanced-leverage", "2x"),
                                 ("#advanced-position", "short")):
                app.query_one(field, Select).value = value
                await pilot.pause()
                self.assertTrue(app.query_one("#advanced-preview", Button).disabled)
                self.assertTrue(app.query_one("#advanced-submit", Button).disabled)
                if field == "#advanced-venue":
                    app.query_one(field, Select).value = "coinbase"
                elif field == "#advanced-leverage":
                    app.query_one(field, Select).value = "1x"
                else:
                    app.query_one(field, Select).value = "long"
                await pilot.pause()
            app.query_one("#advanced-side", Select).value = "SELL"
            app.query_one("#advanced-unit", Select).value = "quote"
            await pilot.pause()
            self.assertTrue(app.query_one("#advanced-preview", Button).disabled)
            self.assertEqual(app.query_one("#coinbase-order-size", Input).value, "12.34")

    async def test_buy_coin_preview_quick_and_shared_safety(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.4)
            app._coinbase_order_unknown = False
            app.query_one("#advanced-size", Input).value = "0.5"
            app.query_one("#advanced-unit", Select).value = "base"
            await pilot.pause()
            calls = []
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_preview":
                    calls.append((name, params))
                    return env({**params, "preview_id": "p1", "expires_at": time.time() + 60,
                                "estimate": {}, "notice": "estimate"})
                if name == "coinbase.order_quick":
                    calls.append((name, params))
                    return env({"order_id": "order-1", "status": "FILLED"})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._advanced_preview_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls[0][1]["size_currency"], "base")
                self.assertIsNotNone(app._advanced_preview_data)
                app.query_one("#advanced-skip-review", Checkbox).value = True
                app.query_one("#advanced-armed", Checkbox).value = True
                await pilot.pause()
                self.assertTrue(app.query_one("#coinbase-order-skip-review", Checkbox).value)
                app._coinbase_order_busy = True
                app._coinbase_order_controls()
                self.assertTrue(app.query_one("#advanced-quick", Button).disabled)
                app._coinbase_order_busy = False
                app._coinbase_order_unknown = True
                app._coinbase_order_controls()
                self.assertTrue(app.query_one("#advanced-quick", Button).disabled)
                app._coinbase_order_unknown = False
                app._advanced_quick_pressed()
                app._advanced_quick_pressed()
                await pilot.pause(.3)
                self.assertEqual([x[0] for x in calls].count("coinbase.order_quick"), 1)
                self.assertEqual(calls[-1][1]["size_currency"], "base")
                self.assertEqual(calls[-1][1]["skip_confirm"], True)

    async def test_timestamped_context_uses_matching_prices_and_recorded_ranked_forecasts(self):
        from textual.widgets import Sparkline, Static
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.3)
            now = time.time()
            prices = env({"live": True, "prices": {"SOL-USDC": {"mid": 123.4, "quote_age_s": 2}}})
            forecasts = env({"rows": [
                {"asset": "SOL", "label": "thin", "resolved": 1, "correct": 1, "minutes": 5,
                 "last_call": 1, "last_issued": now - 10},
                {"asset": "SOL", "label": "ranked", "resolved": 20, "correct": 15, "minutes": 5,
                 "last_call": -1, "last_issued": now - 1000, "settings": [{"name": "rsi", "params": {}}]},
                {"asset": "BTC", "label": "other", "resolved": 100, "correct": 100, "minutes": 5,
                 "last_call": 1, "last_issued": now - 10}]})
            app._advanced_context_done("SOL-USDC", prices, forecasts, now)
            self.assertEqual(app.query_one("#advanced-chart", Sparkline).data, [123.4])
            self.assertIn("UTC", str(app.query_one("#advanced-chart-status", Static).render()))
            text = str(app.query_one("#advanced-forecast-status", Static).render())
            self.assertIn("ranked", text)
            self.assertIn("15/20", text)
            self.assertIn("stale", text)
            self.assertIn("SOL-USD", text)

    async def test_review_consumed_once_and_unknown_locks_both_tickets(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.4)
            app._coinbase_order_unknown = False
            app.query_one("#advanced-size", Input).value = "1"
            await pilot.pause()
            original = app._call
            calls = []
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_preview":
                    return env({**params, "preview_id": "reviewed", "expires_at": time.time() + 60,
                                "estimate": {}, "notice": "estimate"})
                if name == "coinbase.order_submit":
                    calls.append((name, params))
                    return {"ok": False, "error": {"message": "outcome unknown"}}
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._advanced_preview_pressed()
                await pilot.pause(.3)
                app.query_one("#advanced-armed", Checkbox).value = True
                await pilot.pause()
                app._advanced_submit_pressed()
                app._advanced_submit_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls, [("coinbase.order_submit", {"preview_id": "reviewed", "confirm": True})])
                self.assertTrue(app._coinbase_order_unknown)
                self.assertFalse(app.query_one("#advanced-armed", Checkbox).value)
                self.assertTrue(app.query_one("#advanced-preview", Button).disabled)
                self.assertTrue(app.query_one("#coinbase-order-preview", Button).disabled)

    async def test_percent_preview_and_quick_use_balance_commands(self):
        from textual.widgets import Static
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.4)
            app._coinbase_order_unknown = False
            app.query_one("#advanced-unit", Select).value = "percent"
            app.query_one("#advanced-size", Input).value = "5"
            await pilot.pause()
            calls = []
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_percent_preview":
                    calls.append((name, params))
                    return env({"product_id": "SOL-USDC", "side": "BUY", "size": "2.50", "size_currency": "quote",
                                "balance_percentage": "5", "sizing_notice": "5% of available USDC, rounded down.",
                                "preview_id": "percent-preview", "expires_at": time.time() + 60, "estimate": {}})
                if name == "coinbase.order_percent_quick":
                    calls.append((name, params))
                    return env({"order_id": "percent-order", "status": "FILLED"})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._advanced_preview_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls[0], ("coinbase.order_percent_preview", {"product_id": "SOL-USDC", "side": "BUY", "percent": "5"}))
                self.assertIn("2.50 quote", str(app.query_one("#advanced-review", Static).render()))
                app.query_one("#advanced-skip-review", Checkbox).value = True
                app.query_one("#advanced-armed", Checkbox).value = True
                await pilot.pause()
                app._advanced_quick_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls[-1], ("coinbase.order_percent_quick", {"product_id": "SOL-USDC", "side": "BUY", "percent": "5", "skip_confirm": True}))

    async def test_conditional_limit_review_stale_change_and_resting_lock(self):
        from textual.widgets import Static
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.4)
            app._coinbase_order_unknown = False
            app.query_one("#advanced-type", Select).value = "limit"
            app.query_one("#advanced-size", Input).value = "0.1"
            app.query_one("#advanced-limit-price", Input).value = "100"
            await pilot.pause()
            calls = []
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_conditional_preview":
                    calls.append((name, params))
                    return env({**params, "size_currency": "base", "preview_id": "limit-p", "expires_at": time.time() + 60,
                                "estimate": {"fee": "0.02"}, "notice": "GTC"})
                if name == "coinbase.order_submit":
                    calls.append((name, params))
                    return env({"order_id": "resting", "status": "OPEN"})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._advanced_preview_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls[0][1]["size"], "0.1")
                self.assertEqual(calls[0][1]["order_type"], "limit")
                review = str(app.query_one("#advanced-review", Static).render())
                self.assertIn("Estimated fee: 0.02", review)
                self.assertIn("Maker/taker", review)
                app.query_one("#advanced-limit-price", Input).value = "101"
                await pilot.pause()
                self.assertIsNone(app._advanced_preview_data)
                app._advanced_preview_pressed()
                await pilot.pause(.3)
                app.query_one("#advanced-armed", Checkbox).value = True
                await pilot.pause()
                app._advanced_submit_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls[-1], ("coinbase.order_submit", {"preview_id":"limit-p", "confirm":True}))
                self.assertTrue(app._coinbase_order_unknown)
                self.assertTrue(app.query_one("#coinbase-order-preview", Button).disabled)
                self.assertFalse(app.query_one("#advanced-armed", Checkbox).value)

    async def test_bracket_constraints_and_opted_in_quick_submit(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-advanced-order"
            await pilot.pause(.4)
            app._coinbase_order_unknown = False
            app.query_one("#advanced-type", Select).value = "bracket"
            app.query_one("#advanced-size", Input).value = "0.1"
            app.query_one("#advanced-limit-price", Input).value = "200"
            app.query_one("#advanced-stop-price", Input).value = "100"
            await pilot.pause()
            self.assertTrue(app.query_one("#advanced-conditional-preview", Button).disabled)
            app.query_one("#advanced-side", Select).value = "SELL"
            app.query_one("#advanced-unit", Select).value = "percent"
            await pilot.pause()
            self.assertTrue(app.query_one("#advanced-conditional-preview", Button).disabled)
            app.query_one("#advanced-unit", Select).value = "base"
            app.query_one("#advanced-skip-review", Checkbox).value = True
            app.query_one("#advanced-armed", Checkbox).value = True
            await pilot.pause()
            calls = []
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "coinbase.order_conditional_quick":
                    calls.append(params)
                    return env({"order_id":"bracket", "status":"OPEN"})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call):
                app._advanced_quick_pressed()
                await pilot.pause(.3)
                self.assertEqual(calls, [{"product_id":"SOL-USDC", "side":"SELL", "size":"0.1", "order_type":"bracket",
                                          "limit_price":"200", "stop_price":"100", "skip_confirm":True}])
                self.assertTrue(app._coinbase_order_unknown)
                self.assertFalse(app.query_one("#advanced-armed", Checkbox).value)
