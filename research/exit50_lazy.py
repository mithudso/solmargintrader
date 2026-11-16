"""Resume bounded native-first paper replay acquisition, without funded actions."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from research.exit50_acquire import fetch_one
from research.exit50_run import first_missing_windows, study_candidates
from research.reversal_history import canonical
from research.reversal_shapes import boundaries


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--asset", choices=("BTC", "ZEC"), required=True)
    plan.add_argument("--entry-root", required=True)
    plan.add_argument("--cache-root", required=True)
    plan.add_argument("--models", required=True)
    plan.add_argument("--output", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--plan", required=True)
    fetch.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.action == "plan":
        model_bytes = Path(args.models).read_bytes()
        bundle = json.loads(model_bytes)
        prepared, candidates = study_candidates(args.asset, args.entry_root, bundle)
        needed = first_missing_windows(
            args.asset, prepared, candidates, args.entry_root, args.cache_root
        )
        value = {
            "schema": "exit50-lazy-wave-plan/v1",
            "asset": args.asset,
            "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
            "minute_source_sha256": hashlib.sha256(
                Path(
                    f"/Users/mitch/.local/state/reversal-leverage-2289/transport/{args.asset}-oracle-source.json"
                ).read_bytes()
            ).hexdigest(),
            "conflict_ledger_sha256": hashlib.sha256(
                (Path(args.cache_root) / "conflicts.json").read_bytes()
            ).hexdigest()
            if (Path(args.cache_root) / "conflicts.json").exists()
            else None,
            "candidate_count": len(candidates),
            "checked": needed["checked"],
            "all_needed_count": len(needed["slots"]),
            "selected_slots": [
                {"asset": a, "slot": slot} for a, slot in needed["slots"][:800]
            ],
            "permanent": needed["permanent"],
            "cases": needed["cases"],
        }
        raw = canonical(value) + "\n"
        Path(args.output).write_text(raw)
        print(
            canonical(
                {
                    "candidate_count": len(candidates),
                    "checked": needed["checked"],
                    "all_needed_count": len(needed["slots"]),
                    "planned": len(value["selected_slots"]),
                    "permanent": len(needed["permanent"]),
                    "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                }
            )
        )
    else:
        plan_value = json.loads(Path(args.plan).read_text())
        if (
            plan_value.get("schema") != "exit50-lazy-wave-plan/v1"
            or len(plan_value.get("selected_slots", [])) > 800
        ):
            raise ValueError("invalid_wave_plan")
        root = Path(args.output)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        start, _, _, stop = boundaries()
        for item in plan_value["selected_slots"]:
            slot = item.get("slot")
            if (
                item.get("asset") not in ("BTC", "ZEC")
                or type(slot) is not int
                or slot % 120
                or not start <= slot - 60
                or not slot + 60 <= stop
            ):
                raise ValueError("window_outside_frozen_source_range")
        jobs = [(v["asset"], v["slot"], root) for v in plan_value["selected_slots"]]
        plan_hash = hashlib.sha256(Path(args.plan).read_bytes()).hexdigest()
        records = []

        def save_manifest():
            raw = (
                canonical(
                    {
                        "schema": "exit50-lazy-wave-transport/v1",
                        "plan_sha256": plan_hash,
                        "planned": len(jobs),
                        "records": records,
                    }
                )
                + "\n"
            )
            tmp = root / "manifest.pending"
            tmp.write_text(raw)
            tmp.replace(root / "manifest.json")
            return raw

        with ThreadPoolExecutor(max_workers=4) as pool:
            for i, record in enumerate(pool.map(fetch_one, jobs), 1):
                records.append(record)
                if i % 50 == 0:
                    save_manifest()
                    print(f"{i}/{len(jobs)}", flush=True)
        raw = save_manifest()

        print(
            canonical(
                {
                    "planned": len(jobs),
                    "complete": sum(r["status"] == 200 for r in records),
                    "failed": sum(r["status"] != 200 for r in records),
                    "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                }
            )
        )


if __name__ == "__main__":
    main()
