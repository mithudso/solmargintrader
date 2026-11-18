"""Exploratory causal UU→D and UUD→U study with full-bar oracle barriers.

The existing prospective trial and its immutable selection are not modified.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from itertools import pairwise, product
from pathlib import Path

import numpy as np
import pandas as pd

from research.reversal_history import canonical, pack, read_archive, validated_rows
from research.reversal_shapes import (
    INTERVALS,
    START,
    STOP,
    boundaries,
    color,
    group_for,
    shape_labels,
    wilson,
)

BARRIERS = (5, 7.5, 9.8, 10)
BASES = ("oracle_signal", "spot_signal")
STAGES = ("first_down", "second_up")
COMMON = (
    "all",
    "shape_rising",
    "shape_falling",
    "shape_range",
    "ema_up",
    "ema_down",
    "rsi_high",
    "rsi_low",
    "volume_surge",
    "volume_quiet",
    "upper_wick",
    "lower_wick",
    "close_high",
    "close_low",
    "boll_high",
    "boll_low",
    "macd_improving",
    "macd_weakening",
    "atr_low",
    "body_small",
    "body_large",
    "rising_upper_rejection",
    "range_upper_rejection",
)
SECOND = (
    "pullback_shallow",
    "pullback_deep",
    "uptrend_shallow",
    "shallow_lower_rejection",
    "quiet_shallow",
)


def aggregate(rows, minutes, *, require_volume):
    buckets = {}
    for row in validated_rows(rows):
        buckets.setdefault(row[0] // (minutes * 60) * (minutes * 60), []).append(row)
    bars = []
    for stamp, chunk in sorted(buckets.items()):
        if len(chunk) != minutes or any(
            r[0] != stamp + j * 60 or (require_volume and r[5] <= 0)
            for j, r in enumerate(chunk)
        ):
            continue
        bars.append(
            [
                stamp,
                chunk[0][1],
                max(r[2] for r in chunk),
                min(r[3] for r in chunk),
                chunk[-1][4],
                sum(r[5] for r in chunk),
            ]
        )
    return bars


def features(bars, minutes, *, volume_qualified):
    """Every vector operation uses a trailing window or an earlier row only."""
    result = [None] * len(bars)
    edges = (
        [0]
        + [
            i
            for i in range(1, len(bars))
            if bars[i][0] - bars[i - 1][0] != minutes * 60
        ]
        + [len(bars)]
    )
    for left, right in pairwise(edges):
        frame = pd.DataFrame(
            bars[left:right], columns=["time", "open", "high", "low", "close", "volume"]
        )
        c, o, h, low, v = (frame[k] for k in ("close", "open", "high", "low", "volume"))
        tr = pd.concat(
            [h - low, (h - c.shift()).abs(), (low - c.shift()).abs()], axis=1
        ).max(axis=1)
        atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        change = c.diff()
        gain = (
            change.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        )
        loss = (
            (-change.clip(upper=0))
            .ewm(alpha=1 / 14, adjust=False, min_periods=14)
            .mean()
        )
        rsi = (
            (100 - 100 / (1 + gain / loss.replace(0, np.nan)))
            .where(loss != 0, 100)
            .where((gain != 0) | (loss != 0), 50)
        )
        ema12, ema26 = (
            c.ewm(span=12, adjust=False).mean(),
            c.ewm(span=26, adjust=False).mean(),
        )
        macd = ema12 - ema26
        histogram = macd - macd.ewm(span=9, adjust=False).mean()
        ranges = (h - low).replace(0, np.nan)
        columns = pd.DataFrame(
            {
                "rsi": rsi,
                "atr_bps": atr / c * 10000,
                "ema_spread_atr": (ema12 - ema26) / atr,
                "macd_change_atr": histogram.diff() / atr,
                "zscore": (c - c.rolling(20).mean())
                / c.rolling(20)
                .apply(lambda window: np.std(window, ddof=0), raw=True)
                .replace(0, np.nan),
                "upper_wick": (h - pd.concat([o, c], axis=1).max(axis=1)) / ranges,
                "lower_wick": (pd.concat([o, c], axis=1).min(axis=1) - low) / ranges,
                "close_position": (c - low) / ranges,
                "body_atr": (c - o).abs() / atr,
                "volume_ratio": v / v.shift().rolling(20).mean().replace(0, np.nan),
            }
        )
        for j, record in enumerate(columns.to_dict("records"), left):
            result[j] = {
                k: float(x)
                if np.isfinite(x) and (k != "volume_ratio" or volume_qualified)
                else None
                for k, x in record.items()
            }
    return result


def flags(f, shape, stage, pullback):
    def ge(k, x):
        return f.get(k) is not None and f[k] >= x

    def le(k, x):
        return f.get(k) is not None and f[k] <= x

    group = group_for(shape)
    out = {
        "all": True,
        **{f"shape_{g}": group == g for g in ("rising", "falling", "range")},
        "ema_up": ge("ema_spread_atr", 0),
        "ema_down": le("ema_spread_atr", 0),
        "rsi_high": ge("rsi", 60),
        "rsi_low": le("rsi", 40),
        "volume_surge": ge("volume_ratio", 1.5),
        "volume_quiet": le("volume_ratio", 0.75),
        "upper_wick": ge("upper_wick", 0.35),
        "lower_wick": ge("lower_wick", 0.35),
        "close_high": ge("close_position", 0.75),
        "close_low": le("close_position", 0.25),
        "boll_high": ge("zscore", 1),
        "boll_low": le("zscore", -1),
        "macd_improving": f.get("macd_change_atr") is not None
        and f["macd_change_atr"] > 0,
        "macd_weakening": f.get("macd_change_atr") is not None
        and f["macd_change_atr"] < 0,
        "atr_low": le("atr_bps", 10),
        "body_small": le("body_atr", 0.5),
        "body_large": ge("body_atr", 1),
    }
    out["rising_upper_rejection"] = out["shape_rising"] and out["upper_wick"]
    out["range_upper_rejection"] = out["shape_range"] and out["upper_wick"]
    if stage == "second_up":
        out.update(
            {"pullback_shallow": pullback <= 0.5, "pullback_deep": pullback >= 1}
        )
        out["uptrend_shallow"] = out["ema_up"] and out["pullback_shallow"]
        out["shallow_lower_rejection"] = out["pullback_shallow"] and out["lower_wick"]
        out["quiet_shallow"] = out["pullback_shallow"] and out["volume_quiet"]
    return out


def crosses(target, direction, bps):
    entry = Decimal(str(target[1]))
    fraction = Decimal(str(bps)) / 10000
    if direction == "UP":
        return Decimal(str(target[3])) <= entry * (1 - fraction)
    return Decimal(str(target[2])) >= entry * (1 + fraction)


def make_events(signal_rows, oracle_rows, minutes, basis):
    bars = aggregate(signal_rows, minutes, require_volume=basis == "spot_signal")
    targets = {b[0]: b for b in aggregate(oracle_rows, minutes, require_volume=False)}
    labels = shape_labels(bars, minutes)
    values = features(bars, minutes, volume_qualified=basis == "spot_signal")
    cuts = boundaries()
    out = []
    for i in range(2, len(bars)):
        if labels[i] == "unknown" or any(
            bars[j][0] - bars[j - 1][0] != minutes * 60 for j in (i - 1, i)
        ):
            continue
        stage = None
        if color(bars[i - 1]) == color(bars[i]) == "UP":
            stage = "first_down"
        elif (
            color(bars[i - 2]) == color(bars[i - 1]) == "UP"
            and color(bars[i]) == "DOWN"
        ):
            stage = "second_up"
        if stage is None:
            continue
        stamp = bars[i][0] + minutes * 60
        target = targets.get(stamp)
        split = next(
            (
                name
                for name, a, b in zip(("train", "validation", "test"), cuts, cuts[1:])
                if a <= stamp and stamp + minutes * 60 <= b
            ),
            None,
        )
        if target is None or split is None:
            continue
        f = dict(values[i])
        pullback = 0.0
        if stage == "second_up":
            pullback = (bars[i][1] - bars[i][4]) / sum(
                bars[j][4] - bars[j][1] for j in (i - 2, i - 1)
            )
            f["pullback_fraction"] = pullback
        direction = "DOWN" if stage == "first_down" else "UP"
        adverse = max(
            0.0,
            (1 - target[3] / target[1]) * 10000
            if direction == "UP"
            else (target[2] / target[1] - 1) * 10000,
        )
        out.append(
            {
                "basis": basis,
                "minutes": minutes,
                "stage": stage,
                "split": split,
                "signal_at": stamp,
                "target_end": stamp + minutes * 60,
                "direction": direction,
                "signal_shape": labels[i],
                "features": f,
                "flags": flags(f, labels[i], stage, pullback),
                "target_ohlcv": target,
                "hit": color(target) == direction,
                "gross_directional_bps": (target[4] / target[1] - 1)
                * 10000
                * (1 if direction == "UP" else -1),
                "adverse_bps": adverse,
                "crossed": {str(b): crosses(target, direction, b) for b in BARRIERS},
            }
        )
    return out


def metrics(events):
    n, hits = len(events), sum(e["hit"] for e in events)
    joint = sum(e["hit"] and not e["crossed"]["9.8"] for e in events)
    return {
        "n": n,
        "hits": hits,
        "direction_rate": hits / n if n else None,
        "direction_wilson": wilson(hits, n),
        "joint": joint,
        "joint_rate": joint / n if n else None,
        "joint_wilson": wilson(joint, n),
        "correct_but_liquidated": sum(e["hit"] and e["crossed"]["9.8"] for e in events),
        "crossed_by_bps": {
            str(b): sum(e["crossed"][str(b)] for e in events) for b in BARRIERS
        },
        "mean_adverse_bps": float(np.mean([e["adverse_bps"] for e in events]))
        if n
        else None,
        "median_adverse_bps": float(np.median([e["adverse_bps"] for e in events]))
        if n
        else None,
        "mean_gross_directional_bps": float(
            np.mean([e["gross_directional_bps"] for e in events])
        )
        if n
        else None,
    }


def summarize(events):
    rows = []
    for basis, stage, minutes in product(BASES, STAGES, INTERVALS):
        subset = [
            e
            for e in events
            if e["basis"] == basis and e["stage"] == stage and e["minutes"] == minutes
        ]
        for condition in COMMON + (SECOND if stage == "second_up" else ()):
            splits = {
                s: metrics(
                    [e for e in subset if e["split"] == s and e["flags"].get(condition)]
                )
                for s in ("train", "validation", "test")
            }
            rows.append(
                {
                    "id": f"{basis}:{stage}:{minutes}:{condition}",
                    "basis": basis,
                    "stage": stage,
                    "minutes": minutes,
                    "condition": condition,
                    "splits": splits,
                }
            )
    selected = []
    for basis, stage in product(BASES, STAGES):
        eligible = [
            r
            for r in rows
            if r["basis"] == basis
            and r["stage"] == stage
            and r["splits"]["train"]["n"] >= 40
            and r["splits"]["validation"]["n"] >= 20
        ]
        selected.append(
            min(
                eligible,
                key=lambda r: (
                    -r["splits"]["validation"]["joint_wilson"][0],
                    -r["splits"]["validation"]["n"],
                    r["id"],
                ),
            )
            if eligible
            else {"basis": basis, "stage": stage, "id": None}
        )
    return rows, selected


def correlations(events):
    out = []
    for basis, stage in product(BASES, STAGES):
        group = [e for e in events if e["basis"] == basis and e["stage"] == stage]
        keys = sorted({k for e in group for k in e["features"]})
        for split, feature, outcome in product(
            ("train", "validation", "test"), keys, ("direction", "joint")
        ):
            pairs = [
                (
                    e["features"].get(feature),
                    int(
                        e["hit"] and (outcome == "direction" or not e["crossed"]["9.8"])
                    ),
                )
                for e in group
                if e["split"] == split and e["features"].get(feature) is not None
            ]
            x, y = ([p[j] for p in pairs] for j in (0, 1))
            correlation = (
                float(np.corrcoef(x, y)[0, 1])
                if len(x) > 1 and np.std(x) > 0 and np.std(y) > 0
                else None
            )
            out.append(
                {
                    "basis": basis,
                    "stage": stage,
                    "split": split,
                    "feature": feature,
                    "outcome": outcome,
                    "n": len(pairs),
                    "correlation": correlation,
                    "success_mean": float(np.mean([a for a, b in pairs if b]))
                    if any(y)
                    else None,
                    "failure_mean": float(np.mean([a for a, b in pairs if not b]))
                    if any(not b for b in y)
                    else None,
                }
            )
    return out


def analyze(oracle, spot):
    if oracle["coin"] != spot["coin"]:
        raise ValueError("asset_mismatch")
    for source in (oracle, spot):
        rows = validated_rows(source["rows"])
        if [r[0] for r in rows] != list(range(START, STOP, 60)):
            raise ValueError("fixed_source_coverage_mismatch")
    events = [
        e
        for basis, minutes in product(BASES, INTERVALS)
        for e in make_events(
            oracle["rows"] if basis == "oracle_signal" else spot["rows"],
            oracle["rows"],
            minutes,
            basis,
        )
    ]
    candidates, selected = summarize(events)
    return {
        "schema": "second-turn-liquidation-results/v1",
        "coin": oracle["coin"],
        "start": START,
        "stop_exclusive": STOP,
        "qualification": "exploratory retrospective; fixed200ms oracle-OHLC barrier proxy, no funded fill or future survival qualification",
        "primary_barrier_bps": 9.8,
        "barriers": list(BARRIERS),
        "candidate_rows": candidates,
        "selected": selected,
        "correlations": correlations(events),
        "events": events,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--spot", type=Path, required=True)
    args = parser.parse_args(argv)
    print(canonical(pack(analyze(read_archive(args.oracle), read_archive(args.spot)))))


if __name__ == "__main__":
    main()
