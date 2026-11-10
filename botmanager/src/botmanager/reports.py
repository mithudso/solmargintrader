"""Read-only attributed reports and SQL-bounded stable event/history pages."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping

from .accounting import accounting_snapshot
from .domain import ManagerError
from .ledger import RuntimeLedger


def _bounds(after, limit):
    if (
        type(after) is not int
        or after < 0
        or type(limit) is not int
        or not 1 <= limit <= 1000
    ):
        raise ManagerError(
            "invalid_input", "Page requires after >= 0 and limit between 1 and 1000."
        )


def _page(rows, after, limit):
    more = len(rows) > limit
    items = rows[:limit]
    return {
        "schema_version": 1,
        "items": items,
        "after": after,
        "next_after": items[-1]["sequence"] if items else after,
        "has_more": more,
    }


def event_page(ledger, bot_id, *, run_id=None, after=0, limit=100):
    _bounds(after, limit)
    if not ledger.path.is_file():
        return _page([], after, limit)
    with ledger.connection() as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version < 4 and run_id is not None:
            raise ManagerError(
                "evidence_unavailable", "Legacy events lack stable runtime attribution."
            )
        clause = " AND runtime_id=?" if run_id is not None else ""
        args = [bot_id, after] + ([run_id] if run_id is not None else []) + [limit + 1]
        rows = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM events WHERE bot_id=? AND sequence>?"
                + clause
                + " ORDER BY sequence LIMIT ?",
                args,
            )
        ]
        return _page(rows, after, limit)


def history_page(store, bot_id, *, after=0, limit=100):
    """Page append-only spec revisions without loading the runtime archive."""
    _bounds(after, limit)
    spec = store.get_spec(bot_id)
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    with store._connection() as db:
        if db.execute("PRAGMA user_version").fetchone()[0] == 1:
            items = (
                [
                    {
                        "sequence": spec.config_revision,
                        "spec": spec.to_dict(),
                        "saved_at": spec.created_at,
                        "request_id": None,
                    }
                ]
                if after < spec.config_revision
                else []
            )
            return {"bot_id": spec.bot_id, **_page(items, after, limit)}
        rows = [
            {
                "sequence": row["revision"],
                "spec": store._decode(row["body"]).to_dict(),
                "saved_at": row["saved_at"],
                "request_id": row["request_id"],
            }
            for row in db.execute(
                "SELECT * FROM spec_versions WHERE bot_id=? AND revision>? ORDER BY revision LIMIT ?",
                (spec.bot_id, after, limit + 1),
            )
        ]
        if any(
            row["spec"]["bot_id"] != spec.bot_id
            or row["spec"]["config_revision"] != row["sequence"]
            for row in rows
        ):
            raise ManagerError(
                "invalid_spec", "Historical specification attribution is invalid.", 4
            )
    return {"bot_id": spec.bot_id, **_page(rows, after, limit)}


def run_history_page(store, bot_id, *, after=0, limit=100):
    """Archive cursors are SQLite rowids; current runtime is separate metadata."""
    _bounds(after, limit)
    spec = store.get_spec(bot_id)
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    ledger = RuntimeLedger(store.home)
    if not ledger.path.is_file():
        return {"current_runtime_id": None, **_page([], after, limit)}
    with ledger.connection() as db:
        current = db.execute(
            "SELECT runtime_id FROM runs WHERE bot_id=?", (spec.bot_id,)
        ).fetchone()
        rows = []
        if db.execute("PRAGMA user_version").fetchone()[0] >= 3:
            for row in db.execute(
                "SELECT rowid AS sequence,* FROM archives WHERE bot_id=? AND rowid>? ORDER BY rowid LIMIT ?",
                (spec.bot_id, after, limit + 1),
            ):
                rows.append(
                    {
                        "sequence": row["sequence"],
                        "runtime_id": row["runtime_id"],
                        "archived": True,
                    }
                )
        return {
            "current_runtime_id": current[0] if current else None,
            **_page(rows, after, limit),
        }


def _projection(run, archived):
    spec, data, cp = run["spec"], run["input"], run.get("checkpoint") or {}
    descriptor = data.get("descriptor", {})
    identity = data.get("identity", {})
    mode = (
        "prospective_paper"
        if data.get("prospective") is not None
        else "reference_paper"
    )
    metrics = cp.get("research_metrics")
    return {
        "schema_version": 1,
        "bot_id": run["bot_id"],
        "runtime_id": run["runtime_id"],
        "owner_id": run.get("owner"),
        "generation": run["generation"],
        "archived": archived,
        "mode": mode,
        "configuration": spec,
        "provenance": {
            "source": identity.get("source", "coinbase_proxy"),
            "timeframe": identity.get("bar_seconds", descriptor.get("timeframe")),
            "dataset_hash": data.get("snapshot_hash"),
            "cost_model": identity.get("costs"),
            "engine_identity": identity.get("engine_identity"),
            "input_identity": identity,
        },
        "sample_size": run["cursor"],
        "learning_status": "not_implemented",
        "selection_status": "descriptive_not_selection_evidence",
        "research_metrics": metrics,
        "loss_cohort": "negative"
        if cp.get("equity_quote") is not None
        and descriptor.get("capital_quote") is not None
        and cp["equity_quote"] < descriptor["capital_quote"]
        else "unclassified",
        "accounting": accounting_snapshot(run),
    }


def report_page(
    store, bot_id: str, *, run_id: str | None = None, after: int = 0, limit: int = 100
):
    """Report one pinned current/archive run plus a bounded event stream.

    The event sequence is the cursor. Archive selection uses a keyed lookup;
    reporting an old run never loads every archived run or substitutes saved edits.
    """
    _bounds(after, limit)
    spec = store.get_spec(bot_id)
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    ledger = RuntimeLedger(store.home)
    if not ledger.path.is_file():
        return {
            "report": None,
            "reason": "runtime_not_available",
            **_page([], after, limit),
        }
    with ledger.connection() as db:
        raw = db.execute(
            "SELECT * FROM runs WHERE bot_id=?"
            + (" AND runtime_id=?" if run_id else ""),
            (spec.bot_id, run_id) if run_id else (spec.bot_id,),
        ).fetchone()
        archived = False
        if raw is not None:
            run = ledger._decode(db, raw)
        elif run_id and db.execute("PRAGMA user_version").fetchone()[0] >= 3:
            archive = db.execute(
                "SELECT * FROM archives WHERE bot_id=? AND runtime_id=?",
                (spec.bot_id, run_id),
            ).fetchone()
            run = (
                ledger._decode_archive(db, archive)["state"]
                if archive is not None
                else None
            )
            archived = True
        else:
            run = None
        if run is None:
            raise ManagerError(
                "runtime_not_available", "Requested runtime was not found."
            )
        report = _projection(run, archived)
        from .learning import learning_snapshot

        report["learning"] = {
            "scope": "current_bot_not_archived_run",
            **learning_snapshot(store.home, spec.bot_id),
        }
        report["learning_status"] = (
            "historical_run" if archived else report["learning"]["state"]
        )
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version < 4:
            return {
                "report": report,
                "reason": "legacy_event_attribution_unavailable",
                **_page([], after, limit),
            }
        rows = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM events WHERE bot_id=? AND runtime_id=? AND sequence>? ORDER BY sequence LIMIT ?",
                (spec.bot_id, run["runtime_id"], after, limit + 1),
            )
        ]
        return {"report": report, **_page(rows, after, limit)}


def compare_reports(left: Mapping, right: Mapping):
    mismatches = [key for key in ("mode",) if left.get(key) != right.get(key)]
    for key in ("source", "timeframe", "dataset_hash", "cost_model", "engine_identity"):
        a, b = left.get("provenance", {}).get(key), right.get("provenance", {}).get(key)
        if a is None or b is None or a != b:
            mismatches.append(key)
    if (
        left.get("accounting", {}).get("currency")
        != right.get("accounting", {}).get("currency")
        or left.get("accounting", {}).get("currency") is None
    ):
        mismatches.append("currency")
    return {
        "compatible": not mismatches,
        "mismatches": mismatches,
        "reason": "independent_virtual_accounts_are_not_a_wallet_total",
    }


def _flatten(value, prefix=""):
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _flatten(item, f"{prefix}.{key}" if prefix else str(key))
    else:
        yield (
            prefix,
            json.dumps(value, sort_keys=True, allow_nan=False)
            if isinstance(value, (list, tuple))
            else value,
        )


def render_report(page, format="human"):
    if format == "json":
        return json.dumps(page, sort_keys=True, allow_nan=False)
    rows = list(_flatten(page))
    if format == "human":
        return "\n".join(
            f"{key}: {'unavailable' if value is None else value}" for key, value in rows
        )
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["field", "value"])
        writer.writerows(rows)
        return output.getvalue()
    raise ManagerError("invalid_input", "Report format must be human, json or csv.")
