"""Evaluate the completed frozen cohort from native-archived local transport."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research.exit50_backtest import select_policy
from research.exit50_run import (
    btc_taker_filter,
    paired_baseline,
    run_scenarios,
    study_candidates,
    summarize_paired,
)
from research.reversal_history import canonical, pack


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", choices=("BTC", "ZEC"), required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--entry-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--models", required=True)
    parser.add_argument("--flow")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plan_bytes = Path(args.plan).read_bytes()
    plan = json.loads(plan_bytes)
    model_bytes = Path(args.models).read_bytes()
    bundle = json.loads(model_bytes)
    if (
        plan.get("asset") != args.asset
        or plan.get("all_needed_count") != 0
        or plan.get("selected_slots")
        or plan.get("model_sha256") != hashlib.sha256(model_bytes).hexdigest()
        or any(c.get("state") not in ("terminal", "unscored") for c in plan["cases"])
    ):
        raise ValueError("cohort_source_proof_incomplete")
    prepared, candidates = study_candidates(args.asset, args.entry_root, bundle)
    if (
        len(candidates) != plan["candidate_count"]
        or len(plan["cases"]) != len(candidates) * 12
    ):
        raise ValueError("cohort_census_mismatch")
    flow = None
    if args.asset == "BTC" and not args.flow:
        raise ValueError("btc_taker_flow_input_required")
    if args.flow:
        if args.asset != "BTC":
            raise ValueError("flow_only_qualified_for_btc")
        flow_bytes = Path(args.flow).read_bytes()
        if (
            hashlib.sha256(flow_bytes).hexdigest()
            != "f72189e3cc1d6c807f97280578bc014197cdde49d53aa87bfdd6be8351ffb2b0"
        ):
            raise ValueError("btc_taker_flow_hash_mismatch")
        flow = btc_taker_filter(json.loads(flow_bytes))
        for c in candidates:
            c["taker_flow_available"] = c["decision_s"] in flow
            c["taker_flow_negative"] = flow.get(c["decision_s"])
    variants = run_scenarios(
        args.asset, prepared, candidates, args.entry_root, args.cache_root, flow
    )
    selected = select_policy(variants)
    chosen = next(v for v in variants if v["id"] == selected["id"])
    paired = paired_baseline(
        args.asset,
        prepared,
        candidates,
        chosen["records"],
        args.entry_root,
        args.cache_root,
        10,
    )
    comparisons = {
        s: summarize_paired(
            [x for x in chosen["records"] if x["split"] == s],
            [x for x in paired if x["split"] == s],
        )
        for s in ("train", "validation", "test")
    }
    value = {
        "schema": "exit50-study-result/v1",
        "asset": args.asset,
        "qualification": "exploratory retrospective; observed 200ms grid plus qualified 1m no-touch envelopes; intragrid path and keeper-consumed updates censored; historical fees/fills/keeper path/entry and network costs unqualified; oracle-price counterfactual, no profitable-edge claim",
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "complete_plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "candidates": candidates,
        "variants": variants,
        "selected": selected,
        "selected_paired_baseline": paired,
        "selected_paired_comparisons": comparisons,
    }
    Path(args.output).write_text(canonical(pack(value)) + "\n")
    print(
        canonical(
            {
                "asset": args.asset,
                "candidates": len(candidates),
                "variants": len(variants),
                "selected": selected,
                "output_sha256": hashlib.sha256(
                    Path(args.output).read_bytes()
                ).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
