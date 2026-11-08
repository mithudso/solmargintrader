"""Read-only wallet discovery: what the owner's two public addresses hold, and where it lives.

Nothing here can move funds. There is no key, no signature, no transaction and no write to a chain:
only JSON-RPC reads (`getBalance`, `getTokenAccountsByOwner`, `getProgramAccounts`,
`eth_getBalance`, `eth_call` to `balanceOf`), the public Jupiter, DefiLlama and DexScreener price
APIs, the optional configured CDP CLI's indexed balances, and Blockscout's token list.
SolTUI never loads or stores an API credential; the CDP CLI manages its own API authentication.

## What it finds

* **Solana:** native SOL; SPL tokens under the Token program and the Token-2022 program; stake
  accounts (as staker or withdrawer); token names and USD prices from Jupiter.
* **Base:** native ETH; ERC-20 balances; the position NFTs held in the Aero, Uniswap v3 and
  PancakeSwap v3 position managers; the Aero positions the liquidity daemon reports.
* **Contracts:** every holding is listed with the token contract (or token account, stake account or
  position manager) it lives in, and an explorer link.

## Honest limits

* The configured CDP CLI discovers Base tokens across all balance pages. Without it, Blockscout is
  the fallback. Blockscout often answers 403. If both fail, the scan says so and checks known
  Base tokens by `eth_call`: a built-in
  list, the tokens the liquidity daemon watches, and any `tokens=[...]` the caller adds. A token
  sent to the address that is in none of those is **not discoverable without an indexer**; the scan
  says that too instead of implying it saw everything.
* A fallback RPC or price source that fails produces a **partial** result with the error named, never
  an exception and never a silently smaller total.
* Unrecognized indexed tokens are flagged and left out of totals until explicitly requested or
  trusted by the built-in/daemon lists. Their balances and metadata come from the indexer. This
  module never calls their contracts or visits their sites, and never signs or approves anything.

Every figure is labelled `wallet (live)`: it is a read of real money at the time of the scan.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import stat as stat_mod
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

LABEL = "wallet (live)"
USER_AGENT = "soltui-wallet-scan/1 (read-only)"

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
BASE_RPCS = ("https://base-rpc.publicnode.com", "https://mainnet.base.org")
JUPITER_PRICE = "https://lite-api.jup.ag/price/v3"
JUPITER_TOKENS = "https://lite-api.jup.ag/tokens/v2/search"
BLOCKSCOUT = "https://base.blockscout.com/api/v2"
LLAMA_PRICES = "https://coins.llama.fi/prices/current/"
DEXSCREENER = "https://api.dexscreener.com/tokens/v1/base/"

TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
STAKE_PROGRAM = "Stake11111111111111111111111111111111111111"
WSOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS = 1_000_000_000

# Base. The Aero addresses are the ones in liquidity/src/aero_lp/addresses.py (two independent sources
# agree there); the others are the position managers that file lists for the comparison venues.
POSITION_MANAGERS = {
    "Aero Slipstream": "0x4857DB576eE0e45F10525eC59527BfD10beeC60b",
    "Uniswap v3": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
    "PancakeSwap v3": "0x46A15B0b27311cedF172AB29E4f4766fbE7F4364",
}
WETH_BASE = "0x4200000000000000000000000000000000000006"
# Tokens checked by `eth_call` even when no indexer answers: (address, symbol, decimals).
KNOWN_BASE_TOKENS = (
    (WETH_BASE, "WETH", 18),
    ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "USDC", 6),
    ("0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", "USDbC", 6),
    ("0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", "DAI", 18),
    ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", "cbBTC", 8),
    ("0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", "cbETH", 18),
    ("0x940181a94A35A4569E4529A3CDfB74e38FD98631", "AERO", 18),
    ("0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452", "wstETH", 18),
    ("0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42", "EURC", 6),
    ("0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2", "USDT", 6),
    # Gauntlet USDC Prime: a Morpho vault share (ERC-4626) the owner deposited into on 2026-11-06. The
    # CDP Data API found it (docs/BASE-WALLET-QUERIES.md); Blockscout is often Cloudflare-blocked, and
    # without an indexer this ~$87 position was invisible. DefiLlama prices the share directly.
    ("0xeE8F4eC5672F09119b96Ab6fB59C27E1b7e44b61", "gtUSDCp", 18),
)
ERC20_BALANCE_OF = "0x70a08231"
ERC20_SYMBOL = "0x95d89b41"
ERC20_DECIMALS = "0x313ce567"
ERC20_NAME = "0x06fdde03"
ERC721_TOKEN_OF_OWNER = "0x2f745c59"
MAX_NFTS_PER_MANAGER = 20
TOP_HOLDINGS_VERIFIED = 10

SOLANA_EXPLORER = "https://solscan.io"
BASE_EXPLORER = "https://basescan.org"

# A token that must have been sent to the address uninvited usually advertises itself.
_SPAM_TEXT = re.compile(
    r"(https?://|www\.|\.(com|io|xyz|net|org|app|site|top|vip|club|cc|finance|claim|live|gg|ly)\b|"
    r"\bclaim\b|airdrop|\breward|\bvisit\b|\bbonus\b|voucher|\bgift\b|\bfree\b|[$€£]\s?\d|\d+\s?(usd|usdc|sol|eth)\b)",
    re.IGNORECASE)
MIN_LIQUIDITY_USD = 5_000.0
DUST_USD = 0.0001
NATIVE_EVM = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
MAX_TOKEN_PAGES = 25

_B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")


def valid_solana_address(text: str) -> bool:
    return bool(text) and bool(_B58.match(text))


def valid_evm_address(text: str) -> bool:
    return bool(text) and bool(_EVM.match(text))


# -- transport ----------------------------------------------------------------------------------------


class WalletHttpError(RuntimeError):
    """One public endpoint refused or failed. `status` is the HTTP status, 0 for a network error."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


Fetch = Callable[..., Any]


class HttpFetcher:
    """GET/POST JSON with a timeout, a per-host pause, bounded retries on 429/5xx and a total budget.

    `fetch(url, body)` is GET when `body` is None, else POST of the JSON body. Public endpoints are
    rate limited, so each host is spaced by `min_gap` seconds; a 429 or 5xx is retried at most
    `retries` times after a short, capped back-off. The whole scan stops asking once `budget_s` has
    elapsed, which turns a hung network into a partial result instead of a stuck tab.
    """

    def __init__(self, timeout: float = 12.0, budget_s: float = 60.0, retries: int = 2,
                 min_gap: float = 0.25, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.timeout, self.retries, self.min_gap = timeout, retries, min_gap
        self._clock, self._sleep = clock, sleep
        self._deadline = clock() + budget_s
        self._last: dict[str, float] = {}

    def __call__(self, url: str, body: Any = None) -> Any:
        host = urllib.parse.urlparse(url).netloc
        data = None if body is None else json.dumps(body).encode()
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if data is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(self.retries + 1):
            now = self._clock()
            if now > self._deadline:
                raise WalletHttpError(0, "scan time budget used up")
            wait = self._last.get(host, 0.0) + self.min_gap - now
            if wait > 0:
                self._sleep(min(wait, 2.0))
            self._last[host] = self._clock()
            req = urllib.request.Request(url, data=data, headers=headers)
            try:
                remaining = self._deadline - self._clock()
                if remaining <= 0:
                    raise WalletHttpError(0, "scan time budget used up")
                with urllib.request.urlopen(req, timeout=min(self.timeout, remaining)) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        pause = float(retry_after) if retry_after else 0.8 * (attempt + 1)
                    except ValueError:
                        pause = 0.8 * (attempt + 1)
                    self._sleep(min(pause, 4.0))
                    continue
                raise WalletHttpError(exc.code, f"HTTP {exc.code} from {host}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < self.retries:
                    self._sleep(0.5 * (attempt + 1))
                    continue
                raise WalletHttpError(0, f"{host}: {getattr(exc, 'reason', exc)}") from None
            except ValueError as exc:
                raise WalletHttpError(0, f"{host} sent something that is not JSON: {exc}") from None
        raise WalletHttpError(0, f"{host}: gave up")

    def base_token_balances(self, address: str, page_token: str | None = None) -> Any:
        """Read one indexed page through the optional, independently configured CDP CLI.

        The CLI owns its API credentials. This process never loads them, forwards stderr, or invokes
        a signing command. Fixed argv and closed stdin prevent shell expansion and login prompts.
        """
        if not valid_evm_address(address):
            raise WalletHttpError(0, "invalid Base address")
        executable = shutil.which("cdp")
        if executable is None:
            # GUI launchers often omit Homebrew from PATH.
            executable = next((p for p in ("/opt/homebrew/bin/cdp", "/usr/local/bin/cdp")
                               if os.path.isfile(p) and os.access(p, os.X_OK)), None)
        if executable is None:
            raise WalletHttpError(0, "CDP CLI unavailable; install and configure cdp for indexed discovery")
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise WalletHttpError(0, "scan time budget used up")
        argv = [executable, "data", "evm", "token-balances", "base", address, "pageSize==100"]
        if page_token:
            argv.append("pageToken==" + page_token)
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    timeout=min(self.timeout, remaining), check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise WalletHttpError(0, "CDP balance request could not finish") from None
        if result.returncode:
            # CLI errors may contain authentication details; expose only the remedy.
            raise WalletHttpError(0, "CDP balance request failed; check cdp environment and API access")
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise WalletHttpError(0, "CDP balance reply was not JSON") from None


# -- result shapes ------------------------------------------------------------------------------------


@dataclass
class ChainScan:
    chain: str
    address: str
    native: dict[str, Any] | None = None
    holdings: list[dict[str, Any]] = field(default_factory=list)
    stakes: list[dict[str, Any]] = field(default_factory=list)
    positions: list[dict[str, Any]] = field(default_factory=list)
    contracts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Chain-specific detail merged into the result (an xpub scan's script types and derived counts).
    extra: dict[str, Any] = field(default_factory=dict)

    def error(self, source: str, exc: Exception) -> None:
        self.errors.append({"source": source, "message": str(exc)})

    def counted(self) -> list[dict[str, Any]]:
        """Every row that goes into the total: native, non-flagged holdings, stakes, valued positions."""
        rows = [self.native] if self.native else []
        rows += [h for h in self.holdings if h["included"]]
        rows += self.stakes
        rows += [p for p in self.positions if p.get("value_usd") is not None]
        return rows

    def to_dict(self) -> dict[str, Any]:
        total = sum(r.get("usd") or r.get("value_usd") or 0.0 for r in self.counted())
        # A balance with no price is unknown, not zero: it stays out of the total and is named here, so a
        # reader cannot take the total for the whole value.
        unpriced = [r["symbol"] for r in ([self.native] if self.native else []) + [h for h in self.holdings if h["included"]]
                    + self.stakes if r.get("usd") is None and (r.get("amount") or 0) > 0]
        flagged = [h for h in self.holdings if h["airdrop"]]
        got_any = bool(self.native or self.holdings or self.stakes or self.positions)
        status = "ok" if not self.errors else ("partial" if got_any else "error")
        return {**self.extra, "unpriced": unpriced, "total_complete": not unpriced and not self.errors,
            "chain": self.chain, "label": LABEL, "address": self.address, "status": status,
            "total_usd": total, "native": self.native,
            "holdings": self.holdings, "stakes": self.stakes, "positions": self.positions,
            "contracts": self.contracts, "errors": self.errors, "notes": self.notes,
            "counts": {"holdings": len([h for h in self.holdings if h["included"]]),
                       "airdrop_flagged": len(flagged), "stakes": len(self.stakes),
                       "positions": len(self.positions), "contracts": len(self.contracts)},
            "airdrop_excluded_usd": sum(h["usd"] or 0.0 for h in flagged),
        }


def _num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return None
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return None


def airdrop_reasons(symbol: str, name: str, *, price: float | None, liquidity: float | None,
                    verified: bool, known: bool) -> list[str]:
    """Why a token looks like an unsolicited airdrop; an empty list means it does not.

    A known or verified-and-liquid token is never flagged on price alone. Spam wording flags a token
    even when it has a price, because a fake pool can price anything.
    """
    reasons = []
    if _SPAM_TEXT.search(f"{symbol} {name}"):
        reasons.append("spam-style name or symbol")
    if not known and not verified:
        if price is None:
            reasons.append("no market price")
        elif liquidity is not None and liquidity < MIN_LIQUIDITY_USD:
            reasons.append(f"thin liquidity (under ${MIN_LIQUIDITY_USD:,.0f})")
    return reasons


# -- Solana -------------------------------------------------------------------------------------------


def _rpc(fetch: Fetch, url: str, method: str, params: list, ident: int = 1) -> Any:
    reply = fetch(url, {"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
    if not isinstance(reply, dict):
        raise WalletHttpError(0, f"{method}: unexpected reply")
    if reply.get("error"):
        err = reply["error"]
        raise WalletHttpError(0, f"{method}: {err.get('message') if isinstance(err, dict) else err}")
    return reply.get("result")


def solana_links(address: str, kind: str) -> str:
    return f"{SOLANA_EXPLORER}/{kind}/{address}"


def scan_solana(address: str, fetch: Fetch, rpc: str = SOLANA_RPC) -> ChainScan:
    scan = ChainScan("solana", address)
    sol_price: float | None = None
    mints: dict[str, dict[str, Any]] = {}

    try:
        lamports = _rpc(fetch, rpc, "getBalance", [address])
        value = lamports.get("value") if isinstance(lamports, dict) else lamports
        sol = (_num(value) or 0.0) / LAMPORTS
        scan.native = {"symbol": "SOL", "name": "Solana", "amount": sol, "price_usd": None, "usd": None,
                       "source": LABEL, "kind": "native"}
    except WalletHttpError as exc:
        scan.error("solana getBalance", exc)

    empty_accounts = 0
    for program, label in ((TOKEN_PROGRAM, "Token"), (TOKEN_2022_PROGRAM, "Token-2022")):
        try:
            result = _rpc(fetch, rpc, "getTokenAccountsByOwner",
                          [address, {"programId": program}, {"encoding": "jsonParsed"}])
        except WalletHttpError as exc:
            scan.error(f"solana getTokenAccountsByOwner ({label})", exc)
            continue
        for item in (result or {}).get("value", []):
            info = (((item.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
            mint, amount = info.get("mint"), info.get("tokenAmount") or {}
            ui = _num(amount.get("uiAmountString")) if amount.get("uiAmountString") is not None else _num(amount.get("uiAmount"))
            if not mint or ui is None:
                continue
            if ui == 0:
                empty_accounts += 1
                continue
            row = mints.setdefault(mint, {"mint": mint, "amount": 0.0, "accounts": [], "program": program,
                                          "program_name": label, "decimals": amount.get("decimals")})
            row["amount"] += ui
            row["accounts"].append(item.get("pubkey"))
    if empty_accounts:
        scan.notes.append(f"{empty_accounts} empty token account(s) hold rent only and are not listed")

    # Stake accounts: the address may be the staker or the withdrawer.
    seen: set[str] = set()
    for offset, role in ((12, "staker"), (44, "withdrawer")):
        try:
            result = _rpc(fetch, rpc, "getProgramAccounts",
                          [STAKE_PROGRAM, {"encoding": "jsonParsed",
                                           "filters": [{"memcmp": {"offset": offset, "bytes": address}}]}])
        except WalletHttpError as exc:
            scan.error(f"solana getProgramAccounts (stake, {role})", exc)
            continue
        for item in result or []:
            pubkey = item.get("pubkey")
            if not pubkey or pubkey in seen:
                continue
            seen.add(pubkey)
            lamports = _num((item.get("account") or {}).get("lamports")) or 0.0
            info = (((item.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
            delegation = ((info.get("stake") or {}).get("delegation") or {})
            scan.stakes.append({"account": pubkey, "role": role, "amount": lamports / LAMPORTS,
                                "symbol": "SOL", "voter": delegation.get("voter"), "price_usd": None,
                                "usd": None, "source": LABEL, "kind": "stake",
                                "link": solana_links(pubkey, "account")})

    # Prices and token facts, in as few calls as the APIs allow.
    prices: dict[str, dict[str, Any]] = {}
    meta: dict[str, dict[str, Any]] = {}
    ids = [WSOL_MINT] + sorted(mints)
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        try:
            reply = fetch(f"{JUPITER_PRICE}?ids={','.join(chunk)}")
            if isinstance(reply, dict):
                prices.update({k: v for k, v in reply.items() if isinstance(v, dict)})
        except WalletHttpError as exc:
            scan.error("jupiter price", exc)
            break
    mint_list = sorted(mints)
    for i in range(0, len(mint_list), 100):
        chunk = mint_list[i:i + 100]
        try:
            reply = fetch(f"{JUPITER_TOKENS}?query={','.join(chunk)}")
            for tok in reply if isinstance(reply, list) else []:
                if isinstance(tok, dict) and tok.get("id"):
                    meta[tok["id"]] = tok
        except WalletHttpError as exc:
            scan.error("jupiter token metadata", exc)
            break

    sol_price = _num((prices.get(WSOL_MINT) or {}).get("usdPrice"))
    if scan.native is not None:
        scan.native["price_usd"] = sol_price
        scan.native["usd"] = None if sol_price is None else scan.native["amount"] * sol_price
        scan.contracts.append({"holding": "SOL", "kind": "wallet", "address": address,
                               "program": "System Program", "link": solana_links(address, "account")})
    for st in scan.stakes:
        st["price_usd"] = sol_price
        st["usd"] = None if sol_price is None else st["amount"] * sol_price
        scan.contracts.append({"holding": "SOL (staked)", "kind": "stake account", "address": st["account"],
                               "program": STAKE_PROGRAM, "link": st["link"]})

    dust = 0
    for mint, row in sorted(mints.items()):
        tok = meta.get(mint, {})
        price = _num((prices.get(mint) or {}).get("usdPrice"))
        if price is None:
            price = _num(tok.get("usdPrice"))
        liquidity = _num((prices.get(mint) or {}).get("liquidity"))
        if liquidity is None:
            liquidity = _num(tok.get("liquidity"))
        symbol, name = str(tok.get("symbol") or mint[:4] + "…"), str(tok.get("name") or "unknown token")
        verified = bool(tok.get("isVerified")) or "verified" in (tok.get("tags") or [])
        known = mint == WSOL_MINT
        reasons = airdrop_reasons(symbol, name, price=price, liquidity=liquidity,
                                  verified=verified, known=known)
        usd = None if price is None else row["amount"] * price
        if usd is not None and usd < DUST_USD:
            dust += 1      # a few millionths of a coin: listing it would only be noise
            continue
        scan.holdings.append({
            "symbol": symbol, "name": name, "mint": mint, "amount": row["amount"], "price_usd": price,
            "usd": usd, "program": row["program_name"], "accounts": row["accounts"], "verified": verified,
            "airdrop": bool(reasons), "airdrop_reasons": reasons, "included": not reasons,
            "source": LABEL, "kind": "spl-token",
            "link": solana_links(mint, "token")})
        scan.contracts.append({"holding": symbol, "kind": "token mint", "address": mint,
                               "program": row["program_name"], "link": solana_links(mint, "token"),
                               "airdrop": bool(reasons)})
        for acct in row["accounts"]:
            scan.contracts.append({"holding": symbol, "kind": "token account", "address": acct,
                                   "program": row["program_name"], "link": solana_links(acct, "account"),
                                   "airdrop": bool(reasons)})
    if dust:
        scan.notes.append(f"{dust} balance(s) worth under ${DUST_USD} are not listed")
    if any(h["airdrop"] for h in scan.holdings):
        scan.notes.append("flagged airdrop tokens are listed but excluded from totals; their sites and "
                          "contracts are not visited or called")
    return scan


# -- Base ---------------------------------------------------------------------------------------------


def _pad(addr: str) -> str:
    return addr.lower().removeprefix("0x").rjust(64, "0")


def _hex_int(value: Any) -> int | None:
    if isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{1,64}", value):
        return int(value, 16)
    return None


def _decode_string(value: Any) -> str | None:
    """ABI string, or the bytes32 some old tokens return, decoded; None when it is neither."""
    if not isinstance(value, str) or not value.startswith("0x") or len(value) < 66:
        return None
    try:
        raw = bytes.fromhex(value[2:])
        if len(raw) >= 96:
            length = int.from_bytes(raw[32:64], "big")
            if 0 < length <= len(raw) - 64:
                return raw[64:64 + length].decode("utf-8", "replace")
        return raw[:32].rstrip(b"\x00").decode("utf-8", "replace") or None
    except (ValueError, UnicodeDecodeError):
        return None


def _batch(fetch: Fetch, rpc: str, calls: list[tuple[str, list]]) -> list[Any]:
    """One JSON-RPC batch. A per-call error comes back as None, so one bad token cannot sink the rest."""
    if not calls:
        return []
    body = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
    reply = fetch(rpc, body)
    if not isinstance(reply, list):
        raise WalletHttpError(0, "batch reply was not a list")
    by_id = {r.get("id"): r for r in reply if isinstance(r, dict)}
    return [(by_id.get(i) or {}).get("result") if not (by_id.get(i) or {}).get("error") else None
            for i in range(len(calls))]


def _eth_call(to: str, data: str) -> tuple[str, list]:
    return "eth_call", [{"to": to, "data": data}, "latest"]


def base_links(address: str, kind: str = "address") -> str:
    return f"{BASE_EXPLORER}/{kind}/{address}"


def daemon_context(status: dict[str, Any] | None, ledger_tokens: list[str] | None) -> dict[str, Any]:
    """What the liquidity daemon already knows: token addresses it watches and the positions it reports."""
    tokens: dict[str, str] = {}
    for t in ((status or {}).get("wallet") or {}).get("tokens") or []:
        if isinstance(t, dict) and valid_evm_address(str(t.get("address", ""))):
            tokens[t["address"].lower()] = str(t.get("symbol") or "")
    for addr in ledger_tokens or []:
        if valid_evm_address(addr):
            tokens.setdefault(addr.lower(), "")
    positions = [p for p in ((status or {}).get("positions") or []) if isinstance(p, dict)]
    return {"tokens": tokens, "positions": positions, "mode": (status or {}).get("mode")}


def _raw_token_amount(value: Any, decimals: Any) -> tuple[int, int]:
    """Reject malformed indexed amounts before scaling; never round an integer through float."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,78}", value):
        raise WalletHttpError(0, "invalid indexed token amount")
    if isinstance(decimals, bool) or not isinstance(decimals, (str, int)) or not str(decimals).isdigit():
        raise WalletHttpError(0, "invalid indexed token decimals")
    dec = int(decimals)
    if not 0 <= dec <= 255:
        raise WalletHttpError(0, "invalid indexed token decimals")
    return int(value), dec


def _base_indexed_tokens(address: str, fetch: Fetch, scan: ChainScan) -> tuple[dict, bool]:
    """CDP first, then paginated Blockscout. Retain earlier pages if a later page fails."""
    indexer: dict[str, dict[str, Any]] = {}
    read_page = getattr(fetch, "base_token_balances", None)
    if callable(read_page):
        cursor = None
        seen: set[str] = set()
        try:
            for _ in range(MAX_TOKEN_PAGES):
                reply = read_page(address, cursor)
                if not isinstance(reply, dict) or not isinstance(reply.get("balances"), list):
                    raise WalletHttpError(0, "CDP balance reply has no balances list")
                for row in reply["balances"]:
                    if not isinstance(row, dict):
                        raise WalletHttpError(0, "invalid CDP balance row")
                    tok, amt = row.get("token"), row.get("amount")
                    if not isinstance(tok, dict) or not isinstance(amt, dict):
                        raise WalletHttpError(0, "invalid CDP token metadata")
                    addr = str(tok.get("contractAddress") or "")
                    if not valid_evm_address(addr) or tok.get("network") != "base":
                        raise WalletHttpError(0, "invalid CDP token address or network")
                    raw, dec = _raw_token_amount(amt.get("amount"), amt.get("decimals"))
                    indexer[addr.lower()] = {
                        "token": {"address_hash": addr, "symbol": tok.get("symbol"),
                                  "name": tok.get("name"), "decimals": dec},
                        "item": {"value": str(raw)}, "via": "cdp"}
                cursor = reply.get("nextPageToken")
                if not cursor:
                    scan.notes.append("Base token discovery: CDP indexed balances (all pages); "
                                      "trusted tokens verified by balanceOf; other balances are indexed reads")
                    return indexer, True
                if not isinstance(cursor, str) or cursor in seen:
                    raise WalletHttpError(0, "CDP pagination repeated or invalid cursor")
                seen.add(cursor)
            raise WalletHttpError(0, "CDP token page limit reached; discovery is incomplete")
        except WalletHttpError as exc:
            scan.error("cdp token list", exc)

    params: dict[str, Any] = {"type": "ERC-20"}
    seen_pages: set[str] = set()
    try:
        for _ in range(MAX_TOKEN_PAGES):
            query = urllib.parse.urlencode(params)
            reply = fetch(f"{BLOCKSCOUT}/addresses/{address}/tokens?{query}")
            if not isinstance(reply, dict) or not isinstance(reply.get("items"), list):
                raise WalletHttpError(0, "Blockscout reply has no items list")
            for item in reply["items"]:
                if not isinstance(item, dict) or not isinstance(item.get("token"), dict):
                    raise WalletHttpError(0, "invalid Blockscout token row")
                tok = item["token"]
                if tok.get("type", "ERC-20") != "ERC-20":
                    continue
                addr = str(tok.get("address_hash") or tok.get("address") or "")
                if not valid_evm_address(addr):
                    raise WalletHttpError(0, "invalid Blockscout token address")
                _raw_token_amount(item.get("value"), tok.get("decimals"))
                indexer.setdefault(addr.lower(), {"item": item, "token": tok, "via": "blockscout"})
            next_params = reply.get("next_page_params")
            if not next_params:
                return indexer, True
            if not isinstance(next_params, dict):
                raise WalletHttpError(0, "invalid Blockscout pagination")
            cursor = json.dumps(next_params, sort_keys=True)
            if cursor in seen_pages:
                raise WalletHttpError(0, "Blockscout pagination repeated cursor")
            seen_pages.add(cursor)
            params = {**next_params, "type": "ERC-20"}
        raise WalletHttpError(0, "Blockscout token page limit reached; discovery is incomplete")
    except WalletHttpError as exc:
        why = "blocked by Cloudflare" if exc.status == 403 else str(exc)
        scan.error("blockscout token list", WalletHttpError(exc.status, f"{why} ({exc})"))
        scan.notes.append("token discovery incomplete: only available indexed pages, the built-in list, "
                          "the liquidity daemon's tokens and tokens you pass in were checked. "
                          "Other tokens cannot be discovered without an indexer")
    return indexer, False


def scan_base(address: str, fetch: Fetch, rpcs: tuple[str, ...] = BASE_RPCS, *,
              daemon: dict[str, Any] | None = None, extra_tokens: list[str] | None = None) -> ChainScan:
    scan = ChainScan("base", address)
    daemon = daemon or {"tokens": {}, "positions": [], "mode": None}

    def call_rpc(label: str, fn: Callable[[str], Any]) -> Any:
        """Try each public RPC in turn; the error names the last one if all fail."""
        last: Exception | None = None
        for url in rpcs:
            try:
                return fn(url)
            except WalletHttpError as exc:
                last = exc
        scan.error(label, last or RuntimeError("no RPC"))
        return None

    # 1. native ETH
    raw = call_rpc("base eth_getBalance", lambda u: _rpc(fetch, u, "eth_getBalance", [address, "latest"]))
    wei = _hex_int(raw)
    if wei is None and not any(e["source"] == "base eth_getBalance" for e in scan.errors):
        scan.error("base eth_getBalance", WalletHttpError(0, "invalid ETH balance reply"))
    eth = wei / 1e18 if wei is not None else None
    if eth is not None:
        scan.native = {"symbol": "ETH", "name": "Ether", "amount": eth, "price_usd": None, "usd": None,
                       "source": LABEL, "kind": "native"}

    # 2. candidate tokens: the indexer when it answers, plus the known set
    candidates: dict[str, dict[str, Any]] = {}
    for addr, sym, dec in KNOWN_BASE_TOKENS:
        candidates[addr.lower()] = {"address": addr, "symbol": sym, "decimals": dec, "name": sym,
                                    "known": True, "via": "built-in list"}
    for addr, sym in daemon["tokens"].items():
        candidates.setdefault(addr, {"address": _checksumless(addr), "symbol": sym or None, "decimals": None,
                                     "name": sym or None, "known": True, "via": "liquidity daemon"})
    for addr in extra_tokens or []:
        if valid_evm_address(addr):
            candidates.setdefault(addr.lower(), {"address": addr, "symbol": None, "decimals": None,
                                                 "name": None, "known": False, "via": "requested"})
    indexer, complete = _base_indexed_tokens(address, fetch, scan)
    scan.extra["token_discovery_complete"] = complete
    for addr, entry in indexer.items():
        tok = entry["token"]
        if addr == NATIVE_EVM:
            if scan.native is None:
                raw, dec = _raw_token_amount(entry["item"]["value"], tok["decimals"])
                scan.native = {"symbol": "ETH", "name": "Ether", "amount": raw / 10 ** dec,
                               "price_usd": None, "usd": None, "source": LABEL, "kind": "native",
                               "verified_onchain": False, "discovered_via": entry["via"]}
            continue
        c = candidates.setdefault(addr, {"address": tok.get("address_hash") or addr,
                                         "known": False, "via": entry["via"]})
        c.setdefault("symbol", None)
        c["symbol"] = c.get("symbol") or tok.get("symbol")
        c["name"] = c.get("name") or tok.get("name")
        dec = _num(tok.get("decimals"))
        c["decimals"] = c.get("decimals") if c.get("decimals") is not None else (None if dec is None else int(dec))
        c["indexer_value"] = int(entry["item"]["value"])
        c["indexer_rate"] = _num(tok.get("exchange_rate"))

    # 3. Only call trusted or explicitly requested contracts. Indexed airdrops stay indexed reads.
    addrs = sorted(candidates)
    rpc_addrs = [a for a in addrs if candidates[a]["known"] or candidates[a]["via"] == "requested"]
    verified: set[str] = set()
    balances: dict[str, int | None] = {a: c.get("indexer_value") for a, c in candidates.items()}
    for i in range(0, len(rpc_addrs), 40):
        chunk = rpc_addrs[i:i + 40]
        out = call_rpc("base balanceOf batch", lambda u, ch=chunk: _batch(
            fetch, u, [_eth_call(a, ERC20_BALANCE_OF + _pad(address)) for a in ch]))
        for a, res in zip(chunk, out or [None] * len(chunk)):
            value = _hex_int(res)
            if value is not None:
                balances[a] = value
                verified.add(a)
            elif balances.get(a) is not None:
                scan.error("base balanceOf", WalletHttpError(0, f"{a}: using indexed balance; RPC read failed"))
            else:
                scan.error("base balanceOf", WalletHttpError(0, f"{a}: RPC balance unavailable"))
    # metadata for tokens that came without it
    need = [a for a in rpc_addrs if balances.get(a) and (candidates[a].get("decimals") is None
                                                      or not candidates[a].get("symbol"))]
    if need:
        calls = [c for a in need for c in (_eth_call(a, ERC20_DECIMALS), _eth_call(a, ERC20_SYMBOL),
                                           _eth_call(a, ERC20_NAME))]
        out = call_rpc("base token metadata", lambda u: _batch(fetch, u, calls)) or [None] * len(calls)
        for j, a in enumerate(need):
            dec, sym, name = out[3 * j], out[3 * j + 1], out[3 * j + 2]
            if candidates[a].get("decimals") is None and _hex_int(dec) is not None:
                candidates[a]["decimals"] = _hex_int(dec)
            candidates[a]["symbol"] = candidates[a].get("symbol") or _decode_string(sym) or "?"
            candidates[a]["name"] = candidates[a].get("name") or _decode_string(name) or candidates[a]["symbol"]

    held = {a: c for a, c in candidates.items() if balances.get(a) and c.get("decimals") is not None}
    skipped = len([a for a in addrs if balances.get(a) is None])
    if skipped and not any(e["source"] == "base balanceOf batch" for e in scan.errors):
        scan.notes.append(f"{skipped} token(s) did not answer balanceOf and are not listed")

    # 4. prices: bounded DefiLlama batches, DexScreener for what it did not price
    price: dict[str, float] = {}
    liquidity: dict[str, float] = {}
    if held or scan.native:
        keys = [f"base:{c['address']}" for c in held.values()] + ["coingecko:ethereum"]
        coins: dict[str, Any] = {}
        for i in range(0, len(keys), 40):
            try:
                reply = fetch(LLAMA_PRICES + ",".join(keys[i:i + 40]))
                coins.update((reply or {}).get("coins", {}))
            except WalletHttpError as exc:
                scan.error("defillama prices", exc)
        if coins:
            for a, c in held.items():
                p = coins.get(f"base:{c['address']}") or coins.get(f"base:{a}") or {}
                if _num(p.get("price")) is not None and (_num(p.get("confidence")) or 0.0) >= 0.5:
                    price[a] = _num(p["price"])
        eth_price = _num((coins.get("coingecko:ethereum") or {}).get("price"))
        unpriced = [c["address"] for a, c in held.items() if a not in price]
        for i in range(0, len(unpriced), 30):
            chunk = unpriced[i:i + 30]
            try:
                reply = fetch(DEXSCREENER + ",".join(chunk))
            except WalletHttpError as exc:
                scan.error("dexscreener prices", exc)
                break
            best: dict[str, tuple[float, float]] = {}
            for pair in reply if isinstance(reply, list) else []:
                base = (pair.get("baseToken") or {}).get("address", "").lower()
                px, liq = _num(pair.get("priceUsd")), _num((pair.get("liquidity") or {}).get("usd")) or 0.0
                if base and px is not None and liq >= best.get(base, (0.0, -1.0))[1]:
                    best[base] = (px, liq)
            for a, (px, liq) in best.items():
                price[a], liquidity[a] = px, liq
        for a in held:  # fall back to the indexer's own exchange rate
            if a not in price and candidates[a].get("indexer_rate") is not None:
                price[a] = candidates[a]["indexer_rate"]
        if scan.native is not None:
            scan.native["price_usd"] = eth_price
            scan.native["usd"] = None if eth_price is None else scan.native["amount"] * eth_price
    if scan.native is not None:
        scan.contracts.append({"holding": "ETH", "kind": "wallet", "address": address,
                               "program": "externally owned account", "link": base_links(address)})

    # 5. holdings
    dust = 0
    for a, c in sorted(held.items()):
        dec = c["decimals"]
        amount = balances[a] / (10 ** dec)
        if price.get(a) is not None and amount * price[a] < DUST_USD:
            dust += 1      # e.g. 9e-18 DAI left behind by a swap; listing it would only be noise
            continue
        mismatch = None
        if a in verified and c.get("indexer_value") is not None:
            ind = c["indexer_value"] / (10 ** dec)
            if abs(ind - amount) > 0.005 * max(amount, 1e-18):
                mismatch = f"indexer said {ind:g}, on-chain balanceOf says {amount:g}; on-chain used"
        px = price.get(a)
        reasons = airdrop_reasons(str(c.get("symbol") or ""), str(c.get("name") or ""), price=px,
                                  liquidity=liquidity.get(a), verified=False,
                                  known=bool(c.get("known")))
        if not c.get("known") and c["via"] != "requested":
            reasons.append("unrecognized indexed token; excluded until explicitly requested")
        scan.holdings.append({
            "symbol": c.get("symbol") or "?", "name": c.get("name") or "", "address": c["address"],
            "amount": amount, "price_usd": px, "usd": None if px is None else amount * px,
            "verified_onchain": a in verified, "indexer_mismatch": mismatch, "discovered_via": c["via"],
            "airdrop": bool(reasons), "airdrop_reasons": reasons, "included": not reasons,
            "source": LABEL, "kind": "erc20", "link": base_links(c["address"], "token")})
        scan.contracts.append({"holding": c.get("symbol") or "?", "kind": "token contract",
                               "address": c["address"], "program": "ERC-20",
                               "link": base_links(c["address"], "token"), "airdrop": bool(reasons)})
    if dust:
        scan.notes.append(f"{dust} balance(s) worth under ${DUST_USD} are not listed")
    if any(h["airdrop"] for h in scan.holdings):
        scan.notes.append("flagged airdrop tokens are listed but excluded from totals; their sites and "
                          "contracts are not visited or called")

    # 6. position NFTs and the daemon's Aero positions
    daemon_ids = {str(p.get("token_id")): p for p in daemon["positions"] if p.get("token_id") is not None}
    owned_ids: set[str] = set()
    for proto, manager in POSITION_MANAGERS.items():
        count_raw = call_rpc(f"base {proto} balanceOf", lambda u, m=manager: _rpc(
            fetch, u, "eth_call", [{"to": m, "data": ERC20_BALANCE_OF + _pad(address)}, "latest"]))
        count = _hex_int(count_raw) or 0
        if not count:
            continue
        ids_raw = call_rpc(f"base {proto} tokenOfOwnerByIndex", lambda u, m=manager, n=count: _batch(
            fetch, u, [_eth_call(m, ERC721_TOKEN_OF_OWNER + _pad(address) + f"{i:064x}")
                       for i in range(min(n, MAX_NFTS_PER_MANAGER))])) or []
        for raw_id in ids_raw:
            tid = _hex_int(raw_id)
            if tid is None:
                continue
            owned_ids.add(str(tid))
            known = daemon_ids.get(str(tid)) if proto == "Aero Slipstream" else None
            scan.positions.append({
                "protocol": proto, "manager": manager, "token_id": tid, "held_by": "wallet",
                "pair": (known or {}).get("pair"), "value_usd": _num((known or {}).get("value_usd")),
                "value_source": "liquidity daemon state" if known else "not valued (no source)",
                "source": LABEL, "kind": "position-nft",
                "link": f"{BASE_EXPLORER}/nft/{manager}/{tid}"})
            scan.contracts.append({"holding": f"{proto} position #{tid}", "kind": "position NFT",
                                   "address": manager, "program": "NonfungiblePositionManager",
                                   "link": f"{BASE_EXPLORER}/nft/{manager}/{tid}"})
        if count > MAX_NFTS_PER_MANAGER:
            scan.notes.append(f"{proto}: {count} position NFTs, the first {MAX_NFTS_PER_MANAGER} are listed")
    for tid, p in daemon_ids.items():
        if tid in owned_ids:
            continue
        scan.positions.append({
            "protocol": "Aero Slipstream", "manager": POSITION_MANAGERS["Aero Slipstream"],
            "token_id": p.get("token_id"), "held_by": "gauge (staked) or not in the wallet",
            "pair": p.get("pair"), "value_usd": _num(p.get("value_usd")),
            "value_source": "liquidity daemon state", "source": LABEL, "kind": "position-nft",
            "link": f"{BASE_EXPLORER}/nft/{POSITION_MANAGERS['Aero Slipstream']}/{p.get('token_id')}"})
        scan.contracts.append({"holding": f"Aero position #{p.get('token_id')}", "kind": "position NFT",
                               "address": POSITION_MANAGERS["Aero Slipstream"],
                               "program": "NonfungiblePositionManager",
                               "link": f"{BASE_EXPLORER}/nft/{POSITION_MANAGERS['Aero Slipstream']}/{p.get('token_id')}"})
    if daemon["positions"] and daemon.get("mode") != "live":
        scan.notes.append(f"daemon mode is {daemon.get('mode')!r}: its position values are not live")
    return scan


def _checksumless(addr: str) -> str:
    """The address as given; Base accepts any case, and a checksum needs keccak this module avoids."""
    return addr


# -- whole scan, key sources, history -----------------------------------------------------------------


CHAIN_ALIASES = {"btc": "bitcoin", "ltc": "litecoin", "doge": "dogecoin", "eth": "ethereum", "sol": "solana"}
CHAINS = ("solana", "base", "ethereum", "bitcoin", "litecoin", "dogecoin")


def normalise_chain(text: str) -> str | None:
    """A chain name (or alias) as one of `CHAINS`, `all`, or None when unknown."""
    t = (text or "all").strip().lower()
    t = CHAIN_ALIASES.get(t, t)
    return t if t == "all" or t in CHAINS else None


def scan_wallet(solana_address: str, base_address: str, fetch: Fetch, *, chain: str = "all",
                daemon: dict[str, Any] | None = None, extra_tokens: list[str] | None = None,
                now: float | None = None, eth_address: str = "",
                xpubs: dict[str, str] | None = None) -> dict[str, Any]:
    """Every configured wallet (or one chain), as one JSON-ready dict. Never raises for a network failure.

    `xpubs` maps "btc"/"ltc"/"doge" to an extended public key. A chain with nothing configured is listed
    under `skipped` only when it was asked for by name; under `all` it is simply not configured.
    """
    now = time.time() if now is None else now
    chain = normalise_chain(chain) or "all"
    xpubs = {k: v for k, v in (xpubs or {}).items() if v}
    chains: dict[str, Any] = {}
    skipped: list[str] = []
    explicit = chain != "all"
    if chain in ("all", "solana"):
        if valid_solana_address(solana_address):
            chains["solana"] = scan_solana(solana_address, fetch).to_dict()
        else:
            skipped.append("solana: no valid address in Settings")
    if chain in ("all", "base"):
        if valid_evm_address(base_address):
            chains["base"] = scan_base(base_address, fetch, daemon=daemon,
                                       extra_tokens=extra_tokens).to_dict()
        else:
            skipped.append("base: no valid address in Settings")
    if chain in ("all", "ethereum"):
        if valid_evm_address(eth_address):
            from .eth_scan import scan_ethereum  # noqa: PLC0415 - these modules import this one

            chains["ethereum"] = scan_ethereum(eth_address, fetch).to_dict()
        elif explicit:
            skipped.append("ethereum: no valid eth_address in Settings")
    from .utxo_scan import CHAIN_NAMES, scan_utxo_wallets  # noqa: PLC0415

    utxo_wanted = [c for c in CHAIN_NAMES if chain == "all" or chain == CHAIN_NAMES[c]]
    if utxo_wanted:
        scans, _ = scan_utxo_wallets({c: xpubs[c] for c in utxo_wanted if c in xpubs}, fetch,
                                     only=None if chain == "all" else chain)
        for name, scan in scans.items():
            chains[name] = scan.to_dict()
        for c in utxo_wanted:
            if c not in xpubs and explicit:
                skipped.append(f"{CHAIN_NAMES[c]}: no {c}_xpub in Settings")
    total = sum(c["total_usd"] for c in chains.values())
    statuses = {c["status"] for c in chains.values()}
    return {
        "label": LABEL, "scanned_at": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds"),
        "ts": now, "chains": chains, "total_usd": total, "skipped": skipped,
        "partial": bool(statuses - {"ok"}) or bool(skipped),
        "total_complete": all(c.get("total_complete", True) for c in chains.values()),
        "counts": {
            "holdings": sum(c["counts"]["holdings"] for c in chains.values()),
            "airdrop_flagged": sum(c["counts"]["airdrop_flagged"] for c in chains.values()),
            "stakes": sum(c["counts"]["stakes"] for c in chains.values()),
            "positions": sum(c["counts"]["positions"] for c in chains.values()),
            "contracts": sum(c["counts"]["contracts"] for c in chains.values()),
        },
        "read_only": "No key, signature or transaction is involved: public reads only.",
    }


KEY_FILES = (("base", "wallet.private", "EVM (Ethereum/Base) key"), ("solana", "solana.private", "Solana key"))


def key_dir() -> Path:
    return Path(os.environ.get("SOLTUI_KEY_DIR") or Path.home() / ".ssh")


def key_sources() -> dict[str, Any]:
    """Whether each signing-key file exists and is mode 600, by `stat` alone.

    The files are never opened, read, hashed or printed. Signing lives in a separate gated component
    that loads keys itself; this console only reports that the files are present and private.
    """
    rows = []
    for chain, name, label in KEY_FILES:
        path = key_dir() / name
        try:
            st = os.stat(path)
        except FileNotFoundError:
            rows.append({"chain": chain, "label": label, "path": str(path), "exists": False, "mode": None,
                         "mode_600": False, "problem": None})
            continue
        except OSError as exc:
            rows.append({"chain": chain, "label": label, "path": str(path), "exists": False, "mode": None,
                         "mode_600": False, "problem": f"stat failed: {exc}"})
            continue
        mode = stat_mod.S_IMODE(st.st_mode)
        rows.append({"chain": chain, "label": label, "path": str(path), "exists": True, "mode": format(mode, "04o"),
                     "mode_600": mode == 0o600, "problem": None if mode == 0o600 else
                     f"mode is {mode:04o}; it should be 0600"})
    return {"keys": rows,
            "note": "Status from stat only; the files are never opened. Signing lives in a separate gated "
                    "component that loads keys itself. This console has no private-key field."}


def history_path() -> Path:
    base = Path(os.environ.get("SOLTUI_CONFIG_DIR") or Path.home() / ".config" / "soltui")
    return base / "wallet-history.jsonl"


def record_scan(result: dict[str, Any], path: Path | None = None) -> None:
    """Append one summary line (time, totals per chain) so the P&L tab can show value over time."""
    line = {"ts": result["ts"], "total_usd": result["total_usd"],
            "chains": {k: c["total_usd"] for k, c in result["chains"].items()},
            "partial": result["partial"]}
    target = path or history_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")


def load_history(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or history_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for raw in lines:
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict) and _num(row.get("ts")) is not None and _num(row.get("total_usd")) is not None:
            out.append(row)
    return sorted(out, key=lambda r: r["ts"])
