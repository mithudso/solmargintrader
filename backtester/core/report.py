"""Comparison reporting, with the caveats the numbers require.

A sorted Sharpe table is the most misleading artifact a backtester can emit.
Everything here exists to stop that: buy-and-hold is always shown as the
baseline, in-sample and out-of-sample are separate columns, and the count of
configurations evaluated is printed so a reader can weigh the selection bias.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from .engine import BacktestResult
from .types import RunManifest

NOT_ADVICE = (
    "Historical simulation for research and education only. NOT investment "
    "advice. Simulated past performance does not predict future results."
)

# Grounding for the multiple-comparisons warning.
MULTIPLE_TESTING_NOTE = """\
SELECTION BIAS WARNING -- read before acting on the ranking above.

The best of N backtests is upward-biased by the act of selection, and the bias
grows with N. Two calibration points from the literature:

  * Harvey, Liu & Zhu (2016) audited 316+ published "significant" factors and
    argued the t-statistic bar should rise from ~2.0 to ~3.0+ once multiple
    testing is accounted for. Most published factors below t = 3.0 are likely
    false discoveries.
  * McLean & Pontiff (2016) tracked 97 published factors: returns decayed 26%
    in-sample post-publication and 58% out-of-sample.

Practical reading of this report: treat the out-of-sample column as the only
column that carries evidence, treat any strategy that fails to beat
buy-and-hold as failing, and remember that a strategy you arrived at by trying
several variants has already spent some of its statistical significance."""

# Columns shown in the human-readable table, in order.
TABLE_COLUMNS = (
    "strategy",
    "total_return",
    "cagr",
    "sharpe",
    "sortino",
    "max_drawdown",
    "calmar",
    "win_rate",
    "trade_count",
    "exposure_fraction",
    "total_fees",
    "total_borrow_fees",
    "liquidation_count",
    "final_equity",
)

PERCENT_COLUMNS = frozenset(
    {
        "total_return",
        "cagr",
        "max_drawdown",
        "win_rate",
        "exposure_fraction",
        # Walk-forward split columns are the same quantities, per segment.
        "is_return",
        "oos_return",
        "is_maxdd",
        "oos_maxdd",
    }
)


@dataclass
class SplitResult:
    """One strategy's results across the full range and each split segment."""

    name: str
    full: BacktestResult
    in_sample: BacktestResult | None = None
    out_of_sample: BacktestResult | None = None


def library_versions() -> dict[str, str]:
    """Versions pinned into the manifest so a run can be reproduced."""
    versions = {"python": platform.python_version()}
    for mod in ("numpy", "pandas", "matplotlib"):
        try:
            versions[mod] = __import__(mod).__version__
        except ImportError:  # pragma: no cover - optional at runtime
            versions[mod] = "absent"
    return versions


def results_frame(results: Sequence[BacktestResult], gross: bool = False) -> pd.DataFrame:
    """One row per strategy, one column per metric."""
    rows: list[dict[str, Any]] = []
    for r in results:
        m = (r.gross_metrics if gross else r.metrics).to_dict()
        rows.append({"strategy": r.strategy_name, **m})
    return pd.DataFrame(rows)


def _fmt_cell(col: str, value: Any) -> str:
    """Format one table cell, using percentages where they are the natural unit."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, float) and not np.isfinite(value):
        return "inf" if value > 0 else "-inf"
    if col in PERCENT_COLUMNS:
        return f"{value * 100:.2f}%"
    if col in ("trade_count", "liquidation_count", "max_drawdown_bars", "bars"):
        return f"{int(value)}"
    if col in ("final_equity", "total_fees", "total_borrow_fees"):
        return f"{value:,.2f}"
    return f"{value:.3f}"


def render_table(df: pd.DataFrame, columns: Sequence[str] = TABLE_COLUMNS) -> str:
    """Fixed-width text table for stdout."""
    cols = [c for c in columns if c in df.columns]
    cells = [[_fmt_cell(c, row[c]) for c in cols] for _, row in df.iterrows()]
    headers = [c.replace("_", " ") for c in cols]
    widths = [
        max(len(headers[j]), *(len(r[j]) for r in cells)) if cells else len(headers[j])
        for j in range(len(cols))
    ]
    sep = "  "
    out = [sep.join(h.rjust(w) for h, w in zip(headers, widths))]
    out.append(sep.join("-" * w for w in widths))
    for row in cells:
        out.append(sep.join(v.rjust(w) for v, w in zip(row, widths)))
    return "\n".join(out)


def render_report(
    splits: Sequence[SplitResult],
    manifest: RunManifest,
    configurations_evaluated: int,
) -> str:
    """Full human-readable report: settings, tables, caveats."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append(f"BACKTEST REPORT -- {manifest.asset} {manifest.interval}")
    lines.append("=" * 78)
    lines.append(NOT_ADVICE)
    lines.append("")
    lines.append(
        f"Range          : {manifest.start} .. {manifest.end}  "
        f"({manifest.bar_count} bars)"
    )
    lines.append(
        f"Mode           : {manifest.mode}"
        + (f" @ {manifest.leverage:g}x" if manifest.mode == "perp" else "")
    )
    lines.append(f"Capital        : {manifest.initial_capital:,.2f}")
    lines.append(
        f"Costs          : fee {manifest.costs['fee_bps']:g}bps, "
        f"slippage {manifest.costs['slippage_bps']:g}bps"
    )
    if manifest.mode == "perp":
        lines.append(
            f"Borrow (max/hr): long {manifest.costs['max_hourly_rate_bps_long']:g}bps, "
            f"short {manifest.costs['max_hourly_rate_bps_short']:g}bps "
            f"@ utilization {manifest.costs['utilization']:g} "
            f"(floor {manifest.costs['min_hourly_rate_bps']:g}bps)"
        )
        lines.append(
            "                 Borrow fees are charged on notional to BOTH sides "
            "and are never negative."
        )
    lines.append(
        f"Fill           : signal at bar t -> fill at "
        + ("this bar's close" if manifest.fill_delay == 0 else f"t+{manifest.fill_delay} open")
    )
    lines.append(f"Sharpe         : {manifest.sharpe_convention}")
    lines.append(f"Periods/year   : {manifest.periods_per_year:g}")
    lines.append(f"Data           : {manifest.data_source} (sha256:{manifest.data_checksum})")
    lines.append(f"Seed           : {manifest.seed}")
    lines.append("")

    full = [s.full for s in splits]
    lines.append("-" * 78)
    lines.append("FULL SAMPLE -- net of fees, slippage, and borrow costs")
    lines.append("-" * 78)
    lines.append(render_table(results_frame(full)))
    lines.append("")
    lines.append("Gross (zero-cost) comparison, to show cost drag:")
    lines.append(
        render_table(
            results_frame(full, gross=True),
            ("strategy", "total_return", "cagr", "sharpe", "max_drawdown"),
        )
    )
    lines.append("")

    if any(s.in_sample is not None for s in splits):
        lines.append("-" * 78)
        lines.append("WALK-FORWARD -- in-sample vs out-of-sample (net)")
        lines.append("-" * 78)
        rows = []
        for s in splits:
            row: dict[str, Any] = {"strategy": s.name}
            for label, res in (("is", s.in_sample), ("oos", s.out_of_sample)):
                if res is None:
                    continue
                row[f"{label}_return"] = res.metrics.total_return
                row[f"{label}_sharpe"] = res.metrics.sharpe
                row[f"{label}_maxdd"] = res.metrics.max_drawdown
            rows.append(row)
        oos_df = pd.DataFrame(rows)
        lines.append(
            render_table(
                oos_df,
                [c for c in oos_df.columns],
            )
        )
        lines.append("")
        lines.append(
            "Out-of-sample indicators may warm up from the trailing in-sample "
            "bars; reading earlier history is not look-ahead."
        )
        lines.append("")

    # Baseline verdict -- stated plainly, not left to the reader to notice.
    baseline = next((s.full for s in splits if s.name == "buy_and_hold"), None)
    if baseline is not None:
        lines.append("-" * 78)
        lines.append("VERSUS BUY-AND-HOLD BASELINE")
        lines.append("-" * 78)
        base_ret = baseline.metrics.total_return
        beat, lost = [], []
        for r in full:
            if r.strategy_name == "buy_and_hold":
                continue
            delta = r.metrics.total_return - base_ret
            entry = f"  {r.strategy_name:<24} {delta * 100:+.2f} pp vs baseline"
            (beat if delta > 0 else lost).append(entry)
        lines.append(f"Baseline buy-and-hold total return: {base_ret * 100:.2f}%")
        if lost:
            lines.append("UNDERPERFORMED the baseline:")
            lines.extend(lost)
        if beat:
            lines.append("Outperformed the baseline:")
            lines.extend(beat)
        if not beat:
            lines.append(
                "No strategy beat simply holding the asset over this period."
            )
        lines.append("")

    lines.append("-" * 78)
    lines.append(f"Configurations evaluated in this run: {configurations_evaluated}")
    lines.append("-" * 78)
    lines.append(MULTIPLE_TESTING_NOTE)
    lines.append("")
    lines.append(NOT_ADVICE)
    return "\n".join(lines)


def write_outputs(
    out_dir: str | Path,
    splits: Sequence[SplitResult],
    manifest: RunManifest,
    report_text: str,
) -> list[Path]:
    """Write machine-readable results plus report.md. Returns paths written.

    Machine-readable files carry no caveat prose -- the caveats live in stdout
    and report.md, so a downstream consumer never has to parse around them.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    full = [s.full for s in splits]

    net = results_frame(full)
    net.insert(1, "book", "net")
    gross = results_frame(full, gross=True)
    gross.insert(1, "book", "gross")
    comparison = pd.concat([net, gross], ignore_index=True)
    p = out / "comparison.csv"
    comparison.to_csv(p, index=False)
    written.append(p)

    p = out / "run_manifest.json"
    p.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n")
    written.append(p)

    for s in splits:
        r = s.full
        trades = pd.DataFrame(
            [
                {
                    "timestamp": t.ts,
                    "datetime": pd.Timestamp(t.ts, unit="s", tz="UTC").isoformat(),
                    "bar_index": t.bar_index,
                    "side": t.side,
                    "reason": t.reason,
                    "price": t.price,
                    "units": t.units,
                    "notional": t.notional,
                    "fee": t.fee,
                    "slippage": t.slippage,
                    "borrow_fee_settled": t.borrow_fee_settled,
                    "realized_pnl": t.realized_pnl,
                    "equity_after": t.equity_after,
                }
                for t in r.trades
            ]
        )
        p = out / f"trades_{r.strategy_name}.csv"
        trades.to_csv(p, index=False)
        written.append(p)

        equity = pd.DataFrame(
            {
                "timestamp": r.timestamps,
                "datetime": pd.to_datetime(r.timestamps, unit="s", utc=True),
                "equity": r.equity,
                "exposure": r.exposure,
            }
        )
        p = out / f"equity_{r.strategy_name}.csv"
        equity.to_csv(p, index=False)
        written.append(p)

    p = out / "report.md"
    p.write_text("```\n" + report_text + "\n```\n")
    written.append(p)
    return written
