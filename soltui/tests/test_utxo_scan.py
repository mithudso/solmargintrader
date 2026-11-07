"""xpub scanning against recorded-shape explorer replies: script types, the gap limit, partial results.

The network is a fake that answers from a table of derived addresses. Keys are BIP32/BIP84 test vectors.
"""

from __future__ import annotations

import json
import re
import unittest

from soltui import hdwallet as h
from soltui import utxo_scan as u
from soltui.tests.test_hdwallet import BIP84_ZPUB, V2_M
from soltui.wallet import ChainScan, WalletHttpError


def esplora(balance: int, txs: int) -> dict:
    return {"chain_stats": {"funded_txo_count": txs, "funded_txo_sum": balance, "spent_txo_count": 0,
                            "spent_txo_sum": 0, "tx_count": txs},
            "mempool_stats": {"funded_txo_count": 0, "funded_txo_sum": 0, "spent_txo_count": 0,
                              "spent_txo_sum": 0, "tx_count": 0}}


class Net:
    """Answers explorer and price URLs from `history` {address: (sats, tx_count)}."""

    def __init__(self, history: dict[str, tuple[int, int]] | None = None, prices: dict[str, str] | None = None,
                 fail: tuple[str, ...] = ()) -> None:
        self.history = history or {}
        self.prices = {"BTC": "50000", "LTC": "50", "DOGE": "0.1"} if prices is None else prices
        self.fail = fail
        self.urls: list[str] = []

    def __call__(self, url: str, body=None):
        self.urls.append(url)
        if any(f in url for f in self.fail):
            raise WalletHttpError(0, "fake outage")
        m = re.search(r"/address/([^/?]+)$", url)
        if m:
            return esplora(*self.history.get(m.group(1), (0, 0)))
        m = re.search(r"/addrs/([^/]+)/balance$", url)
        if m:
            rows = []
            for a in m.group(1).split(";"):
                bal, txs = self.history.get(a, (0, 0))
                rows.append({"address": a, "final_balance": bal, "final_n_tx": txs})
            return rows if len(rows) > 1 else rows[0]
        m = re.search(r"/prices/([A-Z]+)-USD/spot$", url)
        if m:
            if m.group(1) not in self.prices:
                raise WalletHttpError(404, "HTTP 404 from api.coinbase.com")
            return {"data": {"amount": self.prices[m.group(1)]}}
        raise AssertionError(url)


def addr(coin: str, xpub: str, script: str, branch: int, index: int) -> str:
    key = h.parse_extended_key(xpub, coin)
    return h.encode_address(coin, script, key.pubkey_at(branch, index))


class ScriptTypeTests(unittest.TestCase):
    def test_each_style_with_history_is_kept_and_the_empty_one_is_not(self) -> None:
        hist = {addr("btc", V2_M, "p2wpkh", 0, 0): (150_000_000, 2),
                addr("btc", V2_M, "p2wpkh", 0, 2): (50_000_000, 1),
                addr("btc", V2_M, "p2pkh", 0, 1): (10_000_000, 3),
                addr("btc", V2_M, "p2pkh", 1, 0): (0, 2)}      # spent change: used, empty
        scan = u.scan_xpub("btc", V2_M, Net(hist))
        out = scan.to_dict()
        self.assertEqual(out["status"], "ok")
        types = {t["type"]: t for t in out["script_types"]}
        self.assertEqual(set(types), {"p2wpkh", "p2pkh"})
        self.assertAlmostEqual(types["p2wpkh"]["balance"], 2.0)
        self.assertEqual(types["p2wpkh"]["receive_used"], 3)     # indexes 0..2 are within the used prefix
        self.assertEqual(types["p2pkh"]["change_used"], 1)
        self.assertEqual(out["script_types_tried"], ["p2pkh", "p2sh-p2wpkh", "p2wpkh"])
        self.assertAlmostEqual(out["native"]["amount"], 2.1)

    def test_a_zpub_tries_only_its_own_style(self) -> None:
        net = Net({addr("btc", BIP84_ZPUB, "p2wpkh", 0, 0): (1000, 1)})
        scan = u.scan_xpub("btc", BIP84_ZPUB, net)
        self.assertEqual(scan.extra["script_types_tried"], ["p2wpkh"])
        self.assertEqual(len(net.urls), 2 * u.GAP_LIMIT + 1)      # 20 past index 0 on receive, 20 on change, plus 1

    def test_dogecoin_is_p2pkh_only_and_batched(self) -> None:
        hist = {addr("doge", V2_M, "p2pkh", 0, 0): (2_500_000_000, 1)}
        net = Net(hist)
        scan = u.scan_xpub("doge", V2_M, net)
        out = scan.to_dict()
        self.assertEqual(out["script_types_tried"], ["p2pkh"])
        self.assertAlmostEqual(out["native"]["amount"], 25.0)
        self.assertEqual(out["chain"], "dogecoin")
        self.assertTrue(all("/addrs/" in x for x in net.urls))
        self.assertLessEqual(len(net.urls), 4)                     # 20 per request, not one call per address

    def test_litecoin_uses_its_own_explorer(self) -> None:
        net = Net({addr("ltc", V2_M, "p2wpkh", 0, 0): (100_000_000, 1)})
        scan = u.scan_xpub("ltc", V2_M, net)
        self.assertEqual(scan.extra["explorer"], "litecoinspace.org")
        self.assertTrue(all("litecoinspace.org" in x for x in net.urls))


class GapLimitTests(unittest.TestCase):
    def test_an_address_exactly_at_the_gap_is_found_and_one_past_it_is_not(self) -> None:
        for index, found in ((19, True), (20, False)):
            with self.subTest(index=index):
                net = Net({addr("btc", BIP84_ZPUB, "p2wpkh", 0, index): (1000, 1)})
                scan = u.scan_xpub("btc", BIP84_ZPUB, net)
                self.assertEqual(bool(scan.extra["script_types"]), found)

    def test_a_used_address_extends_the_window(self) -> None:
        hist = {addr("btc", BIP84_ZPUB, "p2wpkh", 0, i): (1000, 1) for i in (0, 15, 34)}
        scan = u.scan_xpub("btc", BIP84_ZPUB, Net(hist))
        (t,) = scan.extra["script_types"]
        self.assertEqual(t["receive_used"], 35)
        self.assertAlmostEqual(t["balance"], 3000 / 1e8)

    def test_an_empty_wallet_derives_exactly_the_gap_on_each_chain(self) -> None:
        scan = u.scan_xpub("btc", BIP84_ZPUB, Net())
        self.assertEqual(scan.extra["derived_addresses"], 2 * u.GAP_LIMIT)
        self.assertIn("no history", " ".join(scan.notes))


class PartialAndPriceTests(unittest.TestCase):
    def test_an_explorer_outage_gives_a_partial_lower_bound_not_an_exception(self) -> None:
        hist = {addr("btc", V2_M, "p2wpkh", 0, 0): (1000, 1)}
        scan = u.scan_xpub("btc", V2_M, Net(hist, fail=("blockstream",)))   # primary answers: no failure
        self.assertEqual(scan.to_dict()["status"], "ok")
        down = Net(hist, fail=("mempool.space", "blockstream.info"))
        out = u.scan_xpub("btc", V2_M, down).to_dict()
        self.assertEqual(out["status"], "partial" if out["native"] else "error")
        self.assertTrue(out["errors"])
        self.assertTrue(any("lower bound" in n for n in out["notes"]))

    def test_the_fallback_explorer_takes_over(self) -> None:
        hist = {addr("btc", BIP84_ZPUB, "p2wpkh", 0, 0): (1000, 1)}
        net = Net(hist, fail=("mempool.space",))
        scan = u.scan_xpub("btc", BIP84_ZPUB, net)
        self.assertEqual(scan.to_dict()["status"], "ok")
        self.assertEqual(scan.extra["explorer"], "blockstream.info")

    def test_a_malformed_explorer_reply_is_an_error_not_a_zero(self) -> None:
        def fetch(url, body=None):
            return {"unexpected": True}
        out = u.scan_xpub("ltc", V2_M, fetch).to_dict()
        self.assertTrue(out["errors"])

    def test_a_missing_price_is_unknown_never_zero(self) -> None:
        hist = {addr("doge", V2_M, "p2pkh", 0, 0): (2_500_000_000, 1)}
        net = Net(hist, prices={"BTC": "50000"})                 # no DOGE price
        scans, _ = u.scan_utxo_wallets({"doge": V2_M}, net)
        out = scans["dogecoin"].to_dict()
        self.assertIsNone(out["native"]["usd"])
        self.assertIsNone(out["native"]["price_usd"])
        self.assertEqual(out["unpriced"], ["DOGE"])
        self.assertFalse(out["total_complete"])

    def test_a_price_outage_is_named(self) -> None:
        hist = {addr("btc", BIP84_ZPUB, "p2wpkh", 0, 0): (100_000_000, 1)}
        net = Net(hist, fail=("coinbase",))
        scans, _ = u.scan_utxo_wallets({"btc": BIP84_ZPUB}, net)
        out = scans["bitcoin"].to_dict()
        self.assertEqual(out["status"], "partial")
        self.assertTrue(any(e["source"] == "price" for e in out["errors"]))
        self.assertEqual(out["unpriced"], ["BTC"])

    def test_priced_total(self) -> None:
        hist = {addr("btc", BIP84_ZPUB, "p2wpkh", 0, 0): (200_000_000, 1)}
        scans, _ = u.scan_utxo_wallets({"btc": BIP84_ZPUB}, Net(hist))
        out = scans["bitcoin"].to_dict()
        self.assertAlmostEqual(out["total_usd"], 100_000.0)
        self.assertTrue(out["total_complete"])

    def test_a_bad_key_in_settings_becomes_a_chain_error(self) -> None:
        scans, _ = u.scan_utxo_wallets({"btc": "xpub-not-a-key"}, Net())
        out = scans["bitcoin"].to_dict()
        self.assertEqual(out["status"], "error")
        self.assertNotIn("xpub-not-a-key", json.dumps(out))


class RateLimitTests(unittest.TestCase):
    def test_blockcypher_429_is_retried_after_a_pause_then_succeeds(self) -> None:
        calls, sleeps = [], []
        net = Net({addr("doge", V2_M, "p2pkh", 0, 0): (100_000_000, 1)})

        def fetch(url, body=None):
            calls.append(url)
            if len(calls) <= 2:
                raise WalletHttpError(429, "HTTP 429 from api.blockcypher.com")
            return net(url, body)

        backend = u.BlockCypherBackend(fetch, sleep=sleeps.append)
        scan = u.scan_xpub("doge", V2_M, fetch, backend=backend)
        self.assertEqual(scan.to_dict()["status"], "ok")
        self.assertEqual(sleeps[:2], [8.0, 20.0])
        self.assertAlmostEqual(scan.native["amount"], 1.0)

    def test_persistent_429_ends_as_partial_not_an_exception(self) -> None:
        def fetch(url, body=None):
            raise WalletHttpError(429, "HTTP 429 from api.blockcypher.com")

        backend = u.BlockCypherBackend(fetch, sleep=lambda s: None)
        out = u.scan_xpub("doge", V2_M, fetch, backend=backend).to_dict()
        self.assertTrue(out["errors"])
        self.assertTrue(any("lower bound" in n for n in out["notes"]))


class PrivacyTests(unittest.TestCase):
    def test_a_result_holds_no_derived_address_and_no_full_xpub(self) -> None:
        hist = {addr("btc", V2_M, t, b, i): (1000, 1)
                for t in ("p2pkh", "p2wpkh") for b in (0, 1) for i in (0, 1)}
        scans, _ = u.scan_utxo_wallets({"btc": V2_M}, Net(hist))
        text = json.dumps(scans["bitcoin"].to_dict())
        self.assertNotIn(V2_M, text)
        self.assertNotIn(V2_M[8:], text)
        for a in hist:
            self.assertNotIn(a, text)
        self.assertEqual(scans["bitcoin"].address, "xpub66…")
        self.assertIsInstance(scans["bitcoin"], ChainScan)

    def test_no_xpub_is_ever_sent_to_an_explorer(self) -> None:
        net = Net()
        u.scan_xpub("btc", V2_M, net)
        self.assertFalse([x for x in net.urls if "xpub" in x or V2_M[8:] in x])


if __name__ == "__main__":
    unittest.main()
