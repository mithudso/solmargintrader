"""Protocol 2 additions to ExperimentStore; no second temporal authority.

Legacy schema 1 rows, splits and retries retain their original meaning. Manager
trials are consumed before execution and final exposure is irreversible.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from .evidence_identity import ExperimentError, canonical, fingerprint

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def exact(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ExperimentError("protocol2 schema fields differ")


class ManagerEvidence:
    def _manager_schema(self, db):
        db.executescript("""
        CREATE TABLE IF NOT EXISTS manager_history_gaps(identity TEXT PRIMARY KEY, reason TEXT NOT NULL, cutoff REAL);
        CREATE TABLE IF NOT EXISTS manager_budgets(
          scope TEXT PRIMARY KEY, last_ordinal INTEGER NOT NULL, imported_count INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS manager_attempts(
          run_id TEXT PRIMARY KEY REFERENCES runs(id), scope TEXT NOT NULL,
          ordinal INTEGER NOT NULL, state TEXT NOT NULL, challenger TEXT,
          final_spent_at REAL, outcome TEXT, UNIQUE(scope,ordinal));
        CREATE TABLE IF NOT EXISTS manager_trials(
          run_id TEXT REFERENCES runs(id), candidate TEXT, split TEXT, block INTEGER,
          result TEXT, PRIMARY KEY(run_id,candidate,split,block));
        CREATE TABLE IF NOT EXISTS manager_artifacts(
          run_id TEXT REFERENCES runs(id), name TEXT, body TEXT NOT NULL,
          PRIMARY KEY(run_id,name));
        CREATE TABLE IF NOT EXISTS manager_clients(
          root TEXT PRIMARY KEY, kind TEXT NOT NULL, active INTEGER NOT NULL,
          coverage TEXT NOT NULL, identity TEXT NOT NULL, checked_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS manager_imports(
          source TEXT, record TEXT, digest TEXT NOT NULL, attempts INTEGER NOT NULL,
          admitted_at REAL NOT NULL, historical INTEGER NOT NULL,
          PRIMARY KEY(source,record));
        CREATE TABLE IF NOT EXISTS manager_exposures(
          source TEXT, record TEXT, coin TEXT, start REAL, end REAL,
          PRIMARY KEY(source,record,coin,start,end));
        CREATE TABLE IF NOT EXISTS manager_final_dates(
          run_id TEXT REFERENCES runs(id), coin TEXT, start REAL, end REAL,
          PRIMARY KEY(run_id,coin,start,end));
        """)
        gap_columns = {
            r[1] for r in db.execute("PRAGMA table_info(manager_history_gaps)")
        }
        if "cutoff" not in gap_columns:
            db.execute("ALTER TABLE manager_history_gaps ADD COLUMN cutoff REAL")
        self._manager_import_migration(db)

    def _manager_import_migration(self, db):
        columns = {r[1] for r in db.execute("PRAGMA table_info(manager_imports)")}
        if "admitted_at" not in columns:
            db.execute(
                "ALTER TABLE manager_imports ADD COLUMN admitted_at REAL NOT NULL DEFAULT 0"
            )
        if "historical" not in columns:
            db.execute(
                "ALTER TABLE manager_imports ADD COLUMN historical INTEGER NOT NULL DEFAULT 1"
            )

    def manager_create(self, spec):
        exact(
            spec,
            (
                "protocol_version",
                "source",
                "bot",
                "incumbent_id",
                "scope",
                "context",
                "candidates",
                "budget",
                "geometry",
                "policy",
                "confidence",
                "search",
                "owner_identity",
            ),
        )
        if (
            spec["protocol_version"] != 2
            or type(spec["protocol_version"]) is not int
            or spec["source"] != "native"
            or spec["bot"] not in ("grid", "dca", "trend", "momentum", "arbitrage")
        ):
            raise ExperimentError("unsupported manager protocol or family")
        scope = spec["scope"]
        exact(
            scope,
            (
                "family",
                "coin",
                "base_mint",
                "quote_mint",
                "bar_seconds",
                "execution_model",
            ),
        )
        if (
            scope["family"] != spec["bot"]
            or scope["coin"] != "SOL"
            or scope["base_mint"] != SOL
            or scope["quote_mint"] != USDC
            or type(scope["bar_seconds"]) is not int
            or scope["bar_seconds"] < 1
            or not scope["execution_model"]
        ):
            raise ExperimentError("unsupported or aliased research scope")
        if spec["policy"] != {
            "minimum_trades": 30,
            "maximum_drawdown": 0.2,
            "drawdown_weight": 0.5,
        }:
            raise ExperimentError("unsupported frozen objective")
        if spec["budget"] != {"configurations": 32, "cells": 1000}:
            raise ExperimentError("unsupported frozen search budget")
        if (
            not isinstance(spec["candidates"], list)
            or not 1 <= len(spec["candidates"]) <= 32
        ):
            raise ExperimentError("configuration budget exceeded")
        import re

        ids = []
        for c in spec["candidates"]:
            exact(c, ("id", "config"))
            if (
                not isinstance(c["id"], str)
                or not re.fullmatch("[0-9a-f]{32}", c["id"])
                or not isinstance(c["config"], dict)
            ):
                raise ExperimentError("invalid opaque candidate")
            ids.append(c["id"])
        if len(set(ids)) != len(ids) or spec["incumbent_id"] not in ids:
            raise ExperimentError("invalid incumbent or duplicate candidate")
        exact(spec["geometry"], ("train", "validation", "holdout"))
        previous_end = None
        for split in ("train", "validation", "holdout"):
            intervals = self._intervals(spec["geometry"][split])
            for coin, start, end in intervals:
                if coin != scope["coin"] or (
                    previous_end is not None and start < previous_end
                ):
                    raise ExperimentError("overlapping or unordered partitions")
                previous_end = end
        exact(spec["confidence"], ("method", "seed", "minimum_blocks"))
        if (
            spec["confidence"]["method"] not in ("independent_sign", "block_bootstrap")
            or type(spec["confidence"]["seed"]) is not int
            or spec["confidence"]["minimum_blocks"] != 10
        ):
            raise ExperimentError("unsupported preregistered confidence policy")
        encoded = canonical(spec)
        run_id, now = uuid.uuid4().hex, time.time()
        # A market-wide superset is deliberately more conservative than the
        # exact scope: aliases, new timeframes and policy changes cannot reset k.
        ordinal_scope = "SOL:all-related-strategies-and-execution-models:v1"
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT COALESCE(MAX(ordinal),0) FROM manager_attempts WHERE scope=?",
                (ordinal_scope,),
            ).fetchone()[0]
            imported = db.execute(
                "SELECT COALESCE(SUM(attempts),0) FROM manager_imports"
            ).fetchone()[0]
            legacy = db.execute(
                "SELECT COUNT(*) FROM runs WHERE json_extract(spec,'$.protocol_version') IS NULL AND json_extract(spec,'$.source')='native'"
            ).fetchone()[0]
            budget = db.execute(
                "SELECT last_ordinal,imported_count FROM manager_budgets WHERE scope=?",
                (ordinal_scope,),
            ).fetchone()
            previous = budget["last_ordinal"] if budget else prior
            consumed = budget["imported_count"] if budget else 0
            ordinal = previous + max(0, imported + legacy - consumed) + 1
            db.execute(
                "INSERT INTO manager_budgets VALUES (?,?,?) ON CONFLICT(scope) DO UPDATE SET last_ordinal=excluded.last_ordinal,imported_count=excluded.imported_count",
                (ordinal_scope, ordinal, imported + legacy),
            )
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, encoded, "created", None, None, None, None, now, now),
            )
            db.execute(
                "INSERT INTO manager_artifacts VALUES (?,?,?)",
                (run_id, "admitted_external_attempts", canonical(imported + legacy)),
            )
            db.execute(
                "INSERT INTO manager_attempts VALUES (?,?,?,?,?,?,?)",
                (run_id, ordinal_scope, ordinal, "prepared", None, None, None),
            )
        return {
            "run_id": run_id,
            "ordinal": ordinal,
            "alpha": 0.05 / (ordinal * (ordinal + 1)),
        }

    def manager_status(self, run_id):
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM manager_attempts WHERE run_id=?", (run_id,)
            ).fetchone()
            if row is None:
                raise ExperimentError("manager run does not exist")
            count = db.execute(
                "SELECT COUNT(*) FROM manager_trials WHERE run_id=?", (run_id,)
            ).fetchone()[0]
        result = dict(row)
        result["outcome"] = (
            json.loads(result["outcome"])
            if result["outcome"]
            else (
                {
                    "outcome": "retained_incumbent",
                    "reason": "final_spent_pending_receipt",
                }
                if result["final_spent_at"] is not None
                else None
            )
        )
        return {
            **result,
            "alpha": 0.05 / (row["ordinal"] * (row["ordinal"] + 1)),
            "consumed_cells": count,
        }

    def manager_artifact(self, run_id, name, body):
        if name not in (
            "input",
            "training",
            "validation",
            "finalists",
            "mapping",
            "mapping_revealed",
            "proposal",
            "adoption_receipt",
            "final",
        ):
            raise ExperimentError("unknown manager evidence artifact")
        encoded = canonical(body)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT body FROM manager_artifacts WHERE run_id=? AND name=?",
                (run_id, name),
            ).fetchone()
            if old and old[0] != encoded:
                raise ExperimentError("immutable manager evidence artifact")
            db.execute(
                "INSERT OR IGNORE INTO manager_artifacts VALUES (?,?,?)",
                (run_id, name, encoded),
            )
        return body

    def manager_read_artifact(self, run_id, name):
        with self._connect() as db:
            row = db.execute(
                "SELECT body FROM manager_artifacts WHERE run_id=? AND name=?",
                (run_id, name),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def _manager_fence(self, db, intervals, *, final=False, own_run=None):
        for coin, start, end in intervals:
            query = "SELECT run_id FROM manager_final_dates WHERE coin=? AND start<? AND end>?"
            args = [coin, end, start]
            if own_run is not None:
                query += " AND run_id<>?"
                args.append(own_run)
            if not final:
                query += " AND run_id IN (SELECT run_id FROM manager_attempts WHERE state!='finished')"
            if db.execute(query, args).fetchone():
                raise ExperimentError("dates overlap protected or spent manager final")
            if final:
                for table in ("exposures", "holdouts", "manager_exposures"):
                    if db.execute(
                        f"SELECT 1 FROM {table} WHERE coin=? AND start<? AND end>?",
                        (coin, end, start),
                    ).fetchone():
                        raise ExperimentError(
                            "dates already exposed or spent; fresh evidence required"
                        )

    def manager_expose(self, run_id, split):
        if split not in ("train", "validation"):
            raise ExperimentError("only exploration may expose dates")
        spec = self.get_run(run_id)["spec"]
        if (
            split == "validation"
            and self.manager_read_artifact(run_id, "finalists") is None
        ):
            raise ExperimentError("validation finalists must be frozen before exposure")
        intervals = self._intervals(spec["geometry"][split])
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._manager_fence(db, intervals)
            for coin, start, end in intervals:
                if db.execute(
                    "SELECT 1 FROM holdouts WHERE coin=? AND start<? AND end>? AND sealed_at IS NULL",
                    (coin, end, start),
                ).fetchone():
                    raise ExperimentError("exploration overlaps native reserved final")
                db.execute(
                    "INSERT OR IGNORE INTO exposures VALUES (?,?,?,?,?)",
                    (spec["bot"], coin, start, end, run_id),
                )

    def manager_trial(self, run_id, candidate, split, block):
        spec = self.get_run(run_id)["spec"]
        if self.get_run(run_id)["status"] in (
            "cancel_requested",
            "cancelled",
            "pause_requested",
            "paused",
        ):
            raise ExperimentError("cancelled")
        if (
            candidate not in [c["id"] for c in spec["candidates"]]
            or split not in ("train", "validation", "holdout")
            or type(block) is not int
            or not 0 <= block < 1000
        ):
            raise ExperimentError("invalid manager trial")
        if split == "validation" and candidate not in (
            self.manager_read_artifact(run_id, "finalists") or []
        ):
            raise ExperimentError("validation candidate was not frozen as a finalist")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute(
                "SELECT * FROM manager_attempts WHERE run_id=?", (run_id,)
            ).fetchone()
            if state is None or state["state"] == "finished":
                raise ExperimentError("manager attempt finished")
            if split == "holdout" and (
                state["state"] != "unsealed"
                or candidate not in (spec["incumbent_id"], state["challenger"])
            ):
                raise ExperimentError("final requires spent frozen pair")
            if split != "holdout" and state["state"] != "prepared":
                raise ExperimentError("exploration is frozen")
            count = db.execute(
                "SELECT COUNT(*) FROM manager_trials WHERE run_id=?", (run_id,)
            ).fetchone()[0]
            if count >= 1000:
                raise ExperimentError("cell budget exhausted")
            try:
                db.execute(
                    "INSERT INTO manager_trials VALUES (?,?,?,?,NULL)",
                    (run_id, candidate, split, block),
                )
            except sqlite3.IntegrityError as exc:
                raise ExperimentError(
                    "trial already consumed; failed or dropped trials cannot retry"
                ) from exc
        return {"candidate": candidate, "split": split, "block": block}

    def manager_trial_result(self, run_id, ticket, result):
        exact(ticket, ("candidate", "split", "block"))
        encoded = canonical(result)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT result FROM manager_trials WHERE run_id=? AND candidate=? AND split=? AND block=?",
                (run_id, ticket["candidate"], ticket["split"], ticket["block"]),
            ).fetchone()
            if old is None or (old[0] is not None and old[0] != encoded):
                raise ExperimentError("trial missing or immutable")
            db.execute(
                "UPDATE manager_trials SET result=? WHERE run_id=? AND candidate=? AND split=? AND block=?",
                (
                    encoded,
                    run_id,
                    ticket["candidate"],
                    ticket["split"],
                    ticket["block"],
                ),
            )

    def _manager_verify_evidence(self, run_id, split, evidence):
        from botmanager.blind import verify

        exact(evidence, ("packet", "verdict"))
        spec = self.get_run(run_id)["spec"]
        try:
            verify(evidence["packet"], evidence["verdict"])
        except ValueError as exc:
            raise ExperimentError("invalid blind verdict") from exc
        if evidence["packet"]["policy"] != spec["policy"]:
            raise ExperimentError("blind policy differs from frozen specification")
        with self._connect() as db:
            rows = db.execute(
                "SELECT candidate,block,result FROM manager_trials WHERE run_id=? AND split=?",
                (run_id, split),
            ).fetchall()
        results = {
            (r["candidate"], r["block"]): json.loads(r["result"])
            if r["result"]
            else None
            for r in rows
        }
        for candidate in evidence["packet"]["candidates"]:
            if candidate["id"] not in [c["id"] for c in spec["candidates"]]:
                raise ExperimentError("verdict candidate is not frozen")
            for cell in candidate["cells"]:
                normal = results.get((candidate["id"], cell["block"] * 2))
                stress = results.get((candidate["id"], cell["block"] * 2 + 1))
                if (
                    not normal
                    or not stress
                    or normal.get("status") != "completed"
                    or stress.get("status") != "completed"
                ):
                    raise ExperimentError(
                        "blind packet has no completed comparable trials"
                    )
                n, t = normal["report"], stress["report"]
                expected = {
                    "block": cell["block"],
                    **n["metrics"],
                    "coverage": True,
                    "certified": n["certified"] and t["certified"],
                    "cost_stress": t["metrics"]["net_return"] >= 0,
                }
                if cell != expected:
                    raise ExperimentError(
                        "blind packet differs from immutable trial evidence"
                    )
            if len(candidate["cells"]) != len(spec["geometry"][split]):
                raise ExperimentError("blind packet omits chronological blocks")

    def manager_finalists(self, run_id, evidence):
        from botmanager.blind import resolve_tie

        self._manager_verify_evidence(run_id, "train", evidence)
        spec = self.get_run(run_id)["spec"]
        if {c["id"] for c in evidence["packet"]["candidates"]} != {
            c["id"] for c in spec["candidates"]
        }:
            raise ExperimentError("training omitted consumed configurations")
        challenger = resolve_tie(evidence["verdict"], spec["incumbent_id"])
        if challenger in (None, spec["incumbent_id"]):
            raise ExperimentError("no eligible challenger")
        finalists = [spec["incumbent_id"], challenger]
        self.manager_artifact(run_id, "training", evidence)
        self.manager_artifact(run_id, "finalists", finalists)
        return finalists

    def manager_freeze(self, run_id, candidate, evidence):
        spec = self.get_run(run_id)["spec"]
        if (
            candidate not in [c["id"] for c in spec["candidates"]]
            or candidate == spec["incumbent_id"]
        ):
            raise ExperimentError("freeze requires one challenger")
        # The protocol owner receives the complete anonymous packet and validates
        # the deterministic verdict before any resolver mapping is revealed.
        from botmanager.blind import resolve_tie

        self._manager_verify_evidence(run_id, "validation", evidence)
        finalists = self.manager_read_artifact(run_id, "finalists")
        if finalists != [spec["incumbent_id"], candidate] or {
            c["id"] for c in evidence["packet"]["candidates"]
        } != set(finalists):
            raise ExperimentError("validation differs from frozen finalists")
        if resolve_tie(evidence["verdict"], spec["incumbent_id"]) != candidate:
            raise ExperimentError("verdict did not select challenger")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute(
                "SELECT state,challenger FROM manager_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if state["state"] != "prepared":
                raise ExperimentError("challenger already frozen")
            db.execute(
                "INSERT INTO manager_artifacts VALUES (?,?,?)",
                (run_id, "validation", canonical(evidence)),
            )
            db.execute(
                "UPDATE manager_attempts SET state='frozen',challenger=? WHERE run_id=?",
                (candidate, run_id),
            )
            db.execute(
                "UPDATE runs SET frozen_candidate=? WHERE id=?", (candidate, run_id)
            )
        self.manager_artifact(
            run_id,
            "mapping_revealed",
            {"after_verdict_digest": evidence["verdict"]["verdict_digest"]},
        )

    def manager_unseal(self, run_id):
        spec = self.get_run(run_id)["spec"]
        if self.get_run(run_id)["status"] in (
            "cancel_requested",
            "cancelled",
            "pause_requested",
            "paused",
        ):
            raise ExperimentError("cancelled")
        intervals = self._intervals(spec["geometry"]["holdout"])
        with self._connect() as db:
            clients = [
                dict(r)
                for r in db.execute("SELECT root,kind,active,identity FROM manager_clients")
            ]
        for client in clients:
            previous = json.loads(client["identity"])
            declared = previous.get("declared_active")
            # An observed flock may later clear. Explicit manual declarations
            # and legacy records whose origin is unknown remain conservative.
            self.manager_register_client({
                "root": client["root"], "kind": client["kind"],
                "active": declared if type(declared) is bool else bool(client["active"]),
            })
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute(
                "SELECT * FROM manager_attempts WHERE run_id=?", (run_id,)
            ).fetchone()
            audit = db.execute(
                "SELECT body FROM manager_artifacts WHERE run_id=? AND name='mapping_revealed'",
                (run_id,),
            ).fetchone()
            verdict = db.execute(
                "SELECT body FROM manager_artifacts WHERE run_id=? AND name='validation'",
                (run_id,),
            ).fetchone()
            if (
                audit is None
                or verdict is None
                or json.loads(audit[0])["after_verdict_digest"]
                != json.loads(verdict[0])["verdict"]["verdict_digest"]
            ):
                raise ExperimentError(
                    "final requires persisted verdict and mapping access audit"
                )
            if state["state"] != "frozen" or state["final_spent_at"] is not None:
                raise ExperimentError("final attempt already spent or not frozen")
            if db.execute(
                "SELECT 1 FROM manager_clients WHERE active=1 OR coverage!='verified'"
            ).fetchone():
                raise ExperimentError(
                    "client coverage unavailable or unaware active client"
                )
            if db.execute(
                "SELECT 1 FROM manager_history_gaps WHERE cutoff IS NULL OR cutoff>?",
                (min(start for _, start, _ in intervals),),
            ).fetchone():
                raise ExperimentError(
                    "unknown prior history prevents fresh-final admission"
                )
            admitted = db.execute(
                "SELECT body FROM manager_artifacts WHERE run_id=? AND name='admitted_external_attempts'",
                (run_id,),
            ).fetchone()
            external = db.execute(
                "SELECT COALESCE(SUM(attempts),0) FROM manager_imports"
            ).fetchone()[0]
            legacy = db.execute(
                "SELECT COUNT(*) FROM runs WHERE json_extract(spec,'$.protocol_version') IS NULL AND json_extract(spec,'$.source')='native'"
            ).fetchone()[0]
            if admitted is None or json.loads(admitted[0]) != external + legacy:
                raise ExperimentError(
                    "external attempt history changed after preregistration; prepare with current alpha"
                )
            self._manager_fence(db, intervals, final=True)
            for coin, start, end in intervals:
                db.execute(
                    "INSERT INTO manager_final_dates VALUES (?,?,?,?)",
                    (run_id, coin, start, end),
                )
                # Same native temporal ledger also fences legacy consumers.
                db.execute(
                    "INSERT INTO holdouts(bot,coin,start,end,run_id,candidate_id,context) VALUES (?,?,?,?,?,?,?)",
                    (
                        spec["bot"],
                        coin,
                        start,
                        end,
                        run_id,
                        state["challenger"],
                        fingerprint(spec),
                    ),
                )
            db.execute(
                "UPDATE manager_attempts SET state='unsealed',final_spent_at=? WHERE run_id=?",
                (time.time(), run_id),
            )
        return self.manager_status(run_id)

    def manager_finish(self, run_id, outcome):
        encoded = canonical(outcome)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT state,outcome FROM manager_attempts WHERE run_id=?", (run_id,)
            ).fetchone()
            if old is None or (
                old["state"] == "finished" and old["outcome"] != encoded
            ):
                raise ExperimentError("immutable finished outcome")
            db.execute(
                "UPDATE manager_attempts SET state='finished',outcome=? WHERE run_id=?",
                (encoded, run_id),
            )
            db.execute(
                "UPDATE runs SET status='completed',summary=?,updated_at=? WHERE id=?",
                (encoded, time.time(), run_id),
            )
            db.execute(
                "UPDATE holdouts SET sealed_at=COALESCE(sealed_at,?) WHERE run_id=?",
                (time.time(), run_id),
            )
        return self.manager_status(run_id)

    def manager_history_revision(self, exclude_run=None):
        """Only possibly-prior exposure of this final and its frozen alpha matter.

        Later unrelated dates and ordinary paper reads after final admission do
        not retrospectively invalidate an accepted experiment's shadow period.
        """
        run = self.get_run(exclude_run)
        intervals = self._intervals(run["spec"]["geometry"]["holdout"])
        with self._connect() as db:
            attempt = db.execute(
                "SELECT scope,ordinal,final_spent_at FROM manager_attempts WHERE run_id=?",
                (exclude_run,),
            ).fetchone()
            if attempt is None or attempt["final_spent_at"] is None:
                raise ExperimentError("final scope is not admitted")
            imports = set()
            native = set()
            for coin, start, end in intervals:
                imports.update(
                    tuple(r)
                    for r in db.execute(
                        "SELECT DISTINCT i.source,i.record,i.digest,i.attempts FROM manager_imports i JOIN manager_exposures e ON e.source=i.source AND e.record=i.record WHERE e.coin=? AND e.start<? AND e.end>? AND (i.historical=1 OR i.admitted_at<=?)",
                        (coin, end, start, attempt["final_spent_at"]),
                    )
                )
                for table in ("exposures", "holdouts"):
                    native.update(
                        tuple(r)
                        for r in db.execute(
                            f"SELECT DISTINCT r.id,r.spec,e.coin,e.start,e.end FROM {table} e JOIN runs r ON r.id=e.run_id WHERE e.coin=? AND e.start<? AND e.end>? AND r.created_at<=? AND json_extract(r.spec,'$.protocol_version') IS NULL",
                            (coin, end, start, attempt["final_spent_at"]),
                        )
                    )
            body = {
                "imports": sorted(imports),
                "native": sorted(native),
                "attempt": dict(attempt),
                "spec_digest": fingerprint(run["spec"]),
                "gaps": [
                    tuple(r)
                    for r in db.execute(
                        "SELECT identity,reason,cutoff FROM manager_history_gaps WHERE cutoff IS NULL OR cutoff>? ORDER BY identity",
                        (min(start for _, start, _ in intervals),),
                    )
                ],
                "clients": [
                    tuple(r)
                    for r in db.execute(
                        "SELECT root,kind,active,coverage FROM manager_clients ORDER BY root"
                    )
                ],
            }
        return fingerprint(body)

    def manager_coverage(self):
        with self._connect() as db:
            gaps = [
                {
                    "code": "unknown_prior_history",
                    "identity": r["identity"],
                    "reason": r["reason"],
                    "affects_dates_before": r["cutoff"],
                }
                for r in db.execute("SELECT * FROM manager_history_gaps")
            ]
            clients = [
                {
                    "code": "active_unverified_client"
                    if r["active"]
                    else "history_coverage_unavailable",
                    "root": r["root"],
                    "coverage": r["coverage"],
                }
                for r in db.execute(
                    "SELECT root,active,coverage FROM manager_clients WHERE active=1 OR coverage!='verified'"
                )
            ]
        return {
            "coverage": "registered_roots_only",
            "globally_fresh": False,
            "production_eligible": False,
            "blockers": gaps + clients,
        }

    def manager_mark_history_gap(self, identity, reason, *, cutoff=None):
        """Retain unknown history; an owner-issued epoch never moves or resets k."""
        if cutoff is not None:
            import math

            if (
                type(cutoff) not in (int, float)
                or not math.isfinite(cutoff)
                or cutoff <= 0
            ):
                raise ExperimentError("invalid history epoch")
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO manager_history_gaps VALUES (?,?,?)",
                (identity, reason, cutoff),
            )

    def manager_pre_read(self, intervals):
        """Admit trusted input freezing without evaluating or exposing sealed rows.

        The optimizer lease spans this check and snapshot capture. Exploration
        is separately recorded before each simulation; candidate generation has
        no access to validation/final arrays.
        """
        normalized = self._intervals(intervals)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._manager_fence(db, normalized)
            for coin, start, end in normalized:
                if db.execute(
                    "SELECT 1 FROM holdouts WHERE coin=? AND start<? AND end>? AND sealed_at IS NULL",
                    (coin, end, start),
                ).fetchone():
                    raise ExperimentError("input read overlaps protected native final")

    def manager_import(
        self, source, record, digest, intervals, *, attempts=0, historical=False
    ):
        normalized = self._intervals(intervals) if intervals else []
        if intervals and not historical:
            self.manager_pre_read(intervals)
        if type(attempts) is not int or attempts < 0:
            raise ExperimentError("invalid imported attempts")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT digest,attempts FROM manager_imports WHERE source=? AND record=?",
                (source, record),
            ).fetchone()
            if old:
                if old["digest"] != digest or old["attempts"] != attempts:
                    raise ExperimentError(
                        "import identity changed; new immutable receipt required"
                    )
                return
            if not historical:
                self._manager_fence(db, normalized)
            db.execute(
                "INSERT INTO manager_imports VALUES (?,?,?,?,?,?)",
                (source, record, digest, attempts, time.time(), int(historical)),
            )
            for coin, start, end in normalized:
                db.execute(
                    "INSERT INTO manager_exposures VALUES (?,?,?,?,?)",
                    (source, record, coin, start, end),
                )

    def manager_register_client(self, descriptor):
        exact(descriptor, ("root", "kind", "active"))
        root = Path(descriptor["root"])
        if (
            not root.is_absolute()
            or descriptor["kind"] not in ("native", "f5", "bg", "forward")
            or type(descriptor["active"]) is not bool
        ):
            raise ExperimentError("invalid known owner root")
        root = root.resolve()
        from .research_admission import inspect_history

        evidence = inspect_history(root, descriptor["kind"])
        evidence["declared_active"] = descriptor["active"]
        with self._connect() as db:
            previous = db.execute(
                "SELECT kind,identity FROM manager_clients WHERE root=?", (str(root),)
            ).fetchone()
        if previous is not None and previous["kind"] != descriptor["kind"]:
            raise ExperimentError("registered owner kind cannot change")
        prior = json.loads(previous["identity"]) if previous else {}
        observed = prior.get("history_observed", not prior.get("absence_checked", True))
        evidence["history_observed"] = observed or not evidence["absence_checked"]
        if observed and evidence["absence_checked"]:
            evidence["coverage"] = "unavailable"
        for row in evidence["records"]:
            if root == self.root.resolve() and (
                row["id"].startswith("native:") or row["id"].startswith("attempt:")
            ):
                continue
            self.manager_import(
                str(root),
                row["id"],
                row["digest"],
                row["intervals"],
                attempts=row["attempts"],
                historical=True,
            )
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO manager_clients VALUES (?,?,?,?,?,?) ON CONFLICT(root) DO UPDATE SET active=excluded.active,coverage=excluded.coverage,identity=excluded.identity,checked_at=excluded.checked_at",
                (
                    str(root),
                    descriptor["kind"],
                    descriptor["active"] or evidence["active"],
                    evidence["coverage"],
                    canonical(evidence),
                    time.time(),
                ),
            )
        return evidence
