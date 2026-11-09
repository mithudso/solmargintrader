"""Historical, order-free strategy simulations for the Dry Run view."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from backtester.core.strategies import REGISTRY
from backtester.core.types import INTERVAL_SECONDS

# Legacy integration fixture; this file no longer determines the default strategy.
RECOMMENDATION_FILE = Path(__file__).resolve().parent.parent / "research" / "TOP_UNTESTED_RECOMMENDATION.json"


def get_best_strategy() -> dict[str, str]:
    """Offer a neutral baseline without presenting a research candidate as proven."""
    return {"strategy": "buy_and_hold", "source": "Baseline",
            "details": "Neutral starting choice, not a recommendation or proof of profitability."}


def run_dryrun(strategy_name: str, settings=None, progress=None) -> dict:
    """Run the chosen strategy on cached historical bars using the simulation engine.

    Each call has its own session. It does not start a live paper feed or place orders.
    """
    from .config import load_settings
    from .paper import start_session
    from .runner import engine_config, load_arrays
    from . import presets
    from backtester.core.strategies import build

    settings = settings or load_settings()
    progress = progress or (lambda _line: None)
    name = strategy_name.strip()
    if not name:
        raise ValueError("Choose a strategy first")
    rank = presets.parse_value(name)
    if rank is not None:
        preset = presets.find_preset(rank)
        progress(f"Loading {preset['asset']} {preset['interval']} cached bars for {name}")
        arrays = presets.load_preset_arrays(preset, settings.data_dir)
        strategy = presets.build_strategy(preset)
        config = engine_config(settings, interval=preset["interval"])
        asset, interval = preset["asset"], preset["interval"]
    else:
        if name not in REGISTRY:
            raise ValueError(f"Unknown strategy {name!r}; choose a registered strategy or Top 5 preset")
        strategy = build(name)
        asset, interval = settings.asset, settings.interval
        progress(f"Loading {asset} {interval} cached bars for {name}")
        arrays = load_arrays(settings)
        config = engine_config(settings)
    # The engine requires contiguous candles. Use the latest contiguous segment rather
    # than filling a price gap, and disclose exactly how much history was excluded.
    total_bars = len(arrays["ts"])
    seconds = INTERVAL_SECONDS.get(interval)
    if seconds is None:
        raise ValueError(f"Unsupported candle interval {interval!r}")
    gaps = np.flatnonzero(np.diff(arrays["ts"]) != seconds)
    first = int(gaps[-1] + 1) if len(gaps) else 0
    if first:
        arrays = {key: value[first:] for key, value in arrays.items()}
        progress(f"Price history has gaps; using the most recent contiguous segment and excluding {first} earlier bars")
    progress(f"Running {name} on {len(arrays['ts'])} historical bars; no orders are placed")
    from .simulation import gate
    session = start_session(gate(strategy, settings, interval), arrays, config)
    session.seek_end()
    summary = session.summary()
    progress(f"Completed {name}: {summary['fills']} simulated fills")
    start_date = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(arrays["ts"][0])))
    end_date = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(arrays["ts"][-1])))
    text = (f"Historical dry run: {name} on {asset} {interval}\n"
            f"Window: {start_date} to {end_date}\n"
            f"Bars: {summary['bars_total']} of {total_bars} cached bars; simulated fills: {summary['fills']}\n"
            + (f"Price gaps: excluded {first} earlier bars; used the latest contiguous segment.\n" if first else "")
            + f"Net return: {summary['pnl']:+.2%}; final equity: ${summary['equity']:,.2f}\n"
            "No live prices or orders; this is not a forward test.")
    return {"command": ["historical simulation", name], "returncode": 0,
            "stdout": text, "net_pct": summary["pnl"], "asset": asset, "interval": interval,
            "strategy": name, "mode": "historical simulation", "input_bars_total": total_bars,
            "bars_excluded_for_gaps": first}


_CAPITAL_RE = re.compile(r"capital needed:\s*\$([0-9][0-9,]*\.?[0-9]*)")
_TICK_NET_RE = re.compile(r"^tick\s+\d+\s.*\bnet\s+\$(-?[0-9][0-9,]*\.?[0-9]*)", re.MULTILINE)


def dryrun_net_pct(stdout: str) -> float | None:
    """Net % of the extension's dry run: last tick's marked net USD over the capital it printed.

    Both numbers come from the tool's own output (`capital needed:` and the final `tick N ... net`
    line). None when either is absent, so a changed output format shows "no figure" and not 0.
    """
    cap = _CAPITAL_RE.search(stdout or "")
    ticks = _TICK_NET_RE.findall(stdout or "")
    if not cap or not ticks:
        return None
    try:
        capital = float(cap.group(1).replace(",", ""))
        net = float(ticks[-1].replace(",", ""))
    except ValueError:
        return None
    return net / capital if capital > 0 else None


def spawn_dryrun(strategy_name: str, update_status: Callable[[str], None]) -> None:
    """Compatibility wrapper for the same historical simulation."""
    try:
        result = run_dryrun(strategy_name, progress=update_status)
        update_status(result["stdout"])
    except Exception as exc:
        update_status(f"Dry run failed: {type(exc).__name__}: {exc}")
