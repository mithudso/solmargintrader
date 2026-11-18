"""A close-only GUM consumer for a trusted signing host.

The host supplies authenticated, revocable mandates and position attestations
with a unique opening lineage. The host must use the same account lock for every
writer on this account. This module does not expose an approval or signing tool.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import stat
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .gum_orders import GumAmbiguous, GumError, GumOrders
from .gum_webhook_orders import (
    _acceptance,
    _decimal,
    _identity,
    _receipt,
    client_order_id,
)

_MANDATE_ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
_FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
_TERMINAL = {"closed", "refused", "cancelled"}
_CREATE_LEDGER = """CREATE TABLE zec_exits (
    mandate_id TEXT PRIMARY KEY, account_scope TEXT NOT NULL, binding TEXT NOT NULL,
    client_id TEXT NOT NULL UNIQUE, plan TEXT NOT NULL, status TEXT NOT NULL, result TEXT
)"""


@dataclass(frozen=True, kw_only=True)
class CloseMandate:
    """Owner-approved policy from the host's authenticated authority store."""

    mandate_id: str
    binding: str
    position_fingerprint: str
    position_side: str
    quantity: str
    expires_at: float
    max_data_age_seconds: float
    price_limit: str
    max_notional_usd: str
    max_taker_fee_bps: str
    max_slippage_bps: int


@dataclass(frozen=True, kw_only=True)
class PositionEvidence:
    """Fresh, host-verified evidence from the exclusive position owner."""

    binding: str
    fingerprint: str
    side: str
    quantity: str
    observed_at: float


def _private_ledger(path: Path, *, create=False) -> tuple[int, int]:
    parent = path.parent.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.geteuid()
        or stat.S_IMODE(parent.st_mode) != 0o700
    ):
        raise ValueError("zec_exit_ledger_parent_not_private")
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ValueError("zec_exit_ledger_not_private")
        return info.st_dev, info.st_ino
    finally:
        os.close(fd)


def initialize_exit_ledger(path: Path) -> None:
    """Provision once before admitting any mandates. Never replace a lost ledger."""
    path = Path(path)
    _private_ledger(path, create=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute(_CREATE_LEDGER)


def _result(status, reason, client_id=None, receipt=None):
    result = {"status": status, "reason": reason}
    if client_id is not None:
        result["client_order_id"] = client_id
    if receipt is not None:
        result["receipt"] = receipt
    return result


class ZecExitGuard:
    """Consume an authenticated mandate once, then use only reconciliation reads."""

    def __init__(
        self,
        ledger: Path,
        venue: GumOrders,
        *,
        lookup_mandate: Callable[[str], CloseMandate | None],
        attest_position: Callable[[], PositionEvidence | None],
        owner_lock: Callable[[], AbstractContextManager],
        enabled: Callable[[], bool],
    ):
        if not all(
            callable(x) for x in (lookup_mandate, attest_position, owner_lock, enabled)
        ):
            raise TypeError("zec_exit_trusted_host_required")
        self.ledger = Path(ledger)
        self.venue = venue
        self.lookup_mandate = lookup_mandate
        self.attest_position = attest_position
        self.owner_lock = owner_lock
        self.enabled = enabled
        self._ledger_identity = _private_ledger(self.ledger)
        with self._database() as db:
            db.execute("SELECT mandate_id FROM zec_exits LIMIT 0")

    @contextmanager
    def _database(self):
        if _private_ledger(self.ledger) != self._ledger_identity:
            raise ValueError("zec_exit_ledger_identity_changed")
        with (
            closing(
                sqlite3.connect(self.ledger.absolute().as_uri() + "?mode=rw", uri=True)
            ) as db,
            db,
        ):
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            yield db

    def _record(self, mandate_id):
        with self._database() as db:
            return db.execute(
                "SELECT * FROM zec_exits WHERE mandate_id = ?", (mandate_id,)
            ).fetchone()

    def _consume(self, mandate, client_id, plan):
        account_scope = json.dumps(
            [self.venue.owner, self.venue.account_id, self.venue.subaccount_id]
        )
        with self._database() as db:
            db.execute("BEGIN IMMEDIATE")
            unresolved = db.execute(
                """SELECT 1 FROM zec_exits
                   WHERE account_scope = ? AND status NOT IN ('closed', 'refused', 'cancelled')
                   LIMIT 1""",
                (account_scope,),
            ).fetchone()
            if unresolved:
                return False
            return (
                db.execute(
                    """INSERT INTO zec_exits
                       (mandate_id, account_scope, binding, client_id, plan, status)
                   VALUES (?, ?, ?, ?, ?, 'submitting')
                   ON CONFLICT (mandate_id) DO NOTHING""",
                    (
                        mandate.mandate_id,
                        account_scope,
                        mandate.binding,
                        client_id,
                        json.dumps(plan, allow_nan=False),
                    ),
                ).rowcount
                == 1
            )

    def _save(self, mandate_id, status, reason, client_id, receipt=None):
        result = _result(status, reason, client_id, receipt)
        with self._database() as db:
            db.execute(
                "UPDATE zec_exits SET status = ?, result = ? WHERE mandate_id = ?",
                (status, json.dumps(result, allow_nan=False), mandate_id),
            )
        return result

    @staticmethod
    def _previous(row):
        if row["result"] is not None:
            return json.loads(row["result"])
        return _result(
            "unknown", "submission_requires_reconciliation", row["client_id"]
        )

    def _require_active(self, mandate_id, mandate=None):
        if self.enabled() is not True:
            raise ValueError("zec_exit_disarmed")
        current = self.lookup_mandate(mandate_id)
        if (
            not isinstance(current, CloseMandate)
            or current.mandate_id != mandate_id
            or current.binding != self.venue.binding
            or (mandate is not None and current != mandate)
            or not _FINGERPRINT.fullmatch(current.position_fingerprint)
            or current.position_side not in ("buy", "sell")
            or not math.isfinite(current.expires_at)
            or current.expires_at <= time.time()
            or not 0 < current.max_data_age_seconds <= 5
            or type(current.max_slippage_bps) is not int
            or not 0 <= current.max_slippage_bps <= 1000
            or min(
                _decimal(current.quantity),
                _decimal(current.price_limit),
                _decimal(current.max_notional_usd),
            )
            <= 0
        ):
            raise ValueError("zec_exit_mandate_inactive_or_invalid")
        _decimal(current.max_taker_fee_bps)
        evidence = self.attest_position()
        if (
            not isinstance(evidence, PositionEvidence)
            or evidence.binding != current.binding
            or evidence.fingerprint != current.position_fingerprint
            or evidence.side != current.position_side
            or _decimal(evidence.quantity) != _decimal(current.quantity)
            or not 0
            <= time.time() - evidence.observed_at
            <= current.max_data_age_seconds
            or current.expires_at <= time.time()
            or self.lookup_mandate(mandate_id) != current
            or self.enabled() is not True
        ):
            raise ValueError("zec_exit_position_changed_or_stale")
        return current

    def _check_plan(self, plan, side, mandate):
        _identity(plan, {"side": side}, self.venue)
        position = plan["position_before"]
        price = _decimal(plan["price_cap"])
        bound = _decimal(mandate.price_limit)
        now = time.time()
        age = now - plan["observed_at"]
        cached_age = _decimal(str(plan["market_last_updated_ms"])) / 1000
        if (
            plan["action"] != "close"
            or plan.get("symbol") != "ZEC"
            or type(plan.get("collateral_native")) is not int
            or plan["collateral_native"] != 0
            or position["side"] != mandate.position_side
            or position["isolated"] is not True
            or _decimal(position["size"]) != _decimal(mandate.quantity)
            or _decimal(plan["quantity"]) != _decimal(mandate.quantity)
            or price <= 0
            or (price > bound if side == "buy" else price < bound)
            or not 0
            < _decimal(plan["notional_cap"])
            <= _decimal(mandate.max_notional_usd)
            or _decimal(plan["taker_fee_bps"]) > _decimal(mandate.max_taker_fee_bps)
            or type(plan["max_slippage_bps"]) is not int
            or not 0 <= plan["max_slippage_bps"] <= mandate.max_slippage_bps
            or not 0 <= age <= mandate.max_data_age_seconds
            or type(plan["market_timestamp"]) is not int
            or abs(now - plan["market_timestamp"]) > mandate.max_data_age_seconds
            or age + float(cached_age) > mandate.max_data_age_seconds
        ):
            raise ValueError("zec_exit_plan_outside_mandate")

    def close(self, mandate_id: str) -> dict:
        """Attempt one full reduce-only close for a host-issued mandate ID."""
        if not isinstance(mandate_id, str) or not _MANDATE_ID.fullmatch(mandate_id):
            return _result("blocked", "invalid_mandate_id")
        with self.owner_lock():
            row = self._record(mandate_id)
            if row is not None:
                if row["binding"] != self.venue.binding:
                    return _result("blocked", "mandate_binding_mismatch")
                return self._previous(row)
            try:
                mandate = self._require_active(mandate_id)
                side = "sell" if mandate.position_side == "buy" else "buy"
                plan = self.venue.plan("ZEC", side, self.venue.account_id)
                self._check_plan(plan, side, mandate)
                self._require_active(mandate_id, mandate)
            except Exception:  # noqa: BLE001 - no submission has been attempted
                return _result("blocked", "close_preflight_refused")

            client_id = client_order_id(mandate.binding, f"zec-exit:{mandate_id}", 0)
            if not self._consume(mandate, client_id, plan):
                return _result("blocked", "mandate_consumed_or_prior_close_unresolved")

            def approve_fresh(fresh):
                try:
                    self._require_active(mandate_id, mandate)
                    self._check_plan(fresh, side, mandate)
                    # The persisted plan sets the maximum fee used in fill reconciliation.
                    return _decimal(fresh["taker_fee_bps"]) <= _decimal(
                        plan["taker_fee_bps"]
                    )
                except Exception:  # noqa: BLE001 - the signer guard must fail closed
                    return False

            try:
                if not approve_fresh(plan):
                    raise GumError("zec_exit_no_longer_authorized")
                accepted = self.venue.submit_leg(
                    plan,
                    client_id,
                    enabled=lambda: self.enabled() is True,
                    deadline=mandate.expires_at,
                    approve_fresh=approve_fresh,
                )
            except GumAmbiguous:
                return self._save(
                    mandate_id,
                    "unknown",
                    "submission_requires_reconciliation",
                    client_id,
                )
            except GumError:
                return self._save(
                    mandate_id, "refused", "close_definitely_unsent", client_id
                )
            except Exception:  # noqa: BLE001 - any other post-commit error is ambiguous
                return self._save(
                    mandate_id,
                    "unknown",
                    "submission_requires_reconciliation",
                    client_id,
                )
            try:
                _acceptance(accepted, plan, client_id)
            except (ValueError, KeyError, TypeError):
                return self._save(
                    mandate_id, "unknown", "unverified_acceptance", client_id
                )
            return self._save(
                mandate_id, "pending", "close_accepted_not_filled", client_id
            )

    def reconcile(self, mandate_id: str) -> dict:
        """Verify the committed close without executing or approving a new leg."""
        if not isinstance(mandate_id, str) or not _MANDATE_ID.fullmatch(mandate_id):
            return _result("blocked", "invalid_mandate_id")
        with self.owner_lock():
            row = self._record(mandate_id)
            if row is None or row["binding"] != self.venue.binding:
                return _result("blocked", "close_not_owned_or_not_committed")
            if row["status"] in _TERMINAL:
                return self._previous(row)
            client_id = row["client_id"]
            plan = json.loads(row["plan"])
            try:
                raw = self.venue.reconcile(plan, client_id)
                receipt = _receipt(raw, plan, client_id)
            except Exception:  # noqa: BLE001 - a missing or unverified receipt proves nothing
                return self._save(
                    mandate_id, "unknown", "unverified_close_outcome", client_id
                )
            filled = _decimal(receipt["filled_quantity"])
            quantity = _decimal(plan["quantity"])
            position = receipt["position"]
            if (
                receipt["status"] == "filled"
                and filled == quantity
                and position["side"] is None
            ):
                if receipt["settled"]:
                    return self._save(
                        mandate_id, "closed", "close_verified", client_id, receipt
                    )
                return self._save(
                    mandate_id,
                    "pending",
                    "close_awaiting_settlement",
                    client_id,
                    receipt,
                )
            if 0 < filled < quantity:
                return self._save(
                    mandate_id, "partial", "close_partially_filled", client_id, receipt
                )
            if (
                receipt["status"] == "cancelled"
                and filled == 0
                and position == plan["position_before"]
            ):
                return self._save(
                    mandate_id,
                    "cancelled",
                    "close_verified_unfilled",
                    client_id,
                    receipt,
                )
            return self._save(
                mandate_id, "unknown", "close_outcome_unresolved", client_id, receipt
            )
