#!/usr/bin/env python3
"""Compile the public tracked documentation allowlist; no inference or network."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ecosystem.wiki import (
    CANONICAL_REPO,
    MAX_PAGE_BYTES,
    MAX_PAGES,
    SCHEMA_VERSION,
    canonical,
    classification,
    page_id,
    selected_source,
)


def _git(repo: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments], cwd=repo, check=True, capture_output=True, timeout=30
    ).stdout


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == raw:
        return
    fd, temporary = tempfile.mkstemp(prefix=".wiki-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def compile_snapshot(
    repo: Path, output: Path, *, refresh_provenance: bool = False
) -> tuple[bytes, bytes]:
    """Bind exact source bytes and retain unchanged pages' build provenance."""
    tracked = _git(repo, "ls-files", "-z").decode().split("\0")
    paths = sorted({path for path in tracked if selected_source(path)})
    selected = set(paths)
    if not 0 < len(paths) <= MAX_PAGES:
        raise ValueError("invalid_wiki_source_count")
    head_blobs = {}
    for entry in _git(repo, "ls-tree", "-r", "-z", "HEAD").decode().split("\0"):
        if entry:
            header, name = entry.split("\t", 1)
            head_blobs[name] = header.split()[2]
    # One history traversal establishes each file's last content-changing commit.
    history = _git(
        repo,
        "log",
        "--format=@%H",
        "--name-only",
        "HEAD",
        "--",
        *sorted({str(Path(p).parts[0]) for p in paths}),
    ).decode()
    revisions = {}
    commit = None
    for line in history.splitlines():
        if line.startswith("@"):
            commit = line[1:]
        elif line in selected and line not in revisions:
            revisions[line] = commit
    previous = {}
    try:
        saved = json.loads((output / "manifest.json").read_text())
        previous = {item["source_path"]: item for item in saved["pages"]}
    except (OSError, ValueError, TypeError, KeyError):
        pass
    bundle, rows = {}, []
    for source in paths:
        path = repo / source
        components = Path(source).parts
        if (
            any(
                (repo / Path(*components[:length])).is_symlink()
                for length in range(1, len(components) + 1)
            )
            or not path.is_file()
            or path.stat().st_size > MAX_PAGE_BYTES
        ):
            raise ValueError("invalid_wiki_source")
        raw = path.read_bytes()
        body = raw.decode("utf-8")
        identity = page_id(source)
        digest = hashlib.sha256(raw).hexdigest()
        match = re.search(r"^#{1,6}\s+(.+?)\s*#*\s*$", body, re.MULTILINE)
        title = (match.group(1) if match else path.stem.replace("_", " "))[:300]
        category, kind, priority = classification(source)
        git_blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode() + raw, usedforsecurity=False
        ).hexdigest()
        source_commit = (
            revisions.get(source) if git_blob == head_blobs.get(source) else None
        )
        provenance = {
            "source_commit": source_commit,
            "source_state": "committed" if source_commit else "working_tree_snapshot",
        }
        prior = previous.get(source)
        # A snapshot records where bytes came from at build time. Merely
        # committing identical bytes does not invalidate that truthful record.
        if (
            not refresh_provenance
            and isinstance(prior, dict)
            and prior.get("content_sha256") == digest
            and prior.get("source_state") in {"committed", "working_tree_snapshot"}
            and (
                prior.get("source_commit") is None
                or isinstance(prior.get("source_commit"), str)
            )
        ):
            provenance = {key: prior[key] for key in ("source_commit", "source_state")}
        rows.append(
            {
                "id": identity,
                "title": title,
                "category": category,
                "kind": kind,
                "priority": priority,
                "source_path": source,
                "source_location": f"{CANONICAL_REPO}/{source}",
                "content_sha256": digest,
                **provenance,
                "source_url": f"https://github.com/mithudso/solmargintrader/blob/{provenance['source_commit']}/{source}"
                if provenance["source_commit"]
                else None,
                "is_execution_evidence": False,
            }
        )
        bundle[identity] = body
    bundle_raw = canonical(bundle)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "format": "source-markdown-snapshot",
        "bundle_sha256": hashlib.sha256(bundle_raw).hexdigest(),
        "total": len(rows),
        "pages": rows,
    }
    manifest["snapshot_sha256"] = hashlib.sha256(canonical(manifest)).hexdigest()
    return canonical(manifest), bundle_raw


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-provenance", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.expanduser().resolve()
    output = args.output or repo / "ecosystem/wiki_content"
    try:
        manifest, bundle = compile_snapshot(
            repo, output, refresh_provenance=args.refresh_provenance
        )
        if args.check:
            valid = (output / "manifest.json").read_bytes() == manifest and (
                output / "pages.json"
            ).read_bytes() == bundle
            print(json.dumps({"ok": valid, "status": "current" if valid else "stale"}))
            return 0 if valid else 1
        _write(output / "pages.json", bundle)
        _write(output / "manifest.json", manifest)
        summary = json.loads(manifest)
        print(
            json.dumps(
                {
                    "ok": True,
                    "pages": summary["total"],
                    "snapshot_sha256": summary["snapshot_sha256"],
                    "bundle_bytes": len(bundle),
                }
            )
        )
        return 0
    except (
        OSError,
        ValueError,
        UnicodeError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ):
        print(json.dumps({"ok": False, "error": "wiki_build_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
