"""Aggregate every committed backtest result — with the evidence floor applied.

Pure logic behind the Cumulative tab. No Textual import, no widget.

## The defect this module is built to avoid

`cpcv_evaluate` marks a configuration `insufficient` when it falls below
`min_total_trades`, prints it **DROPPED**, and **still returns a full path count**.
So the obvious aggregation — read every CSV, filter `n_paths > 0`, take a median —
counts rows the engine has already refused. That is not hypothetical: BTC's
top-ranked strategy in `cpcv_all25_btc_eth_1d.csv` is `ou_reversion` at **+1.657 on
six trades**, and a naive "best configuration across all results" view would put it
at the top of the screen.

A cumulative view is the single easiest place in this repo to manufacture a
confident wrong number, because it strips every row of the context its own file
carried. So:

* every row is classified `rankable` or `below-floor`, never silently dropped and
  never silently counted;
* `n_paths` travels with every figure, because 15-path and 28-path medians are not
  the same claim and only three configurations in the whole study reached 28;
* rows from different files are **not** pooled into one ranking. Horizons, assets
  and geometries differ between files, and a median across them would describe
  nothing. Files are summarised side by side instead.

## What it does not do

No re-computation. This reads what the drivers wrote; it never re-runs a backtest,
so it cannot disagree with `verify_numbers.py`. If a figure here looks wrong, the
CSV is wrong, and the fix is in the driver that produced it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "research" / "results"

# The project's own evidence floor, matching `MIN_RANKABLE_TRADES` in
# research/cross_asset_cpcv.py and the selection checks in TOP5-RECOMMENDATION.md.
# Defined here rather than imported so this module stays independent of research/.
MIN_RANKABLE_TRADES = 10

# Column aliases. The result CSVs were written by different drivers over time and
# do not share one schema, so each field is resolved by trying known names rather
# than assuming a layout that only some files have.
COLUMNS = {
    "label": ("label", "strategy", "configuration"),
    "median_sharpe": ("median_sharpe",),
    "trades": ("total_trades", "trades"),
    "n_paths": ("n_paths",),
    "median_return": ("median_return",),
    "frac_positive": ("frac_paths_positive", "frac_positive"),
    "asset": ("asset",),
    "horizon": ("horizon",),
}


def _pick(row: dict[str, str], field_name: str) -> str | None:
    for name in COLUMNS[field_name]:
        if name in row and row[name] != "":
            return row[name]
    return None


def _as_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return None if f != f else f  # NaN -> None; an insufficient row writes NaN


def _as_int(v: str | None) -> int | None:
    f = _as_float(v)
    return None if f is None else int(f)


@dataclass(frozen=True)
class ResultRow:
    """One configuration from one result file, with its evidence intact."""

    source: str
    label: str
    asset: str
    horizon: str
    median_sharpe: float | None
    median_return: float | None
    frac_positive: float | None
    trades: int | None
    n_paths: int | None

    @property
    def rankable(self) -> bool:
        """Enough evidence to appear in a ranking.

        Both conditions matter. A row with no paths was never evaluated; a row with
        paths but too few trades was evaluated and refused. Treating them the same
        is fine here — neither may be ranked — but conflating either with a valid
        row is the defect this module exists to prevent.
        """
        return (self.n_paths or 0) > 0 and (self.trades or 0) >= MIN_RANKABLE_TRADES


@dataclass
class FileSummary:
    """One result file, summarised without pooling it with any other."""

    source: str
    rows: list[ResultRow] = field(default_factory=list)

    @property
    def rankable(self) -> list[ResultRow]:
        return [r for r in self.rows if r.rankable]

    @property
    def below_floor(self) -> list[ResultRow]:
        return [r for r in self.rows if not r.rankable]

    @property
    def positive(self) -> int:
        return sum(1 for r in self.rankable
                   if (r.median_sharpe or 0) > 0)

    @property
    def made_money(self) -> int:
        return sum(1 for r in self.rankable
                   if (r.median_return or 0) > 0)

    @property
    def median_sharpe(self) -> float | None:
        vals = [r.median_sharpe for r in self.rankable if r.median_sharpe is not None]
        return median(vals) if vals else None

    @property
    def path_range(self) -> str:
        vals = [r.n_paths for r in self.rankable if r.n_paths]
        if not vals:
            return "-"
        lo, hi = min(vals), max(vals)
        return str(lo) if lo == hi else f"{lo}-{hi}"

    @property
    def best(self) -> ResultRow | None:
        """Highest median Sharpe **among rankable rows only**."""
        ranked = [r for r in self.rankable if r.median_sharpe is not None]
        return max(ranked, key=lambda r: r.median_sharpe) if ranked else None


def load_result_file(path: Path) -> FileSummary:
    """Parse one CSV into rows, skipping files that carry no comparable figures."""
    summary = FileSummary(source=path.name)
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                sharpe = _as_float(_pick(row, "median_sharpe"))
                label = _pick(row, "label")
                if label is None and sharpe is None:
                    continue
                summary.rows.append(ResultRow(
                    source=path.name,
                    label=label or "(unnamed)",
                    asset=_pick(row, "asset") or "",
                    horizon=_pick(row, "horizon") or "",
                    median_sharpe=sharpe,
                    median_return=_as_float(_pick(row, "median_return")),
                    frac_positive=_as_float(_pick(row, "frac_positive")),
                    trades=_as_int(_pick(row, "trades")),
                    n_paths=_as_int(_pick(row, "n_paths")),
                ))
    except (OSError, csv.Error):
        return summary
    return summary


def load_all(results_dir: Path | None = None) -> list[FileSummary]:
    """Every CSV in `research/results/` that carries a `median_sharpe` column.

    Files without one are not results in the sense this tab means — they are
    parameter grids or geometry tables — and including them as empty rows would
    imply the aggregation missed something.
    """
    root = results_dir or RESULTS_DIR
    if not root.exists():
        return []
    out = []
    for p in sorted(root.glob("*.csv")):
        s = load_result_file(p)
        if s.rows:
            out.append(s)
    return out


def totals(summaries: list[FileSummary]) -> dict[str, int]:
    """Corpus-wide counts. Counts only — deliberately no pooled Sharpe.

    A median across files spanning different assets, horizons and CPCV geometries
    would be a number with no referent. Counting how much evidence exists, and how
    much of it clears the floor, is the honest aggregate.
    """
    rows = [r for s in summaries for r in s.rows]
    rankable = [r for r in rows if r.rankable]
    return {
        "files": len(summaries),
        "rows": len(rows),
        "rankable": len(rankable),
        "below_floor": len(rows) - len(rankable),
        "positive": sum(1 for r in rankable if (r.median_sharpe or 0) > 0),
        "made_money": sum(1 for r in rankable if (r.median_return or 0) > 0),
    }


def floor_casualties(summaries: list[FileSummary], limit: int = 12) -> list[ResultRow]:
    """Below-floor rows that would have ranked highly — the interesting ones.

    Sorted by the Sharpe they claim, because those are exactly the rows a naive
    aggregate would surface first, and seeing them is the point of the tab.
    """
    out = [r for s in summaries for r in s.below_floor
           if r.median_sharpe is not None and (r.n_paths or 0) > 0]
    out.sort(key=lambda r: r.median_sharpe, reverse=True)
    return out[:limit]


def headline(summaries: list[FileSummary]) -> str:
    """One line for the tab header, stating the floor rather than hiding it."""
    t = totals(summaries)
    if not t["rows"]:
        return ("No result CSVs found in research/results/ — "
                "run python3 research/cpcv_sweep.py")
    return (f"{t['files']} files · {t['rows']} configurations · "
            f"{t['rankable']} rankable at ≥{MIN_RANKABLE_TRADES} trades · "
            f"{t['below_floor']} below the floor · "
            f"{t['positive']} positive · {t['made_money']} made money")
