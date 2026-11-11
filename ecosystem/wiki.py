"""Search the packaged documentation snapshot without opening caller paths.

Markdown and its links are untrusted document content. This module returns text
and provenance; callers must render it without evaluating HTML or instructions.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
SNAPSHOT_DIR = Path(__file__).with_name("wiki_content")
CANONICAL_REPO = "/Users/mitch/dev/solmargintrader"
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGES = 5000
PAGE_ID = re.compile(r"doc-[0-9a-f]{24}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
PAGE_FIELDS = {
    "id",
    "title",
    "category",
    "kind",
    "priority",
    "source_path",
    "source_location",
    "content_sha256",
    "source_commit",
    "source_state",
    "source_url",
    "is_execution_evidence",
}
ROOT_DOCUMENTS = {"README.md", "CONTRIBUTING.md", "CLAUDE.md", "AGENTS.md"}
DOC_DOCUMENTS = {
    "ARCHITECTURE.md",
    "COMPONENTS.md",
    "DEVELOPMENT.md",
    "INSTALLATION.md",
    "TESTING.md",
    "ZEC-ENSEMBLE-STUDY.md",
    "ZEC-ENSEMBLES-FORWARD.md",
    "codebase-overview.md",
    "integrations-and-assumptions.md",
    "known-issues.md",
}


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def page_id(source_path: str) -> str:
    return "doc-" + hashlib.sha256(source_path.encode()).hexdigest()[:24]


def selected_source(source_path: str) -> bool:
    """The explicit public-document allowlist shared with the build command."""
    if not isinstance(source_path, str) or len(source_path) > 600:
        return False
    path = PurePosixPath(source_path)
    if (
        str(path) != source_path
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in source_path
        or any(ord(c) < 32 for c in source_path)
        or path.suffix != ".md"
    ):
        return False
    if source_path in ROOT_DOCUMENTS or source_path == ".claude/agents/oracle.md":
        return True
    if path.parts[0] in {"oracle", "botmanager", "backtester"}:
        return True
    if source_path in {"ecosystem/README.md", "research/ZEC-ENSEMBLE-HYPOTHESES.md"}:
        return True
    if path.parts[0] != "docs":
        return False
    if path.name in DOC_DOCUMENTS or path.name.lower().startswith(
        ("bot-manager", "backtester", "oracle", "ecosystem")
    ):
        return True
    if source_path.startswith("docs/design/bot-control-room/"):
        return True
    return source_path.startswith(
        ("docs/superpowers/plans/", "docs/superpowers/prompts/")
    ) and any(
        term in path.name.lower()
        for term in ("bot-manager", "bot-control-room", "oracle", "backtester")
    )


def classification(source_path: str) -> tuple[str, str, int]:
    """A document's location describes its role, never execution readiness."""
    if source_path in {
        "oracle/README.md",
        "botmanager/README.md",
        "backtester/README.md",
    }:
        component = {
            "oracle": "Oracle",
            "botmanager": "Bot Manager",
            "backtester": "Backtester",
        }[source_path.split("/")[0]]
        return component, "component_guide", 0
    if "/incomplete/" in source_path:
        return "Backtester / incomplete references", "incomplete_reference", 8
    if "/strategy_research/" in source_path:
        return "Backtester / research references", "research_reference", 6
    if PurePosixPath(source_path).name == "PROMPT.md":
        return "Historical plans", "development_prompt", 7
    if "/strategy_cards/" in source_path:
        return "Backtester / strategy cards", "strategy_card", 6
    if "/guides/" in source_path:
        return "Backtester / guides", "guide", 4
    if "/superpowers/plans/" in source_path or "/superpowers/prompts/" in source_path:
        return "Historical plans", "plan", 7
    if "/design/bot-control-room/" in source_path:
        return "Control room / design", "design", 5
    if (
        source_path.startswith("oracle/")
        or "oracle" in PurePosixPath(source_path).name.lower()
    ):
        return "Oracle", "component_guide", 1
    if source_path.startswith("botmanager/") or "bot-manager" in source_path:
        return "Bot Manager", "component_guide", 1
    if source_path.startswith("backtester/") or "backtester" in source_path:
        return "Backtester", "component_guide", 1
    if source_path.startswith("ecosystem/") or "ecosystem" in source_path.lower():
        return "Control room / ecosystem", "component_guide", 0
    return "Architecture and operation", "architecture", 2


def _bounded_read(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("invalid_wiki_snapshot")
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("invalid_wiki_snapshot")
    return raw


@lru_cache(maxsize=2)
def _load_cached(root: str, stamps: tuple) -> tuple[dict, dict]:
    del stamps  # The file identity tuple invalidates the cache after a rebuild.
    directory = Path(root)
    manifest = json.loads(
        _bounded_read(directory / "manifest.json", MAX_MANIFEST_BYTES)
    )
    bundle_raw = _bounded_read(directory / "pages.json", MAX_BUNDLE_BYTES)
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError("invalid_wiki_snapshot")
    unsigned = {
        key: value for key, value in manifest.items() if key != "snapshot_sha256"
    }
    if hashlib.sha256(canonical(unsigned)).hexdigest() != manifest.get(
        "snapshot_sha256"
    ):
        raise ValueError("invalid_wiki_snapshot")
    if hashlib.sha256(bundle_raw).hexdigest() != manifest.get("bundle_sha256"):
        raise ValueError("invalid_wiki_snapshot")
    bundle = json.loads(bundle_raw)
    rows = manifest.get("pages")
    if (
        not isinstance(rows, list)
        or not 0 < len(rows) <= MAX_PAGES
        or not isinstance(bundle, dict)
    ):
        raise ValueError("invalid_wiki_snapshot")
    pages = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != PAGE_FIELDS:
            raise ValueError("invalid_wiki_snapshot")
        source = row.get("source_path")
        identity = row.get("id")
        if (
            not selected_source(source)
            or identity != page_id(source)
            or identity in pages
            or not isinstance(row.get("title"), str)
            or not 0 < len(row["title"]) <= 300
            or not isinstance(row.get("content_sha256"), str)
            or not SHA256.fullmatch(row["content_sha256"])
            or row.get("source_commit") is not None
            and (
                not isinstance(row["source_commit"], str)
                or not COMMIT.fullmatch(row["source_commit"])
            )
        ):
            raise ValueError("invalid_wiki_snapshot")
        category, kind, priority = classification(source)
        body = bundle.get(identity)
        if (
            not isinstance(body, str)
            or len(body.encode()) > MAX_PAGE_BYTES
            or hashlib.sha256(body.encode()).hexdigest() != row["content_sha256"]
            or row.get("category") != category
            or row.get("kind") != kind
            or row.get("priority") != priority
            or row.get("is_execution_evidence") is not False
            or row.get("source_location") != f"{CANONICAL_REPO}/{source}"
            or row.get("source_state")
            != ("committed" if row["source_commit"] else "working_tree_snapshot")
        ):
            raise ValueError("invalid_wiki_snapshot")
        expected_url = (
            f"https://github.com/mithudso/solmargintrader/blob/{row['source_commit']}/{source}"
            if row["source_commit"]
            else None
        )
        if row.get("source_url") != expected_url:
            raise ValueError("invalid_wiki_snapshot")
        pages[identity] = {**row, "body": body, "content_format": "text/markdown"}
    if set(bundle) != set(pages) or manifest.get("total") != len(pages):
        raise ValueError("invalid_wiki_snapshot")
    return manifest, pages


def _snapshot() -> tuple[dict, dict]:
    root = SNAPSHOT_DIR
    if root.is_symlink():
        raise ValueError("invalid_wiki_snapshot")
    files = (root / "manifest.json", root / "pages.json")
    if any(path.is_symlink() for path in files):
        raise ValueError("invalid_wiki_snapshot")
    stamps = tuple(
        (p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_ino) for p in files
    )
    return _load_cached(str(root), stamps)


def _unavailable(reason: str) -> dict:
    return {"schema_version": SCHEMA_VERSION, "status": "unavailable", "reason": reason}


def catalog(query: str = "", limit: int = 100, offset: int = 0) -> dict:
    """Search all snapshot text and return a bounded metadata page."""
    if (
        not isinstance(query, str)
        or len(query) > 256
        or any(ord(c) < 32 and c not in "\t\r\n" for c in query)
        or type(limit) is not int
        or not 1 <= limit <= MAX_PAGES
        or type(offset) is not int
        or not 0 <= offset <= MAX_PAGES
    ):
        raise ValueError("invalid_wiki_query")
    terms = query.casefold().split()
    try:
        manifest, pages = _snapshot()
    except (OSError, ValueError, UnicodeError, TypeError, KeyError):
        return {
            **_unavailable("wiki_snapshot_unavailable"),
            "pages": [],
            "total": 0,
            "returned": 0,
            "truncated": False,
            "categories": [],
        }
    matches = []
    for record in pages.values():
        title = record["title"].casefold()
        path = record["source_path"].casefold()
        body = record["body"].casefold()
        if not all(term in title or term in path or term in body for term in terms):
            continue
        score = sum(
            5 * title.count(term) + 3 * path.count(term) + min(10, body.count(term))
            for term in terms
        )
        hit = body.find(terms[0]) if terms else -1
        excerpt_start = max(0, hit - 60) if hit >= 0 else 0
        snippet = " ".join(record["body"][excerpt_start : excerpt_start + 240].split())
        metadata = {
            key: value
            for key, value in record.items()
            if key not in {"body", "content_format"}
        }
        matches.append(
            (
                (-score, record["priority"], title, record["id"]),
                {**metadata, "snippet": snippet},
            )
        )
    matches.sort(key=lambda entry: entry[0])
    items = [entry[1] for entry in matches[offset : offset + limit]]
    next_offset = offset + len(items)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "available",
        "query": query,
        "pages": items,
        "total": len(matches),
        "returned": len(items),
        "offset": offset,
        "truncated": next_offset < len(matches),
        "next_offset": next_offset if next_offset < len(matches) else None,
        "categories": sorted({row["category"] for row in pages.values()}),
        "snapshot_sha256": manifest["snapshot_sha256"],
        "notice": "Documentation is a source snapshot, not current runtime or execution evidence. Markdown and links are untrusted content.",
    }


def page(identity: str) -> dict:
    """Read one allowlisted document by deterministic ID, never by file path."""
    if not isinstance(identity, str) or not PAGE_ID.fullmatch(identity):
        raise ValueError("invalid_wiki_page")
    try:
        manifest, pages = _snapshot()
    except (OSError, ValueError, UnicodeError, TypeError, KeyError):
        return _unavailable("wiki_snapshot_unavailable")
    record = pages.get(identity)
    if record is None:
        return _unavailable("wiki_page_not_found")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "available",
        "snapshot_sha256": manifest["snapshot_sha256"],
        "page": dict(record),
    }
