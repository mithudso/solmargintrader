"""Equity-curve and drawdown charts.

matplotlib is imported lazily behind a guard so that a missing install
degrades to "no charts" rather than failing an otherwise complete run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from .engine import BacktestResult


def charts_available() -> bool:
    """Whether matplotlib can be imported in this environment."""
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def plot_comparison(
    results: Sequence[BacktestResult],
    out_dir: str | Path,
    asset: str,
    *,
    log_scale: bool = True,
) -> list[Path]:
    """Write equity-curve and drawdown PNGs. Returns paths written."""
    if not charts_available():
        return []

    import matplotlib

    # Non-interactive backend: this runs headless and must never open a window.
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    fig, (ax_eq, ax_dd) = plt.subplots(
        2, 1, figsize=(12, 9), sharex=True, height_ratios=[2, 1]
    )

    for r in results:
        dates = pd.to_datetime(r.timestamps, unit="s", utc=True)
        ax_eq.plot(dates, r.equity, label=r.strategy_name, linewidth=1.4)

        peak = np.maximum.accumulate(r.equity)
        safe = np.where(peak <= 0, np.nan, peak)
        dd = np.nan_to_num((r.equity - peak) / safe, nan=0.0) * 100.0
        ax_dd.plot(dates, dd, label=r.strategy_name, linewidth=1.1)

    title = f"{asset} strategy comparison -- equity (net of costs)"
    if results and results[0].mode == "perp":
        title += f" -- perp {results[0].leverage:g}x"
    ax_eq.set_title(title)
    ax_eq.set_ylabel("Equity (USD)")
    if log_scale and all((r.equity > 0).all() for r in results):
        ax_eq.set_yscale("log")
    ax_eq.legend(loc="upper left", fontsize=9)
    ax_eq.grid(alpha=0.3)

    ax_dd.set_title("Drawdown from running peak")
    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.set_xlabel("Date (UTC)")
    ax_dd.grid(alpha=0.3)

    fig.tight_layout()
    p = out / "equity_comparison.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    written.append(p)

    # Per-strategy exposure, which explains a lot of return differences.
    fig2, ax = plt.subplots(figsize=(12, 4))
    for r in results:
        dates = pd.to_datetime(r.timestamps, unit="s", utc=True)
        ax.plot(dates, r.exposure, label=r.strategy_name, linewidth=1.0)
    ax.set_title(f"{asset} signed exposure (notional / equity)")
    ax.set_ylabel("Exposure")
    ax.set_xlabel("Date (UTC)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    fig2.tight_layout()
    p = out / "exposure.png"
    fig2.savefig(p, dpi=120)
    plt.close(fig2)
    written.append(p)

    return written
