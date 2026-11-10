"""Canonical research-scoped labels, real shadow ownership and transition receipts.

This module owns wall clocks and quotas. Wire callers cannot supply timestamps,
counts, certification, shadow fills or a replacement research namespace.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from botmanager.domain import BotSpec, ManagerError, canonical, fingerprint
from botmanager.learning import (
    canonical_scope,
    classify_outcome,
    comparable_identity,
    learned_spec,
    outcome_summary,
    runtime_outcomes,
    shadow_input_binding,
    shadow_pair,
)

DAY = 86400
COOLDOWN = 48 * 3600
FORECAST_MAX_ROWS = 100000
FORECAST_MAX_BYTES = 16 * 1024 * 1024


from .experiments import ExperimentStore


class ForecastCoverageError(ValueError):
    pass


def excluded_oracle_forecast(scope, row):
    """Current Oracle contracts predict direction, not manager trade outcomes.

    No catalog ID is an accepted alias. Preserve the original model, parameters,
    horizon and source policy so a later verified attribution contract can be
    added without pretending that past rows used today's manager configuration.
    """
    (
        sequence,
        forecast_id,
        hit,
        resolved_at,
        resolution_raw,
        strategy,
        version,
        issued,
        target,
        forecast_raw,
    ) = row
    try:
        forecast, resolution = json.loads(forecast_raw), json.loads(resolution_raw)
    except (ValueError, TypeError, RecursionError):
        forecast = resolution = None
    valid = (
        isinstance(forecast, dict)
        and isinstance(resolution, dict)
        and forecast.get("forecast_id") == forecast_id
        and resolution.get("forecast_id") == forecast_id
        and forecast.get("strategy_id") == strategy
        and forecast.get("version") == version
        and forecast.get("issued_at") == issued
        and forecast.get("expires_at") == target
        and resolution.get("hit") == hit
        and resolution.get("resolved_at") == resolved_at
        and isinstance(forecast.get("parameters"), dict)
        and type(forecast.get("horizon_seconds")) is int
        and forecast["horizon_seconds"] > 0
        and forecast["horizon_seconds"] == target - issued
    )
    reasons = [
        "oracle_directional_forecast_not_manager_trade_outcome",
        "manager_oracle_model_parameter_contract_unverified",
        "manager_trade_horizon_not_oracle_fixed_horizon",
    ]
    if not valid:
        reasons.append("oracle_forecast_provenance_invalid")
    if (
        not isinstance(forecast, dict)
        or not isinstance(forecast.get("policy_hash"), str)
        or any(
            not isinstance(forecast.get(key), str)
            for key in ("source", "venue", "instrument", "kind")
        )
    ):
        reasons.append("oracle_forecast_source_policy_unbound")
    resolved = (
        valid
        and hit in (0, 1)
        and type(resolved_at) in (int, float)
        and math.isfinite(resolved_at)
    )
    provenance = (
        forecast
        if isinstance(forecast, dict)
        else {"state": "unavailable", "reason": "oracle_forecast_provenance_invalid"}
    )
    source_key = "oracle_excluded:" + fingerprint(
        {
            "strategy": strategy,
            "version": version,
            "parameters": provenance.get("parameters"),
            "horizon_seconds": provenance.get("horizon_seconds"),
            "source": {
                key: provenance.get(key)
                for key in ("source", "venue", "instrument", "kind", "policy_hash")
            },
        }
    )
    return source_key, {
        "id": fingerprint([scope, forecast_id, forecast_raw, resolution_raw]),
        "kind": "forecast",
        "resolved": bool(resolved),
        "correct": bool(hit) if resolved else None,
        "comparable": False,
        "eligibility": "ineligible",
        "exclusion_reasons": reasons,
        "forecast_id": forecast_id,
        "oracle_sequence": sequence,
        "oracle_provenance": provenance,
        "resolution": resolution if isinstance(resolution, dict) else None,
    }


class ReadOnlyResearch(ExperimentStore):
    """Read existing evidence without invoking schema migration or initialization."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.path = self.root / "experiments.sqlite3"

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=1)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            yield db
        finally:
            db.close()


class LearningOwner:
    def __init__(self, root, registration, research_store=None):
        self.root = Path(root).resolve()
        self.path = self.root / "experiments.sqlite3"
        self.registration = registration
        self.research_store = research_store

    @contextmanager
    def connection(self, write=False):
        if not self.path.is_file():
            raise ValueError("canonical research authority unavailable")
        db = sqlite3.connect(
            self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
            uri=True,
            timeout=1,
        )
        try:
            db.row_factory = sqlite3.Row
            if not write:
                db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if write:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS learning_labels (id TEXT PRIMARY KEY, scope TEXT NOT NULL, comparable TEXT NOT NULL, body TEXT NOT NULL, recorded REAL NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS learning_proposals (id TEXT PRIMARY KEY, scope TEXT NOT NULL, day TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(scope,day))"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS learning_requests (request_id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL, operation TEXT NOT NULL, body TEXT NOT NULL, manager_receipt TEXT)"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS learning_cooldowns (scope TEXT PRIMARY KEY, reserved REAL NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS learning_schedule (scope TEXT NOT NULL, day TEXT NOT NULL, home TEXT NOT NULL, state TEXT NOT NULL, attempted REAL NOT NULL, body TEXT NOT NULL, PRIMARY KEY(scope,day))"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS learned_defaults (scope TEXT PRIMARY KEY, body TEXT NOT NULL, receipt TEXT NOT NULL)"
                )
            yield db
            if write:
                db.commit()
        finally:
            db.close()

    def daily(self, home):
        """One canonical daily attempt per scope; reuses M4's accepted results."""
        from botmanager.store import ManagerStore

        home = Path(home).resolve()
        store = ManagerStore(home)
        now = time.time()
        day = datetime.fromtimestamp(now, UTC).date().isoformat()
        with self.connection(True) as db:
            shadow_ids = set()
            for (raw,) in db.execute("SELECT body FROM learning_proposals"):
                shadow = json.loads(raw).get("shadow")
                if shadow:
                    shadow_ids.update(shadow["pair_ids"].values())
        groups = {}
        for spec in store.list_specs():
            if spec.bot_id in shadow_ids:
                continue
            try:
                _, row = self._runtime(home, spec.bot_id)
            except (ValueError, ManagerError):
                continue
            scope = canonical_scope(spec, row["input"]["identity"])
            groups.setdefault(scope, []).append(spec)
        results = []
        for scope, specs in groups.items():
            with self.connection(True) as db:
                previous = db.execute(
                    "SELECT state,body FROM learning_schedule WHERE scope=? AND day=?",
                    (scope, day),
                ).fetchone()
                if previous:
                    results.append(
                        {
                            "scope": scope,
                            "state": previous["state"],
                            "reason": "canonical_daily_attempt_already_recorded",
                            "prior": json.loads(previous["body"]),
                        }
                    )
                    continue
                db.execute(
                    "INSERT INTO learning_schedule VALUES (?,?,?,?,?,?)",
                    (
                        scope,
                        day,
                        str(home),
                        "running",
                        now,
                        canonical({"reason": "canonical_attempt_reserved"}),
                    ),
                )
            result = {
                "scope": scope,
                "state": "retained_incumbent",
                "reason": "accepted_compatible_research_proposal_unavailable",
                "proposal_id": None,
            }
            try:
                # Try all active configurations in the same scope; creating another
                # UUID cannot create another daily reservation or optimizer.
                for spec in specs:
                    counts = self.collect(home, spec.bot_id)
                    if counts.get("counts_complete") is False:
                        result["reason"] = counts["reason"]
                        continue
                    result["counts"] = {
                        key: counts[key]
                        for key in (
                            "resolved_comparable_labels",
                            "completed_trades",
                            "cohorts",
                        )
                    }
                    if (
                        counts["resolved_comparable_labels"] < 300
                        or counts["completed_trades"] < 30
                    ):
                        result["reason"] = (
                            "minimum_300_labels_and_30_completed_trades_pending"
                        )
                        continue
                    with self.research_store._connect() as research_db:
                        candidates = [
                            row[0]
                            for row in research_db.execute(
                                "SELECT run_id FROM manager_attempts WHERE state='finished' ORDER BY rowid DESC LIMIT 1000"
                            )
                        ]
                    for run_id in candidates:
                        try:
                            evidence, _ = self._evidence(run_id)
                            if (
                                evidence["bot_id"] != spec.bot_id
                                or evidence["baseline_hash"] != spec.config_hash
                            ):
                                continue
                            proposal = self.propose(home, spec.bot_id, run_id)
                            from botmanager.learning import record_owner_view

                            record_owner_view(store, proposal)
                            result.update(
                                state="proposal_pending_shadow",
                                reason="accepted_m4_proposal_staged",
                                proposal_id=proposal["id"],
                                bot_id=spec.bot_id,
                            )
                            break
                        except (ValueError, ManagerError):
                            continue
                    if result["proposal_id"] is not None:
                        break
                    result["reason"] = (
                        "accepted_compatible_research_proposal_unavailable"
                    )
            except (ValueError, ManagerError, sqlite3.Error):
                result["reason"] = "owner_measurement_or_evidence_unavailable"
            with self.connection(True) as db:
                db.execute(
                    "UPDATE learning_schedule SET state=?,body=? WHERE scope=? AND day=?",
                    (result["state"], canonical(result), scope, day),
                )
            results.append(result)
        return {
            "day": day,
            "attempted_at": now,
            "scopes": results,
            "starts_workers": False,
            "new_optimizer": False,
            "reason": "no_registered_active_scope"
            if not groups
            else "daily_canonical_scope_attempts_recorded",
        }

    def _read_proposal(self, db, proposal_id):
        row = db.execute(
            "SELECT body FROM learning_proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        if row is None:
            raise ValueError("learning proposal not found")
        return json.loads(row[0])

    def _save(self, db, proposal):
        db.execute(
            "UPDATE learning_proposals SET body=? WHERE id=?",
            (canonical(proposal), proposal["id"]),
        )

    def _runtime(self, home, bot_id):
        from botmanager.ledger import RuntimeLedger
        from botmanager.store import ManagerStore

        home = Path(home)
        if not home.is_absolute() or home.is_symlink() or not home.is_dir():
            raise ValueError("existing explicit manager home required")
        spec = ManagerStore(home).get_spec(bot_id)
        row = RuntimeLedger(home).get(bot_id) if spec else None
        if not row or row["spec"]["config_hash"] != spec.config_hash:
            raise ValueError("saved and active configurations must match")
        return spec, row

    def _all_runtime_labels(self, ledger, run):
        # Runtime validation reconciles segment fill prefixes before this read.
        with ledger.connection() as db:
            fills = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT body FROM fills WHERE bot_id=? AND sequence<? ORDER BY sequence",
                    (
                        run["bot_id"],
                        run.get("fill_base", 0)
                        + len((run.get("checkpoint") or {}).get("fills", [])),
                    ),
                )
            ]
        cp = dict(run.get("checkpoint") or {}, fills=fills)
        return runtime_outcomes({**run, "checkpoint": cp})

    def collect(self, home, bot_id):
        from botmanager.ledger import RuntimeLedger

        spec, current = self._runtime(home, bot_id)
        scope = canonical_scope(spec, current["input"]["identity"])
        comparable = comparable_identity(current)
        rows = [current]
        ledger = RuntimeLedger(home)
        with ledger.connection() as runtime_db:
            if runtime_db.execute("PRAGMA user_version").fetchone()[0] >= 3:
                if (
                    runtime_db.execute(
                        "SELECT count(*) FROM archives WHERE bot_id=?", (spec.bot_id,)
                    ).fetchone()[0]
                    > 1000
                ):
                    raise ValueError(
                        "archive outcome budget exceeded; no partial learning count accepted"
                    )
                for archived in runtime_db.execute(
                    "SELECT * FROM archives WHERE bot_id=? ORDER BY rowid LIMIT 1000",
                    (spec.bot_id,),
                ):
                    decoded = ledger._decode_archive(runtime_db, archived)["state"]
                    archive_body = json.loads(archived["body"])
                    cp = dict(
                        decoded.get("checkpoint") or {},
                        fills=[
                            json.loads(fill["body"]) for fill in archive_body["fills"]
                        ],
                    )
                    decoded["account_outcomes"] = runtime_outcomes(
                        {**decoded, "checkpoint": cp}
                    )
                    rows.append(decoded)
        outcomes = []
        for run in rows:
            if (
                canonical_scope(
                    BotSpec.from_dict(run["spec"]), run["input"]["identity"]
                )
                != scope
            ):
                continue
            run_key = comparable_identity(run)
            labels = (
                self._all_runtime_labels(ledger, run)
                if run["runtime_id"] == current["runtime_id"]
                else run["account_outcomes"]
            )
            outcomes.extend((run_key, label) for label in labels)
        archive = current["input"]["descriptor"].get("archive_path")
        forecast_labels = []
        if archive:
            db = sqlite3.connect(
                Path(archive).as_uri() + "?mode=ro", uri=True, timeout=1
            )
            try:
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                if db.execute("PRAGMA application_id").fetchone()[0] != 0x4F52434C:
                    raise ValueError("forecast archive identity mismatch")
                total_bytes = 0
                for index, row in enumerate(
                    db.execute(
                        "SELECT r.rowid,r.forecast,r.hit,r.resolved_at,r.body,f.strategy,f.version,f.issued,f.target,f.body FROM resolutions r JOIN forecasts f ON f.id=r.forecast ORDER BY r.rowid LIMIT ?",
                        (FORECAST_MAX_ROWS + 1,),
                    )
                ):
                    if index >= FORECAST_MAX_ROWS:
                        raise ForecastCoverageError(
                            "forecast_resolution_scan_budget_exceeded"
                        )
                    total_bytes += len(row[4].encode()) + len(row[9].encode())
                    if total_bytes > FORECAST_MAX_BYTES:
                        raise ForecastCoverageError(
                            "forecast_resolution_byte_budget_exceeded"
                        )
                    forecast_labels.append(excluded_oracle_forecast(scope, row))
            except (ForecastCoverageError, sqlite3.DataError) as exc:
                reason = (
                    str(exc)
                    if isinstance(exc, ForecastCoverageError)
                    else "forecast_resolution_body_budget_exceeded"
                )
                return {
                    "scope": scope,
                    "comparability": comparable,
                    "state": "unavailable",
                    "reason": reason,
                    "counts_complete": False,
                    "outcomes": None,
                    "resolved_comparable_labels": None,
                    "completed_trades": None,
                    "cohorts": {},
                    "forecast_ingestion": {"state": "unavailable", "reason": reason},
                }
            finally:
                db.close()
        outcomes.extend(forecast_labels)
        from botmanager.health import HealthStore

        for alert in HealthStore(Path(home)).page(bot_id=bot_id, limit=1000)["alerts"]:
            if alert["code"] in ("submission_unknown", "execution_failed"):
                outcomes.append(
                    (
                        comparable,
                        {
                            "id": fingerprint(["alert", bot_id, alert["sequence"]]),
                            "kind": "execution_fault",
                            "resolved": alert["state"] == "resolved",
                            "comparable": False,
                            "evidence": alert,
                        },
                    )
                )
        now = time.time()
        with self.connection(True) as db:
            for key, outcome in outcomes:
                label = classify_outcome(outcome)
                db.execute(
                    "INSERT OR IGNORE INTO learning_labels VALUES (?,?,?,?,?)",
                    (label["id"], scope, key, canonical(label), now),
                )
            labels = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT body FROM learning_labels WHERE scope=? AND comparable=?",
                    (scope, comparable),
                )
            ]
        # Excluded Oracle labels keep their own provenance key and never borrow
        # the active account's comparable identity or its eligibility counts.
        labels.extend(classify_outcome(label) for _, label in forecast_labels)
        return {
            "scope": scope,
            "comparability": comparable,
            "state": "available",
            "reason": None,
            "counts_complete": True,
            "forecast_ingestion": {
                "state": "ineligible" if forecast_labels else "not_observed",
                "reason": "oracle_manager_forecast_contract_unverified"
                if forecast_labels
                else "no_resolved_forecasts",
                "resolved_rows": len(forecast_labels),
            },
            **outcome_summary(labels),
        }

    def _evidence(self, run_id):
        if self.research_store is None:
            raise ValueError("research artifact reader unavailable")
        proposal = self.research_store.manager_read_artifact(run_id, "proposal")
        state = self.research_store.manager_status(run_id)
        if (
            not proposal
            or state["state"] != "finished"
            or state.get("outcome", {}).get("outcome") != "proposal_pending_shadow"
        ):
            raise ValueError("accepted M4 proposal required")
        if proposal["authority"]["roster_revision"] != fingerprint(
            self.registration
        ) or proposal["authority"][
            "history_revision"
        ] != self.research_store.manager_history_revision(exclude_run=run_id):
            raise ValueError("research authority evidence changed")
        final = self.research_store.manager_read_artifact(run_id, "final")
        training = self.research_store.manager_read_artifact(run_id, "training")
        if (
            not final
            or not training
            or not final["comparison"].get("accepted")
            or fingerprint(
                {"final": final["packet"], "comparison": final["comparison"]}
            )
            != proposal["evidence_digest"]
        ):
            raise ValueError("fresh-final evidence digest mismatch")
        from botmanager.blind import verify

        verify(training["packet"], training["verdict"])
        certified = all(
            cell.get("certified") is True
            for candidate in final["packet"]["candidates"]
            for cell in candidate["cells"]
        )
        return proposal, certified

    def propose(self, home, bot_id, run_id):
        summary = self.collect(home, bot_id)
        if summary.get("counts_complete") is False:
            raise ValueError(summary["reason"])
        if (
            summary["resolved_comparable_labels"] < 300
            or summary["completed_trades"] < 30
        ):
            raise ValueError(
                "300 resolved comparable labels AND 30 completed trades required"
            )
        spec, row = self._runtime(home, bot_id)
        evidence, certified = self._evidence(run_id)
        if (
            evidence["bot_id"] != spec.bot_id
            or evidence["baseline_hash"] != spec.config_hash
            or evidence["baseline_revision"] != spec.config_revision
            or evidence["pins"] != dict(spec.user_overrides)
        ):
            raise ValueError("proposal baseline or manual pins changed")
        learned_spec(spec, evidence["changes"], evidence["evidence_digest"])
        with self.research_store._connect() as research_db:
            raw = research_db.execute(
                "SELECT spec FROM runs WHERE id=?", (run_id,)
            ).fetchone()
        frozen = json.loads(raw[0])
        research_input = self.research_store.manager_read_artifact(run_id, "input")
        if not research_input or comparable_identity(
            {"input": research_input}
        ) != comparable_identity(row):
            raise ValueError(
                "research source, currency, costs or policy are incompatible"
            )
        if (
            frozen["context"]["bot_spec"]["config_hash"] != spec.config_hash
            or frozen["context"]["engine_identity"]
            != row["input"]["identity"]["engine_identity"]
        ):
            raise ValueError("research configuration or engine is incompatible")
        now = time.time()
        day = datetime.fromtimestamp(now, UTC).date().isoformat()
        body = {
            "version": 1,
            "id": evidence["request_id"],
            "scope": summary["scope"],
            "day": day,
            "home": str(Path(home).resolve()),
            "bot_id": bot_id,
            "runtime_id": row["runtime_id"],
            "baseline": spec.to_dict(),
            "changes": evidence["changes"],
            "pins": dict(spec.user_overrides),
            "evidence": evidence,
            "certified": certified,
            "counts": summary,
            "comparability": summary["comparability"],
            "created_at": now,
            "state": "pending_shadow",
            "shadow": None,
            "adoption": None,
            "rollback": None,
        }
        with self.connection(True) as db:
            old = db.execute(
                "SELECT body FROM learning_proposals WHERE scope=? AND day=?",
                (summary["scope"], day),
            ).fetchone()
            if old:
                existing = json.loads(old[0])
                if existing["id"] == body["id"]:
                    return existing
                raise ValueError("daily canonical-scope proposal already consumed")
            db.execute(
                "INSERT INTO learning_proposals VALUES (?,?,?,?)",
                (body["id"], body["scope"], day, canonical(body)),
            )
        return body

    def inspect(self, proposal_id):
        with self.connection() as db:
            if not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_proposals'"
            ).fetchone():
                return {"proposal": None, "reason": "learning_not_initialized"}
            proposal = self._read_proposal(db, proposal_id)
            cooldown = db.execute(
                "SELECT reserved FROM learning_cooldowns WHERE scope=?",
                (proposal["scope"],),
            ).fetchone()
        gates = self._gates(proposal, cooldown[0] if cooldown else None)
        return {"proposal": proposal, "gates": gates, "eligible": not gates}

    def start_shadow(self, proposal_id):
        now = time.time()
        with self.connection(True) as db:
            proposal = self._read_proposal(db, proposal_id)
            if (
                proposal["shadow"] is not None
                and proposal["shadow"]["runs"] is not None
            ):
                return proposal
            if proposal["shadow"] is None:
                proposal["shadow"] = {
                    "started_at": now,
                    "pair_ids": {
                        role: str(uuid4()) for role in ("incumbent", "challenger")
                    },
                    "runs": None,
                }
                self._save(db, proposal)
        # Durable IDs precede worker creation. A crash reuses the same accounts.
        baseline, active = self._runtime(proposal["home"], proposal["bot_id"])
        if (
            baseline.config_hash != proposal["baseline"]["config_hash"]
            or active["runtime_id"] != proposal["runtime_id"]
            or comparable_identity(active) != proposal["comparability"]
        ):
            raise ValueError(
                "shadow originating runtime or input compatibility changed"
            )
        runs = shadow_pair(
            Path(proposal["home"]),
            BotSpec.from_dict(proposal["baseline"]),
            proposal["changes"],
            proposal["evidence"]["evidence_digest"],
            proposal["shadow"]["pair_ids"],
        )
        if (
            len({run["comparability"] for run in runs}) != 1
            or len({run["immutable_input"] for run in runs}) != 1
        ):
            raise ValueError("shadow sources or activation contracts are incompatible")
        with self.connection(True) as db:
            current = self._read_proposal(db, proposal_id)
            current["shadow"]["started_at"] = time.time()
            current["shadow"]["runs"] = runs
            current["state"] = "shadow_running"
            self._save(db, current)
            return current

    def _shadow_progress(self, proposal):
        from botmanager.health import health_snapshot
        from botmanager.ledger import RuntimeLedger

        shadow = proposal["shadow"]
        if not shadow or not shadow["runs"]:
            return {"complete": False, "reason": "shadow_not_started", "trades": 0}
        if (
            len(shadow["runs"]) != 2
            or {run.get("role") for run in shadow["runs"]}
            != {"incumbent", "challenger"}
            or len({run.get("immutable_input") for run in shadow["runs"]}) != 1
        ):
            return {"complete": False, "reason": "shadow_binding_changed", "trades": 0}
        baseline = BotSpec.from_dict(proposal["baseline"])
        expected_configs = {
            "incumbent": baseline.config_hash,
            "challenger": learned_spec(
                baseline, proposal["changes"], proposal["evidence"]["evidence_digest"]
            ).config_hash,
        }
        ledger = RuntimeLedger(Path(proposal["home"]))
        states = []
        for binding in shadow["runs"]:
            run = ledger.get(binding["bot_id"])
            if (
                not run
                or run["runtime_id"] != binding["runtime_id"]
                or comparable_identity(run) != binding["comparability"]
                or binding.get("config_hash") != expected_configs[binding["role"]]
                or run["spec"]["config_hash"] != binding.get("config_hash")
                or run["input"].get("origin_hash", run["input"]["snapshot_hash"])
                != binding.get("input_hash")
                or shadow_input_binding(run) != binding.get("immutable_input")
                or run["input"].get("prospective") is None
            ):
                return {
                    "complete": False,
                    "reason": "shadow_binding_changed",
                    "trades": 0,
                }
            labels = self._all_runtime_labels(ledger, run)
            completed = [
                label for label in labels if classify_outcome(label)["completed_trade"]
            ]
            cp = run.get("checkpoint") or {}
            health = health_snapshot(run, now=time.time())
            inputs = [run["input"]]
            with ledger.connection() as runtime_db:
                first_evaluation = runtime_db.execute(
                    "SELECT min(at) FROM events WHERE runtime_id=? AND cursor>0 AND kind IN ('prospective.committed','tick.committed')",
                    (run["runtime_id"],),
                ).fetchone()[0]
                if runtime_db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='segments'"
                ).fetchone():
                    inputs.extend(
                        json.loads(segment[0])["input"]
                        for segment in runtime_db.execute(
                            "SELECT body FROM segments WHERE runtime_id=?",
                            (run["runtime_id"],),
                        )
                    )
            first_observed = min(
                (data["bars"][0]["ts"] for data in inputs if data["bars"]), default=None
            )
            deliveries = [
                period
                for data in inputs
                for period in data.get("prospective", {}).get("evaluation_ranges", [])
            ]
            states.append(
                {
                    "binding": binding,
                    "first_evaluated_at": first_evaluation,
                    "first_observed_at": first_observed,
                    "deliveries": deliveries,
                    "run": run,
                    "trades": len(completed),
                    "health": health,
                    "net_pnl": cp.get("equity_quote", 0)
                    - run["input"]["descriptor"]["capital_quote"]
                    if cp.get("equity_quote") is not None
                    else None,
                }
            )
        return {
            "complete": True,
            "reason": None,
            "trades": min(state["trades"] for state in states),
            "states": states,
        }

    def _gates(self, proposal, cooldown):
        gates = []
        now = time.time()
        baseline = BotSpec.from_dict(proposal["baseline"])
        try:
            current, row = self._runtime(proposal["home"], proposal["bot_id"])
            if (
                current.config_hash != baseline.config_hash
                or dict(current.user_overrides) != proposal["pins"]
                or row["runtime_id"] != proposal["runtime_id"]
            ):
                gates.append("originating_revision_or_pins_changed")
        except (ValueError, ManagerError):
            gates.append("originating_runtime_unavailable")
        try:
            evidence, certified = self._evidence(proposal["evidence"]["run_id"])
            if evidence != proposal["evidence"] or not certified:
                gates.append("certified_fresh_final_required")
        except (ValueError, ManagerError):
            gates.append("certified_fresh_final_required")
        if (
            not proposal["certified"]
            or proposal["evidence"].get("production_eligible") is not True
        ):
            gates.append("certified_production_evidence_required")
        shadow = proposal["shadow"]
        if not shadow or now - shadow["started_at"] < 7 * DAY:
            gates.append("seven_actual_calendar_days_required")
        progress = self._shadow_progress(proposal)
        if not progress["complete"]:
            gates.append(progress["reason"])
        elif progress["trades"] < 30:
            gates.append("thirty_comparable_shadow_trades_required")
        if progress["complete"]:
            for state in progress["states"]:
                if (
                    state["health"]["blockers"]
                    or state["run"]["tick_started"] is not None
                ):
                    gates.append("shadow_reconciliation_unhealthy")
            if any(
                state.get("first_evaluated_at") is None
                or now - state["first_evaluated_at"] < 7 * DAY
                for state in progress["states"]
            ):
                gates.append("seven_days_since_first_actual_worker_evaluation_required")
            if any(
                state.get("first_observed_at") is None
                or (state["run"].get("checkpoint") or {}).get("last_bar_ts", 0)
                - state["first_observed_at"]
                < 7 * DAY
                for state in progress["states"]
            ):
                gates.append("seven_days_of_prospective_observations_required")
            if any(
                not state.get("deliveries")
                or any(
                    period.get("delivery") != "prospective_reference"
                    for period in state["deliveries"]
                )
                for state in progress["states"]
            ):
                gates.append("historical_or_delayed_shadow_delivery")
            if (
                len(
                    {
                        (state["run"].get("checkpoint") or {}).get("last_bar_ts")
                        for state in progress["states"]
                    }
                )
                != 1
            ):
                gates.append("shadow_comparison_clock_mismatch")
            a, b = progress["states"]
            if (
                a["net_pnl"] is None
                or b["net_pnl"] is None
                or b["net_pnl"] <= a["net_pnl"]
            ):
                gates.append("shadow_has_no_comparable_net_advantage")
            # Current feed explicitly has no independently certified execution.
            if any(
                state["run"]["input"]["identity"].get("venue_compatibility_verified")
                is not True
                for state in progress["states"]
            ):
                gates.append("shadow_source_uncertified")
        if cooldown is not None and now - cooldown < COOLDOWN:
            gates.append("promotion_48h_cooldown")
        return sorted(set(gates))

    def authorize(self, proposal_id, operation, request_id):
        from uuid import UUID

        if (
            operation not in ("promote", "rollback")
            or str(UUID(request_id)) != request_id
        ):
            raise ValueError("valid transition operation and UUID required")
        with self.connection(True) as db:
            old = db.execute(
                "SELECT * FROM learning_requests WHERE request_id=?", (request_id,)
            ).fetchone()
            if old:
                if old["proposal_id"] != proposal_id or old["operation"] != operation:
                    raise ValueError("learning request identity conflict")
                retained = json.loads(old["body"])
                proposal = self._read_proposal(db, proposal_id)
                if retained.get("manager_home") != proposal["home"]:
                    raise ValueError(
                        "legacy authorization manager-home binding unavailable"
                    )
                return retained
            proposal = self._read_proposal(db, proposal_id)
            cooldown = db.execute(
                "SELECT reserved FROM learning_cooldowns WHERE scope=?",
                (proposal["scope"],),
            ).fetchone()
            if operation == "promote":
                gates = self._gates(proposal, cooldown[0] if cooldown else None)
                baseline = BotSpec.from_dict(proposal["baseline"])
                changes = proposal["changes"]
            else:
                if proposal["adoption"] is None:
                    raise ValueError("rollback requires reconciled prior adoption")
                baseline, row = self._runtime(proposal["home"], proposal["bot_id"])
                adopted = proposal["adoption"]["manager_receipt"]
                if (
                    baseline.config_hash != adopted["accepted_hash"]
                    or row["runtime_id"] != proposal["runtime_id"]
                ):
                    raise ValueError("rollback origin changed")
                changes = {
                    key: proposal["baseline"]["resolved_values"][key]
                    for key in proposal["changes"]
                }
                gates = [
                    gate
                    for gate in self._gates(proposal, cooldown[0] if cooldown else None)
                    if gate != "originating_revision_or_pins_changed"
                ]
                # Same evidence, clocks, counts, cooldown, safe boundary and risk rules.
                try:
                    evidence, certified = self._evidence(proposal["evidence"]["run_id"])
                    if evidence != proposal["evidence"] or not certified:
                        gates.append("certified_fresh_final_required")
                except (ValueError, ManagerError):
                    gates.append("certified_fresh_final_required")
                if (
                    not proposal["certified"]
                    or proposal["evidence"].get("production_eligible") is not True
                ):
                    gates.append("certified_production_evidence_required")
                if cooldown is not None and time.time() - cooldown[0] < COOLDOWN:
                    gates.append("promotion_48h_cooldown")
            if gates:
                raise ValueError("learning transition blocked: " + ",".join(gates))
            proposed = learned_spec(
                baseline, changes, proposal["evidence"]["evidence_digest"]
            )
            receipt = {
                "version": 1,
                "request_id": request_id,
                "proposal_id": proposal_id,
                "operation": operation,
                "manager_home": proposal["home"],
                "scope": proposal["scope"],
                "bot_id": proposal["bot_id"],
                "runtime_id": proposal["runtime_id"],
                "expected_revision": baseline.config_revision,
                "expected_hash": baseline.config_hash,
                "pins": dict(baseline.user_overrides),
                "changes": changes,
                "accepted_spec": proposed.to_dict(),
                "evidence_digest": proposal["evidence"]["evidence_digest"],
                "authority": {
                    "root": str(self.root),
                    "namespace_id": self.registration["namespace_id"],
                },
                "authorized_at": time.time(),
                "state": "authorized_pending_manager",
                "safe_to_retry": False,
            }
            receipt["digest"] = fingerprint(receipt)
            db.execute(
                "INSERT INTO learning_requests VALUES (?,?,?,?,NULL)",
                (request_id, proposal_id, operation, canonical(receipt)),
            )
            db.execute(
                "INSERT OR REPLACE INTO learning_cooldowns VALUES (?,?)",
                (proposal["scope"], receipt["authorized_at"]),
            )
            return receipt

    def reconcile(self, proposal_id, request_id, manager_receipt):
        with self.connection(True) as db:
            row = db.execute(
                "SELECT * FROM learning_requests WHERE request_id=? AND proposal_id=?",
                (request_id, proposal_id),
            ).fetchone()
            if row is None:
                raise ValueError("owner authorization receipt missing")
            receipt = json.loads(row["body"])
            proposal = self._read_proposal(db, proposal_id)
            manager_path = Path(proposal["home"]) / "runtime.sqlite3"
            local_db = sqlite3.connect(
                manager_path.as_uri() + "?mode=ro", uri=True, timeout=1
            )
            try:
                local_db.execute("PRAGMA query_only=ON")
                local = local_db.execute(
                    "SELECT owner_digest,body FROM learning_adoptions WHERE request_id=?",
                    (request_id,),
                ).fetchone()
            finally:
                local_db.close()
            if (
                local is None
                or local[0] != receipt["digest"]
                or json.loads(local[1]) != manager_receipt
            ):
                raise ValueError(
                    "manager publication is not present in the bound local journal"
                )
            if (
                manager_receipt.get("request_id") != request_id
                or manager_receipt.get("owner_receipt_digest") != receipt["digest"]
                or manager_receipt.get("accepted_hash")
                != receipt["accepted_spec"]["config_hash"]
            ):
                raise ValueError("manager publication receipt binding mismatch")
            if (
                row["manager_receipt"] is not None
                and json.loads(row["manager_receipt"]) != manager_receipt
            ):
                raise ValueError("manager receipt replay conflict")
            proposal = self._read_proposal(db, proposal_id)
            proposal["adoption" if row["operation"] == "promote" else "rollback"] = {
                "owner_receipt": receipt,
                "manager_receipt": manager_receipt,
            }
            proposal["state"] = (
                "adopted" if row["operation"] == "promote" else "rolled_back"
            )
            self._save(db, proposal)
            db.execute(
                "UPDATE learning_requests SET manager_receipt=? WHERE request_id=?",
                (canonical(manager_receipt), request_id),
            )
            db.execute(
                "INSERT OR REPLACE INTO learned_defaults VALUES (?,?,?)",
                (proposal["scope"], canonical(receipt["changes"]), canonical(receipt)),
            )
            return {
                "proposal_id": proposal_id,
                "state": proposal["state"],
                "receipt": manager_receipt,
            }
