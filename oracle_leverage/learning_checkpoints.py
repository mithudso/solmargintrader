"""Private disk mirror of prospective browser learners; never a trading owner.

Browser transactions own learning. Admission checks the complete frozen schemas
before opening writable storage. A checkpoint and its recent outcomes commit in
one transaction; neither raw historical ticks nor unobserved labels are inferred.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import time
import zlib
from pathlib import Path
from typing import Any

MAX_BYTES = 2 * 1024 * 1024
MAX_COMPRESSED_BYTES = MAX_BYTES + 65536
CHUNK_CHARS = 128 * 1024
MAX_INTEGER = 2**53 - 1
HORIZONS = (60, 300, 600, 900, 1200, 3600)
HORIZON_KEYS = {str(h) for h in HORIZONS}
UUID = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
MINUTE_FORECAST = {"id", "cutoff", "target", "issuedAtMs", "reference", "x", "p", "baselineP", "servedP", "mode", "modelSamples"}
MINUTE_RESULT = {"outcome", "y", "close", "scores", "resolvedAtMs"}
MINUTE_SCORES = ("candidate", "baseline", "served")
LIVE_SCORES = ("candidate", "uniform", "frequency")


def _home(create: bool = False) -> Path | None:
    path = Path(os.environ.get("ORACLE_LEARNING_HOME", Path.home() / ".local/state/oracle-learning"))
    if not path.is_absolute():
        raise ValueError("Learning storage must use an absolute private directory")
    try:
        info = path.lstat()
    except FileNotFoundError:
        if not create:
            return None
        try:
            path.mkdir(parents=True, mode=0o700)
        except FileExistsError:
            # Another native request may have created it after lstat. Verify
            # the winner, including symlinks and permissions, before using it.
            pass
        info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Learning storage directory is not private")
    return path


def _database(create: bool = False) -> sqlite3.Connection | None:
    home = _home(create)
    if home is None:
        return None
    path = home / "checkpoints.sqlite3"
    try:
        info = path.lstat()
    except FileNotFoundError:
        if not create:
            return None
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
        raise ValueError("Learning database is not a private regular file")
    db = sqlite3.connect(path.as_uri() + ("?mode=rw" if create else "?mode=ro"), uri=True, timeout=3)
    try:
        if create:
            # journal_mode can return SQLITE_BUSY immediately while another
            # first creator changes it, even with SQLite's connection timeout.
            for attempt in range(5):
                try:
                    db.execute("PRAGMA journal_mode=WAL")
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower() or attempt == 4:
                        raise
                    time.sleep(0.01 * (attempt + 1))
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                namespace TEXT NOT NULL, kind TEXT NOT NULL, key TEXT NOT NULL,
                lineage TEXT NOT NULL, revision INTEGER NOT NULL, digest TEXT NOT NULL,
                payload BLOB NOT NULL, length INTEGER NOT NULL, saved_at REAL NOT NULL,
                PRIMARY KEY(namespace,kind,key)
            );
            CREATE TABLE IF NOT EXISTS outcomes (
                namespace TEXT NOT NULL, kind TEXT NOT NULL, key TEXT NOT NULL,
                id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(namespace,kind,key,id)
            );
            """)
        return db
    except Exception:
        db.close()
        raise


def _integer(value: Any, minimum: int = 0, maximum: int = MAX_INTEGER) -> int:
    if type(value) is not int or not minimum <= value <= min(maximum, MAX_INTEGER):
        raise ValueError("Invalid learning integer")
    return value


def _number(value: Any, minimum: float = -math.inf, maximum: float = math.inf) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Invalid learning number")
    return value


def _object(value: Any, fields: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Invalid learning checkpoint fields")
    return value


def _array(value: Any, maximum: int, length: int | None = None) -> list[Any]:
    if type(value) is not list or len(value) > maximum or (length is not None and len(value) != length):
        raise ValueError("Invalid learning array")
    return value


def _vector(value: Any, length: int, bound: int) -> None:
    for item in _array(value, length, length):
        _number(item, -bound, bound)


def _probabilities(value: Any) -> None:
    values = _array(value, 3, 3)
    for item in values:
        _number(item, 0, 1)
    if abs(sum(values) - 1) >= 1e-9:
        raise ValueError("Invalid learning probabilities")


def _identity(value: Any) -> None:
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise ValueError("Invalid learning profile or lineage")


def _address(namespace: str, kind: str, key: str) -> tuple[str, str]:
    _identity(namespace)
    if kind not in ("minute", "live") or not isinstance(key, str) or len(key) > 1024:
        raise ValueError("Invalid learning partition")
    try:
        binding = json.loads(key)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Invalid learning partition identity") from exc
    expected = ("projected-logit-l2-v1", "fixed-price-context-v1", "closed-price-up-vs-nonup-v1") if kind == "minute" else ("live-softmax-l2-v1", "endpoint-exact-price-v1")
    if not isinstance(binding, list) or len(binding) != (7 if kind == "minute" else 5) or type(binding[0]) is not int or binding[0] != 1 or binding[1:1 + len(expected)] != list(expected):
        raise ValueError("Unsupported learning model identity")
    market, source = binding[-2:]
    if not isinstance(market, str) or not re.fullmatch(r"[A-Z][A-Z0-9]{0,11}", market) or not isinstance(source, str):
        raise ValueError("Unsupported learning source identity")
    match = re.fullmatch(r"fixed_rate@200ms:([1-9][0-9]*):[1-9A-HJ-NP-Za-km-z]{32,44}:oracle-ohlc", source)
    if not match or int(match[1]) > MAX_INTEGER:
        raise ValueError("Unsupported learning source identity")
    if kind == "minute" and (type(binding[4]) is not int or binding[4] not in HORIZONS):
        raise ValueError("Unsupported learning horizon")
    if key != json.dumps(binding, separators=(",", ":")):
        raise ValueError("Invalid learning partition encoding")
    return market, source


def _score(p: float, y: int) -> dict[str, float]:
    bounded = max(1e-9, min(1 - 1e-9, p))
    return {"hit": int((1 if p > 0.5 else 0) == y), "brier": (p - y) ** 2,
            "logLoss": -(y * math.log(bounded) + (1 - y) * math.log(1 - bounded))}


def _close(actual: float, expected: float) -> bool:
    # libm and browser Math.log may differ at the final binary digit.
    return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)


def _minute_forecast(row: Any, key: str, horizon: int, *, resolved: bool) -> None:
    f = _object(row, MINUTE_FORECAST | MINUTE_RESULT if resolved else MINUTE_FORECAST)
    cutoff = _integer(f["cutoff"])
    if cutoff % 60 or f["id"] != f"{key}:{cutoff}" or _integer(f["target"]) != cutoff + horizon:
        raise ValueError("Invalid minute learning forecast identity")
    _number(f["reference"], 0)
    if f["reference"] == 0:
        raise ValueError("Invalid minute learning reference")
    _integer(f["issuedAtMs"], cutoff * 1000, cutoff * 1000 + 15000)
    _vector(f["x"], 22, 1)
    _number(f["p"], 0, 1)
    _number(f["baselineP"], 0, 1)
    _number(f["servedP"], 0, 1)
    _integer(f["modelSamples"])
    if f["baselineP"] != 0.5 or f["mode"] not in ("active", "baseline-warmup", "baseline-performance") or f["servedP"] != (f["p"] if f["mode"] == "active" else 0.5):
        raise ValueError("Invalid minute learning probability")
    if not resolved:
        return
    _number(f["close"], 0)
    outcome = "UP" if f["close"] > f["reference"] else "DOWN" if f["close"] < f["reference"] else "FLAT"
    if f["close"] == 0 or f["outcome"] != outcome or _integer(f["y"], 0, 1) != int(outcome == "UP"):
        raise ValueError("Invalid minute learning outcome")
    _integer(f["resolvedAtMs"], f["target"] * 1000, f["target"] * 1000 + 90000)
    scores = _object(f["scores"], set(MINUTE_SCORES))
    for name, p in zip(MINUTE_SCORES, (f["p"], f["baselineP"], f["servedP"])):
        actual = _object(scores[name], {"hit", "brier", "logLoss"})
        expected = _score(p, f["y"])
        if _integer(actual["hit"], 0, 1) != expected["hit"] or any(not _close(_number(actual[field], 0), expected[field]) for field in ("brier", "logLoss")):
            raise ValueError("Invalid minute learning score")


def _minute(value: dict[str, Any], key: str) -> list[tuple[str, dict[str, Any]]]:
    _object(value, {"schema", "key", "market", "source", "model", "pending", "recent", "totals", "issued", "expired", "lastIssuedCutoff", "lastClosedTarget", "updatedAtMs", "historicalTrainingSamples"})
    model = _object(value["model"], {"weights", "bias", "n"})
    _vector(model["weights"], 22, 8)
    _number(model["bias"], -8, 8)
    n = _integer(model["n"])
    totals = _object(value["totals"], {"n", "up", "down", "flat", *MINUTE_SCORES})
    for field in ("n", "up", "down", "flat"):
        _integer(totals[field])
    pending = _array(value["pending"], 64)
    recent = _array(value["recent"], 128)
    for field in ("issued", "expired", "lastIssuedCutoff", "lastClosedTarget"):
        _integer(value[field])
    if value["updatedAtMs"] is not None:
        _integer(value["updatedAtMs"])
    if _integer(value["historicalTrainingSamples"]) != 0 or n != totals["n"] or sum(totals[f] for f in ("up", "down", "flat")) != n or value["issued"] != n + value["expired"] + len(pending) or len(recent) != min(n, 128):
        raise ValueError("Invalid minute learning counts")
    for name in MINUTE_SCORES:
        score = _object(totals[name], {"hits", "brier", "logLoss"})
        _integer(score["hits"], 0, n)
        _number(score["brier"], 0, n + 1e-9)
        _number(score["logLoss"], 0, n * (-math.log(1e-9) + 1e-6) + 1e-9)
    ids: set[str] = set()
    horizon = json.loads(key)[4]
    for resolved, rows in ((False, pending), (True, recent)):
        for f in rows:
            _minute_forecast(f, key, horizon, resolved=resolved)
            if f["id"] in ids or f["cutoff"] > value["lastIssuedCutoff"] or f["modelSamples"] > n:
                raise ValueError("Invalid minute learning forecast progress")
            ids.add(f["id"])
    return [(row["id"], row) for row in recent]


def _live_id(value: Any, horizon: int) -> None:
    if not isinstance(value, str) or not re.fullmatch(rf"{horizon}:(0|[1-9][0-9]*)", value):
        raise ValueError("Invalid live learning forecast identity")
    _integer(int(value.split(":")[1]))


def _live(value: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    _object(value, {"schema", "key", "market", "source", "models", "metrics", "pending", "history", "lastQuote", "lastProbeBucket", "lastProbeAtMs", "revision"})
    models = _object(value["models"], HORIZON_KEYS)
    metrics = _object(value["metrics"], HORIZON_KEYS)
    _integer(value["revision"])
    for field in ("lastProbeBucket", "lastProbeAtMs"):
        if value[field] is not None:
            _integer(value[field])
    if (value["lastProbeBucket"] is None) != (value["lastProbeAtMs"] is None) or (value["lastProbeAtMs"] is not None and value["lastProbeBucket"] != value["lastProbeAtMs"] // 5000):
        raise ValueError("Invalid live learning probe progress")
    ids: set[str] = set()
    pending_counts = dict.fromkeys(HORIZONS, 0)
    for row in _array(value["pending"], 1500):
        f = _object(row, {"id", "horizon", "issuedAtMs", "targetMs", "reference", "x", "p", "baseline"})
        h = _integer(f["horizon"])
        if h not in HORIZONS:
            raise ValueError("Invalid live learning horizon")
        _integer(f["issuedAtMs"])
        if _integer(f["targetMs"]) != f["issuedAtMs"] + h * 1000 or f["id"] != f"{h}:{f['issuedAtMs'] // 5000}" or f["id"] in ids:
            raise ValueError("Invalid live learning forecast identity")
        ids.add(f["id"])
        _number(f["reference"], 0)
        if f["reference"] == 0:
            raise ValueError("Invalid live learning reference")
        _vector(f["x"], 5, 1)
        _probabilities(f["p"])
        _probabilities(f["baseline"])
        pending_counts[h] += 1
    history = _array(value["history"], 120)
    previous_time = None
    for row in history:
        q = _object(row, {"t", "price"})
        t = _integer(q["t"])
        _number(q["price"], 0)
        if q["price"] == 0 or (previous_time is not None and not 0 < t - previous_time <= 2000):
            raise ValueError("Invalid live learning quote history")
        previous_time = t
    quote = value["lastQuote"]
    if quote is not None:
        _object(quote, {"price", "exchangeMs", "receivedMs"})
        for field in ("price", "exchangeMs", "receivedMs"):
            _number(quote[field], 0)
        if quote["price"] == 0 or quote["exchangeMs"] > quote["receivedMs"] + 250 or not history or history[-1]["t"] != math.floor(quote["receivedMs"] / 1000) * 1000 or history[-1]["price"] != quote["price"]:
            raise ValueError("Invalid live learning last quote")
    elif history:
        raise ValueError("Invalid live learning quote history")
    outcomes = []
    for h in HORIZONS:
        model = _object(models[str(h)], {"weights", "bias", "n"})
        for weights in _array(model["weights"], 3, 3):
            _vector(weights, 5, 8)
        _vector(model["bias"], 3, 8)
        n = _integer(model["n"])
        metric = _object(metrics[str(h)], {"issued", "resolved", "expired", "capacityDrops", "counts", "recent", *LIVE_SCORES})
        for field in ("issued", "resolved", "expired", "capacityDrops"):
            _integer(metric[field])
        for count in _array(metric["counts"], 3, 3):
            _integer(count)
        recent = _array(metric["recent"], 128)
        if n != metric["resolved"] or sum(metric["counts"]) != n or metric["issued"] != n + metric["expired"] + pending_counts[h] or len(recent) != min(n, 128):
            raise ValueError("Invalid live learning counts")
        for name in LIVE_SCORES:
            score = _object(metric[name], {"brier", "hits"})
            _number(score["brier"], 0, 2 * n + 1e-9)
            _integer(score["hits"], 0, n)
        for index, row in enumerate(recent):
            r = _object(row, {"id", "ordinal", "y", "p", "baseline"})
            _live_id(r["id"], h)
            if r["id"] in ids or _integer(r["ordinal"], 1) != n - len(recent) + index + 1:
                raise ValueError("Invalid live learning outcome progress")
            ids.add(r["id"])
            _integer(r["y"], 0, 2)
            _probabilities(r["p"])
            _probabilities(r["baseline"])
            outcomes.append((f"{h}:{r['id']}", r))
    return outcomes


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("Duplicate learning checkpoint field")
    return value


def _state(kind: str, key: str, text: str) -> tuple[dict[str, Any], list[int], list[tuple[str, dict[str, Any]]]]:
    if not isinstance(text, str):
        raise TypeError("Invalid learning checkpoint text")
    try:
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Learning checkpoint exceeds the size limit")
        def invalid_constant(_: str) -> None:
            raise ValueError("Learning state contains a nonfinite number")
        value = json.loads(text, parse_constant=invalid_constant, object_pairs_hook=_unique_object)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise ValueError("Invalid learning checkpoint JSON or size") from exc
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1 or value.get("key") != key:
        raise ValueError("Invalid learning checkpoint identity")
    if [value.get("market"), value.get("source")] != json.loads(key)[-2:]:
        raise ValueError("Learning checkpoint source does not match")
    outcomes = _minute(value, key) if kind == "minute" else _live(value)
    counts = [value["model"]["n"]] if kind == "minute" else [value["models"][str(h)]["n"] for h in HORIZONS]
    return value, counts, outcomes


def _progress(kind: str, value: dict[str, Any]) -> dict[str, int | float]:
    if kind == "minute":
        result = {field: value[field] for field in ("issued", "expired", "lastIssuedCutoff", "lastClosedTarget")}
        result["updatedAtMs"] = value["updatedAtMs"] if value["updatedAtMs"] is not None else -1
        result.update({field: value["totals"][field] for field in ("n", "up", "down", "flat")})
        for name in MINUTE_SCORES:
            result.update({f"{name}.{field}": amount for field, amount in value["totals"][name].items()})
        return result
    result = {field: value[field] if value[field] is not None else -1 for field in ("revision", "lastProbeBucket", "lastProbeAtMs")}
    for field in ("exchangeMs", "receivedMs"):
        result[f"quote.{field}"] = value["lastQuote"][field] if value["lastQuote"] is not None else -1
    for h, metric in value["metrics"].items():
        for field in ("issued", "resolved", "expired", "capacityDrops"):
            result[f"{h}.{field}"] = metric[field]
        for index, count in enumerate(metric["counts"]):
            result[f"{h}.count.{index}"] = count
        for name in LIVE_SCORES:
            result.update({f"{h}.{name}.{field}": amount for field, amount in metric[name].items()})
    return result


def _advance(kind: str, old: dict[str, Any], new: dict[str, Any]) -> None:
    before, after = _progress(kind, old), _progress(kind, new)
    if any(after[name] < amount for name, amount in before.items()):
        raise ValueError("learning_checkpoint_count_regression")
    old_pending = {row["id"]: row for row in old["pending"]}
    new_pending = {row["id"]: row for row in new["pending"]}
    if any(new_pending[ident] != row for ident, row in old_pending.items() if ident in new_pending):
        raise ValueError("learning_pending_identity_conflict")
    if kind == "minute":
        if old["model"]["n"] == new["model"]["n"] and (old["model"] != new["model"] or old["totals"] != new["totals"] or old["recent"] != new["recent"]):
            raise ValueError("learning_checkpoint_training_without_samples")
        removed = old_pending.keys() - new_pending.keys()
        progress = new["totals"]["n"] - old["totals"]["n"] + new["expired"] - old["expired"]
        if len(removed) > progress or any(old_pending[ident]["target"] > new["lastClosedTarget"] for ident in removed):
            raise ValueError("learning_pending_progress_missing")
        for row in new["recent"]:
            if row["id"] in old_pending and any(row[field] != old_pending[row["id"]][field] for field in MINUTE_FORECAST):
                raise ValueError("learning_pending_identity_conflict")
        if any(row["cutoff"] <= old["lastIssuedCutoff"] for ident, row in new_pending.items() if ident not in old_pending):
            raise ValueError("learning_pending_identity_reused")
    else:
        for h in HORIZONS:
            a, b = old["metrics"][str(h)], new["metrics"][str(h)]
            if a["resolved"] == b["resolved"] and (old["models"][str(h)] != new["models"][str(h)] or any(a[field] != b[field] for field in ("counts", "recent", *LIVE_SCORES))):
                raise ValueError("learning_checkpoint_training_without_samples")
            removed = [row for ident, row in old_pending.items() if ident not in new_pending and row["horizon"] == h]
            if len(removed) > b["resolved"] - a["resolved"] + b["expired"] - a["expired"]:
                raise ValueError("learning_pending_progress_missing")
            for row in b["recent"]:
                if row["id"] in old_pending and any(row[field] != old_pending[row["id"]][field] for field in ("p", "baseline")):
                    raise ValueError("learning_pending_identity_conflict")
        if any(old["lastProbeAtMs"] is not None and row["issuedAtMs"] <= old["lastProbeAtMs"] for ident, row in new_pending.items() if ident not in old_pending):
            raise ValueError("learning_pending_identity_reused")


def _head(db: sqlite3.Connection, namespace: str, kind: str, key: str) -> tuple[Any, ...] | None:
    # Do not materialize an arbitrarily large damaged compressed BLOB in Python.
    return db.execute("""SELECT lineage,revision,digest,
        CASE WHEN typeof(payload)='blob' AND length(payload)<=? THEN payload END,
        length,saved_at FROM checkpoints WHERE namespace=? AND kind=? AND key=?""",
        (MAX_COMPRESSED_BYTES, namespace, kind, key)).fetchone()


def _decode(row: tuple[Any, ...]) -> str:
    lineage, revision, digest, payload, length, saved_at = row
    try:
        _identity(lineage)
        _integer(revision, 1)
        _integer(length, 0, MAX_BYTES)
        _number(saved_at, 0)
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest) or type(payload) is not bytes or len(payload) > MAX_COMPRESSED_BYTES:
            raise ValueError("Invalid stored learning metadata")
        unpacker = zlib.decompressobj()
        raw = unpacker.decompress(payload, MAX_BYTES + 1)
        if len(raw) > MAX_BYTES or not unpacker.eof or unpacker.unused_data or unpacker.unconsumed_tail or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Invalid stored learning payload")
        text = raw.decode("utf-8")
        if len(text) != length:
            raise ValueError("Invalid stored learning length")
        return text
    except (ValueError, TypeError, UnicodeError, zlib.error, OverflowError) as exc:
        raise ValueError("learning_checkpoint_corrupt") from exc


def save(namespace: str, kind: str, key: str, checkpoint: dict[str, Any]) -> dict[str, Any]:
    _address(namespace, kind, key)
    _object(checkpoint, {"lineage", "revision", "text"})
    _identity(checkpoint["lineage"])
    _integer(checkpoint["revision"], 1)
    text = checkpoint["text"]
    value, _, outcomes = _state(kind, key, text)
    raw = text.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    db = _database(True)
    try:
        with db:
            db.execute("BEGIN IMMEDIATE")
            old = _head(db, namespace, kind, key)
            if old:
                previous, _, _ = _state(kind, key, _decode(old))
                if old[0] != checkpoint["lineage"]:
                    raise ValueError("learning_checkpoint_lineage_conflict")
                if old[1] == checkpoint["revision"] and old[2] != digest:
                    raise ValueError("learning_checkpoint_revision_conflict")
                if old[1] >= checkpoint["revision"]:
                    return {"saved": old[2] == digest, "revision": old[1], "digest": old[2], "status": "unchanged" if old[2] == digest else "disk_newer"}
                _advance(kind, previous, value)
            for ident, row in outcomes:
                payload = json.dumps(row, sort_keys=True, allow_nan=False, separators=(",", ":"))
                prior = db.execute("SELECT payload FROM outcomes WHERE namespace=? AND kind=? AND key=? AND id=?", (namespace, kind, key, ident)).fetchone()
                if prior and prior[0] != payload:
                    raise ValueError("learning_outcome_identity_conflict")
                db.execute("INSERT OR IGNORE INTO outcomes VALUES(?,?,?,?,?)", (namespace, kind, key, ident, payload))
            db.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(namespace,kind,key) DO UPDATE SET lineage=excluded.lineage,revision=excluded.revision,digest=excluded.digest,payload=excluded.payload,length=excluded.length,saved_at=excluded.saved_at", (namespace, kind, key, checkpoint["lineage"], checkpoint["revision"], digest, zlib.compress(raw), len(text), time.time()))
        return {"saved": True, "revision": checkpoint["revision"], "digest": digest, "status": "saved"}
    finally:
        db.close()


def _has_checkpoints(db: sqlite3.Connection) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='checkpoints'").fetchone() is not None


def load(namespace: str, kind: str, key: str, offset: int = 0, digest: str | None = None) -> dict[str, Any]:
    _address(namespace, kind, key)
    _integer(offset, 0, MAX_BYTES)
    if digest is not None and (not isinstance(digest, str) or not DIGEST.fullmatch(digest)):
        raise ValueError("Invalid learning checkpoint read")
    db = _database()
    if db is None:
        return {"found": False}
    try:
        row = _head(db, namespace, kind, key) if _has_checkpoints(db) else None
        if row is None:
            return {"found": False}
        if digest is not None and digest != row[2]:
            raise ValueError("learning_checkpoint_changed_during_read")
        text = _decode(row)
        _state(kind, key, text)
        if offset > len(text):
            raise ValueError("Invalid learning checkpoint offset")
        return {"found": True, "lineage": row[0], "revision": row[1], "digest": row[2], "length": row[4], "offset": offset, "text": text[offset:offset + CHUNK_CHARS], "saved_at": row[5]}
    finally:
        db.close()


def profiles(limit: int = 32) -> dict[str, Any]:
    """Bounded metadata for manual recovery; never choose another profile."""
    _integer(limit, 1, 32)
    db = _database()
    if db is None:
        return {"profiles": []}
    try:
        rows = db.execute("SELECT namespace,COUNT(*),MAX(saved_at) FROM checkpoints GROUP BY namespace ORDER BY MAX(saved_at) DESC,namespace LIMIT ?", (limit,)).fetchall() if _has_checkpoints(db) else []
        result = []
        for namespace, partitions, saved_at in rows:
            _identity(namespace)
            _integer(partitions, 1)
            _number(saved_at, 0)
            result.append({"namespace": namespace, "partitions": partitions, "saved_at": saved_at})
        return {"profiles": result}
    finally:
        db.close()
