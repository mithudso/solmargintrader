"""Mechanical half of the /dso statistical-honesty passes, run over the CPCV result CSVs.

    python3 research/dso_audit.py                 # audit every cpcv_* result file
    python3 research/dso_audit.py --floor 30      # raise the evidence floor

`/dso` (the deep-strategy-optimizer skill) defines 19 audit passes. Four of them are
arithmetic rather than judgement, so they belong in code where they can be re-run and
cannot be forgotten:

    S2  multiple-testing burden  — how many configurations were searched, and was the
                                   comparison drawn against zero rather than against the
                                   expected maximum of that many trials?
    S3  evidence floor           — a result standing on too few trades is not evidence.
                                   A `q1_sharpe` of exactly 0.000 is the specific tell
                                   that most CPCV paths took no trade at all.
    S4  degeneracy               — nominally different strategies whose RESULT VECTORS
                                   coincide are one strategy wearing several names. It
                                   compares outputs, never parameters, because the cause
                                   is usually a constraint binding on every bar.
    S5  attribution              — a strategy that ranks 1st on one asset or timeframe
                                   and near-last on another was measuring the dataset.

**This flags, it does not fix.** Every hit is a claim to re-examine, and a few are
expected to be benign: two strategies can legitimately post the same rounded Sharpe. The
value is that a run cannot silently ship the ones that are not benign.

Findings never change the exit code: this is a report, not a gate. Turning it into a gate
would create an incentive to delete inconvenient strategies, which is the survivorship
bias the skill's own guardrails forbid. Exit 1 is reserved for not being able to read the
inputs at all.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).resolve().parent / "results"

# A CPCV path Sharpe of exactly 0.000 at the first quartile means at least a quarter of
# paths produced no trades. Compared with a tolerance rather than `== 0` because the CSV
# round-trips through text.
FLAT_TOL = 5e-4

# Columns whose agreement across strategies constitutes a degenerate twin. Deliberately
# the OUTPUTS, at the precision the CSV publishes.
RESULT_KEYS = ("median_sharpe", "median_return", "total_trades")


class AuditError(RuntimeError):
    """Raised when a result file cannot be read or lacks the columns to audit."""


def load(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise AuditError(f"could not read {path.name}: {exc}") from exc
    if "strategy" not in df.columns:
        raise AuditError(f"{path.name} has no 'strategy' column; nothing to audit")
    df["_file"] = path.name
    return df


def s2_burden(frames: dict[str, pd.DataFrame]) -> list[str]:
    """Report the size of the search, which sets the multiple-testing burden."""
    out = []
    total = 0
    for name, df in frames.items():
        n = len(df)
        total += n
        out.append(f"  {name}: {n} configurations")
    out.append(
        f"  TOTAL {total} configurations evaluated across {len(frames)} files.\n"
        f"  A best-of-{total} Sharpe is expected to look good even with no edge present. "
        "Any claim\n  drawn against a benchmark of ZERO overstates itself by the expected "
        "maximum of\n  that many trials — apply a Deflated-Sharpe haircut before ranking. "
        "Verify the DSR\n  expected-maximum formula against its source paper before "
        "implementing it."
    )
    return out


def s3_evidence_floor(df: pd.DataFrame, floor: int) -> list[str]:
    """Rows resting on too few trades, or whose Q1 path Sharpe is flat at zero."""
    out = []
    if "total_trades" in df:
        thin = df[df["total_trades"] < floor]
        for _, r in thin.iterrows():
            out.append(
                f"  [{r['_file']}] {r.get('asset', '')} {r['strategy']}: "
                f"{int(r['total_trades'])} trades (floor {floor}) — "
                f"median Sharpe {r['median_sharpe']:+.3f} is not evidence"
            )
    if "q1_sharpe" in df:
        flat = df[df["q1_sharpe"].abs() < FLAT_TOL]
        for _, r in flat.iterrows():
            out.append(
                f"  [{r['_file']}] {r.get('asset', '')} {r['strategy']}: "
                f"q1_sharpe = {r['q1_sharpe']:.3f} — a quarter or more of paths took "
                "no trade"
            )
    return out


def s4_degeneracy(df: pd.DataFrame) -> list[str]:
    """Strategies whose published result vectors coincide."""
    keys = [k for k in RESULT_KEYS if k in df]
    if not keys:
        return []
    groups: dict[tuple, list[str]] = defaultdict(list)
    for _, r in df.iterrows():
        sig = tuple(round(float(r[k]), 6) for k in keys)
        label = f"{r.get('asset', '')} {r['strategy']}".strip()
        groups[sig].append(label)
    out = []
    for sig, members in groups.items():
        if len(members) > 1:
            shown = ", ".join(f"{k}={v}" for k, v in zip(keys, sig))
            out.append(
                f"  [{df['_file'].iloc[0]}] {' == '.join(sorted(members))}\n"
                f"      identical on {shown}\n"
                "      One strategy under several names inflates apparent search breadth "
                "without\n      adding diversity, which inflates the S2 burden above."
            )
    return out


def s5_attribution(frames: dict[str, pd.DataFrame], swing: int) -> list[str]:
    """Strategies whose rank moves sharply between datasets."""
    ranks: dict[str, dict[str, int]] = defaultdict(dict)
    for name, df in frames.items():
        if "median_sharpe" not in df or "strategy" not in df:
            continue
        # Drop non-finite scores first: sort_values places NaN last, which would hand a
        # missing result the worst rank and manufacture an S5 swing that is really a gap.
        df = df[df["median_sharpe"].notna()]
        for asset, sub in (
            df.groupby("asset") if "asset" in df else [(name, df)]
        ):
            key = f"{name}:{asset}" if "asset" in df else name
            ordered = sub.sort_values("median_sharpe", ascending=False)
            for i, (_, r) in enumerate(ordered.iterrows(), start=1):
                ranks[r["strategy"]][key] = i

    out = []
    for strategy, per in sorted(ranks.items()):
        if len(per) < 2:
            continue
        best_ds, best = min(per.items(), key=lambda kv: kv[1])
        worst_ds, worst = max(per.items(), key=lambda kv: kv[1])
        if worst - best >= swing:
            spread = ", ".join(f"{k} #{v}" for k, v in sorted(per.items(), key=lambda kv: kv[1]))
            out.append(
                f"  {strategy}: #{best} on {best_ds} but #{worst} on {worst_ds}\n"
                f"      {spread}\n"
                "      The dataset explains more of this than the strategy does; the "
                "favourable\n      ranking is not transferable evidence."
            )
    return out


def section(title: str, rows: list[str]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    if rows:
        print("\n".join(rows))
    else:
        print("  no findings")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 research/dso_audit.py",
        description=(
            "Run the arithmetic /dso statistical-honesty passes (S2, S3, S4, S5) over the "
            "CPCV result CSVs. Reports; never gates. NOT investment advice."
        ),
    )
    ap.add_argument("--floor", type=int, default=30, help="minimum trades to count as evidence")
    ap.add_argument("--swing", type=int, default=10, help="rank change that triggers S5")
    ap.add_argument("--glob", default="cpcv_all25*.csv", help="which result files to audit")
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.floor < 1 or args.swing < 1:
        print("error: --floor and --swing must both be >= 1", file=sys.stderr)
        return 2

    paths = sorted(RESULTS.glob(args.glob))
    if not paths:
        print(f"error: no result files matched {args.glob} in {RESULTS}", file=sys.stderr)
        return 1

    try:
        frames = {p.name: load(p) for p in paths}
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("/dso mechanical audit — passes S2, S3, S4, S5")
    print(f"files: {', '.join(frames)}")

    section("S2 — multiple-testing burden", s2_burden(frames))

    floor_rows: list[str] = []
    degen_rows: list[str] = []
    for df in frames.values():
        floor_rows += s3_evidence_floor(df, args.floor)
        degen_rows += s4_degeneracy(df)
    section(f"S3 — evidence floor (< {args.floor} trades, or flat Q1)", floor_rows)
    section("S4 — degenerate twins (identical result vectors)", degen_rows)
    section(f"S5 — attribution (rank swing >= {args.swing})", s5_attribution(frames, args.swing))

    print(
        "\nFlags are claims to re-examine, not defects. Some coincidences are benign.\n"
        "Historical simulation only, NOT investment advice."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
