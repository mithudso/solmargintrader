"""Research provenance and explicit paper handoffs for the browser workspace.

This module neither fetches data nor starts workers. A snapshot describes the
arrays actually loaded by the sweep, not a later read of a mutable CSV file.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
import uuid
from typing import Any


def context_id(value: dict[str, Any]) -> str:
    body = {k: v for k, v in value.items() if k != "id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def research_context(settings: Any, roster: Any, arrays: dict[str, Any]) -> dict[str, Any]:
    from . import forwardtest
    from .simulation import from_settings

    digest = hashlib.sha256()
    for key in sorted(arrays):
        array = arrays[key]
        digest.update(f"{key}:{array.dtype}:{array.shape}:".encode())
        digest.update(array.tobytes())
    result = {
        "schema": 1, "run_id": uuid.uuid4().hex, "created_at": time.time(), "asset": settings.asset, "interval": settings.interval,
        "start": settings.start, "end": settings.end, "capital": settings.capital,
        "fill_delay": settings.fill_delay,
        "cpcv": {k: getattr(settings, k) for k in ("cpcv_groups", "cpcv_k")
                 if hasattr(settings, k)},
        "data_sha256": digest.hexdigest(), "bars": len(arrays["ts"]),
        "first_ts": int(arrays["ts"][0]) if len(arrays["ts"]) else None,
        "last_ts": int(arrays["ts"][-1]) if len(arrays["ts"]) else None,
        "strategy_revision": forwardtest.revision(), "execution": from_settings(settings).to_dict(),
        "entries": [{"label": e.label, "name": e.name, "params": dict(e.params)} for e in roster],
    }
    # Detach nested dictionaries from the live roster before another UI changes it.
    result = json.loads(json.dumps(result, allow_nan=False))
    result["id"] = context_id(result)
    return result


def handoff_plan(snapshot: Any, label: str, horizons: list[int], tune: bool) -> dict[str, Any]:
    from . import forwardtest
    from .simulation import Execution

    if not isinstance(snapshot, dict) or snapshot.get("schema") != 1:
        raise ValueError("Choose a versioned backtest snapshot from Signal Desk")
    if snapshot.get("id") != context_id(snapshot):
        raise ValueError("The backtest snapshot changed; stage the original result again")
    if snapshot.get("strategy_revision") != forwardtest.revision():
        raise ValueError("Strategy code changed since the backtest; rerun before preparing a trial")
    asset = snapshot.get("asset")
    if not isinstance(asset, str) or not asset.isascii() or not asset.isalnum() or not 1 <= len(asset) <= 20:
        raise ValueError("The snapshot has no valid asset")
    entries = snapshot.get("entries")
    if not isinstance(entries, list):
        raise ValueError("The snapshot has no strategy entries")
    matches = [e for e in entries if isinstance(e, dict) and e.get("label") == label]
    if len(matches) != 1 or not isinstance(matches[0].get("params"), dict):
        raise ValueError("Select one exact strategy label from the backtest")
    e = matches[0]
    member = forwardtest.member(e["name"], e["params"])
    if member["name"] != e["name"]:
        raise ValueError("This strategy wrapper cannot be handed off exactly; backtest the base strategy with explicit execution leverage first")
    execution = snapshot.get("execution")
    fields = {f.name for f in dataclasses.fields(Execution)}
    if not isinstance(execution, dict) or set(execution) != fields:
        raise ValueError("The snapshot must contain the complete execution cost scenario")
    profile = Execution(**execution)
    return {"asset": asset.upper(), "assets": [asset.upper()],
            "trials": [{"label": label, "mode": "all", "members": [member]}],
            "horizons": tuple(sorted(set(horizons))), "cost": profile.round_trip_bps,
            "code": snapshot["strategy_revision"], "tune": tune, "execution": profile.to_dict(),
            "source": {"backtest_context": snapshot["id"], "data_sha256": snapshot.get("data_sha256"),
                       "interval": snapshot.get("interval"), "start": snapshot.get("start"),
                       "end": snapshot.get("end"), "snapshot": json.loads(json.dumps(snapshot))}}
