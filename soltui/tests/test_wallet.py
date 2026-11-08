"""Wallet discovery on recorded fixtures: no network, no key, no transaction.

`fixtures/wallet/*.json` hold real replies recorded on 2026-11-07 for the owner's two public addresses
(Solana token accounts, Jupiter price and token data, Base eth_getBalance / balanceOf / DefiLlama /
DexScreener). Anything a recording could not show (an airdrop token, a stake account, a failing
endpoint) is built in the test from the same shapes.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from soltui import wallet
from soltui.wallet import WalletHttpError

FIX = Path(__file__).parent / "fixtures" / "wallet"
SOL_ADDR = "EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV"
BASE_ADDR = "0x901a89cEC0608eB5435A915f006b45bD46405314"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
JUPSOL = "jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v"
SPAM_MINT = "SpamSpamSpamSpamSpamSpamSpamSpamSpamSpamSpam"
SPAM_TOKEN = "0xBadBadBadBadBadBadBadBadBadBadBadBadBad0"


def load(name: str):
    return json.loads((FIX / name).read_text())


class Fake:
    """A transport that answers from fixtures and records every call it was asked to make."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.sol_stake: list = []
        self.sol_tokens = load("solana_recorded.json")["token"]["result"]
        self.sol_tokens2022: dict = {"context": {"slot": 1}, "value": []}
        self.lamports = 25_595_841
        self.jup = load("jupiter_recorded.json")
        self.base = load("base_recorded.json")
        self.errors: dict[str, Exception] = {}
        self.balances: dict[str, int] = {}          # lower-case token -> raw balance, default recorded
        self.nft_count: dict[str, int] = {}         # manager lower -> count
        self.nft_ids: dict[str, list[int]] = {}
        self.blockscout: object = WalletHttpError(403, "HTTP 403 from base.blockscout.com")
        self.llama_extra: dict = {}
        self.dex: list = list(self.base["dexscreener"])

    # -- routing ---------------------------------------------------------------------------------------
    def __call__(self, url: str, body=None):
        self.calls.append((url, body))
        for key, exc in self.errors.items():
            if key in url or (isinstance(body, dict) and key == body.get("method")):
                raise exc
        if url.startswith(wallet.SOLANA_RPC):
            return self._solana(body)
        if "blockscout" in url:
            if isinstance(self.blockscout, Exception):
                raise self.blockscout
            return self.blockscout
        if "jup.ag/price" in url:
            return {k: v for k, v in self.jup["price"].items() if k in url} | self._extra_jup_price(url)
        if "jup.ag/tokens" in url:
            return list(self.jup["tokens"]) + self._extra_jup_tokens(url)
        if "coins.llama.fi" in url:
            coins = dict(self.base["llama"]["coins"]) | self.llama_extra
            return {"coins": {k: v for k, v in coins.items() if k in url}}
        if "dexscreener" in url:
            return self.dex
        if url in wallet.BASE_RPCS:
            return self._base(body)
        raise WalletHttpError(404, f"no fixture for {url}")

    def _extra_jup_price(self, url):
        return {SPAM_MINT: {"usdPrice": 0.5, "liquidity": 12.0}} if SPAM_MINT in url else {}

    def _extra_jup_tokens(self, url):
        return [{"id": SPAM_MINT, "symbol": "CLAIM-JUP.xyz", "name": "Visit jup-rewards.xyz to claim",
                 "isVerified": False, "tags": []}] if SPAM_MINT in url else []

    def _solana(self, body):
        method, params = body["method"], body["params"]
        if method == "getBalance":
            return {"jsonrpc": "2.0", "result": {"value": self.lamports}, "id": 1}
        if method == "getTokenAccountsByOwner":
            program = params[1]["programId"]
            return {"jsonrpc": "2.0", "id": 1, "result": self.sol_tokens if program == wallet.TOKEN_PROGRAM
                    else self.sol_tokens2022}
        if method == "getProgramAccounts":
            offset = params[1]["filters"][0]["memcmp"]["offset"]
            return {"jsonrpc": "2.0", "id": 1, "result": self.sol_stake if offset == 12 else []}
        raise AssertionError(method)

    def _base(self, body):
        if isinstance(body, list):
            out = []
            for req in body:
                to, data = req["params"][0]["to"].lower(), req["params"][0]["data"]
                out.append({"jsonrpc": "2.0", "id": req["id"], "result": self._call(to, data)})
            return out
        method = body["method"]
        if method == "eth_getBalance":
            return self.base["eth_getBalance"]
        if method == "eth_call":
            return {"jsonrpc": "2.0", "id": 1, "result": self._call(body["params"][0]["to"].lower(),
                                                                    body["params"][0]["data"])}
        raise AssertionError(method)

    def _call(self, to: str, data: str):
        sel = data[:10]
        if sel == wallet.ERC20_BALANCE_OF:
            if to in {m.lower() for m in wallet.POSITION_MANAGERS.values()}:
                return f"0x{self.nft_count.get(to, 0):064x}"
            if to in self.balances:
                return f"0x{self.balances[to]:064x}"
            if to == USDC_BASE.lower():
                return self.base["balances"][0]["result"]
            return f"0x{0:064x}"
        if sel == wallet.ERC721_TOKEN_OF_OWNER:
            index = int(data[-64:], 16)
            return f"0x{self.nft_ids[to][index]:064x}"
        if sel == wallet.ERC20_DECIMALS:
            return f"0x{18:064x}"
        if sel in (wallet.ERC20_SYMBOL, wallet.ERC20_NAME):
            text = b"FREE-USDC.com" if sel == wallet.ERC20_SYMBOL else b"Claim your reward at free-usdc.com"
            return "0x" + (f"{32:064x}" + f"{len(text):064x}" + text.hex().ljust(64, "0"))
        return "0x"

    def methods(self) -> set[str]:
        out = set()
        for url, body in self.calls:
            for req in (body if isinstance(body, list) else [body]):
                if isinstance(req, dict) and "method" in req:
                    out.add(req["method"])
        return out


class SolanaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = Fake()

    def test_recorded_scan_finds_sol_and_jupsol_and_ignores_empty_accounts(self) -> None:
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        self.assertEqual(scan["status"], "ok")
        self.assertEqual(scan["label"], "wallet (live)")
        self.assertAlmostEqual(scan["native"]["amount"], 0.025595841)
        sol_price = self.fake.jup["price"][wallet.WSOL_MINT]["usdPrice"]
        self.assertAlmostEqual(scan["native"]["usd"], 0.025595841 * sol_price)
        (jup,) = scan["holdings"]
        self.assertEqual((jup["symbol"], jup["mint"], jup["program"]), ("JupSOL", JUPSOL, "Token"))
        self.assertAlmostEqual(jup["amount"], 0.449534819)
        self.assertTrue(jup["included"] and not jup["airdrop"] and jup["verified"])
        self.assertTrue(any("empty token account" in n for n in scan["notes"]))
        self.assertAlmostEqual(scan["total_usd"], scan["native"]["usd"] + jup["usd"])

    def test_contracts_name_the_mint_the_token_account_and_the_wallet_with_links(self) -> None:
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        kinds = {(c["holding"], c["kind"]): c for c in scan["contracts"]}
        self.assertEqual(kinds[("JupSOL", "token mint")]["link"], f"https://solscan.io/token/{JUPSOL}")
        acct = kinds[("JupSOL", "token account")]
        self.assertEqual(acct["address"], "HtpHtYv4KMvcetpAypkPdp6mbx2Z5FA5hLGSz58oVsco")
        self.assertEqual(acct["program"], "Token")
        self.assertEqual(kinds[("SOL", "wallet")]["link"], f"https://solscan.io/account/{SOL_ADDR}")

    def test_token_2022_accounts_are_found_too(self) -> None:
        t22 = {"pubkey": "T22acct", "account": {"data": {"parsed": {"info": {
            "mint": "T22mint", "tokenAmount": {"uiAmountString": "5", "decimals": 6}}}}}}
        self.fake.sol_tokens2022 = {"value": [t22]}
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        row = next(h for h in scan["holdings"] if h["mint"] == "T22mint")
        self.assertEqual(row["program"], "Token-2022")
        self.assertEqual(row["amount"], 5.0)
        owners = {b["params"][1]["programId"] for _, b in self.fake.calls
                  if isinstance(b, dict) and b["method"] == "getTokenAccountsByOwner"}
        self.assertEqual(owners, {wallet.TOKEN_PROGRAM, wallet.TOKEN_2022_PROGRAM})

    def test_stake_accounts_are_valued_at_the_sol_price_and_listed_once(self) -> None:
        stake = {"pubkey": "StakeAcct1", "account": {"lamports": 2_000_000_000, "data": {"parsed": {"info": {
            "stake": {"delegation": {"voter": "VoteX", "stake": "1997717120"}}}}}}}
        self.fake.sol_stake = [stake]
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        (st,) = scan["stakes"]                      # found as staker, not duplicated as withdrawer
        sol_price = self.fake.jup["price"][wallet.WSOL_MINT]["usdPrice"]
        self.assertAlmostEqual(st["usd"], 2.0 * sol_price)
        self.assertIn(("SOL (staked)", "stake account"), {(c["holding"], c["kind"]) for c in scan["contracts"]})
        self.assertAlmostEqual(scan["total_usd"], sum(r["usd"] for r in [scan["native"], scan["holdings"][0], st]))

    def test_dust_balance_is_noted_not_listed(self) -> None:
        usdc = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        self.fake.sol_tokens = {"value": self.fake.sol_tokens["value"] + [{
            "pubkey": "DustAcct", "account": {"data": {"parsed": {"info": {
                "mint": usdc, "tokenAmount": {"uiAmountString": "0.000047", "decimals": 6}}}}}}]}
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        self.assertEqual([h["symbol"] for h in scan["holdings"]], ["JupSOL"])
        self.assertTrue(any("under $0.0001" in n for n in scan["notes"]))

    def test_airdrop_token_is_flagged_and_left_out_of_the_total(self) -> None:
        self.fake.sol_tokens = {"value": self.fake.sol_tokens["value"] + [{
            "pubkey": "SpamAcct", "account": {"data": {"parsed": {"info": {
                "mint": SPAM_MINT, "tokenAmount": {"uiAmountString": "1000000", "decimals": 6}}}}}}]}
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        spam = next(h for h in scan["holdings"] if h["mint"] == SPAM_MINT)
        self.assertTrue(spam["airdrop"])
        self.assertFalse(spam["included"])
        self.assertIn("spam-style name or symbol", spam["airdrop_reasons"])
        self.assertEqual(scan["counts"]["airdrop_flagged"], 1)
        self.assertEqual(scan["counts"]["holdings"], 1)
        self.assertAlmostEqual(scan["airdrop_excluded_usd"], 500000.0)
        honest = scan["native"]["usd"] + next(h["usd"] for h in scan["holdings"] if h["included"])
        self.assertAlmostEqual(scan["total_usd"], honest)         # the $500k of "value" is not counted

    def test_rpc_failure_gives_a_partial_result_not_an_exception(self) -> None:
        self.fake.errors["getTokenAccountsByOwner"] = WalletHttpError(429, "HTTP 429 from api.mainnet-beta.solana.com")
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        self.assertEqual(scan["status"], "partial")
        self.assertIsNotNone(scan["native"])
        self.assertEqual(scan["holdings"], [])
        self.assertTrue(any("getTokenAccountsByOwner" in e["source"] and "429" in e["message"]
                            for e in scan["errors"]))

    def test_price_api_failure_keeps_amounts_and_leaves_usd_unknown(self) -> None:
        self.fake.errors["jup.ag/price"] = WalletHttpError(429, "HTTP 429 from lite-api.jup.ag")
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        self.assertEqual(scan["status"], "partial")
        self.assertIsNone(scan["native"]["usd"])
        # SOL stays unpriced and is not counted as a guess; JupSOL still has the token-data price.
        self.assertAlmostEqual(scan["total_usd"], scan["holdings"][0]["usd"])
        self.assertIsNotNone(scan["holdings"][0]["usd"])

    def test_everything_down_is_an_error_status_with_every_source_named(self) -> None:
        self.fake.errors["api.mainnet-beta.solana.com"] = WalletHttpError(0, "timed out")
        self.fake.errors["jup.ag"] = WalletHttpError(0, "timed out")
        scan = wallet.scan_solana(SOL_ADDR, self.fake).to_dict()
        self.assertEqual(scan["status"], "error")
        self.assertGreaterEqual(len(scan["errors"]), 4)


class BaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = Fake()

    def scan(self, **kw):
        return wallet.scan_base(BASE_ADDR, self.fake, **kw).to_dict()

    def test_blocked_indexer_is_reported_and_the_known_set_is_still_checked(self) -> None:
        scan = self.scan()
        self.assertEqual(scan["status"], "partial")
        err = next(e for e in scan["errors"] if e["source"] == "blockscout token list")
        self.assertIn("Cloudflare", err["message"])
        self.assertTrue(any("cannot be discovered without an indexer" in n for n in scan["notes"]))
        (usdc,) = scan["holdings"]
        self.assertEqual((usdc["symbol"], usdc["amount"]), ("USDC", 1.0))
        self.assertAlmostEqual(usdc["price_usd"], self.fake.base["llama"]["coins"][f"base:{USDC_BASE}"]["price"])
        self.assertTrue(usdc["verified_onchain"])

    def test_native_eth_is_valued_with_the_defillama_price(self) -> None:
        scan = self.scan()
        self.assertAlmostEqual(scan["native"]["amount"], 0x1fb9deb2d6ab1 / 1e18)
        eth_price = self.fake.base["llama"]["coins"]["coingecko:ethereum"]["price"]
        self.assertAlmostEqual(scan["native"]["usd"], scan["native"]["amount"] * eth_price)
        self.assertAlmostEqual(scan["total_usd"], scan["native"]["usd"] + scan["holdings"][0]["usd"])

    def test_zero_balances_are_not_listed_and_no_account_is_written_to(self) -> None:
        scan = self.scan()
        self.assertEqual([h["symbol"] for h in scan["holdings"]], ["USDC"])
        self.assertEqual(self.fake.methods(), {"eth_getBalance", "eth_call"})   # reads only

    def test_indexer_tokens_are_verified_on_chain_and_the_chain_wins(self) -> None:
        self.fake.blockscout = {"items": [{"token": {"address_hash": USDC_BASE, "symbol": "USDC", "decimals": "6",
                                                     "exchange_rate": "1.0", "name": "USD Coin"},
                                           "value": "2500000"}]}
        scan = self.scan()
        (usdc,) = scan["holdings"]
        self.assertEqual(usdc["amount"], 1.0)                               # balanceOf says 1.0, indexer 2.5
        self.assertIn("on-chain used", usdc["indexer_mismatch"])
        self.assertFalse(any(e["source"] == "blockscout token list" for e in scan["errors"]))

    def test_unknown_indexer_token_with_spam_name_is_flagged_and_excluded(self) -> None:
        self.fake.blockscout = {"items": [{"token": {"address_hash": SPAM_TOKEN, "symbol": "FREE-USDC.com",
                                                     "decimals": "18", "exchange_rate": "1.0",
                                                     "name": "Claim your reward at free-usdc.com"},
                                           "value": str(10**24)}]}
        self.fake.balances[SPAM_TOKEN.lower()] = 10**24
        self.fake.llama_extra = {f"base:{SPAM_TOKEN}": {"price": 1.0, "confidence": 0.99}}
        scan = self.scan()
        spam = next(h for h in scan["holdings"] if h["address"].lower() == SPAM_TOKEN.lower())
        self.assertTrue(spam["airdrop"] and not spam["included"])
        self.assertEqual(scan["counts"]["airdrop_flagged"], 1)
        self.assertGreaterEqual(scan["airdrop_excluded_usd"], 1_000_000)
        usdc = next(h for h in scan["holdings"] if h["symbol"] == "USDC")
        self.assertAlmostEqual(scan["total_usd"], scan["native"]["usd"] + usdc["usd"])

    def test_dust_is_counted_in_a_note_not_listed(self) -> None:
        self.fake.balances[wallet.KNOWN_BASE_TOKENS[3][0].lower()] = 9      # 9e-18 DAI, as the owner holds
        self.fake.llama_extra = {f"base:{wallet.KNOWN_BASE_TOKENS[3][0]}": {"price": 1.0, "confidence": 0.99}}
        scan = self.scan()
        self.assertEqual([h["symbol"] for h in scan["holdings"]], ["USDC"])
        self.assertTrue(any("under $0.0001" in n for n in scan["notes"]))

    def test_requested_token_without_a_price_is_flagged_not_valued(self) -> None:
        other = "0x1111111111111111111111111111111111111111"
        self.fake.balances[other] = 5 * 10**18
        scan = self.scan(extra_tokens=[other])
        row = next(h for h in scan["holdings"] if h["address"] == other)
        self.assertEqual(row["symbol"], "FREE-USDC.com")      # decoded from the ABI-encoded view reply
        self.assertIn("no market price", row["airdrop_reasons"])
        self.assertIsNone(row["usd"])

    def test_dexscreener_prices_what_defillama_does_not(self) -> None:
        other = "0x2222222222222222222222222222222222222222"
        self.fake.balances[other] = 2 * 10**18
        self.fake.dex = [{"baseToken": {"address": other, "symbol": "OK"}, "priceUsd": "3.5",
                          "liquidity": {"usd": 250000}}]
        scan = self.scan(extra_tokens=[other])
        row = next(h for h in scan["holdings"] if h["address"] == other)
        self.assertEqual(row["price_usd"], 3.5)

    def test_position_nfts_are_listed_with_manager_contract_and_daemon_value(self) -> None:
        aero = wallet.POSITION_MANAGERS["Aero Slipstream"]
        self.fake.nft_count[aero.lower()] = 1
        self.fake.nft_ids[aero.lower()] = [1609324]
        daemon = wallet.daemon_context(
            {"mode": "live", "positions": [{"token_id": 1609324, "pair": "WETH/cbBTC", "value_usd": 43.1},
                                           {"token_id": 777, "pair": "A/B", "value_usd": 10.0}]}, [])
        scan = self.scan(daemon=daemon)
        by_id = {p["token_id"]: p for p in scan["positions"]}
        self.assertEqual(by_id[1609324]["held_by"], "wallet")
        self.assertEqual(by_id[1609324]["value_usd"], 43.1)
        self.assertEqual(by_id[777]["held_by"], "gauge (staked) or not in the wallet")
        self.assertEqual(by_id[777]["manager"], aero)
        self.assertTrue(by_id[777]["link"].startswith("https://basescan.org/nft/"))
        positions_usd = 43.1 + 10.0
        base = scan["native"]["usd"] + scan["holdings"][0]["usd"]
        self.assertAlmostEqual(scan["total_usd"], base + positions_usd)
        self.assertTrue(any(c["kind"] == "position NFT" and c["address"] == aero for c in scan["contracts"]))

    def test_an_owned_nft_with_no_value_source_is_listed_but_not_counted(self) -> None:
        uni = wallet.POSITION_MANAGERS["Uniswap v3"]
        self.fake.nft_count[uni.lower()] = 1
        self.fake.nft_ids[uni.lower()] = [42]
        scan = self.scan()
        (pos,) = scan["positions"]
        self.assertEqual((pos["protocol"], pos["value_usd"]), ("Uniswap v3", None))
        self.assertEqual(pos["value_source"], "not valued (no source)")
        base = scan["native"]["usd"] + scan["holdings"][0]["usd"]
        self.assertAlmostEqual(scan["total_usd"], base)

    def test_daemon_dry_run_positions_are_noted_as_not_live(self) -> None:
        daemon = wallet.daemon_context({"mode": "dry-run", "positions": [{"token_id": 1, "value_usd": 5.0}]}, [])
        scan = self.scan(daemon=daemon)
        self.assertTrue(any("not live" in n for n in scan["notes"]))

    def test_first_rpc_down_falls_back_to_the_second(self) -> None:
        first = wallet.BASE_RPCS[0]

        def flaky(url, body=None):
            if url == first:
                raise WalletHttpError(429, "HTTP 429 from base-rpc.publicnode.com")
            return self.fake(url, body)
        scan = wallet.scan_base(BASE_ADDR, flaky).to_dict()
        self.assertIsNotNone(scan["native"])
        self.assertFalse(any("eth_getBalance" in e["source"] for e in scan["errors"]))

    def test_all_rpcs_down_names_the_failure(self) -> None:
        self.fake.errors["eth_getBalance"] = WalletHttpError(0, "timed out")
        scan = self.scan()
        self.assertIsNone(scan["native"])
        self.assertTrue(any(e["source"] == "base eth_getBalance" for e in scan["errors"]))


class BaseDiscoveryTests(unittest.TestCase):
    OTHER = "0x2222222222222222222222222222222222222222"

    def setUp(self):
        self.fake = Fake()

    def row(self, address=OTHER, amount="2000000000000000000", decimals=18, symbol="OTHER"):
        return {"amount": {"amount": amount, "decimals": decimals},
                "token": {"contractAddress": address, "network": "base", "symbol": symbol, "name": symbol}}

    def scan(self):
        return wallet.scan_base(BASE_ADDR, self.fake).to_dict()

    def test_cdp_follows_all_pages_and_never_calls_unknown_contracts(self):
        self.fake.base_token_balances = mock.Mock(side_effect=[
            {"balances": [self.row(USDC_BASE, "2500000", 6, "USDC")], "nextPageToken": "page2"},
            {"balances": [self.row()]}])
        self.fake.llama_extra[f"base:{self.OTHER}"] = {"price": 2.0, "confidence": 0.99}
        scan = self.scan()
        by = {h["address"].lower(): h for h in scan["holdings"]}
        self.assertEqual(by[USDC_BASE.lower()]["amount"], 1.0)  # latest RPC wins for trusted tokens
        self.assertEqual(by[self.OTHER]["amount"], 2.0)
        self.assertEqual(by[self.OTHER]["discovered_via"], "cdp")
        self.assertFalse(by[self.OTHER]["verified_onchain"])
        self.assertEqual(scan["status"], "ok")
        self.fake.base_token_balances.assert_has_calls([mock.call(BASE_ADDR, None), mock.call(BASE_ADDR, "page2")])
        self.assertFalse(any("blockscout" in url for url, _ in self.fake.calls))
        for _, body in self.fake.calls:
            for req in body if isinstance(body, list) else []:
                self.assertNotEqual(req["params"][0]["to"].lower(), self.OTHER)

    def test_cdp_native_is_not_an_erc20_and_recovers_an_rpc_outage(self):
        self.fake.base_token_balances = mock.Mock(return_value={"balances": [
            self.row(wallet.NATIVE_EVM, "1000000000000000", 18, "ETH")]})
        self.fake.errors["eth_getBalance"] = WalletHttpError(0, "offline")
        scan = self.scan()
        self.assertEqual(scan["native"]["amount"], 0.001)
        self.assertFalse(scan["native"]["verified_onchain"])
        self.assertFalse(any(h["address"].lower() == wallet.NATIVE_EVM for h in scan["holdings"]))
        self.assertEqual(scan["status"], "partial")
        self.assertFalse(scan["total_complete"])

    def test_page_failure_retains_previous_balances_and_reports_incomplete(self):
        self.fake.base_token_balances = mock.Mock(side_effect=[
            {"balances": [self.row()], "nextPageToken": "page2"}, WalletHttpError(0, "offline")])
        scan = self.scan()
        self.assertIn(self.OTHER, [h["address"] for h in scan["holdings"]])
        self.assertTrue(any(e["source"] == "cdp token list" for e in scan["errors"]))
        self.assertFalse(scan["total_complete"])

    def test_malformed_cdp_data_cannot_become_a_balance(self):
        bad_rows = [self.row(amount="NaN"), self.row(amount="-1"), self.row(decimals=256),
                    self.row(decimals=True), self.row(decimals=1.5), {"amount": [], "token": {}},
                    self.row(address="0x123"), self.row() | {"token": {"network": "ethereum"}}]
        for row in bad_rows:
            with self.subTest(row=row):
                self.fake.base_token_balances = mock.Mock(return_value={"balances": [row]})
                scan = self.scan()
                self.assertTrue(any(e["source"] == "cdp token list" for e in scan["errors"]))
                self.assertNotIn(self.OTHER, [h["address"] for h in scan["holdings"]])

    def test_cdp_repeated_cursor_and_page_cap_stop(self):
        for limit in (1, 25):
            with self.subTest(limit=limit), mock.patch.object(wallet, "MAX_TOKEN_PAGES", limit):
                self.fake.base_token_balances = mock.Mock(return_value={"balances": [], "nextPageToken": "same"})
                scan = self.scan()
                self.assertLessEqual(self.fake.base_token_balances.call_count, 2)
                self.assertTrue(any(e["source"] == "cdp token list" for e in scan["errors"]))

    def test_unknown_spam_is_excluded_without_metadata_calls(self):
        self.fake.base_token_balances = mock.Mock(return_value={"balances": [
            self.row(symbol="FREE-USDC.com")]})
        scan = self.scan()
        row = next(h for h in scan["holdings"] if h["address"] == self.OTHER)
        self.assertTrue(row["airdrop"])
        self.assertFalse(row["included"])
        self.assertFalse(row["verified_onchain"])

    def test_failed_trusted_rpc_retains_indexed_balance_with_error(self):
        self.fake.base_token_balances = mock.Mock(return_value={"balances": [
            self.row(USDC_BASE, "1000000", 6, "USDC")]})
        original = self.fake._base
        self.fake._base = lambda body: [{"id": r["id"], "error": {"code": -1}} for r in body] \
            if isinstance(body, list) else original(body)
        scan = self.scan()
        row = next(h for h in scan["holdings"] if h["symbol"] == "USDC")
        self.assertEqual(row["amount"], 1)
        self.assertFalse(row["verified_onchain"])
        self.assertTrue(any(e["source"] == "base balanceOf" for e in scan["errors"]))

    def test_blockscout_follows_next_page_params(self):
        original = self.fake.__call__
        def fetch(url, body=None):
            if "blockscout" in url:
                if "items_count=50" in url:
                    return {"items": [{"token": {"address_hash": self.OTHER, "symbol": "OTHER",
                                                  "decimals": "18"}, "value": str(2 * 10**18)}]}
                return {"items": [], "next_page_params": {"items_count": 50, "value": "123"}}
            return original(url, body)
        scan = wallet.scan_base(BASE_ADDR, fetch).to_dict()
        self.assertIn(self.OTHER, [h["address"] for h in scan["holdings"]])
        self.assertEqual(scan["status"], "ok")

    def test_invalid_native_reply_is_unknown_not_zero(self):
        for raw in ("not hex", "0x", "0x-1", None, True):
            with self.subTest(raw=raw):
                self.fake.base["eth_getBalance"]["result"] = raw
                scan = self.scan()
                self.assertIsNone(scan["native"])
                self.assertTrue(any(e["source"] == "base eth_getBalance" for e in scan["errors"]))

    def test_price_requests_are_bounded_for_large_wallets(self):
        rows = [self.row(address=f"0x{i:040x}") for i in range(1, 105)]
        self.fake.base_token_balances = mock.Mock(return_value={"balances": rows})
        self.scan()
        urls = [u for u, _ in self.fake.calls if u.startswith(wallet.LLAMA_PRICES)]
        self.assertGreater(len(urls), 1)
        self.assertTrue(all(len(u.removeprefix(wallet.LLAMA_PRICES).split(",")) <= 40 for u in urls))

    def test_cli_uses_fixed_read_argv_and_does_not_expose_stderr(self):
        fetch = wallet.HttpFetcher()
        with mock.patch.object(wallet.shutil, "which", return_value="/opt/homebrew/bin/cdp"), \
                mock.patch.object(wallet.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout='{"balances": []}')
            self.assertEqual(fetch.base_token_balances(BASE_ADDR, "a;echo secret"), {"balances": []})
            args, kwargs = run.call_args
            self.assertEqual(args[0][1:6], ["data", "evm", "token-balances", "base", BASE_ADDR])
            self.assertEqual(args[0][-1], "pageToken==a;echo secret")
            self.assertNotIn("shell", kwargs)
            self.assertEqual(kwargs["stdin"], wallet.subprocess.DEVNULL)
            run.return_value = mock.Mock(returncode=1, stderr="PRIVATE_CREDENTIAL")
            with self.assertRaises(WalletHttpError) as ctx:
                fetch.base_token_balances(BASE_ADDR)
            self.assertNotIn("PRIVATE_CREDENTIAL", str(ctx.exception))

    def test_cli_missing_timeout_and_bad_json_are_sanitized(self):
        fetch = wallet.HttpFetcher()
        with mock.patch.object(wallet.shutil, "which", return_value=None), \
                mock.patch.object(wallet.os.path, "isfile", return_value=False):
            with self.assertRaisesRegex(WalletHttpError, "unavailable"):
                fetch.base_token_balances(BASE_ADDR)
        with mock.patch.object(wallet.shutil, "which", return_value="cdp"), \
                mock.patch.object(wallet.subprocess, "run") as run:
            run.side_effect = wallet.subprocess.TimeoutExpired("cdp", 1, stderr="SECRET")
            with self.assertRaisesRegex(WalletHttpError, "could not finish"):
                fetch.base_token_balances(BASE_ADDR)
            run.side_effect = None
            run.return_value = mock.Mock(returncode=0, stdout="oops")
            with self.assertRaisesRegex(WalletHttpError, "not JSON"):
                fetch.base_token_balances(BASE_ADDR)


class AirdropRuleTests(unittest.TestCase):
    def test_spam_wording_flags_even_a_priced_token(self) -> None:
        r = wallet.airdrop_reasons("USDC.xyz", "Claim", price=1.0, liquidity=1e9, verified=True, known=True)
        self.assertEqual(r, ["spam-style name or symbol"])

    def test_known_or_verified_tokens_are_not_flagged_for_price_alone(self) -> None:
        self.assertEqual(wallet.airdrop_reasons("USDC", "USD Coin", price=None, liquidity=None,
                                                verified=True, known=False), [])
        self.assertEqual(wallet.airdrop_reasons("WETH", "Wrapped Ether", price=None, liquidity=None,
                                                verified=False, known=True), [])

    def test_unverified_unknown_token_with_no_price_or_thin_liquidity_is_flagged(self) -> None:
        self.assertTrue(wallet.airdrop_reasons("ZZZ", "Zed", price=None, liquidity=None, verified=False, known=False))
        self.assertTrue(wallet.airdrop_reasons("ZZZ", "Zed", price=1, liquidity=100, verified=False, known=False))
        self.assertEqual(wallet.airdrop_reasons("ZZZ", "Zed", price=1, liquidity=1e6, verified=False, known=False), [])


class ScanWalletTests(unittest.TestCase):
    def test_both_chains_sum_and_carry_the_label(self) -> None:
        result = wallet.scan_wallet(SOL_ADDR, BASE_ADDR, Fake(), now=1_790_000_000)
        self.assertEqual(result["label"], "wallet (live)")
        self.assertEqual(set(result["chains"]), {"solana", "base"})
        self.assertAlmostEqual(result["total_usd"], sum(c["total_usd"] for c in result["chains"].values()))
        self.assertTrue(result["partial"])               # Blockscout is blocked in the fixture
        self.assertEqual(result["counts"]["holdings"], 2)
        self.assertEqual(result["counts"]["airdrop_flagged"], 0)
        self.assertEqual(result["scanned_at"], "2026-09-21T14:13:20+00:00")
        self.assertIn("public reads only", result["read_only"])

    def test_one_chain_only(self) -> None:
        result = wallet.scan_wallet(SOL_ADDR, BASE_ADDR, Fake(), chain="solana")
        self.assertEqual(list(result["chains"]), ["solana"])

    def test_missing_or_malformed_address_is_skipped_with_a_reason(self) -> None:
        result = wallet.scan_wallet("", "0x123", Fake())
        self.assertEqual(result["chains"], {})
        self.assertEqual(len(result["skipped"]), 2)
        self.assertTrue(result["partial"])

    def test_address_validation(self) -> None:
        self.assertTrue(wallet.valid_solana_address(SOL_ADDR))
        self.assertTrue(wallet.valid_evm_address(BASE_ADDR))
        for bad in ("", "0x123", "0xZZ" + "0" * 38, SOL_ADDR + "0", "O" * 40):
            self.assertFalse(wallet.valid_evm_address(bad), bad)
        for bad in ("", "short", "0" * 40, BASE_ADDR):
            self.assertFalse(wallet.valid_solana_address(bad), bad)

    def test_the_scan_makes_no_write_call_and_carries_no_key(self) -> None:
        fake = Fake()
        wallet.scan_wallet(SOL_ADDR, BASE_ADDR, fake)
        allowed = {"getBalance", "getTokenAccountsByOwner", "getProgramAccounts", "eth_getBalance", "eth_call"}
        self.assertLessEqual(fake.methods(), allowed)
        for url, body in fake.calls:
            blob = json.dumps(body) + url
            self.assertNotIn("sendTransaction", blob)
            self.assertNotIn("apikey", blob.lower())
            self.assertNotIn("api_key", blob.lower())


class KeySourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = mock.patch.dict(os.environ, {"SOLTUI_KEY_DIR": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)

    def test_missing_files(self) -> None:
        rows = wallet.key_sources()["keys"]
        self.assertEqual([(r["chain"], r["exists"], r["mode_600"]) for r in rows],
                         [("base", False, False), ("solana", False, False)])

    def test_mode_is_reported_and_the_file_is_never_opened(self) -> None:
        good, loose = Path(self.tmp.name, "wallet.private"), Path(self.tmp.name, "solana.private")
        good.write_text("SECRET-DO-NOT-READ")
        loose.write_text("SECRET-DO-NOT-READ")
        good.chmod(0o600)
        loose.chmod(0o644)
        opened = []
        real_open = open

        def spy(file, *a, **k):
            opened.append(str(file))
            return real_open(file, *a, **k)
        with mock.patch("builtins.open", spy), mock.patch.object(Path, "read_text", side_effect=AssertionError("read")), \
                mock.patch.object(Path, "read_bytes", side_effect=AssertionError("read")):
            result = wallet.key_sources()
        self.assertEqual(opened, [])
        by = {r["chain"]: r for r in result["keys"]}
        self.assertEqual((by["base"]["mode"], by["base"]["mode_600"]), ("0600", True))
        self.assertEqual((by["solana"]["mode"], by["solana"]["mode_600"]), ("0644", False))
        self.assertIn("should be 0600", by["solana"]["problem"])
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertIn("never opened", result["note"])
        self.assertIn(stat.S_IMODE(os.stat(good).st_mode), (0o600,))


class HistoryTests(unittest.TestCase):
    def test_record_and_load_round_trip_skipping_junk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            result = wallet.scan_wallet(SOL_ADDR, BASE_ADDR, Fake(), now=1_790_000_000)
            wallet.record_scan(result, path)
            with open(path, "a") as fh:
                fh.write("not json\n{\"ts\": \"x\"}\n")
            rows = wallet.load_history(path)
            self.assertEqual(len(rows), 1)
            self.assertAlmostEqual(rows[0]["total_usd"], result["total_usd"])
            self.assertEqual(set(rows[0]["chains"]), {"solana", "base"})
            self.assertEqual(wallet.load_history(Path(tmp) / "none.jsonl"), [])


class FetcherTests(unittest.TestCase):
    """The real transport, with urllib replaced: timeouts, retries and the time budget."""

    def fetcher(self, **kw):
        clock = [0.0]
        sleeps: list[float] = []
        f = wallet.HttpFetcher(clock=lambda: clock[0], sleep=lambda s: (sleeps.append(s), clock.__setitem__(0, clock[0] + s)),
                               **kw)
        return f, clock, sleeps

    class Resp:
        def __init__(self, text): self.text = text
        def read(self): return self.text.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def http_error(self, code, retry_after=None):
        import email.message
        import urllib.error
        hdrs = email.message.Message()
        if retry_after:
            hdrs["Retry-After"] = retry_after
        return urllib.error.HTTPError("https://x.test/a", code, "err", hdrs, None)

    def test_retries_a_429_then_succeeds_and_honours_retry_after(self) -> None:
        f, _, sleeps = self.fetcher()
        replies = [self.http_error(429, "2"), self.Resp('{"ok": true}')]

        def fake_open(req, timeout):
            r = replies.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        with mock.patch("urllib.request.urlopen", fake_open):
            self.assertEqual(f("https://x.test/a"), {"ok": True})
        self.assertIn(2.0, sleeps)

    def test_gives_up_after_the_retry_limit_and_reports_the_status(self) -> None:
        f, _, _ = self.fetcher(retries=1)
        with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: (_ for _ in ()).throw(self.http_error(503))):
            with self.assertRaises(WalletHttpError) as ctx:
                f("https://x.test/a")
        self.assertEqual(ctx.exception.status, 503)

    def test_a_403_is_not_retried(self) -> None:
        f, _, _ = self.fetcher()
        calls = []
        with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: (calls.append(1), (_ for _ in ()).throw(self.http_error(403)))[1]):
            with self.assertRaises(WalletHttpError):
                f("https://x.test/a")
        self.assertEqual(len(calls), 1)

    def test_the_budget_stops_the_scan(self) -> None:
        f, clock, _ = self.fetcher(budget_s=5.0)
        clock[0] = 6.0
        with self.assertRaises(WalletHttpError) as ctx:
            f("https://x.test/a")
        self.assertIn("budget", str(ctx.exception))

    def test_non_json_is_an_error_not_a_crash(self) -> None:
        f, _, _ = self.fetcher()
        with mock.patch("urllib.request.urlopen", lambda req, timeout: self.Resp("<html>")):
            with self.assertRaises(WalletHttpError):
                f("https://x.test/a")

    def test_a_post_sends_json_and_the_read_only_user_agent(self) -> None:
        f, _, _ = self.fetcher()
        seen = {}

        def fake_open(req, timeout):
            seen["body"], seen["ua"], seen["timeout"] = req.data, req.get_header("User-agent"), timeout
            return self.Resp("{}")
        with mock.patch("urllib.request.urlopen", fake_open):
            f("https://x.test/rpc", {"jsonrpc": "2.0"})
        self.assertEqual(json.loads(seen["body"]), {"jsonrpc": "2.0"})
        self.assertIn("read-only", seen["ua"])
        self.assertEqual(seen["timeout"], 12.0)


if __name__ == "__main__":
    unittest.main()
