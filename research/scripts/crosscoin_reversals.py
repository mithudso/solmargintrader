"""Repeat the frozen ZEC reversal definitions on labelled historical candles.

This descriptive analysis emits JSON only. It does not fit rules, submit trades,
estimate fills, or interpret an excursion maximum as an executable profit.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from research.reversal_history import (
    canonical,
    digest,
    iso,
    pack,
    read_archive,
    validated_rows,
)
from research.zec_reversal_excursions import (
    HORIZONS,
    POLICIES,
    aggregate,
    event_outcome,
    events_for,
)

MASKS = ("present", "active")


def wilson(successes, total):
    """Descriptive 95% binomial interval; temporal dependence is not corrected."""
    if not total:
        return None
    z = 1.959963984540054
    p, q = successes / total, z * z / total
    center = (p + q / 2) / (1 + q)
    half = z * math.sqrt(p * (1 - p) / total + q / (4 * total)) / (1 + q)
    return [center - half, center + half]


def dense_bars(source):
    rows = validated_rows(source["rows"])
    start, stop = source["input_start"], source["input_end_exclusive"]
    if type(start) is not int or type(stop) is not int or start % 60 or stop % 60:
        raise ValueError("invalid_source_bounds")
    if not start < stop or stop - start > 40 * 86400:
        raise ValueError("source_window_out_of_bounds")
    if any(not start <= r[0] < stop for r in rows):
        raise ValueError("candle_outside_source_bounds")
    by_time = {r[0]: r for r in rows}
    bars = []
    for stamp in range(start, stop, 60):
        row = by_time.get(stamp)
        bars.append(
            {
                "ts": stamp,
                "open": row[1] if row else None,
                "high": row[2] if row else None,
                "low": row[3] if row else None,
                "close": row[4] if row else None,
                "volume": row[5] if row else None,
                "present": row is not None,
                "active": row is not None and row[5] > 0,
            }
        )
    return bars


def rate_summary(directions):
    n = len(directions)
    counts = {name: directions.count(name) for name in ("UP", "DOWN", "FLAT")}
    return {
        "n": n,
        **counts,
        "down_rate": counts["DOWN"] / n if n else None,
        "down_wilson95_descriptive": wilson(counts["DOWN"], n),
    }


def bar_color_baseline(bars, mask, start, stop):
    """UU means last two closed UP, including longer runs; flats stay in n."""
    table = {b["ts"]: b for b in bars}

    def color(left):
        group = [table.get(t) for t in range(left, left + 600, 60)]
        if not all(b is not None and b[mask] for b in group):
            return None
        delta = group[-1]["close"] - group[0]["open"]
        return "UP" if delta > 0 else "DOWN" if delta < 0 else "FLAT"

    all_colors, uu_colors, records = [], [], []
    for stamp in range(((start + 599) // 600) * 600, stop, 600):
        current = color(stamp)
        if current is None:
            continue
        all_colors.append(current)
        if color(stamp - 600) == "UP" and color(stamp - 1200) == "UP":
            uu_colors.append(current)
            records.append({"current_start": stamp, "color": current})
    return {
        "mask": mask,
        "unconditional": rate_summary(all_colors),
        "after_two_up": rate_summary(uu_colors),
        "uu_events": records,
    }


def unconditional_endpoint(bars, mask, start, stop, horizon):
    table = {b["ts"]: b for b in bars}
    colors = []
    for stamp in range(start, stop, 60):
        prior = table.get(stamp - 60)
        future = [table.get(t) for t in range(stamp, stamp + horizon * 60, 60)]
        if prior is None or not prior[mask] or not all(b and b[mask] for b in future):
            continue
        delta = future[-1]["close"] - prior["close"]
        colors.append("UP" if delta > 0 else "DOWN" if delta < 0 else "FLAT")
    return {"mask": mask, "horizon_minutes": horizon, **rate_summary(colors)}


def analyze(source):
    bars = dense_bars(source)
    table = {b["ts"]: b for b in bars}
    start, stop = source["study_start"], source["study_end_exclusive"]
    if not source["input_start"] <= start < stop <= source["input_end_exclusive"]:
        raise ValueError("study_window_outside_input")
    result = {
        "schema": "crosscoin-reversal-result/v1",
        "input": {
            k: source[k]
            for k in (
                "coin",
                "venue",
                "quote",
                "product",
                "clock",
                "source_url",
                "study_start",
                "study_end_exclusive",
                "input_start",
                "input_end_exclusive",
                "gap_telemetry",
            )
        },
        "source_decoded_sha256": digest(canonical(source).encode()),
        "coverage": {
            "expected_minutes": len(bars),
            "present_minutes": sum(b["present"] for b in bars),
            "positive_volume_minutes": sum(b["active"] for b in bars),
            "zero_volume_minutes": sum(b["present"] and not b["active"] for b in bars),
        },
        "methods": {
            "setup_minutes": 10,
            "policies": POLICIES,
            "cohorts": ["after_one_up", "after_two_up"],
            "horizons": HORIZONS,
            "event_window": "current10m start in half-open study window",
            "mask_active": "all required minutes must have positive volume",
            "gap_telemetry": "none; candle completeness is not tick-feed continuity",
            "costs": "none; excursions and sign counts, not trading P&L",
            "event_id_scope": "IDs are local to this coin, venue, quote and source_decoded_sha256",
            "amount_units": "Legacy *_usd fields use input.quote units per coin; percent fields use percent points",
        },
        "selection_counts": [],
        "summaries": [],
        "events": [],
        "bar_colors": [],
        "unconditional_endpoint": [],
    }
    for mask in MASKS:
        result["bar_colors"].append(bar_color_baseline(bars, mask, start, stop))
        result["unconditional_endpoint"].extend(
            unconditional_endpoint(bars, mask, start, stop, h) for h in HORIZONS
        )
        for policy in POLICIES:
            candidates, counts = events_for(bars, mask, policy)
            events = [e for e in candidates if start <= e["current_start"] < stop]
            result["selection_counts"].append(
                {
                    "mask": mask,
                    "policy": policy,
                    "input_scan_counts": counts,
                    "events_in_study_window": len(events),
                }
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
                        row = {
                            "mask": mask,
                            "policy": policy,
                            "cohort": cohort,
                            **aggregate(selected, table, horizon, nonoverlap),
                        }
                        for stats in row["references"].values():
                            stats["continuation_wilson95_descriptive"] = wilson(
                                stats["continued_down"], stats["n"]
                            )
                        result["summaries"].append(row)
    return result


def report(results):
    lines = [
        "# Ten-minute UP-bar reversals across coins",
        "",
        "Descriptive replication with fixed ZEC definitions. Each row uses native one-minute OHLCV.",
        "A DOWN endpoint means the price ten minutes after the signal close is lower than that close.",
        "Maximum favorable excursion (MFE) is the largest later fall from the reference price; it is not an attainable profit.",
        "",
        "## Midpoint rule: first eligible below-open one-minute close at minutes 5–9",
        "",
        "| Venue / period | Coin | Setup | Lower after 10m | Mean MFE | Maximum MFE | Mean endpoint decline |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for result in results:
        info = result["input"]
        for row in result["summaries"]:
            if (
                row["mask"],
                row["policy"],
                row["horizon_minutes"],
                row["overlap_policy"],
            ) != ("present", "midpoint", 10, "all"):
                continue
            s = row["references"]["signal_close"]
            label = (
                "one UP / bar 2" if row["cohort"] == "after_one_up" else "UU / bar 3"
            )
            values = [
                s[k][p]
                for k, p in (
                    ("down_pct", "mean"),
                    ("down_pct", "maximum"),
                    ("endpoint_decline_pct", "mean"),
                )
            ]
            formatted = [f"{v:.4f}%" if v is not None else "n/a" for v in values]
            rate = f"{100 * s['continuation_rate']:.1f}%" if s["n"] else "n/a"
            lines.append(
                f"| {info['venue']} / {iso(info['study_start'])[:10]} | {info['coin']} | {label} | "
                f"{s['continued_down']}/{s['n']} ({rate}) | "
                + " | ".join(formatted)
                + " |"
            )
    lines.extend(
        [
            "",
            "## Completed UU setup: next ten-minute candle color",
            "",
            "This is the original two-completed-UP-bars question. It does not require an intrabar reversal.",
            "| Venue | Coin | Next DOWN after UU | Unconditional DOWN | Flat next bars after UU |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for r in results:
        row = next(x for x in r["bar_colors"] if x["mask"] == "present")
        s, baseline = row["after_two_up"], row["unconditional"]
        p = f"{100 * s['down_rate']:.1f}%" if s["n"] else "n/a"
        b = f"{100 * baseline['down_rate']:.1f}%" if baseline["n"] else "n/a"
        lines.append(
            f"| {r['input']['venue']} | {r['input']['coin']} | {s['DOWN']}/{s['n']} ({p}) | "
            f"{baseline['DOWN']}/{baseline['n']} ({b}) | {s['FLAT']} |"
        )
    lines.extend(
        [
            "",
            "## Coverage and qualifications",
            "",
            "| Venue | Coin | Study window, UTC (end exclusive) | Input present / expected minutes (includes buffers) | Zero volume |",
            "|---|---|---|---:|---:|",
        ]
    )
    for r in results:
        i, c = r["input"], r["coverage"]
        lines.append(
            f"| {i['venue']} {i['quote']} | {i['coin']} | {iso(i['study_start'])} to "
            f"{iso(i['study_end_exclusive'])} | {c['present_minutes']}/{c['expected_minutes']} | "
            f"{c['zero_volume_minutes']} |"
        )
    lines.extend(
        [
            "",
            "- KuCoin uses USDC, Coinbase uses USD. Their periods differ. Do not pool them.",
            "- Legacy *_usd numeric fields mean quote currency per coin: USDC for KuCoin and USD for Coinbase. Event IDs must be read with their coin, venue, quote and source hash. Positive endpoint decline means a fall; negative means a rise.",
            (
                "- Explicit zero-volume provider rows remain visible. Missing minutes are never filled. "
                "The complete positive-volume sensitivity is archived separately for every setup and outcome. "
                "Future positive-volume eligibility is known retrospectively and cannot serve as an entry filter."
            ),
            (
                "- The original ZEC study uses receipt-time trades. These histories use exchange-time candles; "
                "a candle-complete history does not establish the original tick-feed gap screening."
            ),
            (
                "- Primary intrabar checks minutes 1–9; midpoint checks 5–9; close confirmation checks minute 10. "
                "A midpoint trigger may have first crossed below the open before minute 5."
            ),
            (
                "- One UP means the previous bar is UP and the older bar is not UP. UU means the last two "
                "closed bars are UP, including longer runs. There is no DOWN/DOWN/UP signal."
            ),
            (
                "- Each signal uses only already closed one-minute observations. Subsequent excursions exclude "
                "the signal minute. Five, ten and twenty minute outcomes, next-minute-open references and "
                "non-overlapping windows are retained. Overlap reservation occurs before checking future coverage."
            ),
            (
                "- Flat endpoints stay in denominators. Endpoint DOWN, any lower low, and candle color "
                "answer different questions. MFE maxima are historical observations with event IDs, not targets."
            ),
            (
                "- Descriptive Wilson intervals ignore temporal dependence. Events across policies, masks "
                "and nearby windows are not independent opportunities. No dates or parameters were selected "
                "by performance; this remains exploratory and has no prospective validation."
            ),
            (
                "- There are no executable fills, spread/slippage/fee estimates or net profit here. "
                "These findings do not qualify any coin or strategy for live orders."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="+")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    results = [analyze(read_archive(p)) for p in args.source]
    if args.report:
        print(report(results), end="")
    else:
        print(
            canonical(
                {
                    **pack(results),
                    "summaries": [
                        {
                            "input": r["input"],
                            "coverage": r["coverage"],
                            "bar_colors": r["bar_colors"],
                            "midpoint10": [
                                s
                                for s in r["summaries"]
                                if s["policy"] == "midpoint"
                                and s["horizon_minutes"] == 10
                                and s["overlap_policy"] == "all"
                            ],
                        }
                        for r in results
                    ],
                }
            )
        )


if __name__ == "__main__":
    main()
