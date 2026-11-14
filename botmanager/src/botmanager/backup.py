"""Quiescent manager snapshots; canonical research authority stays external.

Restore verifies dependencies before creating a new home. It never installs a
service, starts a worker, or copies the canonical optimizer database.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import sqlite3
import tempfile
import time
from contextlib import ExitStack, closing
from pathlib import Path

from .domain import ManagerError, canonical
from .mutations import mutation_lock
from .store import ManagerStore
from .worker import lifetime_lock

DATABASES = (
    "manager.sqlite3",
    "runtime.sqlite3",
    "health.sqlite3",
    "controls.sqlite3",
    "browser.sqlite3",
)
MAX_JSON = 4 * 1024 * 1024


def _error(message):
    return ManagerError("backup_unavailable", message, 4)


def _json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON:
        raise _error("Required snapshot document is missing, unsafe or oversized.")
    try:
        body = json.loads(path.read_text())
        if not isinstance(body, dict):
            raise TypeError
        return body
    except (OSError, TypeError, ValueError) as exc:
        raise _error("Snapshot document is unreadable.") from exc


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_db(path):
    if not path.is_file() or path.is_symlink():
        raise _error("Required database is absent or unsafe.")
    db = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True, timeout=1)
    db.execute("PRAGMA query_only=ON")
    return db


def _cutoff(path):
    with closing(_read_db(path)) as db:
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise _error("Database failed integrity verification.")
        tables = {}
        for (name,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ):
            quoted = '"' + name.replace('"', '""') + '"'
            tables[name] = {
                "rows": db.execute("SELECT count(*) FROM " + quoted).fetchone()[0]
            }
            try:
                tables[name]["max_rowid"] = db.execute(
                    "SELECT max(rowid) FROM " + quoted
                ).fetchone()[0]
            except sqlite3.OperationalError:
                tables[name]["max_rowid"] = None
        return {
            "user_version": db.execute("PRAGMA user_version").fetchone()[0],
            "tables": tables,
        }


def _authority_binding(descriptor, registry_path=None, *, verify_owner=True):
    from .research_owner import OwnerClient

    OwnerClient(descriptor)
    authority = descriptor.get("authority") or {}
    root = Path(authority.get("root", "/absent"))
    config_root = Path(descriptor["config_root"])
    registry = Path(
        registry_path
        or os.environ.get("SOLTUI_RESEARCH_REGISTRY")
        or Path.home() / ".local/share/solbot-research/authority.json"
    )
    record = _json(registry)
    expected = {"version": 2, "id": authority.get("id"), "root": str(root.resolve())}
    if (
        record.get("version") != 2
        or record.get("id") != expected["id"]
        or record.get("root") != expected["root"]
        or str(config_root.resolve()) not in record.get("config_roots", [])
        or _json(config_root / "research-authority.json") != expected
    ):
        raise _error(
            "Canonical research registration does not match the reviewed owner."
        )
    if verify_owner:
        discovery = dict(descriptor, authority=None, expected_identity=None)
        described = OwnerClient(discovery).call("describe", {})
        if described.get("identity") != descriptor[
            "expected_identity"
        ] or described.get("canonical_authority") != {
            "id": expected["id"],
            "root": expected["root"],
        }:
            raise _error("Installed research owner identity changed.")
    path = root / "experiments.sqlite3"
    _cutoff(path)
    spent = {}
    with closing(_read_db(path)) as db:
        for table in ("exposures", "holdouts"):
            columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
            fields = [
                c
                for c in (
                    "bot",
                    "coin",
                    "start",
                    "end",
                    "run_id",
                    "candidate_id",
                    "context",
                )
                if c in columns
            ]
            if not {"bot", "coin", "start", "end", "run_id"} <= columns:
                raise _error("Canonical research spending history is unavailable.")
            rows = db.execute(
                "SELECT " + ",".join(fields) + " FROM " + table + " LIMIT 100001"
            ).fetchall()
            if len(rows) > 100000:
                raise _error(
                    "Research spending history exceeds snapshot verification budget."
                )
            spent[table] = sorted(
                hashlib.sha256(canonical(dict(zip(fields, row))).encode()).hexdigest()
                for row in rows
            )
    return {
        "registry_path": str(registry.absolute()),
        "authority": expected,
        "namespace_id": record.get("namespace_id"),
        "spent": spent,
    }


def _validate_authority(descriptor, expected):
    current = _authority_binding(descriptor, expected["registry_path"])
    if (
        current["authority"] != expected["authority"]
        or current["namespace_id"] != expected["namespace_id"]
        or any(
            not set(rows) <= set(current["spent"][table])
            for table, rows in expected["spent"].items()
        )
    ):
        raise _error("Canonical research history rolled back or authority changed.")


def _dependencies(home):
    result = []
    runtime = home / "runtime.sqlite3"
    if runtime.is_file():
        with closing(_read_db(runtime)) as db:
            inputs = [
                json.loads(row[0]) for row in db.execute("SELECT input FROM runs")
            ]
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='archives'"
            ).fetchone():
                inputs.extend(
                    json.loads(json.loads(row[0])["run"]["input"])
                    for row in db.execute("SELECT body FROM archives")
                )
            for body in inputs:
                d = body.get("descriptor", {})
                paths = d.get("paths", []) + (
                    [d["archive_path"]] if "archive_path" in d else []
                )
                for name in paths:
                    path = Path(name)
                    if (
                        not path.is_absolute()
                        or not path.is_file()
                        or path.is_symlink()
                    ):
                        raise _error("Pinned input dependency is unavailable.")
                    result.append(str(path))
    return sorted(set(result))


def _quiescent(home, *, now=None):
    controls = home / "controls.sqlite3"
    if controls.is_file():
        with closing(_read_db(controls)) as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in (1, 2):
                raise _error("Delegated control journal is incompatible.")
            for (body,) in db.execute("SELECT body FROM requests"):
                receipt = json.loads(body)
                if receipt.get("outcome") in ("pending", "unknown"):
                    raise _error(
                        "Delegated owner outcome is unresolved; reconcile before backup."
                    )
                if (
                    receipt.get("operation") == "start"
                    and receipt.get("outcome") == "acknowledged"
                ):
                    raise _error(
                        "External owner start requires explicit stopped-owner verification before backup."
                    )
    browser = home / "browser.sqlite3"
    if browser.is_file():
        from .adapters.extension import browser_quiescent

        if not browser_quiescent(home, now=now):
            raise _error("Browser ownership is not freshly stopped and reconciled.")
    path = home / "runtime.sqlite3"
    if path.is_file():
        with closing(_read_db(path)) as db:
            rows = db.execute(
                "SELECT bot_id,desired,observed,pid,tick_started FROM runs"
            ).fetchall()
            if any(
                desired != "stopped"
                or observed != "stopped"
                or pid is not None
                or tick is not None
                for _, desired, observed, pid, tick in rows
            ):
                raise _error(
                    "Backup requires stopped runs, released owners and no unresolved tick."
                )
            return [r[0] for r in rows]
    return []


def create_backup(home, destination):
    home, destination = Path(home).absolute(), Path(destination).absolute()
    if (
        destination.exists()
        or home == destination
        or home in destination.parents
        or destination in home.parents
        or not (home / "manager.sqlite3").is_file()
    ):
        raise _error(
            "Backup requires an initialized home and a new external destination."
        )
    temporary = None
    try:
        with ExitStack() as stack:
            stack.enter_context(lifetime_lock(home / "supervisor.lock"))
            stack.enter_context(mutation_lock(home))
            for bot in _quiescent(home):
                stack.enter_context(lifetime_lock(home / "locks" / (bot + ".lock")))
            _quiescent(home)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = Path(
                tempfile.mkdtemp(prefix=".solbot-backup-", dir=destination.parent)
            )
            databases = {}
            for name in DATABASES:
                source = home / name
                if not source.exists():
                    continue
                guard = stack.enter_context(closing(sqlite3.connect(source, timeout=1)))
                guard.execute("BEGIN IMMEDIATE")
                with (
                    closing(_read_db(source)) as src,
                    closing(sqlite3.connect(temporary / name)) as dst,
                ):
                    src.backup(dst)
                os.chmod(temporary / name, 0o600)
                databases[name] = {
                    "sha256": _hash(temporary / name),
                    "cutoff": _cutoff(temporary / name),
                }
            captured_at = time.time()
            _quiescent(home, now=captured_at)
            documents = {}
            names = (
                [home / "research-owner.json"]
                if (home / "research-owner.json").exists()
                else []
            ) + sorted(home.glob("research-plan-*.json"))
            authority = None
            with closing(_read_db(home / "manager.sqlite3")) as manager_db:
                proposals = manager_db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_proposals'"
                ).fetchone()
                if (
                    proposals
                    and manager_db.execute(
                        "SELECT 1 FROM research_proposals LIMIT 1"
                    ).fetchone()
                    and not (home / "research-owner.json").is_file()
                ):
                    raise _error(
                        "Research proposals require the local reviewed owner binding in the snapshot."
                    )
            for path in names:
                body = _json(path)
                if path.name == "research-owner.json":
                    authority = _authority_binding(body)
                (temporary / path.name).write_text(canonical(body) + "\n")
                os.chmod(temporary / path.name, 0o600)
                documents[path.name] = {"sha256": _hash(temporary / path.name)}
            manifest = {
                "schema_version": 1,
                "captured_at": captured_at,
                "source_home": str(home),
                "consistency": "stopped_quiescent_per_database_cutoffs",
                "databases": databases,
                "documents": documents,
                "dependencies": _dependencies(home),
                "research_authority": authority,
                "research_database_included": False,
                "starts_workers": False,
            }
            (temporary / "manifest.json").write_text(canonical(manifest) + "\n")
            os.chmod(temporary / "manifest.json", 0o600)
            temporary.rename(destination)
            temporary = None
            return {"backup_path": str(destination), "manifest": manifest}
    except (OSError, sqlite3.Error, ValueError) as exc:
        if isinstance(exc, ManagerError):
            raise
        raise _error("Backup failed; stop owners and verify dependencies.") from exc
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)


def restore_backup(source, destination):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if destination.exists() or source == destination or source in destination.parents:
        raise _error("Restore requires a new, absent manager home.")
    temporary = None
    try:
        manifest = _json(source / "manifest.json")
        if (
            manifest.get("schema_version") != 1
            or manifest.get("research_database_included") is not False
            or manifest.get("starts_workers") is not False
        ):
            raise _error("Snapshot manifest is incompatible.")
        databases, documents = manifest["databases"], manifest["documents"]
        if (
            "manager.sqlite3" not in databases
            or set(databases) - set(DATABASES)
            or any(
                name != "research-owner.json"
                and not (
                    name.startswith("research-plan-")
                    and name.endswith(".json")
                    and Path(name).name == name
                )
                for name in documents
            )
        ):
            raise _error("Snapshot file inventory is incompatible.")
        if {p.name for p in source.iterdir()} != set(databases) | set(documents) | {
            "manifest.json"
        }:
            raise _error("Snapshot contains unreviewed files.")
        for name, entry in {**databases, **documents}.items():
            path = source / name
            if (
                path.is_symlink()
                or not path.is_file()
                or _hash(path) != entry["sha256"]
            ):
                raise _error("Snapshot checksum mismatch.")
            if name in databases and _cutoff(path) != entry["cutoff"]:
                raise _error("Snapshot database cutoffs differ.")
        for name in manifest["dependencies"]:
            path = Path(name)
            if not path.is_absolute() or not path.is_file() or path.is_symlink():
                raise _error("Snapshot input dependency is unavailable.")
        authority = manifest["research_authority"]
        if authority is not None:
            _validate_authority(_json(source / "research-owner.json"), authority)
        elif "research-owner.json" in documents:
            raise _error("Snapshot research authority binding is absent.")
        captured_at = manifest.get("captured_at")
        if (
            isinstance(captured_at, bool)
            or not isinstance(captured_at, (int, float))
            or not math.isfinite(captured_at)
            or captured_at <= 0
        ):
            raise _error("Snapshot capture cutoff is invalid.")
        _quiescent(source, now=captured_at)
        # Existing decoders verify immutable references without starting runtime.
        store = ManagerStore(source)
        from .ledger import RuntimeLedger

        ledger = RuntimeLedger(source)
        for spec in store.list_specs():
            ledger.get(spec.bot_id)
        if ledger.path.is_file():
            with ledger.connection() as db:
                if db.execute("PRAGMA user_version").fetchone()[0] >= 3:
                    for row in db.execute("SELECT * FROM archives"):
                        ledger._decode_archive(db, row)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = Path(
            tempfile.mkdtemp(prefix=".solbot-restore-", dir=destination.parent)
        )
        for name in [*databases, *documents]:
            shutil.copyfile(source / name, temporary / name)
            os.chmod(temporary / name, 0o600)
            expected = databases.get(name, documents.get(name))
            if _hash(temporary / name) != expected["sha256"]:
                raise _error("Snapshot changed during restore copy.")
        temporary.rename(destination)
        temporary = None
        return {
            "restored_home": str(destination),
            "starts_workers": False,
            "research_authority": authority,
            "canonical_research_restored": False,
        }
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, ManagerError):
            raise
        raise _error("Restore failed integrity or dependency verification.") from exc
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)
