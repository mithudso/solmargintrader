"""Derive the readable report and fixed examples from native second-turn results."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from research.reversal_history import read_archive
from research.reversal_second_turn import aggregate


def iso(stamp):
    return datetime.fromtimestamp(stamp, UTC).isoformat().replace("+00:00", "Z")


def fraction(m, field="hits"):
    return (
        f"{m[field]}/{m['n']} ({100 * m[field] / m['n']:.1f}%)"
        if m["n"]
        else "unavailable"
    )


def baseline_rows(result, stage):
    return [
        r
        for r in result["candidate_rows"]
        if r["basis"] == "oracle_signal"
        and r["stage"] == stage
        and r["condition"] == "all"
    ]


def lifts(result):
    baselines = {
        (r["basis"], r["stage"], r["minutes"]): r
        for r in result["candidate_rows"]
        if r["condition"] == "all"
    }
    out = []
    for r in result["candidate_rows"]:
        base = baselines[r["basis"], r["stage"], r["minutes"]]
        changes = {
            s: r["splits"][s]["direction_rate"] - base["splits"][s]["direction_rate"]
            if r["splits"][s]["n"] and base["splits"][s]["n"]
            else None
            for s in ("train", "validation", "test")
        }
        out.append(
            {
                "id": r["id"],
                "direction_lift": changes,
                "positive_all_three": all(
                    v is not None and v > 0 for v in changes.values()
                ),
            }
        )
    return out


def examples(result):
    out = []
    for stage in ("first_down", "second_up"):
        rows = sorted(
            [
                e
                for e in result["events"]
                if e["basis"] == "oracle_signal"
                and e["stage"] == stage
                and e["split"] == "test"
            ],
            key=lambda e: (e["signal_at"], e["minutes"]),
        )
        for name, crossed in (
            ("correct_and_survived", False),
            ("correct_but_liquidated", True),
        ):
            out.extend(
                [
                    {**e, "example_class": name}
                    for e in rows
                    if e["hit"] and e["crossed"]["9.8"] == crossed
                ][:3]
            )
    return out


def report(results):
    lines = [
        "# First reversal, second reversal and 1000x liquidation path",
        "",
        "A correct closing direction does not establish a surviving 1000x trade. The tables below require the entire holding bar to stay inside the modeled liquidation boundary. No stop-loss or take-profit is assumed; exit is at the target bar's close.",
        "",
        "The first decision is SHORT after two completed UP bars. The second is LONG only after UP–UP–DOWN has completed. Each uses information available at its own entry. A DOWN bar's wick or indicator value is unavailable when forecasting that same DOWN bar.",
        "",
        "## Price path and liquidation",
        "",
        "The main results use Jupiter's historical fixed_rate@200ms oracle OHLC for both signals and outcomes. Each asset has 41,680 complete minutes in 14 exact pages. Independent first-minute BTC and ZEC sample checks reproduced those oracle highs/lows from 300 consecutive 200 ms observations. These probes do not certify every historical update consumed by the keeper.",
        "",
        "The official client reserves the close fee: F=min(M,floor(N×20/1000000)). A long is liquidatable when N×(entry−price)≥(M−F)×entry; the short uses price−entry. At 1000x and the current 20 ppm close fee, the modeled adverse boundary is 9.8 bps (0.098%). Touching it counts. Historical fee settings, actual fills, latency and keeper/on-chain equivalence remain unverified. Sensitivities at 5/7.5/10 bps are retained in the full results.",
        "",
        "The client also has a nonlinear favorable-payout curve, a 0.2 bps favorable dead zone and profit fees. This study does not multiply spot returns by 1000 or claim executable P&L.",
        "",
        "## Unfiltered final-split results",
        "",
        "Joint means the direction was correct AND the 9.8 bps barrier was never touched during that complete target bar. All setups, including failures and flats, stay in the denominator.",
        "",
        "| Asset | Entry setup | Minutes | Direction correct | Correct and survived | Correct but liquidated |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in results:
        for stage in ("first_down", "second_up"):
            for r in baseline_rows(result, stage):
                m = r["splits"]["test"]
                lines.append(
                    f"| {result['coin']} | {'UU → SHORT' if stage == 'first_down' else 'UUD → LONG'} | {r['minutes']} | {fraction(m)} | {fraction(m, 'joint')} | {m['correct_but_liquidated']} |"
                )
    lines += [
        "",
        "Longer bars expose a position to more adverse movement before the fixed exit. A later favorable close cannot recover a position already liquidated. These conditional rates are not a prospective accuracy or profit guarantee.",
        "",
        "## What the frozen validation selector chose",
        "",
        "Each asset has 408 predeclared interval/condition/basis candidates. Eligibility is training ≥40 and validation ≥20. Ranking uses the validation Wilson lower bound for JOINT success, then sample count and stable ID. Final-split results never rerank these choices. All of these histories were already studied, so the entire extension remains exploratory and retrospective.",
        "",
        "| Asset | Oracle signal gate | Validation direction | Validation joint | Final direction | Final joint |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in results:
        for r in result["selected"]:
            if r["basis"] != "oracle_signal" or not r["id"]:
                continue
            v, t = r["splits"]["validation"], r["splits"]["test"]
            lines.append(
                f"| {result['coin']} | {r['stage']} {r['minutes']}m / {r['condition']} | {fraction(v)} | {fraction(v, 'joint')} | {fraction(t)} | {fraction(t, 'joint')} |"
            )
    lines += [
        "",
        "## Correlates worth observing prospectively",
        "",
        "The following is a POST-HOC descriptive screen, not a new validated strategy selection. It requires positive directional lift over the same-interval baseline in train, validation and final splits, with training ≥40 and both later splits≥20. Rows are ordered by the minimum lift across those splits; only two per asset/stage are printed. This screen uses final outcomes, has many comparisons, and cannot qualify a forward winner.",
        "",
        "| Asset | Stage | Minutes / gate | Train direction | Validation direction | Final direction | Final lift pp | Final joint |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lift_map = {r["id"]: r for r in lifts(result)}
        for stage in ("first_down", "second_up"):
            rows = [
                r
                for r in result["candidate_rows"]
                if r["basis"] == "oracle_signal"
                and r["stage"] == stage
                and r["condition"] != "all"
                and r["splits"]["train"]["n"] >= 40
                and min(r["splits"][s]["n"] for s in ("validation", "test")) >= 20
                and lift_map[r["id"]]["positive_all_three"]
            ]
            rows.sort(
                key=lambda r: (
                    -min(lift_map[r["id"]]["direction_lift"].values()),
                    r["id"],
                )
            )
            for r in rows[:2]:
                a, v, t = (r["splits"][s] for s in ("train", "validation", "test"))
                lines.append(
                    f"| {result['coin']} | {stage} | {r['minutes']} / {r['condition']} | {fraction(a)} | {fraction(v)} | {fraction(t)} | {100 * lift_map[r['id']]['direction_lift']['test']:+.2f} | {fraction(t, 'joint')} |"
                )
    lines += [
        "",
        "Gate definitions: close_high/close_low mean the completed signal bar closes in its top/bottom quarter. Wick gates require at least 35% of that bar's range. RSI high is ≥60. Rising/falling/range use 48 completed bars. EMA direction compares EMA 12/26; MACD improving/weakening compares its 12/26/9 histogram with the previous completed bar. A shallow pullback's DOWN body is ≤half the two preceding UP bodies combined.",
        "",
        "For the first reversal, test rejection/extension and regime together; a strong UP close can correlate with a later DOWN bar without making its adverse wick safe. For the second reversal, a rising regime, pullback depth, wick geometry and momentum change are separate causal hypotheses. The familiar uptrend-plus-shallow-pullback story is not assumed successful: its complete cells remain in the archive even when it fails. Full point-biserial feature correlations and successful/failed feature means are retained for every split.",
        "",
        "Oracle volume semantics are unqualified and volume features are unavailable in the primary study. The diagnostic spot_signal basis uses Binance pattern/indicator/volume inputs but still executes and scores against the matched oracle target bar; it has its own complete counts and frozen selections. No spot/oracle entry prices are mixed.",
        "",
        "## Detailed instances and charts",
        "",
        "Examples below are the first three correct survivors and first three correct-but-liquidated events per asset/stage in the final split, sorted by entry time then interval. They were not selected for largest profits. The four charts show the first example of each class and use indicators only through entry.",
        "",
        "| Asset | Stage | UTC entry | Minutes | Class | Oracle entry | Oracle high | Oracle low | Oracle close | Adverse bps |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        for e in examples(result):
            _, o, h, low, c, _ = e["target_ohlcv"]
            lines.append(
                f"| {result['coin']} | {e['stage']} | {iso(e['signal_at'])} | {e['minutes']} | {e['example_class']} | {o:.8f} | {h:.8f} | {low:.8f} | {c:.8f} | {e['adverse_bps']:.3f} |"
            )
    for result in results:
        for stage in ("first_down", "second_up"):
            lines += [
                "",
                f"![{result['coin']} {stage}: complete adverse path](second-turn-20261116/{result['coin']}-{stage}.svg)",
            ]
    lines += [
        "",
        "## Evidence and forward use",
        "",
        "Full native inputs, all 24,480 events, all 816 candidate rows, all split metrics, source pages, causal features and numerical audit bindings are listed in second-turn-20261116/manifest.json. Each rate is descriptive: overlapping setups, serial dependence and multiple comparisons are not corrected by the Wilson intervals.",
        "",
        "The existing live paper selection stays frozen. These new oracle/second-turn hypotheses need a separately frozen prospective test before becoming a claimed improvement. A future entry's actual oracle fill, exact liquidation threshold and observed adverse path must be recorded; no heuristic can promise that its price will never cross liquidation.",
        "",
    ]
    return "\n".join(lines)


def figures(result, oracle, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    from matplotlib.patches import Rectangle

    plt.rcParams["svg.hashsalt"] = "second-turn-v1"
    for stage in ("first_down", "second_up"):
        chosen = [
            next(
                e
                for e in examples(result)
                if e["stage"] == stage and e["example_class"] == label
            )
            for label in ("correct_and_survived", "correct_but_liquidated")
        ]
        fig, axes = plt.subplots(
            2, 2, figsize=(13, 7), gridspec_kw={"height_ratios": [3, 1]}
        )
        for col, e in enumerate(chosen):
            bars = aggregate(oracle["rows"], e["minutes"], require_volume=False)
            idx = next(i for i, b in enumerate(bars) if b[0] == e["signal_at"])
            start = max(0, idx - 12)
            window = bars[start : idx + 1]
            ax, lower = axes[0, col], axes[1, col]
            for j, b in enumerate(window):
                _, o, h, low, c, _ = b
                color = "#16856b" if c >= o else "#cf4b52"
                ax.vlines(j, low, h, color=color, linewidth=1)
                ax.add_patch(
                    Rectangle(
                        (j - 0.3, min(o, c)),
                        0.6,
                        max(abs(c - o), (h - low) * 0.01),
                        color=color,
                    )
                )
            close = pd.Series([b[4] for b in bars[:idx]])
            ema12, ema26 = (
                close.ewm(span=12, adjust=False).mean(),
                close.ewm(span=26, adjust=False).mean(),
            )
            macd = ema12 - ema26
            hist = macd - macd.ewm(span=9, adjust=False).mean()
            xs = range(len(window) - 1)
            ax.plot(
                xs,
                ema12.iloc[start:].values,
                label="EMA12 through signal",
                color="#4169b5",
                linewidth=1,
            )
            ax.plot(
                xs,
                ema26.iloc[start:].values,
                label="EMA26 through signal",
                color="#b27d25",
                linewidth=1,
            )
            lower.bar(xs, hist.iloc[start:].values, color="#657b98")
            target_x = len(window) - 1
            entry = e["target_ohlcv"][1]
            liquidation = entry * (
                1 - 0.00098 if e["direction"] == "UP" else 1 + 0.00098
            )
            ax.axvspan(target_x - 0.5, target_x + 0.5, color="#ccd8e7", alpha=0.4)
            ax.hlines(
                entry,
                target_x - 0.5,
                target_x + 0.5,
                colors="#233445",
                linestyles="dotted",
                label="Modeled entry",
            )
            ax.hlines(
                liquidation,
                target_x - 0.5,
                target_x + 0.5,
                colors="#b61939",
                linestyles="dashed",
                label="9.8bps liquidation",
            )
            ax.set_title(
                e["example_class"].replace("_", " ")
                + f"\n{iso(e['signal_at'])}, {e['minutes']}m"
            )
            ax.set_ylabel("Oracle USD price")
            lower.set_ylabel("MACD hist")
            lower.set_xticks(
                range(0, len(window), 3),
                [
                    datetime.fromtimestamp(window[j][0], UTC).strftime("%H:%M")
                    for j in range(0, len(window), 3)
                ],
            )
            lower.set_xlabel("UTC; shaded final price bar is the held target")
            for chart in (ax, lower):
                chart.set_xlim(-0.7, target_x + 0.7)
                chart.grid(alpha=0.2)
            ax.legend(fontsize=7, loc="best")
        fig.suptitle(
            f"{result['coin']} / {stage}: correct close versus full-path survival\nOracle-OHLC proxy; fixed time exit, no stop-loss/take-profit; historical fees/fills unverified"
        )
        fig.tight_layout()
        fig.savefig(output / f"{result['coin']}-{stage}.svg", metadata={"Date": None})
        fig.savefig(output / f"{result['coin']}-{stage}.png", dpi=120)
        plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", choices=("v1", "v2"), default="v2")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.revision == "v1" else "-v2"
    results = [
        read_archive(args.transport / f"{coin}-second-turn-results{suffix}.json")
        for coin in ("ZEC", "BTC")
    ]
    for r in results:
        figures(
            r,
            read_archive(args.transport / f"{r['coin']}-oracle-source.json"),
            args.output,
        )
    (args.output / "derived-details.json").write_text(
        json.dumps(
            {r["coin"]: {"lifts": lifts(r), "examples": examples(r)} for r in results},
            indent=2,
        )
        + "\n"
    )
    print(report(results))


if __name__ == "__main__":
    main()
