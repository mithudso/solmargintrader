"""Durable GUM position changes; an accepted action is never treated as a fill."""

from __future__ import annotations

import hashlib
import json
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .gum_orders import GumAmbiguous, GumError
from .webhook_orders import _update, database, recover_planning

__all__ = ["client_order_id", "process_one", "recover_planning"]

VENUE = "jupiter-gum"
PRODUCT = "ZEC-PERP"


def client_order_id(binding: str, event_id: str, leg: int) -> str:
    """A separate nonzero u64 correlation id for every committed leg."""
    digest = hashlib.sha256(
        f"soloracle:{VENUE}:{binding}:{event_id}:{leg}".encode()
    ).digest()
    return str(int.from_bytes(digest[:8], "big") or 1)


def _decimal(value) -> Decimal:
    if not isinstance(value, str):
        raise TypeError("invalid_quantity")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid_quantity") from None
    if not number.is_finite() or number < 0:
        raise ValueError("invalid_quantity")
    return number


def _json(value) -> str:
    return json.dumps(value, allow_nan=False, separators=(",", ":"))


def _save(path, row, status, state, *, result=None, client_id=None):
    fields = {"plan": _json(state)}
    if result is not None:
        fields["result"] = _json(result)
        if result.get("order_id"):
            fields["order_id"] = result["order_id"]
    if client_id is not None:
        fields["client_order_id"] = client_id
    _update(path, row["event_id"], status, **fields)


def _refuse(path, row, state, reason, *, ambiguous=False):
    status = "unknown" if ambiguous else "refused"
    if ambiguous:
        state["phase"] = "halted"
    _save(path, row, status, state, result={"reason": reason})
    return status


def _identity(plan, row, venue):
    if not isinstance(plan, dict) or (
        plan.get("venue") != VENUE
        or plan.get("product_id") != PRODUCT
        or plan.get("account_id") != venue.account_id
        or plan.get("owner") != venue.owner
        or plan.get("subaccount_id") != venue.subaccount_id
        or plan.get("binding") != venue.binding
        or plan.get("target_side") != row["side"]
        or plan.get("side") != row["side"]
        or plan.get("action") not in ("open", "close", "noop")
        or plan.get("isolated") is not True
    ):
        raise ValueError("unverified_plan_identity")
    if plan["action"] != "noop" and (
        _decimal(plan.get("quantity")) <= 0
        or plan.get("reduce_only") is not (plan["action"] == "close")
    ):
        raise ValueError("unverified_plan_quantity")


def _acceptance(result, plan, client_id):
    if not isinstance(result, dict) or (
        result.get("client_order_id") != client_id
        or result.get("account_id") != plan["account_id"]
        or result.get("symbol") != "ZEC"
        or result.get("side") != plan["side"]
    ):
        raise ValueError("unverified_acceptance")
    return {
        "client_order_id": client_id,
        "account_id": plan["account_id"],
        "symbol": "ZEC",
        "side": plan["side"],
        "status": "accepted",
    }


def _receipt(result, plan, client_id):
    if not isinstance(result, dict) or (
        result.get("client_order_id") != client_id
        or result.get("account_id") != plan["account_id"]
        or result.get("owner") != plan["owner"]
        or result.get("subaccount_id") != plan["subaccount_id"]
        or result.get("symbol") != "ZEC"
        or result.get("side") != plan["side"]
        or result.get("reduce_only") is not plan["reduce_only"]
        or result.get("isolated") is not True
        or result.get("status") not in ("filled", "cancelled", "unknown", "pending")
        or _decimal(result.get("original_quantity")) != _decimal(plan["quantity"])
        or _decimal(result.get("filled_quantity")) > _decimal(plan["quantity"])
    ):
        raise ValueError("unverified_fill_identity")
    position = result.get("position")
    if not isinstance(position, dict) or (
        position.get("side") not in (None, "buy", "sell")
        or position.get("isolated") is not True
    ):
        raise ValueError("unverified_position")
    size = _decimal(position.get("size"))
    if (position["side"] is None) != (size == 0):
        raise ValueError("unverified_position")
    order_id = result.get("order_id")
    if not isinstance(order_id, str) or not order_id.isdigit():
        raise ValueError("unverified_order_id")
    transactions = result.get("transactions")
    if not isinstance(transactions, list):
        raise TypeError("unverified_transactions")
    trail = []
    for transaction in transactions:
        if (
            not isinstance(transaction, dict)
            or not isinstance(transaction.get("signature"), str)
            or not 1 <= len(transaction["signature"]) <= 256
            or transaction.get("type") not in ("submit", "fill", "cancel")
        ):
            raise ValueError("unverified_transactions")
        item = {"signature": transaction["signature"], "type": transaction["type"]}
        for key in ("price", "size", "fee"):
            if key in transaction:
                _decimal(transaction[key])
                item[key] = transaction[key]
        if "timestamp" in transaction:
            if (
                type(transaction["timestamp"]) is not int
                or transaction["timestamp"] <= 0
            ):
                raise ValueError("unverified_transaction_timestamp")
            item["timestamp"] = transaction["timestamp"]
        if "role" in transaction:
            if transaction["role"] not in ("maker", "taker"):
                raise ValueError("unverified_transaction_role")
            item["role"] = transaction["role"]
        trail.append(item)
    if result["status"] == "filled" and not any(
        transaction["type"] == "fill" for transaction in trail
    ):
        raise ValueError("missing_fill_transaction")
    economic = {}
    if "actual_fee_usdc" in result:
        _decimal(result["actual_fee_usdc"])
        economic["actual_fee_usdc"] = result["actual_fee_usdc"]
    return (
        {
            key: result[key]
            for key in (
                "client_order_id",
                "account_id",
                "owner",
                "subaccount_id",
                "symbol",
                "side",
                "reduce_only",
                "isolated",
                "status",
                "original_quantity",
                "filled_quantity",
                "position",
            )
        }
        | {
            "settled": result.get("settled") is True,
            "order_id": order_id,
            "transactions": trail,
        }
        | economic
    )


def _completed_close(state, row, venue):
    """Reopening also verifies the close proof stored before the restart."""
    if not isinstance(state.get("legs"), list) or len(state["legs"]) != 1:
        raise ValueError("missing_close_proof")
    leg = state["legs"][0]
    plan, client_id = leg["plan"], leg["client_order_id"]
    _identity(plan, row, venue)
    receipt = _receipt(leg["receipt"], plan, client_id)
    if (
        client_id != client_order_id(state["binding"], row["event_id"], 0)
        or plan["action"] != "close"
        or leg["state"] != "filled"
        or receipt["status"] != "filled"
        or _decimal(receipt["filled_quantity"]) != _decimal(plan["quantity"])
        or receipt["position"]["side"] is not None
        or _decimal(receipt["position"]["size"]) != 0
        or not receipt["settled"]
    ):
        raise ValueError("missing_close_proof")


def _prepare(path, row, venue, state, *, now, started, enabled):
    """No mutation has happened in this stage; a crash can safely refuse it."""
    after_close = state["phase"] == "ready_to_open"
    try:
        plan = venue.plan(row["symbol"], row["side"], venue.account_id)
        _identity(plan, row, venue)
        if after_close and plan["action"] != "open":
            return _refuse(
                path, row, state, "position_changed_after_close", ambiguous=True
            )
        if not enabled():
            return _refuse(path, row, state, "disarmed_before_submission")
        if now + time.monotonic() - started - row["timestamp"] > 300:
            _save(path, row, "expired", state, result={"reason": "signal_expired"})
            return "expired"
        if row["mode"] != "live":
            state["preview"] = plan
            state["phase"] = "dry-run"
            _save(path, row, "dry-run", state)
            return "dry-run"
        if plan["action"] == "noop":
            state["preview"] = plan
            state["phase"] = "complete"
            _save(
                path,
                row,
                "complete",
                state,
                result={"reason": "target_position_already_held"},
            )
            return "complete"
        client_id = client_order_id(
            state["binding"], row["event_id"], len(state["legs"])
        )
        state["legs"].append(
            {"plan": plan, "client_order_id": client_id, "state": "submitting"}
        )
        state["phase"] = "awaiting_fill"
        # This exact leg and its id survive any exception or process death below.
        _save(path, row, "submitting", state, client_id=client_id)
    except (ValueError, RuntimeError, OSError, TypeError):
        return _refuse(path, row, state, "gum_plan_unavailable")

    if not enabled():
        return _refuse(path, row, state, "disarmed_before_submission")
    try:
        try:
            result = venue.submit_leg(
                plan, client_id, enabled=enabled, deadline=row["timestamp"] + 300
            )
        except GumAmbiguous:
            raise
        except GumError:
            # Only the adapter's documented, definitely-unsent refusal is safe
            # to terminate. Receipt validation and writes stay outside this catch.
            state["legs"][-1]["state"] = "refused"
            state["phase"] = "refused"
            return _refuse(path, row, state, "gum_submission_preflight_refused")
        accepted = _acceptance(result, plan, client_id)
        state["legs"][-1]["state"] = "pending"
        _save(path, row, "pending", state, result=accepted)
        return "pending"
    except Exception:  # noqa: BLE001 - any post-commit failure is ambiguous
        _save(
            path,
            row,
            "unknown",
            state,
            result={"reason": "submission_requires_reconciliation"},
        )
        return "unknown"


def _resume(path, row, venue, state, *, now, started, enabled, allow_live):
    if state.get("phase") == "halted":
        return "blocked"
    if state.get("phase") == "ready_to_open":
        try:
            _completed_close(state, row, venue)
        except (ValueError, TypeError, KeyError):
            return _refuse(path, row, state, "close_proof_unavailable", ambiguous=True)
        if not allow_live or not enabled():
            return "disarmed"
        if now - row["timestamp"] > 300:
            _save(
                path,
                row,
                "expired",
                state,
                result={"reason": "signal_expired_after_close"},
            )
            return "expired"
        _save(path, row, "planning", state)
        return _prepare(
            path, row, venue, state, now=now, started=started, enabled=enabled
        )
    if state.get("phase") != "awaiting_fill" or not state.get("legs"):
        return "blocked"
    try:
        if not isinstance(state["legs"], list) or not isinstance(state["legs"][-1], dict):
            raise TypeError("invalid_durable_legs")
        leg = state["legs"][-1]
        plan, client_id = leg["plan"], leg["client_order_id"]
        _identity(plan, row, venue)
        if client_id != client_order_id(
            state["binding"], row["event_id"], len(state["legs"]) - 1
        ):
            raise ValueError("unverified_leg_id")
        receipt = _receipt(venue.reconcile(plan, client_id), plan, client_id)
        status = receipt["status"]
        if status == "filled":
            if _decimal(receipt["filled_quantity"]) != _decimal(plan["quantity"]):
                raise ValueError("partial_fill")
            position = receipt["position"]
            if plan["action"] == "close":
                if position["side"] is not None or _decimal(position["size"]) != 0:
                    raise ValueError("position_not_flat_after_close")
                if not receipt["settled"]:
                    # A fill can precede isolated collateral settling to its parent.
                    leg["receipt"] = receipt
                    _save(path, row, "pending", state, result=receipt)
                    return "pending"
                state["phase"] = "ready_to_open"
                next_status, answer = "pending", "closed"
            elif plan["action"] == "open":
                if position["side"] != row["side"] or _decimal(
                    position["size"]
                ) != _decimal(plan["quantity"]):
                    raise ValueError("position_does_not_match_fill")
                state["phase"] = "complete"
                next_status, answer = "complete", "complete"
            else:
                raise ValueError("unexpected_noop_leg")
        elif status == "cancelled":
            if _decimal(receipt["filled_quantity"]) != 0:
                raise ValueError("partial_fill_requires_review")
            state["phase"] = "cancelled"
            next_status, answer = "cancelled", "cancelled"
        else:
            next_status = answer = status
        leg["state"], leg["receipt"] = status, receipt
        _save(path, row, next_status, state, result=receipt)
        return answer
    except (ValueError, RuntimeError, OSError, TypeError, KeyError):
        # Polling remains read-only. A later complete venue receipt may resolve it.
        _save(
            path,
            row,
            "unknown",
            state,
            result={"reason": "fill_requires_reconciliation"},
        )
        return "unknown"


def process_one(
    path: Path,
    venue,
    portfolio_id: str,
    *,
    now=None,
    enabled=lambda: True,
    allow_live=False,
) -> str:
    """Run under the inbox owner lock; submit at most one committed GUM leg."""
    now = time.time() if now is None else now
    started = time.monotonic()
    try:
        binding = venue.binding
    except (ValueError, RuntimeError, TypeError):
        return "blocked"
    if not isinstance(binding, str) or not binding or portfolio_id != binding:
        return "blocked"
    with database(path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM signals WHERE status IN ('planning','submitting','unknown','pending') ORDER BY rowid LIMIT 1"
        ).fetchone()
        if row is not None:
            db.commit()
            # A different venue/account's durable state is never reinterpreted.
            if row["portfolio_id"] != binding or row["mode"] != "live":
                return "blocked"
            if row["status"] == "planning":
                return "blocked"
            try:
                state = json.loads(row["plan"])
            except (ValueError, TypeError):
                return "blocked"
            if (
                not isinstance(state, dict)
                or state.get("venue") != VENUE
                or state.get("binding") != binding
            ):
                return "blocked"
            return _resume(
                path,
                row,
                venue,
                state,
                now=now,
                started=started,
                enabled=enabled,
                allow_live=allow_live,
            )
        if not enabled():
            db.commit()
            return "disarmed"
        row = db.execute(
            "SELECT * FROM signals WHERE status='queued' ORDER BY rowid LIMIT 1"
        ).fetchone()
        if row is None:
            db.commit()
            return "idle"
        if row["portfolio_id"] != binding:
            db.commit()
            return "blocked"
        if row["mode"] == "live" and not allow_live:
            db.commit()
            return "disarmed"
        if row["mode"] not in ("live", "dry-run"):
            db.commit()
            return "blocked"
        if not now - 300 <= row["timestamp"] <= now + 30:
            db.execute(
                "UPDATE signals SET status='expired' WHERE event_id=?",
                (row["event_id"],),
            )
            db.commit()
            return "expired"
        db.execute(
            "UPDATE signals SET status='planning' WHERE event_id=?", (row["event_id"],)
        )
        db.commit()
    state = {
        "version": 1,
        "venue": VENUE,
        "binding": binding,
        "phase": "planning",
        "legs": [],
    }
    return _prepare(path, row, venue, state, now=now, started=started, enabled=enabled)
