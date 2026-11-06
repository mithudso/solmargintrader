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

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .state import atomic_write_json

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
    return doc if isinstance(doc, dict) and doc.get("schema") == SOAK_SCHEMA else None


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
        doc["last_tick_at"] = now
    atomic_write_json(_soak_path(root), doc)
    return doc


def grandfather(root: Path, cfg: Config, reason: str, now: float | None = None) -> dict[str, Any]:
    """Record the one-time exemption for the configuration that is live today.

    It exempts exactly this fingerprint from the soak. Any later strategy or cap change makes the entry stale, and the
    new configuration must soak. The entry is never renewed: a second call is refused.
    """
    now = time.time() if now is None else now
    if not reason.strip():
        raise ValueError("a grandfather entry needs a reason")
    fp = config_fingerprint(cfg)
    doc = load_soak(root) or _empty(fp, now)
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


def record_research_result(
    root: Path, cfg: Config, strategy: str, result: str, source: str, note: str = "", now: float | None = None
) -> dict[str, Any]:
    """Append a research/backtest gate result. `result` is `pass` or `fail`; `source` says where it came from."""
    if result not in ("pass", "fail"):
        raise ValueError("result must be pass or fail")
    if not strategy or not source.strip():
        raise ValueError("strategy and source are required")
    now = time.time() if now is None else now
    path = research_path(root, cfg)
    try:
        doc = json.loads(path.read_text())
        results = doc["results"] if isinstance(doc, dict) and isinstance(doc.get("results"), list) else []
    except (OSError, ValueError):
        results = []
    results.append({"strategy": strategy, "result": result, "checked_at": now, "source": source, "note": note})
    doc = {"schema": RESEARCH_SCHEMA, "results": results}
    atomic_write_json(path, doc)
    return doc


def latest_research_result(root: Path, cfg: Config) -> dict[str, Any] | None:
    try:
        results = json.loads(research_path(root, cfg).read_text())["results"]
        mine = [
            r
            for r in results
            if isinstance(r, dict)
            and r.get("strategy") == cfg.gates.strategy_id
            and isinstance(r.get("checked_at"), int | float)
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return max(mine, key=lambda r: r["checked_at"]) if mine else None


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
