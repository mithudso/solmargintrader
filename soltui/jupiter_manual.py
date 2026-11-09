"""Unsigned Jupiter Swap API v2 previews with structural checks and disk locking.

Enforces the $100 input-value cap using positive independent USD valuation.
Submission is unavailable until the exact V2 transaction has independent economic verification.
Historical ambiguous submissions remain blocked until chain evidence resolves them.
"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

# Ensure executor is importable
try:
    from executor import txverify
    from executor.signer import load_keypair
except ImportError:
    _repo_root = Path(__file__).resolve().parents[1]
    _executor_src = _repo_root / "executor" / "src"
    if _executor_src.is_dir() and str(_executor_src) not in sys.path:
        sys.path.insert(0, str(_executor_src))
    from executor import txverify
    from executor.signer import load_keypair

from . import jupiter_tokens

MAX_QUOTE = Decimal("100")  # Hard per-order cap in USD / USDC
SUBMISSION_UNAVAILABLE = "Jupiter Swap v2 submission is unavailable without independent economic verification"
PREVIEW_SECONDS = 45
DEFAULT_SLIPPAGE_BPS = 50
MAX_PRIORITY_FEE_LAMPORTS = 50_000
MIN_SOL_RESERVE_LAMPORTS = 5_000_000

WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
STABLE_MINTS = {USDC_MINT, USDT_MINT}

DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
JUPITER_PROD_URL = "https://api.jup.ag"
JUPITER_LITE_URL = "https://lite-api.jup.ag"

TERMINAL = {"FILLED", "CANCELLED", "CANCELED", "EXPIRED", "FAILED", "REJECTED"}


def _decimal(value: Any, name: str, *, allow_zero: bool = False) -> Decimal:
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be a finite number") from None
    if not x.is_finite() or x < 0 or (not allow_zero and x == 0):
        raise ValueError(f"{name} must be a finite positive number")
    return x


def _storage_dir() -> Path:
    base = os.environ.get("SOLMARGINTRADER_STORAGE")
    path = Path(base).expanduser() if base else Path.home() / ".config" / "solmargintrader"
    return path / "manual-jupiter-orders"


def _preview_path(preview_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", preview_id):
        raise ValueError("Invalid preview ID")
    return _storage_dir() / f"{preview_id}.json"


@contextmanager
def _lock():
    d = _storage_dir()
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(d / ".jupiter.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError("Invalid Jupiter order record")
    return value


def _save(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp." + uuid.uuid4().hex[:8])
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _has_unresolved() -> bool:
    if not _storage_dir().is_dir():
        return False
    for p in _storage_dir().glob("*.json"):
        if p.name.startswith("."):
            continue
        try:
            r = _read(p)
            if r.get("state") in ("submitting", "unknown", "pending"):
                return True
        except Exception:
            return True
    return False


def _block_unresolved() -> None:
    if _has_unresolved():
        raise ValueError("A previous Jupiter order is unresolved. Reconcile onchain status before ordering.")


def state() -> dict[str, Any]:
    """Expose unresolved intent after restart without exposing secret key material."""
    pending = []
    if _storage_dir().is_dir():
        for p in _storage_dir().glob("*.json"):
            if p.name.startswith("."):
                continue
            try:
                r = _read(p)
                if r.get("state") in ("submitting", "unknown", "pending"):
                    pending.append({k: r.get(k) for k in (
                        "preview_id", "product_id", "side", "state", "signature", "submit_started_at"
                    )})
            except Exception:
                pass
    return {"unresolved": bool(pending), "orders": pending}


def _resolve_token(query: str, *, is_quote: bool = False) -> dict[str, Any]:
    q = query.strip()
    qu = q.upper()
    if qu in ("USDC", "USD"):
        return {"mint": USDC_MINT, "symbol": "USDC", "name": "USD Coin", "decimals": 6, "verified": True, "usdPrice": 1.0}
    if qu == "USDT":
        return {"mint": USDT_MINT, "symbol": "USDT", "name": "Tether USD", "decimals": 6, "verified": True, "usdPrice": 1.0}
    if qu in ("SOL", "WSOL"):
        return {"mint": WSOL_MINT, "symbol": "SOL", "name": "Wrapped SOL", "decimals": 9, "verified": True}

    res = jupiter_tokens.resolve(q)
    decimals = res.get("decimals")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not (0 <= decimals <= 18):
        raise ValueError(f"Token {q} does not have a verified integer decimal precision")
    if not res.get("verified"):
        raise ValueError(f"Token {q} is not verified by Jupiter")
    return res


def _usd_price(token: dict[str, Any]) -> Decimal:
    if token["mint"] in STABLE_MINTS:
        return Decimal(1)
    price = token.get("usdPrice")
    try:
        if isinstance(price, bool):
            raise ValueError
        return _decimal(price, "USD price")
    except ValueError:
        raise ValueError(f"Cannot value input or size base units without a verified price for {token['symbol']}") from None


def _get_rpc_account_info(rpc_url: str, pubkey: str, http_call: Callable[..., Any] | None = None) -> dict[str, Any] | None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [pubkey, {"encoding": "base64", "commitment": "confirmed"}]
    }
    if http_call:
        res = http_call(rpc_url, payload)
    else:
        req = urllib.request.Request(rpc_url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            res = json.loads(resp.read().decode("utf-8"))
    val = (res or {}).get("result", {}).get("value")
    return val if isinstance(val, dict) else None


def _get_solana_balance(rpc_url: str, owner: str, mint: str, http_call: Callable[..., Any] | None = None) -> int:
    """Returns balance in base units (lamports for SOL, raw token units for SPL)."""
    if mint == WSOL_MINT:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [owner, {"commitment": "confirmed"}]}
        if http_call:
            res = http_call(rpc_url, payload)
        else:
            req = urllib.request.Request(rpc_url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
        val = (res or {}).get("result", {}).get("value")
        return int(val or 0)
    else:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [owner, {"mint": mint}, {"encoding": "jsonParsed", "commitment": "confirmed"}]
        }
        if http_call:
            res = http_call(rpc_url, payload)
        else:
            req = urllib.request.Request(rpc_url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
        total = 0
        for item in (res or {}).get("result", {}).get("value", []):
            info = (((item.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
            amt_str = (info.get("tokenAmount") or {}).get("amount")
            if amt_str and amt_str.isdigit():
                total += int(amt_str)
        return total


def _resolve_lut_tables(rpc_url: str, table_keys: list[str], http_call: Callable[..., Any] | None = None) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    if not table_keys:
        return tables
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [table_keys, {"encoding": "base64", "commitment": "confirmed"}]
    }
    if http_call:
        res = http_call(rpc_url, payload)
    else:
        req = urllib.request.Request(rpc_url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            res = json.loads(resp.read().decode("utf-8"))
    values = (res or {}).get("result", {}).get("value", [])
    for k, val in zip(table_keys, values, strict=False):
        if val and isinstance(val.get("data"), list) and val["data"]:
            raw_data = base64.b64decode(val["data"][0])
            tables[k] = txverify.lookup_table_addresses(raw_data)
    return tables


def order_preview(params: dict[str, Any], taker_pubkey: str,
                  *, rpc_url: str | None = None, api_key: str | None = None,
                  http_client: Any = None) -> dict[str, Any]:
    taker_pubkey = taker_pubkey.strip()
    if not taker_pubkey or not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", taker_pubkey):
        raise ValueError("A valid Solana wallet address is required")

    rpc = rpc_url or os.environ.get("SOLANA_RPC_URL", DEFAULT_RPC)
    api_key = api_key or os.environ.get("JUPITER_API_KEY", "").strip() or None
    base_api = JUPITER_PROD_URL if api_key else JUPITER_LITE_URL

    with _lock():
        _block_unresolved()

        product = str(params.get("product_id") or "").strip()
        side = str(params.get("side") or "").strip().upper()
        size_str = str(params.get("size") or "").strip()
        unit = str(params.get("size_currency") or "auto").strip().lower()

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        if "-" in product:
            base_sym, quote_sym = product.split("-", 1)
        else:
            base_sym, quote_sym = product, "USDC"

        base_tok = _resolve_token(base_sym)
        quote_tok = _resolve_token(quote_sym, is_quote=True)

        if base_tok["mint"] == quote_tok["mint"]:
            raise ValueError("Base and quote tokens must have distinct mints")

        if unit == "auto":
            unit = "quote" if side == "BUY" else "base"
        if (side, unit) not in (("BUY", "quote"), ("BUY", "base"), ("SELL", "base")):
            raise ValueError("Market BUY accepts quote or coin units; SELL accepts coin units")

        amount_dec = _decimal(size_str, "Order size")

        # Atomic decimal conversions
        if side == "BUY":
            in_tok, out_tok = quote_tok, base_tok
            if unit == "quote":
                in_amount_dec = amount_dec
                in_amount_raw = int(in_amount_dec * (Decimal(10) ** in_tok["decimals"]))
            else:
                in_amount_dec = amount_dec * _usd_price(base_tok) / _usd_price(quote_tok)
                in_amount_raw = int(in_amount_dec * (Decimal(10) ** in_tok["decimals"]))
        else:
            in_tok, out_tok = base_tok, quote_tok
            in_amount_dec = amount_dec
            in_amount_raw = int(in_amount_dec * (Decimal(10) ** in_tok["decimals"]))

        if in_amount_raw <= 0:
            raise ValueError("Calculated input amount must be positive")

        # Price the actual rounded input, independently of Jupiter's quoted output.
        input_price = _usd_price(in_tok)
        est_usd = Decimal(in_amount_raw) / (Decimal(10) ** in_tok["decimals"]) * input_price
        if est_usd > MAX_QUOTE:
            raise ValueError(f"Order value ${est_usd:.2f} exceeds the ${MAX_QUOTE:.2f} limit")

        # Balance check
        sol_balance = _get_solana_balance(rpc, taker_pubkey, WSOL_MINT, http_call=getattr(http_client, "rpc", None))
        if sol_balance < MIN_SOL_RESERVE_LAMPORTS:
            raise ValueError(f"Insufficient SOL balance for rent and fee reserve (available: {Decimal(sol_balance) / 10**9:.4f} SOL, required: {Decimal(MIN_SOL_RESERVE_LAMPORTS) / 10**9:.4f} SOL)")

        if in_tok["mint"] == WSOL_MINT:
            if sol_balance < in_amount_raw + MIN_SOL_RESERVE_LAMPORTS:
                raise ValueError(f"Insufficient SOL balance (available: {Decimal(sol_balance) / 10**9:.4f} SOL, required: {Decimal(in_amount_raw + MIN_SOL_RESERVE_LAMPORTS) / 10**9:.4f} SOL)")
        else:
            token_balance = _get_solana_balance(rpc, taker_pubkey, in_tok["mint"], http_call=getattr(http_client, "rpc", None))
            if token_balance < in_amount_raw:
                avail_ui = Decimal(token_balance) / (Decimal(10) ** in_tok["decimals"])
                needed_ui = Decimal(in_amount_raw) / (Decimal(10) ** in_tok["decimals"])
                raise ValueError(f"Insufficient {in_tok['symbol']} balance (available: {avail_ui}, required: {needed_ui})")

        # Fetch quote & transaction from Jupiter Swap v2 /order
        slippage_bps = int(params.get("slippage_bps") or DEFAULT_SLIPPAGE_BPS)
        query_params = {
            "inputMint": in_tok["mint"],
            "outputMint": out_tok["mint"],
            "amount": str(in_amount_raw),
            "taker": taker_pubkey,
            "slippageBps": str(slippage_bps),
        }
        url = f"{base_api}/swap/v2/order?{urllib.parse.urlencode(query_params)}"
        if http_client and hasattr(http_client, "get"):
            quote_data = http_client.get(url, params=query_params)
        else:
            req = urllib.request.Request(url, headers={"Accept": "application/json", **({"x-api-key": api_key} if api_key else {})})
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                quote_data = json.loads(resp.read().decode("utf-8"))

        if not isinstance(quote_data, dict) or not quote_data.get("transaction"):
            raise ValueError("Jupiter returned an invalid quote/order response")

        tx_b64 = str(quote_data["transaction"])
        tx = txverify.decode_b64(tx_b64)

        # Resolve lookup tables if present
        table_keys = [str(lk.account_key) for lk in getattr(tx.message, "address_table_lookups", []) or []]
        tables = _resolve_lut_tables(rpc, table_keys, http_call=getattr(http_client, "rpc", None))

        out_amount_raw = int(quote_data["outAmount"])
        out_amount_dec = Decimal(out_amount_raw) / (Decimal(10) ** out_tok["decimals"])
        min_out_raw = int(quote_data.get("otherAmountThreshold") or out_amount_raw)

        # Structural checks do not establish amounts, owner deltas, or reserve economics.
        exp = txverify.Expectation(
            owner=taker_pubkey,
            mint_in=in_tok["mint"],
            mint_out=out_tok["mint"],
            amount_in=in_amount_raw,
            min_out=min_out_raw,
            max_priority_fee_lamports=MAX_PRIORITY_FEE_LAMPORTS,
            min_sol_reserve_lamports=MIN_SOL_RESERVE_LAMPORTS,
        )
        facts = txverify.inspect_tx(tx, tables=tables)
        problems, info = txverify.check_static(facts, exp)
        if problems:
            raise ValueError("Transaction failed structural safety verification: " + "; ".join(problems))

        preview_id = uuid.uuid4().hex
        now = time.time()
        expires_at = now + PREVIEW_SECONDS

        record = {
            "preview_id": preview_id,
            "venue": "jupiter",
            "product_id": f"{base_tok['symbol']}-{quote_tok['symbol']}",
            "side": side,
            "size": str(amount_dec),
            "size_currency": unit,
            "in_token": in_tok,
            "out_token": out_tok,
            "in_amount_raw": in_amount_raw,
            "out_amount_raw": out_amount_raw,
            "min_out_raw": min_out_raw,
            "price_impact_pct": str(quote_data.get("priceImpactPct", "0")),
            "request_id": str(quote_data.get("requestId", "")),
            "transaction_b64": tx_b64,
            "taker": taker_pubkey,
            "created_at": now,
            "expires_at": expires_at,
            "state": "preview",
            "verification": "structural_only",
            "info": info,
        }
        _save(_preview_path(preview_id), record)

        return {
            "preview_id": preview_id,
            "venue": "jupiter",
            "product_id": f"{base_tok['symbol']}-{quote_tok['symbol']}",
            "side": side,
            "size": str(amount_dec),
            "size_currency": unit,
            "expires_at": expires_at,
            "estimate": {
                "in_amount": f"{Decimal(in_amount_raw) / (Decimal(10) ** in_tok['decimals']):g} {in_tok['symbol']}",
                "out_amount": f"{out_amount_dec:g} {out_tok['symbol']}",
                "price_impact_pct": f"{float(quote_data.get('priceImpactPct', 0))*100:.3f}%" if quote_data.get("priceImpactPct") is not None else "0.000%",
                "fee_lamports": info.get("fee_lamports", 5000),
                "route_plan": [
                    leg.get("swapInfo", {}).get("label") or "AMM"
                    for leg in quote_data.get("routePlan", []) if isinstance(leg, dict)
                ],
            },
            "submission_available": False,
            "notice": "Unsigned Jupiter Swap v2 preview; structural checks only. Submission unavailable without independent economic verification. Preview expires in 45s.",
        }


def order_submit(preview_id: str, keypair_path: str, expected_pubkey: str,
                 *, api_key: str | None = None, http_client: Any = None) -> dict[str, Any]:
    # No independent V2 economic verifier exists here. Refuse before key loading,
    # signing, network access, or modifying an unsigned preview or historical intent.
    raise ValueError(SUBMISSION_UNAVAILABLE)


def order_reconcile(preview_id_or_sig: str, *, rpc_url: str | None = None, http_client: Any = None) -> dict[str, Any]:
    identifier = preview_id_or_sig.strip()
    rpc = rpc_url or os.environ.get("SOLANA_RPC_URL", DEFAULT_RPC)

    with _lock():
        target_path: Path | None = None
        target_rec: dict[str, Any] | None = None

        if _storage_dir().is_dir():
            for p in _storage_dir().glob("*.json"):
                if p.name.startswith("."):
                    continue
                try:
                    r = _read(p)
                    if r.get("preview_id") == identifier or r.get("signature") == identifier:
                        target_path = p
                        target_rec = r
                        break
                except Exception:
                    pass

        if not target_path or not target_rec:
            raise ValueError(f"No order found matching '{identifier}'")

        sig = target_rec.get("signature")
        if sig:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[sig], {"searchTransactionHistory": True}]
            }
            if http_client and hasattr(http_client, "rpc"):
                res = http_client.rpc(rpc, payload)
            else:
                req = urllib.request.Request(rpc, data=json.dumps(payload).encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))

            statuses = (res or {}).get("result", {}).get("value", [])
            if statuses and statuses[0]:
                st = statuses[0]
                conf = st.get("confirmationStatus")
                err = st.get("err")
                if err:
                    target_rec["state"] = "failed"
                    target_rec["status"] = "FAILED"
                    target_rec["onchain_error"] = err
                elif conf in ("confirmed", "finalized"):
                    target_rec["state"] = "complete"
                    target_rec["status"] = "FILLED"
                _save(target_path, target_rec)
            # A missing status is not proof of failure or expiry. Old intents can
            # have landed outside this response, including records without a signature.

        return {
            "preview_id": target_rec.get("preview_id"),
            "signature": target_rec.get("signature"),
            "status": target_rec.get("status", target_rec.get("state")),
            "state": target_rec.get("state"),
            "unresolved": _has_unresolved(),
        }
