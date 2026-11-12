"""Shared pre-read admission and conservative import of existing owner history."""

from __future__ import annotations

import contextvars
import fcntl
import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager, nullcontext
from functools import wraps
from pathlib import Path

_LEASE = contextvars.ContextVar("research_optimizer_lease", default=None)


def source_identity():
    paths = [
        Path(__file__),
        Path(__file__).with_name("experiments.py"),
        Path(__file__).with_name("manager_evidence.py"),
        Path(__file__).with_name("evidence_identity.py"),
    ]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@contextmanager
def optimizer_lease(root):
    from .experiments import ExperimentError

    root = Path(root).resolve()
    if _LEASE.get() == (os.getpid(), str(root)):
        yield
        return
    if not (root / "experiments.sqlite3").is_file():
        raise ExperimentError("canonical research authority unavailable")
    with (root / "research-optimizer.lock").open("a+b") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExperimentError("shared optimizer already active") from exc
        token = _LEASE.set((os.getpid(), str(root)))
        try:
            yield
        finally:
            _LEASE.reset(token)
            fcntl.flock(stream, fcntl.LOCK_UN)


def participating(function):
    """Legacy clients opt in explicitly; old immutable installations stay unchanged.

    The shared lock precedes each client's run/database locks. All manager jobs
    use the same lock, so an admitted F5 coordinator remains the execution owner.
    """

    @wraps(function)
    def wrapped(*args, **kwargs):
        authority = os.environ.get("SOLTUI_RESEARCH_AUTHORITY")
        with optimizer_lease(authority) if authority else nullcontext():
            return function(*args, **kwargs)

    return wrapped


def native_authority(store=None, *, coins=None):
    """Participating native work must keep receipts in the canonical ledger."""
    configured = os.environ.get("SOLTUI_RESEARCH_AUTHORITY")
    if not configured:
        return
    from .experiments import ExperimentError, ExperimentStore

    root = Path(configured).resolve()
    if store is None:
        store = ExperimentStore(root)
    if store.root.resolve() != root:
        raise ExperimentError(
            "native store differs from canonical research authority; select the registered canonical store"
        )
    if coins:
        store.manager_pre_read(
            [{"coin": coin, "start": 0, "end": time.time()} for coin in coins]
        )


def admit_read(coin, *, source, end=None, attempts=1):
    """Register a conservative history envelope BEFORE opening evaluation inputs."""
    authority = os.environ.get("SOLTUI_RESEARCH_AUTHORITY")
    if not authority:
        return None
    from .experiments import ExperimentStore, fingerprint

    if (
        not Path(authority).is_absolute()
        or not (Path(authority) / "experiments.sqlite3").is_file()
    ):
        raise ValueError("explicit canonical research authority unavailable")
    stop = time.time() if end is None else end
    receipt = {
        "coin": coin.upper(),
        "start": 0,
        "end": stop,
        "source": source,
        "identity": source_identity(),
    }
    store = ExperimentStore(authority)
    store.manager_import(
        source,
        uuid.uuid4().hex,
        fingerprint(receipt),
        [{"coin": coin.upper(), "start": 0, "end": stop}],
        attempts=attempts,
    )
    return receipt


@contextmanager
def _readonly(path):
    connection = sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2
    )
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def inspect_history(root, kind):
    """Absence is checked. Unrecoverable or partial bounds remain explicit gaps.

    Snapshot import cannot certify active clients. The caller persists that
    separate blocker and refreshes each root before final exposure.
    """
    from .experiments import fingerprint

    root = Path(root)
    evidence = {
        "root": str(root),
        "kind": kind,
        "coverage": "verified",
        "records": [],
        "absence_checked": not root.exists(),
        "active": False,
    }
    if not root.exists():
        if kind == "native":
            try:
                _native_legacy(root, evidence)
            except (OSError, ValueError, KeyError):
                evidence["coverage"] = "unavailable"
        return evidence
    if not root.is_dir():
        return {**evidence, "coverage": "unavailable"}
    try:
        if kind == "native":
            path = root / "experiments.sqlite3"
            if not path.exists():
                _native_legacy(root, evidence)
                return {**evidence, "absence_checked": True}
            for lock in (root / "locks").glob("*.lock"):
                with lock.open("rb") as stream:
                    try:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(stream, fcntl.LOCK_UN)
                    except BlockingIOError:
                        evidence["active"] = True
            with _readonly(path) as db:
                rows = []
                for table in ("exposures", "holdouts"):
                    rows.extend(
                        dict(row)
                        for row in db.execute(
                            f"SELECT bot,coin,start,end,run_id FROM {table}"
                        )
                    )
                runs = [dict(r) for r in db.execute("SELECT id,spec FROM runs")]
            for row in rows:
                evidence["records"].append(
                    {
                        "id": "native:" + fingerprint(row),
                        "digest": fingerprint(row),
                        "intervals": [{k: row[k] for k in ("coin", "start", "end")}],
                        "attempts": 0,
                    }
                )
            for run in runs:
                evidence["records"].append(
                    {
                        "id": "attempt:" + run["id"],
                        "digest": fingerprint(run),
                        "intervals": [],
                        "attempts": 1,
                    }
                )
        elif kind == "f5":
            paths = list(root.glob("*/batch.sqlite3"))
            if (root / "batch.sqlite3").is_file():
                paths.append(root / "batch.sqlite3")
            if not paths:
                evidence["absence_checked"] = True
                if any(p.name != "f5-worker.lock" for p in root.iterdir()):
                    evidence["coverage"] = "unknown_history"
            global_lock = root / "f5-worker.lock"
            if global_lock.exists():
                with global_lock.open("rb") as stream:
                    try:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(stream, fcntl.LOCK_UN)
                    except BlockingIOError:
                        evidence["active"] = True
            for path in sorted(paths):
                with _readonly(path) as db:
                    meta = {
                        r["key"]: json.loads(r["value"])
                        for r in db.execute("SELECT key,value FROM meta")
                    }
                    cells = [
                        dict(r)
                        for r in db.execute("SELECT * FROM cell WHERE state!='pending' OR id IN (SELECT cell FROM attempt)")
                    ]
                    trials = [dict(r) for r in db.execute("SELECT * FROM attempt")]
                    series = [dict(r) for r in db.execute("SELECT * FROM series")]
                lock = path.parent / "worker.lock"
                if lock.exists():
                    with lock.open("rb") as handle:
                        try:
                            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            fcntl.flock(handle, fcntl.LOCK_UN)
                        except BlockingIOError:
                            evidence["active"] = True
                if not cells and not trials and meta.get("phase") == "planned":
                    continue
                known_cells = {cell["id"] for cell in cells}
                if any(trial["cell"] not in known_cells for trial in trials):
                    evidence["coverage"] = "unknown_history"
                evaluated = {(c["asset"], c["interval"]) for c in cells}
                intervals = []
                for asset, interval in evaluated:
                    record = next(
                        (
                            r
                            for r in series
                            if (r["asset"], r["interval"]) == (asset, interval)
                        ),
                        None,
                    )
                    try:
                        if record is None:
                            raise ValueError
                        bound = _series_interval(
                            record, meta.get(f"data_selection:{asset}:{interval}")
                        )
                        intervals.append(bound)
                    except (ValueError, OSError, KeyError):
                        evidence["coverage"] = "unknown_history"
                        intervals.append(
                            {"coin": asset, "start": 0, "end": time.time()}
                        )
                # Every attempted and interrupted variant remains counted. Each
                # source-record identity is stable, so repeated imports are inert.
                for trial in trials:
                    body = {
                        "batch": str(path),
                        "cell": trial["cell"],
                        "job_id": trial["job_id"],
                        "state": trial["state"],
                        "result": trial["result"],
                    }
                    evidence["records"].append(
                        {
                            "id": "trial:" + fingerprint(body),
                            "digest": fingerprint(body),
                            "intervals": intervals,
                            "attempts": 1,
                        }
                    )
                for cell in cells:
                    body = {"batch": str(path), "cell": cell}
                    evidence["records"].append(
                        {
                            "id": "cell:" + fingerprint(body),
                            "digest": fingerprint(body),
                            "intervals": intervals,
                            "attempts": int(cell["state"] == "running"),
                        }
                    )
                if (path.parent / "forward.sqlite3").exists():
                    # CPCV receipts do not cover subsequent prospective reads.
                    evidence["coverage"] = "unknown_history"

        else:
            # Legacy bg/forward schemas do not certify complete read intervals.
            # Do not infer that an unfamiliar or nonempty root is fresh history.
            files = [
                p
                for p in root.iterdir()
                if p.is_file() and p.name != "research-authority.json"
            ]
            if files:
                evidence["coverage"] = "unknown_history"
                for p in files:
                    stamp = p.stat()
                    body = {
                        "path": str(p),
                        "size": stamp.st_size,
                        "mtime_ns": stamp.st_mtime_ns,
                    }
                    evidence["records"].append(
                        {
                            "id": fingerprint(body),
                            "digest": fingerprint(body),
                            "intervals": [
                                {"coin": "SOL", "start": 0, "end": time.time()}
                            ],
                            "attempts": 1,
                        }
                    )
        if kind == "native":
            _native_legacy(root, evidence)
    except (OSError, ValueError, KeyError, sqlite3.Error):
        evidence["coverage"] = "unavailable"
    return evidence


def _native_legacy(root, evidence):
    from .experiments import fingerprint

    legacy_paths = list(root.glob("legacy-exposure-*.json")) + list(
        (root.parent / "bots").glob("optimize*.json")
    )
    for path in legacy_paths:
        raw = json.loads(path.read_text())
        if path.name.startswith("legacy-exposure-"):
            cutoff = raw.get("cutoff")
            attempts = 0
        else:
            rows = raw.get("log", [raw])
            legacy = [r for r in rows if not r.get("experiment_id")]
            if not legacy and not raw.get("runs"):
                continue
            dates = [r.get("at") for r in legacy]
            valid = all(type(v) in (int, float) and 0 < v < 1e12 for v in dates)
            cutoff = max(dates) if dates and valid else time.time()
            attempts = max(
                int(raw.get("runs", 0)), len(raw.get("tried", [])), len(legacy)
            )
            if not valid or not dates:
                evidence["coverage"] = "unknown_history"
        if cutoff:
            evidence["records"].append(
                {
                    "id": "legacy:" + fingerprint({"path": str(path), "body": raw}),
                    "digest": fingerprint(raw),
                    "intervals": [{"coin": "SOL", "start": 0, "end": cutoff}],
                    "attempts": attempts,
                }
            )


def _series_interval(record, selection):
    import csv
    import math

    from backtester.core.types import INTERVAL_SECONDS

    path = Path(record["path"])
    if path.stat().st_size > 512 * 1024 * 1024:
        raise ValueError("history source exceeds import bound")
    import io

    with path.open("rb") as stream:

        def hash_stream():
            stream.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(65536), b""):
                digest.update(chunk)
            return digest.hexdigest()

        if not record["sha256"] or hash_stream() != record["sha256"]:
            raise ValueError("historical source hash changed")
        stream.seek(0)
        text = io.TextIOWrapper(stream, newline="")
        try:
            timestamps = [float(row["timestamp"]) for row in csv.DictReader(text)]
        finally:
            text.detach()
        if hash_stream() != record["sha256"]:
            raise ValueError("historical source changed while importing bounds")
    if not timestamps or any(not math.isfinite(v) or v != int(v) for v in timestamps):
        raise ValueError("invalid historical timestamp bounds")
    first, last = min(timestamps), max(timestamps)
    if selection:
        if (
            selection.get("policy") != "longest_contiguous"
            or selection["first_ts"] not in timestamps
            or selection["last_ts"] not in timestamps
        ):
            raise ValueError("historical selection lacks bound timestamps")
        first, last = selection["first_ts"], selection["last_ts"]
    return {
        "coin": record["asset"],
        "start": first,
        "end": last + INTERVAL_SECONDS[record["interval"]],
    }


def registry_path():
    """One per-user authority, independent of both manager and owner homes.

    The explicit environment override is for a separately labelled controlled
    inventory (including isolated tests). It is never derived from a bot/home ID.
    """
    configured = os.environ.get("SOLTUI_RESEARCH_REGISTRY")
    path = (
        Path(configured)
        if configured
        else Path.home() / ".local/share/solbot-research/authority.json"
    )
    if not path.is_absolute():
        raise ValueError("research registry path must be absolute")
    return path.resolve()


def registered_authority(authority, config_root):
    from .experiments import ExperimentError

    path = registry_path()
    if not path.is_file():
        raise ExperimentError(
            "authority_registration_required: unknown research namespace history"
        )
    record = json.loads(path.read_text())
    if (
        record.get("version") != 2
        or record.get("id") != authority["id"]
        or record.get("root") != str(Path(authority["root"]).resolve())
    ):
        raise ExperimentError(
            "canonical authority identity mismatch across owner roots"
        )
    if str(Path(config_root).resolve()) not in record["config_roots"]:
        raise ExperimentError(
            "authority_registration_required: unknown owner configuration-root history"
        )
    return record


def register_authority(authority, config_root, *, consent, initialize_first=False):
    """Public enrollment: import into an existing selected owner, never a new DB."""
    from .experiments import ExperimentError, ExperimentStore, fingerprint

    if consent is not True:
        raise ExperimentError("explicit registered-roots-only scope consent required")
    root = Path(authority["root"]).resolve()
    if type(initialize_first) is not bool:
        raise ExperimentError("first authority initialization must be explicit boolean")
    registry = registry_path()
    registry.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Lock order: namespace registry -> shared optimizer -> owner SQL. No client
    # holds owner SQL while acquiring either process lock.
    with registry.with_suffix(".lock").open("a+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        old = json.loads(registry.read_text()) if registry.exists() else None
        if old and (
            old.get("version") != 2
            or old.get("id") != authority["id"]
            or old.get("root") != str(root)
        ):
            raise ExperimentError(
                "canonical authority identity mismatch; new homes cannot reset history"
            )
        initialized = False
        epoch = old.get("initialization_epoch") if old else None
        if not (root / "experiments.sqlite3").is_file():
            if old or not initialize_first:
                raise ExperimentError(
                    "registered authority missing or explicit first initialization required"
                )
            store = ExperimentStore(root)
            epoch = time.time()
            store.manager_mark_history_gap(
                "namespace-first-initialization",
                "unknown history before owner initialization epoch; earlier dates remain unavailable",
                cutoff=epoch,
            )
            initialized = True
        clients = {
            str(Path(r["root"]).resolve()): {
                **r,
                "root": str(Path(r["root"]).resolve()),
            }
            for r in (old["known_clients"] if old else [])
        }
        discovered, _ = known_clients(config_root)
        for client in [
            *discovered,
            {"root": str(root), "kind": "native", "active": False},
            *authority["known_clients"],
        ]:
            clients[str(Path(client["root"]).resolve())] = {
                **client,
                "root": str(Path(client["root"]).resolve()),
            }
        with optimizer_lease(root):
            store = ExperimentStore(root)
            evidence = [
                store.manager_register_client(client) for client in clients.values()
            ]
            config_roots = sorted(
                set(
                    (old["config_roots"] if old else [])
                    + [str(Path(config_root).resolve())]
                )
            )
            record = {
                "version": 2,
                "id": authority["id"],
                "root": str(root),
                "config_roots": config_roots,
                "known_clients": list(clients.values()),
                "coverage": "registered_roots_only",
                "initialization_epoch": epoch,
                "initialization_history": old.get(
                    "initialization_history", "imported_existing"
                )
                if old
                else ("unknown" if initialized else "imported_existing"),
                "namespace_id": fingerprint(str(registry)),
                "isolation_mode": "isolated"
                if os.environ.get("SOLTUI_RESEARCH_REGISTRY")
                else "registered_clients",
            }
            _atomic_json(registry, record)
            binding = Path(config_root) / "research-authority.json"
            _atomic_json(
                binding, {"version": 2, "id": authority["id"], "root": str(root)}
            )
    return {
        "registered": True,
        "initialization_history": record["initialization_history"],
        "initialization_epoch": record["initialization_epoch"],
        "coverage": "registered_roots_only",
        "namespace_id": record["namespace_id"],
        "isolation_mode": record["isolation_mode"],
        "globally_fresh": False,
        "production_eligible": False,
        "receipt_digest": fingerprint(record),
        "history": [
            {
                "root": e["root"],
                "coverage": e["coverage"],
                "active": e["active"],
                "absence_checked": e["absence_checked"],
            }
            for e in evidence
        ],
    }


def _atomic_json(path, body):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(body, stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def known_clients(config_root, source_descriptor=None):
    """Bounded installation defaults; omission cannot hide a known owner."""
    config_roots = {Path(config_root).resolve()}
    ecosystem_roots = set()
    if not os.environ.get("SOLTUI_RESEARCH_REGISTRY"):
        config_roots.add((Path.home() / ".config/soltui").resolve())
        ecosystem_roots.update(
            Path.home() / ".local/share/solmargintrader" / name
            for name in ("ecosystem", "ecosystem-paper-v1", "ecosystem-paper-v2")
        )
    unknown_source = False
    if source_descriptor and source_descriptor.get("source") == "oracle_archive":
        archive = Path(source_descriptor["archive_path"]).resolve()
        if archive.name == "history.sqlite3" and archive.parent.parent.name == "oracle":
            ecosystem_roots.add(archive.parent.parent.parent)
        else:
            unknown_source = True
    rows = [
        {"root": str(root / name), "kind": kind, "active": False}
        for root in sorted(config_roots)
        for name, kind in (
            ("experiments", "native"),
            ("f5-batches", "f5"),
            ("bg", "bg"),
            ("forwardtest", "forward"),
        )
    ]
    rows.extend(
        {"root": str(root.resolve() / "batches"), "kind": "f5", "active": False}
        for root in sorted(ecosystem_roots)
    )
    return rows, unknown_source
