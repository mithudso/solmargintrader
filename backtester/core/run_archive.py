"""Transactional archive for completed backtester artifact bundles.

A manifest proves byte consistency, not the accuracy or completeness of a model.
This module does not execute strategies or fetch market data.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3


class ArchiveError(ValueError):
    """A run or archive does not meet the integrity contract."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ArchiveError(f"duplicate manifest key: {key}")
        result[key] = value
    return result


def _inventory(manifest: object) -> dict:
    if not isinstance(manifest, dict):
        raise ArchiveError("invalid run manifest")
    required = {"asset", "start", "end", "interval", "mode", "leverage", "initial_capital",
                "fill_delay", "seed", "rebalance_threshold", "costs", "strategies",
                "data_source", "data_checksum", "bar_count", "split", "library_versions",
                "periods_per_year", "sharpe_convention", "artifact_sha256"}
    if not required.issubset(manifest):
        raise ArchiveError("incomplete run manifest")
    strategies = manifest["strategies"]
    inventory = manifest["artifact_sha256"]
    if not isinstance(strategies, dict) or not strategies or not isinstance(inventory, dict):
        raise ArchiveError("invalid strategies or artifact inventory")
    names = {"comparison.csv", "report.md"}
    for name in strategies:
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or "\x00" in name:
            raise ArchiveError("unsafe strategy name")
        names.update({f"trades_{name}.csv", f"equity_{name}.csv"})
    if not names.issubset(inventory):
        raise ArchiveError("incomplete artifact inventory")
    return inventory


def _bundle(directory: Path) -> tuple[bytes, dict[str, bytes]]:
    manifest_path = directory / "run_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ArchiveError("missing or unsafe run manifest")
    raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(raw, object_pairs_hook=_unique_object)
        inventory = _inventory(manifest)
    except (ValueError, KeyError, TypeError) as exc:
        raise ArchiveError("invalid run manifest") from exc
    if not isinstance(inventory, dict) or not inventory:
        raise ArchiveError("empty or invalid artifact inventory")
    artifacts: dict[str, bytes] = {}
    for name, expected in inventory.items():
        if (not isinstance(name, str) or name in {"", ".", "..", "run_manifest.json"}
                or "/" in name or "\\" in name or "\x00" in name):
            raise ArchiveError("unsafe artifact name")
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ArchiveError(f"invalid artifact digest: {name}")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ArchiveError(f"missing or unsafe artifact: {name}")
        data = path.read_bytes()
        if _digest(data) != expected:
            raise ArchiveError(f"artifact digest mismatch: {name}")
        artifacts[name] = data
    return raw, artifacts


def _connect(path: Path) -> sqlite3.Connection:
    if path.is_symlink():
        raise ArchiveError("archive path must not be a symlink")
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise ArchiveError("archive must be a private regular file (mode 600)")
    db = sqlite3.connect(path, timeout=30)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA synchronous = FULL")
    db.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, manifest BLOB NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS artifacts (run_id TEXT NOT NULL REFERENCES runs(run_id), name TEXT NOT NULL, content BLOB NOT NULL, PRIMARY KEY(run_id, name))")
    return db


def import_run(archive: str | Path, directory: str | Path) -> str:
    """Store an exact verified bundle atomically; repeated imports are idempotent."""
    manifest, artifacts = _bundle(Path(directory))
    run_id = _digest(manifest)
    with closing(_connect(Path(archive))) as db, db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT manifest FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if old is not None:
            if bytes(old[0]) != manifest or _read(db, run_id) != (manifest, artifacts):
                raise ArchiveError("existing run differs from imported bundle")
            return run_id
        db.execute("INSERT INTO runs VALUES (?, ?)", (run_id, manifest))
        db.executemany("INSERT INTO artifacts VALUES (?, ?, ?)",
                       ((run_id, name, data) for name, data in sorted(artifacts.items())))
    return run_id


def _read(db: sqlite3.Connection, run_id: str) -> tuple[bytes, dict[str, bytes]]:
    row = db.execute("SELECT manifest FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise ArchiveError("run not found")
    manifest = bytes(row[0])
    if _digest(manifest) != run_id:
        raise ArchiveError("stored manifest digest mismatch")
    try:
        inventory = _inventory(json.loads(manifest, object_pairs_hook=_unique_object))
    except (ValueError, KeyError, TypeError) as exc:
        raise ArchiveError("invalid stored manifest") from exc
    artifacts = {name: bytes(data) for name, data in db.execute(
        "SELECT name, content FROM artifacts WHERE run_id = ? ORDER BY name", (run_id,))}
    if not isinstance(inventory, dict) or not inventory or set(inventory) != set(artifacts):
        raise ArchiveError("stored artifact inventory mismatch")
    if any(_digest(data) != inventory[name] for name, data in artifacts.items()):
        raise ArchiveError("stored artifact digest mismatch")
    return manifest, artifacts


def read_run(archive: str | Path, run_id: str) -> tuple[bytes, dict[str, bytes]]:
    """Read and verify every byte of a stored run; raise if anything changed."""
    path = Path(archive)
    if not path.exists():
        raise ArchiveError("archive not found")
    with closing(_connect(path)) as db:
        return _read(db, run_id)


def backup_archive(archive: str | Path, destination: str | Path) -> None:
    """Create and verify a new consistent SQLite backup without overwriting files."""
    source = Path(archive)
    target = Path(destination)
    if not source.exists():
        raise ArchiveError("archive not found")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(_connect(source)) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ArchiveError("backup database integrity check failed")
            for (run_id,) in dst.execute("SELECT run_id FROM runs"):
                _read(dst, run_id)
            exists = dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='history_snapshots'").fetchone()
            if exists:
                from .history_store import _verify
                for (snapshot_id,) in dst.execute("SELECT snapshot_id FROM history_snapshots"):
                    _verify(dst, snapshot_id)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog="Example: python -m backtester.core.run_archive runs.db results/")
    parser.add_argument("archive", type=Path)
    parser.add_argument("directory", type=Path, help="completed output directory")
    args = parser.parse_args()
    print(import_run(args.archive, args.directory))


if __name__ == "__main__":
    main()
