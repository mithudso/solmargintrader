#!/usr/bin/env python3
"""Check card coverage; optionally re-bind evidence to the owner's local dumps.

The default is offline and uses committed evidence. --source-root verifies physical
capture hashes, decoded descriptions and excerpt offsets; it never fetches pages.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from backtester.core.strategy_cards import load_all  # noqa: E402


def normalize_description(text: str) -> str:
    """tv-description-v2: presentation cleanup, without semantic rewriting."""
    text = re.sub(r'</?(?:p|div|h[1-6]|li|br|blockquote|tr|pre)(?:\s[^>]*)?/?>', '\n', text, flags=re.I)
    text = re.sub(r"\[(?:image|url)\]https?://.*?\[/(?:image|url)\]", "", text, flags=re.S)
    text = re.sub(
        r"\[/?(?:b|i|u|s|list|quote|code|center|left|right|url|size|color)(?:=[^\]]*)?\]|\[\*\]",
        "", text,
    )
    text = re.sub(r'</?(?:span|a|b|i|u|em|strong|img|table|thead|tbody|td|th|ul|ol|code|figure|figcaption|sup|sub)(?:\s[^>]*)?/?>', '', text, flags=re.I)
    text = html.unescape(text)
    return "\n".join(re.sub(r"\s+", " ", line).strip() for line in text.splitlines()).strip()


def source_description(path: Path, *, normalized: bool = True) -> str:
    text = path.read_text(encoding="utf-8")
    result = None
    if path.suffix == ".md":
        result = text.split("---", 2)[-1]
        return normalize_description(result) if normalized else result
    for match in re.finditer(
        r'<script[^>]*type="application/prs.init-data\+json"[^>]*>(.*?)</script>', text, re.S
    ):
        try:
            payload = json.loads(match[1])
        except ValueError:
            continue
        for value in payload.values():
            if isinstance(value, dict) and isinstance(value.get("ssrIdeaData"), dict):
                result = value["ssrIdeaData"].get("description") or ""
            if isinstance(value, dict) and isinstance(value.get("solution"), dict):
                result = value["solution"].get("description") or ""
            if result is not None:
                return normalize_description(result) if normalized else result
    raise ValueError(f"publication description missing: {path}")


def validate(data: dict, repo: Path = REPO, source_root: Path | None = None) -> dict:
    cards = load_all(repo / "backtester/strategy_cards")
    created = set(data["created_card_ids"])
    if len(created) != len(data["created_card_ids"]):
        raise ValueError("duplicate created card id")
    if created & set(data["existing_card_ids"]):
        raise ValueError("new card overwrites an existing card")
    if not created <= cards.keys():
        raise ValueError("created card missing from card directory")
    if {key for key in cards if key.startswith("tv_")} != created:
        raise ValueError("unrecorded or orphaned TradingView card")
    rows = data["rows"]
    builtin_rows = [row for row in rows if row["kind"] == "builtin"]
    catalog = (repo / "docs/TRADINGVIEW-REFERENCE.md").read_text().split(
        "### 1. Catalog of built-in indicators"
    )[1].split("### Standard equations")[0]
    names = re.findall(r"^\| `([^`]+)` \|", catalog, re.M)
    if len(names) != 114 or sorted(names) != sorted(row["name"] for row in builtin_rows):
        raise ValueError("built-in study coverage differs from source catalog")
    publications = [row for row in rows if row["kind"] in ("script", "chart", "support", "other")]
    by_url = {row["url"]: row for row in publications}
    if len(by_url) != len(publications):
        raise ValueError("duplicate canonical publication URL")
    expected_counts = data.get("source_publication_counts")
    actual_counts = {kind: sum(row["kind"] == kind for row in publications)
                     for kind in ("script", "chart", "support", "other")}
    if expected_counts is None or actual_counts != expected_counts:
        raise ValueError("source publication inventory count mismatch")
    claimed = set()
    verified_files: set[Path] = set()
    descriptions: dict[str, str] = {}
    definitions: dict[str, set[str]] = {}
    allowed = {"new-card", "existing", "existing-code", "alias", "duplicate",
               "non-signal", "market-commentary", "covered-concepts", "library",
               "source-insufficient", "named-only"}
    for row in rows:
        if row["disposition"] not in allowed or not row.get("reason"):
            raise ValueError(f"unresolved disposition: {row['name']}")
        targets = row.get("cards", []) + row.get("referenced_cards", [])
        missing = set(targets) - cards.keys()
        if missing:
            raise ValueError(f"{row['name']}: unknown card targets {sorted(missing)}")
        if "data_review" in row:
            review = row["data_review"]
            for target in row.get("cards", []):
                if target in created and (cards[target].data_required != review["required"]
                                          or cards[target].data_available != review["available"]):
                    raise ValueError(f"{target}: reviewed data requirements drifted")
        if row["disposition"] in {"new-card", "existing", "alias", "covered-concepts"}:
            if not row.get("cards") and not row.get("code"):
                raise ValueError(f"{row['name']}: coverage match has no target")
        if row["disposition"] == "new-card":
            if len(row["cards"]) != 1 or row["cards"][0] in claimed:
                raise ValueError(f"{row['name']}: duplicate new-card ownership")
            claimed.add(row["cards"][0])
            card = cards[row["cards"][0]]
            if card.status != "spec-only" or card.runner is not None or card.registry_key is not None:
                raise ValueError(f"{card.id}: source specification claims runnable status")
            if card.evaluation is not None or card.success_basis != "a-priori":
                raise ValueError(f"{card.id}: source specification claims measured evidence")
            if not re.search(r"^Version: \d+\.\d+\.\d+\b", card.body, re.M) or "Delta:" not in card.body:
                raise ValueError(f"{card.id}: missing version/delta")
            for excerpt in row.get("excerpts", []):
                if excerpt["quote"] not in card.body:
                    raise ValueError(f"{card.id}: source passage omitted from card")
        for pointer in row.get("code", []):
            filename, symbol = pointer.split(":", 1)
            if filename not in definitions:
                tree = ast.parse((repo / filename).read_text())
                definitions[filename] = {node.name for node in ast.walk(tree)
                                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            if symbol not in definitions[filename]:
                raise ValueError(f"stale implementation pointer: {pointer}")
        for source in row.get("sources", []):
            for field in ("path", "sha256"):
                if not source.get(field):
                    raise ValueError(f"{row['name']}: missing source {field}")
            if not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
                raise ValueError("invalid source sha256")
            path = Path(source["path"])
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("source path escapes its declared root")
            root = repo if source.get("scope") == "repository" else source_root
            if root is not None:
                source_path = root / path
                if source_path not in verified_files:
                    actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
                    if actual != source["sha256"]:
                        raise ValueError(f"source hash mismatch: {source_path}")
                    verified_files.add(source_path)
        if source_root is not None and row.get("description_sha256"):
            if row["normalizer"] != "tv-description-v2":
                raise ValueError("unsupported publication description normalizer")
            text = source_description(source_root / row["sources"][0]["path"])
            if hashlib.sha256(text.encode()).hexdigest() != row["description_sha256"]:
                raise ValueError(f"description hash mismatch: {row['name']}")
            descriptions[row["url"]] = text
            for excerpt in row["excerpts"]:
                if text[excerpt["start"]:excerpt["end"]] != excerpt["quote"]:
                    raise ValueError(f"excerpt mismatch: {row['name']}")
        if source_root is not None and row.get("raw_description_sha256"):
            raw = source_description(source_root / row["sources"][0]["path"], normalized=False)
            if hashlib.sha256(raw.encode()).hexdigest() != row["raw_description_sha256"]:
                raise ValueError(f"raw description hash mismatch: {row['name']}")
            for excerpt in row["raw_excerpts"]:
                if raw[excerpt["start"]:excerpt["end"]] != excerpt["quote"]:
                    raise ValueError(f"raw excerpt mismatch: {row['name']}")
    if claimed != created:
        raise ValueError(f"created/covered card mismatch: {sorted(claimed ^ created)}")
    if source_root is not None:
        for source in data["nonpublication_files"]:
            path = source_root / source["path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"excluded source hash mismatch: {path}")
            verified_files.add(path)
        for row in rows:
            for evidence in row.get("evidence", []):
                text = descriptions[evidence["url"]]
                if hashlib.sha256(text.encode()).hexdigest() != evidence["description_sha256"]:
                    raise ValueError("method evidence description hash mismatch")
                for excerpt in evidence["excerpts"]:
                    if text[excerpt["start"]:excerpt["end"]] != excerpt["quote"]:
                        raise ValueError("method evidence excerpt mismatch")
        actual_paths = {path.relative_to(source_root).as_posix()
                        for kind in ("script", "chart")
                        for path in (source_root / "www.tradingview.com/www.tradingview.com" / kind).rglob("*.html")}
        actual_paths.update(path.relative_to(source_root).as_posix()
                            for folder in source_root.glob("01a1b7d7-*") for path in folder.glob("*.md"))
        actual_paths.update(path.relative_to(source_root).as_posix()
                            for path in (source_root / "www.tradingview.com/www.tradingview.com/support/solutions").rglob("*.html"))
        recorded_paths = {source["path"] for row in publications for source in row["sources"]}
        recorded_paths.update(item["path"] for item in data["nonpublication_files"])
        if actual_paths != recorded_paths:
            raise ValueError("physical source inventory differs from ledger")
    return {"builtins": len(builtin_rows), "publications": len(publications),
            "new_cards": len(created), "total_cards": len(cards),
            "verified_source_files": len(verified_files)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    data = json.loads((REPO / "research/tradingview-card-coverage.json").read_text())
    try:
        result = validate(data, source_root=args.source_root)
    except (ValueError, KeyError, OSError) as exc:
        print(f"TradingView card coverage: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
