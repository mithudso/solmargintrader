"""Consolidate trial evidence without treating overlapping artifacts as studies.

The single JSON output preserves original records and units. The prose synthesis
uses family-level findings; it never pools incompatible returns into a grand mean.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_original": str(value)}
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(x) for x in value]
    return value


def load(path, raw=None):
    path = Path(path)
    raw = path.read_bytes() if raw is None else raw
    if path.name.endswith(".gz"):
        raw = gzip.decompress(raw)
    with io.StringIO(raw.decode("utf-8-sig")) as stream:
        if path.suffix in (".md", ".txt"):
            return "text_report", stream.read()
        if path.name.endswith((".csv", ".csv.gz")):
            return "csv", list(csv.DictReader(stream))
        if path.suffix == ".jsonl":
            return "jsonl", [json.loads(line) for line in stream if line.strip()]
        return "json", json.load(stream)


def family(path):
    name = str(path).lower()
    for needle, label in (
        ("strategy-config-sweep-validated", "validated_configuration_sweep"),
        ("strategy_experiment", "paired_dso"),
        ("coinbase50", "coinbase50_factorial"),
        ("shape_spot", "shape_routing"),
        ("zec_cycles", "zec_wavelength"),
        ("zec-ensembles", "zec_ensembles"),
        ("volty_predictive", "volty_predictive_sensitivity"),
        ("volty", "volty_walkforward"),
        ("perturb", "perturbation"),
        ("redundancy", "signal_redundancy"),
        ("geometry", "geometry_diagnostic"),
        ("rotation", "ratio_rotation"),
        ("trigger", "trigger_conjunctions"),
        ("leverage", "leverage_economics"),
        ("compound", "compound_direction"),
        ("frontier", "compound_frontier"),
        ("minute", "minute_common_window"),
        ("cpcv", "cpcv_and_cross_asset"),
        ("grid", "grid_review"),
        ("sweep", "single_split_sweep"),
        ("top_coin", "single_split_sweep"),
    ):
        if needle in name:
            return label
    return "other_retained_evidence"


def role(path):
    name = Path(path).name.lower()
    if Path(path).suffix in (".md", ".txt"):
        return "report_text_not_an_independent_replication"
    if any(x in name for x in ("tradingstrategyresults", "5minleveragestrategies", "tradingview", "exchangefees")):
        return "reference_or_capability_not_empirical_profit_evidence"
    if any(x in name for x in ("manifest", "audit", "snapshot", "coverage", "specs", "calibration", "top50-screen", "top50-nonpegged")):
        return "provenance_or_diagnostic"
    if any(x in name for x in ("conditional", "redundancy", "geometry", "pivot", "attribution")):
        return "diagnostic_not_independent_profit_trial"
    if "summary" in name or "comparison" in name or "tables" in name:
        return "derived_summary_not_independent_replication"
    return "empirical_records_require_family_specific_interpretation"


def sources(repo, evidence):
    paths = []
    for base in (repo / "research/results", repo / "research/strategy_experiment/results"):
        for path in sorted(base.rglob("*")):
            # Earlier gapped comparisons are documented as invalid, not
            # counted alongside the repaired experiment.
            if path.is_file() and path.name.endswith((".csv", ".csv.gz", ".json", ".jsonl")) and "initial-gapped-run" not in path.parts and not path.name.startswith("meta_analysis_"):
                paths.append(path)
    external = (
        evidence / "strategy-config-sweep-validated-20261110",
        evidence / "zec-ensembles-20261110/study-validated",
    )
    for base in external:
        for name in ("manifest.json", "results.jsonl", "summary.json", "top10.json", "holdout.json", "selection.json"):
            if (base / name).is_file():
                paths.append(base / name)
    paths.extend(p for p in sorted((repo / "research").glob("*.md")) if not p.name.startswith("META-"))
    paths.extend(sorted((repo / "research").glob("*.json")))
    for name in ("ZEC-ENSEMBLE-STUDY.md", "VOLTY-ZEC-STUDY.md", "VOLTY-PREDICTIVE-CHECKS.md", "ZEC-ENSEMBLES-FORWARD.md", "VOLTY-FORWARD-SERVICE.md"):
        if (repo / "docs" / name).is_file():
            paths.append(repo / "docs" / name)
    fees = evidence / "meta-analysis-20261111/authenticated-fees.json"
    if fees.exists():
        paths.append(fees)
    return list(dict.fromkeys(paths))


def consolidate(paths, exclusions=()):
    artifacts, payloads, aliases, errors = [], {}, [], []
    for path in paths:
        path = Path(path).resolve()
        try:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest in payloads:
                aliases.append({"path": str(path), "same_bytes_as": payloads[digest]["source_path"], "sha256": digest})
                continue
            kind, data = load(path, raw)
        except (ValueError, OSError) as exc:
            errors.append({"path": str(path), "error": str(exc)})
            continue
        artifact = {"source_path": str(path), "sha256": digest, "bytes": len(raw), "family": family(path), "role": role(path), "format": kind, "top_level_rows": len(data) if isinstance(data, list) else None, "data": clean(data)}
        payloads[digest] = artifact
        artifacts.append(artifact)
    return {"schema_version": 1, "interpretation": "A source-bound evidence consolidation, not an independent-study count or pooled-return estimate. CSV strings preserve original units and identifiers. Derived rows and nested summaries can overlap. Current source counts and historical report claims are distinct.", "artifacts": artifacts, "byte_identical_aliases": aliases, "excluded_or_missing": list(exclusions), "read_errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-source", type=Path, action="append", default=[],
                        help="Additional explicit result/receipt file; repeat as needed")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    exclusions = [
        {"path": str(args.evidence / "strategy-config-sweep-invalid-epoch-20261110"), "reason": "invalid epoch; superseded by validated run"},
        {"path": str(args.evidence / "strategy-config-sweep"), "reason": "prevalidation sibling; not independent confirmation"},
        {"path": str(args.repo / "research/strategy_experiment/results/initial-gapped-run"), "reason": "gapped initial run superseded by corrected paired comparison"},
        {"path": "/Users/mitch/Downloads/_scripts", "reason": "historical nine-coin raw source unavailable; report-only evidence remains"},
        {"path": "/Users/mitch/.local/share/solmargintrader/volty-forward-20261111", "reason": "retired forward cohort with unverified durability; not prospective qualification"},
    ]
    result = consolidate(sources(args.repo, args.evidence) + args.extra_source, exclusions)
    target = args.output / "all-trials.json"
    if target.exists():
        raise ValueError("use a fresh output directory; preserve accepted ledgers")
    target.write_text(json.dumps(result, allow_nan=False, separators=(",", ":")) + "\n")
    inventory = {"schema_version": 1, "all_trials": str(target), "sha256": sha(target), "artifact_count": len(result["artifacts"]), "aliases": result["byte_identical_aliases"], "errors": result["read_errors"], "sources": [{k: v for k, v in a.items() if k != "data"} for a in result["artifacts"]], "excluded": exclusions}
    (args.output / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print(json.dumps({k: inventory[k] for k in ("all_trials", "sha256", "artifact_count", "errors")}))
    return int(bool(result["read_errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
