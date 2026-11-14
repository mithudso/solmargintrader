"""Pre-live gates: a dry-run soak and a research-gate check.

Why these exist: on 2026-11-06 the bot was built, its research gate failed (9 of 70 claims unsupported), and it was
switched to live signing within hours. Two gates now stand between a configuration and live signing.

1. Dry-run soak. The configuration must have run in dry-run (`aero-lp daemon` without `--live`) for
   `[gates].soak_hours` (default 24). The dry-run daemon records its progress in `$AERO_LP_HOME/soak.json`. A change to
   anything that affects strategy or caps (`config_fingerprint`) resets the soak. The one exception is a *grandfather*
   entry: a visible, one-time record that exempts one exact configuration (see `grandfather`).
2. Research gate. `$AERO_LP_HOME/research-gate.json` holds research/backtest gate results per strategy. Live mode is
   refused when the latest result for `[gates].strategy_id` is `fail` or absent. The owner can override only with
   `[gates].allow_failed_research_gate = true`; every use is printed and appended to `gate-overrides.jsonl`.

Neither gate applies to `exit-to-safe`: reducing risk must always be possible.
All checks fail closed: a missing or unreadable record counts as "not satisfied".
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .state import atomic_write_json
from .validation import finite_number

SOAK_SCHEMA = "aero-lp-soak/1"
RESEARCH_SCHEMA = "aero-lp-research-gate/1"
# One dry-run interval counts for at most this long, so a stopped daemon cannot bank the downtime as soak.
MAX_TICK_GAP_S = 1800.0
MAX_RESETS_KEPT = 20


class LiveGateError(RuntimeError):
    """Live signing is refused. The message says which gate failed and what to do."""


def config_fingerprint(cfg: Config) -> str:
    """Hash of everything that affects strategy or caps. Polling, RPC, paths and the gates themselves are excluded."""
    doc = {
        "owner": cfg.owner.lower(),
        "reward_mode": cfg.reward_mode,
        "strategy": asdict(cfg.strategy),
        "execution": asdict(cfg.execution),
        "safety": asdict(cfg.safety),
        "allocator": asdict(cfg.allocator),
    }
    return hashlib.sha256(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()


def _soak_path(root: Path) -> Path:
    return root / "soak.json"


def load_soak(root: Path) -> dict[str, Any] | None:
    try:
        doc = json.loads(_soak_path(root).read_text())
    except (OSError, ValueError):
        return None
    try:
        if not isinstance(doc, dict) or doc.get("schema") != SOAK_SCHEMA or not isinstance(doc["fingerprint"], str):
            return None
        for name in ("started_at", "last_tick_at", "accumulated_s"):
            finite_number(doc[name], name)
        resets = doc["resets"]
        if not isinstance(resets, list):
            return None
        for reset in resets:
            finite_number(reset["at"], "reset time")
            if not all(isinstance(reset[k], str) for k in ("from", "to")):
                return None
        gf = doc.get("grandfather")
        if gf is not None:
            finite_number(gf["at"], "grandfather time")
            if not all(isinstance(gf[k], str) and gf[k].strip() for k in ("fingerprint", "reason", "owner")):
                return None
    except (KeyError, TypeError, ValueError):
        return None
    return doc


@contextmanager
def _record_lock(path: Path):
    """Serialize each read-modify-replace using a stable inode, including across processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _empty(fp: str, now: float) -> dict[str, Any]:
    return {
        "schema": SOAK_SCHEMA,
        "fingerprint": fp,
        "started_at": now,
        "last_tick_at": now,
        "accumulated_s": 0.0,
        "resets": [],
        "grandfather": None,
    }


def record_dry_run_tick(root: Path, cfg: Config, now: float | None = None) -> dict[str, Any]:
    """Credit one dry-run interval to the current configuration; reset the soak when the configuration changed."""
    now = time.time() if now is None else now
    finite_number(now, "soak time")
    fp = config_fingerprint(cfg)
    doc = load_soak(root)
    if doc is None:
        doc = _empty(fp, now)
    elif doc["fingerprint"] != fp:
        resets = (doc.get("resets") or []) + [{"at": now, "from": doc["fingerprint"], "to": fp}]
        doc.update(
            fingerprint=fp,
            started_at=now,
            last_tick_at=now,
            accumulated_s=0.0,
            resets=resets[-MAX_RESETS_KEPT:],
        )
    else:
        gap = max(0.0, now - float(doc.get("last_tick_at", now)))
        doc["accumulated_s"] = float(doc.get("accumulated_s", 0.0)) + min(gap, MAX_TICK_GAP_S)
        # A backward wall clock must not make an already credited interval available again.
        doc["last_tick_at"] = max(now, float(doc["last_tick_at"]))
    atomic_write_json(_soak_path(root), doc)
    return doc


def grandfather(root: Path, cfg: Config, reason: str, now: float | None = None) -> dict[str, Any]:
    """Record the one-time exemption for the configuration that is live today.

    It exempts exactly this fingerprint from the soak. Any later strategy or cap change makes the entry stale, and the
    new configuration must soak. The entry is never renewed: a second call is refused.
    """
    now = time.time() if now is None else now
    finite_number(now, "grandfather time")
    if not reason.strip():
        raise ValueError("a grandfather entry needs a reason")
    fp = config_fingerprint(cfg)
    doc = load_soak(root)
    if doc is None and _soak_path(root).exists():
        raise LiveGateError("invalid soak record; cannot establish whether a grandfather entry already exists")
    doc = doc or _empty(fp, now)
    if doc.get("grandfather"):
        raise LiveGateError("a grandfather entry already exists (it is one-time); see `aero-lp gates status`")
    doc["grandfather"] = {"fingerprint": fp, "at": now, "reason": reason.strip(), "owner": cfg.owner}
    atomic_write_json(_soak_path(root), doc)
    return doc


@dataclass(frozen=True)
class SoakStatus:
    ok: bool
    reason: str
    accumulated_s: float
    required_s: float
    grandfathered: bool


def soak_status(root: Path, cfg: Config) -> SoakStatus:
    required = cfg.gates.soak_hours * 3600
    fp = config_fingerprint(cfg)
    doc = load_soak(root)
    if doc is None:
        return SoakStatus(False, "no soak record: run `aero-lp daemon` in dry-run first", 0.0, required, False)
    gf = doc.get("grandfather") or {}
    if gf.get("fingerprint") == fp:
        return SoakStatus(True, f"grandfathered on {_iso(gf.get('at'))}: {gf.get('reason')}", 0.0, required, True)
    done = float(doc.get("accumulated_s", 0.0)) if doc.get("fingerprint") == fp else 0.0
    if done >= required:
        return SoakStatus(True, f"soaked {done / 3600:.1f} h in dry-run", done, required, False)
    stale = (
        " (the configuration changed since the last dry-run tick; the dry-run daemon will reset the soak)"
        if (doc.get("fingerprint") != fp)
        else ""
    )
    return SoakStatus(
        False,
        f"dry-run soak {done / 3600:.1f} h of {cfg.gates.soak_hours:g} h required{stale}",
        done,
        required,
        False,
    )


def _iso(ts: Any) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))
    except (TypeError, ValueError, OverflowError):
        return "unknown time"


# ---------------------------------------------------------------------------------------------- research gate


def research_path(root: Path, cfg: Config) -> Path:
    return (
        Path(cfg.gates.research_gate_file).expanduser() if cfg.gates.research_gate_file else root / "research-gate.json"
    )


def _research_document(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != RESEARCH_SCHEMA or not isinstance(doc.get("results"), list):
        raise ValueError("invalid research gate document")
    for row in doc["results"]:
        if not isinstance(row, dict) or row.get("result") not in ("pass", "fail"):
            raise ValueError("invalid research gate result")
        finite_number(row.get("checked_at"), "research timestamp")
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in ("strategy", "source")):
            raise ValueError("research strategy and source are required")
    return doc


def record_research_result(
    root: Path, cfg: Config, strategy: str, result: str, source: str, note: str = "", now: float | None = None
) -> dict[str, Any]:
    """Append a research/backtest gate result. `result` is `pass` or `fail`; `source` says where it came from."""
    if result not in ("pass", "fail"):
        raise ValueError("result must be pass or fail")
    if not strategy or not source.strip():
        raise ValueError("strategy and source are required")
    now = time.time() if now is None else now
    finite_number(now, "research timestamp")
    path = research_path(root, cfg)
    with _record_lock(path):
        try:
            doc = _research_document(path)
        except FileNotFoundError:
            doc = {"schema": RESEARCH_SCHEMA, "results": []}
        doc["results"].append(
            {"strategy": strategy, "result": result, "checked_at": now, "source": source, "note": note}
        )
        atomic_write_json(path, doc)
    return doc


def latest_research_result(root: Path, cfg: Config) -> dict[str, Any] | None:
    try:
        results = _research_document(research_path(root, cfg))["results"]
        mine = [
            r
            for r in results
            if isinstance(r, dict)
            and r.get("strategy") == cfg.gates.strategy_id
            and isinstance(r.get("checked_at"), int | float)
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    # Append order breaks equal timestamp ties, so a same-time failure cannot hide behind an older pass.
    return max(enumerate(mine), key=lambda item: (item[1]["checked_at"], item[0]))[1] if mine else None


def research_status(root: Path, cfg: Config) -> tuple[bool, str]:
    latest = latest_research_result(root, cfg)
    sid = cfg.gates.strategy_id
    if latest is None:
        return False, f"no research-gate result recorded for strategy '{sid}'"
    if latest.get("result") != "pass":
        return False, f"latest research-gate result for '{sid}' is {latest.get('result')!r} ({latest.get('source')})"
    return True, f"research gate passed ({latest.get('source')}, {_iso(latest.get('checked_at'))})"


def _log_override(root: Path, cfg: Config, why: str, now: float) -> None:
    line = {"at": now, "iso": _iso(now), "gate": "research", "strategy": cfg.gates.strategy_id, "why": why}
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "gate-overrides.jsonl", "a") as f:
        f.write(json.dumps(line) + "\n")


def check_live_allowed(root: Path, cfg: Config, now: float | None = None) -> list[str]:
    """Return notes to print when live signing may start; raise `LiveGateError` listing every failed gate."""
    now = time.time() if now is None else now
    finite_number(now, "gate check time")
    problems: list[str] = []
    notes: list[str] = []
    soak = soak_status(root, cfg)
    (notes if soak.ok else problems).append(f"soak gate: {soak.reason}")
    ok, why = research_status(root, cfg)
    if ok:
        notes.append(f"research gate: {why}")
    elif cfg.gates.allow_failed_research_gate:
        _log_override(root, cfg, why, now)
        notes.append(f"WARNING research gate OVERRIDDEN by [gates].allow_failed_research_gate: {why}")
    else:
        problems.append(
            f"research gate: {why}. Record a passing result with `aero-lp gates record-research`, or the owner can set "
            "[gates].allow_failed_research_gate = true (logged)"
        )
    if problems:
        raise LiveGateError("refusing live mode:\n  " + "\n  ".join(problems))
    return notes


def summary(root: Path, cfg: Config) -> dict[str, Any]:
    """Compact view for status.json."""
    soak = soak_status(root, cfg)
    ok, why = research_status(root, cfg)
    return {
        "soak_ok": soak.ok,
        "soak_reason": soak.reason,
        "soak_hours": soak.accumulated_s / 3600,
        "soak_required_hours": soak.required_s / 3600,
        "grandfathered": soak.grandfathered,
        "research_ok": ok,
        "research_reason": why,
        "research_override": cfg.gates.allow_failed_research_gate,
    }
