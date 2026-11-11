"""Verify shape-study evidence and render its measured tables without hand edits."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from research.shape_study import PAIRS, SINGLES, digest


def table(frame):
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    rule = "| " + " | ".join("---" for _ in frame.columns) + " |"
    lines = [header, rule]
    for row in frame.itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(f"{x:.2f}" if isinstance(x, float) else str(x) for x in row)
            + " |"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = json.loads((args.run / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("study did not complete")
    if digest(args.repo / "research/shape_study.py") != manifest["source_sha256"]:
        raise ValueError("runner differs from completed evidence")
    for name, expected in manifest["artifacts"].items():
        if digest(args.run / name) != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
    for name, expected in manifest["code_sha256"].items():
        if digest(args.repo / name) != expected:
            raise ValueError(f"accounting/strategy source mismatch: {name}")
    data = pd.read_csv(args.run / "summary.csv")
    if data.duplicated(["asset", "interval", "scenario", "policy"]).any():
        raise ValueError("duplicate summary cells")
    comparisons, ranks = [], []
    for (asset, interval, scenario), group in data.groupby(
        ["asset", "interval", "scenario"]
    ):
        curves = pd.read_csv(args.run / f"{asset}_{interval}_{scenario}_equity.csv.gz")
        by_policy = group.set_index("policy")
        for policy, row in by_policy.iterrows():
            np.testing.assert_allclose(
                (curves[policy].iloc[-1] / 10000 - 1) * 100, row.return_pct, atol=1e-9
            )
        nulls = by_policy.loc[[f"null_shape_{seed}" for seed in range(5)], "return_pct"]
        for policy in ("shape_router", "shape_zone_router", "rule_shape"):
            result = by_policy.loc[policy]
            comparisons.append(
                {
                    "asset": asset,
                    "interval": interval,
                    "scenario": scenario,
                    "policy": policy,
                    "return_pct": result.return_pct,
                    "vs_fixed_pp": result.return_pct
                    - by_policy.loc["selected_fixed"].return_pct,
                    "vs_hold_pp": result.return_pct
                    - by_policy.loc["buy_hold"].return_pct,
                    "null_median_pct": float(nulls.median()),
                    "beats_all_five_nulls": bool(result.return_pct > nulls.max()),
                }
            )
        ranks.append(
            {
                "asset": asset,
                "interval": interval,
                "scenario": scenario,
                "passive_pct": by_policy.loc["buy_hold"].return_pct,
                "fixed_pct": by_policy.loc["selected_fixed"].return_pct,
                "shape_pct": by_policy.loc["shape_router"].return_pct,
                "zone_pct": by_policy.loc["shape_zone_router"].return_pct,
            }
        )
    comparison = pd.DataFrame(comparisons)
    ranking = pd.DataFrame(ranks)
    attr = pd.read_csv(args.run / "by_shape.csv")
    # Conditional arithmetic means are bar-weighted; this is P&L attribution,
    # never an isolated strategy that magically enters at a known regime boundary.
    attr["weighted_bps"] = attr.mean_next_bar_bps * attr.bars
    conditional = attr.groupby(
        ["asset", "interval", "scenario", "policy", "shape"], as_index=False
    ).agg(
        bars=("bars", "sum"),
        episodes=("episodes", "sum"),
        weighted_bps=("weighted_bps", "sum"),
        log_return_sum=("log_return_sum", "sum"),
    )
    conditional["inside_bps"] = conditional.weighted_bps / conditional.bars
    totals = conditional.groupby(["asset", "interval", "scenario", "policy"])[
        ["weighted_bps", "bars"]
    ].transform("sum")
    conditional["outside_bps"] = (totals.weighted_bps - conditional.weighted_bps) / (
        totals.bars - conditional.bars
    )
    conditional["inside_minus_outside_bps"] = (
        conditional.inside_bps - conditional.outside_bps
    )
    prefix = args.repo / "research/results/shape_spot_20261111"
    data.to_csv(str(prefix) + "_summary.csv", index=False)
    comparison.to_csv(str(prefix) + "_comparisons.csv", index=False)
    conditional.to_csv(
        str(prefix) + "_conditional.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    for src, suffix in (
        ("manifest.json", "manifest.json"),
        ("latest_historical_shapes.json", "snapshots.json"),
    ):
        shutil.copyfile(args.run / src, str(prefix) + "_" + suffix)
    text = """# Shape-aware spot study

As of 2026-11-11. Historical research only. The detector and results establish no live trading edge.
All return tables are percentages on an initial $10,000 spot account, with no borrowing or shorting.

The practical result is mixed: use shape routing as a research candidate, not an established edge.
At zero commission and 2 bps execution per side, hourly shape routing beats fixed selection on five
of eight coins and continuous holding on six. Adding range-position zones does worse. At 25 bps
execution per side, every hourly shape router loses money. ZEC leads passive returns, and shape
routing leaves substantial ZEC upside uncaptured. Lower commission helps; spread can erase the gain.

## What counts as a shape, and where are we within it?

The prior research found five conceptual families: order-book saddles, liquidity-void V reversals,
rounding bowls, compression wedges and topological persistence loops. Its quoted win rates, Sharpe
deltas, profit factor and drawdown reductions failed independent source review. Two bowl citations
were copies of the same US equity overnight-drift paper. Those numbers are not used here.

This study measures **OHLC price-path proxies**. It cannot identify a true order-book saddle, establish
liquidation flow/VPIN, or compute persistent homology from an unimplemented proxy. Those three
mechanisms require additional observations or a separately implemented topological estimator.

| Observable state | Completed-bar rule, fixed before evaluating results | Position within the observed shape |
| --- | --- | --- |
| Up/down trend | Absolute net log move / sum absolute log moves >= 0.25 over 48 bars; net sign gives direction | Range position, direction, episode age |
| Range | Path efficiency < 0.25 | Lower/middle/upper third of the trailing high-low range |
| V rebound / inverted V | First half falls/rises > 2 rolling one-bar standard deviations; second half reverses > 2; range position confirms recovery | Fraction of observed drop recovered; only confirms after the turn |
| Bowl / cap | Quadratic fit of log closes, R² >= 0.80, normalized bend >= 0.15; fitted vertex in the interior | Fitted turn age, curvature sign, range position |
| Compression | Fitted high slope negative and low slope positive; end width 10–65% of start width | Position between current fitted bounds and extrapolated bars to apex |

Rules use 48 trailing completed candles. Priority is compression, bowl/cap, V/inverted V, then trend/range.
The first 47 bars are unknown. Shapes can overlap; priority assigns one primary label. R² is fit quality,
not the probability of profit. Episode age counts consecutive detected labels, not the true pattern start.
Range position and rebound fractions describe observed history, not the eventual lifecycle percentage.
An extrapolated wedge apex is a geometric estimate, not a forecast that a breakout must occur there.

Every tag has a candle timestamp and an `available_at` timestamp at its close. Decisions fill at the
following open. The saved interval files contain when each label became known, its last observed time,
bar count and start/end range position. Future poisoning and prefix replay tests prevent retroactive tags.

## Data and evaluation contract

Eight Coinbase USD markets: BTC, ETH, SOL, XRP, DOGE, ZEC, LINK and AVAX. Existing native Coinbase
hourly/daily caches supply seven assets. The explicit public fetch step obtained missing ZEC-USD
hourly and daily candles. Six-hour bars require all six hourly candles. No candle is interpolated.
Within each timeframe, every coin has exactly the same contiguous dates. The common suffix rule
trims gaps using timestamps, before seeing strategy returns. Different timeframe windows are not pooled.

The historical source pool was already explored in earlier studies. These are expanding chronological
walk-forward tests, not a new untouched final holdout. The run checks the existing holdout ledger in
read-only mode and refuses any overlap with unsealed protected dates. It does not overwrite reservations.

The first 40% trains selection; the next three 20% windows are disjoint tests. Canonical indicators
warm from prior history. Training starts after the longest 251-bar warmup and excludes two boundary
bars. Later folds may learn from earlier test windows once those windows are history. Each active
fold starts flat and pays its final exit; compound fold returns. `buy_hold` continuously holds across
all three test folds; `fold_reset_hold` supplies a separately named turnover-matched passive comparator.

Six canonical default singles: MACD, breakout, RSI, Bollinger reversion, OU reversion and ADX trend.
Three fixed half-weight exposure mixtures: MACD/RSI, breakout/OU and ADX/Bollinger. Mixtures rebalance
one shared account; they are not fictitious simultaneous full-capital books. The shape-free selector
chooses among these nine policies and cash by training net log return. The rule-based shape policy
uses MACD for rising trends/bowls, OU for ranges/V rebounds, breakout for compression, otherwise cash.

The learned shape router chooses a training-best arm per shape. The shape/zone router also conditions
on lower/middle/upper range position. A state needs 30 training bars and three observed episodes;
otherwise it uses the training-best shape-free arm. These floors do not imply independent samples.
Training scores attribute continuous-arm next-bar returns to the preceding shape. Actual routed replay
pays its own switching costs. Five fixed-seed permutations of **training labels only** provide a noise
diagnostic. They are not a calibrated significance test because shuffling removes serial dependence.

## Coinbase One and costs

Coinbase One waives commission on eligible simple trades within plan limits. A spread remains.
Coinbase Advanced is excluded; official terms also describe a 1% limit-execution exception. API access
for automated trading is part of Advanced. Therefore membership does not establish fee-free bot execution.
The zero-commission runs are conditional scenarios. Execution drag is 2, 10, 25 or 50 bps **per side**;
these are assumptions, not measured account quotes. A control charges 10 bps commission plus 2 bps
execution per side. Both entry and exit pay costs, including fold exits. Membership price, plan-cap
exhaustion, rebates, tax, order-size constraints, market impact and latency are not modeled. Turnover
is saved so the owner can compare it with the actual plan cap. Spot needs no borrow/funding model.

https://help.coinbase.com/en/coinbase/other-topics/coinbase-one/account
https://help.coinbase.com/en-gb/getting-started/other/coinbase-vs-coinbase-advanced

## Measured results

The tables below use zero commission and **2 bps execution per side** unless stated otherwise.
They are generated from checksum-bound curves, not copied from the geometry dossier.

"""
    for interval in manifest["intervals"]:
        subset = ranking[
            (ranking.interval == interval) & (ranking.scenario == "zero_2")
        ].sort_values("shape_pct", ascending=False)
        timing = data[(data.interval == interval) & (data.scenario == "zero_2")].iloc[0]
        start, end = (
            pd.to_datetime(timing[k], unit="s", utc=True).strftime("%Y-%m-%d %H:%M UTC")
            for k in ("test_start", "test_end")
        )
        text += f"### {interval}: {start} through {end}\n\n"
        text += (
            table(
                subset[["asset", "passive_pct", "fixed_pct", "shape_pct", "zone_pct"]]
            )
            + "\n\n"
        )
    counts = comparison.groupby(["interval", "scenario", "policy"], as_index=False).agg(
        beats_fixed=("vs_fixed_pp", lambda s: int((s > 0).sum())),
        beats_hold=("vs_hold_pp", lambda s: int((s > 0).sum())),
        beats_five_nulls=("beats_all_five_nulls", "sum"),
    )
    text += "### Does conditioning improve decisions?\n\nCounts are out of eight coins per row. Compare within each timeframe.\n\n"
    text += (
        table(
            counts[
                (counts.scenario == "zero_2") & (counts.policy != "rule_shape")
            ].drop(columns="scenario")
        )
        + "\n\n"
    )
    sensitivity = (
        data[(data.policy == "shape_router") & (data.interval == "1h")]
        .pivot(index="asset", columns="scenario", values="return_pct")
        .reset_index()
    )
    text += "### Hourly shape-router cost sensitivity\n\nColumn suffixes are execution bps per side. `fee10_exec2` additionally charges 10 bps commission per side.\n\n"
    text += table(sensitivity) + "\n\n"
    selected = conditional[
        (conditional.interval == "1h")
        & (conditional.scenario == "zero_2")
        & conditional.policy.isin([*SINGLES, *[f"mean_{a}_{b}" for a, b in PAIRS]])
    ]
    pooled = selected.groupby(["shape", "policy"], as_index=False).agg(
        bars=("bars", "sum"),
        episodes=("episodes", "sum"),
        weighted_bps=("weighted_bps", "sum"),
    )
    pooled["mean_bps"] = pooled.weighted_bps / pooled.bars
    examples = []
    for shape, group in pooled.groupby("shape"):
        singles = group[group.policy.isin(SINGLES)]
        mixtures = group[~group.policy.isin(SINGLES)]
        single = singles.loc[singles.mean_bps.idxmax()]
        mixture = mixtures.loc[mixtures.mean_bps.idxmax()]
        examples.append(
            {
                "shape": shape,
                "best_single": single.policy,
                "single_bps": single.mean_bps,
                "best_mixture": mixture.policy,
                "mixture_bps": mixture.mean_bps,
                "bars_per_policy": int(single.bars),
            }
        )
    text += "### Which policies behaved better inside each hourly shape?\n\n"
    text += "Descriptive, hindsight-ranked **next-bar P&L attribution**, pooled across eight correlated coins. These are not trade returns or recommendations. Bars overlap in their 48-bar detection windows.\n\n"
    text += table(pd.DataFrame(examples)) + "\n\n"
    text += """Full conditional results include per-coin inside/outside mean bps, bar/episode counts and log-return contributions.
Positions can predate a label change. Neither a conditional mean nor the best hindsight row establishes a causal effect.
The strategy/coin/timeframe/cost search is extensive; there is no multiplicity-adjusted significance claim.
The six-hour training segment after warmup is especially small. No shape router consistently wins across all assets.
Adding position zones increases selection complexity and can reduce performance. A favorable zero-fee result does
not prove membership offsets leverage; removing commission changes costs, while leverage/shorting change exposure.

## Which coins were profitable again?

The older common-window minute study's passive leaders were **ZEC +145.7537%** and **HYPE +74.6592%**
(February–August 2026). Its positive active VWAP-reversion cells included **DOGE +17.8762%**, **SOL +3.8742%**
and **ETH +0.1807%**. That single-pass minute sweep had gaps and no held-out selection.
The daily CPCV breadth leaders were **BTC 24/24 rankable singles positive** and **ZEC 24/25**, followed by
ETH 18/24, DOGE 16/25 and SOL 13/25. Breadth of positive median Sharpe is not a return ranking.
The recent ZEC Volty daily adaptive study earned **+22.688%**, versus **+1783.710% passive**; every fixed
training winner lost out of sample. These are different experiments, not interchangeable coin league tables.

For this study, read the within-timeframe tables above: ZEC is the strongest passive coin in each tested
window. Shape routing can improve some other coins while giving up part of ZEC's buy-and-hold gain.
None of these rankings establishes the most profitable coin for the next period.

## Reproduction and artifacts

The runner never places orders or changes installed Oracle/paper policies. All raw input hashes, canonical
engine/strategy hashes, versions, windows, scenarios and output hashes are in the committed manifest.
Full bars, tags, shape intervals, per-bar decisions, selections and equity curves live in the run folder.
The compact committed results retain all policy returns, conditional inside/outside attribution and snapshots.
Snapshots describe the final **historical** candle, not the live market.

The source taxonomy is `/Users/mitch/.global-ai-hub/research/market-graph-geometry/dossier.md`,
with related claim and strategy-matrix files in that directory. Historical comparison sources are
`research/CROSS-ASSET-TRANSFER.md`, `research/results/minute_sweep_x1_common.csv` and
`docs/VOLTY-ZEC-STUDY.md`. The corrected evidence verdict is in Stele KNOW-1277; study task TASK-1296.

```bash
python -m unittest research.tests.test_shape_study -v
python -m research.shape_study --data-dir /Users/mitch/dev/solmargintrader/data --zec-dir /Users/mitch/.local/share/solmargintrader/research/shape-spot-20261111/input --output /Users/mitch/.local/share/solmargintrader/research/shape-spot-20261111/reproduction
```

Use a fresh output directory. The runner refuses to overwrite completed evidence.
The exact primary run is `/Users/mitch/.local/share/solmargintrader/research/shape-spot-20261111/run-v3`.
Prior exploratory runs are retained separately and do not certify the final source.
"""
    (args.repo / "research/SHAPE-AWARE-SPOT.md").write_text(text)
    print(
        f"Verified {len(manifest['artifacts'])} artifacts and {len(data)} policy cells; report generated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
