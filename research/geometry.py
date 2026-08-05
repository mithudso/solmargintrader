"""How much of the CPCV ranking is an artifact of the block count?

    python3 research/geometry.py --horizon long
    python3 research/geometry.py --horizon medium --blocks 6 12 --k 2

## The question, and why it is not the perturbation question

`perturb.py` asks whether a configuration's *number* survives nudging its
parameters. This asks something different and arguably more damaging: whether the
*ranking* survives nudging the evaluation. The block count N is a free choice --
nobody can justify 8 blocks over 9 from first principles -- so if the leaderboard
reshuffles as N moves, the leaderboard is partly reporting how the data was
sliced.

It exists because the perturbation run turned up something unexpected: for the top
pair, changing 8 blocks to 9 moved the median Sharpe MORE (-0.441) than any 10%
parameter change did (-0.392). That is worth measuring properly rather than
leaving as an anecdote.

## What is measured

For each N in the requested range, every strategy is CPCV-evaluated and ranked by
median path Sharpe. Then:

  * **Rank correlation between every pair of geometries.** Spearman on the shared
    strategy set. High correlation means the ranking is a property of the
    strategies; low means it is a property of N.
  * **Whether the #1 strategy changes with N** -- the most concrete form of the
    question, and the one a reader actually acts on.
  * **Spread of each strategy's median Sharpe across N**, which separates
    "everything moves together" (harmless, a level shift) from "they reorder"
    (harmful).
  * **PBO per N**, since PBO is itself computed from the block structure and has
    no reason to be invariant either.

## The comparability rule

Larger N means smaller blocks, which means more strategies fail their warm-up or
trade floor. Comparing rankings across N is only meaningful on strategies
evaluable at EVERY N, so the common set is intersected first and the dropped
names are reported. Ranking a shrinking population against a growing one would
manufacture disagreement that is really just differing membership.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import cpcv_evaluate, pbo_cscv  # noqa: E402
from backtester.core.strategies import build  # noqa: E402
from research.sweep import HORIZONS, load_horizon  # noqa: E402

OUT = REPO / "research" / "results"


@dataclass
class GeometryRun:
    """Every strategy evaluated at one block count."""

    blocks: int
    k: int
    medians: dict[str, float] = field(default_factory=dict)
    frac_positive: dict[str, float] = field(default_factory=dict)
    trades: dict[str, int] = field(default_factory=dict)
    # Name -> why it dropped out. A bare list of names cannot distinguish a benign
    # warm-up drop (expected as blocks shrink) from a strategy that stopped trading
    # altogether, and those two facts warrant opposite reactions from a reader.
    unevaluable: dict[str, str] = field(default_factory=dict)
    pbo: float = float("nan")
    pbo_splits: int = 0

    def ranking(self, names: list[str]) -> list[str]:
        """`names` ordered best-first by median Sharpe at this geometry."""
        return sorted(names, key=lambda n: self.medians[n], reverse=True)


def spearman(a: list[float], b: list[float]) -> float:
    """Rank correlation without scipy."""
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    if len(ra) < 3 or ra.std() == 0 or rb.std() == 0:
        # A constant ranking has no order to correlate with. numpy would divide by a
        # zero standard deviation, warn, and hand back NaN; say NaN outright instead.
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def evaluate_geometry(horizon: str, blocks: int, k: int) -> GeometryRun:
    """CPCV-evaluate every strategy in the horizon's grid at one block count."""
    arrays, cfg = load_horizon(horizon)
    params = HORIZONS[horizon]["params"]
    run = GeometryRun(blocks=blocks, k=k)
    per_config_blocks: dict[str, dict[int, np.ndarray]] = {}

    for name, ps in params.items():
        res = cpcv_evaluate(
            name, lambda n=name, q=ps: build(n, **q), arrays, cfg,
            n_groups=blocks, k_test=k,
        )
        if res.insufficient or not np.isfinite(res.median_sharpe):
            run.unevaluable[name] = res.reason or "non-finite median Sharpe"
            continue
        run.medians[name] = res.median_sharpe
        run.frac_positive[name] = res.frac_positive
        run.trades[name] = res.total_trades
        per_config_blocks[name] = {b.index: b.returns for b in res.blocks if b.usable}

    if len(per_config_blocks) >= 2:
        common = sorted(set.intersection(*(set(d) for d in per_config_blocks.values())))
        if len(common) >= 4:
            out = pbo_cscv({n: [d[i] for i in common] for n, d in per_config_blocks.items()})
            run.pbo = out["pbo"]
            run.pbo_splits = int(out["n_splits"])
    return run


def tidy_frame(horizon: str, runs: list[GeometryRun], names: list[str]) -> pd.DataFrame:
    """One row per (strategy, block count) -- the frame verify_numbers recomputes from."""
    return pd.DataFrame([
        {
            "horizon": horizon, "blocks": r.blocks, "k": r.k, "strategy": n,
            "median_sharpe": r.medians[n], "frac_positive": r.frac_positive[n],
            "trades": r.trades[n],
        }
        for n in names for r in runs
    ])


def render(horizon: str, runs: list[GeometryRun]) -> tuple[str, pd.DataFrame]:
    """Report plus a tidy frame of every (strategy, blocks) median."""
    # Comparability: only strategies evaluable at every geometry.
    common = set(runs[0].medians)
    for r in runs[1:]:
        common &= set(r.medians)
    names = sorted(common)
    dropped = sorted(set(HORIZONS[horizon]["params"]) - common)
    if not names:
        # Ranking nothing would otherwise die with an IndexError further down. The
        # realistic cause is a block count near the series length, so say that.
        raise SystemExit(
            f"no strategy is evaluable at every block count "
            f"{[r.blocks for r in runs]}; lower the range or use a longer series"
        )

    lines = [
        f"CPCV GEOMETRY SWEEP — {horizon} horizon, k={runs[0].k}",
        f"block counts: {', '.join(str(r.blocks) for r in runs)}",
        f"comparable strategies: {len(names)} of "
        f"{len(HORIZONS[horizon]['params'])} (evaluable at every block count)",
        "",
    ]
    if dropped:
        lines += [f"dropped (not evaluable at all geometries): {', '.join(dropped)}"]
        # One reason per dropped name, so a reader can tell a warm-up drop from a
        # strategy that simply stopped trading without re-running the sweep.
        for name in dropped:
            why = next((r.unevaluable[name] for r in runs if name in r.unevaluable), "")
            lines.append(f"    {name}: {why}" if why else f"    {name}")
        lines.append("")

    # Per-strategy medians across N.
    header = f"{'strategy':<24}" + "".join(f"{r.blocks:>8}" for r in runs) + f"{'spread':>9}{'rank Δ':>8}"
    lines += [header, "-" * len(header)]
    rank_positions: dict[str, list[int]] = {n: [] for n in names}
    for r in runs:
        order = r.ranking(names)
        for pos, n in enumerate(order, 1):
            rank_positions[n].append(pos)

    for n in sorted(names, key=lambda x: -float(np.median([r.medians[x] for r in runs]))):
        vals = [r.medians[n] for r in runs]
        spread = max(vals) - min(vals)
        rd = max(rank_positions[n]) - min(rank_positions[n])
        lines.append(
            f"{n[:23]:<24}" + "".join(f"{v:>+8.2f}" for v in vals)
            + f"{spread:>9.2f}{rd:>8d}"
        )

    # Who is #1 at each geometry.
    lines += ["", "top-ranked strategy by block count:"]
    winners = []
    for r in runs:
        w = r.ranking(names)[0]
        winners.append(w)
        lines.append(f"  {r.blocks:>2} blocks: {w:<24} median {r.medians[w]:+.3f}"
                      f"   PBO {r.pbo:.3f} ({r.pbo_splits} splits)")
    distinct = sorted(set(winners))

    # Pairwise rank correlation.
    lines += ["", "pairwise Spearman between geometries (on the comparable set):"]
    grid = [[""] + [f"{r.blocks:>6}" for r in runs]]
    taus = []
    for ri in runs:
        row = [f"{ri.blocks:>2}"]
        for rj in runs:
            if ri.blocks == rj.blocks:
                row.append(f"{1.0:>6.2f}")
                continue
            rho = spearman([ri.medians[n] for n in names], [rj.medians[n] for n in names])
            row.append(f"{rho:>6.2f}")
            if ri.blocks < rj.blocks:
                taus.append(rho)
        grid.append(row)
    lines += ["  " + " ".join(c for c in g) for g in grid]

    spreads = np.array([max(r.medians[n] for r in runs) - min(r.medians[n] for r in runs)
                        for n in names])
    rank_deltas = np.array([max(rank_positions[n]) - min(rank_positions[n]) for n in names])
    mean_rho = float(np.mean(taus)) if taus else float("nan")

    lines += [
        "",
        f"median |Δ median Sharpe| across geometries: {np.median(spreads):.2f} "
        f"(max {spreads.max():.2f})",
        f"median rank movement: {np.median(rank_deltas):.0f} places "
        f"(max {rank_deltas.max()} of {len(names)})",
        f"mean pairwise Spearman: {mean_rho:+.3f}",
        f"distinct top-ranked strategies across {len(runs)} geometries: "
        f"{len(distinct)} ({', '.join(distinct)})",
        "",
        "VERDICT: " + verdict(mean_rho, distinct, rank_deltas, len(names)),
    ]
    # Row order follows the report: best median first, so the CSV reads the same way
    # the table does.
    ordered = sorted(names, key=lambda x: -float(np.median([r.medians[x] for r in runs])))
    return "\n".join(lines), tidy_frame(horizon, runs, ordered)


def verdict(mean_rho: float, distinct_winners: list[str], rank_deltas, n: int) -> str:
    """Plain-language reading of geometry dependence."""
    if not np.isfinite(mean_rho):
        return "INCONCLUSIVE — too few comparable strategies"
    median_move = float(np.median(rank_deltas))
    parts = [
        f"mean pairwise rank correlation {mean_rho:+.3f}",
        f"the median strategy moves {median_move:.0f} of {n} places as the block count varies",
        f"{len(distinct_winners)} distinct strategies hold first place",
    ]
    if mean_rho >= 0.9 and len(distinct_winners) == 1:
        head = ("GEOMETRY-STABLE — the ranking is a property of the strategies, not of "
                "the block count. Reading the leaderboard is safe on this axis.")
    elif mean_rho >= 0.7:
        head = ("MOSTLY STABLE — the ordering broadly survives, but the top spot is not "
                "fixed. Quote the distribution, not the rank.")
    else:
        head = ("GEOMETRY-DEPENDENT — a large part of the ranking is an artifact of how "
                "the series was sliced. Do not read positions off the leaderboard.")
    return head + "\n    " + "\n    ".join(parts)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="CPCV block-count sensitivity sweep.")
    ap.add_argument("--horizon", choices=list(HORIZONS), default="long")
    ap.add_argument("--blocks", nargs=2, type=int, default=[6, 12],
                    metavar=("LO", "HI"), help="inclusive block-count range")
    ap.add_argument("--k", type=int, default=2, help="blocks per test path")
    args = ap.parse_args(argv)

    lo, hi = args.blocks
    if lo < 3 or hi < lo:
        ap.error("need 3 <= LO <= HI")
    if args.k < 1:
        ap.error("need k >= 1: a test path must contain at least one block")
    if args.k >= lo:
        ap.error(f"k={args.k} must be smaller than the smallest block count ({lo})")

    runs = []
    for n in range(lo, hi + 1):
        print(f"  {args.horizon}: {n} blocks …", file=sys.stderr)
        runs.append(evaluate_geometry(args.horizon, n, args.k))

    text, frame = render(args.horizon, runs)
    print(text)

    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"geometry_{args.horizon}_k{args.k}"
    (OUT / f"{stem}.txt").write_text(text + "\n")
    frame.to_csv(OUT / f"{stem}.csv", index=False)
    (OUT / f"{stem}.json").write_text(json.dumps(
        [{"blocks": r.blocks, "k": r.k, "pbo": r.pbo, "pbo_splits": r.pbo_splits,
          "unevaluable": r.unevaluable} for r in runs], indent=2) + "\n")
    print(f"\nwrote {OUT}/{stem}.{{txt,csv,json}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
