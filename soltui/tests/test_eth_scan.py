"""Ethereum mainnet scan: native ETH, the built-in token list, Coinbase prices, partial results."""

from __future__ import annotations

import json
import unittest

from soltui import eth_scan
from soltui.wallet import ERC20_BALANCE_OF, WalletHttpError

ADDR = "0x" + "12" * 20
USDC, STETH = eth_scan.TOKENS[0][0].lower(), eth_scan.TOKENS[5][0].lower()


class FakeEth:
    def __init__(self, fail_rpc: bool = False, prices: dict[str, str] | None = None) -> None:
        self.fail_rpc = fail_rpc
        self.prices = {"ETH": "2000", "USDC": "1"} if prices is None else prices
        self.balances = {USDC: 2_500_000, STETH: 3 * 10**18}

    def __call__(self, url: str, body=None):
        if "coinbase" in url:
            sym = url.split("/prices/")[1].split("-")[0]
            if sym not in self.prices:
                raise WalletHttpError(404, "HTTP 404 from api.coinbase.com")
            return {"data": {"amount": self.prices[sym]}}
        if self.fail_rpc:
            raise WalletHttpError(0, "rpc down")
        if isinstance(body, list):
            out = []
            for req in body:
                to = req["params"][0]["to"].lower()
                assert req["params"][0]["data"].startswith(ERC20_BALANCE_OF)
                out.append({"jsonrpc": "2.0", "id": req["id"], "result": hex(self.balances.get(to, 0))})
            return out
        assert body["method"] == "eth_getBalance"
        return {"jsonrpc": "2.0", "id": 1, "result": hex(10**18 // 2)}


class EthScanTests(unittest.TestCase):
    def test_native_and_tokens_are_priced_and_unlisted_prices_stay_unknown(self) -> None:
        out = eth_scan.scan_ethereum(ADDR, FakeEth()).to_dict()
        self.assertEqual(out["status"], "ok")
        self.assertAlmostEqual(out["native"]["usd"], 1000.0)
        by = {h["symbol"]: h for h in out["holdings"]}
        self.assertAlmostEqual(by["USDC"]["usd"], 2.5)
        self.assertIsNone(by["stETH"]["usd"])                  # no Coinbase price: unknown, not zero
        self.assertEqual(out["unpriced"], ["stETH"])
        self.assertFalse(out["total_complete"])
        self.assertAlmostEqual(out["total_usd"], 1002.5)
        self.assertTrue(any("well-known tokens" in n for n in out["notes"]))

    def test_rpc_outage_is_an_error_envelope_in_the_result_not_an_exception(self) -> None:
        out = eth_scan.scan_ethereum(ADDR, FakeEth(fail_rpc=True)).to_dict()
        self.assertEqual(out["status"], "error")
        self.assertTrue(out["errors"])
        self.assertIsNone(out["native"])

    def test_no_eth_price_leaves_native_value_unknown(self) -> None:
        out = eth_scan.scan_ethereum(ADDR, FakeEth(prices={"USDC": "1"})).to_dict()
        self.assertIsNone(out["native"]["usd"])
        self.assertIn("ETH", out["unpriced"])

    def test_the_token_list_has_distinct_contracts(self) -> None:
        addrs = [t[0].lower() for t in eth_scan.TOKENS]
        self.assertEqual(len(addrs), len(set(addrs)))
        json.dumps(eth_scan.scan_ethereum(ADDR, FakeEth()).to_dict())


if __name__ == "__main__":
    unittest.main()
