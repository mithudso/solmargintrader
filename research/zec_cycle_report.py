"""Render verified ZEC periodicity evidence, plots and compact public results."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from research.shape_report import table
from research.zec_cycles import TZ, sha, write_json


def render_plots(run, root, target_day):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    target = pd.Timestamp(target_day, tz=TZ)
    lo, hi = int(target.timestamp()), int((target + pd.Timedelta(days=1)).timestamp())
    points = pd.read_csv(run / "pivots.csv")
    spec = pd.read_csv(run / "spectra.csv")
    forecasts = pd.read_csv(run / "forecast_curves.csv")
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), constrained_layout=True)
    raw = pd.read_csv(run / "ZEC_USD_15m_bars.csv.gz")
    raw = raw.loc[(raw.timestamp >= lo) & (raw.timestamp < hi)]
    dates = pd.to_datetime(raw.timestamp + 900, unit="s", utc=True).dt.tz_convert(TZ)
    axes[0].plot(
        dates, raw.close, color="#263b53", lw=1.6, label="Coinbase ZEC-USD 15m close"
    )
    selected = points[
        (points.interval == "15m") & (points.threshold == 0.02)
    ].sort_values("timestamp")
    turns = pd.to_datetime(selected.timestamp + 900, unit="s", utc=True).dt.tz_convert(
        TZ
    )
    axes[0].scatter(
        turns,
        selected.price,
        color="#b45309",
        marker="o",
        zorder=5,
        label="2% reversal pivots (retrospective)",
    )
    for i in range(1, len(selected)):
        left, right = selected.iloc[i - 1], selected.iloc[i]
        stamp = pd.to_datetime(
            (left.timestamp + right.timestamp) / 2 + 900, unit="s", utc=True
        ).tz_convert(TZ)
        axes[0].annotate(
            f"{(right.timestamp - left.timestamp) / 60:.0f}m",
            (stamp, max(left.price, right.price) + 1),
            ha="center",
            fontsize=8,
        )
    axes[0].set(
        title=f"ZEC, {target_day}: an apparent local rhythm is visible",
        ylabel="USD per ZEC",
    )
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=ZoneInfo(TZ)))
    axes[0].set_xlabel(
        "America/New_York; candle-close time. Pivots become known only after reversal confirmation."
    )
    axes[0].legend(loc="best", fontsize=8)
    for interval, color in (("1m", "#2563eb"), ("5m", "#d97706"), ("15m", "#15803d")):
        s = spec[
            (spec.window == target_day)
            & (spec.interval == interval)
            & (spec.series == "log_price")
        ].sort_values("period_minutes")
        axes[1].plot(s.period_minutes / 60, s.power, color=color, label=interval)
        axes[1].axhline(s.null95_max_power.iloc[0], color=color, ls="--", alpha=0.5)
    axes[1].set(
        title="The strongest eligible spectral peak fails the no-clock comparison",
        xlabel="Full cycle length (hours); search requires at least four cycles/day",
        ylabel="Fraction of detrended variation",
    )
    axes[1].text(
        0.02,
        0.96,
        "Dashed: 95th percentile of the maximum searched power on no-clock paths.\nSame market at three resolutions; these are not independent replications.",
        transform=axes[1].transAxes,
        va="top",
        fontsize=8,
    )
    axes[1].legend(loc="center right", fontsize=8)
    s = forecasts[
        (forecasts.interval == "5m")
        & (forecasts.timestamp >= lo)
        & (forecasts.timestamp < hi)
    ]
    x = pd.to_datetime(s.timestamp + 300, unit="s", utc=True).dt.tz_convert(TZ)
    axes[2].plot(x, np.exp(s.actual), color="#263b53", label="Observed")
    for index, (_, group) in enumerate(s.groupby("forecast_origin")):
        times = pd.to_datetime(group.timestamp + 300, unit="s", utc=True).dt.tz_convert(
            TZ
        )
        axes[2].plot(
            times,
            np.exp(group.cycle),
            color="#dc2626",
            label="Frozen harmonic + trend" if index == 0 else None,
        )
        axes[2].plot(
            times,
            np.exp(group.persistence),
            color="#15803d",
            ls="--",
            label="Last observed price" if index == 0 else None,
        )
    axes[2].set(
        title="A fixed harmonic + trend forecast did not predict the next six hours reliably",
        ylabel="USD per ZEC",
        xlabel="America/New_York; each forecast is frozen before its six-hour window",
    )
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=ZoneInfo(TZ)))
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=0.15)
    p = root / "research/results/zec_cycles_20261111_yesterday.png"
    fig.savefig(p, dpi=160)
    plt.close(fig)
    tests = pd.read_csv(run / "spectral_tests.csv")
    folds = pd.read_csv(run / "forecasts.csv")
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    s = tests[
        (tests.interval == "5m")
        & (tests.series == "log_price")
        & (tests.window != "previous_week")
    ]
    axes[0].plot(pd.to_datetime(s.window), s.period_minutes / 60, "o-", color="#2563eb")
    axes[0].axhline(
        6, color="#64748b", ls="--", label="Upper edge of eligible daily search"
    )
    axes[0].set(
        title="The dominant eligible period moves between days",
        ylabel="Full cycle length (hours)",
    )
    axes[0].legend(fontsize=8)
    intervals = ["1m", "5m", "15m", "1h"]
    ratios = []
    for interval in intervals:
        g = folds[folds.interval == interval]
        means = g[["cycle_mse", "linear_mse", "persistence_mse"]].mean()
        ratios.append(
            [
                means.cycle_mse / means.persistence_mse,
                means.linear_mse / means.persistence_mse,
            ]
        )
    x = np.arange(4)
    ratios = np.asarray(ratios)
    axes[1].bar(
        x - 0.18,
        ratios[:, 0],
        width=0.36,
        color="#dc2626",
        label="Frozen harmonic + trend",
    )
    axes[1].bar(
        x + 0.18, ratios[:, 1], width=0.36, color="#d97706", label="Frozen linear trend"
    )
    axes[1].axhline(1, color="#15803d", ls="--", label="Last-price baseline = 1")
    axes[1].set(
        xticks=x,
        xticklabels=intervals,
        ylabel="Mean squared log-price error / baseline",
        title="Future-window errors: lower is better; 29 disjoint six-hour tests per resolution",
    )
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.15)
    q = root / "research/results/zec_cycles_20261111_stability.png"
    fig.savefig(q, dpi=160)
    plt.close(fig)
    return [p, q]


def verify_fixed_report_contract(manifest, repo):
    canonical = json.loads((Path(repo) / "research/results/zec_cycles_20261111_manifest.json").read_text())
    fields = ("artifacts", "target_day", "timezone", "cutoff", "replicates", "seed", "intervals", "scenarios", "assets")
    if any(manifest.get(key) != canonical.get(key) for key in fields) or not manifest.get("artifacts"):
        raise ValueError("fixed report prose requires the canonical artifact set; alternative runs need a new report")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = json.loads((args.run / "manifest.json").read_text())
    verify_fixed_report_contract(manifest, args.repo)
    if (
        manifest["status"] != "complete"
        or sha(args.repo / "research/zec_cycles.py") != manifest["source_sha256"]
    ):
        raise ValueError("run incomplete or source changed")
    for name, expected in manifest["artifacts"].items():
        if sha(args.run / name) != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
    tests = pd.read_csv(args.run / "spectral_tests.csv")
    spacing = pd.read_csv(args.run / "spacing.csv")
    forecast = pd.read_csv(args.run / "forecasts.csv")
    calibration_path = args.run.parent / "calibration.json"
    calibration = json.loads(calibration_path.read_text())
    if (
        calibration["source_sha256"] != manifest["source_sha256"]
        or len(calibration["rows"]) != 50
    ):
        raise ValueError("calibration source or sample count differs")
    if calibration["rejected"] != sum(
        r["p_conservative"] <= 0.05 for r in calibration["rows"]
    ):
        raise ValueError("calibration rejection count differs")
    yesterday = tests[tests.window == manifest["target_day"]]
    summary = []
    for interval, group in forecast.groupby("interval"):
        means = group[["cycle_mse", "linear_mse", "persistence_mse"]].mean()
        summary.append(
            {
                "interval": interval,
                "folds": len(group),
                "cycle_vs_last_price_mse": means.cycle_mse / means.persistence_mse,
                "cycle_vs_linear_mse": means.cycle_mse / means.linear_mse,
                "beats_last_price": int(
                    (group.cycle_mse < group.persistence_mse).sum()
                ),
                "beats_linear": int((group.cycle_mse < group.linear_mse).sum()),
            }
        )
    summary = pd.DataFrame(summary)
    prefix = args.repo / "research/results/zec_cycles_20261111_"
    files = []
    for name in (
        "spectral_tests.csv",
        "spacing.csv",
        "forecasts.csv",
        "coverage.csv",
        "pivots.csv",
        "manifest.json",
    ):
        path = Path(str(prefix) + name)
        shutil.copyfile(args.run / name, path)
        files.append(path)
    calibration_copy = Path(str(prefix) + "calibration.json")
    shutil.copyfile(calibration_path, calibration_copy)
    files.append(calibration_copy)
    summary_path = Path(str(prefix) + "forecast_summary.csv")
    summary.to_csv(summary_path, index=False)
    files.append(summary_path)
    files.extend(render_plots(args.run, args.repo, manifest["target_day"]))
    significant = int((tests.p_holm <= 0.05).sum())
    text = f"""# Does ZEC have a recurring chart frequency?

As of 2026-11-11. The observed day is **2026-11-10, America/New_York**. The exact original chart
timeframe/venue was not supplied; this study checks Coinbase ZEC-USD at 1m, 5m, 15m and 1h.

**A local rhythm is visible, but a stable coin-specific clock is not validated.** On the 15m close
chart, a fixed 2% reversal rule found five intervals between larger alternating turns with a median
of 270 minutes (4.5 hours). That is a **peak-to-dip half-cycle**, not peak-to-peak frequency. It would
suggest about nine hours for a full cycle, leaving fewer than three full cycles in one day. That small,
threshold-dependent observation is insufficient to establish regularity or future turning times.
Four of those five alternating gaps were 270–285 minutes; the other was 120 minutes.

![Yesterday's apparent rhythm, spectral control and frozen forecasts](results/zec_cycles_20261111_yesterday.png)

## What the tests say

Across {len(tests)} declared price/return tests, **{significant} survive the family-wise correction**.
Yesterday's strongest admissible price period is six hours on 1m, 5m and 15m data. It hits the upper
edge of a search requiring at least four cycles per window; it is not an identified natural frequency.
Even before the across-window correction, no-clock paths routinely produce a peak at least this strong.
This rejects neither every possible slow cycle nor adaptive stochastic oscillation. It fails to validate
a fixed clock within the specified search band.
The prior-week scan includes slower periods: its strongest price wavelength was about 18.7 hours,
also far below the no-clock threshold. That scan did not support a stable nine-hour rhythm either.

| Meaning | Interpretation |
| --- | --- |
| Full period | Peak-to-peak or dip-to-dip spacing |
| Half-period | Alternating peak-to-dip spacing for a symmetric oscillation |
| Local wavelength | A temporarily prominent rhythm; can change with time and scale |
| Stable clock | Period and phase selected earlier continue to predict later observations |

### Yesterday's search-aware results

Periods are minutes. `power` is the fraction of detrended variation explained by one harmonic.
`p_conservative` takes the larger of two no-clock p-values. `p_holm` adjusts every eligible
window/timeframe/series test together. These are not the probability that a cycle exists.

"""
    text += table(
        yesterday[
            [
                "interval",
                "series",
                "period_minutes",
                "power",
                "p_random_sign",
                "p_block_permutation",
                "p_conservative",
                "p_holm",
            ]
        ]
    )
    text += """

The hourly chart has only 24 observations yesterday and fails the declared 48-observation floor.
It remains in the longer-window and prediction comparisons. The three finer charts are resolutions
of the same market, not three independent confirmations.

## Are the turns equally spaced?

Turns are amplitude-defined directional changes at fixed 1% and 2% **log-price** reversal thresholds.
No minimum time separation is imposed. A pivot is shown at its actual extreme only retrospectively;
the saved `confirmed_at` records when a reversal made it knowable. Thresholds were fixed before results.
`cv` is interval standard deviation divided by its mean: zero means exactly equal intervals.
The 1m 1% peak spacing has a median of 73 minutes, but its middle half spans 49–114 minutes.
The 15m 2% alternating spacing has a 270-minute median and a 270–285-minute middle half, on only five intervals.
These different answers show why chart zoom and what counts as a meaningful swing matter.

The table's random-sign CV reference uses the first 199 surrogate paths. It is descriptive, not a
multiple-comparison-adjusted peak-spacing test. Rows with too few intervals are absent; reference
paths with too few intervals are also omitted. Do not interpret a reference quantile as significance.

"""
    text += table(
        spacing[
            [
                "interval",
                "threshold",
                "kind",
                "intervals",
                "median_minutes",
                "q25_minutes",
                "q75_minutes",
                "cv",
                "null_cv_median",
            ]
        ]
    )
    text += """

## Does a cycle identified earlier predict later prices?

Each fold uses the preceding three elapsed days to select a period, fit phase/amplitude and linear
trend, then freezes all coefficients before the next disjoint six-hour window. There is no within-test
phase refitting. Compare it with an earlier-fitted linear trend and simply retaining the last observed
price. There are 29 windows per resolution, ending at 2026-11-11 06:00 America/New_York.
Earlier test observations can become training history for a later fold. This is historical replay,
not a prospective trial or profit backtest. It tests this fixed harmonic model, not every cycle model.

Ratios below one improve on the comparator; ratios above one worsen its mean squared log-price error.

"""
    text += table(summary)
    text += """

At 5m, the cycle forecast beats last-price persistence on only 6/29 windows, and its aggregate error
is about 4.54 times larger. It is also worse than extrapolating the earlier linear trend. That gives
no support for scheduling trades from an unchanged period and phase. No trading rule or P&L is inferred.

![Changing wavelengths and future prediction errors](results/zec_cycles_20261111_stability.png)

## Methods, data and limits

- Public native Coinbase Exchange ZEC-USD 1m/5m/15m/1h candles were fetched for 2026-10-20 through
  2026-11-11 11:40 UTC. Only candles completed by the fixed cutoff are analyzed. Raw hashes and exact
  coverage are retained. The minute feed has 119 timestamp gaps overall and four missing candles yesterday.
- Use actual timestamps in nested harmonic regression. Both price and sine/cosine bases are residualized
  against intercept and linear trend. No interpolation or synthetic zero-return candle fills a gap.
  Native larger candles are independent venue aggregates; they need not contain a trade in every minute.
- Frequency candidates are up to 128 unique log-spaced Fourier indices from four cycles/window to six
  bars/cycle. Daily eligible ranges are 6min–6h at 1m, 30min–6h at 5m and 90min–6h at 15m. The prior-week
  analysis admits longer cycles. A daily result at the six-hour boundary deserves extra caution.
- The declared family includes seven calendar days ending yesterday and a prior-seven-day aggregate,
  four resolutions and both detrended log prices and log returns. At least 48 observations and 95%
  expected coverage are required. Holm correction permits dependent windows; it does not make them independent.
- Each of two null models has 1,999 replicates. Random signs preserve centered return magnitudes and
  their temporal volatility pattern. Permuting blocks of up to four returns preserves short local sequences but
  rearranges their order. Both nulls retain the actual sample timestamps. Each replicate repeats the
  complete frequency search. Empirical upper-tail p-values use the plus-one correction.
- These are two specified no-clock null models, not an exhaustive model of crypto markets. Stronger
  long-memory processes, changing regimes and market-wide effects remain possible. One coin cannot
  establish that any rhythm is intrinsic to it. Longer cycles need more elapsed history.
- Yesterday was selected because the owner noticed a pattern. This is an exploratory check of that
  observation, not an untouched confirmatory sample. Threshold/timeframe choices must remain visible.
- No live services, Oracle policy, paper accounts or protected holdout reservations were changed.

## Verification and reproduction

Eight unit tests recover a known clock despite missing observations, compare the spectrum with independent
nested regression, reject linear-trend artifacts, verify Holm adjustment and surrogate properties, and
prove pivot-confirmation and forecast causality. A separate fixed-seed calibration rejected 0/50 Gaussian
random-walk controls at the unadjusted 5% level. That small calibration is a sanity check, not a size guarantee.
NumPy/pandas/matplotlib run in an isolated environment; Endor package-risk tooling was unavailable, so no
package-security verdict is claimed. Context7 was unavailable because its API key was rejected.

From the repository root, use a fresh output directory:

```bash
python -m unittest research.tests.test_zec_cycles -v
python -m research.zec_cycles --input-dir /Users/mitch/.local/share/solmargintrader/research/zec-cycles-20261111/input --output /Users/mitch/.local/share/solmargintrader/research/zec-cycles-20261111/reproduction
```

The primary run is `/Users/mitch/.local/share/solmargintrader/research/zec-cycles-20261111/run-v1`.
Its manifest inventories every input/output hash. Compact tests, spacing, forecasts, coverage, pivots,
plots and manifest are committed under `research/results/zec_cycles_20261111_*`.
The related shape study remains separate: `research/SHAPE-AWARE-SPOT.md` and Stele TASK-1296.
This periodicity task is TASK-1307. A cycle detector or Ehlers autocorrelation indicator can describe
changing wavelengths; its existence does not establish that an apparent wavelength predicts the next turn.
"""
    report = args.repo / "research/ZEC-CYCLE-VALIDATION.md"
    report.write_text(text)
    files.append(report)
    receipt = {
        "version": 1,
        "run_manifest_sha256": sha(args.run / "manifest.json"),
        "analysis_source_sha256": manifest["source_sha256"],
        "report_source_sha256": sha(__file__),
        "outputs": {str(p.relative_to(args.repo)): sha(p) for p in files},
    }
    write_json(Path(str(prefix) + "report_manifest.json"), receipt)
    print(
        f"Verified {len(manifest['artifacts'])} run artifacts; generated report and two figures."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
