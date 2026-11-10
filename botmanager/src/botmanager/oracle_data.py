"""Inert Oracle accepted-observation snapshots and bounded prospective pages.

No Oracle producer class is imported here. A descriptor freezes source consent,
policy, activation and assumed costs. The existing archive owner alone appends.
"""

from __future__ import annotations

import copy
import json
import math
import re
import sqlite3
import time
from pathlib import Path

from .data import MAX_BARS, _number, engine_identity
from .domain import ManagerError, fingerprint

MAX_OBSERVATIONS = MAX_BARS * 120
PAGE_SIZE = 4096
KNOWN_ARCHIVE = (
    Path.home()
    / ".local/share/solmargintrader/ecosystem-paper-v1/oracle/SOL/history.sqlite3"
)
SCOPE = {
    "source": "coinbase_recorder",
    "venue": "coinbase_exchange",
    "instrument": "SOL/USD",
    "kind": "stream_snapshot_mid",
}


def read_page(path, *, after=0, limit=PAGE_SIZE, now=None, start=None, end=None):
    """One SQLite read transaction binds policy, accepted rows and event watermark."""
    now = time.time() if now is None else now
    path = Path(path)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise ManagerError(
            "source_absent", "The selected existing Oracle archive is absent.", 3
        )
    if (
        type(after) is not int
        or after < 0
        or type(limit) is not int
        or not 1 <= limit <= MAX_OBSERVATIONS + 1
    ):
        raise ManagerError("invalid_input", "Archive page exceeds the finite bound.")
    db = None
    try:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        if (
            db.execute("PRAGMA application_id").fetchone()[0] != 0x4F52434C
            or db.execute("PRAGMA user_version").fetchone()[0] != 1
        ):
            raise ManagerError(
                "incompatible_source",
                "Oracle application/schema identity is unsupported.",
                3,
            )
        meta = {
            r["key"]: json.loads(r["body"])
            for r in db.execute(
                "SELECT * FROM metadata WHERE key IN ('scope','policy')"
            )
        }
        policy, scope = meta["policy"], meta["scope"]
        if (
            scope != SCOPE
            or type(policy["schema_version"]) is not int
            or policy["schema_version"] != 1
            or policy["instrument"] != scope["instrument"]
            or policy["bar_seconds"] != 60
            or not isinstance(policy["implementation_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", policy["implementation_sha256"])
        ):
            raise ManagerError(
                "source_mismatch",
                "Selected Oracle policy/source is incompatible with SOL/USD reference paper.",
                3,
            )
        high = db.execute("SELECT coalesce(max(sequence),0) FROM events").fetchone()[0]
        latest = db.execute(
            "SELECT observed,received FROM observations ORDER BY observed DESC LIMIT 1"
        ).fetchone()
        if latest and not 0 < latest["observed"] <= latest["received"] <= now:
            raise ManagerError(
                "invalid_observation",
                "Newest accepted source clock is invalid or in the future.",
                3,
            )
        query = """SELECT e.sequence, o.* FROM observations o JOIN events e
            ON e.event_key='observation:' || o.event_id AND e.kind='observation'
            WHERE e.sequence>? AND e.sequence<=?"""
        args = [after, high]
        if start is not None:
            query += " AND o.observed>=?"
            args.append(start)
        if end is not None:
            query += " AND o.observed<?"
            args.append(end)
        rows = db.execute(
            query + " ORDER BY e.sequence LIMIT ?", [*args, limit]
        ).fetchall()
        accepted = []
        previous = None
        for r in rows:
            o = json.loads(r["body"])
            if (
                any(o[k] != v for k, v in scope.items())
                or o["event_id"] != r["event_id"]
                or any(
                    type(o[k]) not in (int, float) or not math.isfinite(o[k])
                    for k in ("observed_at", "received_at", "price")
                )
                or not 0 < o["observed_at"] <= o["received_at"] <= now
                or o["price"] <= 0
                or o["observed_at"] != r["observed"]
                or o["received_at"] != r["received"]
                or o["price"] != r["price"]
                or previous is not None
                and o["observed_at"] <= previous
            ):
                raise ManagerError(
                    "invalid_observation",
                    "Accepted Oracle observation clocks, scope or value are invalid.",
                    3,
                )
            previous = o["observed_at"]
            accepted.append(
                {"sequence": r["sequence"], "sha256": fingerprint(o), "observation": o}
            )
        return {
            "schema_version": 1,
            "scope": scope,
            "policy": policy,
            "policy_hash": fingerprint(policy),
            "high_watermark": high,
            "observations": accepted,
            "latest_observed": latest["observed"] if latest else None,
            "latest_received": latest["received"] if latest else None,
            "read_at": now,
        }
    except ManagerError:
        raise
    except (sqlite3.Error, OSError) as exc:
        raise ManagerError(
            "source_unreachable", "Selected Oracle archive cannot be read.", 3
        ) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise ManagerError(
            "incompatible_source", "Selected Oracle metadata is invalid.", 3
        ) from exc
    finally:
        if db is not None:
            db.close()


def cost_profile():
    from backtester.core.types import CostConfig

    c = CostConfig()
    return {
        "profile": "canonical-spot-reference-v1",
        "fee_bps": c.fee_bps,
        "slippage_bps": c.slippage_bps,
        "carry_bps_per_hour": 0.0,
        "min_order_quote": 10.0,
        "provenance": "explicit_reference_assumptions_not_observed_jupiter_fees",
    }


def prepare_descriptor(
    path,
    *,
    capital_quote,
    strategy_id,
    now=None,
    mode="prospective",
    start_ts=None,
    end_ts=None,
):
    now = time.time() if now is None else now
    page = read_page(path, now=now, limit=1)
    costs = cost_profile()
    d = {
        "schema_version": 2,
        "source": "oracle_archive",
        "archive_path": str(Path(path)),
        "installation_id": "existing-ecosystem-oracle",
        "source_scope": page["scope"],
        "policy_hash": page["policy_hash"],
        "policy": page["policy"],
        "quote_currency": "USD",
        "product": "SOL/USD",
        "strategy_id": strategy_id,
        "bar_seconds": 60,
        "mode": mode,
        "capital_quote": _number(capital_quote, positive=True),
        "cost_profile": costs.pop("profile"),
        "cost_provenance": costs.pop("provenance"),
        **costs,
        "max_bars": MAX_BARS,
        "max_sample_gap_s": 5.0,
        "max_quote_age_s": 5.0,
        "max_source_age_s": 15.0,
        "reference_consent": True,
    }
    if mode == "prospective":
        d.update(
            activation_at=now,
            activation_watermark=page["high_watermark"],
            start_ts=math.ceil(now / 60) * 60,
            end_ts=None,
        )
    elif mode == "historical":
        d.update(start_ts=start_ts, end_ts=end_ts)
    else:
        raise ManagerError("invalid_input", "Unknown reference capture mode.")
    return d


def _validate(d, strategy_id, now):
    try:
        required = {
            "schema_version",
            "source",
            "archive_path",
            "installation_id",
            "source_scope",
            "policy_hash",
            "policy",
            "quote_currency",
            "product",
            "strategy_id",
            "bar_seconds",
            "mode",
            "capital_quote",
            "cost_profile",
            "cost_provenance",
            "fee_bps",
            "slippage_bps",
            "carry_bps_per_hour",
            "min_order_quote",
            "max_bars",
            "max_sample_gap_s",
            "max_quote_age_s",
            "max_source_age_s",
            "reference_consent",
            "start_ts",
            "end_ts",
        }
        if d.get("mode") == "prospective":
            required |= {"activation_at", "activation_watermark"}
        if set(d) != required:
            raise ValueError
        if (
            type(d["schema_version"]) is not int
            or d["schema_version"] != 2
            or d["source"] != "oracle_archive"
            or d["reference_consent"] is not True
            or d["source_scope"] != SCOPE
            or d["product"] != "SOL/USD"
            or d["quote_currency"] != "USD"
            or d["policy_hash"] != fingerprint(d["policy"])
            or d["strategy_id"] != strategy_id
            or d["bar_seconds"] != 60
            or type(d["start_ts"]) is not int
            or d["start_ts"] % 60
            or type(d["max_bars"]) is not int
            or not 1 <= d["max_bars"] <= MAX_BARS
        ):
            raise ValueError
        for key in (
            "fee_bps",
            "slippage_bps",
            "carry_bps_per_hour",
            "capital_quote",
            "min_order_quote",
        ):
            _number(d[key], positive=key in ("capital_quote", "min_order_quote"))
        if d["fee_bps"] >= 10000 or d["slippage_bps"] >= 10000:
            raise ValueError
        for key in ("max_sample_gap_s", "max_quote_age_s"):
            if not 0 < _number(d[key], positive=True) <= 5:
                raise ValueError
        if not 0 < _number(d["max_source_age_s"], positive=True) <= 15:
            raise ValueError
        if d["mode"] == "prospective":
            if (
                not 0 < d["activation_at"] <= now
                or d["start_ts"] != math.ceil(d["activation_at"] / 60) * 60
                or type(d["activation_watermark"]) is not int
                or d["activation_watermark"] < 0
                or d["end_ts"] is not None
            ):
                raise ValueError
        elif d["mode"] == "historical":
            if (
                type(d["end_ts"]) is not int
                or d["end_ts"] % 60
                or not d["start_ts"] < d["end_ts"] <= now
                or (d["end_ts"] - d["start_ts"]) // 60 > d["max_bars"]
            ):
                raise ValueError
        else:
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise ManagerError(
            "input_unavailable",
            "Oracle descriptor identity, costs or bounds are invalid.",
            3,
        ) from exc


def _bars(observations, d, end):
    selected = [
        x["observation"]
        for x in observations
        if d["start_ts"] <= x["observation"]["observed_at"] < end
    ]
    if end <= d["start_ts"]:
        return []
    bars, previous = [], None
    for o in selected:
        t, price = o["observed_at"], o["price"]
        age = o["received_at"] - t
        if (
            age > d["max_quote_age_s"]
            or previous is not None
            and (t <= previous or t - previous > d["max_sample_gap_s"])
        ):
            raise ManagerError(
                "source_gap", "Reference samples have a gap or delayed clock.", 3
            )
        previous = t
        ts = int(t) // 60 * 60
        if not bars or bars[-1]["ts"] != ts:
            bars.append(
                {
                    "ts": ts,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "first_arrival": t,
                    "last_arrival": t,
                    "max_quote_age_s": age,
                }
            )
        else:
            b = bars[-1]
            b.update(
                high=max(b["high"], price),
                low=min(b["low"], price),
                close=price,
                last_arrival=t,
                max_quote_age_s=max(age, b["max_quote_age_s"]),
            )
    expected = (end - d["start_ts"]) // 60
    if len(bars) != expected or any(
        b["ts"] != d["start_ts"] + i * 60
        or b["first_arrival"] - b["ts"] > d["max_sample_gap_s"]
        or b["ts"] + 60 - b["last_arrival"] > d["max_sample_gap_s"]
        for i, b in enumerate(bars)
    ):
        raise ManagerError(
            "source_gap", "Completed bins lack required observed edges or cadence.", 3
        )
    return bars


def _seal(data):
    data["snapshot_hash"] = fingerprint(
        {k: v for k, v in data.items() if k != "snapshot_hash"}
    )
    return data


def capture(descriptor, *, strategy_id="grid", now=None):
    now = time.time() if now is None else now
    d = copy.deepcopy(descriptor)
    _validate(d, strategy_id, now)
    page = read_page(
        d["archive_path"],
        now=now,
        after=d.get("activation_watermark", 0),
        start=d["start_ts"],
        end=d["end_ts"],
        limit=MAX_OBSERVATIONS + 1 if d["mode"] == "historical" else 1,
    )
    if page["policy_hash"] != d["policy_hash"]:
        raise ManagerError(
            "source_mismatch", "Oracle policy changed after source selection.", 3
        )
    identity = {
        "schema_version": 2,
        "kind": "reference_paper",
        "venue": "coinbase_proxy",
        "source": "oracle_archive",
        "installation_id": d["installation_id"],
        "product": d["product"],
        "quote_currency": "USD",
        "base_currency": "SOL",
        "bar_seconds": 60,
        "execution_model": {
            "grid": "sampled_mid_ohlc_resting_ladder",
            "dca": "sampled_mid_safety_orders",
            "trend": "sampled_mid_next_open",
            "momentum": "sampled_mid_next_open",
        }[strategy_id],
        "quote_provenance": "oracle_accepted_sampled_mid_not_executable",
        "quote_age_max_seconds": d["max_quote_age_s"],
        "start_ts": d["start_ts"],
        "end_ts": d["end_ts"] or d["start_ts"],
        "volume": None,
        "volume_reason": "not_observed",
        "source_scope": page["scope"],
        "policy": page["policy"],
        "policy_hash": page["policy_hash"],
        "sources": [
            {
                "path": d["archive_path"],
                "event_high_watermark": d.get(
                    "activation_watermark", page["high_watermark"]
                ),
            }
        ],
        "costs": {
            k: d[k]
            for k in (
                "fee_bps",
                "slippage_bps",
                "carry_bps_per_hour",
                "min_order_quote",
            )
        },
        "cost_provenance": d["cost_provenance"],
        "capital_quote": d["capital_quote"],
        "engine_identity": engine_identity(strategy_id),
        "venue_compatibility_verified": False,
        "live_eligible": False,
        "arrival_policy": "post_activation_completed_bins"
        if d["mode"] == "prospective"
        else "immutable_closed_interval",
        "transformation": "accepted_observed_clock_60s_mid_OHLC_no_interpolation",
    }
    data = {"schema_version": 2, "descriptor": d, "identity": identity, "bars": []}
    if d["mode"] == "historical":
        if len(page["observations"]) > MAX_OBSERVATIONS:
            raise ManagerError(
                "resource_limit",
                "Closed capture exceeds accepted observation bound.",
                3,
            )
        data["observations"] = page["observations"]
        data["bars"] = _bars(page["observations"], d, d["end_ts"])
    else:
        data["prospective"] = {
            "cursor": d["activation_watermark"],
            "high_watermark": d["activation_watermark"],
            "observations": [],
            "health": "waiting_for_observations",
            "latest_observed": None,
            "latest_received": None,
            "last_poll_at": None,
            "delivery": "waiting",
            "evaluated_bars": 0,
            "evaluation_ranges": [],
        }
    _seal(data)
    if d["mode"] == "prospective":
        data["origin_hash"] = data["snapshot_hash"]
        _seal(data)
    return data


def advance(data, *, now=None):
    """Pure transition over a read-only page; caller atomically commits input+book."""
    now = time.time() if now is None else now
    result = copy.deepcopy(data)
    state = result["prospective"]
    d = result["descriptor"]
    state["last_poll_at"] = now
    try:
        if (
            len(result["bars"]) >= d["max_bars"]
            or len(state["observations"]) >= MAX_OBSERVATIONS
        ):
            raise ManagerError(
                "resource_limit", "Finite prospective replay capacity reached.", 3
            )
        page = read_page(d["archive_path"], after=state["cursor"], now=now)
        if (
            page["policy_hash"] != d["policy_hash"]
            or page["high_watermark"] < state["cursor"]
        ):
            raise ManagerError(
                "source_mismatch",
                "Selected archive changed policy or lost its durable cursor.",
                3,
            )
        state.update(
            high_watermark=page["high_watermark"],
            latest_observed=page["latest_observed"],
            latest_received=page["latest_received"],
        )
        if page["latest_observed"] is None:
            raise ManagerError(
                "waiting_for_observations", "Producer has no accepted observations.", 3
            )
        if (
            not 0 <= now - page["latest_observed"] <= d["max_source_age_s"]
            or not 0 <= now - page["latest_received"] <= d["max_source_age_s"]
        ):
            raise ManagerError(
                "source_stale", "Source is stale; new reference entries are held.", 3
            )
        selected = [
            x
            for x in page["observations"]
            if x["observation"]["observed_at"] >= d["activation_at"]
            and x["observation"]["received_at"] >= d["activation_at"]
        ]
        combined = state["observations"] + selected
        if len(combined) > MAX_OBSERVATIONS:
            raise ManagerError(
                "resource_limit", "Finite prospective observation capacity reached.", 3
            )
        # Do not close a bin before the page reaches its end. A large backlog
        # must not turn a partial page into an apparent coverage failure.
        through = (
            selected[-1]["observation"]["observed_at"]
            if selected
            else (
                combined[-1]["observation"]["observed_at"]
                if combined
                else d["start_ts"]
            )
        )
        end = min(
            int(now) // 60 * 60,
            int(through) // 60 * 60,
            d["start_ts"] + d["max_bars"] * 60,
        )
        bars = _bars(combined, d, end)
        if bars[: len(data["bars"])] != data["bars"]:
            raise ManagerError("source_mismatch", "A closed reference bar changed.", 3)
        state["observations"] = combined
        state["cursor"] = (
            page["observations"][-1]["sequence"]
            if page["observations"]
            else page["high_watermark"]
        )
        state["delivery"] = (
            "delayed_replay"
            if now - through > 60
            or (selected and now - selected[0]["observation"]["received_at"] > 90)
            else "prospective_reference"
        )
        state["health"] = (
            "resource_limit"
            if len(bars) >= d["max_bars"]
            else "available"
            if len(bars) > len(data["bars"])
            else "waiting_for_completed_bin"
        )
        if len(bars) > len(data["bars"]):
            state["evaluation_ranges"].append(
                {
                    "start_bar": len(data["bars"]),
                    "end_bar": len(bars),
                    "delivery": state["delivery"],
                    "evaluated_at": now,
                    "source_high_watermark": page["high_watermark"],
                }
            )
        state["evaluated_bars"] = len(bars)
        result["bars"] = bars
    except ManagerError as exc:
        state["health"] = exc.code
    return _seal(result)
