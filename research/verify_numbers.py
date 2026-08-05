"""Assert every performance figure in the research documents came from the sweep.

The documents' entire credibility rests on "no number was estimated". A
transcription slip is indistinguishable from a fabrication to a reader, so this
checks the whole surface rather than a sample. Every figure is checked against the
run that produced it -- `sweep_results.csv` for the walk-forward tables, the CPCV
results for the CPCV tables, `perturb_*.csv` for the perturbation tables -- and the
derived block-count figures of finding 1f (medians across geometries, spreads, rank
movements, correlations) are RECOMPUTED from the per-block medians, because no CSV
contains a "median across geometries" to look up. The PBO figures quoted in the same
finding are the exception: those are a lookup against the sweep's JSON sidecars.

    python3 research/verify_numbers.py        # exit 0 iff every figure matches

Deliberately conservative: it only checks rows it can unambiguously parse, and
reports how many figures it verified so a low count is visible rather than
silently passing.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH = Path(__file__).resolve().parent
CSV = RESEARCH / "results" / "sweep_results.csv"
DOCS = (RESEARCH / "RANKED_LISTS.md", RESEARCH / "STRATEGIES.md")

# How many figures each document is known to contain.
#
# Without this the script has no floor: every check is driven by a regex, so a table
# whose format drifts simply stops matching, and the run prints a pass having quietly
# verified fewer numbers than it did yesterday. Measured: deleting six CPCV rows took
# the count from 923 to 893 and still exited 0. The `checked < 100` backstop below
# only catches a collapse, not a leak.
#
# To be exact about the guarantee, since it is easy to read as more: this detects a
# DROP from the set currently recognised. It cannot detect a figure that was never
# recognised in the first place -- one of those does not lower the count. It prevents
# regression; it does not prove completeness, and "EVERY PARSED FIGURE MATCHES" below
# carries real weight on the word "parsed".
#
# Update these in the same commit that changes the documents' figures -- deliberately,
# after reading the new count. Never lower one to make a red run go green; that is
# the same act as deleting the evidence.
EXPECTED_FIGURES = {
    "RANKED_LISTS.md": {
        "prose": 8, "walk_forward": 180, "cpcv": 615,
        "perturb": 7, "geometry": 58, "pair": 36,
    },
    "STRATEGIES.md": {"prose": 31},
}

# Sharpe values are quoted to 3dp, returns to 1dp; allow half a unit of the
# last printed digit plus a little slack for rounding direction.
TOL_SHARPE = 0.0006
TOL_PCT = 0.06

# Table rows look like:
#   | 1 | `label` | family | **+0.488** | -2.490 | +3.4% | -59.7% | -11.8% | 29 |
ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|[^|]*\|"          # rank | label | family
    r"\s*\*{0,2}([-+]?\d+\.\d+)\*{0,2}\s*\|"           # OOS sharpe
    r"\s*\*{0,2}([-+]?\d+\.\d+)\*{0,2}\s*\|"           # IS sharpe
    r"\s*\*{0,2}([-+]?\d+\.\d+)%\*{0,2}\s*\|"          # OOS return
    r"\s*\*{0,2}([-+]?[\d,]+\.\d+)%\*{0,2}\s*\|"       # IS return
    r"\s*\*{0,2}([-+]?\d+\.\d+)%\*{0,2}\s*\|"          # OOS maxdd
    r"\s*\*{0,2}(\d+)\*{0,2}\s*\|",                    # OOS trades
    re.M,
)

# Simpler 4-column pair tables: | `label` | +2.572 | -1.407 | +9.0% | 18 |
PAIR_ROW = re.compile(
    r"^\|\s*`([^`]+)`\s*\|"
    r"\s*([-+]?\d+\.\d+)\s*\|"
    r"\s*([-+]?\d+\.\d+)\s*\|"
    r"\s*([-+]?\d+\.\d+)%\s*\|"
    r"\s*(\d+)\s*\|",
    re.M,
)

# STRATEGIES.md states figures in prose rather than tables, e.g.
#   "IS +1,932.1% (Sharpe 1.494) -> OOS -69.2% (Sharpe -1.383)"
#   "OOS Sharpe +0.488"
PROSE_IS_OOS = re.compile(
    r"IS\s+([-+]?[\d,]+\.\d+)%\s*\(Sharpe\s*([-+]?\d+\.\d+)\)"
    r".{0,40}?OOS\s+([-+]?[\d,]+\.\d+)%\s*\(Sharpe\s*([-+]?\d+\.\d+)\)",
    re.S,
)
PROSE_OOS_SHARPE = re.compile(r"OOS Sharpe\s*\*{0,2}([-+]?\d+\.\d+)")


def normalise(text: str) -> str:
    """ASCII-ify typographic characters that break numeric regexes.

    The documents are written with U+2212 MINUS SIGN and U+2013 EN DASH for
    readability. Matching on the raw text silently finds far fewer figures than
    exist -- which is exactly the failure this script is supposed to catch, so
    it must not be the failure this script contains.
    """
    return (
        text.replace("−", "-")   # minus sign
        .replace("–", "-")       # en dash
        .replace("—", "-")       # em dash
        .replace(" ", " ")       # nbsp
    )


CPCV_CSV = RESEARCH / "results" / "cpcv_results.csv"

# CPCV table rows:
#   | 1 | `label` | family | **+0.534** | 1.434 | 68% | +9.4% | 16 |
CPCV_ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|[^|]*\|"
    r"\s*\*{0,2}([-+]?\d+\.\d+)\*{0,2}\s*\|"      # median sharpe
    r"\s*([-+]?\d+\.\d+)\s*\|"                    # iqr
    r"\s*\*{0,2}(\d+)%\*{0,2}\s*\|"               # % paths positive
    r"\s*\*{0,2}([-+]?\d+\.\d+)%\*{0,2}\s*\|"     # median path return
    r"\s*(\d+)\s*\|",                             # trades
    re.M,
)


def spearman(a: list[float], b: list[float]) -> float:
    """Rank correlation, defined here rather than imported from research.geometry.

    To be exact about what this buys, because it is easy to overclaim: two identical
    copies cannot catch a bug that was always in both. What separation does prevent
    is a LATER edit to geometry.py silently redefining the thing that checks it. The
    real independence lives in geometry_stats, which re-derives every figure from the
    raw per-block medians by a different route than render() used.

    The len<3 guard mirrors research.geometry.spearman deliberately: if the two
    disagreed on degenerate input, one would return NaN while the other returned a
    confident +/-1.0, and only the NaN is honest.
    """
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    if len(ra) < 3 or ra.std() == 0 or rb.std() == 0:
        # A constant ranking has no order to correlate with. numpy would divide by a
        # zero standard deviation, warn, and hand back NaN; say NaN outright instead.
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def load() -> pd.DataFrame:
    """Sweep results, indexed for lookup by label."""
    if not CSV.exists():
        raise SystemExit(f"missing {CSV}; run: python3 research/sweep.py")
    return pd.read_csv(CSV)


CPCV_COMBOS_CSV = RESEARCH / "results" / "cpcv_combos_results.csv"
PERTURB_GLOB = "perturb_*.csv"
# Heading that opens the perturbation results, used to scope the match.
PERTURB_SECTION = "### 1d. The top pair survives parameter perturbation"

# Perturbation tables are 4-column and would not be matched by the 8-column
# CPCV_ROW pattern, so they need their own extraction. Without this the figures in
# finding 1d would sit in the document unverified, quietly weakening the
# "every number is checked" guarantee this whole script exists for.
PERTURB_ROW = re.compile(
    r"^\|\s*(?:\*\*)?(?:baseline|`[^`]+`|geometry:[^|]*?)(?:\*\*)?\s*\|"
    r"\s*\*{0,2}([-+]?\d+\.\d+)\*{0,2}\s*\|",
    re.M,
)


GEOMETRY_GLOB = "geometry_*.csv"
# Heading that opens the block-count sweep results, used to scope the match.
GEOMETRY_SECTION = "### 1f."

# The geometry tables report DERIVED quantities -- a median across block counts, a
# spread, a rank movement -- none of which appear as a number in any CSV. So unlike
# every other check here, these are recomputed from the raw per-block medians rather
# than looked up. Recomputing independently of research/geometry.py is deliberate: a
# lookup against that script's own text report would only prove the report was
# copied faithfully, not that the arithmetic behind it is right.
GEOMETRY_VERDICT_ROW = re.compile(
    r"^\|\s*\*{0,2}(Short|Medium|Long)\*{0,2}\s*\|"
    r"\s*\*{0,2}([-+]?\d+\.\d+)\*{0,2}\s*\|"
    r"\s*\*{0,2}(\d+) of (\d+)\*{0,2}\s*\|"
    r"\s*\*{0,2}(\d+)\*{0,2}\s*\|"
    r"\s*\*{0,2}([a-z -]+?)\*{0,2}\s*\|",
    re.M,
)


def verdict_label(mean_rho: float, winners: int) -> str:
    """The reader-facing word, re-derived from the recomputed statistics.

    Deliberately NOT research.geometry.verdict: this must be able to disagree with the
    script that produced the table. Kept in step with geometry.verdict's thresholds --
    if those move, this fails and says so, which is the correct outcome.
    """
    if mean_rho >= 0.9 and winners == 1:
        return "geometry-stable"
    return "mostly stable" if mean_rho >= 0.7 else "geometry-dependent"
GEOMETRY_STRATEGY_ROW = re.compile(
    r"^\|\s*`([a-z0-9_]+)`\s*\|"
    r"\s*\*{0,2}([-+]?\d+\.\d+)\*{0,2}\s*\|"
    r"\s*\*{0,2}(\d+\.\d+)\*{0,2}\s*\|"
    r"\s*\*{0,2}(\d+)\*{0,2}\s*\|"
    r"\s*\*{0,2}(\d+)/(\d+)\*{0,2}\s*\|",
    re.M,
)
# {2,3} rather than {3}: "0.70 (8 blocks)" is a perfectly natural way to write it and
# would otherwise not match, dropping the figure with no complaint.
GEOMETRY_PBO = re.compile(r"\*{0,2}(\d\.\d{2,3})\*{0,2}\s*\((\d+)(?:\s*blocks\b)?\)")
GEOMETRY_RANKCORR = re.compile(r"how far its rank moves is\s*\*{0,2}([-+]?\d+\.\d+)")
GEOMETRY_MEANMOVE = re.compile(
    r"move a mean of\s*\*{0,2}(\d+\.\d+)\*{0,2}\s*places;? everyone else\s*\*{0,2}(\d+\.\d+)",
    re.S,
)


def load_geometry() -> dict[str, pd.DataFrame]:
    """Per-horizon block-count sweep results; empty when none have been run.

    Refuses to merge two files covering one horizon. The filename encodes k
    (`geometry_long_k2.csv`) because several k can coexist, and the document's
    figures came from exactly one of them -- silently keeping whichever sorted last
    would verify against evidence that did not produce the number.
    """
    out: dict[str, pd.DataFrame] = {}
    seen: dict[str, str] = {}
    for path in sorted((RESEARCH / "results").glob(GEOMETRY_GLOB)):
        frame = pd.read_csv(path)
        for horizon, part in frame.groupby("horizon"):
            key = str(horizon)
            if key in seen:
                raise SystemExit(
                    f"two geometry result files cover the {key!r} horizon: "
                    f"{seen[key]} and {path.name}. The document quotes one k; "
                    "verifying against a mix of both would prove nothing. "
                    "Remove the stale file."
                )
            seen[key] = path.name
            out[key] = part
    return out


def load_geometry_pbo() -> dict[tuple[str, int], float]:
    """PBO per (horizon, block count) from the sweep's JSON sidecars.

    Refuses two sidecars covering one horizon, for the same reason load_geometry does.
    This is a separate glob from the CSVs, and the realistic case is an aborted run
    leaving `geometry_long_k3.json` behind with no sibling CSV -- so the CSV loader's
    guard never sees it.
    """
    pbo: dict[tuple[str, int], float] = {}
    seen: dict[str, str] = {}
    for path in sorted((RESEARCH / "results").glob("geometry_*.json")):
        horizon = path.stem.split("_")[1]
        if horizon in seen and seen[horizon] != path.name:
            raise SystemExit(
                f"two geometry sidecars cover the {horizon!r} horizon: {seen[horizon]} "
                f"and {path.name}. Remove the stale one; the document quotes one run."
            )
        seen[horizon] = path.name
        for entry in json.loads(path.read_text()):
            pbo[(horizon, int(entry["blocks"]))] = float(entry["pbo"])
    return pbo


def geometry_stats(part: pd.DataFrame) -> dict:
    """Recompute every derived geometry figure from the raw per-block medians.

    `rank` here is position by median Sharpe, best first, which is why the sort is
    descending -- ranking ascending would silently invert every movement figure.
    """
    blocks = sorted(part.blocks.unique())
    dupes = part.duplicated(subset=["strategy", "blocks"]).sum()
    if dupes:
        # pivot_table would average them and produce a plausible wrong number.
        raise SystemExit(
            f"{dupes} duplicate (strategy, blocks) rows in the geometry results; "
            "regenerate them rather than averaging over the duplicates"
        )
    wide = part.pivot_table(index="strategy", columns="blocks", values="median_sharpe")
    if wide.dropna().empty:
        raise SystemExit(
            "no strategy in the geometry results is evaluable at every block count, "
            "so no ranking can be compared across them"
        )
    # Comparability: a strategy missing at any block count cannot be ranked across
    # them, and including it would manufacture rank movement out of absence.
    wide = wide.dropna()
    ranks = wide.rank(ascending=False, method="first")
    movement = (ranks.max(axis=1) - ranks.min(axis=1)).astype(int)
    best_rank = ranks.min(axis=1).astype(int)
    top3 = (ranks <= 3).sum(axis=1).astype(int)

    rhos = []
    for i, j in itertools.combinations(blocks, 2):
        rhos.append(spearman(list(wide[i]), list(wide[j])))
    winners = {wide[b].idxmax() for b in blocks}
    held_first = best_rank == 1
    return {
        "blocks": blocks,
        "n": len(wide),
        "median": wide.median(axis=1),
        "hi": wide.max(axis=1),
        "lo": wide.min(axis=1),
        "leader": {int(b): str(wide[b].idxmax()) for b in blocks},
        "spread": wide.max(axis=1) - wide.min(axis=1),
        "movement": movement,
        "top3": top3,
        "mean_rho": float(np.mean(rhos)),
        "median_movement": float(np.median(movement)),
        "winners": winners,
        "rankcorr": spearman(list(best_rank), list(movement)),
        "mean_move_winners": float(movement[held_first].mean()),
        "mean_move_others": float(movement[~held_first].mean()),
    }

def load_perturb() -> pd.DataFrame | None:
    """Every perturbation result concatenated; None when none have been run."""
    paths = sorted((RESEARCH / "results").glob(PERTURB_GLOB))
    if not paths:
        return None
    return pd.concat([pd.read_csv(x) for x in paths], ignore_index=True)


def load_cpcv() -> pd.DataFrame | None:
    """CPCV results (singles and combinations), if those sweeps have been run.

    Singles and combinations share the same column schema, so they are
    concatenated and looked up by label -- a CPCV table row in the document does
    not say which sweep produced it, and it does not need to.
    """
    frames = [pd.read_csv(p) for p in (CPCV_CSV, CPCV_COMBOS_CSV) if p.exists()]
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def candidates(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """All rows matching a label across horizons."""
    return df[df.label == label]


def check(
    df: pd.DataFrame, label: str, field: str, value: float, tol: float
) -> tuple[bool, str]:
    """True when `value` matches `field` for `label` in ANY horizon.

    Horizon is not always recoverable from a lone table row, so a match in any
    horizon is accepted; the label plus five simultaneously-matching fields
    makes a false positive implausible.
    """
    rows = candidates(df, label)
    if rows.empty:
        return False, f"label not in sweep results: {label!r}"
    got = rows[field].to_numpy()
    if any(abs(g - value) <= tol for g in got):
        return True, ""
    return False, (
        f"{label} {field}: doc says {value}, sweep has "
        + ", ".join(f"{g:.4f}" for g in got)
    )


# Spread is printed to 2dp, so half a unit is 0.005 -- exactly the rounding boundary.
# Several real spreads sit within 5e-4 of it (buy_and_hold 0.27459), so a tolerance of
# exactly 0.005 would turn a benign regeneration into a MISMATCH on a figure that is
# correct to 2dp. Same half-unit-plus-slack reasoning as TOL_PCT.
TOL_SPREAD = 0.0055

# Marker for the paragraph quoting PBO per block count. PBO figures must be tied to
# the horizon they are quoted under, and the horizon only appears in the prose.
GEOMETRY_PBO_MARKER = "PBO is not geometry-invariant"
# Header of the per-strategy invariance table. Used to count its rows STRUCTURALLY:
# requiring merely "some rows matched" lets a single reformatted row drop out of
# verification while the others keep the run green.
GEOMETRY_TABLE_HEADER = "| Strategy | median across"

# "`macd` (6, 10)" -- which strategy topped the leaderboard at which block counts.
# The correction to finding 1e rests on obv_trend having been first at 8 and nowhere
# else, so the identities are checked, not just the count of distinct winners.
GEOMETRY_WINNER = re.compile(r"`([a-z0-9_]+)`\s*\(([\d,\s]+)\)")
GEOMETRY_WINNER_MARKER = "hold first place across"
# "ranging from +0.78 to -0.60"
# Bounded rather than [^.]*? because the intervening prose quotes "+0.604" and a class
# excluding "." cannot cross its decimal point. (?!`) forbids an intervening backtick,
# which pins the range to the NEAREST preceding strategy name -- without it the lazy
# quantifier reaches back past `adx_trend` and attributes the range to `obv_trend`.
GEOMETRY_RANGE = re.compile(
    r"`([a-z0-9_]+)`(?:(?!`)[\s\S]){0,240}?ranging from"
    r"\s*([-+]?\d+\.\d+)\s*to\s*([-+]?\d+\.\d+)"
)
GEOMETRY_HORIZON_WORD = re.compile(r"\b(short|medium|long)\b", re.I)


def markdown_table_rows(section: str, header: str) -> int | None:
    """Count data rows under `header`, or None when the header itself is gone.

    Structural count, independent of the field regexes, so a row that stops matching
    is visible as a shortfall rather than as silence.
    """
    if header not in section:
        return None
    lines = section[section.index(header):].split("\n")
    rows = 0
    for line in lines[1:]:
        if not line.startswith("|"):
            break
        if set(line) <= set("|- :"):   # the |---|---| separator
            continue
        rows += 1
    return rows


class Tally:
    """Figures checked, counted per pattern family.

    A single per-document total lets a loss in one table be masked by a gain in
    another: six figures dropped from the CPCV tables and six added to the geometry
    tables net to zero and pass. Counting per family closes that, and makes the
    failure message name the table that moved.
    """

    def __init__(self) -> None:
        self.per: dict[str, int] = {}

    def add(self, family: str, n: int = 1) -> None:
        self.per[family] = self.per.get(family, 0) + n

    @property
    def total(self) -> int:
        return sum(self.per.values())


def census_failures(per_doc: dict[str, dict[str, int]]) -> list[str]:
    """Complain when any family's recognised count moves in either direction."""
    out = []
    for name, got in sorted(per_doc.items()):
        want = EXPECTED_FIGURES.get(name)
        if want is None:
            continue
        for family in sorted(set(want) | set(got)):
            expected, actual = want.get(family, 0), got.get(family, 0)
            if actual == expected:
                continue
            if actual < expected:
                out.append(
                    f"{name}: the {family} tables yielded only {actual} figures but "
                    f"{expected} are expected, so {expected - actual} went unchecked "
                    "-- that table's format has drifted"
                )
            else:
                out.append(
                    f"{name}: the {family} tables yielded {actual} figures but only "
                    f"{expected} are expected. If figures were added deliberately, "
                    f"set EXPECTED_FIGURES[{name!r}][{family!r}] to {actual}"
                )
    return out


def check_geometry(section: str, geometry: dict[str, pd.DataFrame]) -> tuple[int, list[str]]:
    """Verify finding 1f by recomputing every figure from the per-block medians.

    Returns (figures checked, failure messages). A figure that cannot be recomputed
    is a failure, never a skip: the whole point of this script is that "the run said
    PASS" and "the numbers were checked" are the same statement.
    """
    checked = 0
    failures: list[str] = []
    stats = {h: geometry_stats(part) for h, part in geometry.items()}

    def compare(what: str, doc_val: float, got: float, tol: float) -> None:
        """Record a failure unless the doc value matches the recomputed one.

        `not isfinite(got)` is load-bearing. `abs(x - nan) > tol` is False, so the
        naive form silently PASSES an unrecomputable figure -- the exact failure mode
        this file exists to prevent.
        """
        nonlocal checked
        checked += 1
        if not np.isfinite(got) or abs(doc_val - got) > tol:
            failures.append(f"geometry {what}: doc says {doc_val}, recomputed {got:.4f}")

    seen_horizons: set[str] = set()
    for m in GEOMETRY_VERDICT_ROW.finditer(section):
        horizon, rho, move, total, winners, label = m.groups()
        key = horizon.lower()
        seen_horizons.add(key)
        s = stats.get(key)
        if s is None:
            checked += 1
            failures.append(f"no geometry results for {key!r}")
            continue
        compare(f"{key} mean Spearman", float(rho), s["mean_rho"], TOL_SHARPE)
        compare(f"{key} median rank movement", float(move), s["median_movement"], 0.5)
        compare(f"{key} comparable count", float(total), float(s["n"]), 0.5)
        compare(f"{key} distinct winners", float(winners), float(len(s["winners"])), 0.5)
        checked += 1
        want = verdict_label(s["mean_rho"], len(s["winners"]))
        if label.strip().lower() != want:
            failures.append(
                f"geometry {key} verdict: the table says {label.strip()!r} but the "
                f"recomputed statistics give {want!r}"
            )

    # Format drift would otherwise drop these figures while the run still reported a
    # pass, because the total stays well above the `checked < 100` backstop.
    for missing in sorted(set(stats) - seen_horizons):
        failures.append(
            f"the 1f verdict table has no row for the {missing!r} horizon, but "
            f"geometry results for it exist -- those figures went unchecked"
        )

    # The per-strategy invariance table is long-horizon only.
    long_stats = stats.get("long")
    if long_stats is None:
        failures.append("no long-horizon geometry results; the 1f invariance table "
                        "and its prose figures could not be checked")
        return checked, failures

    rows = 0
    for m in GEOMETRY_STRATEGY_ROW.finditer(section):
        name, med, spread, move, top3, n_geom = m.groups()
        rows += 1
        if name not in long_stats["median"].index:
            checked += 1
            failures.append(f"strategy not in geometry results: {name!r}")
            continue
        compare(f"long {name} median", float(med), long_stats["median"][name], TOL_SHARPE)
        compare(f"long {name} spread", float(spread), long_stats["spread"][name], TOL_SPREAD)
        compare(f"long {name} rank movement", float(move),
                float(long_stats["movement"][name]), 0.5)
        compare(f"long {name} top-3 count", float(top3),
                float(long_stats["top3"][name]), 0.5)
        compare(f"long {name} geometry count", float(n_geom),
                float(len(long_stats["blocks"])), 0.5)
    expected = markdown_table_rows(section, GEOMETRY_TABLE_HEADER)
    if expected is None:
        failures.append(f"the 1f invariance table header ({GEOMETRY_TABLE_HEADER!r}) is "
                        "missing, so its rows could not be counted or checked")
    elif rows != expected:
        failures.append(
            f"the 1f invariance table has {expected} rows but only {rows} matched the "
            "field pattern, so the rest went unchecked"
        )

    m = GEOMETRY_RANKCORR.search(section)
    if m is None:
        failures.append("the best-rank/movement correlation sentence did not match; "
                        "that figure went unchecked")
    else:
        compare("best-rank/movement correlation", float(m.group(1)),
                long_stats["rankcorr"], TOL_SHARPE)

    m = GEOMETRY_MEANMOVE.search(section)
    if m is None:
        failures.append("the mean-rank-movement sentence did not match; those two "
                        "figures went unchecked")
    else:
        compare("winner mean movement", float(m.group(1)),
                long_stats["mean_move_winners"], 0.05)
        compare("other mean movement", float(m.group(2)),
                long_stats["mean_move_others"], 0.05)

    checked += _check_geometry_winners(section, long_stats, failures)

    m = GEOMETRY_RANGE.search(section)
    if m is None:
        failures.append("the min/max range sentence did not match; those figures "
                        "went unchecked")
    else:
        name, hi, lo = m.group(1), float(m.group(2)), float(m.group(3))
        if name not in long_stats["hi"].index:
            checked += 1
            failures.append(f"range quoted for a strategy not in the results: {name!r}")
        else:
            compare(f"long {name} max", hi, long_stats["hi"][name], 0.0055)
            compare(f"long {name} min", lo, long_stats["lo"][name], 0.0055)

    checked += _check_geometry_pbo(section, failures)
    return checked, failures


def _check_geometry_winners(section: str, long_stats: dict, failures: list[str]) -> int:
    """Check the "who was first at which block count" list against the recomputation.

    Counting six distinct winners says nothing about WHICH six. The 1e correction
    turns on obv_trend having led at 8 blocks specifically, so verify the mapping.
    """
    if GEOMETRY_WINNER_MARKER not in section:
        failures.append(f"could not locate the winners sentence "
                        f"({GEOMETRY_WINNER_MARKER!r}); the mapping went unchecked")
        return 0
    at = section.index(GEOMETRY_WINNER_MARKER)
    end = section.find("\n\n", at)
    para = section[at : end if end != -1 else len(section)]

    leaders: dict[int, str] = long_stats["leader"]
    checked = 0
    claimed: dict[int, str] = {}
    for m in GEOMETRY_WINNER.finditer(para):
        name = m.group(1)
        for raw in m.group(2).split(","):
            raw = raw.strip()
            if not raw.isdigit():
                continue
            claimed[int(raw)] = name
    if not claimed:
        failures.append("the winners sentence matched no `strategy` (blocks) pairs; "
                        "the mapping went unchecked")
        return 0
    for blocks, name in sorted(claimed.items()):
        checked += 1
        actual = leaders.get(blocks)
        if actual is None:
            failures.append(f"a winner is claimed at {blocks} blocks, which is not in "
                            "the geometry results")
        elif actual != name:
            failures.append(f"the leader at {blocks} blocks is {actual!r}, but the "
                            f"document says {name!r}")
    missing = sorted(set(leaders) - set(claimed))
    if missing:
        failures.append(f"no leader is stated for block counts {missing}, so those "
                        "went unchecked")
    return checked


def _check_geometry_pbo(section: str, failures: list[str]) -> int:
    """Check each quoted PBO against the sidecar for the horizon it is quoted under.

    Matching on block count alone would let a long-horizon figure verify against a
    medium-horizon run: at 8 blocks both happen to be 0.700, so the check would pass
    on the wrong evidence.
    """
    pbo = load_geometry_pbo()
    if not pbo:
        failures.append(
            "no geometry_*.json sidecars, so every quoted PBO went unchecked; "
            "regenerate with research/geometry.py"
        )
        return 0
    if GEOMETRY_PBO_MARKER not in section:
        failures.append(f"could not locate the PBO paragraph ({GEOMETRY_PBO_MARKER!r}); "
                        "the quoted PBO figures went unchecked")
        return 0

    para_start = section.index(GEOMETRY_PBO_MARKER)
    end = section.find("\n\n", para_start)
    para = section[para_start : end if end != -1 else len(section)]

    # Attribution needs the horizon named nearby, so only this paragraph can be walked
    # reliably. A PBO quoted anywhere else in the finding would therefore go unchecked
    # -- so refuse it explicitly rather than passing over it.
    stray = len(GEOMETRY_PBO.findall(section)) - len(GEOMETRY_PBO.findall(para))
    if stray > 0:
        failures.append(
            f"{stray} PBO figure(s) are quoted in finding 1f outside the paragraph "
            f"beginning {GEOMETRY_PBO_MARKER!r}; only that paragraph names the horizon "
            "each belongs to, so they cannot be attributed or checked"
        )

    # Walk the paragraph in order, carrying the most recent horizon word, so
    # "At the long horizon ... 0.800 (6 blocks) ... ; at medium, 0.445 (12)"
    # attributes each figure to the right run.
    events = [(mm.start(), "h", mm.group(1).lower())
              for mm in GEOMETRY_HORIZON_WORD.finditer(para)]
    events += [(mm.start(), "v", mm.groups()) for mm in GEOMETRY_PBO.finditer(para)]
    events.sort()

    checked = 0
    horizon: str | None = None
    for _, kind, payload in events:
        if kind == "h":
            horizon = payload
            continue
        value, blocks = float(payload[0]), int(payload[1])
        checked += 1
        if horizon is None:
            failures.append(f"PBO {value} at {blocks} blocks is quoted before any "
                            "horizon is named, so it cannot be attributed")
            continue
        got = pbo.get((horizon, blocks))
        if got is None:
            failures.append(f"PBO {value}: no {horizon} sidecar entry at {blocks} blocks")
        elif not np.isfinite(got):
            # geometry.py writes NaN when it could not compute PBO for a geometry, and
            # json round-trips it. `abs(nan - v) > tol` is False, so without this the
            # figure is counted as checked and compared against nothing.
            failures.append(
                f"PBO at {horizon} {blocks} blocks: the sidecar value is not a number, "
                f"so the quoted {value} was compared against nothing"
            )
        elif abs(got - value) > TOL_SHARPE:
            failures.append(f"PBO at {horizon} {blocks} blocks: doc says {value}, "
                            f"sidecar has {got:.4f}")
    return checked

def main() -> int:
    """Verify every parseable figure; exit non-zero on any mismatch."""
    df = load()
    cpcv = load_cpcv()
    perturb = load_perturb()
    geometry = load_geometry()
    checked = 0
    failures: list[str] = []
    per_doc: dict[str, int] = {}

    def check_cpcv(label: str, field: str, value: float, tol: float) -> tuple[bool, str]:
        """Match a CPCV figure against the CPCV results for any horizon.

        A missing results file is reported by the preflight below, never treated
        as a pass -- silently counting unverifiable figures as verified is the
        one failure mode this whole script exists to prevent.
        """
        if cpcv is None:
            return False, f"no CPCV results loaded, cannot verify {label!r}"
        rows = cpcv[cpcv.label == label]
        if rows.empty:
            return False, f"CPCV label not in results: {label!r}"
        got = rows[field].to_numpy()
        if any(abs(g - value) <= tol for g in got):
            return True, ""
        return False, (
            f"CPCV {label} {field}: doc says {value}, results have "
            + ", ".join(f"{g:.4f}" for g in got)
        )

    # -- preflight: are the results complete enough to verify against? --------
    # Without this, stale or partial results produce hundreds of per-figure
    # mismatches that look like the DOCUMENTS are wrong, when the real problem is
    # that the evidence was never regenerated. Fail once, clearly, up front.
    doc_labels: set[str] = set()
    for d in DOCS:
        if d.exists():
            t = normalise(d.read_text())
            doc_labels |= {m.group(1) for m in CPCV_ROW.finditer(t)}
    if doc_labels:
        if cpcv is None:
            print(
                "PREFLIGHT FAIL: the documents contain CPCV tables but no CPCV "
                "results were found.\n  Regenerate with:\n"
                "    python3 research/cpcv_sweep.py\n"
                "    python3 research/cpcv_sweep.py --stage pairs --stage triples",
                file=sys.stderr,
            )
            return 1
        unknown = sorted(doc_labels - set(cpcv.label))
        if unknown:
            print(
                f"PREFLIGHT FAIL: {len(unknown)} of {len(doc_labels)} CPCV labels in the "
                f"documents are absent from the results, so the results are stale or "
                f"incomplete.\n  Missing e.g.: {', '.join(unknown[:4])}\n"
                "  Regenerate BOTH sweeps before trusting any figure:\n"
                "    python3 research/cpcv_sweep.py\n"
                "    python3 research/cpcv_sweep.py --stage pairs --stage triples",
                file=sys.stderr,
            )
            return 1

    # A geometry section with no geometry results is the same failure mode as the
    # CPCV preflight above: the figures would simply go unchecked and the run would
    # report success.
    has_geometry_section = any(
        d.exists() and GEOMETRY_SECTION in d.read_text() for d in DOCS
    )
    if geometry and not has_geometry_section:
        print(
            f"PREFLIGHT FAIL: geometry results exist for "
            f"{', '.join(sorted(geometry))} but no document contains a "
            f"{GEOMETRY_SECTION!r} section, so none of their figures can be checked.\n"
            "  Either the heading was renumbered (update GEOMETRY_SECTION) or the "
            "results are stale (remove them).",
            file=sys.stderr,
        )
        return 1
    if has_geometry_section and not geometry:
        print(
            "PREFLIGHT FAIL: the documents contain a block-count geometry section but "
            "no geometry results were found.\n  Regenerate with:\n"
            "    python3 research/geometry.py --horizon short --blocks 6 12 --k 2\n"
            "    python3 research/geometry.py --horizon medium --blocks 6 12 --k 2\n"
            "    python3 research/geometry.py --horizon long --blocks 6 12 --k 2",
            file=sys.stderr,
        )
        return 1

    for doc in DOCS:
        if not doc.exists():
            failures.append(f"missing document {doc}")
            continue
        text = normalise(doc.read_text())
        tally = Tally()

        # Prose "IS x% (Sharpe y) -> OOS z% (Sharpe w)" quadruples. These carry
        # no label, so verify each value exists SOMEWHERE in the sweep for the
        # matching field -- weaker than a labelled check, but it still catches a
        # fabricated or mistyped figure, which is the actual risk.
        for m in PROSE_IS_OOS.finditer(text):
            is_r, is_s, oos_r, oos_s = m.groups()
            for field, v, tol in (
                ("is_return", float(is_r.replace(",", "")) / 100.0, TOL_PCT / 100.0),
                ("is_sharpe", float(is_s), TOL_SHARPE),
                ("oos_return", float(oos_r.replace(",", "")) / 100.0, TOL_PCT / 100.0),
                ("oos_sharpe", float(oos_s), TOL_SHARPE),
            ):
                tally.add("prose")
                if not any(abs(g - v) <= tol for g in df[field].to_numpy()):
                    failures.append(
                        f"{doc.name}: prose {field}={v} appears nowhere in the sweep"
                    )

        for m in PROSE_OOS_SHARPE.finditer(text):
            v = float(m.group(1))
            tally.add("prose")
            if not any(abs(g - v) <= TOL_SHARPE for g in df["oos_sharpe"].to_numpy()):
                failures.append(
                    f"{doc.name}: prose OOS Sharpe={v} appears nowhere in the sweep"
                )

        for m in ROW.finditer(text):
            label, oos_s, is_s, oos_r, is_r, oos_dd, trades = m.groups()
            for field, raw, tol in (
                ("oos_sharpe", oos_s, TOL_SHARPE),
                ("is_sharpe", is_s, TOL_SHARPE),
                ("oos_return", oos_r, TOL_PCT),
                ("is_return", is_r.replace(",", ""), TOL_PCT),
                ("oos_maxdd", oos_dd, TOL_PCT),
            ):
                v = float(raw)
                if field.endswith(("return", "maxdd")):
                    v /= 100.0
                    tol /= 100.0
                ok, msg = check(df, label, field, v, tol)
                tally.add("walk_forward")
                if not ok:
                    failures.append(f"{doc.name}: {msg}")
            ok, msg = check(df, label, "oos_trades", float(trades), 0.5)
            tally.add("walk_forward")
            if not ok:
                failures.append(f"{doc.name}: {msg}")

        # CPCV tables. Matched BEFORE the pair regex, whose 4-column shape can
        # also match a CPCV row prefix and would then compare the wrong fields.
        cpcv_labels: set[str] = set()
        for m in CPCV_ROW.finditer(text):
            label, med_s, iqr, frac, med_r, trades = m.groups()
            cpcv_labels.add(label)
            for field, v, tol in (
                ("median_sharpe", float(med_s), TOL_SHARPE),
                ("iqr_spread", float(iqr), TOL_SHARPE),
                ("frac_paths_positive", float(frac) / 100.0, 0.005),
                ("median_path_return", float(med_r) / 100.0, TOL_PCT / 100.0),
                ("total_trades", float(trades), 0.5),
            ):
                tally.add("cpcv")
                ok, msg = check_cpcv(label, field, v, tol)
                if not ok:
                    failures.append(f"{doc.name}: {msg}")

        # Perturbation tables. Matched by NUMBER rather than by label, because
        # the document abbreviates variant names for readability while the CSV
        # keeps them verbose.
        if perturb is not None and PERTURB_SECTION in text:
            # Scope to the perturbation section only. Searching the whole document
            # collides with the single-split pair tables, which share the same
            # 4-column shape and produced three false failures.
            start = text.index(PERTURB_SECTION)
            nxt = text.find("\n### ", start + len(PERTURB_SECTION))
            section = text[start : nxt if nxt != -1 else len(text)]
            known = perturb["median_sharpe"].to_numpy()
            for m in PERTURB_ROW.finditer(section):
                v = float(m.group(1))
                tally.add("perturb")
                if not any(abs(g - v) <= TOL_SHARPE for g in known):
                    failures.append(
                        f"{doc.name}: perturbation median {v} appears in no perturb_*.csv"
                    )

        # Block-count geometry tables (finding 1f), verified by recomputation.
        if geometry and GEOMETRY_SECTION in text:
            at = text.index(GEOMETRY_SECTION)
            nxt = text.find("\n### ", at + len(GEOMETRY_SECTION))
            n, msgs = check_geometry(text[at : nxt if nxt != -1 else len(text)], geometry)
            tally.add("geometry", n)
            failures += [f"{doc.name}: {m}" for m in msgs]

        for m in PAIR_ROW.finditer(text):
            label, oos_s, is_s, oos_r, trades = m.groups()
            for field, raw, tol in (
                ("oos_sharpe", oos_s, TOL_SHARPE),
                ("is_sharpe", is_s, TOL_SHARPE),
                ("oos_return", str(float(oos_r) / 100.0), TOL_PCT / 100.0),
                ("oos_trades", trades, 0.5),
            ):
                ok, msg = check(df, label, field, float(raw), tol)
                tally.add("pair")
                if not ok:
                    failures.append(f"{doc.name}: {msg}")

        per_doc[doc.name] = tally.per
        checked += tally.total

    failures += census_failures(per_doc)

    print("figures checked against the run that produced them "
          f"(sweep, CPCV, perturbation, recomputed geometry): {checked}")
    for name, families in per_doc.items():
        detail = ", ".join(f"{k} {v}" for k, v in sorted(families.items()))
        print(f"  {name}: {sum(families.values())}  ({detail})")
    if failures:
        print(f"\nMISMATCHES ({len(failures)}):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    # No `checked < 100` backstop any more: EXPECTED_FIGURES is a per-document floor,
    # which subsumes it and says something specific when it trips.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
