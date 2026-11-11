# SolTUI Jupiter Advanced Ordering Widget: Implementation Guide

## 1. Architectural Overview & Venue Multiplexing

SolTUI currently routes advanced orders exclusively through Coinbase (`coinbase_manual.py`). Adding Jupiter (`jup`) requires multiplexing between a centralized order book (Coinbase REST API) and a decentralized Solana aggregator (Jupiter Swap API v2 & Trigger API v2).

```
                      +-----------------------------+
                      |    #advanced-order-ticket   |
                      |   (soltui/tui.py: Select)   |
                      +--------------+--------------+
                                     |
                     +---------------+---------------+
                     |                               |
              [venue == "coinbase"]           [venue == "jupiter"]
                     |                               |
                     v                               v
         +-----------------------+       +-----------------------+
         |  soltui/commands.py   |       |  soltui/commands.py   |
         |  coinbase.order_*     |       |  jupiter.order_*      |
         +-----------+-----------+       +-----------+-----------+
                     |                               |
                     v                               v
         +-----------------------+       +-----------------------+
         | coinbase_manual.py    |       | jupiter_manual.py     |
         | • CDP REST API        |       | • jupiter_tokens.py   |
         | • Static Pair Catalog |       | • Swap API v2 (/order)|
         | • USD / Coin Size     |       | • Decimal Scaling     |
         | • 60s Preview Lock    |       | • Keypair Signer      |
         +-----------------------+       | • /execute (Beam)     |
                                         | • 45s Preview Lock    |
                                         +-----------------------+
```

### Key Differences & Invariants

| Invariant / Feature | Coinbase Implementation | Jupiter Implementation |
|---|---|---|
| **Pair Model** | Static products (e.g. `SOL-USDC`) from saved catalog | Dynamic SPL token mints; arbitrary input $\to$ output mint routes |
| **Price & Discovery** | Product book via Coinbase Advanced API | Jupiter Tokens API v2 (`/tokens/v2/search`, `/tokens/v2/toptraded/24h`) |
| **Sizing Units** | Base coin units or USD quote amount | Atomic integer lamports/units scaled by mint decimals (`10^decimals`) |
| **Execution Path** | CEX REST order submission (`POST /api/v3/brokerage/orders`) | `GET /swap/v2/order` $\to$ serialize $\to$ sign `VersionedTransaction` $\to$ `POST /swap/v2/execute` |
| **Settlement** | Offchain orderbook matching; delayed custodial fill | Atomic onchain transaction via Jupiter Beam / SWQoS (gasless/managed) |
| **Leverage & Position** | Spot 1x, Long only | Spot 1x, Long only (Jupiter Perps requires margin account / Pyth oracle) |
| **Safety Limits** | \$100 max per-order quote cap; file lock; no auto-retry | \$100 max per-order quote cap; file lock; no auto-retry |

---

## 2. Dynamic Token Discovery & Local Caching Engine (`soltui/jupiter_tokens.py`)

Solana hosts hundreds of thousands of tokens. Preloading all tokens into a static dropdown is impractical. The token engine provides:
1. **Local Persistent Cache**: Preloads top-traded 24h tokens and verified tokens into `~/.config/solmargintrader/jupiter_tokens.json`.
2. **Debounced Search**: Queries `https://api.jup.ag/tokens/v2/search?query={query}` (or `lite-api.jup.ag`) with 0.5 RPS pacing.
3. **Symbol & Mint Resolution**: Resolves tickers (e.g. `BONK`, `JUP`, `WIF`, `SOL`, `USDC`) to verified mint addresses and token decimals.

```python
"""soltui/jupiter_tokens.py: Dynamic SPL token registry and Jupiter Tokens API v2 client."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

BASE_URL = os.environ.get("JUPITER_BASE_URL", "https://api.jup.ag")
LITE_URL = "https://lite-api.jup.ag"
CACHE_TTL = 3600 * 4  # 4 hours


@dataclass(frozen=True)
class JupiterToken:
    address: str
    symbol: str
    name: str
    decimals: int
    is_verified: bool
    usd_price: float | None = None


def storage_dir() -> Path:
    base = os.environ.get("SOLMARGINTRADER_STORAGE")
    path = Path(base).expanduser() if base else Path.home() / ".config" / "solmargintrader"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def _cache_path() -> Path:
    return storage_dir() / "jupiter_tokens.json"


class TokenRegistry:
    def __init__(self, api_key: str | None = None, min_gap_s: float = 1.1):
        self.api_key = api_key or os.environ.get("JUPITER_API_KEY")
        self.base_url = BASE_URL if self.api_key else LITE_URL
        self.min_gap_s = min_gap_s
        self._last_call = 0.0
        self._memory_cache: dict[str, JupiterToken] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        p = _cache_path()
        if not p.is_file():
            return
        try:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("saved_at", 0) < CACHE_TTL:
                for item in data.get("tokens", []):
                    tok = JupiterToken(**item)
                    self._memory_cache[tok.address] = tok
                    self._memory_cache[tok.symbol.upper()] = tok
        except Exception:
            pass

    def _save_cache(self) -> None:
        p = _cache_path()
        tokens = [asdict(t) for t in set(self._memory_cache.values())]
        try:
            with p.open("w", encoding="utf-8") as f:
                json.dump({"saved_at": time.time(), "tokens": tokens}, f, indent=2)
        except Exception:
            pass

    def _http_get(self, path: str, params: dict[str, str]) -> Any:
        wait = self.min_gap_s - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "SolTUI-Advanced-Widget/1.0")
        req.add_header("Accept", "application/json")
        if self.api_key:
            req.add_header("x-api-key", self.api_key)

        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search(self, query: str) -> list[JupiterToken]:
        q = query.strip()
        if not q:
            return self.top_traded()
        
        # Exact match in memory cache
        if q.upper() in self._memory_cache:
            return [self._memory_cache[q.upper()]]
        if q in self._memory_cache:
            return [self._memory_cache[q]]

        try:
            data = self._http_get("/tokens/v2/search", {"query": q})
        except Exception:
            return [t for t in self._memory_cache.values() if q.upper() in t.symbol.upper()][:10]

        results = []
        for item in (data if isinstance(data, list) else []):
            addr = item.get("id") or item.get("address")
            if not addr:
                continue
            is_ver = bool(item.get("isVerified")) or "verified" in (item.get("tags") or [])
            tok = JupiterToken(
                address=addr,
                symbol=str(item.get("symbol") or addr[:6]).upper(),
                name=str(item.get("name") or "Unknown"),
                decimals=int(item.get("decimals") or 9),
                is_verified=is_ver,
                usd_price=float(item.get("usdPrice")) if item.get("usdPrice") is not None else None,
            )
            self._memory_cache[addr] = tok
            self._memory_cache[tok.symbol] = tok
            results.append(tok)
        self._save_cache()
        return results

    def top_traded(self) -> list[JupiterToken]:
        try:
            data = self._http_get("/tokens/v2/toptraded/24h", {})
            results = []
            for item in (data if isinstance(data, list) else []):
                addr = item.get("id") or item.get("address")
                if not addr:
                    continue
                tok = JupiterToken(
                    address=addr,
                    symbol=str(item.get("symbol") or addr[:6]).upper(),
                    name=str(item.get("name") or "Unknown"),
                    decimals=int(item.get("decimals") or 9),
                    is_verified=bool(item.get("isVerified")) or "verified" in (item.get("tags") or []),
                    usd_price=float(item.get("usdPrice")) if item.get("usdPrice") is not None else None,
                )
                self._memory_cache[addr] = tok
                self._memory_cache[tok.symbol] = tok
                results.append(tok)
            self._save_cache()
            return results[:20]
        except Exception:
            return [t for t in self._memory_cache.values() if t.is_verified][:20]

    def resolve_pair(self, text: str) -> tuple[JupiterToken, JupiterToken]:
        """Resolves raw pair input: 'BONK', 'BONK-USDC', 'BONK/SOL' into (base, quote)."""
        clean = text.strip().upper().replace("/", "-")
        if "-" in clean:
            base_sym, quote_sym = clean.split("-", 1)
        else:
            base_sym, quote_sym = clean, "USDC"

        base_matches = self.search(base_sym)
        if not base_matches:
            raise ValueError(f"Unknown token: {base_sym}")
        base_tok = base_matches[0]

        if quote_sym in ("USDC", "USD"):
            quote_matches = self.search(USDC_MINT)
        elif quote_sym == "SOL":
            quote_matches = self.search(WSOL_MINT)
        else:
            quote_matches = self.search(quote_sym)

        if not quote_matches:
            raise ValueError(f"Unknown quote token: {quote_sym}")
        return base_tok, quote_matches[0]
```

---

## 3. Order Quoting, Preview & Safety Module (`soltui/jupiter_manual.py`)

Adheres strictly to `coinbase_manual.py`'s safety pattern:
1. **Fail Closed**: Interrupted submissions block subsequent orders until state is resolved.
2. **Order Cap**: Estimated size capped at \$100 (`MAX_QUOTE`).
3. **Atomic Decimal Math**: Integer units scaled strictly by `token.decimals`.
4. **File Locking**: Atomic review storage in `~/.config/solmargintrader/manual-orders/jupiter-<id>.json`.

```python
"""soltui/jupiter_manual.py: Explicitly reviewed Jupiter Swap API v2 orders with disk locking."""
from __future__ import annotations

import fcntl
import json
import os
import re
import time
import uuid
import urllib.request
import urllib.parse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .jupiter_tokens import TokenRegistry, JupiterToken, WSOL_MINT, USDC_MINT

MAX_QUOTE = Decimal('100')
PREVIEW_SECONDS = 45


def _storage_dir() -> Path:
    base = os.environ.get("SOLMARGINTRADER_STORAGE")
    path = Path(base).expanduser() if base else Path.home() / ".config" / "solmargintrader"
    return path / "manual-orders"


def _preview_path(preview_id: str) -> Path:
    if not re.fullmatch(r'[0-9a-f]{32}', preview_id):
        raise ValueError('Invalid preview ID')
    return _storage_dir() / f"jup_{preview_id}.json"


@contextmanager
def _lock():
    _storage_dir().mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(_storage_dir() / '.jupiter.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _has_unresolved() -> bool:
    for p in _storage_dir().glob('jup_*.json'):
        try:
            with p.open(encoding='utf-8') as f:
                r = json.load(f)
            if r.get('state') in ('submitting', 'pending', 'unknown'):
                return True
        except Exception:
            return True
    return False


def order_preview(params: dict[str, Any], taker_pubkey: str) -> dict[str, Any]:
    with _lock():
        if _has_unresolved():
            raise ValueError("A previous Jupiter order is unresolved. Check onchain status before ordering.")

        pair = str(params.get("product_id", "")).strip()
        side = str(params.get("side", "")).strip().upper()
        size_str = str(params.get("size", "")).strip()
        unit = str(params.get("size_currency", "base")).strip().lower()

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        registry = TokenRegistry()
        base_tok, quote_tok = registry.resolve_pair(pair)

        try:
            size_dec = Decimal(size_str)
        except InvalidOperation:
            raise ValueError("Size must be a valid positive number")
        if size_dec <= 0:
            raise ValueError("Size must be greater than zero")

        # Determine in/out mints and raw atomic amount
        if side == "BUY":
            # BUY: Input is Quote token (e.g. USDC), Output is Base token (e.g. BONK)
            if unit == "quote":
                in_token, out_token = quote_tok, base_tok
                in_amount_raw = int(size_dec * (10 ** quote_tok.decimals))
            else:
                # User specified base units to buy; estimate quote inAmount using price
                if not base_tok.usd_price or base_tok.usd_price <= 0:
                    raise ValueError(f"Cannot auto-convert base size for unpriced token {base_tok.symbol}")
                est_quote = size_dec * Decimal(str(base_tok.usd_price))
                in_token, out_token = quote_tok, base_tok
                in_amount_raw = int(est_quote * (10 ** quote_tok.decimals))
        else:
            # SELL: Input is Base token, Output is Quote token
            in_token, out_token = base_tok, quote_tok
            in_amount_raw = int(size_dec * (10 ** base_tok.decimals))

        # Enforce $100 cap
        est_usd = (size_dec if in_token.address == USDC_MINT else
                   size_dec * Decimal(str(in_token.usd_price or 0)))
        if est_usd > MAX_QUOTE:
            raise ValueError(f"Order value ${est_usd:.2f} exceeds ${MAX_QUOTE:.2f} limit")

        # Call Jupiter Swap API v2 /order
        api_key = os.environ.get("JUPITER_API_KEY")
        base_url = "https://api.jup.ag" if api_key else "https://lite-api.jup.ag"
        req_params = {
            "inputMint": in_token.address,
            "outputMint": out_token.address,
            "amount": str(in_amount_raw),
            "taker": taker_pubkey,
            "slippageBps": str(params.get("slippage_bps", 50)),
        }
        url = f"{base_url}/swap/v2/order?{urllib.parse.urlencode(req_params)}"
        req = urllib.request.Request(url)
        if api_key:
            req.add_header("x-api-key", api_key)
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=12.0) as resp:
            quote_data = json.loads(resp.read().decode("utf-8"))

        out_amount_raw = int(quote_data["outAmount"])
        out_amount_dec = Decimal(out_amount_raw) / Decimal(10 ** out_token.decimals)
        price_impact = Decimal(str(quote_data.get("priceImpactPct", "0")))

        preview_id = uuid.uuid4().hex
        now = time.time()
        record = {
            "preview_id": preview_id,
            "venue": "jupiter",
            "product_id": f"{base_tok.symbol}-{quote_tok.symbol}",
            "side": side,
            "size": str(size_dec),
            "size_currency": unit,
            "in_token": asdict(in_token),
            "out_token": asdict(out_token),
            "in_amount_raw": in_amount_raw,
            "out_amount_raw": out_amount_raw,
            "out_amount_dec": str(out_amount_dec),
            "price_impact_pct": str(price_impact),
            "request_id": quote_data.get("requestId"),
            "transaction_b64": quote_data.get("transaction"),
            "created_at": now,
            "expires_at": now + PREVIEW_SECONDS,
            "state": "reviewed"
        }

        path = _preview_path(preview_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        return {
            "preview_id": preview_id,
            "product_id": f"{base_tok.symbol}-{quote_tok.symbol}",
            "side": side,
            "size": str(size_dec),
            "size_currency": unit,
            "expires_at": now + PREVIEW_SECONDS,
            "estimate": {
                "in_amount": f"{Decimal(in_amount_raw) / Decimal(10 ** in_token.decimals)} {in_token.symbol}",
                "out_amount": f"{out_amount_dec} {out_token.symbol}",
                "price_impact_pct": f"{price_impact * 100:.3f}%",
                "route_plan": [leg.get("swapInfo", {}).get("label") for leg in quote_data.get("routePlan", [])]
            },
            "notice": "Jupiter Swap v2 Meta-Aggregator route. Transaction landing managed via Beam."
        }
```

---

## 4. Keypair Signing & Execution Module (`soltui/jupiter_order.py`)

Uses `solders` (already installed in virtualenv) to deserialize the `VersionedTransaction`, sign the message, and dispatch to `POST /swap/v2/execute`.

```python
"""soltui/jupiter_order.py: VersionedTransaction signing and Jupiter Beam execution."""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any

from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from . import jupiter_manual as jm
from executor.signer import load_keypair


def submit_order(preview_id: str, keypair_path: str, expected_pubkey: str) -> dict[str, Any]:
    with jm._lock():
        path = jm._preview_path(preview_id)
        if not path.is_file():
            raise ValueError("Preview record not found")

        with path.open(encoding="utf-8") as f:
            rec = json.load(f)

        if rec.get("state") != "reviewed":
            raise ValueError(f"Invalid preview state: {rec.get('state')}")
        if rec.get("expires_at", 0) < jm.time.time():
            raise ValueError("Preview has expired. Generate a new quote.")

        # Mark as submitting immediately before network access
        rec["state"] = "submitting"
        rec["submit_started_at"] = jm.time.time()
        with path.open("w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)

        # 1. Load keypair with strict 0o600 file permissions and owner check
        keypair = load_keypair(keypair_path, expected_pubkey)

        # 2. Deserialize base64 VersionedTransaction from Jupiter /order
        raw_tx_bytes = base64.b64decode(rec["transaction_b64"])
        tx = VersionedTransaction.from_bytes(raw_tx_bytes)

        # 3. Sign transaction message
        message_bytes = bytes(tx.message)
        sig = keypair.sign_message(message_bytes)

        # Replace signature at the signer's account key index
        account_keys = tx.message.account_keys
        signer_idx = account_keys.index(keypair.pubkey())
        signatures = list(tx.signatures)
        signatures[signer_idx] = sig

        signed_tx = VersionedTransaction.populate(tx.message, signatures)
        signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")

        # 4. Dispatch to /swap/v2/execute
        api_key = os.environ.get("JUPITER_API_KEY")
        base_url = "https://api.jup.ag" if api_key else "https://lite-api.jup.ag"
        payload = {
            "signedTransaction": signed_b64,
            "requestId": rec["request_id"]
        }

        req = urllib.request.Request(
            f"{base_url}/swap/v2/execute",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        if api_key:
            req.add_header("x-api-key", api_key)

        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            rec["state"] = "unknown"
            rec["submit_error"] = str(exc)
            with path.open("w", encoding="utf-8") as f:
                json.dump(rec, f, indent=2)
            raise ValueError(f"Jupiter execute request error: {exc}. Reconcile onchain before retrying.") from None

        status = result.get("status")
        signature = result.get("signature")

        rec["state"] = "confirmed" if status == "Success" else "failed"
        rec["signature"] = signature
        rec["execute_result"] = result
        with path.open("w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)

        if status != "Success":
            raise ValueError(f"Transaction failed: {result.get('error')} (code: {result.get('code')})")

        return {
            "order_id": signature,
            "status": "FILLED",
            "venue": "jupiter",
            "signature": signature,
            "solscan_url": f"https://solscan.io/tx/{signature}",
            "in_amount": rec["in_amount_raw"],
            "out_amount": rec["out_amount_raw"],
        }
```

---

## 5. Command Registration (`soltui/commands.py`)

Expose Jupiter operations to the SolTUI dispatch layer:

```python
# In soltui/commands.py

@command("jupiter.tokens_search", "Search Solana tokens dynamically via Jupiter Tokens API v2.")
def jupiter_tokens_search(ctx: Context, p: dict[str, Any]) -> Any:
    from .jupiter_tokens import TokenRegistry
    registry = TokenRegistry()
    return {"tokens": [asdict(t) for t in registry.search(str(p.get("query", "")))]}


@command("jupiter.order_preview", "Review an estimated Jupiter swap; places no order.")
def jupiter_order_preview(ctx: Context, p: dict[str, Any]) -> Any:
    from . import jupiter_manual as jm
    taker = ctx.settings.get("solana_wallet_address", "")
    if not taker:
        raise ValueError("No Solana wallet configured in SolTUI settings")
    return jm.order_preview(p, taker_pubkey=taker)


@command("jupiter.order_submit", "Submit one explicitly confirmed, reviewed Jupiter swap.")
def jupiter_order_submit(ctx: Context, p: dict[str, Any]) -> Any:
    from . import jupiter_order as jo
    key_path = ctx.settings.get("solana_keypair_path", "~/.config/solana/id.json")
    expected_pubkey = ctx.settings.get("solana_wallet_address", "")
    return jo.submit_order(p["preview_id"], keypair_path=key_path, expected_pubkey=expected_pubkey)


@command("jupiter.order_quick", "Place a live Jupiter swap without second confirmation after opting in.")
def jupiter_order_quick(ctx: Context, p: dict[str, Any]) -> Any:
    preview = jupiter_order_preview(ctx, p)
    return jupiter_order_submit(ctx, {"preview_id": preview["preview_id"], "confirm": True})
```

---

## 6. Textual UI Wiring & Dynamic Autocomplete (`soltui/tui.py`)

### A. Updating the `#advanced-order-ticket` View
In `soltui/tui.py`:
1. Change `#advanced-venue` options from `[("Coinbase", "coinbase"), ("Jupiter — unavailable", "jupiter")]` to `[("Coinbase", "coinbase"), ("Jupiter", "jupiter")]`.
2. Update the ticket subtitle hint to reflect Jupiter market swaps.

```diff
--- a/soltui/tui.py
+++ b/soltui/tui.py
@@ -4705,4 +4705,4 @@
                 ticket.border_title = "Advanced order ticket"
-                yield Static("Coinbase market orders support amounts or balance percentages; conditional orders use coin units. $100 order cap. Jupiter is unavailable.", classes="hint")
+                yield Static("Coinbase & Jupiter spot swaps. Max $100 cap. Jupiter executes via onchain Beam routing.", classes="hint")
                 with Horizontal(classes="form-row"):
-                    yield Select([("Coinbase", "coinbase"), ("Jupiter — unavailable", "jupiter")], value="coinbase",
+                    yield Select([("Coinbase", "coinbase"), ("Jupiter", "jupiter")], value="coinbase",
                                  allow_blank=False, id="advanced-venue")
```

### B. Updating Form Validation (`_advanced_supported`)
Allow `venue == "jupiter"` for spot market orders:

```python
    def _advanced_supported(self) -> bool:
        venue, kind, side, product, size, unit = self._advanced_values()
        if (side not in ("BUY", "SELL") or not product or not size
                or self.query_one("#advanced-leverage", Select).value != "1x"
                or self.query_one("#advanced-position", Select).value != "long"):
            return False

        if venue == "jupiter":
            # Jupiter supports market swaps in base or quote units
            return kind == "market" and unit in ("quote", "base")

        if venue == "coinbase":
            if kind == "market":
                return unit in (("quote", "base", "percent") if side == "BUY" else ("base", "percent"))
            if kind not in ("limit", "stop_limit", "bracket") or unit != "base" or (kind == "bracket" and side != "SELL"):
                return False
            return bool(self.query_one("#advanced-limit-price", Input).value.strip()
                        and (kind == "limit" or self.query_one("#advanced-stop-price", Input).value.strip()))

        return False
```

### C. Dynamic Token Resolution Worker
Add debounced token autocomplete when typing in `#advanced-product` while `venue == "jupiter"`:

```python
    @on(Input.Changed, "#advanced-product")
    def _advanced_product_changed(self) -> None:
        if self._advanced_values()[0] != "jupiter":
            return
        query = self.query_one("#advanced-product", Input).value.strip()
        if len(query) >= 2:
            self._search_tokens_worker(query)

    @work(thread=True, exit_on_error=False, group="jupiter-token-search")
    def _search_tokens_worker(self, query: str) -> None:
        env = self._call("jupiter.tokens_search", {"query": query}, quiet=True)
        if env.get("ok"):
            self.call_from_thread(self._search_tokens_done, env.get("result", {}).get("tokens", []))

    def _search_tokens_done(self, tokens: list[dict[str, Any]]) -> None:
        if not tokens or self._advanced_values()[0] != "jupiter":
            return
        top = tokens[0]
        badge = "✓" if top.get("is_verified") else "⚠"
        price_str = f"${top.get('usd_price'):.4f}" if top.get("usd_price") else "No price"
        self.query_one("#advanced-message", Static).update(
            f"Resolved: {top.get('symbol')} ({badge} {top.get('name')}) · {price_str} · Mint: {top.get('address')[:8]}…"
        )
```

### D. Routing Preview & Execution
Branch `_advanced_preview_pressed`, `_advanced_submit_pressed`, and `_advanced_quick_pressed` based on `venue`:

```python
    @on(Button.Pressed, "#advanced-preview")
    def _advanced_preview_pressed(self) -> None:
        venue, kind, side, product, size, unit = self._advanced_values()
        if not self._advanced_supported():
            return
        self._coinbase_order_busy = True
        self._coinbase_order_controls()

        if venue == "jupiter":
            self.query_one("#advanced-message", Static).update("Fetching Jupiter Swap v2 quote…")
            operation = "jupiter.order_preview"
            params = {"product_id": product, "side": side, "size": size, "size_currency": unit}
        else:
            self.query_one("#advanced-message", Static).update("Reviewing with Coinbase…")
            operation = "coinbase.order_preview"
            params = {"product_id": product, "side": side, "size": size, "size_currency": unit}

        self._advanced_worker(operation, params, self._advanced_generation, self._advanced_signature())
```

---

## 7. Testing & Verification Suite

Add end-to-end Textual async UI test cases to `soltui/tests/test_advanced_order_ui.py`:

```python
    async def test_jupiter_swap_preview_and_execute_flow(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-wallet"
            await pilot.pause(.4)

            # Select Jupiter venue
            app.query_one("#advanced-venue", Select).value = "jupiter"
            app.query_one("#advanced-product", Input).value = "BONK-USDC"
            app.query_one("#advanced-size", Input).value = "10.0"
            app.query_one("#advanced-unit", Select).value = "quote"
            app.query_one("#advanced-armed", Checkbox).value = True
            await pilot.pause()

            self.assertTrue(self.query_one("#advanced-preview", Button).enabled)

            calls = []
            def mock_call(name, params=None, **kwargs):
                calls.append((name, params))
                if name == "jupiter.order_preview":
                    return env({
                        "preview_id": "jup-p1",
                        "product_id": "BONK-USDC",
                        "side": "BUY",
                        "size": "10.0",
                        "size_currency": "quote",
                        "expires_at": time.time() + 45,
                        "estimate": {"out_amount": "450000 BONK", "price_impact_pct": "0.02%"},
                        "notice": "Jupiter route ready"
                    })
                if name == "jupiter.order_submit":
                    return env({
                        "order_id": "sig-123",
                        "status": "FILLED",
                        "signature": "sig-123",
                        "solscan_url": "https://solscan.io/tx/sig-123"
                    })
                return env({})

            with mock.patch.object(app, "_call", side_effect=mock_call):
                app._advanced_preview_pressed()
                await pilot.pause(.3)

                self.assertEqual(calls[0][0], "jupiter.order_preview")
                self.assertIsNotNone(app._advanced_preview_data)

                # Submit order
                app._advanced_submit_pressed()
                await pilot.pause(.3)

                self.assertEqual(calls[1][0], "jupiter.order_submit")
                self.assertIn("sig-123", app.query_one("#advanced-receipt", Static).renderable)
```

---

## 8. Rollout Plan & Checkpoints

1. **Phase 1 (Token Engine)**: Install `soltui/jupiter_tokens.py`, test token query and cache on `lite-api.jup.ag`.
2. **Phase 2 (Manual Review & Disk Lock)**: Add `soltui/jupiter_manual.py`, verify `MAX_QUOTE` enforcement and flock recovery.
3. **Phase 3 (Signer & Execution)**: Add `soltui/jupiter_order.py` with `load_keypair` permission checks.
4. **Phase 4 (TUI Integration)**: Update `#advanced-venue` in `soltui/tui.py`, wire dynamic dispatch and test in Textual test harness.
