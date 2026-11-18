"""Build frozen-cohort oracle minute acquisition plan and paper replay.

All input transports must be archived and hash-verified before results publish.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from math import inf, nextafter
from pathlib import Path

from oracle_leverage.exit50 import (
    PAPER_MARGIN,
    PAPER_NOTIONAL,
    prepare_signals,
    quote_position,
    signal_at,
)
from oracle_leverage.mtf_forward import FEEDS
from research.reversal_history import read_archive
from research.reversal_shapes import boundaries


def price_int(value):
    x = Decimal(str(value)) * 10**12
    if not x.is_finite() or x <= 0 or x != x.to_integral_value():
        raise ValueError("invalid_exact_oracle_price")
    return int(x)


def slot_data(root, asset, slot):
    path = Path(root) / f"{asset}-{slot}.json.zlib"
    meta = Path(root) / f"{asset}-{slot}.meta.json"
    if not path.exists() or not meta.exists():
        return None
    metadata = json.loads(meta.read_text())
    raw = zlib.decompress(path.read_bytes())
    if metadata.get("sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("oracle_body_hash_mismatch")
    conflicts = set(metadata.get("price_conflict_timestamps", []))
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return []
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        return []
    points = {}
    for row in value["data"]:
        if not isinstance(row, dict):
            continue
        stamp = row.get("publish_time")
        if (
            type(stamp) is not int
            or stamp % 200_000
            or not (slot - 60) * 1_000_000 <= stamp <= (slot + 60) * 1_000_000
        ):
            continue
        if stamp in conflicts:
            points[stamp] = None
            continue
        if stamp in points:
            points[stamp] = None
            continue
        update = row.get("feed_update_timestamp")
        price = row.get("price")
        exponent = row.get("exponent")
        if (
            type(row.get("price_feed_id")) is not int
            or row["price_feed_id"] != FEEDS[asset]
            or type(update) is not int
            or not 0 <= stamp - update <= 1_000_000
            or type(price) is not int
            or not 0 < price <= 2**53 - 1
            or type(exponent) is not int
            or not -12 <= exponent <= 0
        ):
            points[stamp] = None
            continue
        exact = Decimal(price) * (Decimal(10) ** exponent)
        points[stamp] = {"publish_time_us": stamp, "price": str(exact)}
    return [point for _, point in sorted(points.items()) if point is not None]


def study_candidates(asset, root, bundle):
    source = read_archive(
        f"/Users/mitch/.local/state/reversal-leverage-2289/transport/{asset}-oracle-source.json"
    )
    prepared = prepare_signals(source["rows"])
    cuts = boundaries()
    out = []
    for t in range((cuts[0] // 600 + 1) * 600, cuts[-1] - 610 + 1, 600):
        for family, at in (("near_end", t - 60), ("confirmed_uu", t)):
            signal = signal_at(prepared, at, family, bundle["models"][asset][family])
            if not signal["eligible"]:
                continue
            cap = t + 600
            split = next(
                (
                    name
                    for name, left, right in zip(
                        ("train", "validation", "test"), cuts, cuts[1:]
                    )
                    if left <= at and cap + 10 <= right
                ),
                None,
            )
            if split is None:
                continue
            data = slot_data(root, asset, t)
            price = None
            if data:
                item = next(
                    (
                        p
                        for p in data
                        if p["publish_time_us"] == (at * 1_000_000 + 200_000)
                    ),
                    None,
                )
                if item:
                    price = price_int(item["price"])
            out.append(
                {
                    "id": f"{asset}:{family}:{at}",
                    "asset": asset,
                    "family": family,
                    "decision_s": at,
                    "cap_s": cap,
                    "split": split,
                    "entry_price": price,
                    "signal": signal,
                }
            )
    return prepared, out


def acquisition_slots(asset, prepared, candidates):
    """Conservative possible-boundary and timed-exit windows, never a result."""
    slots = set()
    missing_entry = 0
    for c in candidates:
        entry = c["entry_price"]
        if entry is None:
            missing_entry += 1
            continue
        start = c["decision_s"] // 60 * 60
        cap = c["cap_s"]
        minutes = set()
        for stamp in range(start, cap + 61, 60):
            bar = prepared["rows"].get(stamp)
            if bar is None:
                continue
            high = int(
                (
                    Decimal.from_float(nextafter(float(bar[2]), inf)) * 10**12
                ).to_integral_value(rounding=ROUND_CEILING)
            )
            low = int(
                (
                    Decimal.from_float(nextafter(float(bar[3]), -inf)) * 10**12
                ).to_integral_value(rounding=ROUND_FLOOR)
            )
            qhigh = quote_position(PAPER_MARGIN, PAPER_NOTIONAL, entry, high, "SHORT")
            qlow = quote_position(PAPER_MARGIN, PAPER_NOTIONAL, entry, low, "SHORT")
            flags = prepared["features"].get(stamp, {})
            if (
                qhigh["liquidatable"]
                or qlow["target_50"]
                or flags.get("momentum_exit")
                or stamp == cap
            ):
                minutes.add(stamp)
                minutes.add(stamp + 60)
        for minute in minutes:
            slot = ((minute + 119) // 120) * 120
            slots.add((asset, slot))
    return sorted(slots), missing_entry


def minute_reader(asset, entry_root, secondary_root):
    """Return a cached, hash-verified per-minute grid reader."""
    from functools import lru_cache

    conflict_path = Path(secondary_root) / "conflicts.json"
    conflicts = set()
    if conflict_path.exists():
        conflicts = {
            (item["asset"], item["stamp"])
            for item in json.loads(conflict_path.read_text())["conflicts"]
        }

    @lru_cache(maxsize=512)
    def load(minute):
        slot = ((minute + 119) // 120) * 120
        data = slot_data(secondary_root, asset, slot)
        if data is None:
            data = slot_data(entry_root, asset, slot)
        if data is None:
            return None
        return [
            (p["publish_time_us"], price_int(p["price"]))
            for p in data
            if minute * 1_000_000 <= p["publish_time_us"] < (minute + 60) * 1_000_000
            and (asset, p["publish_time_us"]) not in conflicts
        ]

    return load


def summarize(records):
    scored = [
        r for r in records if r["outcome"]["status"] in ("closed_proxy", "liquidated")
    ]
    n = len(scored)
    net_micro_sum = sum(r["outcome"]["payout"] - PAPER_MARGIN for r in scored)
    return {
        "attempted": len(records),
        "n": n,
        "unscored": len(records) - n,
        "mean_roe": net_micro_sum / (n * PAPER_MARGIN) if n else None,
        "net_micro_sum": net_micro_sum,
        "target_touched": sum(
            r["outcome"].get("target_first_us") is not None for r in scored
        ),
        "target_filled": sum(bool(r["outcome"].get("target_filled")) for r in scored),
        "liquidated": sum(r["outcome"]["status"] == "liquidated" for r in scored),
        "liquidated_before_intent": sum(
            r["outcome"]["status"] == "liquidated"
            and r["outcome"].get("intent") is None
            for r in scored
        ),
        "liquidated_during_eligibility": sum(
            r["outcome"]["status"] == "liquidated"
            and r["outcome"].get("intent") is not None
            and r["outcome"]["exit_us"] < r["outcome"]["submit_us"]
            for r in scored
        ),
        "liquidated_during_delay": sum(
            bool(r["outcome"].get("delay_liquidation")) for r in scored
        ),
        "direction_down": sum(r["bar3_color"] == "DOWN" for r in scored),
        "direction_known": sum(r["bar3_color"] != "UNKNOWN" for r in scored),
        "partial_second": {
            color: {
                "n": sum(r.get("partial_second_direction") == color for r in scored),
                "next_down": sum(
                    r.get("partial_second_direction") == color
                    and r["bar3_color"] == "DOWN"
                    for r in scored
                ),
            }
            for color in ("UP", "DOWN", "FLAT")
        },
        "intents": {
            key: sum(r["outcome"].get("intent") == key for r in scored)
            for key in ("target", "momentum", "cap")
        },
    }


def run_scenarios(asset, prepared, candidates, entry_root, secondary_root, flow=None):
    """Run predeclared policies; missing paths occupy asset until conservative cap."""
    from research.exit50_backtest import sparse_replay
    from research.reversal_shapes import color

    bars = prepared["rows"]
    features = {
        stamp * 1_000_000: value for stamp, value in prepared["features"].items()
    }
    ten = {bar[0]: bar for bar in prepared["frames"]["10"][0]}
    get_minute = minute_reader(asset, entry_root, secondary_root)
    variants = []
    for family in ("confirmed_uu", "near_end"):
        family_rows = [c for c in candidates if c["family"] == family]
        for filter_name in ("none", "shape", "shape_bop", "shape_flow"):
            if filter_name == "shape_flow" and flow is None:
                continue
            for exit_name in ("fixed", "second_turn", "target", "target_momentum"):
                for delay in (0, 5, 10):
                    records = []
                    overlap = 0
                    until = -1
                    for c in family_rows:
                        sig = c["signal"]
                        if filter_name != "none" and not sig["shape_filter"]:
                            continue
                        if filter_name == "shape_bop" and not sig["bop_filter"]:
                            continue
                        if filter_name == "shape_flow" and not flow.get(
                            c["decision_s"], False
                        ):
                            continue
                        if c["decision_s"] * 1_000_000 < until:
                            overlap += 1
                            continue
                        target_start = c["decision_s"] + (
                            60 if family == "near_end" else 0
                        )
                        target = ten.get(target_start)
                        bar3_color = color(target) if target else "UNKNOWN"
                        if c["entry_price"] is None:
                            result = {
                                "status": "unscored",
                                "reason": "missing_entry_sample",
                            }
                        else:
                            result = sparse_replay(
                                c["decision_s"] * 1_000_000,
                                c["cap_s"] * 1_000_000,
                                c["entry_price"],
                                bars,
                                features,
                                get_minute,
                                exit_name,
                                delay,
                            )
                        until = (
                            result.get("exit_us") or (c["cap_s"] + delay) * 1_000_000
                        )
                        records.append(
                            {
                                "id": c["id"],
                                "split": c["split"],
                                "bar3_color": bar3_color,
                                "partial_second_direction": sig[
                                    "partial_second_direction"
                                ],
                                "outcome": result,
                            }
                        )
                    summaries = {
                        name: summarize([r for r in records if r["split"] == name])
                        for name in ("train", "validation", "test")
                    }
                    ident = f"{family}/{filter_name}/{exit_name}/{delay}"
                    variants.append(
                        {
                            "id": ident,
                            "family": family,
                            "filter": filter_name,
                            "exit": exit_name,
                            "delay_seconds": delay,
                            "overlap_skips": overlap,
                            "records": records,
                            **summaries,
                        }
                    )
    return variants


def check_envelopes(asset, prepared, root, slots):
    """Compare retained minute extrema to observed grid points; not a keeper proof."""
    mismatches = []
    sampled = missing_bars = 0
    for slot in slots:
        points = slot_data(root, asset, slot)
        if points is None:
            continue
        for point in points:
            stamp = point["publish_time_us"]
            minute = stamp // 60_000_000 * 60
            bar = prepared["rows"].get(minute)
            if bar is None:
                missing_bars += 1
                continue
            low = int(
                (
                    Decimal.from_float(nextafter(float(bar[3]), -inf)) * 10**12
                ).to_integral_value(rounding=ROUND_FLOOR)
            )
            high = int(
                (
                    Decimal.from_float(nextafter(float(bar[2]), inf)) * 10**12
                ).to_integral_value(rounding=ROUND_CEILING)
            )
            price = price_int(point["price"])
            sampled += 1
            if not low <= price <= high:
                mismatches.append(
                    {
                        "minute_s": minute,
                        "sample_us": stamp,
                        "price": price,
                        "low": low,
                        "high": high,
                    }
                )
    return {
        "asset": asset,
        "sampled_points": sampled,
        "missing_bar_points": missing_bars,
        "mismatches": mismatches,
    }


def paired_baseline(
    asset, prepared, candidates, records, entry_root, secondary_root, delay_seconds=10
):
    """Replay fixed-next-bar exit for exactly the strategy's attempted entries.

    This is a per-entry counterfactual and may overlap another paired baseline
    position; stand-alone baseline capacity is reported separately.
    """
    from research.exit50_backtest import sparse_replay

    by_id = {c["id"]: c for c in candidates}
    minute_signals = {
        stamp * 1_000_000: value for stamp, value in prepared["features"].items()
    }
    get_minute = minute_reader(asset, entry_root, secondary_root)
    paired = []
    for record in records:
        c = by_id[record["id"]]
        if c["entry_price"] is None:
            outcome = {"status": "unscored", "reason": "missing_entry_sample"}
        else:
            outcome = sparse_replay(
                c["decision_s"] * 1_000_000,
                c["cap_s"] * 1_000_000,
                c["entry_price"],
                prepared["rows"],
                minute_signals,
                get_minute,
                "fixed",
                delay_seconds,
            )
        paired.append(
            {
                "id": c["id"],
                "split": c["split"],
                "bar3_color": record["bar3_color"],
                "partial_second_direction": record.get("partial_second_direction"),
                "outcome": outcome,
            }
        )
    return paired


def summarize_paired(strategy, baseline):
    """Summarize only common entry IDs with both terminal outcomes qualified."""
    valid = {"closed_proxy", "liquidated"}
    baseline_by_id = {r["id"]: r for r in baseline if r["outcome"]["status"] in valid}
    left = [
        r
        for r in strategy
        if r["outcome"]["status"] in valid and r["id"] in baseline_by_id
    ]
    right = [baseline_by_id[r["id"]] for r in left]
    return {
        "common_n": len(left),
        "strategy": summarize(left),
        "baseline": summarize(right),
    }


def compare_reference(asset, prepared, candidates, plan, entry_root, reference_root):
    """Compare full-grid and sparse engines for frozen reference events."""
    from research.exit50_backtest import replay, sparse_replay

    by_id = {c["id"]: c for c in candidates}
    minute_signals = {
        stamp * 1_000_000: value for stamp, value in prepared["features"].items()
    }
    get_minute = minute_reader(asset, entry_root, reference_root)
    checks = []
    keys = (
        "status",
        "entry_us",
        "entry_price",
        "exit_us",
        "exit_price",
        "intent",
        "submit_us",
        "deadline_us",
        "target_first_us",
        "payout",
        "target_filled",
        "delay_liquidation",
    )
    for event in plan["events"]:
        if event["asset"] != asset:
            continue
        cid = f"{asset}:{event['family']}:{event['decision_s']}"
        c = by_id[cid]
        sample_list = []
        for minute in range(c["decision_s"] // 60 * 60, c["cap_s"] + 61, 60):
            points = get_minute(minute)
            if points:
                sample_list.extend(
                    p for p in points if p[0] > c["decision_s"] * 1_000_000
                )
        for policy in ("fixed", "second_turn", "target", "target_momentum"):
            for delay in (0, 5, 10):
                if c["entry_price"] is None:
                    full = sparse = {
                        "status": "unscored",
                        "reason": "missing_entry_sample",
                    }
                else:
                    full = replay(
                        c["decision_s"] * 1_000_000,
                        c["cap_s"] * 1_000_000,
                        sample_list,
                        minute_signals,
                        policy,
                        delay,
                    )
                    sparse = sparse_replay(
                        c["decision_s"] * 1_000_000,
                        c["cap_s"] * 1_000_000,
                        c["entry_price"],
                        prepared["rows"],
                        minute_signals,
                        get_minute,
                        policy,
                        delay,
                    )
                equal = full["status"] in ("closed_proxy", "liquidated") and all(
                    full.get(k) == sparse.get(k) for k in keys
                )
                checks.append(
                    {
                        "id": cid,
                        "policy": policy,
                        "delay": delay,
                        "equal": equal,
                        "full_status": full["status"],
                        "sparse_status": sparse["status"],
                        "full": full,
                        "sparse": sparse,
                    }
                )
    return checks


def policy_bundle(model_bundle_sha256, variants_by_asset):
    """Bind per-asset validation-selected experimental policies to frozen models."""
    from research.exit50_backtest import select_policy

    if len(model_bundle_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in model_bundle_sha256
    ):
        raise ValueError("invalid_model_bundle_hash")
    assets = {}
    for asset in ("BTC", "ZEC"):
        variants = variants_by_asset[asset]
        selected = select_policy(variants)
        found = next((v for v in variants if v["id"] == selected["id"]), None)
        validation = (
            found["validation"]
            if found is not None and selected["selection"] != "experimental_fallback"
            else None
        )
        assets[asset] = {
            "family": selected["family"],
            "filter": selected["filter"],
            "policy": selected["exit"],
            "delay_seconds": selected["delay_seconds"],
            "selection_status": "validation-selected" if validation else "experimental",
            "id": selected["id"],
            "validation_n": validation["n"] if validation else None,
            "validation_mean_roe": validation["mean_roe"] if validation else None,
        }
    return {
        "schema": "exit50-selected-policy/v1",
        "model_bundle_sha256": model_bundle_sha256,
        "assets": assets,
    }


def first_missing_windows(asset, prepared, candidates, entry_root, secondary_root):
    """Find first missing proof window per full-cohort candidate/policy.

    Results are acquisition needs only. Re-run after each archived batch. Never
    choose candidates by observed performance; each variant proceeds through
    its own terminal or an irrecoverable data gap.
    """
    from research.exit50_backtest import sparse_replay

    get_minute = minute_reader(asset, entry_root, secondary_root)
    features = {
        stamp * 1_000_000: value for stamp, value in prepared["features"].items()
    }
    slots = set()
    permanent = []
    cases = []
    checked = 0
    metadata_cache = {}
    conflict_path = Path(secondary_root) / "conflicts.json"
    conflict_stamps = (
        {
            (x["asset"], x["stamp"])
            for x in json.loads(conflict_path.read_text())["conflicts"]
        }
        if conflict_path.exists()
        else set()
    )

    def source_sha(root, slot):
        key = (str(root), slot)
        if key not in metadata_cache:
            path = Path(root) / f"{asset}-{slot}.meta.json"
            metadata_cache[key] = (
                json.loads(path.read_text()).get("sha256") if path.exists() else None
            )
        return metadata_cache[key]

    for c in candidates:
        entry_slot = c["decision_s"] + (60 if c["family"] == "near_end" else 0)
        entry_sha = source_sha(entry_root, entry_slot)
        source_hashes = {entry_sha} if entry_sha else set()
        if c["entry_price"] is None:
            for policy in ("fixed", "second_turn", "target", "target_momentum"):
                for delay in (0, 5, 10):
                    cases.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "state": "unscored",
                            "reason": "missing_entry_sample",
                        }
                    )
                    permanent.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "reason": "missing_entry_sample",
                        }
                    )
                    checked += 1
            continue
        for policy in ("fixed", "second_turn", "target", "target_momentum"):
            for delay in (0, 5, 10):
                source_hashes = {entry_sha} if entry_sha else set()

                def tracked_minute(minute, source_hashes=source_hashes):
                    slot = ((minute + 119) // 120) * 120
                    root = (
                        secondary_root
                        if (Path(secondary_root) / f"{asset}-{slot}.meta.json").exists()
                        else entry_root
                    )
                    sha = source_sha(root, slot)
                    if sha:
                        source_hashes.add(sha)
                    return get_minute(minute)

                outcome = sparse_replay(
                    c["decision_s"] * 1_000_000,
                    c["cap_s"] * 1_000_000,
                    c["entry_price"],
                    prepared["rows"],
                    features,
                    tracked_minute,
                    policy,
                    delay,
                )
                checked += 1
                if outcome["status"] != "unscored":
                    cases.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "state": "terminal",
                            "terminal_us": outcome["exit_us"],
                        }
                    )
                    continue
                if outcome.get("reason") != "incomplete_or_invalid_grid":
                    cases.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "state": "unscored",
                            "reason": outcome["reason"],
                        }
                    )
                    permanent.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "reason": outcome["reason"],
                        }
                    )
                    continue
                minute = outcome["at_us"] // 60_000_000 * 60
                slot = ((minute + 119) // 120) * 120
                path = Path(secondary_root) / f"{asset}-{slot}.meta.json"
                old = Path(entry_root) / f"{asset}-{slot}.meta.json"
                if path.exists() or old.exists():
                    metadata = json.loads((path if path.exists() else old).read_text())
                    if (asset, outcome["at_us"]) in conflict_stamps or outcome[
                        "at_us"
                    ] in metadata.get("price_conflict_timestamps", []):
                        reason = "conflicting_price_at_needed_timestamp"
                    elif metadata.get("status") == "failed":
                        reason = "source_failed_after_bounded_attempts"
                    elif metadata.get("grid_status") == "partial_or_invalid":
                        reason = "incomplete_grid_after_bounded_attempts"
                    else:
                        reason = "existing_grid_gap"
                    cases.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "state": "unscored",
                            "reason": reason,
                            "at_us": outcome["at_us"],
                        }
                    )
                    permanent.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "reason": reason,
                            "at_us": outcome["at_us"],
                        }
                    )
                else:
                    cases.append(
                        {
                            "id": c["id"],
                            "policy": policy,
                            "delay": delay,
                            "source_sha256": sorted(source_hashes),
                            "state": "need_source",
                            "slot": slot,
                        }
                    )
                    slots.add((asset, slot))
    return {
        "checked": checked,
        "slots": sorted(slots),
        "permanent": permanent,
        "cases": cases,
    }


def verify_wave_joins(wave_root, entry_root, cache_root):
    """Reject differing valid prices at overlapping archived window timestamps."""
    manifest = json.loads((Path(wave_root) / "manifest.json").read_text())
    records = manifest["records"]
    checked = 0
    conflicts = []
    for record in records:
        asset, slot = record["asset"], record["slot"]
        own = slot_data(wave_root, asset, slot)
        if own is None:
            continue
        own_by_time = {p["publish_time_us"]: p["price"] for p in own}
        for adjacent in (slot - 120, slot + 120):
            for source in (wave_root, cache_root, entry_root):
                if not (Path(source) / f"{asset}-{adjacent}.meta.json").exists():
                    continue
                neighbor = slot_data(source, asset, adjacent)
                if neighbor is None:
                    continue
                for point in neighbor:
                    stamp = point["publish_time_us"]
                    if stamp in own_by_time:
                        checked += 1
                        if Decimal(own_by_time[stamp]) != Decimal(point["price"]):
                            conflicts.append(
                                {
                                    "asset": asset,
                                    "stamp": stamp,
                                    "slot": slot,
                                    "adjacent": adjacent,
                                    "source": str(source),
                                    "price": own_by_time[stamp],
                                    "other_price": point["price"],
                                }
                            )
    return {"join_points_checked": checked, "conflicts": conflicts}


def btc_taker_filter(feature_document):
    """Map exact completed-minute Binance quote pressure to short eligibility."""
    import math

    if feature_document.get("schema") != "binance-btc-taker-quote-pressure/v1":
        raise ValueError("invalid_btc_flow_source")
    result = {}
    for row in feature_document["rows"]:
        at = row["available_at_ms"]
        if type(at) is not int or at % 1000:
            raise ValueError("invalid_flow_timestamp")
        value = row["sma3"]
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("invalid_flow_value")
        if at // 1000 in result:
            raise ValueError("duplicate_flow_timestamp")
        result[at // 1000] = value < 0
    return result
