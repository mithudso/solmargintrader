#!/usr/bin/env python3
"""Generate `docs/high_signal_file_index.json` from `docs/codebase-overview.md`.

    python3 scripts/build_doc_index.py

The overview is the human-readable file map; the JSON is the machine-readable
one for LLM retrieval. Deriving the second from the first means they cannot
disagree -- two hand-maintained lists of the same files would drift within a
week, and the drift is invisible until an agent is told a file exists that does
not.

Every entry comes from a table row of the form:

    | `path/to/file.py` | what it is |

Rows naming a path that does not exist are skipped and reported, so a rename
shows up here rather than silently producing a dead index entry.
`scripts/check_docs.py` then validates the result in CI.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OVERVIEW = REPO / "docs" / "codebase-overview.md"
INDEX = REPO / "docs" / "high_signal_file_index.json"

COMPONENTS = ("backtester", "research", "extension", "soltui")

# `| `some/path` | description |` -- the table shape used throughout the overview.
ROW = re.compile(r"^\| `([\w./-]+)` \| (.+?) \|$", re.MULTILINE)

KIND_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".md": "markdown",
    ".json": "json",
    ".txt": "text",
    ".yml": "yaml",
    ".html": "html",
    ".css": "css",
}


def is_ignored(rel: str) -> bool:
    """True when git deliberately ignores `rel` (so its absence is expected).

    Both spellings are tried: `.gitignore` writes directory rules with a trailing
    slash (`data/`), and `git check-ignore` will not match that rule against a
    bare name when the directory does not exist on disk -- which is precisely the
    case this has to answer.
    """
    for candidate in (rel, f"{rel}/"):
        done = subprocess.run(
            ["git", "check-ignore", "-q", "--", candidate],
            cwd=REPO,
            capture_output=True,
        )
        if done.returncode == 0:
            return True
    return False


def component_of(rel: str) -> str:
    """Which component a path belongs to, or 'repo' for top-level files."""
    head = rel.split("/", 1)[0]
    return head if head in COMPONENTS else "repo"


def build() -> tuple[list[dict[str, object]], list[str]]:
    """Index entries plus the list of rows naming a missing path."""
    text = OVERVIEW.read_text(encoding="utf-8")
    entries: list[dict[str, object]] = []
    missing: list[str] = []
    seen: set[str] = set()

    for raw, description in ROW.findall(text):
        # Directory rows are written with a trailing slash in the overview.
        rel = raw.rstrip("/")
        if rel in seen:
            continue
        seen.add(rel)
        path = REPO / rel
        if not path.exists():
            # `data/` and `results/` are regenerable and gitignored, so their
            # absence is expected rather than drift. Anything else is a rename
            # the overview has not caught up with.
            if not is_ignored(rel):
                missing.append(rel)
            continue
        entry: dict[str, object] = {
            "path": rel,
            "component": component_of(rel),
            "kind": (
                "directory"
                if path.is_dir()
                else KIND_BY_SUFFIX.get(path.suffix, "other")
            ),
            # Strip the overview's emphasis markers: the JSON is read by machines
            # that have no use for bold.
            "summary": re.sub(r"[*`]", "", description).strip(),
        }
        if path.is_file():
            entry["lines"] = len(
                path.read_text(encoding="utf-8", errors="replace").splitlines()
            )
        entries.append(entry)

    return entries, missing


def main() -> int:
    """Write the index; report any row that names a path which no longer exists."""
    entries, missing = build()
    payload = {
        "$comment": (
            "Generated from docs/codebase-overview.md by "
            "scripts/build_doc_index.py. Do not hand-edit; regenerate instead. "
            "Validated in CI by scripts/check_docs.py."
        ),
        "repo": "solmargintrader",
        "components": list(COMPONENTS),
        "files": entries,
    }
    INDEX.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for rel in missing:
        print(f"skipped missing path: {rel}", file=sys.stderr)
    print(f"wrote {INDEX.relative_to(REPO)} with {len(entries)} entries")
    # A missing path is a real problem, but it is the overview that needs fixing,
    # so report it and let check_docs.py be the gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
