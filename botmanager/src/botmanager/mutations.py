"""Serialized saved-spec mutations and attributable, replay-only receipts."""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import time
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID, uuid4

from .domain import BotSpec, ManagerError, canonical, fingerprint, utc_now

MAX_MUTATIONS = 100000


def request_identity(request_id=None, expected_revision=None):
    request_id = str(uuid4()) if request_id is None else request_id
    try:
        if str(UUID(request_id)) != request_id or (
            expected_revision is not None
            and (type(expected_revision) is not int or expected_revision < 1)
        ):
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise ManagerError(
            "invalid_input", "A canonical UUID and positive revision are required."
        ) from exc
    return request_id


def check_revision(spec, expected_revision):
    if expected_revision is not None and spec.config_revision != expected_revision:
        raise ManagerError(
            "stale_revision",
            "The saved revision changed; inspect it before submitting a new request.",
        )


@contextmanager
def mutation_lock(home):
    """Hold across both journals; stops never require this lock or its quota."""
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(home / "mutation.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise ManagerError(
                "store_unavailable", "Mutation lock ownership or mode is invalid.", 4
            )
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ManagerError(
                        "store_unavailable",
                        "Another configuration mutation is still in progress.",
                        4,
                    ) from None
                time.sleep(0.01)
        yield
    finally:
        os.close(fd)


def request_body(operation, bot_id, changes, expected_revision, request_id):
    return {
        "schema_version": 1,
        "operation": operation,
        "bot_id": bot_id,
        "changes": changes,
        "expected_revision": expected_revision,
        "request_id": request_id,
    }


def mutation_result(
    request,
    before,
    after,
    *,
    active_runtime_id=None,
    prior_runtime_id=None,
    owner_generation=None,
    input_snapshot_hash=None,
    reason,
    changed,
):
    receipt = {
        **request,
        "accepted_at": utc_now(),
        "actor": "local_user",
        "actor_uid": os.getuid(),
        "prior_revision": before.config_revision,
        "prior_hash": before.config_hash,
        "accepted_revision": after.config_revision,
        "accepted_hash": after.config_hash,
        "active_runtime_id": active_runtime_id,
        "prior_runtime_id": prior_runtime_id,
        "owner_generation": owner_generation,
        "input_snapshot_hash": input_snapshot_hash,
        "outcome": "acknowledged" if changed else "skipped",
        "reason": reason,
        "safe_to_retry": False,
    }
    return {"spec": after.to_dict(), "receipt": receipt}


def save_mutation(db, table, request, result):
    # The table name is a code constant, never a command argument.
    if db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] >= MAX_MUTATIONS:
        raise ManagerError(
            "resource_limit", "Configuration request capacity is exhausted.", 3
        )
    acceptance = dict(result["receipt"])
    body = {"request": request, "result": result, "acceptance": acceptance}
    db.execute(
        f"INSERT INTO {table}(request_id,request,result,checksum,acceptance) VALUES (?,?,?,?,?)",
        (
            request["request_id"],
            canonical(request),
            canonical(result),
            fingerprint(body),
            canonical(acceptance),
        ),
    )


def validate_tables(db, tables):
    for table, columns in tables.items():
        if [
            row[1] for row in db.execute(f"PRAGMA table_info({table})")
        ] != columns.split():
            raise ManagerError(
                "incompatible_store",
                "Journal schema does not match its declared version.",
                4,
            )


def _validate_acceptance(receipt, request):
    expected = set(request) | {
        "accepted_at",
        "actor",
        "actor_uid",
        "prior_revision",
        "prior_hash",
        "accepted_revision",
        "accepted_hash",
        "active_runtime_id",
        "prior_runtime_id",
        "owner_generation",
        "input_snapshot_hash",
        "outcome",
        "reason",
        "safe_to_retry",
    }
    if (
        set(receipt) != expected
        or type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != 1
    ):
        raise ValueError
    for key in ("prior_revision", "accepted_revision"):
        if type(receipt[key]) is not int or receipt[key] < 1:
            raise ValueError
    for key in ("prior_hash", "accepted_hash"):
        if not isinstance(receipt[key], str) or not re.fullmatch(
            r"[0-9a-f]{64}", receipt[key]
        ):
            raise ValueError
    for key in ("active_runtime_id", "prior_runtime_id"):
        if receipt[key] is not None and str(UUID(receipt[key])) != receipt[key]:
            raise ValueError
    gen = receipt["owner_generation"]
    if gen is not None and (type(gen) is not int or gen < 0):
        raise ValueError
    if (receipt["active_runtime_id"] is None) != (gen is None):
        raise ValueError
    input_hash = receipt["input_snapshot_hash"]
    if receipt["active_runtime_id"] is None:
        if input_hash is not None:
            raise ValueError
    elif not isinstance(input_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", input_hash
    ):
        raise ValueError
    if (
        receipt["expected_revision"] is not None
        and receipt["expected_revision"] != receipt["prior_revision"]
    ):
        raise ValueError
    reason = receipt["reason"]
    if receipt["operation"] == "edit":
        changed = receipt["accepted_revision"] != receipt["prior_revision"]
        if (
            receipt["accepted_revision"] != receipt["prior_revision"] + int(changed)
            or receipt["prior_runtime_id"] is not None
        ):
            raise ValueError
        if reason != ("spec_revision_saved" if changed else "settings_already_pinned"):
            raise ValueError
    elif receipt["operation"] == "apply":
        changed = reason == "saved_revision_applied"
        if (
            reason
            not in (
                "saved_revision_applied",
                "revision_already_active",
                "draft_uses_saved_revision",
            )
            or receipt["accepted_revision"] != receipt["prior_revision"]
            or receipt["accepted_hash"] != receipt["prior_hash"]
        ):
            raise ValueError
        if (
            reason == "draft_uses_saved_revision"
            and receipt["active_runtime_id"] is not None
        ):
            raise ValueError
    else:
        raise ValueError
    if receipt["outcome"] != ("acknowledged" if changed else "skipped"):
        raise ValueError


def replay_mutation(row, request):
    """Validate row attribution independently of its checksum, then replay verbatim."""
    if row is None:
        return None
    try:
        saved = json.loads(row["request"])
        result = json.loads(row["result"])
        receipt = result["receipt"]
        acceptance = json.loads(row["acceptance"])
        spec = BotSpec.from_dict(result["spec"])
        _validate_acceptance(receipt, saved)
        if (
            set(result) != {"spec", "receipt"}
            or canonical(receipt) != canonical(acceptance)
            or set(saved) != set(request)
            or row["request_id"] != request["request_id"]
            or saved["request_id"] != row["request_id"]
            or canonical({key: receipt[key] for key in saved}) != canonical(saved)
            or spec.bot_id != saved["bot_id"]
            or receipt["accepted_revision"] != spec.config_revision
            or receipt["accepted_hash"] != spec.config_hash
            or receipt["safe_to_retry"] is not False
            or receipt["actor"] != "local_user"
            or type(receipt["actor_uid"]) is not int
            or receipt["actor_uid"] < 0
            or receipt["outcome"] not in ("acknowledged", "skipped")
            or datetime.fromisoformat(receipt["accepted_at"]).tzinfo is None
            or fingerprint(
                {"request": saved, "result": result, "acceptance": acceptance}
            )
            != row["checksum"]
        ):
            raise ValueError
        request_identity(saved["request_id"], saved["expected_revision"])
        if canonical(saved) != canonical(request):
            raise ManagerError(
                "identity_conflict",
                "Request UUID belongs to a different configuration mutation.",
            )
        return result
    except (ValueError, TypeError, KeyError, AttributeError, ManagerError) as exc:
        if isinstance(exc, ManagerError) and exc.code == "identity_conflict":
            raise
        raise ManagerError(
            "invalid_receipt", "Mutation receipt does not match its durable request.", 4
        ) from exc
