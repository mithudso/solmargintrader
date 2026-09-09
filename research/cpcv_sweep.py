"""CPCV sweep: replaces the single 70/30 split with a distribution of paths.

    python3 research/cpcv_sweep.py
    python3 research/cpcv_sweep.py --horizon medium --groups 8 --k 2

Why this exists: a single 70/30 split on SOL ends its in-sample window on the
highest close in the whole series, so one split conflates "is this strategy any
good" with "which regime landed in the test set". C(N,k) paths sample many
regime mixes and produce a distribution instead of a point estimate.

Reports per configuration: median path Sharpe, interquartile spread, fraction of
paths positive, and the per-block Sharpe series. Then computes **PBO** across the
configuration set -- the probability that the in-sample winner ranks below median
out-of-sample. PBO is the number that actually answers "is the top-ranked row
real?", which the single-split sweep could not answer at all.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import cpcv_evaluate, pbo_cscv  # noqa: E402
from backtester.core.strategies import FAMILY, build, build_composite  # noqa: E402
from research.sweep import (  # noqa: E402
    COMBO_CANDIDATES,
    HORIZONS,
    PAIR_GATES,
    independent_combos,
    load_horizon,
)

OUT = REPO / "research" / "results"

# ---------------------------------------------------------------------------
# Self-explaining output
#
# Every number this script prints is easy to misread, and two of the misreadings
# are actively dangerous ("83 positive" sounds like 83 working strategies; a low
# PBO sounds like good news). The legend and per-line interpretation below print
# WITH the results by default so the numbers cannot travel without their meaning.
# Pass --quiet for bare output in scripts.
# ---------------------------------------------------------------------------

LEGEND = """\
────────────────────────────────────────────────────────────────────────────────
HOW TO READ THIS OUTPUT
────────────────────────────────────────────────────────────────────────────────
Each line is one CPCV sweep. CPCV = combinatorial purged cross-validation: the
price series is cut into N contiguous blocks, and every combination of k blocks
forms one out-of-sample "path". With 8 blocks and k=2 that is 28 paths per
configuration, instead of the single arbitrary train/test split it replaces.

  "129/140 evaluable"
      140 cross-family combinations were generated (same-family combos are
      skipped -- two trend signals mostly measure the same thing twice). 11 were
      DROPPED, not zeroed: a combination is unevaluable when its slowest member
      needs more warm-up bars than precede a block, or when it produced fewer
      than MIN_OOS_TRADES across all blocks. Dropping loudly beats reporting a
      confident number built on 3 trades.

  "2 with positive median Sharpe"
      Of the 28 paths per configuration, the MEDIAN path's Sharpe is positive.
      This is NOT "2 profitable strategies". A positive median with a wide
      interquartile spread still straddles zero -- read the IQR column in
      results/cpcv_combos_tables.md before believing any single row.

  "PBO 0.371"
      Probability of Backtest Overfitting (Bailey et al., via CSCV): the fraction
      of train/test splits where the configuration that looked BEST in-sample
      landed BELOW MEDIAN out-of-sample.

      PBO scale, calibrated against constructed controls in the test suite
      (backtester/tests/test_cpcv.py):

          0.00  in-sample rank predicts out-of-sample rank perfectly
          0.50  PURE NOISE -- measured mean over 30 seeds of random returns
          >0.50 ANTI-INFORMATIVE: picking the best in-sample performer is
                measurably WORSE than picking at random

      So PBO is the number that decides whether the ranking above it means
      anything. A high positive-count with a high PBO is the classic overfit
      signature: lots of things look good, and in-sample rank still cannot tell
      you which one will keep working.
────────────────────────────────────────────────────────────────────────────────"""

# PBO thresholds, named so the interpretation logic reads like the legend.
PBO_NOISE = 0.50
PBO_INFORMATIVE = 0.35
# Below this share of evaluable configs being positive, a low PBO is not good
# news -- it means the in-sample winner generalises reliably as a loser.
LOW_POSITIVE_SHARE = 0.25


def interpret(evaluable: int, total: int, positive: int, pbo: float) -> list[str]:
    """Plain-language reading of one sweep line. Pure function, so it is testable.

    Returns zero or more annotation lines. The important one is the trap: a LOW
    PBO alongside a LOW positive count looks like the best result on the page and
    is actually the worst, because PBO measures whether in-sample *rank*
    generalises, not whether anything is profitable. That condition is computed
    here rather than left to the reader to notice.
    """
    lines: list[str] = []
    if evaluable == 0:
        return ["      -> nothing evaluable; check warm-up lengths and trade floors"]

    share = positive / evaluable
    dropped = total - evaluable
    if dropped:
        lines.append(
            f"      -> {dropped} dropped for insufficient warm-up or too few trades "
            f"(not counted as zero)"
        )

    if pbo != pbo:  # NaN
        lines.append("      -> PBO unavailable: too few comparable configurations")
    elif pbo > PBO_NOISE:
        lines.append(
            f"      -> PBO {pbo:.3f} is ABOVE the 0.50 noise line: in-sample rank is "
            f"ANTI-informative here."
        )
        lines.append(
            f"         Picking the best of these {evaluable} in-sample is worse than "
            f"picking at random."
        )
        if share > 0.5:
            lines.append(
                f"         Note {positive}/{evaluable} ({share:.0%}) look positive while "
                f"rank fails -- the classic overfit signature."
            )
    elif pbo < PBO_INFORMATIVE and share < LOW_POSITIVE_SHARE:
        lines.append(
            f"      -> TRAP: PBO {pbo:.3f} looks excellent, but only {positive}/{evaluable} "
            f"({share:.0%}) are positive."
        )
        lines.append(
            "         Low PBO means in-sample rank GENERALISES -- here it generalises "
            "reliably as a loser."
        )
    elif pbo < PBO_INFORMATIVE:
        lines.append(
            f"      -> PBO {pbo:.3f} is below the noise line: in-sample rank carries "
            f"some signal. Still verify with a parameter-perturbation check."
        )
    else:
        lines.append(
            f"      -> PBO {pbo:.3f} sits near the 0.50 noise line: in-sample rank is "
            f"close to uninformative."
        )
    return lines

# Triples are drawn from this fixed a-priori set, one member per family, chosen
# for mechanical complementarity rather than for measured performance.
#
# Selecting triples from the top-N measured singles (as the single-split sweep
# did) borrows information from the very data used to evaluate them, which
# biases the result optimistically and had to be disclosed as a caveat. Fixing
# the candidate set up front removes that leak entirely: the combinations tested
# are decided before any CPCV number is seen.
TRIPLE_CANDIDATES = (
    "ma_crossover",     # trend
    "ts_momentum",      # momentum
    "sma_regime",       # regime filter
    "breakout",         # breakout
    "rsi",              # oscillator reversion
    "zscore",           # mean reversion
    "obv_trend",        # volume flow
)


def run_horizon(horizon: str, n_groups: int, k_test: int) -> tuple[pd.DataFrame, dict]:
    """CPCV-evaluate every single at one horizon, then compute PBO across them."""
    arrays, cfg = load_horizon(horizon)
    params = HORIZONS[horizon]["params"]
    rows: list[dict] = []
    # block index -> returns, per configuration. PBO needs every configuration
    # to expose the SAME blocks, so the common set is intersected afterwards
    # rather than requiring all n_groups: block 0 is never usable (nothing
    # precedes it to warm up from), so requiring all of them would silently
    # reduce PBO to the single warm-up-free strategy.
    per_config_blocks: dict[str, dict[int, np.ndarray]] = {}

    for name, p in params.items():
        label = build(name, **p).name
        res = cpcv_evaluate(
            label, lambda n=name, q=p: build(n, **q), arrays, cfg,
            n_groups=n_groups, k_test=k_test,
        )
        rows.append({
            "horizon": horizon,
            "strategy": name,
            "label": label,
            "family": FAMILY[name],
            "n_paths": res.n_paths,
            "usable_blocks": res.usable_blocks,
            "median_sharpe": res.median_sharpe,
            "q1_sharpe": res.q1_sharpe,
            "q3_sharpe": res.q3_sharpe,
            "iqr_spread": res.spread,
            "frac_paths_positive": res.frac_positive,
            "median_path_return": res.median_return,
            "total_trades": res.total_trades,
            "insufficient": res.insufficient,
            "reason": res.reason,
        })
        if not res.insufficient:
            per_config_blocks[label] = {
                b.index: b.returns for b in res.blocks if b.usable
            }

    # Intersect on block indices so every configuration contributes the same
    # blocks, then build equal-length lists in a stable order.
    common: set[int] = set()
    if per_config_blocks:
        common = set.intersection(*(set(d) for d in per_config_blocks.values()))
    order = sorted(common)
    block_returns = {
        label: [d[i] for i in order] for label, d in per_config_blocks.items()
    }

    pbo = (
        pbo_cscv(block_returns)
        if len(block_returns) >= 2 and len(order) >= 4
        else {
            "pbo": float("nan"),
            "n_splits": 0.0,
            "n_configs": float(len(block_returns)),
        }
    )
    pbo["horizon"] = horizon
    pbo["common_blocks"] = order
    pbo["configs_included"] = sorted(block_returns)
    return pd.DataFrame(rows), pbo


def run_combos(
    horizon: str,
    size: int,
    n_groups: int,
    k_test: int,
    modes: tuple[str, ...],
    candidates: tuple[str, ...],
    gate: str = "both",
) -> tuple[pd.DataFrame, dict]:
    """CPCV-evaluate non-redundant combinations of `size` members at one horizon.

    The gate is the one in `sweep.py`, so a combination the single-split sweep
    refuses to build is not silently resurrected here. PBO is a statement about
    the size and content of a search, so measuring it over a search that includes
    one signal counted twice measures the wrong search.
    """
    arrays, cfg = load_horizon(horizon)
    params = HORIZONS[horizon]["params"]
    usable = [n for n in candidates if n in params]
    rows: list[dict] = []
    per_config_blocks: dict[str, dict[int, np.ndarray]] = {}

    for combo in independent_combos(usable, size, horizon, gate):
        specs = [(n, params[n]) for n in combo]
        for mode in modes:
            label = f"{mode}({'+'.join(combo)})"
            res = cpcv_evaluate(
                label,
                lambda s=specs, m=mode: build_composite(list(s), mode=m),
                arrays, cfg, n_groups=n_groups, k_test=k_test,
            )
            rows.append({
                "horizon": horizon,
                "kind": {2: "pair", 3: "triple"}.get(size, f"n{size}"),
                "label": label,
                "mode": mode,
                "family": "+".join(FAMILY[n] for n in combo),
                "n_paths": res.n_paths,
                "usable_blocks": res.usable_blocks,
                "median_sharpe": res.median_sharpe,
                "q1_sharpe": res.q1_sharpe,
                "q3_sharpe": res.q3_sharpe,
                "iqr_spread": res.spread,
                "frac_paths_positive": res.frac_positive,
                "median_path_return": res.median_return,
                "total_trades": res.total_trades,
                "insufficient": res.insufficient,
                "reason": res.reason,
            })
            if not res.insufficient:
                per_config_blocks[label] = {
                    b.index: b.returns for b in res.blocks if b.usable
                }

    common: set[int] = set()
    if per_config_blocks:
        common = set.intersection(*(set(d) for d in per_config_blocks.values()))
    order = sorted(common)
    block_returns = {l: [d[i] for i in order] for l, d in per_config_blocks.items()}
    pbo = (
        pbo_cscv(block_returns)
        if len(block_returns) >= 2 and len(order) >= 4
        else {"pbo": float("nan"), "n_splits": 0.0, "n_configs": float(len(block_returns))}
    )
    pbo["horizon"] = horizon
    pbo["kind"] = {2: "pair", 3: "triple"}.get(size, f"n{size}")
    pbo["common_blocks"] = order
    return pd.DataFrame(rows), pbo


def main(argv: list[str] | None = None) -> int:
    """Run the CPCV sweep and write results."""
    ap = argparse.ArgumentParser(description="CPCV sweep for SOL strategies.")
    ap.add_argument("--horizon", action="append", choices=list(HORIZONS), default=None)
    ap.add_argument("--groups", type=int, default=8, help="number of CPCV blocks")
    ap.add_argument("--k", type=int, default=2, help="blocks per test path")
    ap.add_argument(
        "--stage", action="append", choices=["singles", "pairs", "triples"], default=None,
        help="which of List 1 / List 2 / List 3 to compute (default: all)",
    )
    ap.add_argument(
        "--quiet", action="store_true",
        help="suppress the how-to-read legend and per-line interpretation",
    )
    ap.add_argument(
        "--pair-gate", choices=list(PAIR_GATES), default="both",
        help="which redundancy test a combination must clear (default: both); "
             "'family' reproduces the pre-2026-08 published CPCV numbers",
    )
    args = ap.parse_args(argv)

    horizons = args.horizon or list(HORIZONS)
    stages = args.stage or ["singles", "pairs", "triples"]
    OUT.mkdir(parents=True, exist_ok=True)

    # Explanations are ON by default: these numbers are easy to misread, and the
    # two most likely misreadings are the dangerous ones.
    explain = not args.quiet
    if explain:
        print(LEGEND, file=sys.stderr)

    if "pairs" in stages or "triples" in stages:
        combo_frames, combo_pbos = [], []
        for h in horizons:
            if "pairs" in stages:
                print(f"[{h}] CPCV pairs…", file=sys.stderr)
                df, pbo = run_combos(
                    h, 2, args.groups, args.k, ("all", "any"), COMBO_CANDIDATES,
                    gate=args.pair_gate,
                )
                combo_frames.append(df)
                combo_pbos.append(pbo)
                ok = df[~df.insufficient]
                pos = int((ok.median_sharpe > 0).sum())
                print(f"  {len(ok)}/{len(df)} evaluable, "
                      f"{pos} with positive median Sharpe, "
                      f"PBO {pbo['pbo']:.3f}", file=sys.stderr)
                if explain:
                    for line in interpret(len(ok), len(df), pos, pbo["pbo"]):
                        print(line, file=sys.stderr)
            if "triples" in stages:
                print(f"[{h}] CPCV triples (a-priori candidate set)…", file=sys.stderr)
                df, pbo = run_combos(
                    h, 3, args.groups, args.k, ("all", "vote"), TRIPLE_CANDIDATES,
                    gate=args.pair_gate,
                )
                combo_frames.append(df)
                combo_pbos.append(pbo)
                ok = df[~df.insufficient]
                pos = int((ok.median_sharpe > 0).sum())
                print(f"  {len(ok)}/{len(df)} evaluable, "
                      f"{pos} with positive median Sharpe, "
                      f"PBO {pbo['pbo']:.3f}", file=sys.stderr)
                if explain:
                    for line in interpret(len(ok), len(df), pos, pbo["pbo"]):
                        print(line, file=sys.stderr)

        combos = pd.concat(combo_frames, ignore_index=True)
        combos.to_csv(OUT / "cpcv_combos_results.csv", index=False)
        (OUT / "cpcv_combos_pbo.json").write_text(
            json.dumps(combo_pbos, indent=2, default=str) + "\n"
        )

        lines: list[str] = []
        for pbo in combo_pbos:
            h, kind = pbo["horizon"], pbo["kind"]
            sub = combos[(combos.horizon == h) & (combos.kind == kind)]
            ok = sub[~sub.insufficient].sort_values("median_sharpe", ascending=False)
            lines.append(
                f"\n### {h.upper()} — {kind}s under CPCV "
                f"({len(sub)} evaluated, {len(ok)} evaluable, "
                f"{int((ok.median_sharpe > 0).sum())} with positive median Sharpe)\n\n"
                f"**PBO = {pbo['pbo']:.3f}** across {int(pbo['n_splits'])} splits of "
                f"{int(pbo['n_configs'])} configurations.\n\n"
                "| # | combination | families | median Sharpe | IQR | % paths + | "
                "median ret | trades |\n|---|---|---|---|---|---|---|---|\n"
            )
            for i, (_, r) in enumerate(ok.head(15).iterrows(), 1):
                lines.append(
                    f"| {i} | `{r.label}` | {r.family} | **{r.median_sharpe:+.3f}** | "
                    f"{r.iqr_spread:.3f} | {r.frac_paths_positive * 100:.0f}% | "
                    f"{r.median_path_return * 100:+.1f}% | {int(r.total_trades)} |\n"
                )
            if len(ok) > 15:
                lines.append(f"\n_Top 15 of {len(ok)} evaluable shown._\n")
        (OUT / "cpcv_combos_tables.md").write_text("".join(lines))
        print(f"\nWrote {OUT}/cpcv_combos_results.csv, cpcv_combos_tables.md, "
              f"cpcv_combos_pbo.json", file=sys.stderr)

        if "singles" not in stages:
            return 0

    frames, pbos = [], []
    for h in horizons:
        print(f"[{h}] CPCV {args.groups} groups, k={args.k}…", file=sys.stderr)
        df, pbo = run_horizon(h, args.groups, args.k)
        frames.append(df)
        pbos.append(pbo)
        ranked = df[~df.insufficient].sort_values("median_sharpe", ascending=False)
        print(f"  {len(ranked)}/{len(df)} configurations evaluable", file=sys.stderr)
        print(f"  PBO = {pbo['pbo']:.3f} over {int(pbo['n_splits'])} splits, "
              f"{int(pbo['n_configs'])} configs", file=sys.stderr)
        if explain:
            pos = int((ranked.median_sharpe > 0).sum())
            for line in interpret(len(ranked), len(df), pos, pbo["pbo"]):
                print(line, file=sys.stderr)

    allrows = pd.concat(frames, ignore_index=True)
    allrows.to_csv(OUT / "cpcv_results.csv", index=False)
    (OUT / "cpcv_pbo.json").write_text(json.dumps(pbos, indent=2, default=str) + "\n")

    # Markdown fragment for the documents.
    lines: list[str] = []
    for h in horizons:
        sub = allrows[allrows.horizon == h]
        ok = sub[~sub.insufficient].sort_values("median_sharpe", ascending=False)
        bad = sub[sub.insufficient]
        pbo = next(p for p in pbos if p["horizon"] == h)
        lines.append(
            f"\n### {h.upper()} horizon — CPCV "
            f"({args.groups} blocks, k={args.k}, "
            f"{int(ok.n_paths.max()) if len(ok) else 0} paths per configuration)\n"
        )
        lines.append(
            f"**PBO = {pbo['pbo']:.3f}** across {int(pbo['n_splits'])} splits of "
            f"{int(pbo['n_configs'])} fully-evaluable configurations.\n\n"
        )
        lines.append(
            "| # | strategy | family | median Sharpe | IQR spread | "
            "% paths positive | median path return | trades |\n"
            "|---|---|---|---|---|---|---|---|\n"
        )
        for i, (_, r) in enumerate(ok.iterrows(), 1):
            lines.append(
                f"| {i} | `{r.label}` | {r.family} | **{r.median_sharpe:+.3f}** | "
                f"{r.iqr_spread:.3f} | {r.frac_paths_positive * 100:.0f}% | "
                f"{r.median_path_return * 100:+.1f}% | {int(r.total_trades)} |\n"
            )
        if len(bad):
            lines.append(
                f"\n_{len(bad)} configuration(s) not evaluable: "
                + "; ".join(f"`{r.label}` ({r.reason})" for _, r in bad.iterrows())
                + "._\n"
            )
    (OUT / "cpcv_tables.md").write_text("".join(lines))
    print(f"\nWrote {OUT}/cpcv_results.csv, cpcv_pbo.json, cpcv_tables.md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
