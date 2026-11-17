"""Read-only catalogue and file reader behind the Docs tab.

No Textual import or widgets. Reads are limited to catalogued files; guarded
saves use content revisions, per-document locks, and atomic replacements. That split is what lets this be tested without driving a
terminal, and it matches `config.py`, `roster.py` and the other modules the TUI
sits on.

## Why it reads `index/INDEX.json` rather than walking the tree

The index already knows every tracked file, its `kind`, its size, and a one-line
summary for 245 of them, and it carries a `--check` gate that fails when it drifts
from the tree. Re-walking the filesystem here would duplicate that and disagree
with it eventually. The JSON is consumed as **data** — this module never imports
anything under `index/`, so the two stay decoupled and the index remains a
build-time artifact rather than a runtime dependency.

## Editing, and why `research/results/` is excluded

`write_document()` below is a narrow exception to what was originally a pure
viewer. The guards anticipated when that decision was made are implemented as:

- **allowlist** — `resolve()` already refuses any path not in the catalogue
  (the index build), and `write_document()` reuses it, so this can never
  become an arbitrary-path write.
- **hard refusal under `results/`** — `research/results/` holds the evidence
  for every figure in `research/*.md`; `verify_numbers.py`,
  `turnover_table.py --check` and `index/build.py --check` all assume those
  files change through committed scripts that can be re-run. A GUI text
  editor over the same tree would be an unlogged, unreviewable write path
  into exactly that evidence, so `is_editable()` says no for anything under
  it and `write_document()` refuses regardless of caller.
- **confirm-on-save** — left to the caller (the Save button in `tui.py`),
  since that is a UI concern, not a policy one.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_JSON = REPO / "index" / "INDEX.json"

# Refuse to load a file larger than this into a viewer widget. The largest tracked
# text file is ~75 KB, so this is generous; the cap exists so a future large CSV
# cannot hang the UI thread.
MAX_VIEW_BYTES = 2_000_000

# Directories no write may touch, regardless of caller. research/results/ is
# evidence: everything in it is meant to change only by re-running the driver
# that produced it (see verify_numbers.py, turnover_table.py --check).
NO_WRITE_PREFIXES = ("research/results/",)

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


class _DocumentTooLarge(ValueError):
    pass


def _read_bounded(target: Path) -> bytes:
    with target.open("rb") as stream:
        raw = stream.read(MAX_VIEW_BYTES + 1)
    if len(raw) > MAX_VIEW_BYTES:
        raise _DocumentTooLarge("The document exceeds the viewer limit")
    return raw


def read_document(path: str, entries: list[DocEntry]) -> tuple[str, str, bool]:
    """(text, language, is_real_text) for one catalogued file.

    Binary and oversized files return an explanatory line rather than raising, so
    selecting `SolTUI.icns` in the tree shows a sentence instead of an error
    dialog -- `is_real_text` is False in that case, which is what tells the
    caller not to offer a Save button next to a placeholder sentence.
    """
    target = resolve(path, entries)
    size = target.stat().st_size
    if size > MAX_VIEW_BYTES:
        return (f"{path} is {size:,} bytes, above the {MAX_VIEW_BYTES:,}-byte "
                f"viewer limit. Open it outside the console.", "", False)
    try:
        text = _read_bounded(target).decode("utf-8")
    except _DocumentTooLarge:
        return (f"{path} exceeds the {MAX_VIEW_BYTES:,}-byte viewer limit. Open it outside the console.", "", False)
    except (UnicodeDecodeError, OSError):
        return (f"{path} is not UTF-8 text ({size:,} bytes) — nothing to display.",
                "", False)
    entry = next((e for e in entries if e.path == path), None)
    return text, (entry.language if entry else ""), True


def is_editable(entry: DocEntry) -> bool:
    """Cheap, metadata-only editability check for the catalogue and listing.

    Deliberately does not open the file: `summarise_catalog` and the file
    table run this over every entry (~270 files) on every catalogue load, and
    a decode-check per file there would mean reading the whole repo's text on
    every Docs-tab open. `kind == "other"` catches binaries (icons, etc.) and
    unclassified files; the real UTF-8-decodability check happens once, at
    selection time, via `read_document`'s third return value -- that is the
    authoritative answer `write_document` and the Save button rely on.
    """
    if any(entry.path.startswith(p) for p in NO_WRITE_PREFIXES):
        return False
    if entry.kind in ("result", "other"):
        return False
    return entry.size <= MAX_VIEW_BYTES


def document_revision(text: str) -> str:
    """Exact UTF-8 content revision; line endings are part of the precondition."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_document(path: str, text: str, entries: list[DocEntry], *, expected_revision: str | None = None) -> Path:
    """Replace editable text only while its observed revision still matches.

    The stable per-document lock coordinates native/API/TUI processes across
    configuration profiles. An atomic replacement preserves the prior complete
    file on failure. Protected results never enter this write path.
    """
    entry = next((e for e in entries if e.path == path), None)
    if entry is None or not is_editable(entry):
        raise PermissionError(f"{path} is not editable")
    target = resolve(path, entries)
    canonical_path = target.relative_to(REPO.resolve()).as_posix()
    if any(canonical_path.startswith(prefix) for prefix in NO_WRITE_PREFIXES):
        raise PermissionError(f"{path} resolves to protected research evidence")
    if not isinstance(expected_revision, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_revision):
        raise ValueError("A document revision from docs.read is required")
    payload = text.encode("utf-8")
    if len(payload) > MAX_VIEW_BYTES:
        raise ValueError("New document exceeds the viewer limit")
    # A fixed host-local root keeps different TMPDIR/configuration profiles
    # on the same lock. This application targets macOS/POSIX.
    lock_dir = Path("/tmp") / f"soltui-doc-locks-{os.getuid()}"
    lock_dir.mkdir(mode=0o700, exist_ok=True)
    lock_stat = lock_dir.lstat()
    if (not stat.S_ISDIR(lock_stat.st_mode) or lock_stat.st_uid != os.getuid()
            or stat.S_IMODE(lock_stat.st_mode) & 0o077):
        raise PermissionError("Document lock directory is not private")
    lock_name = hashlib.sha256(os.fsencode(str(target))).hexdigest() + ".lock"
    fd = os.open(lock_dir / lock_name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    tmp = None
    try:
        lock_file_stat = os.fstat(fd)
        if (not stat.S_ISREG(lock_file_stat.st_mode) or lock_file_stat.st_uid != os.getuid()
                or stat.S_IMODE(lock_file_stat.st_mode) & 0o077):
            raise PermissionError("Document lock file is not private")
        fcntl.flock(fd, fcntl.LOCK_EX)
        # Resolve again inside the lock: a stale catalogue cannot redirect a save.
        if resolve(path, entries) != target:
            raise ValueError("The document path changed; reload before saving")
        before = _read_bounded(target)
        before.decode("utf-8")
        if hashlib.sha256(before).hexdigest() != expected_revision:
            raise ValueError("The document changed; reload before saving")
        mode = stat.S_IMODE(target.stat().st_mode)
        tmp_fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        tmp = Path(tmp_name)
        with os.fdopen(tmp_fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return target
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        os.close(fd)


def summarise_catalog(entries: list[DocEntry]) -> str:
    """One line for the tab header."""
    total = sum(e.size for e in entries)
    described = sum(1 for e in entries if e.summary)
    editable = sum(1 for e in entries if is_editable(e))
    return (f"{len(entries)} files · {total / 1e6:.1f} MB · "
            f"{described} with a summary · {editable} editable, rest read-only")
