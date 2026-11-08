#!/usr/bin/env python3
"""Prepare resumable semantic-authoring batches for every saved TradingView script.

Raw author descriptions stay in the gitignored tradingview/.script-card-work cache.
Authors write original interpretations to assigned JSONL files; this helper checks
source coverage and exact quotations, never synthesizes trading rules from titles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_tradingview_strategy_profiles import publication

CACHE = ROOT / "tradingview/.script-card-work"
WORK = ROOT / "research/tradingview-script-profile-work.json"
CLASSES = {
    "indicator",
    "trading-strategy",
    "financial-library",
    "drawing-tool",
    "execution-tool",
    "risk-tool",
    "reporting-tool",
    "analysis-tool",
    "non-trading",
}
FIELDS = ("mechanism", "outputs_and_use", "parameters", "risks", "missing_information")


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def prepare(source_root: Path) -> None:
    protected = json.loads(
        (ROOT / "research/tradingview-strategy-understanding.json").read_text()
    )
    ids = {row["publication_id"] for row in protected["publications"]}
    ledger = json.loads((ROOT / "research/tradingview-card-coverage.json").read_text())
    legacy = {
        row["publication_id"]: row
        for row in ledger["rows"]
        if row.get("kind") == "script"
    }
    sources = []
    for path in sorted(source_root.rglob("*.html")):
        idea = publication(path)
        pid = idea["uuid"]
        description = idea.get("description") or ""
        previous = legacy[pid]
        sources.append(
            {
                "publication_id": pid,
                "name": idea["name"],
                "native_type": (idea.get("script") or {}).get("script_type"),
                "url": "https://www.tradingview.com" + idea["chart_url"],
                "source_path": path.relative_to(source_root).as_posix(),
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "raw_description_sha256": hashlib.sha256(
                    description.encode()
                ).hexdigest(),
                "description": description,
                "description_characters": len(description),
                "pine_source_available": bool(
                    (idea.get("script") or {}).get("content")
                ),
                "legacy_cards": previous.get("cards", []),
                "legacy_disposition": previous["disposition"],
                "legacy_referenced_cards": previous.get("referenced_cards", []),
                "protected_strategy_profile": pid in ids,
            }
        )
    if (
        len(sources) != 742
        or {s["publication_id"] for s in sources if s["protected_strategy_profile"]}
        != ids
    ):
        raise ValueError(
            "Saved source corpus differs from the accepted initial inventory"
        )
    dump(CACHE / "source-corpus.json", {"sources": sources})
    bins = {name: {"characters": 0, "ids": []} for name in ("a", "b", "c")}
    for source in sorted(
        (s for s in sources if not s["protected_strategy_profile"]),
        key=lambda s: (-len(s["description"]), s["publication_id"]),
    ):
        name = min(
            bins,
            key=lambda name: (bins[name]["characters"], len(bins[name]["ids"]), name),
        )
        bins[name]["ids"].append(source["publication_id"])
        bins[name]["characters"] += len(source["description"])
    work = {
        "version": "1.0.0",
        "delta": "expand accepted21-strategy subset to all trading-related script publications",
        "scope": "All742 saved script publications; independently interpret all721 remaining descriptions, including indicator studies and financial libraries. Non-trading decisions require source evidence.",
        "source_count": len(sources),
        "protected_strategy_ids": sorted(ids),
        "native_type_counts": dict(Counter(s["native_type"] for s in sources)),
        "cache": "tradingview/.script-card-work/source-corpus.json",
        "source_corpus_sha256": hashlib.sha256(
            (CACHE / "source-corpus.json").read_bytes()
        ).hexdigest(),
        "shards": {
            name: {
                "publication_ids": sorted(value["ids"]),
                "description_characters": value["characters"],
                "output": f"research/tradingview-script-profiles/shard-{name}.jsonl",
            }
            for name, value in bins.items()
        },
    }
    dump(WORK, work)
    print(
        json.dumps(
            {
                "source_count": len(sources),
                "protected": len(ids),
                "remaining_characters": sum(b["characters"] for b in bins.values()),
                "shards": {
                    k: {"count": len(v["ids"]), "characters": v["characters"]}
                    for k, v in bins.items()
                },
            }
        )
    )


def inputs() -> tuple[dict, dict]:
    work = json.loads(WORK.read_text())
    raw = (CACHE / "source-corpus.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != work["source_corpus_sha256"]:
        raise ValueError("Authoring input corpus changed")
    return work, {s["publication_id"]: s for s in json.loads(raw)["sources"]}


def validate_record(row: dict, source: dict) -> None:
    pid = source["publication_id"]
    if row.get("publication_id") != pid or type(row.get("in_scope")) is not bool:
        raise ValueError(f"Invalid publication identity/scope: {pid}")
    if row.get("classification") not in CLASSES:
        raise ValueError(f"Unknown classification: {pid}")
    intervals = sorted(row.get("source_read_ranges", []))
    end = 0
    for start, stop in intervals:
        if not (0 <= start <= end <= stop <= len(source["description"])):
            raise ValueError(
                f"Incomplete or invalid full-description read coverage: {pid}"
            )
        end = stop
    if end != len(source["description"]):
        raise ValueError(f"Incomplete full-description read: {pid}")
    evidence = row.get("evidence", [])
    if not evidence:
        raise ValueError(f"No exact evidence: {pid}")
    for item in evidence:
        if not item.get("quote") or item["quote"] not in source["description"]:
            raise ValueError(f"Quotation does not occur in the raw description: {pid}")
        if not item.get("supports"):
            raise ValueError(f"Evidence lacks a claim/section binding: {pid}")
    if not row["in_scope"]:
        if row["classification"] != "non-trading" or not row.get("exclusion_reason"):
            raise ValueError(f"Unexplained exclusion: {pid}")
        return
    if (
        row["classification"] == "non-trading"
        or len(row.get("purpose", "").split()) < 8
    ):
        raise ValueError(f"Missing individual purpose: {pid}")
    for field in FIELDS:
        if (
            not isinstance(row.get(field), list)
            or not row[field]
            or any(not isinstance(s, str) or not s.strip() for s in row[field])
        ):
            raise ValueError(f"Missing authored {field}: {pid}")
    if (
        not row.get("required_data")
        or type(row.get("data_available")) is not bool
        or not row.get("data_reason")
    ):
        raise ValueError(f"Missing source-grounded data review: {pid}")
    if "readiness" in row:
        readiness = row["readiness"]
        if (
            readiness.get("status") not in {"usable-specification", "incomplete"}
            or not readiness.get("reason")
            or not isinstance(readiness.get("gaps"), list)
            or (readiness["status"] == "incomplete" and not readiness["gaps"])
        ):
            raise ValueError(f"Invalid computation-completeness decision: {pid}")


def records(shard: str, complete: bool = True) -> list[dict]:
    work, sources = inputs()
    entry = work["shards"][shard]
    path = ROOT / entry["output"]
    rows = (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if path.exists()
        else []
    )
    ids = [row["publication_id"] for row in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= set(entry["publication_ids"]):
        raise ValueError(f"Duplicate or unassigned publication in shard{shard}")
    for row in rows:
        validate_record(row, sources[row["publication_id"]])
    missing = sorted(set(entry["publication_ids"]) - set(ids))
    print(
        json.dumps(
            {
                "shard": shard,
                "valid_records": len(rows),
                "assigned": len(entry["publication_ids"]),
                "missing": len(missing),
                "next_ids": missing[:8],
            }
        )
    )
    if complete and missing:
        raise ValueError(f"Shard{shard} is incomplete")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source-root", type=Path, required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--shard", choices=["a", "b", "c"], required=True)
    show = sub.add_parser("show")
    show.add_argument("publication_id")
    show.add_argument("--start", type=int, default=0)
    show.add_argument("--length", type=int, default=16000)
    check = sub.add_parser("check")
    check.add_argument("--shard", choices=["a", "b", "c"], required=True)
    check.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.source_root)
            return 0
        work, sources = inputs()
        if args.command == "list":
            for pid in work["shards"][args.shard]["publication_ids"]:
                s = sources[pid]
                print(
                    json.dumps(
                        {
                            k: s[k]
                            for k in (
                                "publication_id",
                                "name",
                                "native_type",
                                "description_characters",
                                "legacy_cards",
                                "legacy_disposition",
                            )
                        },
                        ensure_ascii=False,
                    )
                )
        elif args.command == "show":
            s = sources[args.publication_id]
            start = max(0, args.start)
            end = min(len(s["description"]), start + max(1, args.length))
            print(
                json.dumps(
                    {k: v for k, v in s.items() if k != "description"},
                    ensure_ascii=False,
                )
            )
            print(
                "<untrusted_content>\n"
                + s["description"][start:end]
                + "\n</untrusted_content>"
            )
            print(
                f"SOURCE_READ_CHUNK {s['publication_id']} {start}:{end}/{len(s['description'])}; remaining={len(s['description']) - end}"
            )
        elif args.command == "check":
            records(args.shard, complete=not args.partial)
    except (ValueError, KeyError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
