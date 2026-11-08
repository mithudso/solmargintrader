#!/usr/bin/env python3
"""Verify strategy-publication cards and optionally bind them to saved HTML.

Without --source-root, verify committed cards, inventory and quoted evidence.
With --source-root, also verify every HTML hash and the complete strategy subset.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from backtester.core.strategy_cards import load_card


class PublicationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.payloads: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.capture = "init-data+json" in (dict(attrs).get("type") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.payloads.append(data)


def publication(path: Path) -> dict:
    parser = PublicationParser()
    parser.feed(path.read_text(encoding="utf-8"))
    for text in parser.payloads:
        for value in json.loads(text).values():
            if isinstance(value, dict) and isinstance(value.get("ssrIdeaData"), dict):
                return value["ssrIdeaData"]
    raise ValueError(f"Missing ssrIdeaData: {path}")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bounded(root: Path, name: str) -> Path:
    path = root / name
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError(f"Path escapes root: {name}")
    return path


def card_location(repo: Path, profile: dict) -> Path:
    """Resolve reviewed moves while retaining the accepted semantic manifest.

    A location receipt cannot change accepted card bytes. It binds a separately
    reviewed completeness decision to each final path after the owner's move.
    """
    receipt_path = repo / "research/tradingview-strategy-card-locations.json"
    if not receipt_path.exists():
        return bounded(repo, profile["card_path"])
    receipt = json.loads(receipt_path.read_text())
    accepted_path = repo / "research/tradingview-strategy-understanding.json"
    if (
        receipt.get("schema_version") != 1
        or receipt.get("verdict") != "pass"
        or receipt.get("accepted_manifest_sha256") != sha256(accepted_path.read_bytes())
    ):
        raise ValueError("Strategy-card location review is stale or unaccepted")
    entries = {row["publication_id"]: row for row in receipt["publications"]}
    expected = {
        row["publication_id"]
        for row in json.loads(accepted_path.read_text())["publications"]
    }
    if len(entries) != len(receipt["publications"]) or set(entries) != expected:
        raise ValueError(
            "Strategy-card location review must cover all21 accepted profiles"
        )
    entry = entries[profile["publication_id"]]
    if (
        entry["original_card_path"] != profile["card_path"]
        or entry["card_sha256"] != profile["card_sha256"]
        or entry["source_sha256"] != profile["source_sha256"]
        or entry["raw_description_sha256"] != profile["raw_description_sha256"]
    ):
        raise ValueError(
            "Strategy-card relocation does not preserve its accepted source/card binding"
        )
    readiness = entry["readiness"]
    if (
        readiness["status"] not in {"usable-specification", "incomplete"}
        or not readiness.get("reason")
        or not entry.get("evidence")
        or not isinstance(readiness.get("gaps"), list)
        or (readiness["status"] == "incomplete" and not readiness.get("gaps"))
        or (readiness["status"] == "usable-specification" and readiness["gaps"])
    ):
        raise ValueError(
            "Strategy-card relocation lacks a reviewed completeness decision"
        )
    end = 0
    for start, stop in sorted(entry.get("source_read_ranges", [])):
        if not 0 <= start <= end <= stop <= profile["description_characters"]:
            raise ValueError(
                "Strategy-card completeness review has unread source ranges"
            )
        end = stop
    if end != profile["description_characters"]:
        raise ValueError("Strategy-card completeness review lacks a full-source read")
    for evidence in entry["evidence"]:
        if (
            not evidence.get("quote")
            or not 0 <= evidence["start"] < evidence["end"] <= end
            or evidence["end"] - evidence["start"] != len(evidence["quote"])
        ):
            raise ValueError("Strategy-card completeness evidence has invalid offsets")
    target = bounded(repo, entry["current_card_path"])
    incomplete = "backtester/strategy_cards/incomplete/"
    incomplete_placement = (
        entry.get("coin_test_ready") is False or readiness["status"] == "incomplete"
    )
    if incomplete_placement != entry["current_card_path"].startswith(incomplete):
        raise ValueError("Strategy-card completeness disagrees with its location")
    return target


def legacy_normalize(text: str) -> str:
    """Apply the existing ledger's tv-description-v2 presentation rules."""
    text = re.sub(
        r"</?(?:p|div|h[1-6]|li|br|blockquote|tr|pre)(?:\s[^>]*)?/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\[(?:image|url)\]https?://.*?\[/(?:image|url)\]", "", text, flags=re.DOTALL
    )
    text = re.sub(
        r"\[/?(?:b|i|u|s|list|quote|code|center|left|right|url|size|color)(?:=[^\]]*)?\]|\[\*\]",
        "",
        text,
    )
    text = re.sub(
        r"</?(?:span|a|b|i|u|em|strong|img|table|thead|tbody|td|th|ul|ol|code|figure|figcaption|sup|sub)(?:\s[^>]*)?/?>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return "\n".join(
        re.sub(r"\s+", " ", line).strip() for line in html.unescape(text).splitlines()
    ).strip()


def validate(repo: Path, source_root: Path | None = None) -> dict:
    manifest_bytes = (
        repo / "research/tradingview-strategy-understanding.json"
    ).read_bytes()
    data = json.loads(manifest_bytes)
    if data["schema_version"] != 1:
        raise ValueError("Unsupported strategy-understanding schema")
    inventory = data["inventory"]
    inventory_by_id = {row["publication_id"]: row for row in inventory}
    if len(inventory_by_id) != len(inventory):
        raise ValueError("Duplicate publication in inventory")
    expected = {
        row["publication_id"] for row in inventory if row["native_type"] == "strategy"
    }
    profiles = data["publications"]
    receipt = json.loads(
        (repo / "research/tradingview-strategy-understanding-audit.json").read_text()
    )
    tuples = sorted(
        [row["publication_id"], row["card_path"], row["card_sha256"]]
        for row in profiles
    )
    card_set = sha256(
        json.dumps(tuples, separators=(",", ":"), ensure_ascii=True).encode()
    )
    if (
        receipt["qualification_verdict"] != "pass-for-final-card-source-contract"
        or receipt["manifest_sha256"] != sha256(manifest_bytes)
        or receipt["card_set_sha256"] != card_set
    ):
        raise ValueError("Independent source-card review is stale or not qualified")
    actual = {row["publication_id"] for row in profiles}
    if len(actual) != len(profiles) or actual != expected:
        raise ValueError("Strategy subset is incomplete or duplicated")
    card_paths = {row["card_path"] for row in profiles}
    if len(card_paths) != len(profiles):
        raise ValueError("Two publications share a publication-specific card")
    for row in profiles:
        pid = row["publication_id"]
        entry = inventory_by_id[pid]
        if row["native_type"] != "strategy" or not row["full_description_read"]:
            raise ValueError(f"Incomplete source interpretation: {pid}")
        if any(
            row[field] != entry[field] for field in ("source_path", "source_sha256")
        ):
            raise ValueError(f"Profile/inventory source mismatch: {pid}")
        path = card_location(repo, row)
        raw = path.read_bytes()
        if sha256(raw) != row["card_sha256"]:
            raise ValueError(
                f"Card changed without refreshing its interpretation receipt: {path}"
            )
        body = raw.decode("utf-8")
        if row["purpose"] not in body or row["url"] not in body:
            raise ValueError(f"Card omits purpose or source: {pid}")
        if f"**Classification:** {row['classification']}." not in body:
            raise ValueError(f"Card classification differs from its receipt: {pid}")
        if row["canonical_strategy_card"]:
            card = load_card(path)
            if card.id != row["card_id"] or card.status != "spec-only":
                raise ValueError(f"Invalid strategy-card identity/status: {pid}")
            if (
                card.runner is not None
                or card.registry_key is not None
                or card.evaluation is not None
            ):
                raise ValueError(
                    f"Publication card claims runnable/measured status: {pid}"
                )
            if "data_review" in row:
                review = row["data_review"]
                if (
                    card.data_required != review["required"]
                    or card.data_available != review["available"]
                ):
                    raise ValueError(
                        f"Source-reviewed data requirements drifted: {pid}"
                    )
        elif not row["card_path"].startswith("research/tradingview-strategy-tools/"):
            raise ValueError(
                f"Companion tool entered the strategy loader directory: {pid}"
            )
        elif any(
            line not in body
            for line in (
                "kind: research-tool",
                "status: documentation-only",
                "registry_key: null",
                "runner: null",
                "evaluation: null",
            )
        ):
            raise ValueError(f"Companion tool claims a strategy implementation: {pid}")
        unquoted = re.sub(r"(?m)^> ?", "", body)
        for evidence in row["evidence"]:
            if evidence["display_quote"] not in unquoted:
                raise ValueError(f"Card omits cited passage: {pid}/{evidence['label']}")
        for evidence in row["legacy_coverage_excerpts"]:
            if evidence["quote"] not in unquoted:
                raise ValueError(f"Card drops prior coverage passage: {pid}")
    if source_root is not None:
        actual_paths = {
            path.relative_to(source_root).as_posix()
            for path in source_root.rglob("*.html")
        }
        if actual_paths != {row["source_path"] for row in inventory}:
            raise ValueError(
                "Saved HTML inventory differs from the recorded source directory"
            )
        native_strategies: set[str] = set()
        descriptions: dict[str, str] = {}
        for row in inventory:
            path = bounded(source_root, row["source_path"])
            if sha256(path.read_bytes()) != row["source_sha256"]:
                raise ValueError(f"Source HTML changed: {path}")
            idea = publication(path)
            native_type = (idea.get("script") or {}).get("script_type")
            if (
                idea["uuid"] != row["publication_id"]
                or native_type != row["native_type"]
            ):
                raise ValueError(f"Native publication identity/type mismatch: {path}")
            if native_type == "strategy":
                native_strategies.add(idea["uuid"])
                descriptions[idea["uuid"]] = idea.get("description") or ""
        if native_strategies != expected:
            raise ValueError("Actual strategy-typed source subset differs")
        for row in profiles:
            text = descriptions[row["publication_id"]]
            if sha256(text.encode()) != row["raw_description_sha256"]:
                raise ValueError(f"Raw description changed: {row['publication_id']}")
            if len(text) != row["description_characters"]:
                raise ValueError(
                    f"Description read length differs: {row['publication_id']}"
                )
            for evidence in row["evidence"]:
                if text[evidence["start"] : evidence["end"]] != evidence["quote"]:
                    raise ValueError(
                        f"Evidence offsets do not bind to source: {row['publication_id']}"
                    )
            if row["legacy_coverage_excerpts"]:
                if row["legacy_normalizer"] != "tv-description-v2":
                    raise ValueError("Unknown legacy passage normalizer")
                normalized = legacy_normalize(text)
                if (
                    sha256(normalized.encode())
                    != row["legacy_normalized_description_sha256"]
                ):
                    raise ValueError(
                        f"Legacy description binding changed: {row['publication_id']}"
                    )
                for evidence in row["legacy_coverage_excerpts"]:
                    if (
                        normalized[evidence["start"] : evidence["end"]]
                        != evidence["quote"]
                    ):
                        raise ValueError(
                            f"Legacy evidence offsets do not bind: {row['publication_id']}"
                        )
            locations = repo / "research/tradingview-strategy-card-locations.json"
            if locations.exists():
                entry = next(
                    item
                    for item in json.loads(locations.read_text())["publications"]
                    if item["publication_id"] == row["publication_id"]
                )
                for evidence in entry["evidence"]:
                    if text[evidence["start"] : evidence["end"]] != evidence["quote"]:
                        raise ValueError(
                            f"Completeness evidence does not bind: {row['publication_id']}"
                        )
    return {
        "inventory": len(inventory),
        "strategy_publications": len(profiles),
        "canonical_cards": sum(row["canonical_strategy_card"] for row in profiles),
        "companion_cards": sum(not row["canonical_strategy_card"] for row in profiles),
        "bound_passages": sum(len(row["evidence"]) for row in profiles),
        "raw_sources_verified": source_root is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    try:
        result = validate(REPO, args.source_root)
    except (ValueError, KeyError, OSError) as exc:
        print(f"Strategy publication cards: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
