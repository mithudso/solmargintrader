"""Fixed-day, causal one-minute observations of ten-minute bearish setups.

This descriptive study writes nothing, fetches nothing and places no orders.
Signal-minute lows never enter subsequent excursions. Inputs remain immutable.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

import numpy as np

NS = 10**9
MINUTE = 60
SETUP = 600
HORIZONS = (5, 10, 20)
POLICIES = {"intrabar": (1, 9), "midpoint": (5, 9), "close_confirmation": (10, 10)}
TAPE_SHA = "21db6ff5a1b6fdd12f887ef506f654ff634af3c355ca898d2f0838de09fd6f4c"
WAL_SHA = "eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31"
REFERENCE_SHA = "83c4b4b15f990a8d7b7e4804f6c1d2ea15d3f784c2d500033cc4c94fc33734df"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def minute_bars(times, prices, start_ns, end_ns, gaps):
    """Retain empty buckets and independently mark conservative gap exclusions."""
    width = MINUTE * NS
    stamps = np.arange(
        ((start_ns + width - 1) // width) * width,
        (end_ns // width) * width,
        width,
        dtype=np.int64,
    )
    lo, hi = np.searchsorted(times, stamps), np.searchsorted(times, stamps + width)
    present = hi > lo
    safe = present.copy()
    for a, b, _kind in gaps:
        hit = (
            (stamps <= a) & (a < stamps + width)
            if a == b
            else (stamps < b) & (stamps + width > a)
        )
        safe[hit] = False
    bars = []
    for i, stamp in enumerate(stamps):
        p = prices[lo[i] : hi[i]]
        bars.append(
            {
                "ts": int(stamp // NS),
                "open": float(p[0]) if len(p) else None,
                "high": float(p.max()) if len(p) else None,
                "low": float(p.min()) if len(p) else None,
                "close": float(p[-1]) if len(p) else None,
                "present": bool(present[i]),
                "gap_safe": bool(safe[i]),
            }
        )
    return bars


def events_for(bars, mask, policy):
    """Only prior closed bars and the known current prefix select an event."""
    table = {b["ts"]: b for b in bars}
    if not table:
        return [], {"complete_current_windows_considered": 0}
    begin = ((min(table) + SETUP - 1) // SETUP) * SETUP
    stop = max(table) + MINUTE
    first, last = POLICIES[policy]
    events, counts = (
        [],
        {
            "complete_current_windows_considered": 0,
            "prior_history_unavailable": 0,
            "previous_not_up": 0,
            "current_prefix_unavailable": 0,
            "no_trigger": 0,
            "capture_edge_current_window": 0,
        },
    )

    def valid(stamps):
        return all(t in table and table[t][mask] for t in stamps)

    for current in range(begin, stop, SETUP):
        if current + last * MINUTE > stop:
            counts["capture_edge_current_window"] += 1
            # A known early trigger remains eligible at a capture edge. Future
            # availability censors its outcome, never its already known signal.
        counts["complete_current_windows_considered"] += 1
        if not valid(range(current - 2 * SETUP, current, MINUTE)):
            counts["prior_history_unavailable"] += 1
            continue
        previous_open = table[current - SETUP]["open"]
        previous_close = table[current - MINUTE]["close"]
        if previous_close <= previous_open:
            counts["previous_not_up"] += 1
            continue
        older_up = (
            table[current - SETUP - MINUTE]["close"]
            > table[current - 2 * SETUP]["open"]
        )
        cohort = "after_two_up" if older_up else "after_one_up"
        found = False
        for elapsed in range(1, last + 1):
            stamp = current + (elapsed - 1) * MINUTE
            if not valid([stamp]):
                counts["current_prefix_unavailable"] += 1
                found = True
                break
            if elapsed < first:
                continue
            price, opening = table[stamp]["close"], table[current]["open"]
            if price < opening:
                signal = stamp + MINUTE
                events.append(
                    {
                        "id": f"{mask}:{policy}:{cohort}:{current}",
                        "mask": mask,
                        "policy": policy,
                        "cohort": cohort,
                        "current_start": current,
                        "signal_at": signal,
                        "elapsed_minutes": elapsed,
                        "true_open": opening,
                        "signal_price": price,
                        "previous_open": previous_open,
                        "previous_close": previous_close,
                    }
                )
                found = True
                break
        if not found:
            counts["no_trigger"] += 1
    counts["events"] = len(events)
    return events, counts


def event_outcome(event, table, horizon):
    """Future bars start at the signal timestamp, strictly after its close."""
    signal = event["signal_at"]
    stamps = list(range(signal, signal + horizon * MINUTE, MINUTE))
    if any(t not in table for t in stamps):
        return {"status": "capture_censored"}
    if not all(table[t][event["mask"]] for t in stamps):
        return {"status": "missing_or_gap_censored"}
    future = [table[t] for t in stamps]
    low, high, close = (
        min(b["low"] for b in future),
        max(b["high"] for b in future),
        future[-1]["close"],
    )
    refs = {}
    for name, entry in (
        ("signal_close", event["signal_price"]),
        ("next_minute_open", future[0]["open"]),
    ):
        down, adverse, endpoint = (
            max(0.0, entry - low),
            max(0.0, high - entry),
            entry - close,
        )
        refs[name] = {
            "reference": entry,
            "down_usd": down,
            "down_pct": 100 * down / entry,
            "adverse_usd": adverse,
            "adverse_pct": 100 * adverse / entry,
            "endpoint_decline_usd": endpoint,
            "endpoint_decline_pct": 100 * endpoint / entry,
            "continued_down": close < entry,
            "flat_endpoint": close == entry,
        }
    return {
        "status": "observed",
        "horizon_minutes": horizon,
        "future_low": low,
        "future_high": high,
        "future_close": close,
        "references": refs,
    }


def aggregate(events, table, horizon, nonoverlap=False):
    selected, excluded, busy_until = [], 0, -1
    for event in events:
        if nonoverlap and event["signal_at"] < busy_until:
            excluded += 1
            continue
        # Reserve by time before examining future data, even for censored outcomes.
        busy_until = event["signal_at"] + horizon * MINUTE
        selected.append((event, event_outcome(event, table, horizon)))
    observed = [(e, o) for e, o in selected if o["status"] == "observed"]
    summary = {
        "horizon_minutes": horizon,
        "overlap_policy": "nonoverlap" if nonoverlap else "all",
        "candidate_events": len(events),
        "overlap_excluded": excluded,
        "selected_events": len(selected),
        "observed_events": len(observed),
        "capture_censored": sum(o["status"] == "capture_censored" for _, o in selected),
        "missing_or_gap_censored": sum(
            o["status"] == "missing_or_gap_censored" for _, o in selected
        ),
        "references": {},
    }
    for ref in ("signal_close", "next_minute_open"):
        values = [o["references"][ref] for _, o in observed]
        stats = {}
        for key in (
            "down_usd",
            "down_pct",
            "adverse_usd",
            "adverse_pct",
            "endpoint_decline_usd",
            "endpoint_decline_pct",
        ):
            series = [v[key] for v in values]
            stats[key] = {
                "mean": float(np.mean(series)) if series else None,
                "median": float(np.median(series)) if series else None,
                "maximum": max(series) if series else None,
                "minimum": min(series) if series else None,
            }
        n = len(values)
        stats.update(
            n=n,
            continued_down=sum(v["continued_down"] for v in values),
            flat_endpoint=sum(v["flat_endpoint"] for v in values),
            any_further_down=sum(v["down_usd"] > 0 for v in values),
            continuation_rate=sum(v["continued_down"] for v in values) / n
            if n
            else None,
        )
        stats["max_down_usd_event"] = (
            observed[int(np.argmax([v["down_usd"] for v in values]))][0]["id"]
            if n
            else None
        )
        stats["max_down_pct_event"] = (
            observed[int(np.argmax([v["down_pct"] for v in values]))][0]["id"]
            if n
            else None
        )
        summary["references"][ref] = stats
    return summary


def analyze(bars):
    table = {b["ts"]: b for b in bars}
    result = {"schema": 1, "selection_counts": [], "events": [], "summaries": []}
    for mask in ("gap_safe", "present"):
        for policy in POLICIES:
            events, counts = events_for(bars, mask, policy)
            result["selection_counts"].append(
                {"mask": mask, "policy": policy, **counts}
            )
            result["events"].extend(
                {
                    **e,
                    "outcomes": {str(h): event_outcome(e, table, h) for h in HORIZONS},
                }
                for e in events
            )
            for cohort in ("after_one_up", "after_two_up"):
                selected = [e for e in events if e["cohort"] == cohort]
                for horizon in HORIZONS:
                    for nonoverlap in (False, True):
                        result["summaries"].append(
                            {
                                "mask": mask,
                                "policy": policy,
                                "cohort": cohort,
                                **aggregate(selected, table, horizon, nonoverlap),
                            }
                        )
    return result


def study(capture_dir, wal):
    capture_dir = Path(capture_dir)
    metadata = (capture_dir / "capture.json").read_bytes()
    info = json.loads(metadata)
    reference = (
        Path(__file__).resolve().parents[1] / "zec-two-bar-reversal-20261114/results.json"
    )
    if sha(reference) != REFERENCE_SHA:
        raise ValueError("frozen_reference_hash_mismatch")
    original = json.loads(reference.read_bytes())["input"]
    if hashlib.sha256(metadata).hexdigest() != original["capture_metadata_sha256"]:
        raise ValueError("capture_metadata_hash_mismatch")
    if (
        sha(capture_dir / "tape.npz") != info["tape_sha256"]
        or info["tape_sha256"] != TAPE_SHA
    ):
        raise ValueError("tape_hash_mismatch")
    if sha(wal) != info["wal_sha256"] or info["wal_sha256"] != WAL_SHA:
        raise ValueError("wal_hash_mismatch")
    with np.load(capture_dir / "tape.npz", allow_pickle=False) as a:
        times, prices = a["trade_ns"], a["price"]
    if (
        len(times) != 134746
        or len(times) != len(prices)
        or not np.all(times[1:] >= times[:-1])
        or not np.all(np.isfinite(prices))
        or not np.all(prices > 0)
        or times[0] < info["start_ns"]
        or times[-1] >= info["end_ns"]
    ):
        raise ValueError("invalid_fixed_tape")
    bars = minute_bars(times, prices, info["start_ns"], info["end_ns"], info["gaps"])
    result = analyze(bars)
    result["input"] = {
        **original,
        "clock": "accepted receipt-time trades; complete UTC1m buckets",
        "minute_buckets": len(bars),
        "observed_minutes": sum(b["present"] for b in bars),
        "gap_safe_minutes": sum(b["gap_safe"] for b in bars),
        "gap_candidates": len(info["gaps"]),
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--wal", type=Path, required=True)
    parser.add_argument(
        "--packed",
        action="store_true",
        help="Lossless compact transport plus readable primary rows",
    )
    args = parser.parse_args(argv)
    result = study(args.capture_dir, args.wal)
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if args.packed:
        result = {
            "encoding": "zlib+base64",
            "decoded_utf8_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "decoded_utf8_bytes": len(raw.encode()),
            "body": base64.b64encode(zlib.compress(raw.encode(), 9)).decode(),
            "input": result["input"],
            "primary": [
                r
                for r in result["summaries"]
                if r["mask"] == "gap_safe"
                and r["policy"] == "intrabar"
                and r["overlap_policy"] == "all"
            ],
        }
        raw = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    print(raw)


if __name__ == "__main__":
    main()
