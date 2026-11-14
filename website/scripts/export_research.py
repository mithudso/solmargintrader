"""Export tracked public research into deterministic metadata and body shards.

This is a publication transform, not another research verdict. Original source
hashes and transformed-body hashes remain distinct. Never export private stores,
local account state, workflows, credentials or the scraped jup.ag mirror.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "website/public/research"
SHARD_BYTES = 500_000
EXCLUDE_WORDS = ("prompt", "ddo-report", "audit_integrity", "audit_realism", "run-report", "competency-questions")
SENSITIVE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk_live_|sk_test_|rk_live_|whsec_)[A-Za-z0-9]{12,}")


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def public_body(text):
    # Preserve research conclusions, but do not publish workstation locations.
    text = re.sub(r"/Users/[^\s)\]`<>\"']+", "[local artifact not published]", text)
    text = re.sub(r"(?<!\w)~/(?:\.local|\.config|\.ssh|\.research|\.global-ai-hub)/[^\s)\]`<>\"']+", "[local artifact not published]", text)
    return text


def title_summary(source, text):
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    name_match = re.search(r"^name:\s*[\"']?(.+?)[\"']?\s*$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else name_match.group(1) if name_match else Path(source).stem.replace("_", " ").replace("-", " ").title()
    title = re.sub(r"[`*_]", "", title)
    summary_match = re.search(r"^summary:\s*[\"']?(.+?)[\"']?\s*$", text, flags=re.MULTILINE)
    if summary_match:
        summary = summary_match.group(1)
    else:
        body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
        paragraphs = re.split(r"\n\s*\n", body)
        summary = next((p for p in paragraphs if p.strip() and not p.lstrip().startswith(("#", "|", "```", "Version:", "Delta:", "["))), "Original research notes and limitations.")
        summary = " ".join(summary.split())
        summary = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", summary)
        summary = re.sub(r"[`*_>]", "", summary)
    return title[:220], summary[:320]


def export(repo=ROOT):
    repo = Path(repo).resolve()
    names = subprocess.check_output(["git", "ls-files", "-z", "research", "backtester/strategy_cards"], cwd=repo).decode().split("\0")
    articles, skipped, bodies = [], [], []
    for source in sorted(filter(None, names)):
        if not source.endswith(".md"):
            continue
        if any(word in source.lower() for word in EXCLUDE_WORDS) or Path(source).name in ("FILES.md",):
            skipped.append({"source": source, "reason": "workflow_or_review_artifact"})
            continue
        candidate = repo / source
        # Git tracks symlinks, and an untracked parent can also redirect a tracked
        # name. Refuse both before reading any content outside the publication tree.
        if candidate.resolve() != candidate:
            raise ValueError(f"symlink refused in {source}")
        original = candidate.read_bytes()
        text = original.decode("utf-8")
        if SENSITIVE.search(text):
            raise ValueError(f"credential-like content refused in {source}")
        body = public_body(text)
        title, summary = title_summary(source, body)
        slug = re.sub(r"[^a-z0-9]+", "-", Path(source).stem.lower()).strip("-")[:100] + "-" + hashlib.sha256(source.encode()).hexdigest()[:8]
        incomplete = "/incomplete/" in source
        category = "Incomplete profiles" if incomplete else "TradingView profiles" if "/publication-profiles/" in source or "/native-strategy-profiles/" in source else "Strategy cards" if source.startswith("backtester/") else "Coin intelligence" if "/coin-intelligence/" in source else "Research studies"
        status = "incomplete: not coin-test ready" if incomplete else "historical research: not a live recommendation"
        sha = hashlib.sha256(original).hexdigest()
        articles.append({"slug": slug, "title": title, "summary": summary, "category": category, "source": source, "sourceSha256": sha, "status": status})
        bodies.append({"body": body, "sourceSha256": sha, "publishedSha256": hashlib.sha256(body.encode()).hexdigest()})
    shards, pending, size = [], {}, 0
    for article, body in zip(articles, bodies):
        item_size = len(encoded(body))
        if pending and size + item_size > SHARD_BYTES:
            shards.append(pending)
            pending, size = {}, 0
        article["bodyPath"] = f"/research/bodies-{len(shards):02d}.json"
        article["bodyKey"] = article["slug"]
        pending[article["slug"]] = body
        size += item_size
    if pending:
        shards.append(pending)
    articles.sort(key=lambda a: (0 if a["category"] == "Research studies" else 1, a["category"], a["title"].lower()))
    files = {f"bodies-{i:02d}.json": encoded({"articles": shard}) for i, shard in enumerate(shards)}
    files["catalog.json"] = encoded({"version": 1, "articles": articles, "publicationNote": "Original research with source hashes. Historical measurements and incomplete profiles retain their caveats. Local workstation paths are withheld."})
    # The public selector is a generated view of the actual canonical registry.
    from website.engine.server import catalogue
    files["strategies.json"] = encoded(catalogue())
    files["manifest.json"] = encoded({"version": 1, "articleCount": len(articles), "bodyShards": len(shards), "scope": ["tracked research/**/*.md", "tracked backtester/strategy_cards/**/*.md"], "excluded": skipped, "transforms": ["private workstation paths withheld; original source hash retained"], "files": {key: hashlib.sha256(value).hexdigest() for key, value in files.items()}})
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = export()
    stale = [key for key, body in files.items() if not (OUTPUT / key).is_file() or (OUTPUT / key).read_bytes() != body]
    extra = [p.name for p in OUTPUT.glob("*.json") if p.name not in files]
    if args.check:
        if stale or extra:
            raise SystemExit("research export stale: " + ", ".join(stale + extra))
        print(f"Research export current: {len(files)} files")
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for key, body in files.items():
        (OUTPUT / key).write_bytes(body)
    for name in extra:
        (OUTPUT / name).unlink()
    print(f"Exported {len(files)} files; {len(files['catalog.json'])} catalog bytes")


if __name__ == "__main__":
    main()
