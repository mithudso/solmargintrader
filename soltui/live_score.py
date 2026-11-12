"""Read-only forward-prediction agreement for live displays, never an order signal.

Keep this out of forwardtest.py: that file's hash partitions trainer evidence.
The browser adapter uses the same contract and tests against the same vectors.
"""
from __future__ import annotations

import math
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

HORIZONS = (1, 5, 10, 30)
DIRECTIONS = {"UP": 1, "DOWN": -1, "FLAT": 0}
METHOD = "Equal strategy weights; mean of current horizon votes (UP +1, FLAT 0, DOWN -1), scaled to -100..100. Directional agreement, not a probability."


def _finite(value: Any) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def aggregate_predictions(rows: list[dict[str, Any]], *, now: float | None = None,
                          min_accuracy: float = 60.0, min_resolved: int = 20) -> dict[str, Any]:
    now = time.time() if now is None else now
    valid_policy = (_finite(now) and _finite(min_accuracy) and 0 <= min_accuracy <= 100 and _finite(min_resolved)
                    and min_resolved >= 1 and int(min_resolved) == min_resolved)
    strategies = []
    votes = 0
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = row.get("label")
        if not isinstance(label, str) or not label or label in seen:
            continue
        seen.add(label)
        if (not valid_policy or not _finite(row.get("accuracy")) or not min_accuracy <= row["accuracy"] <= 100
                or not _finite(row.get("resolved")) or row["resolved"] < min_resolved
                or int(row["resolved"]) != row["resolved"]):
            continue
        directions = []
        for horizon in HORIZONS:
            raw = row.get(f"pred_{horizon}m")
            direction = DIRECTIONS.get(raw) if isinstance(raw, str) else None
            accuracy, resolved = row.get(f"acc_{horizon}m"), row.get(f"resolved_{horizon}m")
            if (not _finite(accuracy) or not min_accuracy <= accuracy <= 100 or not _finite(resolved)
                    or resolved < min_resolved or int(resolved) != resolved):
                continue
            issued, expires = row.get(f"issued_{horizon}m"), row.get(f"expires_{horizon}m")
            if direction is None or not all(_finite(v) for v in (issued, expires)):
                continue
            if not issued <= now < expires or expires <= issued:
                continue
            directions.append(direction)
        if directions:
            strategies.append(sum(directions) / len(directions))
            votes += len(directions)
    # Round once before choosing a label so the displayed number and label agree.
    score = math.floor(1000 * sum(strategies) / len(strategies) + 0.5) / 10 if strategies else None
    label = ("Strong Buy" if score is not None and score >= 60 else
             "Buy" if score is not None and score >= 20 else
             "Strong Sell" if score is not None and score <= -60 else
             "Sell" if score is not None and score <= -20 else "Flat")
    return {"score": score, "label": label,
            "color": "green" if label in {"Strong Buy", "Buy"} else "red" if label in {"Strong Sell", "Sell"} else "gray",
            "available": bool(strategies), "strategies": len(strategies), "votes": votes,
            "method": METHOD, "min_accuracy": min_accuracy, "min_resolved": min_resolved,
            "reason": "" if strategies else "No current predictions meet the voting floor"}


def prediction_snapshot(asset: str, *, limit: int = 50, now: float | None = None,
                        db_path: Path | None = None, min_accuracy: float = 60.0,
                        min_resolved: int = 20) -> dict[str, Any]:
    from . import config, forwardtest

    rows = forwardtest.top_forward_predictions(asset, limit=limit, db_path=db_path)
    path = db_path or config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
    latest = {}
    if rows and path.exists():
        # Direction and expiry come from the SAME latest call. MAX(direction)
        # across old trial revisions can report an old UP after a newer DOWN.
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            current = db.execute("""
                WITH evidence AS (
                    SELECT calls.trial,count(calls.outcome) AS resolved,
                           sum(calls.outcome=calls.prediction) AS hits
                    FROM call calls JOIN trial trials ON calls.trial=trials.id
                    WHERE trials.asset=? GROUP BY calls.trial
                )
                SELECT t.label,t.minutes,c.prediction,c.issued,c.finish,
                       coalesce(e.resolved,0),coalesce(e.hits,0)
                FROM trial t JOIN call c ON c.trial=t.id
                LEFT JOIN evidence e ON e.trial=t.id
                WHERE t.asset=? AND c.bar=(SELECT max(last.bar) FROM call last WHERE last.trial=t.id)
                ORDER BY c.issued DESC,c.bar DESC,t.id DESC
            """, (asset, asset))
            for label, minutes, direction, issued, expires, resolved, hits in current:
                latest.setdefault((label, minutes), (direction, issued, expires, resolved, hits))
    for row in rows:
        total_resolved = total_hits = 0
        for h in HORIZONS:
            direction, issued, expires, resolved, hits = latest.get((row["label"], h), (None, None, None, 0, 0))
            # Quality must belong to this latest trial too: an old winning
            # revision cannot qualify a new weak or insufficiently tested one.
            row[f"resolved_{h}m"] = resolved
            row[f"acc_{h}m"] = round(100 * hits / resolved, 1) if resolved else None
            total_resolved += resolved
            total_hits += hits
            row[f"pred_{h}m"] = {1: "UP", -1: "DOWN", 0: "FLAT"}.get(direction, "-")
            row[f"issued_{h}m"] = issued
            row[f"expires_{h}m"] = expires
        row["resolved"] = total_resolved
        row["hits"] = total_hits
        row["accuracy"] = round(100 * total_hits / total_resolved, 1) if total_resolved else 0.0
    return {"asset": asset, "rows": rows, "aggregate": aggregate_predictions(rows, now=now, min_accuracy=min_accuracy, min_resolved=min_resolved),
            "voting": {"min_accuracy": min_accuracy, "min_resolved": min_resolved}}


def tick_window(history: list[tuple[float, float]], scores: dict[float, float | None], width: int,
                slot: int = 8) -> dict[str, Any]:
    """The price bars and score labels share fixed slots, anchored at the right."""
    width = max(1, width)
    slot = max(1, min(slot, width))
    visible = history[-max(1, width // slot):]
    return {"points": visible, "scores": [scores.get(t) for t, _ in visible],
            "slot": slot, "padding": width - len(visible) * slot}
