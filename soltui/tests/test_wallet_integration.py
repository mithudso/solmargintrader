"""Wallet discovery wired into the console: Settings addresses, the key-source row, `portfolio.scan`,
the Wallet tab, and the separate `wallet (live)` section of the P&L tab.

The network is replaced by the recorded-fixture `Fake` from test_wallet; nothing here reads a key file.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import DataTable, Input, Select, TabbedContent

from soltui import commands, config, pnl, portfolio, wallet
from soltui.tests.bridge_support import World
from soltui.tests.test_tui import (
    TEST_SIZE,
    make_settings,
    offline_console_reads,
    text_of,
)
from soltui.tests.test_wallet import BASE_ADDR, SOL_ADDR, Fake
from soltui.tui import SolTuiApp


class Env(unittest.TestCase):
    def setUp(self) -> None:
        self.world = World().__enter__()
        self.addCleanup(self.world.__exit__)
        self.fake = Fake()
        self.keys = self.world.root / "keys"
        self.keys.mkdir()
        p = mock.patch.object(wallet, "HttpFetcher", lambda *a, **k: self.fake)
        p.start()
        self.addCleanup(p.stop)

    def call(self, name, params=None):
        return commands.dispatch(name, params or {}, surface="cli")


class SettingsTests(Env):
    def test_the_owners_public_addresses_are_prefilled(self) -> None:
        s = config.default_settings()
        self.assertEqual(s.solana_address, SOL_ADDR)
        self.assertEqual(s.base_address, BASE_ADDR)

    def test_there_is_no_private_key_field_anywhere_in_settings(self) -> None:
        names = {f.name for f in __import__("dataclasses").fields(config.Settings)}
        for bad in ("private", "secret", "mnemonic", "seed", "key"):
            self.assertFalse([n for n in names if bad in n], bad)
        env = self.call("settings.get")
        self.assertNotIn("private", json.dumps(env["result"]["settings"]).lower().replace("private-key", ""))

    def test_addresses_save_and_round_trip(self) -> None:
        other = "0x" + "ab" * 20
        env = self.call("settings.save", {"base_address": other})
        self.assertTrue(env["ok"], env)
        self.assertEqual(config.load_settings().base_address, other)
        self.assertEqual(config.load_settings().solana_address, SOL_ADDR)

    def test_a_malformed_address_is_refused_and_blank_clears(self) -> None:
        for field, bad in (("solana_address", "nope"), ("base_address", "0x123")):
            env = self.call("settings.save", {field: bad})
            self.assertFalse(env["ok"])
            self.assertIn("not a", env["error"]["message"])
        self.assertTrue(self.call("settings.save", {"base_address": ""})["ok"])
        self.assertEqual(config.load_settings().base_address, "")


class KeySourceCommandTests(Env):
    def test_reports_mode_and_never_the_contents(self) -> None:
        (self.keys / "wallet.private").write_text("TOP-SECRET-KEY-TEXT")
        (self.keys / "wallet.private").chmod(0o600)
        (self.keys / "solana.private").write_text("TOP-SECRET-KEY-TEXT")
        (self.keys / "solana.private").chmod(0o640)
        env = self.call("wallet.key_sources")
        self.assertTrue(env["ok"])
        text = json.dumps(env)
        self.assertNotIn("TOP-SECRET", text)
        by = {k["chain"]: k for k in env["result"]["keys"]}
        self.assertTrue(by["base"]["mode_600"])
        self.assertFalse(by["solana"]["mode_600"])
        self.assertTrue(commands.COMMANDS["wallet.key_sources"].read_only)


class ScanCommandTests(Env):
    def test_scan_both_chains_and_records_history(self) -> None:
        env = self.call("portfolio.scan")
        self.assertTrue(env["ok"], env)
        r = env["result"]
        self.assertEqual(r["label"], "wallet (live)")
        self.assertEqual(set(r["chains"]), {"solana", "base"})
        snaps = portfolio.load_snapshots()
        self.assertEqual(len(snaps), 1)
        self.assertAlmostEqual(snaps[0]["total_usd"], r["total_usd"])

    def test_record_false_leaves_no_history(self) -> None:
        self.assertTrue(self.call("portfolio.scan", {"record": False})["ok"])
        self.assertEqual(portfolio.load_snapshots(), [])

    def test_a_one_chain_scan_is_not_recorded_as_the_whole_portfolio(self) -> None:
        self.assertTrue(self.call("portfolio.scan", {"chain": "solana"})["ok"])
        self.assertEqual(portfolio.load_snapshots(), [])

    def test_one_chain(self) -> None:
        r = self.call("portfolio.scan", {"chain": "solana", "record": False})["result"]
        self.assertEqual(list(r["chains"]), ["solana"])

    def test_bad_params(self) -> None:
        for params in ({"chain": "nowhere"}, {"tokens": "0xabc"}, {"tokens": [1]}):
            env = self.call("portfolio.scan", params)
            self.assertEqual((env["ok"], env["error"]["code"]), (False, "bad_params"), params)

    def test_extra_token_addresses_reach_the_scan(self) -> None:
        other = "0x" + "11" * 20
        self.fake.balances[other] = 3 * 10**18
        self.fake.llama_extra = {f"base:{other}": {"price": 2.0, "confidence": 0.99}}
        r = self.call("portfolio.scan", {"chain": "base", "tokens": [other], "record": False})["result"]
        self.assertIn(other, [h["address"] for h in r["chains"]["base"]["holdings"]])

    def test_blank_addresses_are_skipped_with_a_reason(self) -> None:
        self.call("settings.save", {"solana_address": "", "base_address": ""})
        r = self.call("portfolio.scan")["result"]
        self.assertEqual(r["chains"], {})
        self.assertEqual(len(r["skipped"]), 2)
        self.assertEqual(portfolio.load_snapshots(), [])   # nothing scanned, nothing recorded

    def test_daemon_context_feeds_the_scan_read_only(self) -> None:
        home = Path(os.environ["AERO_LP_HOME"])
        home.mkdir(parents=True)
        (home / "status.json").write_text(json.dumps({
            "schema": "aero-lp-status/1", "mode": "live", "owner": BASE_ADDR, "generated_at": 1,
            "wallet": {"tokens": []},
            "positions": [{"token_id": 777, "pair": "A/B", "value_usd": 12.5}]}))
        r = self.call("portfolio.scan", {"chain": "base", "record": False})["result"]
        (pos,) = r["chains"]["base"]["positions"]
        self.assertEqual((pos["token_id"], pos["value_usd"]), (777, 12.5))
        self.assertEqual(sorted(p.name for p in home.iterdir()), ["status.json"])   # nothing written there


class PnlWalletSectionTests(Env):
    def scan_at(self, ts: float, total: float) -> None:
        wallet.record_scan({"ts": ts, "total_usd": total, "chains": {"solana": {"total_usd": total}}, "partial": False})

    def test_no_scan_yet_says_how_to_add_one(self) -> None:
        r = self.call("pnl.summary", {"window": "all", "source": "wallet"})["result"]
        (sec,) = r["sections"]
        self.assertEqual((sec["source"], sec["group"], sec["status"]), ("wallet (live)", "real", "no_data"))
        self.assertTrue(any("portfolio.snapshot" in n for n in sec["notes"]))

    def test_value_change_between_scans_is_a_separate_real_section(self) -> None:
        self.scan_at(pnl.parse_moment("2026-11-01"), 100.0)
        self.scan_at(pnl.parse_moment("2026-11-03"), 110.0)
        r = self.call("pnl.summary", {"window": "all", "source": "wallet"})["result"]
        (sec,) = r["sections"]
        t = sec["totals"]
        self.assertEqual((t["initial"], t["final"], t["net_usd"]), (100.0, 110.0, 10.0))
        self.assertEqual(t["net_pct_text"], "wallet (live) net +10.0%")
        # A balance is not a trading P&L: no gross, realized or unrealized figure is invented for it.
        self.assertIsNone(t["gross_usd"])
        self.assertIsNone(t["realized_usd"])
        self.assertIsNone(t["unrealized_usd"])
        self.assertTrue(any("not trading P&L" in n for n in sec["notes"]))

    def test_one_scan_has_no_change_to_report(self) -> None:
        self.scan_at(pnl.parse_moment("2026-11-01"), 100.0)
        (sec,) = self.call("pnl.summary", {"window": "all", "source": "wallet"})["result"]["sections"]
        self.assertEqual(sec["totals"]["net_usd"], 0.0)
        self.assertTrue(any("second snapshot" in n for n in sec["notes"]))

    def test_window_applies_to_the_history(self) -> None:
        self.scan_at(pnl.parse_moment("2026-11-01"), 100.0)
        self.scan_at(pnl.parse_moment("2026-11-03"), 110.0)
        self.scan_at(pnl.parse_moment("2026-11-05"), 99.0)
        r = self.call("pnl.summary", {"start": "2026-11-03", "end": "2026-11-05", "source": "wallet"})["result"]
        t = r["sections"][0]["totals"]
        self.assertEqual((t["initial"], t["final"]), (100.0, 99.0))      # base = the scan before the window

    def test_never_summed_with_simulated_sections(self) -> None:
        self.scan_at(pnl.parse_moment("2026-11-01"), 100.0)
        r = self.call("pnl.summary", {"window": "all"})["result"]
        self.assertIn("wallet (live)", r["groups"]["real"])
        self.assertNotIn("wallet (live)", r["groups"]["simulated"])
        self.assertNotIn("totals", r)

    def test_series_and_breakdown_accept_the_wallet_source(self) -> None:
        self.scan_at(pnl.parse_moment("2026-11-01"), 100.0)
        self.scan_at(pnl.parse_moment("2026-11-03"), 90.0)
        s = self.call("pnl.series", {"window": "all", "source": "wallet"})["result"]["sections"][0]
        self.assertEqual([d["pnl"] for d in s["days"]], [0.0, 0.0, -10.0])
        self.assertAlmostEqual(s["drawdown"]["max_drawdown_pct"], -0.1)
        b = self.call("pnl.breakdown", {"window": "all", "source": "wallet"})["result"]["sections"][0]
        self.assertIsNone(b["by_strategy"][0]["realized_usd"])


class WalletTabTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.enterContext(offline_console_reads())
        self.tmp = Path(tempfile.mkdtemp(prefix="soltui-wallet-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "keys").mkdir()
        (self.tmp / "keys" / "wallet.private").write_text("TOP-SECRET-KEY-TEXT")
        (self.tmp / "keys" / "wallet.private").chmod(0o600)
        self.fake = Fake()
        env = {"SOLTUI_KEY_DIR": str(self.tmp / "keys"), "SOLTUI_CONFIG_DIR": str(self.tmp / "config"),
               "SOLTUI_LOG_DIR": str(self.tmp / "logs"), "AERO_LP_HOME": str(self.tmp / "aero"),
               "SOLTUI_SUPPORT_DIR": str(self.tmp / "support")}
        for p in (mock.patch.dict(os.environ, env),
                  mock.patch.object(wallet, "HttpFetcher", lambda *a, **k: self.fake)):
            p.start()
            self.addCleanup(p.stop)

    async def test_settings_tab_shows_addresses_and_the_key_source_row_and_no_key_field(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            self.assertEqual(app.query_one("#set-solana_address", Input).value, SOL_ADDR)
            self.assertEqual(app.query_one("#set-base_address", Input).value, BASE_ADDR)
            rows = text_of(app, "#key-sources")
            self.assertIn("wallet.private: present, mode 0600", rows)
            self.assertIn("solana.private: missing", rows)
            self.assertIn("separate gated component", rows)
            self.assertNotIn("TOP-SECRET", rows)
            for field in app.query(Input):
                text = f"{field.id} {field.placeholder}".lower()
                for bad in ("private", "secret", "mnemonic", "seed phrase"):
                    self.assertNotIn(bad, text)
                self.assertFalse(field.password)

    async def test_scan_fills_holdings_and_contracts_and_the_summary_names_the_label(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause()
            app._wallet_scan()
            await pilot.pause(1.5)
            summary = text_of(app, "#wallet-summary")
            self.assertIn("wallet (live) total $", summary)
            self.assertIn("solana: wallet (live)", summary)
            self.assertIn("Cloudflare", summary)                    # the blocked indexer is named, not hidden
            holdings = app.query_one("#wallet-holdings", DataTable)
            names = {str(holdings.get_row_at(i)[1]) for i in range(holdings.row_count)}
            self.assertTrue({"SOL", "JupSOL", "ETH", "USDC"} <= names, names)
            contracts = app.query_one("#wallet-contracts", DataTable)
            links = [str(contracts.get_row_at(i)[5]) for i in range(contracts.row_count)]
            self.assertTrue(any(l.startswith("https://solscan.io/token/") for l in links))
            self.assertTrue(any(l.startswith("https://basescan.org/") for l in links))
            await app.workers.wait_for_complete()
            self.assertEqual(len(portfolio.load_snapshots()), 1)

    async def test_flagged_airdrop_is_shown_as_excluded(self) -> None:
        from soltui.tests.test_wallet import SPAM_MINT
        self.fake.sol_tokens = {"value": self.fake.sol_tokens["value"] + [{
            "pubkey": "SpamAcct", "account": {"data": {"parsed": {"info": {
                "mint": SPAM_MINT, "tokenAmount": {"uiAmountString": "1000", "decimals": 6}}}}}}]}
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause()
            app.query_one("#wallet-chain", Select).value = "solana"
            app._wallet_scan()
            await pilot.pause(1.5)
            holdings = app.query_one("#wallet-holdings", DataTable)
            states = [str(holdings.get_row_at(i)[5]) for i in range(holdings.row_count)]
            self.assertTrue(any(s.startswith("airdrop-flagged, excluded") for s in states), states)
            self.assertIn("1 airdrop-flagged (excluded)", text_of(app, "#wallet-summary"))
            await app.workers.wait_for_complete()

    async def test_wallet_section_appears_in_the_pnl_tab_after_scans(self) -> None:
        wallet.record_scan({"ts": pnl.parse_moment("2026-11-01"), "total_usd": 50.0,
                            "chains": {}, "partial": False})
        wallet.record_scan({"ts": pnl.parse_moment("2026-11-02"), "total_usd": 55.0,
                            "chains": {}, "partial": False})
        app = SolTuiApp(make_settings())
        rendered = asyncio.Event()
        original_render = app._render_pnl

        def render_complete(envs):
            original_render(envs)
            rendered.set()

        # Tab activation queues loading before a worker may even be registered.
        # Observe the real render callback, including its final table updates.
        with mock.patch.object(app, "_render_pnl", render_complete):
            async with app.run_test(size=TEST_SIZE):
                app.query_one("#pnl-window", Select).value = "all"
                app.query_one("#pnl-source", Select).value = "wallet (live)"
                app.query_one(TabbedContent).active = "tab-pnl"
                async with asyncio.timeout(10):
                    await rendered.wait()
                summary = text_of(app, "#pnl-summary")
                self.assertIn("wallet (live) (real)", summary)
                self.assertIn("wallet (live) net +10.0%", summary)
                self.assertEqual(app.query_one("#pnl-strategies", DataTable).row_count, 1)


if __name__ == "__main__":
    unittest.main()
