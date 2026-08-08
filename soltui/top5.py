"""The five recommended configurations, read from the committed evidence.

Pure logic behind the Top 5 tab. No Textual import, no widget, and — like
`cumulative.py` — no re-computation: this reads what the research drivers
wrote and cannot disagree with `verify_numbers.py`.

## Why this is not "top 5 by Sharpe"

The study's own headline finding invalidates that ranking: PBO is 0.700 for
singles at both daily horizons against a 0.500 noise line, and Spearman
ρ(in-sample, out-of-sample) is −0.419 at the medium horizon. A list titled
"top 5 by Sharpe" would be a list of the rows most likely to be noise.

The five shown here are the selection of `research/TOP5-RECOMMENDATION.md`:
drawn from the only seven configurations tested on *two independent
robustness axes* (the CPCV path distribution and ±10% parameter
perturbation), ordered by how many checks they clear, not by Sharpe. This
module does not re-derive that selection — it reads the cross-asset result
file that pinned it, `research/results/cpcv_top5_sol_doge_zec_1d.csv`, which
carries the SOL row for each configuration plus its DOGE and ZEC transfers.

Ranking within that one file does not violate `cumulative.py`'s no-pooling
rule: every row shares one geometry and one driver, and the cross-asset rows
exist precisely to be compared (`delta_vs_sol` is a column, not an
inference).

## Members are parsed from the label, not duplicated

`research/cross_asset_cpcv.py` holds the members/mode literals. Copying them
here would drift; the label ("all(dual_momentum+vol_regime)",
"obv_trend_60") already encodes them, so `parse_members` recovers them from
the string instead. A label this module cannot parse yields no members — the
tab then offers no roster shortcut for it rather than guessing.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOP5_CSV = REPO / "research" / "results" / "cpcv_top5_sol_doge_zec_1d.csv"

# The asset the recommendation was fitted on. Its rows are "the data"; every
# other asset's rows are the transfer test.
HOME_ASSET = "SOL"

# The command that regenerates the evidence file, quoted when it is missing
# and offered as the full-fidelity path for re-running the composites — the
# roster can only hold registry singles, not all()/any() combinations.
REPRO_COMMAND = "python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC"

_COMPOSITE = re.compile(r"^(all|any)\(([^)]+)\)$")


class EvidenceUnavailable(RuntimeError):
    """The result file is missing. Carries the command that regenerates it."""


@dataclass(frozen=True)
class AssetResult:
    """One configuration evaluated on one asset.

    Statistics are Optional on purpose: a figure the file does not carry (or
    carries as NaN) is *absent evidence*, and rendering it as 0.0 would
    present "not measured" as "measured at zero" — in this repo, the exact
    class of confident wrong number `cumulative.py` exists to prevent. The
    tab renders a None as "-".
    """

    asset: str
    median_sharpe: float
    delta_vs_sol: float | None
    iqr: float | None
    frac_positive: float | None
    median_return: float | None
    trades: int | None
    n_paths: int | None


@dataclass
class Top5Config:
    """One recommended configuration with its home run and its transfers."""

    rank: int
    label: str
    horizon: str
    results: list[AssetResult] = field(default_factory=list)

    @property
    def home(self) -> AssetResult | None:
        return next((r for r in self.results if r.asset == HOME_ASSET), None)

    @property
    def transfers(self) -> list[AssetResult]:
        return [r for r in self.results if r.asset != HOME_ASSET]

    @property
    def members(self) -> tuple[str, ...]:
        return parse_members(self.label)[0]

    @property
    def mode(self) -> str:
        return parse_members(self.label)[1]


def parse_members(label: str) -> tuple[tuple[str, ...], str]:
    """(member strategy names, combine mode) recovered from a label.

    "all(dual_momentum+vol_regime)" -> (("dual_momentum", "vol_regime"), "all")
    "obv_trend_60"                  -> (("obv_trend",), "single")

    For a single, trailing numeric parameter tokens are stripped
    ("vol_regime_60_0.5" -> "vol_regime") because the roster resolves
    registry *names*; the parameter values stay visible in the label column.
    An unparseable label returns no members rather than a guess.
    """
    m = _COMPOSITE.match(label.strip())
    if m:
        mode, inner = m.group(1), m.group(2)
        members = tuple(p.strip() for p in inner.split("+") if p.strip())
        return (members, mode) if members else ((), "")
    if "(" in label or ")" in label:
        # Composite-shaped but not parseable as one ("all()", "any(x"): must
        # not fall through to the single-name path, which would hand the
        # roster a garbage "member" like "all()".
        return ((), "")
    tokens = label.strip().split("_")
    while tokens and re.fullmatch(r"[0-9.]+", tokens[-1]):
        tokens.pop()
    name = "_".join(tokens)
    return ((name,), "single") if name else ((), "")


def _f(row: dict[str, str], col: str) -> float | None:
    """A float from the row, or None when absent/unparseable/NaN.

    Same policy as `cumulative._as_float`: NaN is what the engine writes for
    an insufficient row, and it must surface as "no value", never as 0.0.
    """
    try:
        v = float(row.get(col, ""))
    except ValueError:
        return None
    return None if v != v else v


def _i(row: dict[str, str], col: str) -> int | None:
    v = _f(row, col)
    return None if v is None else int(v)


def load_top5(csv_path: Path | None = None) -> list[Top5Config]:
    """The five configurations, rank order, each with all its asset rows.

    Raises `EvidenceUnavailable` with the regeneration command rather than
    returning an empty list: an empty Top 5 tab reads as "nothing was ever
    recommended", which is a worse diagnostic than one sentence saying the
    evidence file is absent.
    """
    src = csv_path or TOP5_CSV
    if not src.exists():
        raise EvidenceUnavailable(
            f"{src.name} is missing. Regenerate it:  {REPRO_COMMAND}")
    configs: dict[int, Top5Config] = {}
    try:
        with src.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    rank = int(row["rank"])
                except (KeyError, ValueError):
                    continue
                sharpe = _f(row, "median_sharpe")
                if sharpe is None:
                    # A row with no median Sharpe carries no evidence at all;
                    # keeping it would put a blank line in a ranking.
                    continue
                cfg = configs.setdefault(rank, Top5Config(
                    rank=rank,
                    label=row.get("label", "(unnamed)"),
                    horizon=row.get("horizon", ""),
                ))
                q1, q3 = _f(row, "q1_sharpe"), _f(row, "q3_sharpe")
                cfg.results.append(AssetResult(
                    asset=row.get("asset", ""),
                    median_sharpe=sharpe,
                    delta_vs_sol=_f(row, "delta_vs_sol"),
                    iqr=None if q1 is None or q3 is None else q3 - q1,
                    frac_positive=_f(row, "frac_paths_positive"),
                    median_return=_f(row, "median_return"),
                    trades=_i(row, "total_trades"),
                    n_paths=_i(row, "n_paths"),
                ))
    except (OSError, csv.Error) as exc:
        raise EvidenceUnavailable(f"{src.name} could not be read: {exc}") from exc
    if not configs:
        raise EvidenceUnavailable(
            f"{src.name} exists but contains no configuration rows — "
            f"it may be truncated. Regenerate it:  {REPRO_COMMAND}")
    return [configs[r] for r in sorted(configs)]


def roster_candidates(configs: list[Top5Config]) -> list[str]:
    """Every distinct member strategy across the five, first-seen order.

    These are what "add to roster" can honestly offer: the roster holds
    registry singles, so a composite's *members* can be swept individually,
    but the all()/any() combination itself cannot — reproducing the actual
    composites is `REPRO_COMMAND`'s job, and the tab says so.
    """
    seen: list[str] = []
    for cfg in configs:
        for name in cfg.members:
            if name not in seen:
                seen.append(name)
    return seen
