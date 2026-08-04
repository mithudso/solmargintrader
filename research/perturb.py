"""Parameter-perturbation stability check for one configuration.

    python3 research/perturb.py --horizon long --pair dual_momentum vol_regime --mode all
    python3 research/perturb.py --horizon medium --single hurst_switch

## What this answers, and why it is the right question

A CPCV median Sharpe tells you how a configuration did across regime-mixed paths.
It does NOT tell you whether that number is a property of the *mechanism* or of
the *particular parameters* someone happened to pick. Those are different claims,
and the second one does not survive contact with new data.

So: nudge each parameter by a small amount (default +/-10%), re-run the full CPCV
evaluation, and see how far the median moves. The reasoning is that a 10% change
in a lookback window is economically meaningless -- nobody can justify 24 bars
over 26 from first principles -- so if the result moves a lot, the result was
about the parameter, not the mechanism.

## The verdict criterion, stated up front

The comparison is against the configuration's **own interquartile spread** across
CPCV paths, not an arbitrary threshold:

  * If perturbation moves the median by much LESS than the path IQR, the
    parameter choice matters less than which regime you sampled. That is what a
    robust result looks like.
  * If perturbation moves it by as much as or more than the IQR, then picking the
    parameter mattered as much as the market did. That is a red flag, and it is
    the same logic as the zscore/bb_reversion natural experiment in
    RANKED_LISTS.md, where a 2.6% threshold change moved out-of-sample return by
    46 points.
  * A perturbation that flips the sign of the median is reported separately and
    counted, because sign stability is the weakest claim worth having.

One-at-a-time perturbation, not a joint grid: a joint sweep IS a parameter search,
and running one here would reintroduce exactly the selection bias the whole
document warns about. The point is sensitivity, not optimisation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import cpcv_evaluate  # noqa: E402
from backtester.core.strategies import build, build_composite  # noqa: E402
from research.sweep import HORIZONS, load_horizon  # noqa: E402

OUT = REPO / "research" / "results"

# Parameters that must not be perturbed as if they were continuous scales.
# `skip` of 1 has no meaningful 10% neighbour, and quantiles/lambdas live in
# (0,1) where a naive multiply can leave the domain.
BOUNDED_UNIT = {"calm_quantile", "lam", "risk_per_trade", "step", "entry_discount",
                "target_vol", "trend_threshold", "revert_threshold"}

# Empirical references for the ratio, so the verdict compares against something
# measured rather than a threshold I picked. SEPARATE references per configuration
# type, because they differ substantially and using one for the other
# mis-calibrates the verdict:
#
#   singles: 72 configurations (all 25 across 3 horizons)
#            min 0.04 · median 0.21 · max 1.33
#   pairs  : 5 top long-horizon pairs
#            min 0.30 · median 0.44 · max 0.72
#
# Pairs are ~2.6x more parameter-sensitive than singles by median ratio, which is
# the same direction as the PBO result that combining signals makes overfitting
# worse -- two independent methods agreeing.
#
# Re-derive with:
#   python3 research/perturb.py --horizon <h> --all-singles
REFERENCE = {
    "single": (0.04, 0.21, 1.33),
    "combo": (0.30, 0.44, 0.72),
}
# Above the observed population's upper end, sensitivity is unusual enough to flag.
REFERENCE_HIGH = {"single": 0.60, "combo": 0.72}


@dataclass
class Trial:
    """One evaluated variant."""

    label: str
    what: str
    median_sharpe: float
    iqr: float
    frac_positive: float
    median_return: float
    trades: int
    evaluable: bool
    reason: str = ""


@dataclass
class Report:
    """Baseline plus every perturbation."""

    target: str
    horizon: str
    baseline: Trial
    kind: str = "single"   # 'single' or 'combo'; selects the reference population
    trials: list[Trial] = field(default_factory=list)

    @property
    def usable(self) -> list[Trial]:
        """Perturbations that produced a number at all."""
        return [t for t in self.trials if t.evaluable and np.isfinite(t.median_sharpe)]

    @property
    def deltas(self) -> np.ndarray:
        """Signed change in median Sharpe for each usable perturbation."""
        return np.array(
            [t.median_sharpe - self.baseline.median_sharpe for t in self.usable]
        )

    @property
    def max_abs_delta(self) -> float:
        """Largest absolute move any single 10% nudge produced."""
        d = np.abs(self.deltas)
        return float(d.max()) if d.size else float("nan")

    @property
    def sign_flips(self) -> list[Trial]:
        """Perturbations that reversed the sign of the median Sharpe."""
        b = self.baseline.median_sharpe
        return [t for t in self.usable if np.sign(t.median_sharpe) != np.sign(b)]

    @property
    def ratio_to_iqr(self) -> float:
        """max|delta| as a fraction of the baseline's own path IQR.

        Below ~0.5 the parameter matters less than the regime. At or above 1.0 the
        parameter mattered as much as the market, which is a red flag.
        """
        if self.baseline.iqr <= 1e-12:
            return float("nan")
        return self.max_abs_delta / self.baseline.iqr

    def verdict(self) -> str:
        """Plain-language reading, using the criterion in the module docstring."""
        if not self.usable:
            return "INCONCLUSIVE — no perturbation produced an evaluable result"
        r = self.ratio_to_iqr
        flips = len(self.sign_flips)
        parts = [
            f"max |Δ median Sharpe| = {self.max_abs_delta:.3f} against a baseline "
            f"path IQR of {self.baseline.iqr:.3f} (ratio {r:.2f})",
            f"{flips} of {len(self.usable)} perturbations flip the sign",
        ]
        if r >= 1.0 or flips >= max(1, len(self.usable) // 3):
            head = ("FRAGILE — the parameter choice moved the result as much as the "
                    "market did. Treat the headline number as a property of those "
                    "parameters, not of the mechanism.")
        elif r >= REFERENCE_HIGH[self.kind]:
            head = ("BORDERLINE — sensitivity is high relative to the measured "
                    "reference population. Worth more data before believing the rank.")
        else:
            head = ("STABLE under this test — a 10% parameter nudge moves the median "
                    "much less than sampling a different regime does.")
        lo, mid, hi = REFERENCE[self.kind]
        parts.append(
            f"reference population for a {self.kind}: {lo:.2f}–{hi:.2f} "
            f"(median {mid:.2f}), so this is "
            f"{'above' if r > mid else 'at or below'} typical"
        )
        parts.append(
            "this test does NOT address multiple testing. It asks whether the "
            "PARAMETERS were cherry-picked; it cannot tell you whether the "
            "CONFIGURATION was cherry-picked from hundreds. PBO answers that, "
            "separately."
        )
        return head + "\n    " + "\n    ".join(parts)


def perturbed_values(name: str, value: Any, pct: float) -> list[tuple[str, Any]]:
    """(description, value) neighbours of `value` for parameter `name`.

    Ints step by at least 1 so a 10% nudge on a small window is not a no-op.
    Unit-interval parameters step additively and are clamped inside (0, 1) rather
    than multiplied out of their domain.
    """
    out: list[tuple[str, Any]] = []
    if isinstance(value, bool) or value is None:
        return out
    if name in BOUNDED_UNIT and isinstance(value, float):
        for sign in (-1, 1):
            v = value + sign * pct * value
            if 0.0 < v < 1.0 and abs(v - value) > 1e-12:
                out.append((f"{name} {value:g}→{v:.4g}", v))
        return out
    if isinstance(value, int):
        step = max(1, round(abs(value) * pct))
        for sign in (-1, 1):
            v = value + sign * step
            if v >= 1:
                out.append((f"{name} {value}→{v}", v))
        return out
    if isinstance(value, float):
        for sign in (-1, 1):
            v = value + sign * pct * value
            if abs(v) > 1e-12:
                out.append((f"{name} {value:g}→{v:.4g}", v))
    return out


def evaluate(
    label: str, what: str, specs: list[tuple[str, dict]], mode: str | None,
    arrays, cfg, groups: int, k: int,
) -> Trial:
    """CPCV-evaluate one variant."""
    def make():
        if mode is None:
            name, params = specs[0]
            return build(name, **params)
        return build_composite(list(specs), mode=mode)

    res = cpcv_evaluate(label, make, arrays, cfg, n_groups=groups, k_test=k)
    return Trial(
        label=label, what=what, median_sharpe=res.median_sharpe, iqr=res.spread,
        frac_positive=res.frac_positive, median_return=res.median_return,
        trades=res.total_trades, evaluable=not res.insufficient, reason=res.reason,
    )


def run(
    horizon: str, members: list[str], mode: str | None, pct: float,
    groups: int, k: int, geometry: bool = True,
) -> Report:
    """Baseline plus a one-at-a-time perturbation of every member parameter."""
    arrays, cfg = load_horizon(horizon)
    params = HORIZONS[horizon]["params"]
    specs = [(m, dict(params[m])) for m in members]
    label = (f"{mode}({'+'.join(members)})" if mode else members[0])

    base = evaluate(label, "baseline", specs, mode, arrays, cfg, groups, k)
    report = Report(target=label, horizon=horizon, baseline=base,
                    kind="single" if mode is None else "combo")

    for idx, (name, ps) in enumerate(specs):
        for pname, pvalue in ps.items():
            for desc, newv in perturbed_values(pname, pvalue, pct):
                variant = [(n, dict(p)) for n, p in specs]
                variant[idx][1][pname] = newv
                report.trials.append(
                    evaluate(label, f"{name}: {desc}", variant, mode,
                             arrays, cfg, groups, k)
                )

    if geometry:
        # The CPCV geometry is also a choice nobody can justify from first
        # principles, so a result should not depend on it either.
        for g, kk in ((groups - 1, k), (groups + 1, k), (groups, k + 1)):
            if g < 3 or kk >= g:
                continue
            report.trials.append(
                evaluate(label, f"geometry: {g} blocks, k={kk}", specs, mode,
                         arrays, cfg, g, kk)
            )
    return report


def render(report: Report) -> str:
    """Human-readable report."""
    b = report.baseline
    lines = [
        f"PARAMETER-PERTURBATION STABILITY CHECK",
        f"target   : {report.target}",
        f"horizon  : {report.horizon}",
        "",
        f"baseline : median Sharpe {b.median_sharpe:+.3f}  IQR {b.iqr:.3f}  "
        f"{b.frac_positive*100:.0f}% paths positive  median return "
        f"{b.median_return*100:+.1f}%  {b.trades} trades",
        "",
        f"{'variant':<46}{'median':>9}{'Δ':>8}{'%pos':>7}{'ret':>9}{'trades':>7}",
        "-" * 86,
    ]
    for t in sorted(report.trials, key=lambda x: x.median_sharpe, reverse=True):
        if not t.evaluable or not np.isfinite(t.median_sharpe):
            lines.append(f"{t.what[:45]:<46}{'n/a':>9}{'':>8}{'':>7}{'':>9}"
                         f"{t.trades:>7}   ({t.reason[:30]})")
            continue
        d = t.median_sharpe - b.median_sharpe
        lines.append(
            f"{t.what[:45]:<46}{t.median_sharpe:>+9.3f}{d:>+8.3f}"
            f"{t.frac_positive*100:>6.0f}%{t.median_return*100:>+9.1f}{t.trades:>7}"
        )
    lines += ["", "VERDICT: " + report.verdict()]
    return "\n".join(lines)


def run_all_singles(
    horizon: str, pct: float, groups: int, k: int
) -> list[Report]:
    """Perturbation check for every single strategy in the horizon's grid."""
    reports: list[Report] = []
    for name in HORIZONS[horizon]["params"]:
        print(f"  {horizon}/{name} …", file=sys.stderr)
        reports.append(run(horizon, [name], None, pct, groups, k, geometry=False))
    return reports


def render_batch(horizon: str, reports: list[Report]) -> str:
    """Stability table for a whole horizon, most robust first.

    Sorted by ratio, NOT by median Sharpe. The interesting question is whether the
    best-performing configurations are also the most stable ones -- if they are
    not, the ranking is selecting for parameter luck.
    """
    rows = [r for r in reports if np.isfinite(r.ratio_to_iqr) and r.usable]
    skipped = [r for r in reports if r not in rows]
    rows.sort(key=lambda r: r.ratio_to_iqr)

    lines = [
        f"PERTURBATION STABILITY — every single strategy, {horizon} horizon",
        f"perturbation: +/-10% one at a time; ratio = max|delta median| / baseline path IQR",
        "",
        f"{'strategy':<28}{'median':>9}{'IQR':>7}{'max|d|':>8}{'ratio':>7}"
        f"{'flips':>8}{'%pos':>7}",
        "-" * 74,
    ]
    for r in rows:
        b = r.baseline
        lines.append(
            f"{b.label[:27]:<28}{b.median_sharpe:>+9.3f}{b.iqr:>7.3f}"
            f"{r.max_abs_delta:>8.3f}{r.ratio_to_iqr:>7.2f}"
            f"{len(r.sign_flips):>4}/{len(r.usable):<3}{b.frac_positive*100:>6.0f}%"
        )
    if skipped:
        lines.append("")
        for r in skipped:
            why = "no tunable parameters" if not r.trials else (r.baseline.reason or "unevaluable")
            lines.append(f"{r.baseline.label[:27]:<28}  skipped — {why}")

    if len(rows) >= 3:
        ratios = np.array([r.ratio_to_iqr for r in rows])
        medians = np.array([r.baseline.median_sharpe for r in rows])
        flips = sum(len(r.sign_flips) for r in rows)
        total = sum(len(r.usable) for r in rows)
        # Rank correlation between performance and stability. Positive means the
        # better performers are the LESS stable ones, which is the bad direction.
        rp = pd.Series(medians).rank()
        rr = pd.Series(ratios).rank()
        rho = float(np.corrcoef(rp, rr)[0, 1])
        lines += [
            "",
            f"population: ratio min {ratios.min():.2f}  median {np.median(ratios):.2f}  "
            f"max {ratios.max():.2f}   |   sign flips {flips}/{total}",
            f"Spearman(median Sharpe, ratio) = {rho:+.3f}  "
            + ("— better performers are LESS stable, i.e. the ranking is partly "
               "selecting parameter luck" if rho > 0.3 else
               "— performance and stability are not strongly linked" if abs(rho) <= 0.3 else
               "— better performers are MORE stable"),
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Perturbation stability check.")
    ap.add_argument("--horizon", choices=list(HORIZONS), default="long")
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"))
    ap.add_argument("--triple", nargs=3, metavar=("A", "B", "C"))
    ap.add_argument("--single", metavar="NAME")
    ap.add_argument(
        "--all-singles", action="store_true",
        help="perturb every single strategy at this horizon and rank by stability",
    )
    ap.add_argument("--mode", default="all", choices=["all", "any", "vote", "mean"])
    ap.add_argument("--pct", type=float, default=0.10, help="perturbation size")
    ap.add_argument("--groups", type=int, default=8)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--no-geometry", action="store_true")
    ap.add_argument("--out", default=None, help="also write the report here")
    args = ap.parse_args(argv)

    if args.all_singles:
        OUT.mkdir(parents=True, exist_ok=True)
        reports = run_all_singles(args.horizon, args.pct, args.groups, args.k)
        text = render_batch(args.horizon, reports)
        print(text)
        stem = f"perturb_all_singles_{args.horizon}"
        (OUT / f"{stem}.txt").write_text(text + "\n")
        pd.DataFrame([
            {"horizon": args.horizon, "label": r.baseline.label,
             "median_sharpe": r.baseline.median_sharpe, "iqr": r.baseline.iqr,
             "max_abs_delta": r.max_abs_delta, "ratio_to_iqr": r.ratio_to_iqr,
             "sign_flips": len(r.sign_flips), "perturbations": len(r.usable),
             "frac_positive": r.baseline.frac_positive,
             "trades": r.baseline.trades}
            for r in reports
        ]).to_csv(OUT / f"{stem}.csv", index=False)
        print(f"\nwrote {OUT}/{stem}.{{txt,csv}}", file=sys.stderr)
        return 0

    if args.single:
        members, mode = [args.single], None
    elif args.pair:
        members, mode = list(args.pair), args.mode
    elif args.triple:
        members, mode = list(args.triple), args.mode
    else:
        ap.error("give --single, --pair, --triple or --all-singles")

    unknown = [m for m in members if m not in HORIZONS[args.horizon]["params"]]
    if unknown:
        print(f"not in the {args.horizon} sweep grid: {unknown}", file=sys.stderr)
        return 1

    report = run(args.horizon, members, mode, args.pct, args.groups, args.k,
                 geometry=not args.no_geometry)
    text = render(report)
    print(text)

    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"perturb_{args.horizon}_{report.target.replace('(', '_').replace(')', '').replace('+', '_')}"
    (OUT / f"{stem}.txt").write_text(text + "\n")
    pd.DataFrame(
        [{"what": t.what, "median_sharpe": t.median_sharpe, "iqr": t.iqr,
          "frac_positive": t.frac_positive, "median_return": t.median_return,
          "trades": t.trades, "evaluable": t.evaluable}
         for t in [report.baseline] + report.trials]
    ).to_csv(OUT / f"{stem}.csv", index=False)
    (OUT / f"{stem}.json").write_text(json.dumps({
        "target": report.target, "horizon": report.horizon,
        "baseline_median_sharpe": report.baseline.median_sharpe,
        "baseline_iqr": report.baseline.iqr,
        "max_abs_delta": report.max_abs_delta,
        "ratio_to_iqr": report.ratio_to_iqr,
        "sign_flips": len(report.sign_flips),
        "perturbations": len(report.usable),
    }, indent=2) + "\n")
    print(f"\nwrote {OUT}/{stem}.{{txt,csv,json}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
