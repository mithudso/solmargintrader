"""Ethereum mainnet (L1) holdings of one public address: native ETH plus a well-known token list.

`base_address` in Settings is the same EVM key viewed on Base; `eth_address` is the mainnet view.
Reads only: `eth_getBalance` and `balanceOf` over public JSON-RPC, USD prices from Coinbase. There is
no indexer here, so a token that is not in `TOKENS` is not discovered, and the scan says so.
"""

from __future__ import annotations

from typing import Any, Callable

from .spot_prices import spot_prices
from .wallet import (
    DUST_USD,
    ERC20_BALANCE_OF,
    LABEL,
    ChainScan,
    WalletHttpError,
    _batch,
    _eth_call,
    _hex_int,
    _pad,
    _rpc,
)

ETH_RPCS = ("https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com", "https://cloudflare-eth.com")
EXPLORER = "https://etherscan.io"

# (contract, symbol, decimals, Coinbase symbol to price it with or None). Symbols and decimals were
# checked against the contracts on 2026-11-07. WETH is an exact 1:1 wrapper, so it uses the ETH price.
TOKENS: tuple[tuple[str, str, int, str | None], ...] = (
    ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USDC", 6, "USDC"),
    ("0xdAC17F958D2ee523a2206206994597C13D831ec7", "USDT", 6, "USDT"),
    ("0x6B175474E89094C44Da98b954EedeAC495271d0F", "DAI", 18, "DAI"),
    ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "WBTC", 8, "WBTC"),
    ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "WETH", 18, "ETH"),
    ("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84", "stETH", 18, None),
    ("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0", "wstETH", 18, None),
    ("0x514910771AF9Ca656af840dff83E8264EcF986CA", "LINK", 18, "LINK"),
    ("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "UNI", 18, "UNI"),
    ("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9", "AAVE", 18, "AAVE"),
    ("0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2", "MKR", 18, "MKR"),
    ("0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", "SHIB", 18, "SHIB"),
)


def scan_ethereum(address: str, fetch: Callable[..., Any], rpcs: tuple[str, ...] = ETH_RPCS) -> ChainScan:
    scan = ChainScan("ethereum", address)

    def call_rpc(label: str, fn: Callable[[str], Any]) -> Any:
        last: Exception | None = None
        for url in rpcs:
            try:
                return fn(url)
            except WalletHttpError as exc:
                last = exc
        scan.error(label, last or RuntimeError("no RPC"))
        return None

    raw = call_rpc("ethereum eth_getBalance", lambda u: _rpc(fetch, u, "eth_getBalance", [address, "latest"]))
    eth = _hex_int(raw) if raw is not None else None
    if eth is not None:
        scan.native = {"symbol": "ETH", "name": "Ether", "amount": eth / 1e18, "price_usd": None, "usd": None,
                       "source": LABEL, "kind": "native"}
    calls = [_eth_call(t[0].lower(), ERC20_BALANCE_OF + _pad(address)) for t in TOKENS]
    out = call_rpc("ethereum balanceOf batch", lambda u: _batch(fetch, u, calls)) or [None] * len(TOKENS)
    held = [(t, _hex_int(r)) for t, r in zip(TOKENS, out) if _hex_int(r)]
    answered = sum(1 for r in out if r is not None)
    if answered < len(TOKENS) and not any(e["source"] == "ethereum balanceOf batch" for e in scan.errors):
        scan.notes.append(f"{len(TOKENS) - answered} token(s) did not answer balanceOf and are not listed")
    scan.notes.append(f"only {len(TOKENS)} well-known tokens are checked (no token indexer): a token "
                      "outside that list is not discovered")
    wanted = (["ETH"] if scan.native else []) + [t[3] for t, _ in held if t[3]]
    prices, errs = spot_prices(fetch, wanted)
    for message in errs:
        scan.errors.append({"source": "price", "message": message})
    if scan.native is not None:
        scan.native["price_usd"] = prices.get("ETH")
        scan.native["usd"] = None if prices.get("ETH") is None else scan.native["amount"] * prices["ETH"]
        scan.contracts.append({"holding": "ETH", "kind": "wallet", "address": address,
                               "program": "externally owned account", "link": f"{EXPLORER}/address/{address}"})
    dust = 0
    for (addr, sym, dec, price_sym), units in held:
        amount = units / (10 ** dec)
        px = prices.get(price_sym) if price_sym else None
        if px is not None and amount * px < DUST_USD:
            dust += 1
            continue
        scan.holdings.append({
            "symbol": sym, "name": sym, "address": addr, "amount": amount, "price_usd": px,
            "usd": None if px is None else amount * px, "verified_onchain": True, "indexer_mismatch": None,
            "discovered_via": "built-in list", "airdrop": False, "airdrop_reasons": [], "included": True,
            "source": LABEL, "kind": "erc20", "link": f"{EXPLORER}/token/{addr}"})
        scan.contracts.append({"holding": sym, "kind": "token contract", "address": addr, "program": "ERC-20",
                               "link": f"{EXPLORER}/token/{addr}", "airdrop": False})
    if dust:
        scan.notes.append(f"{dust} balance(s) worth under ${DUST_USD} are not listed")
    return scan
