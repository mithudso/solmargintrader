"""Bounded, read-only wallet history. CLI credentials and stderr stay outside replies.

The rail worker calls this module; a status poll never starts network requests.
Base uses the same configured CDP CLI as wallet discovery. Unsolicited token
contracts are neither called nor visited. Solana history has explicit address-
only coverage rather than claiming an exhaustive token-account index.
"""
from __future__ import annotations

import http.client
import json
import logging
import math
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable
from urllib.parse import urlsplit

from . import wallet

HASH = re.compile(r"0x[0-9a-fA-F]{64}\Z")
SIGNATURE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{80,96}\Z")
WINDOW_DAYS = 14
BUDGET_SECONDS = 15
logger = logging.getLogger(__name__)


def _observed(operation):
    """Observe fixed operation names without exposing addresses, URLs or payloads."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            logger.debug("wallet_history.request", extra={"operation": operation, "phase": "request"})
            try:
                result = function(*args, **kwargs)
            except Exception as exc:
                logger.warning("wallet_history.failure", extra={"operation": operation,
                    "phase": "failure", "error_kind": type(exc).__name__})
                raise
            logger.debug("wallet_history.success", extra={"operation": operation, "phase": "success"})
            return result
        return wrapped
    return decorate


def _timestamp(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value) if math.isfinite(value) and value > 0 else None
        except OverflowError:
            return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except (ValueError, OverflowError, OSError):
            pass
    return None


@_observed("cdp_history")
def _cdp_query(sql: str, timeout: float) -> list[dict]:
    executable = shutil.which("cdp") or next((p for p in (
        "/opt/homebrew/bin/cdp", "/usr/local/bin/cdp") if os.path.isfile(p) and os.access(p, os.X_OK)), None)
    if not executable:
        raise RuntimeError("CDP CLI unavailable")
    # SQL is generated below from validated public addresses and fixed columns.
    # Native hosts inherit Chrome's minimal PATH. CDP's shebang resolves node
    # with /usr/bin/env; its selected bin directory must be visible to the child.
    child_env = {**os.environ, "PATH": os.pathsep.join(dict.fromkeys([
        os.path.dirname(os.path.abspath(executable)), *os.get_exec_path()]))}
    result = subprocess.run([executable, "data", "query", "run", "sql=" + sql,
                             'cache:={"maxAgeMs":30000}'], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=timeout, check=False, env=child_env)
    if result.returncode:
        raise RuntimeError("CDP history unavailable")
    payload = json.loads(result.stdout)
    rows = payload.get("result")
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Invalid CDP history response")
    return rows


@_observed("solana_history")
def _rpc(method: str, params: list, timeout: float, *, stop=None) -> Any:
    if method not in {"getSignaturesForAddress", "getTransaction"}:
        raise ValueError("Wallet activity accepts only history reads")
    deadline = time.monotonic() + timeout

    def check():
        if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
            raise TimeoutError("Wallet activity read cancelled or expired")

    check()
    target = urlsplit(wallet.SOLANA_RPC)
    if target.scheme not in ("http", "https") or not target.hostname or target.username or target.password:
        raise ValueError("Solana history endpoint unavailable")
    constructor = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
    connection = constructor(target.hostname, target.port, timeout=timeout)
    response = None
    done = threading.Event()
    watcher = None
    try:
        connection.connect()
        transport = connection.sock

        def expire():
            while not done.wait(min(.02, max(0, deadline - time.monotonic()))):
                if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
                    try:
                        transport.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return

        watcher = threading.Thread(target=expire, name="wallet-history-deadline", daemon=True)
        watcher.start()
        check()
        path = target.path or "/"
        if target.query:
            path += "?" + target.query
        connection.request("POST", path, body=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                           headers={"Content-Type": "application/json", "User-Agent": "SolTUI-wallet-history/1"})
        response = connection.getresponse()
        data = bytearray()
        while len(data) <= 1_000_000:
            check()
            part = response.read1(1_000_001 - len(data))
            if not part:
                break
            data.extend(part)
        check()
        if response.status != 200:
            raise ValueError("Solana history unavailable")
        if len(data) > 1_000_000:
            raise ValueError("History response too large")
        payload = json.loads(data)
        if not isinstance(payload, dict) or payload.get("error") or "result" not in payload:
            raise ValueError("Solana history unavailable")
        return payload["result"]
    finally:
        done.set()
        if watcher is not None:
            watcher.join()
        if response is not None:
            response.close()
        connection.close()


def _base(address: str, limit: int, query: Callable, remaining: Callable) -> tuple[list, dict, list]:
    coverage = {"chain": "base", "source": "CDP indexed history", "window_days": WINDOW_DAYS,
                "complete": False, "limit": limit}
    if not wallet.valid_evm_address(address):
        return [], {**coverage, "state": "unavailable"}, ["Base wallet address is missing or invalid."]
    owner = address.lower()
    bound = f"timestamp >= now() - INTERVAL {WINDOW_DAYS} DAY"
    # ClickHouse substitutes aliases in WHERE: do not reuse a source-column
    # name for an aggregate alias (ILLEGAL_AGGREGATION).
    sql = ("SELECT transaction_hash, max(timestamp) AS occurred_at, any(from_address) AS sender, "
           "any(to_address) AS recipient, any(value) AS amount_raw, "
           "substring(any(input),1,10) AS method_selector, sum(action) AS chain_action "
           f"FROM base.transactions WHERE {bound} AND "
           f"(from_address='{owner}' OR to_address='{owner}') GROUP BY transaction_hash "
           "HAVING sum(action)>0 ORDER BY occurred_at DESC LIMIT 50")
    items, gaps = [], []
    trusted = {a.lower(): symbol for a, symbol, _ in wallet.KNOWN_BASE_TOKENS}
    touched = set(trusted)
    successful = 0
    try:
        rows = query(sql, remaining())
        successful += 1
        for row in rows:
            tx = row.get("transaction_hash")
            sender, recipient = row.get("sender", row.get("from_address")), row.get("recipient", row.get("to_address"))
            if not isinstance(tx, str) or not HASH.fullmatch(tx) or owner not in (sender, recipient):
                continue
            if isinstance(row.get("chain_action"), (int, float)) and row["chain_action"] <= 0:
                continue
            if sender == owner and isinstance(recipient, str) and wallet.valid_evm_address(recipient):
                touched.add(recipient.lower())
            direction = "Outgoing" if sender == owner else "Incoming"
            items.append({"id": "base:tx:" + tx.lower(), "at": _timestamp(row.get("occurred_at", row.get("timestamp"))),
                "mode": "wallet", "chain": "base", "kind": "transaction", "status": "indexed",
                "summary": f"{direction} Base transaction", "actor": sender, "counterparty": recipient,
                "url": "https://basescan.org/tx/" + tx, "source": coverage["source"]})
    except Exception:
        gaps.append("Base transaction history unavailable; check the configured CDP CLI/API access.")
    try:
        addresses = ",".join("'" + a + "'" for a in sorted(touched))
        sql = ("SELECT log_id, any(transaction_hash) AS tx_hash, max(block_timestamp) AS occurred_at, "
               "any(address) AS token_address, any(parameters['from']) AS sender, "
               "any(parameters['to']) AS recipient, sum(toInt8(action)) AS chain_action FROM base.events "
               f"WHERE block_timestamp >= now() - INTERVAL {WINDOW_DAYS} DAY "
               "AND event_signature='Transfer(address,address,uint256)' "
               f"AND address IN ({addresses}) AND "
               f"(parameters['from']='{owner}' OR parameters['to']='{owner}') "
               f"GROUP BY log_id HAVING sum(toInt8(action))>0 ORDER BY occurred_at DESC LIMIT {limit}")
        rows = query(sql, remaining())
        successful += 1
        for row in rows:
            tx = row.get("tx_hash", row.get("transaction_hash"))
            sender, recipient = row.get("sender", row.get("from_address")), row.get("recipient", row.get("to_address"))
            contract = row.get("token_address", row.get("address"))
            if (not isinstance(tx, str) or not HASH.fullmatch(tx) or owner not in (sender, recipient)
                    or not isinstance(contract, str) or contract.lower() not in touched
                    or not isinstance(row.get("log_id"), str)):
                continue
            if isinstance(row.get("chain_action"), (int, float)) and row["chain_action"] <= 0:
                continue
            direction = "Received" if recipient == owner else "Sent"
            items.append({"id": "base:log:" + row["log_id"], "at": _timestamp(row.get("occurred_at", row.get("timestamp"))),
                "mode": "wallet", "chain": "base", "kind": "token_transfer", "status": "indexed",
                "summary": f"{direction} {trusted.get(contract.lower(), 'token')} transfer", "actor": sender,
                "counterparty": recipient, "url": "https://basescan.org/tx/" + tx, "source": coverage["source"]})
    except Exception:
        gaps.append("Base token-transfer history unavailable; only independently available transactions are shown.")
    coverage.update(state="available" if successful == 2 else "partial" if successful else "unavailable",
        notes="Latest 14-day indexed transactions and transfers for trusted or owner-used contracts; unsolicited tokens filtered. Indexed does not establish execution success.")
    return items, coverage, gaps


def _solana(address: str, limit: int, rpc: Callable, remaining: Callable) -> tuple[list, dict, list]:
    coverage = {"chain": "solana", "source": "Solana finalized address history", "complete": False,
                "limit": limit, "notes": "Owner-address history; token-only account activity can be missing."}
    if not wallet.valid_solana_address(address):
        return [], {**coverage, "state": "unavailable"}, ["Solana wallet address is missing or invalid."]
    items, gaps = [], []
    try:
        rows = rpc("getSignaturesForAddress", [address, {"limit": limit, "commitment": "finalized"}], remaining())
        if not isinstance(rows, list):
            raise ValueError("Invalid signatures")
    except Exception:
        return [], {**coverage, "state": "unavailable"}, ["Solana history RPC unavailable or rate-limited."]
    for index, row in enumerate(rows[:limit]):
        if not isinstance(row, dict) or not isinstance(row.get("signature"), str) or not SIGNATURE.fullmatch(row["signature"]):
            continue
        signature = row["signature"]
        item = {"id": "solana:" + signature, "at": _timestamp(row.get("blockTime")), "mode": "wallet",
                "chain": "solana", "kind": "transaction", "status": "failed" if row.get("err") is not None else "finalized",
                "summary": "Solana transaction", "url": "https://solscan.io/tx/" + signature,
                "source": coverage["source"]}
        # Details are useful, but a missing detail must not erase a verified signature.
        if index < 3:
            try:
                tx = rpc("getTransaction", [signature, {"encoding": "jsonParsed", "commitment": "finalized",
                         "maxSupportedTransactionVersion": 0}], remaining())
                if not isinstance(tx, dict):
                    raise ValueError("Transaction details unavailable")
                keys = ((tx.get("transaction") or {}).get("message") or {}).get("accountKeys", [])
                signers = [k.get("pubkey") for k in keys if isinstance(k, dict) and k.get("signer")]
                item["actor"] = signers[0] if signers else None
                item["summary"] = "Signed Solana transaction" if address in signers else "Incoming / related Solana transaction"
                if (tx.get("meta") or {}).get("err") is not None:
                    item["status"] = "failed"
            except Exception:
                gaps.append("Some Solana transaction details are unavailable; signatures remain visible.")
        items.append(item)
    return items, {**coverage, "state": "partial" if gaps else "available"}, list(dict.fromkeys(gaps))


def snapshot(settings, *, limit: int = 8, query: Callable | None = None, rpc: Callable | None = None,
             stop: threading.Event | None = None) -> dict:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Activity limit must be an integer from 1 to 20")
    deadline = time.monotonic() + BUDGET_SECONDS

    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0 or (stop is not None and stop.is_set()):
            raise TimeoutError("Wallet activity read cancelled or expired")
        return min(5., seconds)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="wallet-history") as pool:
        base = pool.submit(_base, getattr(settings, "base_address", ""), limit, query or _cdp_query, remaining)
        sol = pool.submit(_solana, getattr(settings, "solana_address", ""), limit,
                          rpc or (lambda method, params, timeout: _rpc(method, params, timeout, stop=stop)), remaining)
        results = [base.result(), sol.result()]
    items = [item for rows, _, _ in results for item in rows]
    items = list({item["id"]: item for item in items}.values())
    items.sort(key=lambda item: item["at"] or 0, reverse=True)
    return {"items": items[:limit], "coverage": [coverage for _, coverage, _ in results],
            "gaps": list(dict.fromkeys(g for _, _, gaps in results for g in gaps)), "observed_at": time.time()}
