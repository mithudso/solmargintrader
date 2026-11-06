"""Durable public transaction intents. Unknown outcomes block another live runner.

The journal stores hashes and decoded intent metadata, never calldata, signed payloads or keys.
A receipt is retained until the caller applies its state/accounting effects idempotently.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from hexbytes import HexBytes
from web3 import Web3

from . import abi, addresses


class PendingSubmission(RuntimeError):
    """An earlier submission has no proven, durably accounted outcome."""


def _hex(value: bytes | str) -> str:
    return value if isinstance(value, str) else "0x" + bytes(value).hex()


def receipt_metadata(receipt: Any, tx_hash: str) -> dict[str, Any]:
    """Keep only public receipt evidence; do not serialize arbitrary RPC objects."""
    if _hex(receipt["transactionHash"]).lower() != tx_hash.lower():
        raise PendingSubmission("receipt hash does not match the submitted transaction")

    def integer(value):
        return int(value, 16) if isinstance(value, str) else int(value)

    status = integer(receipt["status"])
    block = integer(receipt["blockNumber"])
    gas = integer(receipt["gasUsed"])
    price = integer(receipt["effectiveGasPrice"])
    if status not in (0, 1) or block < 1 or gas < 1 or price < 0:
        raise PendingSubmission("receipt has invalid status, block or measured fee evidence")
    return {
        "transactionHash": tx_hash,
        "status": status,
        "blockNumber": block,
        "gasUsed": gas,
        "effectiveGasPrice": price,
        "l1Fee": integer(receipt.get("l1Fee", 0) or 0),
        "logs": [
            {"address": str(log["address"]), "topics": [_hex(t) for t in log["topics"]], "data": _hex(log["data"])}
            for log in receipt["logs"]
        ],
    }


def transaction_intent(tx: Any) -> dict[str, Any]:
    """Decode the minimal recovery metadata from a known transaction, without persisting calldata."""
    w3 = Web3()
    if tx.to.lower() == addresses.NONFUNGIBLE_POSITION_MANAGER.lower():
        contract = w3.eth.contract(abi=abi.NPM)
        fn, args = contract.decode_function_input(tx.data)
        if fn.fn_name == "mint":
            p = args["params"]
            return {
                "kind": "mint",
                "token0": p["token0"],
                "token1": p["token1"],
                "recipient": p["recipient"],
                "range": [p["tickLower"], p["tickUpper"]],
            }
        if fn.fn_name == "collect":
            return {"kind": "collect", "token_id": args["params"]["tokenId"]}
        if fn.fn_name == "increaseLiquidity":
            return {"kind": "increase", "token_id": args["params"]["tokenId"]}
        if fn.fn_name == "multicall" and tx.label.startswith("remove"):
            _, inner = contract.decode_function_input(args["data"][0])
            last, burn = contract.decode_function_input(args["data"][-1])
            token_id = inner["params"]["tokenId"]
            if last.fn_name != "burn" or burn["tokenId"] != token_id:
                raise PendingSubmission("remove intent does not prove a matching NFT burn")
            return {"kind": "remove", "token_id": token_id}
        if fn.fn_name == "approve":
            return {"kind": "approve"}
    if tx.label in ("gauge.withdraw", "gauge.deposit", "gauge.claimEmissions"):
        fn, args = w3.eth.contract(abi=abi.CL_GAUGE).decode_function_input(tx.data)
        if fn.fn_name == "claimEmissions":
            return {"kind": "claim", "token_ids": list(args["_tokenIds"])}
        return {"kind": "unstake" if fn.fn_name == "withdraw" else "stake", "token_id": args["_lp"]}
    if tx.to.lower() == addresses.SWAP_ROUTER.lower():
        fn, args = w3.eth.contract(abi=abi.SWAP_ROUTER).decode_function_input(tx.data)
        if fn.fn_name == "exactInputSingle":
            return {"kind": "swap", "token_in": args["params"]["tokenIn"], "token_out": args["params"]["tokenOut"]}
        if fn.fn_name == "multicall":
            return {"kind": "gas_swap"}
    if tx.label == "weth.withdraw":
        return {"kind": "unwrap"}
    if tx.label.startswith("approve"):
        return {"kind": "approve"}
    raise PendingSubmission(f"cannot journal an unknown transaction intent: {tx.label}")


class SubmissionJournal:
    def __init__(self, path: Path, owner: str, *, ledger_path: Path | None = None):
        self.path, self.owner = Path(path), Web3.to_checksum_address(owner)
        self.ledger_path = Path(ledger_path).resolve() if ledger_path is not None else None

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "version": 1,
                "owner": self.owner,
                "transactions": {},
                "ledger_path": str(self.ledger_path or self.path.with_name("ledger.sqlite").resolve()),
            }
        doc = json.loads(self.path.read_text())
        if doc.get("version") != 1 or doc.get("owner", "").lower() != self.owner.lower():
            raise PendingSubmission("submission journal owner or version does not match")
        return doc

    @contextmanager
    def _edit(self) -> Iterator[dict[str, Any]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            doc = self._read()
            yield doc
            fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".submissions.")
            try:
                with os.fdopen(fd, "w") as output:
                    json.dump(doc, output)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, self.path)
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def acquire(self):
        """Hold the wallet's active-operation lock. The OS releases it if this process dies."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lease = self.path.with_suffix(self.path.suffix + ".active.lock").open("a")
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            lease.close()
            raise PendingSubmission("another live operation or reconciliation is still active") from error
        return lease

    def ledger_file(self) -> Path:
        return Path(self._read()["ledger_path"])

    def records(self) -> list[dict[str, Any]]:
        return list(self._read()["transactions"].values())

    def before_submit(self, tx_hash: str, nonce: int, tx: Any, group: str, pool: str | None, tokens: list[str]) -> None:
        intent = transaction_intent(tx)
        if intent.get("recipient", self.owner).lower() != self.owner.lower():
            raise PendingSubmission("transaction intent recipient is not the journal owner")
        with self._edit() as doc:
            if self.ledger_path is not None and Path(doc["ledger_path"]).resolve() != self.ledger_path:
                raise PendingSubmission("submission journal is bound to a different ledger")
            for record in doc["transactions"].values():
                if not record["processed"] and record["group"] != group:
                    raise PendingSubmission(
                        f"unresolved submitted outcome: {record['hash']}; reconcile before new writes"
                    )
            doc["transactions"][tx_hash] = {
                "hash": tx_hash,
                "nonce": nonce,
                "group": group,
                "owner": self.owner,
                "to": tx.to,
                "label": tx.label,
                "intent": intent,
                "pool": pool,
                "tokens": tokens,
                "receipt": None,
                "processed": False,
            }

    def receipt(self, tx_hash: str, receipt: Any) -> None:
        metadata = receipt_metadata(receipt, tx_hash)
        with self._edit() as doc:
            doc["transactions"][tx_hash]["receipt"] = metadata

    def reconcile(self, chain: Any, apply: Callable[[dict[str, Any], list[dict[str, Any]]], None]) -> None:
        if not any(not r["processed"] for r in self.records()):
            return
        with self.acquire():
            self._reconcile_locked(chain, apply)

    def _reconcile_locked(self, chain: Any, apply: Callable[[dict[str, Any], list[dict[str, Any]]], None]) -> None:
        records = self.records()
        pending = [r for r in records if not r["processed"]]
        # Resolve all hashes first. No account can be declared gone while a related mint remains uncertain.
        for record in pending:
            if record["receipt"] is None:
                try:
                    receipt = chain.w3.eth.get_transaction_receipt(HexBytes(record["hash"]))
                    if receipt is None:
                        raise PendingSubmission("receipt not available")
                    self.receipt(record["hash"], receipt)
                except Exception as error:
                    raise PendingSubmission(f"unresolved submitted outcome: {record['hash']}; {error}") from error
        records = self.records()
        for record in records:
            if record["processed"]:
                continue
            chain.min_block = max(getattr(chain, "min_block", None) or 0, record["receipt"]["blockNumber"])
            group = [r for r in records if r["group"] == record["group"]]
            apply(record, group)
            with self._edit() as doc:
                doc["transactions"][record["hash"]]["processed"] = True
