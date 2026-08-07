"""Read-only catalogue and file reader behind the Docs tab.

Pure logic: no Textual import, no widget, no I/O beyond reading files the
catalogue already lists. That split is what lets this be tested without driving a
terminal, and it matches `config.py`, `roster.py` and the other modules the TUI
sits on.

## Why it reads `index/INDEX.json` rather than walking the tree

The index already knows every tracked file, its `kind`, its size, and a one-line
summary for 245 of them, and it carries a `--check` gate that fails when it drifts
from the tree. Re-walking the filesystem here would duplicate that and disagree
with it eventually. The JSON is consumed as **data** — this module never imports
anything under `index/`, so the two stay decoupled and the index remains a
build-time artifact rather than a runtime dependency.

## Why there is no editor

This is deliberately a viewer, and the omission is the point.

`research/results/` holds the evidence for every figure in `research/*.md`;
`verify_numbers.py`, `turnover_table.py --check` and `index/build.py --check` all
assume those files change through committed scripts that can be re-run. A GUI text
editor over the same tree is an unlogged, unreviewable write path into exactly that
evidence — and a truncation is silent until someone happens to read a diff.

If editing is wanted later it needs a decision about guards (an allowlist, a hard
refusal under `results/`, confirm-on-save), which is a different feature. Adding
`write_file()` to this module without those is the wrong shortcut, so the function
does not exist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_JSON = REPO / "index" / "INDEX.json"

# Refuse to load a file larger than this into a viewer widget. The largest tracked
# text file is ~75 KB, so this is generous; the cap exists so a future large CSV
# cannot hang the UI thread.
MAX_VIEW_BYTES = 2_000_000

# Extension -> Textual/Rich syntax name. Anything absent renders as plain text,
# which is correct for .txt reports and better than guessing wrong.
LANGUAGES = {
    ".py": "python", ".js": "javascript", ".json": "json", ".md": "markdown",
    ".yml": "yaml", ".yaml": "yaml", ".html": "html", ".css": "css",
    ".toml": "toml", ".sh": "bash",
}


@dataclass(frozen=True)
class DocEntry:
    """One catalogue row. Mirrors the fields the Docs tab actually shows."""

    path: str
    name: str
    directory: str
    kind: str
    summary: str
    summary_source: str
    lines: int
    size: int

    @property
    def language(self) -> str:
        return LANGUAGES.get(Path(self.path).suffix, "")


class CatalogUnavailable(RuntimeError):
    """The index has not been built. Carries the command that fixes it."""


def load_catalog(index_json: Path | None = None) -> list[DocEntry]:
    """Every tracked file, from the committed index.

    Raises `CatalogUnavailable` with the build command rather than returning an
    empty list: an empty Docs tab looks like a repo with no files, which is a much
    worse diagnostic than a sentence saying the index is missing.
    """
    src = index_json or INDEX_JSON
    if not src.exists():
        raise CatalogUnavailable(
            f"{src.relative_to(REPO) if src.is_relative_to(REPO) else src} is missing. "
            "Build it:  python3 index/build.py all"
        )
    try:
        raw = json.loads(src.read_text())
    except ValueError as exc:
        raise CatalogUnavailable(f"{src.name} is not valid JSON: {exc}") from exc

    out: list[DocEntry] = []
    for e in raw.get("files", []):
        out.append(DocEntry(
            path=e["path"],
            name=e.get("name") or Path(e["path"]).name,
            directory=e.get("dir") or "",
            kind=e.get("kind") or "other",
            summary=e.get("summary") or "",
            summary_source=e.get("summarySource") or "none",
            lines=int(e.get("lines") or 0),
            size=int(e.get("bytes") or 0),
        ))
    return sorted(out, key=lambda x: x.path)


def kinds_of(entries: list[DocEntry]) -> list[str]:
    """Kinds present, most common first — the Docs tab's filter options."""
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.kind] = counts.get(e.kind, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def filter_entries(entries: list[DocEntry], query: str = "",
                   kind: str = "") -> list[DocEntry]:
    """Substring match over path and summary, optionally narrowed to one kind.

    Matches the summary as well as the path on purpose: "evidence floor" finds the
    files that discuss it, which is what someone types, whereas a path-only filter
    would return nothing.
    """
    q = query.strip().lower()
    out = entries
    if kind:
        out = [e for e in out if e.kind == kind]
    if q:
        out = [e for e in out
               if q in e.path.lower() or q in e.summary.lower()]
    return out


def group_by_directory(entries: list[DocEntry]) -> dict[str, list[DocEntry]]:
    """Directory -> its files, for the tree. Root files group under `(root)`."""
    groups: dict[str, list[DocEntry]] = {}
    for e in entries:
        groups.setdefault(e.directory or "(root)", []).append(e)
    return {k: sorted(v, key=lambda x: x.name) for k, v in sorted(groups.items())}


def resolve(path: str, entries: list[DocEntry]) -> Path:
    """Map a catalogue path to a real file, refusing anything not catalogued.

    The catalogue is the allowlist. Without this check the Docs tab would read any
    path a caller supplied, including `../` outside the repo — and a viewer that
    can open arbitrary files is a file-disclosure surface in a process that also
    serves over HTTP.
    """
    known = {e.path for e in entries}
    if path not in known:
        raise FileNotFoundError(f"{path} is not in the catalogue")
    target = (REPO / path).resolve()
    if not target.is_relative_to(REPO.resolve()):
        raise FileNotFoundError(f"{path} resolves outside the repository")
    return target


def read_document(path: str, entries: list[DocEntry]) -> tuple[str, str]:
    """(text, language) for one catalogued file.

    Binary and oversized files return an explanatory line rather than raising, so
    selecting `SolTUI.icns` in the tree shows a sentence instead of an error dialog.
    """
    target = resolve(path, entries)
    size = target.stat().st_size
    if size > MAX_VIEW_BYTES:
        return (f"{path} is {size:,} bytes, above the {MAX_VIEW_BYTES:,}-byte "
                f"viewer limit. Open it outside the console.", "")
    try:
        text = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return (f"{path} is not UTF-8 text ({size:,} bytes) — nothing to display.", "")
    entry = next((e for e in entries if e.path == path), None)
    return text, (entry.language if entry else "")


def summarise_catalog(entries: list[DocEntry]) -> str:
    """One line for the tab header."""
    total = sum(e.size for e in entries)
    described = sum(1 for e in entries if e.summary)
    return (f"{len(entries)} files · {total / 1e6:.1f} MB · "
            f"{described} with a summary · read-only")
