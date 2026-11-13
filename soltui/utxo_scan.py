"""Watch a Bitcoin, Litecoin or Dogecoin wallet from its extended PUBLIC key. Read-only, keyless.

The xpub is turned into addresses on this machine (`hdwallet`). Only addresses are sent to the public
explorers, never the xpub, and the derived addresses are never logged, printed or returned: a result
carries counts and balances only.

## How a wallet is found

* Chains 0 (receive) and 1 (change). Addresses are checked in order until `GAP_LIMIT` (20) in a row
  have no history, the standard BIP44 stop rule.
* The version bytes of a plain `xpub` do not say which address style the wallet used, so Bitcoin and
  Litecoin try P2PKH, P2SH-P2WPKH and P2WPKH and keep each style that has history. A `ypub`/`zpub`
  announces its style and only that one is tried. Dogecoin is P2PKH only.

## Explorers (verified reachable 2026-11-07, all keyless)

* Bitcoin: mempool.space, then blockstream.info (the Esplora API).
* Litecoin: litecoinspace.org (Esplora).
* Dogecoin: BlockCypher, 20 addresses per request (Trezor's Blockbook and Dogechain sit behind a
  Cloudflare challenge for scripts).

## Honest limits

* A failed explorer call stops that branch and the result is `partial`: the balance is then a lower
  bound and the error names the source. It is never silently a smaller number.
* Used means "has ever had a transaction". A balance on an address past the gap limit is not found.
* The USD price comes from Coinbase. No price means the value is unknown: the figure is left out of
  the total and the chain says so.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import hdwallet
from .spot_prices import spot_prices
from .wallet import LABEL, ChainScan, WalletHttpError

GAP_LIMIT = 20
SATS = 1e8
CHAIN_NAMES = {"btc": "bitcoin", "ltc": "litecoin", "doge": "dogecoin"}
ESPLORA = {"btc": ("https://mempool.space/api", "https://blockstream.info/api"),
           "ltc": ("https://litecoinspace.org/api",)}
BLOCKCYPHER = "https://api.blockcypher.com/v1/doge/main/addrs/{addrs}/balance"
BLOCKCYPHER_BATCH = 20


@dataclass
class AddrStat:
    balance: int  # satoshi-style integer units, confirmed plus unconfirmed
    txs: int      # transactions ever seen; > 0 means the address is used
    utxos: int = 0


def _int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WalletHttpError(0, "explorer reply had a non-numeric field")
    try:
        valid = math.isfinite(value) and value >= 0 and int(value) == value
    except OverflowError:
        valid = False
    if not valid:
        raise WalletHttpError(0, "explorer reply had an invalid integer field")
    return int(value)


class EsploraBackend:
    """mempool.space-style `GET /address/<addr>`, with fallback bases tried in order."""

    def __init__(self, bases: tuple[str, ...], fetch: Callable[..., Any]) -> None:
        self.bases, self.fetch = bases, fetch
        self.name = bases[0].split("//")[1].split("/")[0]

    def stats(self, addresses: list[str]) -> list[AddrStat]:
        return [self._one(a) for a in addresses]

    def _one(self, address: str) -> AddrStat:
        last: WalletHttpError | None = None
        for i, base in enumerate(self.bases):
            try:
                reply = self.fetch(f"{base}/address/{address}")
                chain, pool = reply["chain_stats"], reply["mempool_stats"]
                if i:  # prefer the base that just worked for the rest of the scan
                    self.bases = self.bases[i:] + self.bases[:i]
                    self.name = self.bases[0].split("//")[1].split("/")[0]
                funded = _int(chain["funded_txo_sum"]) + _int(pool["funded_txo_sum"])
                spent = _int(chain["spent_txo_sum"]) + _int(pool["spent_txo_sum"])
                utxos = (_int(chain["funded_txo_count"]) + _int(pool["funded_txo_count"])
                         - _int(chain["spent_txo_count"]) - _int(pool["spent_txo_count"]))
                return AddrStat(funded - spent, _int(chain["tx_count"]) + _int(pool["tx_count"]), max(utxos, 0))
            except WalletHttpError as exc:
                last = exc
            except (KeyError, TypeError):
                last = WalletHttpError(0, f"{base.split('//')[1].split('/')[0]} sent an unexpected reply")
        raise last or WalletHttpError(0, "no explorer configured")


class BlockCypherBackend:
    """`GET /addrs/<a;b;c>/balance`: up to 20 addresses per request (one object when a single one)."""

    name = "api.blockcypher.com"

    RATE_LIMIT_WAITS = (8.0, 20.0, 40.0)  # its keyless window is small; 429s clear after a pause

    def __init__(self, fetch: Callable[..., Any], sleep: Callable[[float], None] = time.sleep) -> None:
        self.fetch, self.sleep = fetch, sleep

    def _get(self, url: str) -> Any:
        for wait in (*self.RATE_LIMIT_WAITS, None):
            try:
                return self.fetch(url)
            except WalletHttpError as exc:
                if exc.status != 429 or wait is None:
                    raise
                self.sleep(wait)

    def stats(self, addresses: list[str]) -> list[AddrStat]:
        out: list[AddrStat] = []
        for i in range(0, len(addresses), BLOCKCYPHER_BATCH):
            chunk = addresses[i:i + BLOCKCYPHER_BATCH]
            reply = self._get(BLOCKCYPHER.format(addrs=";".join(chunk)))
            rows = reply if isinstance(reply, list) else [reply]
            by_addr = {r.get("address"): r for r in rows if isinstance(r, dict)}
            if len(by_addr) != len(chunk) or any(a not in by_addr for a in chunk):
                # Provider messages may echo the derived wallet addresses.
                raise WalletHttpError(0, "blockcypher sent an unexpected address response")
            for a in chunk:
                r = by_addr[a]
                out.append(AddrStat(_int(r.get("final_balance")), _int(r.get("final_n_tx")), 0))
        return out


def backend_for(coin: str, fetch: Callable[..., Any]):
    return BlockCypherBackend(fetch) if coin == "doge" else EsploraBackend(ESPLORA[coin], fetch)


def _branch(coin: str, script: str, pubkeys: "Callable[[int], bytes]", backend, branch: int,
            gap: int) -> dict[str, Any]:
    """Scan one chain (0 receive / 1 change) of one script type until `gap` unused addresses in a row."""
    last_used, nxt = -1, 0
    balance = utxos = 0
    while nxt - (last_used + 1) < gap:
        need = gap - (nxt - (last_used + 1))
        batch = [hdwallet.encode_address(coin, script, pubkeys(i)) for i in range(nxt, nxt + need)]
        for offset, st in enumerate(backend.stats(batch)):
            if st.txs > 0:
                last_used = nxt + offset
            balance += st.balance
            utxos += st.utxos
        nxt += need
    return {"derived": nxt, "used": last_used + 1 if last_used >= 0 else 0, "balance": balance, "utxos": utxos}


def scan_xpub(coin: str, xpub: str, fetch: Callable[..., Any], *, gap_limit: int = GAP_LIMIT,
              backend=None) -> ChainScan:
    """Scan one extended public key. Never raises for a network failure; the result says what failed."""
    spec = hdwallet.COINS[coin]
    key = hdwallet.parse_extended_key(xpub, coin)  # raises ExtKeyError for a bad or private key
    scan = ChainScan(CHAIN_NAMES[coin], hdwallet.redact(xpub))
    backend = backend or backend_for(coin, fetch)
    chains = (key.child(0), key.child(1))
    cache: dict[tuple[int, int], bytes] = {}

    def pubkey(branch: int, index: int) -> bytes:
        if (branch, index) not in cache:
            cache[(branch, index)] = chains[branch].child(index).key
        return cache[(branch, index)]

    tried = hdwallet.script_types_for(coin, key)
    kept: list[dict[str, Any]] = []
    total_sats = 0
    derived = 0
    for script in tried:
        rows = []
        for branch in (0, 1):
            try:
                rows.append(_branch(coin, script, lambda i, b=branch: pubkey(b, i), backend, branch, gap_limit))
            except WalletHttpError as exc:
                scan.error(f"{CHAIN_NAMES[coin]} {script} {'receive' if branch == 0 else 'change'} "
                           f"({backend.name})", exc)
                rows.append({"derived": 0, "used": 0, "balance": 0, "utxos": 0, "failed": True})
        derived += sum(r["derived"] for r in rows)
        if any(r["used"] for r in rows) or any(r["balance"] for r in rows):
            kept.append({"type": script, "receive_used": rows[0]["used"], "change_used": rows[1]["used"],
                         "balance": sum(r["balance"] for r in rows) / SATS,
                         "utxos": sum(r["utxos"] for r in rows),
                         "complete": not any(r.get("failed") for r in rows)})
            total_sats += sum(r["balance"] for r in rows)
    scan.extra = {"kind": "xpub", "gap_limit": gap_limit, "derived_addresses": derived,
                  "script_types_tried": list(tried), "script_types": kept, "explorer": backend.name,
                  "key_style": key.hint or "plain (style not announced)"}
    amount = total_sats / SATS
    if scan.errors:
        scan.notes.append("an explorer failed, so this balance is a lower bound")
    if not kept and not scan.errors:
        scan.notes.append(f"no history found for {', '.join(tried)} addresses within the gap limit")
    scan.native = {"symbol": spec.symbol, "name": spec.name, "amount": amount, "price_usd": None, "usd": None,
                   "source": LABEL, "kind": "native"}
    return scan


def price_chain(scan: ChainScan, prices: dict[str, float | None]) -> None:
    """Fill `price_usd`/`usd` on a scan's rows from `prices`; a missing price stays None (unknown)."""
    for row in ([scan.native] if scan.native else []) + scan.holdings:
        px = prices.get(row["symbol"])
        row["price_usd"] = px
        row["usd"] = None if px is None else row["amount"] * px


def scan_utxo_wallets(keys: dict[str, str], fetch: Callable[..., Any], *, gap_limit: int = GAP_LIMIT,
                      only: str | None = None) -> tuple[dict[str, ChainScan], list[str]]:
    """Scan every configured coin in `keys` ({"btc": xpub, ...}). Returns (scans by chain name, notes)."""
    scans: dict[str, ChainScan] = {}
    notes: list[str] = []
    wanted = [c for c in ("btc", "ltc", "doge") if keys.get(c) and (only in (None, c, CHAIN_NAMES[c]))]
    prices, errs = spot_prices(fetch, [hdwallet.COINS[c].symbol for c in wanted])
    for coin in wanted:
        try:
            scan = scan_xpub(coin, keys[coin], fetch, gap_limit=gap_limit)
        except hdwallet.ExtKeyError as exc:
            scan = ChainScan(CHAIN_NAMES[coin], hdwallet.redact(keys[coin]))
            scan.errors.append({"source": f"{coin}_xpub", "message": str(exc)})
            scans[scan.chain] = scan
            continue
        price_chain(scan, prices)
        scans[scan.chain] = scan
    for message in errs:
        for scan in scans.values():
            scan.errors.append({"source": "price", "message": message})
    return scans, notes
