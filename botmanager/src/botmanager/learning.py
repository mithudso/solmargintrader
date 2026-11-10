"""Attributed learning projections and owner-authorized account transitions.

Wall clocks and canonical scope quotas belong to the registered research owner.
A normal loss is a label, never an instruction to edit a specification.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from .domain import BotSpec, ManagerError, fingerprint

TUNABLES = {
    "grid": frozenset({"range_pct", "rungs", "deadband_bps"}),
    "dca": frozenset({"take_profit_pct", "price_deviation_pct", "cooldown_bars"}),
    "trend": frozenset({"fast_period", "slow_period", "entry_buffer_bps"}),
    "momentum": frozenset({"window", "threshold"}),
}


def canonical_scope(spec, input_identity):
    return fingerprint(
        {
            "strategy": spec.strategy_id,
            "version": spec.strategy_version,
            "venue": spec.venue,
            "base": spec.base_mint,
            "quote": spec.quote_mint,
            "bar_seconds": spec.bar_seconds,
            "execution_model": spec.execution_model,
        }
    )


def comparable_identity(run):
    data = run["input"]
    identity = data["identity"]
    return fingerprint(
        {
            "source": identity.get("source"),
            "venue": identity.get("venue"),
            "currency": identity.get("quote_currency"),
            "bar_seconds": identity.get("bar_seconds"),
            "costs": identity.get("costs"),
            "engine": identity.get("engine_identity"),
            "policy": identity.get("policy_hash"),
        }
    )


def classify_outcome(outcome: Mapping):
    """Retain all cohorts; only resolved comparable forecasts/trades count."""
    kind = outcome.get("kind")
    if kind == "data_fault":
        cohort = "data_fault"
    elif kind == "execution_fault":
        cohort = "execution_fault"
    elif outcome.get("resolved") is not True:
        cohort = "unresolved"
    elif kind == "forecast":
        cohort = (
            "forecast_wrong"
            if outcome.get("correct") is False
            else "forecast_correct"
            if outcome.get("correct") is True
            else "unresolved"
        )
    elif kind == "trade":
        try:
            pnl = Decimal(str(outcome["net_pnl"]))
            if not pnl.is_finite():
                raise ValueError
            cohort = "trade_loss" if pnl < 0 else "trade_nonloss"
        except (KeyError, InvalidOperation, ValueError):
            cohort = "unresolved"
    else:
        cohort = "unresolved"
    eligible = (
        cohort in ("forecast_wrong", "forecast_correct", "trade_loss", "trade_nonloss")
        and outcome.get("comparable") is True
    )
    return {
        **dict(outcome),
        "cohort": cohort,
        "eligible": eligible,
        "completed_trade": eligible and kind == "trade",
    }


def outcome_summary(outcomes):
    labels = [classify_outcome(row) for row in outcomes]
    return {
        "outcomes": len(labels),
        "resolved_comparable_labels": sum(row["eligible"] for row in labels),
        "completed_trades": sum(row["completed_trade"] for row in labels),
        "cohorts": dict(Counter(row["cohort"] for row in labels)),
    }


def learned_spec(spec, changes, evidence_digest):
    if (
        not isinstance(changes, Mapping)
        or not changes
        or set(changes) - TUNABLES.get(spec.strategy_id, frozenset())
        or set(changes) & set(spec.user_overrides)
    ):
        raise ManagerError(
            "learning_blocked",
            "Learning may change only supported unpinned strategy tunables.",
            3,
        )
    raw = spec.to_dict()
    raw["config_revision"] += 1
    raw["resolved_values"].update(changes)
    for key in changes:
        raw["provenance"][key] = {
            "source": "context",
            "source_revision": "learned-" + evidence_digest,
            "reason": "owner_verified_learned_default;"
            + spec.shared_compatibility["reason"],
        }
    raw["config_hash"] = fingerprint({key: raw[key] for key in spec._config_body()})
    return BotSpec.from_dict(raw)


def runtime_outcomes(run):
    """One record per canonical completed exit, with its observed net economics."""
    cp = run.get("checkpoint") or {}
    labels = []
    for index, fill in enumerate(cp.get("fills", [])):
        side = fill.get("side")
        if side not in ("sell", "close"):
            continue
        pnl = fill.get("realized_pnl", fill.get("pnl_usd", fill.get("net_pnl")))
        labels.append(
            {
                "id": fingerprint([run["runtime_id"], index, fill]),
                "kind": "trade",
                "resolved": pnl is not None and fill.get("reason") != "final",
                "net_pnl": pnl,
                "comparable": True,
                "runtime_id": run["runtime_id"],
                "bot_id": run["bot_id"],
                "source": run["input"]["identity"],
                "event_ref": {"fill_index": index, "fill_hash": fingerprint(fill)},
            }
        )
    if cp.get("lots"):
        labels.append(
            {
                "id": fingerprint([run["runtime_id"], "residual", cp["lots"]]),
                "kind": "inventory",
                "resolved": False,
                "comparable": False,
                "runtime_id": run["runtime_id"],
                "bot_id": run["bot_id"],
                "source": run["input"]["identity"],
            }
        )
    prospective = run["input"].get("prospective")
    if prospective is not None and prospective.get("health") not in (
        "available",
        "waiting_for_completed_bin",
        "waiting_for_observations",
    ):
        labels.append(
            {
                "id": fingerprint(
                    [
                        run["runtime_id"],
                        "data",
                        prospective.get("cursor"),
                        prospective.get("health"),
                    ]
                ),
                "kind": "data_fault",
                "resolved": False,
                "comparable": False,
                "runtime_id": run["runtime_id"],
                "source": run["input"]["identity"],
            }
        )
    return labels


def shadow_pair(home, baseline, changes, evidence_digest, pair_ids):
    """Start explicit paired prospective runs through existing worker ownership."""
    from .data import load_recording
    from .ledger import RuntimeLedger
    from .store import ManagerStore

    store, ledger = ManagerStore(home), RuntimeLedger(home)
    active = ledger.get(baseline.bot_id)
    if (
        not active
        or active["spec"]["config_hash"] != baseline.config_hash
        or active["input"].get("prospective") is None
    ):
        raise ManagerError(
            "learning_blocked",
            "Shadow requires the unchanged active prospective source.",
            3,
        )
    from .oracle_data import prepare_descriptor

    original = active["input"]["descriptor"]
    descriptor = prepare_descriptor(
        original["archive_path"],
        capital_quote=original["capital_quote"],
        strategy_id=baseline.strategy_id,
    )
    proposed = learned_spec(baseline, changes, evidence_digest)
    results = []
    for role, spec in (("incumbent", baseline), ("challenger", proposed)):
        identifier = pair_ids[role]
        raw = spec.to_dict()
        raw.update(
            bot_id=identifier,
            source_identity=identifier,
            display_name="shadow-" + identifier,
        )
        shadow = BotSpec.from_dict(raw)
        existing = store.get_spec(identifier)
        if existing is not None and existing.config_hash != shadow.config_hash:
            raise ManagerError(
                "identity_conflict",
                "Shadow identity is bound to another configuration.",
            )
        if existing is None:
            store.create_spec(shadow)
        row = ledger.get(identifier)
        if row is None:
            data = load_recording(descriptor, strategy_id=shadow.strategy_id)
            if data.get("prospective") is None or data["bars"]:
                raise ManagerError(
                    "learning_blocked",
                    "A shadow activation cannot replay historical bars.",
                    3,
                )
            row = ledger.register(shadow, data)
            row = ledger.get(identifier)
        ledger.control(shadow, "start", str(uuid4()))
        results.append(
            {
                "role": role,
                "bot_id": identifier,
                "runtime_id": row["runtime_id"],
                "input_hash": row["input"]["snapshot_hash"],
                "comparability": comparable_identity(row),
                "initial_cursor": row["cursor"],
            }
        )
    return results


def reconcile_transition(
    store, owner, proposal_id, *, operation="promote", request_id=None
):
    """Owner commits authorization first; the manager replays it exactly once."""
    request_id = request_id or str(uuid4())
    response = owner.call(
        "learning-" + operation, {"proposal_id": proposal_id, "request_id": request_id}
    )
    receipt = response["receipt"]
    if (
        receipt["request_id"] != request_id
        or receipt["proposal_id"] != proposal_id
        or receipt["operation"] != operation
    ):
        raise ManagerError(
            "invalid_receipt", "Learning owner receipt binding is invalid.", 4
        )
    result = apply_owner_receipt(store, receipt)
    owner.call(
        "learning-reconcile",
        {
            "proposal_id": proposal_id,
            "request_id": request_id,
            "manager_receipt": result,
        },
    )
    return result


def apply_owner_receipt(store, receipt):
    from .ledger import RuntimeLedger

    ledger = RuntimeLedger(store.home)
    return ledger.learning_adopt(store, receipt)


def record_owner_view(store, response):
    """Cache only an acknowledged proposal pointer; owner eligibility stays remote."""
    from .domain import canonical
    from .mutations import mutation_lock

    proposal = response.get("proposal", response)
    if (
        not isinstance(proposal, Mapping)
        or not proposal.get("id")
        or not proposal.get("bot_id")
    ):
        return
    if proposal.get("home") != str(store.home.resolve()):
        raise ManagerError(
            "identity_conflict", "Proposal belongs to another manager home."
        )
    with mutation_lock(store.home), store._connection(write=True) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS learning_links (proposal_id TEXT PRIMARY KEY, bot_id TEXT NOT NULL, body TEXT NOT NULL)"
        )
        pointer = {
            "proposal_id": proposal["id"],
            "bot_id": proposal["bot_id"],
            "state": proposal["state"],
            "baseline_hash": proposal["baseline"]["config_hash"],
            "owner_scope": proposal["scope"],
            "counts": proposal["counts"],
            "shadow_started_at": proposal["shadow"]["started_at"]
            if proposal.get("shadow")
            else None,
            "owner_eligibility": "unknown_until_explicit_owner_refresh",
        }
        db.execute(
            "INSERT OR REPLACE INTO learning_links VALUES (?,?,?)",
            (proposal["id"], proposal["bot_id"], canonical(pointer)),
        )


def learning_snapshot(home, bot_id):
    """Read bounded local pointers, without migration or owner subprocesses.

    Each source permits 256 candidate rows, 16 KiB per JSON body and 256 KiB
    aggregate body bytes. Both connections have a 32 KiB SQLite row/value cap
    and 100000 SQL VM steps. The schedule reader separately caps 64 KiB;
    auxiliary input is therefore at most 576 KiB, below the report's 8 MiB cap.
    Legacy adoptions have no indexed bot identity. Inspect a bounded rowid window
    and refuse an incomplete window rather than scan arbitrary JSON history.
    """
    import math
    import sqlite3
    from contextlib import closing

    from .store import data_home

    home = Path(home) if home is not None else data_home()
    from .learning_job import schedule_snapshot

    result = {
        "schedule": schedule_snapshot(home),
        "state": "not_observed",
        "reason": "owner_refresh_required",
        "owner_eligibility": "unknown",
        "proposals": [],
        "adoptions": [],
        "local_metadata": {},
    }
    fields = {
        "bot_id",
        "state",
        "proposal_id",
        "baseline_hash",
        "owner_scope",
        "counts",
        "shadow_started_at",
        "owner_eligibility",
        "version",
        "request_id",
        "operation",
        "runtime_id",
        "accepted_revision",
        "accepted_hash",
        "prior_hash",
        "owner_receipt_digest",
        "predecessor",
        "account_preserved",
        "starts_workers",
    }

    def pointer(raw):
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise TypeError("invalid_pointer")
        identity, state = body.get("bot_id"), body.get("state")
        if (
            not isinstance(identity, str)
            or len(identity) > 128
            or not isinstance(state, str)
            or not 1 <= len(state) <= 64
        ):
            raise ValueError("invalid_pointer_identity_or_state")
        # Keep the small documented pointer, never arbitrary proposal payloads.
        projected = {key: value for key, value in body.items() if key in fields}
        for key, value in projected.items():
            if key == "counts":
                if (
                    not isinstance(value, dict)
                    or len(value) > 32
                    or any(
                        not isinstance(name, str)
                        or len(name) > 64
                        or type(count) is not int
                        or count < 0
                        for name, count in value.items()
                    )
                ):
                    raise ValueError("invalid_pointer_counts")
            elif value is not None and (
                not isinstance(value, (str, int, float, bool))
                or isinstance(value, str)
                and len(value) > 512
                or isinstance(value, float)
                and not math.isfinite(value)
            ):
                raise ValueError("invalid_pointer_field")
        return projected

    for name, table, key in (
        ("manager.sqlite3", "learning_links", "proposals"),
        ("runtime.sqlite3", "learning_adoptions", "adoptions"),
    ):
        path = home.absolute() / name
        if not path.is_file() or path.is_symlink():
            continue
        try:
            with closing(
                sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
            ) as db:
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 32768)
                steps = 0

                def progress():
                    nonlocal steps
                    steps += 1000
                    return int(steps > 100000)

                db.set_progress_handler(progress, 1000)
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                if not db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone():
                    continue
                clause = " WHERE bot_id=?" if key == "proposals" else ""
                # SQL identifiers are constants above. Never evaluate JSON while
                # searching for a bot in the unindexed legacy adoption table.
                rows = db.execute(
                    f"SELECT rowid,length(CAST(body AS BLOB)) FROM {table}"
                    + clause
                    + " ORDER BY rowid DESC LIMIT 257",
                    (bot_id,) if key == "proposals" else (),
                ).fetchall()
                if len(rows) > 256:
                    raise ValueError("local_metadata_scan_budget_exceeded")
                if any(type(size) is not int or size > 16384 for _, size in rows):
                    raise ValueError("local_metadata_body_budget_exceeded")
                if sum(size for _, size in rows) > 262144:
                    raise ValueError("local_metadata_byte_budget_exceeded")
                items = []
                for rowid, _ in rows:
                    raw = db.execute(
                        f"SELECT body FROM {table} WHERE rowid=?", (rowid,)
                    ).fetchone()[0]
                    body = pointer(raw)
                    if body["bot_id"] == bot_id and len(items) < 20:
                        items.append(body)
                result[key] = items
                result["local_metadata"][key] = {"state": "available", "reason": None}
        except (sqlite3.Error, ValueError, TypeError, RecursionError):
            # Keep corrupt/oversized raw data out of both output and exceptions.
            result["local_metadata"][key] = {
                "state": "unavailable",
                "reason": "local_metadata_invalid_or_budget_exceeded",
            }
    if any(
        item["state"] == "unavailable" for item in result["local_metadata"].values()
    ):
        result["state"] = "unavailable"
        result["reason"] = "local_learning_metadata_unavailable"
    elif result["adoptions"]:
        result["state"] = result["adoptions"][0]["state"]
    elif result["proposals"]:
        result["state"] = result["proposals"][0]["state"]
    return result
