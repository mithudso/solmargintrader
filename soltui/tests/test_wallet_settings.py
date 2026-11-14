"""Wallet fields in Settings: validation, private-key refusal, redaction, file mode, and the read-only
`wallet.addresses` command the extension's Wallet pubkey button uses."""

from __future__ import annotations

import json
import os
import stat
import struct
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Input

from soltui import commands, config, hdwallet, wallet
from soltui.tests.bridge_support import World
from soltui.tests.test_hdwallet import V2_M, V2_M0
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tests.test_wallet import BASE_ADDR, SOL_ADDR
from soltui.tui import SolTuiApp

ETH = "0x" + "12" * 20


def xprv() -> str:
    return hdwallet.b58check_encode(struct.pack(">I", 0x0488ADE4) + bytes([0]) + b"\0" * 8 + b"\x22" * 32
                                    + bytes([0]) + b"\x11" * 32)


class ValidationTests(unittest.TestCase):
    def test_new_fields_default_to_blank(self) -> None:
        s = config.default_settings()
        self.assertEqual((s.btc_xpub, s.ltc_xpub, s.doge_xpub, s.eth_address), ("", "", "", ""))
        self.assertTrue(s.forwardtest_autostart)

    def test_forwardtest_autostart_validation(self) -> None:
        config.validate(config.Settings(forwardtest_autostart=False))
        with self.assertRaises(config.ConfigError):
            config.validate(config.Settings(forwardtest_autostart="invalid"))

    def test_good_values_validate(self) -> None:
        config.validate(config.Settings(btc_xpub=V2_M, ltc_xpub=V2_M, doge_xpub=V2_M, eth_address=ETH))

    def test_every_wallet_field_refuses_private_material_without_echoing_it(self) -> None:
        secrets = {"xprv": xprv(), "hex": "ab" * 32, "array": json.dumps(list(range(64)))}
        for field in ("btc_xpub", "ltc_xpub", "doge_xpub", "eth_address", "solana_address", "base_address",
                      "hyperliquid_address"):
            for kind, secret in secrets.items():
                with self.subTest(field=field, kind=kind):
                    with self.assertRaises(config.ConfigError) as ctx:
                        config.validate(config.Settings(**{field: secret}))
                    msg = str(ctx.exception)
                    self.assertIn(field, msg)
                    self.assertIn("Private keys do not belong in settings", msg)
                    self.assertNotIn(secret[:10], msg)

    def test_a_coin_mismatch_and_a_bad_checksum_are_refused(self) -> None:
        with self.assertRaisesRegex(config.ConfigError, "btc_xpub"):
            config.validate(config.Settings(btc_xpub=V2_M[:-1] + "1"))
        with self.assertRaisesRegex(config.ConfigError, "ltc_xpub"):
            config.validate(config.Settings(ltc_xpub="xpub-nope"))
        with self.assertRaisesRegex(config.ConfigError, "eth_address"):
            config.validate(config.Settings(eth_address="0x123"))


class SaveAndRedactTests(unittest.TestCase):
    def test_the_file_is_mode_600_and_keeps_the_full_key(self) -> None:
        with World():
            env = commands.dispatch("settings.save", {"btc_xpub": V2_M, "eth_address": ETH}, surface="cli")
            self.assertTrue(env["ok"], env)
            self.assertEqual(stat.S_IMODE(os.stat(config.CONFIG_PATH).st_mode), 0o600)
            self.assertEqual(config.load_settings().btc_xpub, V2_M)

    def test_an_existing_loose_file_is_tightened_on_save(self) -> None:
        with World():
            config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config.CONFIG_PATH.write_text("asset: SOL\n")
            config.CONFIG_PATH.chmod(0o644)
            config.save_settings(config.Settings(btc_xpub=V2_M))
            self.assertEqual(stat.S_IMODE(os.stat(config.CONFIG_PATH).st_mode), 0o600)

    def test_surfaces_show_a_prefix_never_the_full_xpub(self) -> None:
        with World():
            saved = commands.dispatch("settings.save", {"btc_xpub": V2_M, "ltc_xpub": V2_M0}, surface="cli")
            got = commands.dispatch("settings.get", {}, surface="cli")
            for env in (saved, got):
                text = json.dumps(env)
                self.assertNotIn(V2_M[8:], text)
                self.assertNotIn(V2_M0[8:], text)
                s = env["result"]["settings"]
                self.assertEqual(s["btc_xpub"], "xpub66…")
                self.assertTrue(s["btc_xpub_set"])
                self.assertFalse(s["doge_xpub_set"])

    def test_empty_string_clears_and_omission_keeps(self) -> None:
        with World():
            commands.dispatch("settings.save", {"btc_xpub": V2_M}, surface="cli")
            commands.dispatch("settings.save", {"capital": 5000}, surface="cli")
            self.assertEqual(config.load_settings().btc_xpub, V2_M)
            commands.dispatch("settings.save", {"btc_xpub": ""}, surface="cli")
            self.assertEqual(config.load_settings().btc_xpub, "")

    def test_saving_a_private_key_fails_and_writes_nothing(self) -> None:
        with World():
            secret = xprv()
            env = commands.dispatch("settings.save", {"btc_xpub": secret}, surface="cli")
            self.assertFalse(env["ok"])
            self.assertIn("Private keys do not belong in settings", env["error"]["message"])
            self.assertNotIn(secret[:10], json.dumps(env))
            self.assertFalse(config.CONFIG_PATH.exists())

    def test_the_call_log_records_keys_not_values(self) -> None:
        with World() as world:
            commands.dispatch("settings.save", {"btc_xpub": V2_M}, surface="cli")
            text = world.log.read_text()
            self.assertIn("btc_xpub", text)
            self.assertNotIn(V2_M[8:], text)

    def test_forwardtest_autostart_saved_and_loaded(self) -> None:
        with World():
            commands.dispatch("settings.save", {"forwardtest_autostart": False}, surface="cli")
            self.assertFalse(config.load_settings().forwardtest_autostart)
            commands.dispatch("settings.save", {"forwardtest_autostart": True}, surface="cli")
            self.assertTrue(config.load_settings().forwardtest_autostart)


class AddressesCommandTests(unittest.TestCase):
    def test_returns_public_addresses_only(self) -> None:
        with World():
            commands.dispatch("settings.save", {"btc_xpub": V2_M, "eth_address": ETH}, surface="cli")
            env = commands.dispatch("wallet.addresses", {}, surface="native")
            self.assertTrue(env["ok"])
            r = env["result"]
            self.assertEqual(r["solana_address"], SOL_ADDR)
            self.assertEqual(r["base_address"], BASE_ADDR)
            self.assertEqual(r["eth_address"], ETH)
            self.assertEqual(r["hyperliquid_address"], BASE_ADDR)  # the owner's Hyperliquid account is the Base address
            self.assertEqual(set(r), {"solana_address", "base_address", "eth_address", "hyperliquid_address", "note"})
            text = json.dumps(env)
            self.assertNotIn(V2_M[4:], text)
            self.assertNotIn("xpub", text.replace("Extended public keys", ""))

    def test_is_read_only(self) -> None:
        self.assertTrue(commands.COMMANDS["wallet.addresses"].read_only)
        self.assertFalse(commands.COMMANDS["wallet.addresses"].requires_confirm)


class KeySourceLabelTests(unittest.TestCase):
    def test_labels_name_the_chain_family_and_the_files_are_never_opened(self) -> None:
        with World() as world:
            keys = world.root / "keys"
            keys.mkdir()
            (keys / "wallet.private").write_text("TOP-SECRET")
            (keys / "wallet.private").chmod(0o600)
            opened = []
            real_open = open

            def spy(path, *a, **k):
                opened.append(str(path))
                return real_open(path, *a, **k)

            with mock.patch("builtins.open", spy), mock.patch.object(Path, "read_text", side_effect=AssertionError):
                rows = wallet.key_sources()["keys"]
            self.assertFalse([p for p in opened if p.endswith(".private")])
            by = {r["chain"]: r["label"] for r in rows}
            self.assertEqual(by, {"base": "EVM (Ethereum/Base) key", "solana": "Solana key"})


class TuiSettingsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        super().setUp()
        from soltui.tests.test_tui import offline_console_reads
        self.enterContext(offline_console_reads())

    async def test_xpub_inputs_are_blank_and_blank_keeps_the_saved_key(self) -> None:
        config.save_settings(config.Settings(btc_xpub=V2_M))
        self.addCleanup(lambda: config.CONFIG_PATH.exists() and config.CONFIG_PATH.unlink())
        app = SolTuiApp(config.load_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            box = app.query_one("#set-btc_xpub", Input)
            self.assertEqual(box.value, "")
            self.assertIn("xpub66…", box.placeholder)
            self.assertNotIn(V2_M[8:], box.placeholder)
            self.assertEqual(app.query_one("#set-eth_address", Input).value, "")
            app._save()
            await pilot.pause()
            self.assertEqual(config.load_settings().btc_xpub, V2_M)
            box.value = "clear"
            app._save()
            await pilot.pause()
            self.assertEqual(config.load_settings().btc_xpub, "")

    async def test_pasting_a_private_key_is_refused_with_the_message_and_not_shown_back(self) -> None:
        config.save_settings(config.Settings())
        self.addCleanup(lambda: config.CONFIG_PATH.exists() and config.CONFIG_PATH.unlink())
        app = SolTuiApp(config.load_settings())
        secret = xprv()
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one("#set-ltc_xpub", Input).value = secret
            app._save()
            await pilot.pause()
            status = text_of(app, "#settings-status")
            self.assertIn("Private keys do not belong in settings", status)
            self.assertNotIn(secret[:10], status)
            self.assertEqual(config.load_settings().ltc_xpub, "")

    async def test_the_key_source_rows_are_labelled_by_family(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            rows = text_of(app, "#key-sources")
            self.assertIn("EVM (Ethereum/Base) key", rows)
            self.assertIn("Solana key", rows)

    async def test_forwardtest_autostart_toggle_and_save(self) -> None:
        """Forwardtest autostart can be toggled and saved in the settings form."""
        from textual.widgets import Checkbox, TabbedContent

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-settings"
            await pilot.pause()
            cb = app.query_one("#set-forwardtest_autostart", Checkbox)
            self.assertTrue(cb.value)
            cb.value = False
            await pilot.click("#btn-save")
            await pilot.pause()
            self.assertFalse(app.settings.forwardtest_autostart)


if __name__ == "__main__":
    unittest.main()
