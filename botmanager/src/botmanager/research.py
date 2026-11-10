"""Offline canonical replay and preregistered manager research protocol 2.

The existing ExperimentStore owns temporal exposure, attempts and trials. This
module never opens an owner database and never edits a strategy configuration.
"""

from __future__ import annotations

import copy
import itertools
import math
import random
import statistics
from uuid import uuid4

from .blind import resolve_tie, run_judge
from .blind_judge import POLICY, decide
from .domain import BotSpec, ManagerError, fingerprint


def partition(count, *, horizon, warmup, blocks=10):
    if (
        any(type(v) is not int for v in (count, horizon, warmup, blocks))
        or horizon < 1
        or warmup < 0
        or not 10 <= blocks <= 15
    ):
        raise ValueError("invalid chronological geometry")
    edges = (0, count // 2, count * 3 // 4, count)
    result = {}
    for i, name in enumerate(("train", "validation", "holdout")):
        start = edges[i] + (horizon if i else 0)
        stop = edges[i + 1] - (horizon if i < 2 else 0)
        width = (stop - start) // blocks
        if width - horizon < warmup + 2:
            raise ValueError(
                "insufficient evidence: warmup, purge and independent blocks"
            )
        result[name] = [
            (
                start + j * width,
                stop if j == blocks - 1 else start + (j + 1) * width - horizon,
            )
            for j in range(blocks)
        ]
    return result


def candidate_spec(spec, changes):
    from .config import DEFAULTS, validate_values

    if not isinstance(changes, dict) or not set(changes) <= set(
        DEFAULTS[spec.strategy_id]
    ):
        raise ValueError("search may change strategy parameters only")
    if set(changes) & set(spec.user_overrides):
        raise ValueError("search cannot change manual pins")
    raw = spec.to_dict()
    raw["resolved_values"].update(changes)
    validate_values(spec.strategy_id, raw["resolved_values"])
    # Simulation candidates retain the baseline revision and pins. They are not
    # saved manual edits or promoted configurations.
    for key in changes:
        raw["provenance"][key] = {
            "source": "context",
            "source_revision": "research-proposal-v2",
            "reason": "unadopted simulation candidate;"
            + spec.shared_compatibility["reason"],
        }
    raw["config_hash"] = fingerprint({key: raw[key] for key in spec._config_body()})
    return BotSpec.from_dict(raw)


def candidates(spec, ranges, *, max_configurations=32):
    if not isinstance(ranges, dict) or len(ranges) > 8:
        raise ValueError("invalid search ranges or budget")
    if any(not isinstance(v, list) or not v or len(v) > 32 for v in ranges.values()):
        raise ValueError("invalid search ranges or budget")
    count = math.prod(len(v) for v in ranges.values())
    if count + 1 > max_configurations:
        raise ValueError("configuration budget exceeded")
    result = [{}]
    for values in itertools.product(*(ranges[k] for k in sorted(ranges))):
        changes = dict(zip(sorted(ranges), values, strict=True))
        candidate_spec(spec, changes)
        if (
            changes
            and any(spec.resolved_values[k] != v for k, v in changes.items())
            and changes not in result
        ):
            result.append(changes)
    return result


def feature_horizon(spec, parameters):
    return max(
        [1]
        + [
            int(c.get(key, spec.resolved_values.get(key, 1)))
            for c in parameters
            for key in ("window", "slow_period")
        ]
    )


def default_plan(spec):
    """A small validated neighboring search; no claim of position independence."""
    keys = {
        "grid": ("rungs", "deadband_bps", "range_pct"),
        "dca": ("take_profit_pct", "price_deviation_pct", "cooldown_bars"),
        "trend": ("entry_buffer_bps", "fast_period"),
        "momentum": ("threshold", "window"),
    }.get(spec.strategy_id, ())
    ranges = {}
    for key in keys:
        if key in spec.user_overrides:
            continue
        value = spec.resolved_values[key]
        step = 1 if type(value) is int else (abs(value) * 0.1 or 0.001)
        values = []
        for proposed in (value - step, value + step):
            if key == "rungs" and proposed > 100:
                continue
            try:
                candidate_spec(spec, {key: proposed})
            except ManagerError:
                continue
            values.append(proposed)
        if values:
            ranges = {key: values}
            break
    if not ranges:
        raise ManagerError(
            "research_unavailable",
            "No supported unpinned tunable remains for a default research plan.",
            3,
        )
    horizon = feature_horizon(spec, candidates(spec, ranges))
    return {
        "ranges": ranges,
        "horizon_bars": horizon,
        "warmup_bars": horizon,
        "blocks": 10,
        "confidence": {"method": "block_bootstrap", "seed": 0, "minimum_blocks": 10},
    }


def backtest(spec, data):
    from .strategies import evaluate

    result = evaluate(spec, data, len(data["bars"]), research=True)
    return {
        "schema_version": 2,
        "input_hash": data["snapshot_hash"],
        "config_hash": spec.config_hash,
        "metrics": result["research_metrics"],
        "certified": False,
        "reason": "reference_simulation_not_certified_jupiter_execution",
        "independence": {
            "supported": False,
            "reason": "unbounded_position_horizon; feature purge does not prove trade independence",
        },
        "open_lots": len(result["lots"]),
        "pending_targets": result.get("pending_targets"),
        "realized_net_pnl_quote": result["realized_net_pnl_quote"],
        "unrealized_net_pnl_quote": result["unrealized_net_pnl_quote"],
        "quote_currency": result["quote_currency"],
    }


def final_comparison(incumbent, challenger, *, ordinal, confidence):
    alpha = 0.05 / (ordinal * (ordinal + 1))
    result = {
        "accepted": False,
        "reason": "insufficient_evidence",
        "alpha": alpha,
        "ordinal": ordinal,
        "sign_test": "descriptive"
        if confidence["method"] == "block_bootstrap"
        else "independent_fixture_blocks",
    }
    if not incumbent or {c["block"] for c in incumbent} != {
        c["block"] for c in challenger
    }:
        return result
    # Eligibility and alignment use the exact same preregistered judge policy.
    packet = {
        "version": 2,
        "policy": POLICY,
        "candidates": [
            {"id": "a" * 32, "cells": incumbent},
            {"id": "b" * 32, "cells": challenger},
        ],
    }
    try:
        eligible = decide(packet)
    except ValueError:
        return result
    if eligible["rejected_ids"]:
        return {**result, "reason": "uncertified_costs_coverage_trades_or_drawdown"}
    left = {c["block"]: c for c in incumbent}
    deltas = [
        c["net_return"] - left[c["block"]]["net_return"]
        for c in sorted(challenger, key=lambda c: c["block"])
    ]
    decided = [v for v in deltas if v != 0]
    if len(decided) < confidence["minimum_blocks"]:
        return result
    positive = sum(v > 0 for v in decided)
    p = sum(
        math.comb(len(decided), k) for k in range(positive, len(decided) + 1)
    ) / 2 ** len(decided)
    median = statistics.median(deltas)
    if confidence["method"] == "independent_sign":
        gate = p <= alpha
        lower = None
    elif confidence["method"] == "block_bootstrap":
        if alpha * 10000 < 1:
            return {**result, "reason": "insufficient_confidence_resolution"}
        rng = random.Random(confidence["seed"])
        # Resample chronological groups, never correlated asset rows as trials.
        sampled = sorted(
            statistics.median(rng.choices(deltas, k=len(deltas))) for _ in range(10000)
        )
        lower = sampled[max(0, int(alpha * len(sampled)) - 1)]
        gate = lower > 0
    else:
        return {**result, "reason": "unsupported_confidence_policy"}
    accepted = median > 0 and gate
    return {
        **result,
        "accepted": accepted,
        "reason": "fresh_final_passed" if accepted else "retained_incumbent",
        "median_improvement": median,
        "decided_blocks": len(decided),
        "sign_p_value": p,
        "block_lower_bound": lower,
    }


def _slice(data, start, end, *, stress=False):
    body = copy.deepcopy(data)
    body.pop("snapshot_hash", None)
    body["bars"] = body["bars"][start:end]
    body["origin_hash"] = data["snapshot_hash"]
    if stress:
        for key in ("fee_bps", "slippage_bps", "carry_bps_per_hour"):
            body["descriptor"][key] *= 2
    body["snapshot_hash"] = fingerprint(body)
    return body


def execute(
    store,
    spec,
    data,
    options,
    *,
    judge=run_judge,
    evaluator=backtest,
    cancelled=lambda: False,
    authority_context=None,
):
    """Trusted owner orchestration. Test evaluator injection is not a wire API."""
    if set(options) != {
        "ranges",
        "horizon_bars",
        "warmup_bars",
        "blocks",
        "confidence",
    }:
        raise ValueError(
            "research options must freeze all geometry and confidence fields"
        )
    if options["confidence"] != {
        "method": "block_bootstrap",
        "seed": 0,
        "minimum_blocks": 10,
    }:
        raise ValueError("unsupported independence: use preregistered block bootstrap")
    authority_context = authority_context or {
        "namespace_id": "controlled-test-fixture",
        "isolation_mode": "isolated",
        "coverage": "registered_roots_only",
        "roster_revision": "controlled-test-fixture",
    }
    parameters = candidates(spec, options["ranges"])
    feature = feature_horizon(spec, parameters)
    if options["horizon_bars"] < feature or options["warmup_bars"] < feature:
        raise ValueError("insufficient horizon or feature warmup")
    geometry = partition(
        len(data["bars"]),
        horizon=options["horizon_bars"],
        warmup=options["warmup_bars"],
        blocks=options["blocks"],
    )
    if 2 * options["blocks"] * (len(parameters) + 4) > 1000:
        raise ValueError("preregistered allocation exceeds cell budget")
    opaque = [uuid4().hex for _ in parameters]
    mapping = dict(zip(opaque, parameters, strict=True))
    intervals = {
        name: [
            {
                "coin": "SOL",
                "start": data["bars"][a]["ts"],
                "end": data["bars"][b - 1]["ts"] + spec.bar_seconds,
            }
            for a, b in cells
        ]
        for name, cells in geometry.items()
    }
    frozen = {
        "protocol_version": 2,
        "source": "native",
        "bot": spec.strategy_id,
        "incumbent_id": opaque[0],
        "scope": {
            "family": spec.strategy_id,
            "coin": "SOL",
            "base_mint": spec.base_mint,
            "quote_mint": spec.quote_mint,
            "bar_seconds": spec.bar_seconds,
            "execution_model": spec.execution_model,
        },
        "context": {
            "authority": authority_context,
            "bot_spec": spec.to_dict(),
            "input_hash": data["snapshot_hash"],
            "engine_identity": data["identity"]["engine_identity"],
            "geometry_indices": geometry,
            "options": options,
        },
        "candidates": [
            {"id": cid, "config": changes} for cid, changes in mapping.items()
        ],
        "budget": {"configurations": 32, "cells": 1000},
        "geometry": intervals,
        "policy": POLICY,
        "confidence": options["confidence"],
        "search": options["ranges"],
        "owner_identity": __import__(
            "soltui.research_admission", fromlist=["source_identity"]
        ).source_identity(),
    }
    created = store.manager_create(frozen)
    run_id = created["run_id"]
    store.manager_artifact(run_id, "input", data)
    store.manager_artifact(run_id, "mapping", mapping)
    spent = False

    def evaluate_split(split, ids):
        if split != "holdout":
            store.manager_expose(run_id, split)
        rows = []
        for cid in ids:
            cells = []
            candidate = candidate_spec(spec, mapping[cid])
            for block, (start, end) in enumerate(geometry[split]):
                if cancelled():
                    raise ValueError("cancelled")
                reports = []
                for stress in (False, True):
                    ticket = store.manager_trial(
                        run_id, cid, split, block * 2 + int(stress)
                    )
                    try:
                        report = evaluator(
                            candidate, _slice(data, start, end, stress=stress)
                        )
                    except BaseException:
                        store.manager_trial_result(
                            run_id,
                            ticket,
                            {"status": "failed", "reason": "evaluation_failed"},
                        )
                        raise
                    store.manager_trial_result(
                        run_id, ticket, {"status": "completed", "report": report}
                    )
                    reports.append(report)
                normal, stress = reports
                cells.append(
                    {
                        "block": block,
                        **normal["metrics"],
                        "coverage": True,
                        "certified": normal["certified"] and stress["certified"],
                        "cost_stress": stress["metrics"]["net_return"] >= 0,
                    }
                )
            rows.append({"id": cid, "cells": cells})
        return {"version": 2, "policy": POLICY, "candidates": rows}

    try:
        training = evaluate_split("train", opaque)
        verdict = judge(training)
        store.manager_artifact(
            run_id, "training", {"packet": training, "verdict": verdict}
        )
        challenger = resolve_tie(verdict, opaque[0])
        if challenger in (None, opaque[0]):
            return store.manager_finish(
                run_id,
                {
                    "outcome": "retained_incumbent",
                    "reason": "uncertified_reference_evidence"
                    if any(
                        not cell["certified"]
                        for row in training["candidates"]
                        for cell in row["cells"]
                    )
                    else "training_no_eligible_challenger",
                    "proposal": None,
                },
            )
        finalists = store.manager_finalists(
            run_id, {"packet": training, "verdict": verdict}
        )
        validation = evaluate_split("validation", finalists)
        verdict = judge(validation)
        if resolve_tie(verdict, opaque[0]) != challenger:
            return store.manager_finish(
                run_id,
                {
                    "outcome": "retained_incumbent",
                    "reason": "validation_no_eligible_challenger",
                    "proposal": None,
                },
            )
        store.manager_freeze(
            run_id, challenger, {"packet": validation, "verdict": verdict}
        )
        # A process crash after this call permanently spends the final. A new
        # invocation may read its receipts, but cannot execute these cells again.
        store.manager_unseal(run_id)
        spent = True
        final = evaluate_split("holdout", [opaque[0], challenger])
        comparison = final_comparison(
            final["candidates"][0]["cells"],
            final["candidates"][1]["cells"],
            ordinal=created["ordinal"],
            confidence=options["confidence"],
        )
        store.manager_artifact(
            run_id, "final", {"packet": final, "comparison": comparison}
        )
        proposal = None
        if comparison["accepted"]:
            proposal = {
                "version": 2,
                "authority": {
                    **authority_context,
                    "history_revision": store.manager_history_revision(
                        exclude_run=run_id
                    ),
                    "scoped_fresh": True,
                },
                "production_eligible": authority_context["isolation_mode"]
                == "registered_clients",
                "request_id": str(uuid4()),
                "run_id": run_id,
                "bot_id": spec.bot_id,
                "baseline_revision": spec.config_revision,
                "baseline_hash": spec.config_hash,
                "pins": dict(spec.user_overrides),
                "changes": mapping[challenger],
                "evidence_digest": fingerprint(
                    {"final": final, "comparison": comparison}
                ),
                "state": "pending_shadow",
                "automatic_promotion": False,
                "reason": "requires_7_calendar_days_and_30_prospective_paper_trades",
            }
            store.manager_artifact(run_id, "proposal", proposal)
        return store.manager_finish(
            run_id,
            {
                "outcome": "proposal_pending_shadow"
                if proposal
                else "retained_incumbent",
                "reason": comparison["reason"],
                "comparison": comparison,
                "proposal": proposal,
            },
        )
    except BaseException as exc:
        # Sanitized reasons retain control state without logging paths or inputs.
        reason = (
            "cancelled" if str(exc) == "cancelled" else "evaluation_or_admission_failed"
        )
        store.manager_finish(
            run_id,
            {
                "outcome": "retained_incumbent",
                "reason": reason,
                "final_spent": spent,
                "proposal": None,
            },
        )
        raise


def reconcile_proposal(manager_store, owner, run_id):
    response = owner.call("proposal", {"run_id": run_id})
    proposal = response["proposal"]
    if response.get("reconcilable") is not True:
        raise ManagerError(
            "research_scope_changed",
            "Proposal evidence is stale or unavailable; immutable evidence remains inspectable.",
            3,
        )
    if proposal is None:
        raise ManagerError("research_unavailable", "No accepted research proposal.", 3)
    receipt = manager_store.record_research_proposal(proposal)
    owner.call("receipt", {"run_id": run_id, "receipt": receipt})
    return receipt
