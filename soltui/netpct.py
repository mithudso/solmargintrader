"""Net percentage growth or decline, always with the word that names its source.

One definition for every results view: `final / initial - 1`, as a signed fraction. A bare
"+9.4%" reads as "my money is up", and most figures in this package are simulations, so the text
form never leaves the source word off. The source words are the ones the rest of the package uses:
`backtest`, `paper`, `dry-run`, `live LP` (plus `wallet (live)` for the read-only wallet scan).
"""

from __future__ import annotations

import math

SOURCES = ("backtest", "paper", "dry-run", "dry-run LP", "live LP", "reported LP", "wallet (live)",
           "reported")


def net_pct(final: float | None, initial: float | None) -> float | None:
    """`final / initial - 1`, or None when either is missing or the base is not positive.

    None rather than 0.0: "no base to compare with" is not "no change".
    """
    if final is None or initial is None:
        return None
    if not (math.isfinite(final) and math.isfinite(initial)) or initial <= 0:
        return None
    return final / initial - 1.0


def fmt(value: float | None, places: int = 1) -> str:
    """Signed percentage text from a fraction; an em dash when there is no value."""
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value * 100:+.{places}f}%"


def labelled(value: float | None, source: str, what: str = "net", places: int = 1) -> str:
    """`backtest net +9.4%`. The source word is mandatory, so a bare percentage cannot be built."""
    if source not in SOURCES:
        raise ValueError(f"unknown source word {source!r}; expected one of {SOURCES}")
    return f"{source} {what} {fmt(value, places)}"
