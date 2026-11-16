"""Render an auditable report from completed, archived exit50 result packs."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from research.exit50_run import policy_bundle
from research.reversal_history import canonical, read_archive


def pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def line(name, m, eligible=None):
    denominator = str(eligible) if eligible is not None else "n/a"
    attempted = m.get("attempted", m["n"] + m["unscored"])
    return f"| {name} | {denominator} | {attempted} | {m['n']} | {m['unscored']} | {m['target_touched']} | {m['target_filled']} | {m['liquidated']} | {pct(m['mean_roe'])} |"


def eligible_count(candidates, family, filter_name, split):
    total = 0
    for c in candidates:
        if c["family"] != family or c["split"] != split:
            continue
        if filter_name != "none" and not c["signal"]["shape_filter"]:
            continue
        if filter_name == "shape_bop" and not c["signal"]["bop_filter"]:
            continue
        if filter_name == "shape_flow" and c.get("taker_flow_negative") is not True:
            continue
        total += 1
    return total


def render_report(results, model_sha, source_ids, l2=None, l2_id=None):
    variants_by_asset = {asset: results[asset]["variants"] for asset in ("BTC", "ZEC")}
    policies = policy_bundle(model_sha, variants_by_asset)
    lines = [
        "# BTC and ZEC 10-minute exit50 retrospective",
        "",
        "This is an exploratory retrospective: the historical period and earlier shape tables were already seen. The splits do not create an independent holdout. The 200 ms observations and 1-minute no-touch envelopes do not prove a continuous keeper path. Current fee configuration is a scenario, not verified historical fees. Entry, network and keeper costs and actual fills are not qualified.",
        "",
        "The paper model uses 10 JupUSD collateral, 1000x notional, fee-aware exact integer liquidation and the frontend payout formula. The first target or completed-minute EMA/MACD exit intent latches; close submission waits at least 15 seconds since entry, then the main scenario assumes 10 seconds to close. Liquidation has priority through the simulated close. A filled 50% target means the modeled payout is at least 1.5 times collateral; it is not a real venue fill.",
        "",
        "The selector ranks each asset independently by validation modeled trade-fee-only mean ROE, requires at least 30 scored validation entries, and uses count then stable ID for ties. Only target+momentum, 10-second delay, and live-available shape or shape+BOP filters qualify; fallback is explicitly experimental. Final-test outcomes do not select. All returns exclude unverified entry/network/keeper costs.",
        "",
    ]
    for asset in ("BTC", "ZEC"):
        result = results[asset]
        if result["asset"] != asset or result["model_sha256"] != model_sha:
            raise ValueError("result_model_or_asset_mismatch")
        selected = result["selected"]
        policy = policies["assets"][asset]
        if selected["id"] != policy["id"]:
            raise ValueError("selection_reproduction_mismatch")
        winner = next(v for v in result["variants"] if v["id"] == selected["id"])
        baseline = next(
            v
            for v in result["variants"]
            if v["family"] == selected["family"]
            and v["filter"] == "none"
            and v["exit"] == "fixed"
            and v["delay_seconds"] == 10
        )
        lines += [
            f"## {asset}",
            "",
            f"Frozen policy: `{selected['id']}` ({policy['selection_status']}). Result artifact: `{source_ids[asset]}`.",
            "",
            "| Split and cohort | Eligible | Attempted | Scored | Unscored | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for split in ("train", "validation", "test"):
            lines.append(
                line(
                    f"{split} selected",
                    winner[split],
                    eligible_count(
                        result["candidates"],
                        selected["family"],
                        selected["filter"],
                        split,
                    ),
                )
            )
            lines.append(
                line(
                    f"{split} standalone fixed baseline",
                    baseline[split],
                    eligible_count(
                        result["candidates"], selected["family"], "none", split
                    ),
                )
            )
            pair = result["selected_paired_comparisons"][split]
            lines.append(
                line(f"{split} same-entry selected, common proof", pair["strategy"])
            )
            lines.append(
                line(f"{split} same-entry fixed, common proof", pair["baseline"])
            )
        lines += [
            "",
            f"Standalone fixed baseline is a separate one-position run, so it can take different entries. Same-entry comparisons retain only IDs with both terminal proofs; their independent counterfactual positions can overlap. Selected overlap skips: {winner['overlap_skips']}; baseline skips: {baseline['overlap_skips']}.",
            "",
            "For context, the following fixed ablations use the selected entry family, the 10-second delay and target+momentum. They are not retuned on the final split.",
            "",
            "| Test filter | Eligible | Attempted | Scored | Unscored | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for filt in ("none", "shape", "shape_bop", "shape_flow"):
            variant = next(
                (
                    v
                    for v in result["variants"]
                    if v["family"] == selected["family"]
                    and v["filter"] == filt
                    and v["exit"] == "target_momentum"
                    and v["delay_seconds"] == 10
                ),
                None,
            )
            if variant:
                lines.append(
                    line(
                        filt,
                        variant["test"],
                        eligible_count(
                            result["candidates"], selected["family"], filt, "test"
                        ),
                    )
                )
        lines += [
            "",
            "The 10-minute down-then-up second-turn baseline is capped at the next 10-minute close; a second completed bar cannot occur within that cap. It is therefore cap-equivalent, not a test of an extended second reversal.",
            "",
        ]
    lines += [
        "## Source and interpretation limits",
        "",
        "Shape scores use only completed 5/10/15/20-minute contexts and family-specific training counts. BOP is the trailing three completed 1-minute (close-open)/(high-low) price-only average, with flat bars set to zero; it is not an order count. BTC taker-flow ablation uses retained Binance completed-minute executed quote turnover as a spot proxy, not resting liquidity or Jupiter venue flow. BTC true order-book history was not available for this run.",
        "",
    ]
    if l2:
        lines += [
            "## Separate ZEC visible-book diagnostic",
            "",
            f"Result artifact: `{l2_id}`. This is one previously seen 24-hour Coinbase capture, not Jupiter house orders or a measure of Jupiter fills. It is not eligible for policy selection. All 55 eligible decisions had qualified visible book data; report the negative/complement subsets and one-position overlap separately.",
            "",
            "| Family, 10s target+momentum | Eligible | Attempted | Scored | Unscored | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for family in ("confirmed_uu", "near_end"):
            v = next(
                x
                for x in l2["variants"]
                if x["family"] == family
                and x["exit"] == "target_momentum"
                and x["delay_seconds"] == 10
            )
            for group in ("qualified", "negative", "complement"):
                eligible = sum(
                    c["family"] == family
                    and c["book_status"] == "qualified"
                    and (
                        group == "qualified"
                        or c["book_negative"] is (group == "negative")
                    )
                    for c in l2["candidates"]
                )
                lines.append(
                    line(f"{family} {group}", v["cohorts"][group]["summary"], eligible)
                )
        lines += [
            "",
            "Other exit policies have their own one-position overlap skips; the fixed and cap-equivalent second-turn near-end all/qualified groups each skip three entries, and the complement group skips one. Exact same-entry comparisons must not be confused with separately capacity-constrained groups.",
            "",
        ]
    return "\n".join(lines) + "\n", policies


def main():
    parser = argparse.ArgumentParser()
    for key in ("btc", "zec", "models", "btc-id", "zec-id", "output-dir"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--l2")
    parser.add_argument("--l2-id")
    args = parser.parse_args()
    if bool(args.l2) != bool(args.l2_id):
        raise ValueError("l2_artifact_id_required_with_result")
    model_sha = hashlib.sha256(Path(args.models).read_bytes()).hexdigest()
    results = {"BTC": read_archive(args.btc), "ZEC": read_archive(args.zec)}
    text, policies = render_report(
        results,
        model_sha,
        {"BTC": args.btc_id, "ZEC": args.zec_id},
        read_archive(args.l2) if args.l2 else None,
        args.l2_id,
    )
    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    report = root / "EXIT50-REVERSAL.md"
    report.write_text(text)
    bundle = root / "selected-policy.json"
    bundle.write_text(canonical(policies) + "\n")
    print(
        canonical(
            {
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "policy_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
