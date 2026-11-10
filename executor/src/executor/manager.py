"""Strict manager admission delegates signing to the existing executor pipeline.

Scoped certificates are read from executor-owned authority storage. A manager's
claims, paper balance or boolean cannot manufacture certification. This release
issues no certificates: current reference-only research remains unavailable.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from uuid import UUID

from .authority import STRATEGIES, WalletAuthority, digest, identity, positive
from .errors import Refused
from .tokens import USDC_MINT, WSOL_MINT, resolve, ui_to_raw

SCOPE_FIELDS = {
    "strategy",
    "strategy_version",
    "config_hash",
    "bot_id",
    "runtime_id",
    "generation",
    "revision",
    "mints",
    "timeframe",
    "execution_model",
    "cost_model",
    "data_model",
    "owner_identity",
    "authorization",
}
SWAP_FIELDS = {"from", "to", "amount", "live", "exit", "reason"}


def capabilities(engine):
    authority = WalletAuthority(engine.cfg, engine.root)
    return {
        **identity(engine.cfg),
        "canonical_strategies": sorted(STRATEGIES - {"path-validation"}),
        "manager_entry_strategies": ["momentum", "trend"],
        "manager_live_delegation": False,
        "registered": authority.policy_path.is_file(),
        "automatic_live_ready": False,
        "certificate_issuer": "unavailable: independently certified research and shadow receipts required",
        "unsupported": ["trigger", "swap-v2", "non-atomic-arbitrage", "path-validation-manager"],
        "accounting": "executor-average-cost; manager-FIFO-is-reporting-only",
    }


def validate(engine, request):
    if (
        not isinstance(request, dict)
        or set(request) != {"version", "request_id", "scope", "swap"}
        or type(request["version"]) is not int
        or request["version"] != 1
    ):
        raise Refused("unsupported manager executor request schema")
    try:
        if str(UUID(request["request_id"])) != request["request_id"]:
            raise ValueError
        scope, swap = request["scope"], request["swap"]
        if (
            not isinstance(scope, dict)
            or set(scope) != SCOPE_FIELDS
            or not isinstance(swap, dict)
            or set(swap) != SWAP_FIELDS
        ):
            raise ValueError
        for name in ("bot_id", "runtime_id"):
            if str(UUID(scope[name])) != scope[name]:
                raise ValueError
        for name in ("generation", "revision", "timeframe"):
            if type(scope[name]) is not int or scope[name] <= 0:
                raise ValueError
        if not re.fullmatch("[0-9a-f]{64}", scope["config_hash"]):
            raise ValueError
        if any(
            not isinstance(scope[key], str) or not scope[key].strip()
            for key in ("strategy", "strategy_version", "execution_model", "cost_model", "data_model")
        ):
            raise ValueError
        if (
            type(swap["live"]) is not bool
            or type(swap["exit"]) is not bool
            or not isinstance(swap["reason"], str)
            or not swap["reason"].strip()
        ):
            raise ValueError
        authorization = scope["authorization"]
        if (
            not isinstance(authorization, dict)
            or set(authorization)
            != {"mode", "armed", "desired", "observed", "input_state", "accounting_state", "entries_paused"}
            or type(authorization["armed"]) is not bool
            or type(authorization["entries_paused"]) is not bool
            or any(
                not isinstance(authorization[key], str) or not authorization[key]
                for key in ("mode", "desired", "observed", "input_state", "accounting_state")
            )
        ):
            raise ValueError
        tin, tout = resolve(swap["from"]), resolve(swap["to"])
        ui_to_raw(swap["amount"], tin.decimals)
        if scope["mints"] != [tin.mint, tout.mint] or set(scope["mints"]) != {USDC_MINT, WSOL_MINT}:
            raise ValueError
    except (TypeError, ValueError, AttributeError, KeyError):
        raise Refused("invalid exact manager intent scope or measurements") from None
    if swap["live"]:
        if authorization["mode"] != "live" or authorization["armed"] is not True:
            raise Refused("paper or disarmed manager authorization cannot submit live orders")
        if (
            authorization["desired"] != "running"
            or authorization["observed"] != "running"
            or authorization["entries_paused"] is True
            or authorization["input_state"] != "available"
            or authorization["accounting_state"] != "funded_wallet_reconciled"
        ):
            raise Refused("manager lifecycle, input or funded accounting is not live eligible")
        # The current manager protocol has no independently verifiable live
        # authorization issuer. Reject even forged 'eligible' client claims.
        raise Refused(
            "manager live authorization is unavailable; use explicit executor recovery policy for tracked exits"
        )
    if scope["strategy"] not in STRATEGIES - {"path-validation"}:
        raise Refused("unsupported manager strategy; canonical spot families only")
    if scope["owner_identity"] != identity(engine.cfg):
        raise Refused("executor installed source, wallet or configuration identity changed")
    if scope["cost_model"] != "measured-v1" or scope["data_model"] != "jupiter-measured-v1":
        raise Refused("uncertified reference or unsupported data/cost model")
    supported = {"trend": "sma-crossover-v1", "momentum": "ts-momentum-v1"}
    if not swap["exit"] and scope["strategy"] not in supported:
        raise Refused("Trigger/safety-order ladder execution is unsupported by atomic Jupiter Swap v1 admission")
    if not swap["exit"] and (
        scope["execution_model"] != "next_open" or scope["strategy_version"] != supported[scope["strategy"]]
    ):
        raise Refused("only versioned next-open strategy intents through atomic Jupiter Swap v1 are supported")
    return scope, swap


def admit(engine, request):
    scope, swap = validate(engine, request)
    authority = WalletAuthority(engine.cfg, engine.root)
    authority.check()
    authority.require_no_pending(request["request_id"])
    if swap["exit"]:
        # Existing rails establish tracked reduce-only quantity before signing.
        # Stops and research gates must never disable a legitimate tracked exit.
        return {"admitted": True, "exit_only": True, "request_digest": digest(request), "send_authorized": False}
    path = authority.root / "evidence" / (digest(scope) + ".json")
    try:
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        cert = json.loads(raw)
    except (OSError, ValueError):
        raise Refused("exact current research/shadow certification unavailable for this scope") from None
    required = {
        "version",
        "scope",
        "research",
        "shadow",
        "input_healthy",
        "accounting_healthy",
        "issued_at",
        "expires_at",
    }
    if (
        not isinstance(cert, dict)
        or set(cert) != required
        or type(cert["version"]) is not int
        or cert["version"] != 1
        or cert["scope"] != scope
    ):
        raise Refused("research/shadow certificate scope mismatch")
    now = time.time()
    issued = positive(cert["issued_at"], "certificate issuance")
    expiry = positive(cert["expires_at"], "certificate expiry")
    if not issued <= positive(now, "owner clock") < expiry or expiry - issued > 86400:
        raise Refused("research/shadow certificate stale or future-dated")
    for key in ("research", "shadow"):
        receipt = cert[key]
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"certified", "scope_digest", "receipt_digest"}
            or receipt["certified"] is not True
            or receipt["scope_digest"] != digest(scope)
            or not isinstance(receipt["receipt_digest"], str)
            or re.fullmatch("[0-9a-f]{64}", receipt["receipt_digest"]) is None
        ):
            raise Refused("uncertified or incompatible research/shadow evidence")
        # A digest in a certificate is not evidence by itself. Require the
        # immutable executor-owned receipt bytes and recheck their exact scope.
        receipt_path = authority.root / "evidence" / "receipts" / (receipt["receipt_digest"] + ".json")
        try:
            with receipt_path.open("rb") as stream:
                raw_receipt = stream.read(65537)
            if len(raw_receipt) > 65536 or hashlib.sha256(raw_receipt).hexdigest() != receipt["receipt_digest"]:
                raise ValueError
            artifact = json.loads(raw_receipt)
            expected = {
                "version": 1,
                "kind": key,
                "scope": scope,
                "certified": True,
                "production_eligible": True,
                "result": "pass",
            }
            if (
                artifact != expected
                or type(artifact.get("version")) is not int
                or artifact.get("certified") is not True
                or artifact.get("production_eligible") is not True
            ):
                raise ValueError
        except (OSError, ValueError, TypeError):
            raise Refused("bound certified research/shadow receipt artifact unavailable or changed") from None
    if cert["input_healthy"] is not True or cert["accounting_healthy"] is not True:
        raise Refused("input or accounting health unavailable")
    pending = [
        state
        for state in engine.journal.unresolved()
        if not (
            engine._caller_request == request["request_id"]
            and state.get("intent", {}).get("caller_request_id") == request["request_id"]
        )
    ]
    if pending:
        raise Refused("unresolved send blocks manager entry")
    if engine._kill_present():
        raise Refused("KILL blocks manager entry")
    return {
        "admitted": True,
        "request_digest": digest(request),
        "evidence_digest": digest(cert),
        "send_authorized": False,
    }


def execute(engine, request):
    scope, swap = validate(engine, request)
    # Engine binds the exact request under the shared writer lock before any
    # possible signing. Admission is repeated inside that same lock by callback.
    return engine.swap(
        swap["from"],
        swap["to"],
        swap["amount"],
        strategy=scope["strategy"],
        live=swap["live"],
        exit_only=swap["exit"],
        reason=swap["reason"],
        request_id=request["request_id"],
        caller_context=request,
        admission=lambda: admit(engine, request),
    )
