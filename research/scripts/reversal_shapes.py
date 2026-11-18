"""Frozen, causal two-bar/shape study and the identical prospective signal rule.

Spot candles support direction counts and cost sensitivities, not Jupiter fills.
The final chronological split is never consulted by the selector.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from itertools import pairwise, product
from pathlib import Path

import numpy as np
import pandas as pd

from research.reversal_history import canonical, pack, read_archive, validated_rows
from research.shape_study import detect_shapes, protected_intervals

START = 1791663600
STOP = 1794164400
INTERVALS = (5, 10, 15, 20)
WINDOW = 48
FEE_BPS = 16
GROUPS = {
    "rising": {"trend_up", "bowl", "v_rebound"},
    "falling": {"trend_down", "cap", "inverted_v"},
    "range": {"range", "compression"},
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def group_for(shape):
    return next(
        (group for group, labels in GROUPS.items() if shape in labels), "unknown"
    )


def boundaries(start=START, stop=STOP):
    span = stop - start
    return (
        start,
        int((start + span * 0.6) // 1200) * 1200,
        int((start + span * 0.8) // 1200) * 1200,
        stop,
    )


def wilson(correct, n):
    if not n:
        return [None, None]
    z = 1.959963984540054
    p, q = correct / n, z * z / n
    center = (p + q / 2) / (1 + q)
    half = z * np.sqrt(p * (1 - p) / n + q / (4 * n)) / (1 + q)
    return [float(center - half), float(center + half)]


def candles(rows, minutes):
    """Only epoch-aligned buckets with every positive-volume minute survive."""
    rows = validated_rows(rows)
    step = minutes * 60
    buckets = {}
    for row in rows:
        buckets.setdefault(row[0] // step * step, []).append(row)
    result = []
    for stamp, chunk in sorted(buckets.items()):
        if len(chunk) != minutes or any(
            r[0] != stamp + j * 60 or r[5] <= 0 for j, r in enumerate(chunk)
        ):
            continue
        result.append(
            [
                stamp,
                chunk[0][1],
                max(r[2] for r in chunk),
                min(r[3] for r in chunk),
                chunk[-1][4],
                sum(r[5] for r in chunk),
            ]
        )
    return result


def shape_labels(bars, minutes):
    """Restart warmup at a gap rather than fitting across unavailable candles."""
    labels = ["unknown"] * len(bars)
    starts = (
        [0]
        + [
            j
            for j in range(1, len(bars))
            if bars[j][0] - bars[j - 1][0] != minutes * 60
        ]
        + [len(bars)]
    )
    for left, right in pairwise(starts):
        if right - left < WINDOW:
            continue
        frame = pd.DataFrame(
            bars[left:right],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        labels[left:right] = detect_shapes(frame, WINDOW)["shape"].tolist()
    return labels


def color(bar):
    return "UP" if bar[4] > bar[1] else "DOWN" if bar[4] < bar[1] else "FLAT"


def setup(bars, labels, i, minutes):
    if i < 1 or labels[i] == "unknown" or bars[i][0] - bars[i - 1][0] != minutes * 60:
        return None
    a, b = color(bars[i - 1]), color(bars[i])
    if a != b or a == "FLAT":
        return None
    return {
        "pair": "UU" if a == "UP" else "DD",
        "shape": labels[i],
        "shape_group": group_for(labels[i]),
        "signal_available_at": bars[i][0] + minutes * 60,
        "interval_minutes": minutes,
    }


def events(rows, minutes, start=START, stop=STOP):
    bars = candles(rows, minutes)
    labels = shape_labels(bars, minutes)
    cuts = boundaries(start, stop)
    result, baseline = [], []
    for i in range(len(bars) - 1):
        target = bars[i + 1]
        if target[0] != bars[i][0] + minutes * 60 or labels[i] == "unknown":
            continue
        split = next(
            (
                name
                for name, left, right in zip(
                    ("train", "validation", "test"), cuts, cuts[1:]
                )
                if left <= target[0] and target[0] + minutes * 60 <= right
            ),
            None,
        )
        if split is None:
            continue
        record = {
            "interval_minutes": minutes,
            "target_start": target[0],
            "target_end": target[0] + minutes * 60,
            "split": split,
            "target_color": color(target),
            "open": target[1],
            "close": target[4],
            "high": target[2],
            "low": target[3],
            "up_bps": (target[4] / target[1] - 1) * 10000,
        }
        baseline.append(record)
        signal = setup(bars, labels, i, minutes)
        if signal:
            result.append({**record, **signal})
    return result, baseline


def rules():
    for minutes, pair, prediction, group in product(
        INTERVALS,
        ("UU", "DD"),
        ("reversal", "continuation"),
        ("all", "rising", "falling", "range"),
    ):
        direction = (
            ("DOWN" if pair == "UU" else "UP")
            if prediction == "reversal"
            else ("UP" if pair == "UU" else "DOWN")
        )
        yield {
            "id": f"{minutes}m:{pair}:{prediction}:{group}",
            "interval_minutes": minutes,
            "pair": pair,
            "prediction": prediction,
            "shape_group": group,
            "direction": direction,
        }


def matches(event, rule):
    return (
        event["interval_minutes"] == rule["interval_minutes"]
        and event["pair"] == rule["pair"]
        and (
            rule["shape_group"] == "all" or event["shape_group"] == rule["shape_group"]
        )
    )


def metrics(rows, direction):
    n = len(rows)
    correct = sum(r["target_color"] == direction for r in rows)
    gross = [r["up_bps"] * (1 if direction == "UP" else -1) for r in rows]
    return {
        "n": n,
        "correct": correct,
        "flat": sum(r["target_color"] == "FLAT" for r in rows),
        "hit_rate": correct / n if n else None,
        "wilson95_descriptive": wilson(correct, n),
        "mean_gross_bps": float(np.mean(gross)) if n else None,
        "mean_net_bps_by_roundtrip_cost": {
            str(f): float(np.mean(gross)) - f if n else None for f in (8, 16, 24)
        },
        "arithmetic_10x_mean_net_percent": (float(np.mean(gross)) - FEE_BPS) / 10
        if n
        else None,
    }


def select(candidates):
    """No test metrics enter eligibility, fallback or ranking."""
    eligible = [
        c for c in candidates if c["train"]["n"] >= 40 and c["validation"]["n"] >= 20
    ]
    if eligible:
        chosen = min(
            eligible,
            key=lambda c: (
                -c["validation"]["wilson95_descriptive"][0],
                -c["validation"]["mean_gross_bps"],
                -c["validation"]["n"],
                c["rule"]["id"],
            ),
        )
        return chosen, "exploratory-validation-selected"
    usable = [c for c in candidates if c["validation"]["n"]]
    if not usable:
        return None, "no-validation-events"
    return min(
        usable, key=lambda c: (-c["validation"]["n"], c["rule"]["id"])
    ), "exploratory-low-sample-fallback"


def analyze(source):
    start, stop = source["study_start"], source["study_end_exclusive"]
    all_events, baseline = [], []
    for minutes in INTERVALS:
        e, b = events(source["rows"], minutes, start, stop)
        all_events.extend(e)
        baseline.extend(b)
    conditional = []
    for minutes, pair, split in product(
        INTERVALS, ("UU", "DD"), ("train", "validation", "test")
    ):
        pool = [
            e
            for e in all_events
            if (e["interval_minutes"], e["pair"], e["split"]) == (minutes, pair, split)
        ]
        for shape in ["all"] + sorted({e["shape"] for e in pool}):
            picked = (
                pool if shape == "all" else [e for e in pool if e["shape"] == shape]
            )
            conditional.append(
                {
                    "interval_minutes": minutes,
                    "pair": pair,
                    "split": split,
                    "shape": shape,
                    "down": metrics(picked, "DOWN"),
                    "up": metrics(picked, "UP"),
                }
            )
    candidates = []
    for rule in rules():
        row = {"rule": rule}
        # Intentionally compute only training and validation before selecting.
        for split in ("train", "validation"):
            row[split] = metrics(
                [e for e in all_events if e["split"] == split and matches(e, rule)],
                rule["direction"],
            )
        candidates.append(row)
    selected, evidence = select(candidates)
    frozen = (
        {**selected["rule"], "asset": source["coin"], "evidence": evidence}
        if selected
        else None
    )
    # The locked rule exists before the test summary is evaluated.
    for row in candidates:
        row["test"] = metrics(
            [e for e in all_events if e["split"] == "test" and matches(e, row["rule"])],
            row["rule"]["direction"],
        )
    return {
        "schema": "reversal-shape-result/v1",
        "coin": source["coin"],
        "venue": source["venue"],
        "quote": source["quote"],
        "source_sha256": sha(canonical(source).encode()),
        "input_minutes": len(source["rows"]),
        "boundaries": list(boundaries(start, stop)),
        "selected_rule": frozen,
        "selected_metrics": {s: selected[s] for s in ("train", "validation", "test")}
        if selected
        else None,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "conditional": conditional,
        "unconditional": [
            {
                "interval_minutes": m,
                "split": s,
                "up": metrics(
                    [
                        b
                        for b in baseline
                        if b["interval_minutes"] == m and b["split"] == s
                    ],
                    "UP",
                ),
                "down": metrics(
                    [
                        b
                        for b in baseline
                        if b["interval_minutes"] == m and b["split"] == s
                    ],
                    "DOWN",
                ),
            }
            for m, s in product(INTERVALS, ("train", "validation", "test"))
        ],
        "events": all_events,
        "limits": [
            "Previously studied spot histories; test split is untouched only within this run.",
            "Different historical venues/quotes; no Jupiter execution parity.",
            "Wilson intervals are descriptive, not dependence/multiplicity-adjusted.",
            "Costs are 8/16/24bps roundtrip scenarios; no observed spread, borrow or funding.",
            "10x is arithmetic sensitivity without a venue liquidation model; no1000x P&L inference.",
            "Selected rule can lose money despite predictive accuracy.",
        ],
    }


def report(results):
    lines = [
        "# ZEC and BTC: two-bar reversal conditioned on graph shape",
        "",
        "Frozen 5/10/15/20-minute study. Two completed UP bars predict DOWN only under a reversal rule; two DOWN bars predict UP. Shapes use the previous48 completed bars.",
        "",
        "The study ends before the existing unsealed BTC holdout. The60/20/20 split is chronological. The last20% was excluded from selection in this run; these histories were used by older studies, so prospective paper testing remains necessary.",
        "",
        "## Selected prospective candidates",
        "",
        "Selection uses validation Wilson lower bound, then mean gross return, sample count and stable ID. Each asset has64 predeclared candidates. Intervals are descriptive and unadjusted for overlapping events or multiple selection.",
        "",
        "| Asset/source | Frozen rule | Validation n/hit | Final test n/hit | Test gross bps | Test net16bps |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in results:
        s, m = r["selected_rule"], r["selected_metrics"]
        if s is None:
            continue
        v, t = m["validation"], m["test"]
        fmt = lambda x: "unavailable" if x is None else f"{x:.2f}"
        lines.append(
            f"| {r['coin']} / {r['venue']} | {s['id']} → {s['direction']} | {v['n']} / {fmt(100 * v['hit_rate'])}% | {t['n']} / {fmt(100 * t['hit_rate']) if t['n'] else 'unavailable'}% | {fmt(t['mean_gross_bps'])} | {fmt(t['mean_net_bps_by_roundtrip_cost']['16'])} |"
        )
    lines += [
        "",
        "## Does a rising graph change the third bar?",
        "",
        "Final-split rows below compare third-bar DOWN rates after UU. Sparse cells remain descriptive. Rising shapes are trend_up, bowl and v_rebound; falling shapes are trend_down, cap and inverted_v. Range/compression is a separate group.",
        "",
        "| Asset | Minutes | Shape | n | Third bar DOWN |",
        "|---|---:|---|---:|---:|",
    ]
    for r in results:
        for row in r["conditional"]:
            if row["pair"] == "UU" and row["split"] == "test":
                d = row["down"]
                rate = f"{100 * d['hit_rate']:.1f}%" if d["n"] else "unavailable"
                lines.append(
                    f"| {r['coin']} | {row['interval_minutes']} | {row['shape']} | {d['n']} | {rate} |"
                )
    lines += [
        "",
        "## Execution and forward-test limits",
        "",
        "The16bps roundtrip scenario uses8bps per fill. Report8/16/24bps sensitivities separately. These are spot open-to-close proxies, not observed Jupiter fees/fills, borrow or funding. The10x sensitivity multiplies notional return; it does not simulate liquidation. Minute candles cannot establish executable1000x profitability.",
        "",
        "Historical ZEC and BTC are Binance spot USDT candles. The forward worker uses newly observed Coinbase ZEC-USD and BTC-USD prices, records decisions before outcomes, and never sends orders. Venue transfer is unqualified.",
        "",
        "No candidate is described as profitable or qualified merely because it is the highest ranked. The full artifact retains every candidate, both UU/DD directions, shape cells, unconditional baselines, gaps and sample counts.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--zec-csv", type=Path, required=True)
    prepare.add_argument("--btc-archive", type=Path, required=True)
    prepare.add_argument("--asset", choices=("ZEC", "BTC"), required=True)
    prepare.add_argument("--part", type=int, default=0)
    prepare.add_argument("--part-size", type=int, default=4000)
    run = sub.add_parser("analyze")
    run.add_argument("--source", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "analyze":
        print(canonical(pack(analyze(read_archive(args.source)))))
        return
    reservations = protected_intervals(
        Path.home() / ".config/soltui/experiments/experiments.sqlite3", ("ZEC", "BTC")
    )
    if any(START < r["end"] and STOP > r["start"] for r in reservations):
        raise ValueError("study overlaps protected unsealed holdout")
    if args.asset == "ZEC":
        raw = args.zec_csv.read_bytes()
        if (
            sha(raw)
            != "7803d0184c2a4437a89deda2e65869ef7d290576a1324e20bf52b8826ae3cd6f"
        ):
            raise ValueError("ZEC retained source hash mismatch")
        with args.zec_csv.open() as stream:
            reader = csv.reader(stream)
            next(reader)
            rows = validated_rows(list(reader))
        metadata = {
            "coin": "ZEC",
            "venue": "Binance spot",
            "quote": "USDT",
            "product": "ZECUSDT",
            "parent_csv_sha256": sha(raw),
            "source_url": "https://api.binance.com/api/v3/klines",
        }
    else:
        source = read_archive(args.btc_archive)
        rows = validated_rows(source["rows"])
        metadata = {
            k: source[k] for k in ("coin", "venue", "quote", "product", "source_url")
        }
        metadata["fetched_at"] = source.get("fetched_at")
    rows = [r for r in rows if START <= r[0] < STOP]
    left = args.part * args.part_size
    value = {
        **metadata,
        "schema": "reversal-shape-source-part/v1",
        "study_start": START,
        "study_end_exclusive": STOP,
        "part": args.part,
        "total_rows": len(rows),
        "part_size": args.part_size,
        "rows": rows[left : left + args.part_size],
    }
    if args.asset == "BTC":
        end = min(STOP, START + (left + args.part_size) * 60)
        value["pages"] = [
            p for p in source.get("pages", []) if START + left * 60 <= p["start"] < end
        ]
    print(canonical(pack(value)))


if __name__ == "__main__":
    main()
