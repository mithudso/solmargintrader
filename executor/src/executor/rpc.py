"""Solana JSON-RPC client over the injectable HTTP seam.

Read calls retry (bounded, with backoff) because repeating a read is harmless. `send_transaction` NEVER retries:
a send that errors or times out has an unknown outcome, and the caller must journal it as such.
"""

from __future__ import annotations

import base64
import itertools
import time
from typing import Any

from .errors import RpcError, SendRejected
from .http import Http

READ_RETRIES = 2


class Rpc:
    def __init__(self, url: str, http: Http, sleep=time.sleep):
        self.url = url
        self.http = http
        self._ids = itertools.count(1)
        self._sleep = sleep

    def call(self, method: str, params: list[Any], retries: int = READ_RETRIES) -> Any:
        body = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params}
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self.http.post_json(self.url, body)
            except RpcError:
                raise
            except Exception as exc:  # noqa: BLE001 - transport errors are retryable for reads only
                last = exc
                if attempt < retries:
                    self._sleep(0.5 * (attempt + 1))
                    continue
                raise RpcError(f"RPC {method} failed: {exc}") from None
            if not isinstance(resp, dict):
                raise RpcError(f"RPC {method} returned a non-object")
            if resp.get("error"):
                err = resp["error"]
                msg = err.get("message") if isinstance(err, dict) else str(err)
                raise RpcError(f"RPC {method} error: {str(msg)[:300]}")
            if "result" not in resp:
                raise RpcError(f"RPC {method} returned no result")
            return resp["result"]
        raise RpcError(f"RPC {method} failed: {last}")

    # -- reads ---------------------------------------------------------------------------------------------

    def balance(self, address: str) -> int:
        res = self.call("getBalance", [address, {"commitment": "confirmed"}])
        return int(res["value"])

    def accounts(self, addresses: list[str]) -> list[dict[str, Any] | None]:
        """getMultipleAccounts (base64), chunked to the 100-key limit. Each entry: dict(lamports, owner, data) or None."""
        out: list[dict[str, Any] | None] = []
        for i in range(0, len(addresses), 100):
            res = self.call(
                "getMultipleAccounts", [addresses[i : i + 100], {"encoding": "base64", "commitment": "confirmed"}]
            )
            out.extend(_account(v) for v in res["value"])
        return out

    def block_height(self) -> int:
        return int(self.call("getBlockHeight", [{"commitment": "confirmed"}]))

    def signature_statuses(self, signatures: list[str]) -> list[dict[str, Any] | None]:
        res = self.call("getSignatureStatuses", [signatures, {"searchTransactionHistory": True}])
        return list(res["value"])

    def transaction(self, signature: str) -> dict[str, Any] | None:
        return self.call(
            "getTransaction",
            [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0, "commitment": "confirmed"}],
        )

    # -- simulate / send -----------------------------------------------------------------------------------

    def simulate(self, tx_b64: str, watch: list[str], sig_verify: bool, replace_blockhash: bool) -> dict[str, Any]:
        cfg: dict[str, Any] = {
            "encoding": "base64",
            "commitment": "confirmed",
            "sigVerify": sig_verify,
            "replaceRecentBlockhash": replace_blockhash,
            "accounts": {"encoding": "base64", "addresses": watch},
        }
        res = self.call("simulateTransaction", [tx_b64, cfg])
        value = res["value"]
        value["accounts"] = [_account(a) for a in value.get("accounts") or []]
        return value

    def send_transaction(self, tx_b64: str) -> str:
        """Single attempt. Any exception here means the outcome is unknown to the caller."""
        body = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": "sendTransaction",
            "params": [
                tx_b64,
                {"encoding": "base64", "skipPreflight": False, "preflightCommitment": "confirmed", "maxRetries": 3},
            ],
        }
        resp = self.http.post_json(self.url, body)  # deliberately not wrapped: the caller treats any raise as unknown
        if not isinstance(resp, dict):
            raise RpcError("sendTransaction returned a non-object")
        if "error" in resp:
            err = resp["error"]
            definite = (
                resp.get("jsonrpc") == "2.0"
                and resp.get("id") == body["id"]
                and "result" not in resp
                and isinstance(err, dict)
                and type(err.get("code")) is int
                and isinstance(err.get("message"), str)
                and err["code"] == -32002
                and isinstance(err.get("data"), dict)
                and isinstance(err["data"].get("err"), (str, dict))
                and bool(err["data"]["err"])
            )
            if definite:
                raise SendRejected("sendTransaction rejected by preflight simulation")
            raise RpcError("sendTransaction returned an ambiguous RPC error; reconciliation is required")
        sig = resp.get("result")
        if not isinstance(sig, str) or not sig:
            raise RpcError("sendTransaction returned no signature")
        return sig


def _account(v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    data = v.get("data")
    raw = base64.b64decode(data[0]) if isinstance(data, list) and data and isinstance(data[0], str) else b""
    return {"lamports": int(v.get("lamports", 0)), "owner": str(v.get("owner")), "data": raw}
