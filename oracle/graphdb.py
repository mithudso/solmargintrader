"""Append-only per-evaluation graph snapshots in the Oracle archive."""

from __future__ import annotations

import itertools
import json
import math
import sqlite3

from .feeds import validate_instrument
from .store import canonical

GRAPH_SCHEMA_VERSION = 1
DEFAULT_LIMIT = 240
MAX_LIMIT = 500


def market_shape(bars: list[dict]) -> dict:
    """Summarize only the completed bars supplied to this evaluation."""
    rows = bars[-21:]
    if not rows:
        return {
            "lookback_bars": 0,
            "net_return_bps": None,
            "range_bps": None,
            "path_efficiency": None,
            "realized_volatility_bps": None,
        }

    closes = [row["close"] for row in rows]
    returns = [math.log(right / left) for left, right in itertools.pairwise(closes)]
    net = math.log(closes[-1] / closes[0]) if len(closes) > 1 else None
    path = sum(abs(value) for value in returns)
    high = max(row["high"] for row in rows)
    low = min(row["low"] for row in rows)
    return {
        "lookback_bars": len(rows),
        "lookback_start": rows[0]["ts"],
        "lookback_end": rows[-1]["ts"],
        "net_return_bps": net * 10_000 if net is not None else None,
        "range_bps": (high - low) / closes[0] * 10_000,
        "path_efficiency": abs(net) / path if net is not None and path else None,
        "realized_volatility_bps": math.sqrt(sum(value * value for value in returns))
        * 10_000,
    }


def record_tick(
    db: sqlite3.Connection, tick: dict, predictions: list[dict]
) -> bool:
    """Atomically append one graph tick and its complete strategy roster."""
    if type(predictions) is not list or len(predictions) != 14:
        raise ValueError("invalid_graphdb_strategy_roster")
    instrument = validate_instrument(tick.get("instrument"))
    if (
        not isinstance(tick.get("tick_id"), str)
        or not tick["tick_id"]
        or type(tick.get("bar_index")) is not int
        or tick["bar_index"] < 0
        or type(tick.get("chart_time")) is not int
        or tick["chart_time"] < 0
        or any(
            type(tick.get(key)) not in (int, float)
            or not math.isfinite(tick[key])
            for key in ("observed_at", "received_at", "price")
        )
        or tick["price"] <= 0
        or not isinstance(tick.get("policy_hash"), str)
        or not isinstance(tick.get("observation_id"), str)
    ):
        raise ValueError("invalid_graphdb_tick")

    body = (
        instrument,
        tick["policy_hash"],
        tick["bar_index"],
        tick["chart_time"],
        tick["observed_at"],
        tick["received_at"],
        tick["price"],
        tick["observation_id"],
        canonical(tick["market_shape"]),
        canonical(tick["aggregate"]),
    )
    existing = db.execute(
        "SELECT instrument,policy_hash,bar_index,chart_time,observed_at,received_at,price,observation_id,market_shape,aggregate FROM graphdb_ticks WHERE tick_id=?",
        (tick["tick_id"],),
    ).fetchone()
    if existing is not None:
        if tuple(existing) != body:
            raise ValueError("graphdb_tick_conflict")
        return False

    db.execute(
        "INSERT INTO graphdb_ticks VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (tick["tick_id"], *body),
    )
    seen = set()
    for row in predictions:
        strategy_id, version = row.get("strategy_id"), row.get("version")
        direction = row.get("direction")
        if (
            not isinstance(strategy_id, str)
            or not strategy_id
            or strategy_id in seen
            or not isinstance(version, str)
            or (direction is not None and (type(direction) is not int or direction not in (-1, 0, 1)))
            or type(row.get("hits")) is not int
            or type(row.get("resolved")) is not int
            or not 0 <= row["hits"] <= row["resolved"]
            or type(row.get("vote_eligible")) is not bool
        ):
            raise ValueError("invalid_graphdb_prediction")
        seen.add(strategy_id)
        db.execute(
            "INSERT INTO graphdb_predictions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                tick["tick_id"],
                strategy_id,
                version,
                row.get("forecast_id"),
                direction,
                row.get("issued_at"),
                row.get("expires_at"),
                row["hits"],
                row["resolved"],
                row.get("accuracy_percent"),
                row.get("vote_weight"),
                int(row["vote_eligible"]),
                row.get("reason"),
            ),
        )
    return True


def history(db: sqlite3.Connection, instrument: str, limit: int = DEFAULT_LIMIT) -> dict:
    instrument = validate_instrument(instrument)
    if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
        raise ValueError("invalid_graphdb_history_limit")
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('graphdb_ticks','graphdb_predictions')"
        )
    }
    if tables != {"graphdb_ticks", "graphdb_predictions"}:
        return {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "graph_history_not_recorded",
            "instrument": instrument,
            "ticks": [],
        }
    rows = db.execute(
        "SELECT tick_id,bar_index,chart_time,observed_at,received_at,price,observation_id,market_shape,aggregate FROM graphdb_ticks WHERE instrument=? ORDER BY bar_index DESC LIMIT ?",
        (instrument, limit),
    ).fetchall()
    result = []
    for row in reversed(rows):
        strategies = db.execute(
            "SELECT strategy_id,strategy_version,forecast_id,direction,issued_at,expires_at,hits,resolved,accuracy_percent,vote_weight,vote_eligible,reason FROM graphdb_predictions WHERE tick_id=? ORDER BY strategy_id",
            (row[0],),
        ).fetchall()
        if len(strategies) != 14:
            raise ValueError("graphdb_strategy_roster_incomplete")
        result.append(
            {
                "tick_id": row[0],
                "bar_index": row[1],
                "time": row[2],
                "observed_at": row[3],
                "received_at": row[4],
                "price": row[5],
                "observation_id": row[6],
                "market_shape": json.loads(row[7]),
                "aggregate": json.loads(row[8]),
                "strategies": [
                    {
                        "strategy_id": value[0],
                        "version": value[1],
                        "forecast_id": value[2],
                        "direction": value[3],
                        "issued_at": value[4],
                        "expires_at": value[5],
                        "hits": value[6],
                        "resolved": value[7],
                        "accuracy_percent": value[8],
                        "vote_weight": value[9],
                        "vote_eligible": bool(value[10]),
                        "reason": value[11],
                    }
                    for value in strategies
                ],
            }
        )
    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "status": "available" if result else "unavailable",
        "reason": None if result else "graph_history_empty",
        "instrument": instrument,
        "count": len(result),
        "limit": limit,
        "ticks": result,
        "aggregate_semantics": "signed_weighted_vote_balance_not_probability",
    }
