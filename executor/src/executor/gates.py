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
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import Config, fingerprint
from .errors import BadParams

SOAK_SCHEMA = "executor-soak/1"
RESEARCH_SCHEMA = "executor-research-gate/1"
MAX_TICK_GAP_S = 1800.0


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
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def _mutation_lock(path: Path):
    """Lock the stable sidecar, since replacement changes the data file's inode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path.with_name(path.name + ".lock"), os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _finite_nonnegative(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def _valid_soak(cur: Any) -> bool:
    return (
        isinstance(cur, dict)
        and isinstance(cur.get("fingerprint"), str)
        and all(_finite_nonnegative(cur.get(name)) for name in ("started_at", "last_tick_at", "accumulated_s"))
        and type(cur.get("dry_runs")) is int
        and cur["dry_runs"] >= 0
        and isinstance(cur.get("resets"), list)
    )


def _valid_research(row: Any) -> bool:
    return (
        isinstance(row, dict)
        and isinstance(row.get("strategy"), str)
        and bool(row["strategy"].strip())
        and row.get("result") in ("pass", "fail")
        and _finite_nonnegative(row.get("checked_at"))
        and isinstance(row.get("source"), str)
        and bool(row["source"].strip())
    )


def _iso(ts: Any) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))
    except (TypeError, ValueError, OverflowError):
        return "unknown time"


# -- soak ----------------------------------------------------------------------------------------------------


def _soak_path(root: Path) -> Path:
    return root / "soak.json"


def load_soak(root: Path) -> dict[str, Any]:
    try:
        doc = json.loads(_soak_path(root).read_text())
    except (OSError, ValueError):
        return {"schema": SOAK_SCHEMA, "strategies": {}}
    if not isinstance(doc, dict) or doc.get("schema") != SOAK_SCHEMA or not isinstance(doc.get("strategies"), dict):
        return {"schema": SOAK_SCHEMA, "strategies": {}}
    return doc


def record_dry_run(root: Path, cfg: Config, strategy: str, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    if not _finite_nonnegative(now):
        raise BadParams("dry-run timestamp must be finite and nonnegative")
    fp = fingerprint(cfg, strategy)
    doc = load_soak(root)
    cur = doc["strategies"].get(strategy)
    if not _valid_soak(cur) or cur.get("fingerprint") != fp:
        cur = cur if _valid_soak(cur) else None
        resets = (cur or {}).get("resets", [])
        if cur:
            resets = (resets + [{"at": now, "from": cur.get("fingerprint")}])[-20:]
        cur = {
            "fingerprint": fp,
            "started_at": now,
            "last_tick_at": now,
            "accumulated_s": 0.0,
            "dry_runs": 1,
            "resets": resets,
        }
    else:
        gap = max(0.0, now - float(cur.get("last_tick_at", now)))
        cur["accumulated_s"] = float(cur.get("accumulated_s", 0.0)) + min(gap, MAX_TICK_GAP_S)
        cur["last_tick_at"] = now
        cur["dry_runs"] = int(cur.get("dry_runs", 0)) + 1
    doc["strategies"][strategy] = cur
    _atomic_write(_soak_path(root), doc)
    return cur


def soak_status(root: Path, cfg: Config, strategy: str) -> tuple[bool, str]:
    required = cfg.gates.soak_hours * 3600
    cur = load_soak(root)["strategies"].get(strategy)
    if not _valid_soak(cur):
        return False, f"no valid dry-run soak recorded for '{strategy}': run it in dry-run first"
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


def record_research_result(
    root: Path, cfg: Config, strategy: str, result: str, source: str, note: str = "", now: float | None = None
) -> dict[str, Any]:
    if result not in ("pass", "fail"):
        raise BadParams("result must be pass or fail")
    if not strategy.strip() or not source.strip():
        raise BadParams("strategy and source are required")
    path = research_path(root, cfg)
    now = time.time() if now is None else now
    if not _finite_nonnegative(now):
        raise BadParams("research timestamp must be finite and nonnegative")
    row = {"strategy": strategy, "result": result, "checked_at": now, "source": source, "note": note}
    with _mutation_lock(path):
        try:
            doc = json.loads(path.read_text())
            results = doc["results"]
            if doc.get("schema") != RESEARCH_SCHEMA or not isinstance(results, list):
                results = []
        except (OSError, ValueError, KeyError, TypeError):
            results = []
        results.append(row)
        _atomic_write(path, {"schema": RESEARCH_SCHEMA, "results": results})
    return row


def latest_research_result(root: Path, cfg: Config, strategy: str) -> dict[str, Any] | None:
    try:
        doc = json.loads(research_path(root, cfg).read_text())
        results = doc["results"]
        if doc.get("schema") != RESEARCH_SCHEMA or not isinstance(results, list):
            return None
        if any(not _valid_research(row) for row in results):
            return None
        mine = [row for row in results if row["strategy"] == strategy]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return max(mine, key=lambda row: row["checked_at"]) if mine else None


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
    now = time.time() if now is None else now
    root.mkdir(parents=True, exist_ok=True)
    if not _finite_nonnegative(now):
        raise BadParams("override timestamp must be finite and nonnegative")
    line = {"at": now, "iso": _iso(now), "gate": "research", "strategy": strategy, "why": why}
    fd = os.open(root / "gate-overrides.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, (json.dumps(line, allow_nan=False) + "\n").encode())
        os.fsync(fd)
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
