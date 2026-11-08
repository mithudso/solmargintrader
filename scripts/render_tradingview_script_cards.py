#!/usr/bin/env python3
"""Render and verify source-reviewed documentation cards for saved trading scripts.

The authored JSONL records are the semantic input. Rendering does no semantic
classification. Final rendering requires an independent review of every record.
The raw HTML stays local; the default check uses only committed artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_tradingview_script_profiles import FIELDS, WORK, inputs, records
from scripts.check_tradingview_strategy_profiles import (
    bounded,
    card_location,
    publication,
)
from scripts.check_tradingview_strategy_profiles import validate as validate_protected

MANIFEST = Path("research/tradingview-script-understanding.json")
INDEX = Path("research/TRADINGVIEW-SCRIPT-CARDS.md")
CARD_DIR = Path("research/tradingview-script-cards")
INCOMPLETE_DIR = Path("backtester/strategy_cards/incomplete/publication-profiles")
PROTECTED = Path("research/tradingview-strategy-understanding.json")
LOCATIONS = Path("research/tradingview-strategy-card-locations.json")
FROZEN_MANIFEST = "1d40b13ab4eb8976f7cf2f419aa70932c9c1aab45ea54e19342d14736724ecd5"
REVIEW_FIELDS = {
    "in_scope",
    "classification",
    "purpose",
    *FIELDS,
    "required_data",
    "data_available",
    "data_reason",
    "evidence",
    "readiness",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def identity(value: object) -> str:
    """Stable identity independent of JSONL spacing and key order."""
    return sha(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    )


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def protected_entries() -> list[dict]:
    frozen = json.loads((ROOT / PROTECTED).read_text())
    moves = {}
    if (ROOT / LOCATIONS).exists():
        moves = {
            row["publication_id"]: row
            for row in json.loads((ROOT / LOCATIONS).read_text())["publications"]
        }
    entries = []
    for row in frozen["publications"]:
        entry = {**row, "in_scope": True, "protected": True}
        if moves:
            entry.update(
                {
                    "accepted_card_path": row["card_path"],
                    "card_path": card_location(ROOT, row).relative_to(ROOT).as_posix(),
                    "readiness": moves[row["publication_id"]]["readiness"],
                    "coin_test_ready": moves[row["publication_id"]].get(
                        "coin_test_ready", False
                    ),
                }
            )
        entries.append(entry)
    return entries


def read_coverage(ranges: list, length: int) -> bool:
    end = 0
    for start, stop in sorted(ranges):
        if not 0 <= start <= end <= stop <= length:
            return False
        end = stop
    return end == length


def check_review(profile: dict, source: dict, audit: dict) -> None:
    pid = profile["publication_id"]
    if profile["in_scope"]:
        check_readiness(profile)
    if any(
        audit.get(k) != v
        for k, v in {
            "publication_id": pid,
            "profile_sha256": identity(profile),
            "source_sha256": source["source_sha256"],
            "raw_description_sha256": source["raw_description_sha256"],
            "verdict": "pass",
        }.items()
    ):
        raise ValueError(f"Missing, stale or failing independent source review: {pid}")
    expected = (
        REVIEW_FIELDS
        if profile["in_scope"]
        else {
            "in_scope",
            "classification",
            "exclusion_reason",
            "evidence",
        }
    )
    if not expected <= set(audit.get("reviewed_fields", [])):
        raise ValueError(f"Incomplete independent semantic review: {pid}")
    if not read_coverage(
        audit.get("source_read_ranges", []), source["description_characters"]
    ):
        raise ValueError(f"Independent review lacks a full-source read: {pid}")
    if not audit.get("summary") or any(
        finding.get("severity") in {"critical", "high", "medium"}
        and finding.get("status") != "resolved"
        for finding in audit.get("findings", [])
    ):
        raise ValueError(f"Independent review has unresolved findings: {pid}")


def check_readiness(profile: dict) -> None:
    readiness = profile.get("readiness", {})
    if (
        readiness.get("status") not in {"usable-specification", "incomplete"}
        or not readiness.get("reason")
        or not isinstance(readiness.get("gaps"), list)
        or any(
            not isinstance(gap, str) or not gap.strip()
            for gap in readiness.get("gaps", [])
        )
        or (readiness.get("status") == "incomplete" and not readiness["gaps"])
        or (readiness.get("status") == "usable-specification" and readiness["gaps"])
    ):
        raise ValueError(
            f"Missing or contradictory computation-readiness decision: {profile['publication_id']}"
        )


def card_path(source: dict, profile: dict) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", source["name"].lower()).strip("_")[:80]
    # These reviews qualify source interpretation, not a self-contained coin test.
    directory = INCOMPLETE_DIR
    return directory / f"tv_{source['publication_id'].lower()}_{slug or 'script'}.md"


def bullets(lines: list[str]) -> str:
    return "\n".join("- " + line.replace("\n", "\n  ") for line in lines)


def literal(quote: str) -> str:
    fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", quote)), default=0))
    display = "\n".join(
        line.rstrip(" \t")
        for line in quote.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )
    return f"{fence}text\n{display}\n{fence}"


def render_card(source: dict, profile: dict, *, reviewed: bool) -> str:
    pid = profile["publication_id"]
    status = (
        "independently reviewed" if reviewed else "draft; independent review pending"
    )
    readiness = profile.get(
        "readiness",
        {
            "status": "incomplete",
            "reason": "Computation-completeness review is pending.",
            "gaps": [
                "Complete and independently review the per-publication readiness assessment."
            ],
        },
    )
    sections = [
        "---",
        f"id: tv_profile_{pid.lower()}",
        "name: " + json.dumps(source["name"], ensure_ascii=False),
        "kind: research-tool",
        "status: documentation-only",
        "coin_test_ready: false",
        "classification: " + profile["classification"],
        "summary: " + json.dumps(profile["purpose"], ensure_ascii=False),
        "registry_key: null",
        "runner: null",
        "evaluation: null",
        "---",
        "# " + source["name"].strip(),
        "Version: 1.0.0. Delta: individual explanation of the complete saved publication.",
        f"**Classification:** {profile['classification']}. Native publication type: {source['native_type']}. Review: {status}.",
        "## Idea and objective",
        profile["purpose"],
        "## Coin-test readiness: incomplete",
        "No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.",
        "## Source calculation and gaps",
        (
            "**Disclosed principal calculation.** "
            if readiness["status"] == "usable-specification"
            else "**Partly disclosed computation.** "
        )
        + readiness["reason"],
        bullets(readiness["gaps"])
        if readiness["gaps"]
        else "No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.",
        "## How it works",
        bullets(profile["mechanism"]),
        "## Outputs and intended use",
        bullets(profile["outputs_and_use"]),
        "## Parameters and stated settings",
        bullets(profile["parameters"]),
        "## Failure modes and caveats",
        bullets(profile["risks"]),
        "## Missing information and implementation boundary",
        bullets(profile["missing_information"]),
        "## Data requirements",
        "Required inputs: " + ", ".join(profile["required_data"]) + ".",
        "Repository input-class support: "
        + ("available" if profile["data_available"] else "unavailable or unresolved")
        + ". "
        + profile["data_reason"],
        "This input review does not establish cached coverage for a market, code parity or a measured trading result.",
        "## Evidence and interpretation",
        "The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.",
        "Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.",
        (
            "The saved script.content field is empty. Description snippets do not establish the complete Pine source."
            if not source["pine_source_available"]
            else "The saved page includes script content; this card reviews the author description and does not certify code parity."
        ),
    ]
    for n, evidence in enumerate(profile["evidence"], 1):
        sections.extend(
            [
                f"### E{n}: " + ", ".join(evidence["supports"]),
                literal(evidence["quote"]),
            ]
        )
    related = sorted(set(source["legacy_cards"] + source["legacy_referenced_cards"]))
    if related:
        sections.extend(
            [
                "## Earlier catalog references",
                "The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.",
                "\n".join(
                    catalog_link(cid, card_path(source, profile).parent)
                    for cid in related
                ),
            ]
        )
    sections.extend(
        [
            "## Source",
            source["url"],
            f"Publication ID: {pid}. Source SHA-256: {source['source_sha256']}. Raw-description SHA-256: {source['raw_description_sha256']}.",
            "The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.",
        ]
    )
    return "\n\n".join(sections) + "\n"


def catalog_link(cid: str, parent: Path) -> str:
    target = Path("backtester/strategy_cards") / f"{cid}.md"
    if not (ROOT / target).exists():
        target = Path("backtester/strategy_cards/incomplete") / f"{cid}.md"
    if not (ROOT / target).exists():
        raise ValueError(f"Earlier catalog reference no longer resolves: {cid}")
    return f"- [{cid}]({posixpath.relpath(target.as_posix(), parent.as_posix())})"


def table_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def index_text(data: dict) -> str:
    entries = sorted(
        data["publications"],
        key=lambda row: (row["name"].casefold(), row["publication_id"]),
    )
    included = [row for row in entries if row["in_scope"]]
    excluded = [row for row in entries if not row["in_scope"]]
    counts = Counter(row["classification"] for row in included)
    lines = [
        "# TradingView script idea cards",
        "",
        "Version: 1.0.0. Delta: expand the accepted strategy subset to all trading-related saved scripts.",
        "",
        f"Source-review state: **{data['state']}**. {len(entries)} of {data['source_count']} publications accounted for; {len(included)} trading-related cards and {len(excluded)} source-grounded non-trading exclusions.",
        "",
        "**Self-contained coin tests qualified: 0. All cards in this collection remain in the incomplete directory.** Source calculation disclosure is distinct from a complete test with all coin inputs, parameters, timing, calculation and output rules defined. These are research specifications, not ready-to-run coin tests.",
        "",
        "Each card explains the idea, mechanism, intended use, settings, limitations and data needs. Indicator and tool cards are documentation outside the executable strategy loader. Author claims are not measured results. Missing rules remain explicit.",
        "",
        "The 21 previously reviewed native-strategy cards retain their accepted files and evidence. The remaining source records receive separate documentation cards. The earlier broad catalog remains available as a historical component index.",
        "",
        "Classification counts: "
        + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        + ".",
        "",
        "## Trading-related publications",
        "",
        "| Publication | Native type | Classification | Coin-test readiness | Idea and objective |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in included:
        relative = (
            Path(row["card_path"]).relative_to("research").as_posix()
            if row["card_path"].startswith("research/")
            else "../" + row["card_path"]
        )
        lines.append(
            f"| [{table_text(row['name'])}]({relative}) (`{row['publication_id']}`) | {row['native_type']} | {row['classification']} | incomplete | {table_text(row['purpose'])} |"
        )
    lines.extend(
        [
            "",
            "## Non-trading publications",
            "",
            "These complete descriptions document art, games or generic utilities without a source-stated financial purpose. Financial libraries, session tools and trading infrastructure remain in scope.",
            "",
            "| Publication | Reason |",
            "| --- | --- |",
        ]
    )
    for row in excluded:
        lines.append(
            f"| [{table_text(row['name'])}]({row['url']}) (`{row['publication_id']}`) | {table_text(row['exclusion_reason'])} |"
        )
    if data["state"] != "accepted":
        lines.extend(
            [
                "",
                "This is a resumable draft. Missing publications and unaccepted semantic reviews remain work in progress.",
            ]
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "The committed understanding manifest records source hashes, profile hashes, card hashes, evidence offsets and review bindings. Run `python3 scripts/render_tradingview_script_cards.py check` for the offline final gate. Add `--source-root` pointing to the saved `/script` directory to verify every local HTML capture and exact raw-source passage.",
            "",
        ]
    )
    return "\n".join(lines)


def render(draft: bool) -> dict:
    work, sources = inputs()
    if sha((ROOT / PROTECTED).read_bytes()) != FROZEN_MANIFEST:
        raise ValueError("Previously accepted strategy manifest changed")
    validate_protected(ROOT)
    if not draft and not (ROOT / LOCATIONS).exists():
        raise ValueError(
            "The21 accepted cards still require completeness/location review"
        )
    previous = (
        json.loads((ROOT / MANIFEST).read_text())
        if (ROOT / MANIFEST).exists()
        else None
    )
    entries = protected_entries()
    bindings = {}
    pending_cards: dict[Path, str] = {}
    if (ROOT / LOCATIONS).exists():
        bindings[LOCATIONS.as_posix()] = sha((ROOT / LOCATIONS).read_bytes())
    for shard in work["shards"]:
        path = Path(work["shards"][shard]["output"])
        audit_path = Path(
            f"research/tradingview-script-profile-audits/shard-{shard}.jsonl"
        )
        authored = records(shard, complete=not draft)
        audit_rows = read_jsonl(ROOT / audit_path)
        audits = {row["publication_id"]: row for row in audit_rows}
        if len(audits) != len(audit_rows) or not audits.keys() <= set(
            work["shards"][shard]["publication_ids"]
        ):
            raise ValueError(f"Duplicate or unassigned audit in shard {shard}")
        for profile in authored:
            pid = profile["publication_id"]
            source = sources[pid]
            audit = audits.get(pid)
            reviewed = False
            if audit is not None:
                try:
                    check_review(profile, source, audit)
                    reviewed = True
                except ValueError:
                    if not draft:
                        raise
            if not draft and not reviewed:
                raise ValueError(f"No accepted independent review: {pid}")
            if profile["in_scope"] and not draft:
                check_readiness(profile)
            entry = {
                k: source[k]
                for k in (
                    "publication_id",
                    "name",
                    "native_type",
                    "url",
                    "source_path",
                    "source_sha256",
                    "raw_description_sha256",
                    "description_characters",
                    "pine_source_available",
                    "legacy_cards",
                    "legacy_referenced_cards",
                )
            }
            entry.update(
                {
                    k: profile[k]
                    for k in (
                        "in_scope",
                        "classification",
                        "source_read_ranges",
                    )
                }
            )
            entry.update(
                {
                    "profile_path": path.as_posix(),
                    "profile_sha256": identity(profile),
                    "audit_path": audit_path.as_posix(),
                    "audit_sha256": identity(audit) if reviewed else None,
                    "protected": False,
                }
            )
            entry["evidence"] = []
            for evidence in profile["evidence"]:
                start = source["description"].index(evidence["quote"])
                entry["evidence"].append(
                    {**evidence, "start": start, "end": start + len(evidence["quote"])}
                )
            if profile["in_scope"]:
                target = card_path(source, profile)
                text = render_card(source, profile, reviewed=reviewed)
                pending_cards[target] = text
                entry.update(
                    {
                        "purpose": profile["purpose"],
                        "card_path": target.as_posix(),
                        "card_sha256": sha(text.encode()),
                        "readiness": profile.get("readiness", {"status": "pending"}),
                        "coin_test_ready": False,
                    }
                )
            else:
                entry["exclusion_reason"] = profile["exclusion_reason"]
            entries.append(entry)
        bindings[path.as_posix()] = sha((ROOT / path).read_bytes())
        if audit_path.exists():
            bindings[audit_path.as_posix()] = sha((ROOT / audit_path).read_bytes())
    prior = (
        {
            row["card_path"]: row["card_sha256"]
            for row in previous["publications"]
            if row["in_scope"] and not row["protected"]
        }
        if previous
        else {}
    )
    for path, content in pending_cards.items():
        target = ROOT / path
        if target.exists() and sha(target.read_bytes()) not in {
            prior.get(path.as_posix()),
            sha(content.encode()),
        }:
            raise ValueError(f"Preserve an edited or unowned output card: {target}")
    if previous is not None:
        remove_obsolete(previous["publications"], entries)
    for path, content in pending_cards.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=".tv-card-",
            delete=False,
        ) as handle:
            handle.write(content)
            staged = Path(handle.name)
        staged.replace(target)
    data = {
        "schema_version": 1,
        "version": "1.0.0",
        "delta": "Expand the accepted21 native-strategy subset to all trading-related scripts.",
        "state": "draft" if draft else "accepted",
        "source_count": len(sources),
        "source_root": "saved /script HTML directory; raw captures remain local",
        "protected_manifest": PROTECTED.as_posix(),
        "protected_manifest_sha256": FROZEN_MANIFEST,
        "work_sha256": sha(WORK.read_bytes()),
        "artifact_hashes": bindings,
        "inventory": [
            {
                k: source[k]
                for k in (
                    "publication_id",
                    "name",
                    "native_type",
                    "url",
                    "source_path",
                    "source_sha256",
                    "raw_description_sha256",
                    "description_characters",
                )
            }
            for source in sources.values()
        ],
        "publications": sorted(entries, key=lambda row: row["publication_id"]),
    }
    data["index_sha256"] = sha(index_text(data).encode())
    (ROOT / INDEX).write_text(index_text(data))
    (ROOT / MANIFEST).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return {
        "state": data["state"],
        "accounted": len(entries),
        "cards": sum(row["in_scope"] for row in entries),
        "excluded": sum(not row["in_scope"] for row in entries),
    }


def remove_obsolete(previous: list[dict], current: list[dict]) -> None:
    """Move only unchanged, task-generated projections after readiness changes."""
    current_paths = {row["card_path"] for row in current if row["in_scope"]}
    for row in previous:
        if row["protected"] or not row["in_scope"] or row["card_path"] in current_paths:
            continue
        path = bounded(ROOT, row["card_path"])
        if path.parent not in {ROOT / CARD_DIR, ROOT / INCOMPLETE_DIR}:
            raise ValueError(
                f"Obsolete projection escapes task-owned directories: {path}"
            )
        if path.exists():
            if sha(path.read_bytes()) != row["card_sha256"]:
                raise ValueError(
                    f"Preserve edited obsolete card instead of deleting it: {path}"
                )
            path.unlink()


def check(source_root: Path | None = None, allow_draft: bool = False) -> dict:
    data = json.loads((ROOT / MANIFEST).read_text())
    if data["schema_version"] != 1 or data["state"] not in {"draft", "accepted"}:
        raise ValueError("Unknown script-understanding manifest schema/state")
    if data["state"] != "accepted" and not allow_draft:
        raise ValueError("Draft script profiles do not satisfy final acceptance")
    if (
        data["protected_manifest_sha256"] != FROZEN_MANIFEST
        or sha((ROOT / PROTECTED).read_bytes()) != FROZEN_MANIFEST
    ):
        raise ValueError("Previously accepted strategy manifest changed")
    validate_protected(ROOT, source_root)
    if data["work_sha256"] != sha(WORK.read_bytes()):
        raise ValueError("Assignment manifest changed after rendering")
    for path, digest in data["artifact_hashes"].items():
        if sha(bounded(ROOT, path).read_bytes()) != digest:
            raise ValueError(f"Authoring/review artifact changed: {path}")
    if data["index_sha256"] != sha((ROOT / INDEX).read_bytes()) or (
        ROOT / INDEX
    ).read_text() != index_text(data):
        raise ValueError("Script index drifted from its manifest")
    inventory = {row["publication_id"]: row for row in data["inventory"]}
    frozen = json.loads((ROOT / PROTECTED).read_text())
    frozen_inventory = {row["publication_id"]: row for row in frozen["inventory"]}
    if set(inventory) != set(frozen_inventory):
        raise ValueError(
            "Source inventory differs from the accepted742-publication inventory"
        )
    for pid, source in inventory.items():
        if any(
            source[k] != frozen_inventory[pid][k]
            for k in (
                "name",
                "native_type",
                "source_path",
                "source_sha256",
            )
        ):
            raise ValueError(f"Accepted source inventory metadata drifted: {pid}")
    protected = {row["publication_id"]: row for row in protected_entries()}
    if (
        data["state"] == "accepted"
        and LOCATIONS.as_posix() not in data["artifact_hashes"]
    ):
        raise ValueError(
            "Accepted strategy cards lack a final completeness/location receipt"
        )
    actual_protected = {
        row["publication_id"] for row in data["publications"] if row["protected"]
    }
    if actual_protected != set(protected):
        raise ValueError("Protected strategy subset differs from the accepted21")
    expected = set(inventory)
    actual = {row["publication_id"] for row in data["publications"]}
    if len(expected) != data["source_count"] or len(actual) != len(
        data["publications"]
    ):
        raise ValueError("Duplicate or missing source inventory entries")
    if not actual <= expected or (data["state"] == "accepted" and actual != expected):
        raise ValueError("Incomplete or unassigned publication coverage")
    profiles = {}
    audits = {}
    for shard, config in json.loads(WORK.read_text())["shards"].items():
        for row in read_jsonl(ROOT / config["output"]):
            if (
                row["publication_id"] in profiles
                or row["publication_id"] not in config["publication_ids"]
            ):
                raise ValueError("Duplicate or unassigned authored publication")
            profiles[row["publication_id"]] = row
        for row in read_jsonl(
            ROOT / f"research/tradingview-script-profile-audits/shard-{shard}.jsonl"
        ):
            if (
                row["publication_id"] in audits
                or row["publication_id"] not in config["publication_ids"]
            ):
                raise ValueError(
                    "Duplicate or unassigned independently reviewed publication"
                )
            audits[row["publication_id"]] = row
    expected_profiles = expected - set(protected)
    if not set(profiles) <= expected_profiles or (
        data["state"] == "accepted" and set(profiles) != expected_profiles
    ):
        raise ValueError("Authored profile inventory is incomplete")
    rendered = set()
    for row in data["publications"]:
        pid = row["publication_id"]
        source = inventory[pid]
        if row["protected"] and row != protected[pid]:
            raise ValueError(f"Accepted protected profile mapping changed: {pid}")
        if any(row[k] != source[k] for k in source if k in row):
            raise ValueError(f"Publication source metadata drifted: {pid}")
        if not row["protected"]:
            profile = profiles[pid]
            if identity(profile) != row["profile_sha256"]:
                raise ValueError(f"Publication profile changed: {pid}")
            if (
                row["in_scope"] != profile["in_scope"]
                or row["classification"] != profile["classification"]
            ):
                raise ValueError(f"Publication classification drifted: {pid}")
            if not read_coverage(
                profile["source_read_ranges"], source["description_characters"]
            ):
                raise ValueError(f"Incomplete source-read coverage: {pid}")
            if not row["evidence"] or len(row["evidence"]) != len(profile["evidence"]):
                raise ValueError(f"Evidence coverage drifted: {pid}")
            for evidence, authored_evidence in zip(
                row["evidence"], profile["evidence"], strict=True
            ):
                if (
                    any(
                        evidence[k] != authored_evidence[k]
                        for k in ("quote", "supports")
                    )
                    or not 0
                    <= evidence["start"]
                    < evidence["end"]
                    <= source["description_characters"]
                    or evidence["end"] - evidence["start"] != len(evidence["quote"])
                ):
                    raise ValueError(f"Evidence binding drifted: {pid}")
            reviewed = row["audit_sha256"] is not None
            if reviewed:
                audit = audits[pid]
                check_review(profile, source, audit)
                if row["audit_sha256"] != identity(audit):
                    raise ValueError(f"Independent review binding drifted: {pid}")
            elif data["state"] == "accepted":
                raise ValueError(f"Unreviewed publication: {pid}")
            if row["in_scope"]:
                if data["state"] == "accepted":
                    check_readiness(profile)
                if row["readiness"] != profile.get("readiness", {"status": "pending"}):
                    raise ValueError(f"Completeness decision drifted: {pid}")
                if row["card_path"] != card_path(row, profile).as_posix():
                    raise ValueError(
                        f"Incomplete/usable card location disagrees with review: {pid}"
                    )
                expected_body = render_card(row, profile, reviewed=reviewed)
                if bounded(ROOT, row["card_path"]).read_text() != expected_body:
                    raise ValueError(
                        f"Card differs from reviewed semantic profile: {pid}"
                    )
            elif row["exclusion_reason"] != profile["exclusion_reason"]:
                raise ValueError(f"Exclusion reason drifted: {pid}")
        if row["in_scope"]:
            if row.get("coin_test_ready") is not False or not row[
                "card_path"
            ].startswith("backtester/strategy_cards/incomplete/"):
                raise ValueError(
                    f"Source documentation falsely claims coin-test readiness: {pid}"
                )
            target = bounded(ROOT, row["card_path"])
            if sha(target.read_bytes()) != row["card_sha256"]:
                raise ValueError(f"Card hash mismatch: {pid}")
            if not row["protected"]:
                rendered.add(target.relative_to(ROOT).as_posix())
        if source_root is not None:
            raw = publication(source_root / source["source_path"])["description"] or ""
            if sha(raw.encode()) != source["raw_description_sha256"]:
                raise ValueError(f"Complete description hash mismatch: {pid}")
            for evidence in row["evidence"]:
                if raw[evidence["start"] : evidence["end"]] != evidence["quote"]:
                    raise ValueError(f"Raw-source evidence mismatch: {pid}")
    if rendered != {
        path.relative_to(ROOT).as_posix()
        for directory in (CARD_DIR, INCOMPLETE_DIR)
        for path in (ROOT / directory).glob("*.md")
    }:
        raise ValueError("Orphaned or missing rendered script documentation card")
    return {
        "state": data["state"],
        "accounted": len(actual),
        "sources": len(expected),
        "cards": sum(row["in_scope"] for row in data["publications"]),
        "excluded": sum(not row["in_scope"] for row in data["publications"]),
        "independent_reviews": sum(
            row.get("audit_sha256") is not None for row in data["publications"]
        ),
        "protected_strategies": sum(row["protected"] for row in data["publications"]),
    }


def check_audit(shard: str, partial: bool) -> dict:
    work, sources = inputs()
    authored = {row["publication_id"]: row for row in records(shard)}
    path = ROOT / f"research/tradingview-script-profile-audits/shard-{shard}.jsonl"
    rows = read_jsonl(path)
    seen = set()
    for audit in rows:
        pid = audit["publication_id"]
        if pid in seen or pid not in work["shards"][shard]["publication_ids"]:
            raise ValueError(f"Duplicate or unassigned audit: {pid}")
        seen.add(pid)
        if partial and audit.get("verdict") == "revise":
            if not audit.get("findings") or audit.get("profile_sha256") != identity(
                authored[pid]
            ):
                raise ValueError(f"Unbound revision finding: {pid}")
        else:
            check_review(authored[pid], sources[pid], audit)
    missing = set(authored) - seen
    if missing and not partial:
        raise ValueError(
            f"Missing independent reviews in shard {shard}: {len(missing)}"
        )
    return {
        "shard": shard,
        "review_records": len(rows),
        "missing": len(missing),
        "verdicts": dict(Counter(row["verdict"] for row in rows)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    rendering = sub.add_parser("render")
    rendering.add_argument("--draft", action="store_true")
    checking = sub.add_parser("check")
    checking.add_argument("--source-root", type=Path)
    checking.add_argument("--allow-draft", action="store_true")
    auditing = sub.add_parser("check-audit")
    auditing.add_argument("--shard", choices=["a", "b", "c"], required=True)
    auditing.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "render":
            result = render(args.draft)
        elif args.command == "check-audit":
            result = check_audit(args.shard, args.partial)
        else:
            result = check(args.source_root, args.allow_draft)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(f"Script idea cards: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
