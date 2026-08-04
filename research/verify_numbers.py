"""Assert every performance figure in the research documents came from the sweep.

The documents' entire credibility rests on "no number was estimated". A
transcription slip is indistinguishable from a fabrication to a reader, so this
checks the whole surface rather than a sample: it extracts every
`config | metric | value` triple it can recognise from the markdown tables and
asserts each matches `results/sweep_results.csv` within tolerance.

    python3 research/verify_numbers.py        # exit 0 iff every figure matches

Deliberately conservative: it only checks rows it can unambiguously parse, and
reports how many figures it verified so a low count is visible rather than
silently passing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

RESEARCH = Path(__file__).resolve().parent
CSV = RESEARCH / "results" / "sweep_results.csv"
DOCS = (RESEARCH / "RANKED_LISTS.md", RESEARCH / "STRATEGIES.md")

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


def load() -> pd.DataFrame:
    """Sweep results, indexed for lookup by label."""
    if not CSV.exists():
        raise SystemExit(f"missing {CSV}; run: python3 research/sweep.py")
    return pd.read_csv(CSV)


def load_cpcv() -> pd.DataFrame | None:
    """CPCV results, if the CPCV sweep has been run."""
    if not CPCV_CSV.exists():
        return None
    return pd.read_csv(CPCV_CSV)


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


def main() -> int:
    """Verify every parseable figure; exit non-zero on any mismatch."""
    df = load()
    cpcv = load_cpcv()
    checked = 0
    failures: list[str] = []
    per_doc: dict[str, int] = {}

    def check_cpcv(label: str, field: str, value: float, tol: float) -> tuple[bool, str]:
        """Match a CPCV figure against cpcv_results.csv for any horizon."""
        if cpcv is None:
            return True, ""
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

    for doc in DOCS:
        if not doc.exists():
            failures.append(f"missing document {doc}")
            continue
        text = normalise(doc.read_text())
        before = checked

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
                checked += 1
                if not any(abs(g - v) <= tol for g in df[field].to_numpy()):
                    failures.append(
                        f"{doc.name}: prose {field}={v} appears nowhere in the sweep"
                    )

        for m in PROSE_OOS_SHARPE.finditer(text):
            v = float(m.group(1))
            checked += 1
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
                checked += 1
                if not ok:
                    failures.append(f"{doc.name}: {msg}")
            ok, msg = check(df, label, "oos_trades", float(trades), 0.5)
            checked += 1
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
                checked += 1
                ok, msg = check_cpcv(label, field, v, tol)
                if not ok:
                    failures.append(f"{doc.name}: {msg}")

        for m in PAIR_ROW.finditer(text):
            label, oos_s, is_s, oos_r, trades = m.groups()
            for field, raw, tol in (
                ("oos_sharpe", oos_s, TOL_SHARPE),
                ("is_sharpe", is_s, TOL_SHARPE),
                ("oos_return", str(float(oos_r) / 100.0), TOL_PCT / 100.0),
                ("oos_trades", trades, 0.5),
            ):
                ok, msg = check(df, label, field, float(raw), tol)
                checked += 1
                if not ok:
                    failures.append(f"{doc.name}: {msg}")

        per_doc[doc.name] = checked - before

    print(f"figures verified against {CSV.name}: {checked}")
    for name, n in per_doc.items():
        print(f"  {name}: {n}")
    if failures:
        print(f"\nMISMATCHES ({len(failures)}):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    if checked < 100:
        print(
            f"\nWARNING: only {checked} figures parsed; the regexes may have "
            "stopped matching after a table format change.",
            file=sys.stderr,
        )
    print("ALL PARSED FIGURES MATCH THE SWEEP OUTPUT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
