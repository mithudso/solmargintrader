"""Pre-live gates, per strategy: a dry-run soak and a research gate. Same pattern as liquidity/src/aero_lp/gates.py.

1. Dry-run soak. A strategy must have run in dry-run for `[gates].soak_hours` (24 h) with at least
   `[gates].min_dry_runs` fully simulated dry-run swaps before it may go live. Every dry-run swap that passes the
   whole pipeline credits one tick (`record_dry_run`). One tick counts for at most MAX_TICK_GAP_S, so a stopped runner
   cannot bank its downtime. A change to the rails or owner resets that strategy's soak.
2. Research gate. `$EXECUTOR_HOME/research-gate.json` holds backtest/research results per strategy. Live is refused
   unless the latest result for the strategy is `pass`. Only `[gates].allow_failed_research_gate = true` overrides
   it, and every use is printed in the result and appended to `gate-overrides.jsonl`.

Exits (reduce-only sells) are never gated: reducing risk must always be possible. Everything fails closed: a missing
or unreadable record counts as "not satisfied".
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import Config, fingerprint
from .errors import BadParams, ExecutorError

SOAK_SCHEMA = "executor-soak/1"
RESEARCH_SCHEMA = "executor-research-gate/1"
MAX_TICK_GAP_S = 1800.0


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        # A recorded failure must remain the latest evidence after a power loss too.
        _sync_directory(path.parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def _state_lock(path: Path) -> Iterator[None]:
    # The data inode changes at replace(). Every writer must lock the stable sidecar instead.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path.with_name(path.name + ".lock"), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _nonnegative_number(value: Any) -> bool:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate gate record field")
        out[key] = value
    return out


def _invalid_constant(_value: str) -> None:
    raise ValueError("non-finite gate record value")


def _read_document(path: Path) -> Any:
    return json.loads(path.read_text(), object_pairs_hook=_json_object, parse_constant=_invalid_constant)


def _recording_time(now: float | None) -> float:
    value = time.time() if now is None else now
    if not _timestamp(value):
        raise BadParams("gate recording time must be a finite nonnegative timestamp")
    return value


def _iso(ts: Any) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))
    except (TypeError, ValueError, OverflowError):
        return "unknown time"


def _timestamp(value: Any) -> bool:
    return _nonnegative_number(value) and _iso(value) != "unknown time"


# -- soak ----------------------------------------------------------------------------------------------------


def _soak_path(root: Path) -> Path:
    return root / "soak.json"


def _valid_soak(cur: Any) -> bool:
    if not isinstance(cur, dict) or not _nonblank(cur.get("fingerprint")):
        return False
    if not all(_timestamp(cur.get(key)) for key in ("started_at", "last_tick_at")):
        return False
    if not _nonnegative_number(cur.get("accumulated_s")):
        return False
    runs = cur.get("dry_runs")
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1:
        return False
    start, last, done = cur["started_at"], cur["last_tick_at"], cur["accumulated_s"]
    if last < start or done > last - start + 1e-6 or done / MAX_TICK_GAP_S > runs - 1:
        return False
    resets = cur.get("resets")
    return isinstance(resets, list) and all(
        isinstance(reset, dict) and _timestamp(reset.get("at")) and _nonblank(reset.get("from")) for reset in resets
    )


def load_soak(root: Path) -> dict[str, Any]:
    try:
        doc = _read_document(_soak_path(root))
    except (OSError, ValueError):
        return {"schema": SOAK_SCHEMA, "strategies": {}}
    if not isinstance(doc, dict) or doc.get("schema") != SOAK_SCHEMA or not isinstance(doc.get("strategies"), dict):
        return {"schema": SOAK_SCHEMA, "strategies": {}}
    # Invalid credit is discarded; it can only be rebuilt by successful dry-runs.
    return {
        "schema": SOAK_SCHEMA,
        "strategies": {key: cur for key, cur in doc["strategies"].items() if _nonblank(key) and _valid_soak(cur)},
    }


def record_dry_run(root: Path, cfg: Config, strategy: str, now: float | None = None) -> dict[str, Any]:
    now = _recording_time(now)
    if not _nonblank(strategy):
        raise BadParams("strategy is required")
    fp = fingerprint(cfg, strategy)
    path = _soak_path(root)
    with _state_lock(path):
        doc = load_soak(root)
        cur = doc["strategies"].get(strategy)
        if not cur or cur["fingerprint"] != fp or now < cur["last_tick_at"]:
            resets = cur["resets"] if cur else []
            if cur:
                resets = (resets + [{"at": now, "from": cur["fingerprint"]}])[-20:]
            cur = {
                "fingerprint": fp,
                "started_at": now,
                "last_tick_at": now,
                "accumulated_s": 0.0,
                "dry_runs": 1,
                "resets": resets,
            }
        else:
            gap = now - cur["last_tick_at"]
            cur["accumulated_s"] += min(gap, MAX_TICK_GAP_S)
            cur["last_tick_at"] = now
            cur["dry_runs"] += 1
        doc["strategies"][strategy] = cur
        _atomic_write(path, doc)
    return cur


def soak_status(root: Path, cfg: Config, strategy: str) -> tuple[bool, str]:
    required = cfg.gates.soak_hours * 3600
    cur = load_soak(root)["strategies"].get(strategy)
    if not cur:
        return False, f"no dry-run soak recorded for '{strategy}': run it in dry-run first"
    if cur.get("fingerprint") != fingerprint(cfg, strategy):
        return False, "the rails or owner changed since the last dry-run; the soak restarts at the next dry-run"
    done = float(cur.get("accumulated_s", 0.0))
    runs = int(cur.get("dry_runs", 0))
    if done < required or runs < cfg.gates.min_dry_runs:
        return False, (
            f"dry-run soak {done / 3600:.1f} h of {cfg.gates.soak_hours:g} h and {runs} of "
            f"{cfg.gates.min_dry_runs} dry-run swaps"
        )
    return True, f"soaked {done / 3600:.1f} h over {runs} dry-run swaps"


# -- research gate -------------------------------------------------------------------------------------------


def research_path(root: Path, cfg: Config) -> Path:
    return (
        Path(cfg.gates.research_gate_file).expanduser() if cfg.gates.research_gate_file else root / "research-gate.json"
    )


def _research_results(path: Path) -> list[dict[str, Any]]:
    try:
        doc = _read_document(path)
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        raise ExecutorError(
            "research gate record is unreadable; inspect it before recording new results", "refused"
        ) from None
    if not isinstance(doc, dict) or doc.get("schema") != RESEARCH_SCHEMA or not isinstance(doc.get("results"), list):
        raise ExecutorError("research gate record is malformed; inspect it before recording new results", "refused")
    results = doc["results"]
    if not all(
        isinstance(row, dict)
        and _nonblank(row.get("strategy"))
        and row.get("result") in ("pass", "fail")
        and _timestamp(row.get("checked_at"))
        and _nonblank(row.get("source"))
        and isinstance(row.get("note", ""), str)
        for row in results
    ):
        # A malformed later failure must never silently revive an older pass.
        raise ExecutorError("research gate evidence is malformed; inspect it before recording new results", "refused")
    last_checked: dict[str, int | float] = {}
    for row in results:
        strategy, checked = row["strategy"], row["checked_at"]
        if strategy in last_checked and checked < last_checked[strategy]:
            raise ExecutorError(
                "research gate chronology is inconsistent; inspect it before recording new results", "refused"
            )
        last_checked[strategy] = checked
    return results


def record_research_result(
    root: Path, cfg: Config, strategy: str, result: str, source: str, note: str = "", now: float | None = None
) -> dict[str, Any]:
    if result not in ("pass", "fail"):
        raise BadParams("result must be pass or fail")
    if not _nonblank(strategy) or not _nonblank(source):
        raise BadParams("strategy and source are required")
    if not isinstance(note, str):
        raise BadParams("note must be text")
    now = _recording_time(now)
    path = research_path(root, cfg)
    with _state_lock(path):
        results = _research_results(path)
        # Retain a clock-regressed result. Readers then block on the chronology instead of reviving an older pass.
        results.append({"strategy": strategy, "result": result, "checked_at": now, "source": source, "note": note})
        _atomic_write(path, {"schema": RESEARCH_SCHEMA, "results": results})
    return results[-1]


def latest_research_result(root: Path, cfg: Config, strategy: str) -> dict[str, Any] | None:
    try:
        results = _research_results(research_path(root, cfg))
    except ExecutorError:
        return None
    mine = [(index, row) for index, row in enumerate(results) if row["strategy"] == strategy]
    return max(mine, key=lambda item: (item[1]["checked_at"], item[0]))[1] if mine else None


def research_status(root: Path, cfg: Config, strategy: str) -> tuple[bool, str]:
    latest = latest_research_result(root, cfg, strategy)
    if latest is None:
        return False, f"no research-gate result recorded for strategy '{strategy}'"
    if latest.get("result") != "pass":
        return (
            False,
            f"latest research-gate result for '{strategy}' is {latest.get('result')!r} ({latest.get('source')})",
        )
    return True, f"research gate passed ({latest.get('source')}, {_iso(latest.get('checked_at'))})"


def log_override(root: Path, strategy: str, why: str, now: float | None = None) -> None:
    now = _recording_time(now)
    root.mkdir(parents=True, exist_ok=True)
    line = {"at": now, "iso": _iso(now), "gate": "research", "strategy": strategy, "why": why}
    fd = os.open(root / "gate-overrides.jsonl", os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        # Short writes are legal. Keep the record locked until all bytes are durable so writers cannot interleave it.
        fcntl.flock(fd, fcntl.LOCK_EX)
        size = os.fstat(fd).st_size
        if size and os.pread(fd, 1, size - 1) != b"\n":
            raise ExecutorError(
                "research gate override audit record is incomplete; inspect it before proceeding", "refused"
            )
        pending = memoryview((json.dumps(line, allow_nan=False) + "\n").encode())
        while pending:
            written = os.write(fd, pending)
            if written <= 0:
                raise ExecutorError("could not persist the research gate override audit record", "refused")
            pending = pending[written:]
        os.fsync(fd)
        _sync_directory(root)
    except OSError:
        raise ExecutorError("could not persist the research gate override audit record", "refused") from None
    finally:
        os.close(fd)


def check_live_allowed(root: Path, cfg: Config, strategy: str, now: float | None = None) -> tuple[list[str], list[str]]:
    """Return (problems, notes). Problems are every failed gate; an override turns the research problem into a note."""
    problems: list[str] = []
    notes: list[str] = []
    ok, why = soak_status(root, cfg, strategy)
    (notes if ok else problems).append(f"soak gate: {why}")
    ok, why = research_status(root, cfg, strategy)
    if ok:
        notes.append(f"research gate: {why}")
    elif cfg.gates.allow_failed_research_gate:
        log_override(root, strategy, why, now)
        notes.append(f"WARNING research gate OVERRIDDEN by [gates].allow_failed_research_gate: {why}")
    else:
        problems.append(
            f"research gate: {why}. Record a pass with `executor gates record-research`, or the owner can set "
            "[gates].allow_failed_research_gate = true (logged)"
        )
    return problems, notes


def summary(root: Path, cfg: Config, strategy: str) -> dict[str, Any]:
    soak_ok, soak_why = soak_status(root, cfg, strategy)
    res_ok, res_why = research_status(root, cfg, strategy)
    return {
        "strategy": strategy,
        "soak_ok": soak_ok,
        "soak": soak_why,
        "research_ok": res_ok,
        "research": res_why,
        "research_override": cfg.gates.allow_failed_research_gate,
        "live_allowed": soak_ok and (res_ok or cfg.gates.allow_failed_research_gate),
    }
