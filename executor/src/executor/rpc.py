"""Solana JSON-RPC client over the injectable HTTP seam.

Reads retry transport failures with bounded backoff. A submit is attempted once.
Uncorrelated or malformed submission evidence always requires reconciliation.
"""

from __future__ import annotations

import base64
import binascii
import itertools
import time
from typing import Any

from solders.pubkey import Pubkey

from .errors import RpcError, SendRejected
from .http import Http

READ_RETRIES = 2


def _envelope(resp: Any, request_id: int, method: str) -> dict[str, Any]:
    if (
        not isinstance(resp, dict)
        or resp.get("jsonrpc") != "2.0"
        or type(resp.get("id")) is not int
        or resp["id"] != request_id
        or (("result" in resp) == ("error" in resp))
    ):
        raise RpcError(f"RPC {method} returned malformed or uncorrelated evidence")
    return resp


def _uint(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise RpcError(f"RPC {label} is not a nonnegative integer")
    return value


def _values(result: Any, count: int, label: str) -> list[Any]:
    values = result.get("value") if isinstance(result, dict) else None
    if not isinstance(values, list) or len(values) != count:
        raise RpcError(f"RPC {label} returned the wrong result cardinality")
    return values


class Rpc:
    def __init__(self, url: str, http: Http, sleep=time.sleep):
        self.url = url
        self.http = http
        self._ids = itertools.count(1)
        self._sleep = sleep

    def call(self, method: str, params: list[Any], retries: int = READ_RETRIES) -> Any:
        body = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params}
        for attempt in range(retries + 1):
            try:
                resp = self.http.post_json(self.url, body)
            except RpcError:
                raise
            except Exception as exc:  # noqa: BLE001 - retry read transports only
                if attempt < retries:
                    self._sleep(0.5 * (attempt + 1))
                    continue
                # Transport exceptions can contain credential-bearing URLs.
                raise RpcError(f"RPC {method} transport failed ({type(exc).__name__})") from None
            resp = _envelope(resp, body["id"], method)
            if "error" in resp:
                raise RpcError(f"RPC {method} returned an error")
            return resp["result"]
        raise RpcError(f"RPC {method} exhausted its read attempts")

    def balance(self, address: str) -> int:
        res = self.call("getBalance", [address, {"commitment": "confirmed"}])
        return _uint(res.get("value") if isinstance(res, dict) else None, "balance")

    def accounts(self, addresses: list[str]) -> list[dict[str, Any] | None]:
        """Decode exactly one explicit account or absence for each requested key."""
        out: list[dict[str, Any] | None] = []
        for i in range(0, len(addresses), 100):
            chunk = addresses[i : i + 100]
            res = self.call("getMultipleAccounts", [chunk, {"encoding": "base64", "commitment": "confirmed"}])
            out.extend(_account(v) for v in _values(res, len(chunk), "accounts"))
        return out

    def block_height(self) -> int:
        return _uint(self.call("getBlockHeight", [{"commitment": "confirmed"}]), "block height")

    def signature_statuses(self, signatures: list[str]) -> list[dict[str, Any] | None]:
        res = self.call("getSignatureStatuses", [signatures, {"searchTransactionHistory": True}])
        values = _values(res, len(signatures), "signature statuses")
        for value in values:
            if value is None:
                continue
            if (
                not isinstance(value, dict)
                or "err" not in value
                or value.get("confirmationStatus") not in (None, "processed", "confirmed", "finalized")
                or (value["err"] is not None and not isinstance(value["err"], (dict, str)))
            ):
                raise RpcError("RPC returned a malformed signature status")
            for key in ("slot", "confirmations"):
                if key in value and value[key] is not None:
                    _uint(value[key], f"signature status {key}")
        return values

    def transaction(self, signature: str) -> dict[str, Any] | None:
        res = self.call(
            "getTransaction",
            [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0, "commitment": "confirmed"}],
        )
        if res is not None and not isinstance(res, dict):
            raise RpcError("RPC returned a malformed transaction")
        return res

    def simulate(self, tx_b64: str, watch: list[str], sig_verify: bool, replace_blockhash: bool) -> dict[str, Any]:
        cfg: dict[str, Any] = {
            "encoding": "base64",
            "commitment": "confirmed",
            "sigVerify": sig_verify,
            "replaceRecentBlockhash": replace_blockhash,
            "accounts": {"encoding": "base64", "addresses": watch},
        }
        res = self.call("simulateTransaction", [tx_b64, cfg])
        value = res.get("value") if isinstance(res, dict) else None
        if not isinstance(value, dict) or "err" not in value:
            raise RpcError("RPC returned a malformed simulation")
        if value["err"] is not None and not isinstance(value["err"], (dict, str)):
            raise RpcError("RPC returned a malformed simulation error")
        accounts = value.get("accounts")
        if accounts is None and value["err"] is not None:
            accounts = []  # Failed simulation is refused before account comparison.
        elif not isinstance(accounts, list) or len(accounts) != len(watch):
            raise RpcError("RPC simulation did not return all watched accounts")
        return {**value, "accounts": [_account(a) for a in accounts]}

    def send_transaction(self, tx_b64: str) -> str:
        """Single attempt. Only a correlated preflight rejection is definite."""
        body = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": "sendTransaction",
            "params": [
                tx_b64,
                {"encoding": "base64", "skipPreflight": False, "preflightCommitment": "confirmed", "maxRetries": 3},
            ],
        }
        resp = _envelope(self.http.post_json(self.url, body), body["id"], "sendTransaction")
        if "error" in resp:
            err = resp["error"]
            definite = (
                isinstance(err, dict)
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
        sig = resp["result"]
        if not isinstance(sig, str) or not sig:
            raise RpcError("sendTransaction returned no signature")
        return sig


def _account(v: Any) -> dict[str, Any] | None:
    if v is None:
        return None
    if not isinstance(v, dict):
        raise RpcError("RPC account is neither an object nor explicit absence")
    lamports = _uint(v.get("lamports"), "account lamports")
    owner = v.get("owner")
    try:
        if not isinstance(owner, str):
            raise ValueError("missing owner")
        Pubkey.from_string(owner)
    except ValueError:
        raise RpcError("RPC account has an invalid owner") from None
    data = v.get("data")
    if not isinstance(data, list) or len(data) != 2 or not isinstance(data[0], str) or data[1] != "base64":
        raise RpcError("RPC account has an invalid base64 envelope")
    try:
        raw = base64.b64decode(data[0], validate=True)
    except (ValueError, binascii.Error):
        raise RpcError("RPC account has invalid base64 data") from None
    return {"lamports": lamports, "owner": owner, "data": raw}
