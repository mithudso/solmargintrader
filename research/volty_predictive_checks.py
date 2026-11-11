"""Frozen-chart diagnostics on local candles; never a forecast or execution client.

These data were already examined. Replaying their later half is a sensitivity
check, not a new untouched holdout. No configuration is selected by these results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core import volty
from backtester.core.volty import VoltyConfig, simulate, validate


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def daily_log_growth(timestamps, equity, initial):
    """Keep complete UTC days only, including fees in marked account wealth."""
    timestamps, equity = np.asarray(timestamps), np.asarray(equity, dtype=float)
    if len(timestamps) != len(equity) or not len(equity):
        raise ValueError("equal nonempty timestamp and equity arrays required")
    previous = np.r_[float(initial), equity[:-1]]
    if np.any(equity <= 0) or np.any(previous <= 0):
        return None  # Log growth is undefined after insolvency, never epsilon-fill.
    increments = np.log(equity / previous)
    days = timestamps // 86400
    return np.asarray([increments[days == day].sum() for day in np.unique(days)
                       if np.count_nonzero(days == day) == 1440], dtype=float)


def block_interval(daily_excess, block_days=7, samples=2000, seed=20261111):
    """Circular paired block bootstrap of mean daily log-growth difference.

    Conditional descriptive uncertainty assumes approximately stationary blocks.
    It is neither a p-value after strategy selection nor future-profit probability.
    """
    values = np.asarray(daily_excess, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("finite one-dimensional daily differences required")
    if block_days < 1 or samples < 1:
        raise ValueError("positive block size and sample count required")
    n = len(values)
    if n < 3 * block_days:
        return {"status": "insufficient_complete_days", "days": n}
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(samples, (n + block_days - 1) // block_days))
    indices = (starts[..., None] + np.arange(block_days)) % n
    means = values[indices.reshape(samples, -1)[:, :n]].mean(axis=1)
    low, high = np.quantile(means, [.025, .975])
    return {"status": "descriptive_only", "days": n, "block_days": block_days,
            "samples": samples, "seed": seed, "mean_daily_log_excess": float(values.mean()),
            "ci95_daily_log_excess": [float(low), float(high)]}


def passive_equity(bars, start, fee_bps, slippage_bps, initial):
    fee, slip = fee_bps / 1e4, slippage_bps / 1e4
    units = initial / (bars["open"][start] * (1 + slip) * (1 + fee))
    equity = units * bars["close"][start:].astype(float)
    equity[-1] *= (1 - slip) * (1 - fee)
    return equity


def run_checks(bars):
    validate(bars, 60)
    start = len(bars["close"]) // 2
    timestamps = bars["timestamp"][start:]
    rows = []
    # The exact inspected TradingView parameters are frozen; costs are scenarios.
    for label, fee, slip, carry, path, delay in (
        ("gross_diagnostic_only", 0, 0, 0, "nearest", 0),
        ("gum_fee_synthetic_carry", 3.5, 2, .1, "nearest", 0),
        ("adverse_execution", 3.5, 10, .2, "nearest", 0),
        ("high_first", 3.5, 2, .1, "high-first", 0),
        ("low_first", 3.5, 2, .1, "low-first", 0),
        ("one_extra_bar_delay", 3.5, 2, .1, "nearest", 1),
    ):
        config = VoltyConfig(length=5, atr_mult=1, fee_bps=fee,
                             slippage_bps=slip, carry_bps_hour=carry)
        result = simulate(bars, config, 60, start=start, path=path, signal_delay_bars=delay)
        hold = passive_equity(bars, start, fee, slip, config.initial_capital)
        daily = daily_log_growth(timestamps, result["equity"], config.initial_capital)
        hold_daily = daily_log_growth(timestamps, hold, config.initial_capital)
        uncertainty = ({"status": "undefined_after_insolvency"} if daily is None
                       else block_interval(daily - hold_daily))
        rows.append({"scenario": label, "config": asdict(config), "path": path,
                     "signal_delay_bars": delay,
                     **{k: v for k, v in result.items() if k != "equity"},
                     "passive_return": float(hold[-1] / config.initial_capital - 1),
                     "paired_daily_block_bootstrap": uncertainty})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        parser.error("expected-sha256 must be a lowercase SHA-256 digest")
    if digest(args.data) != args.expected_sha256:
        parser.error("source checksum mismatch")
    code_paths = {"research/volty_predictive_checks.py": Path(__file__).resolve(),
                  "backtester/core/volty.py": Path(volty.__file__).resolve()}
    code_hashes = {name: digest(path) for name, path in code_paths.items()}
    frame = pd.read_csv(args.data)
    bars = {k: frame[k].to_numpy() for k in ("timestamp", "open", "high", "low", "close", "volume")}
    report = {"schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
              "source": str(args.data.resolve()), "source_sha256": args.expected_sha256,
              "source_market": "Binance spot ZECUSDT; not GUM ZECUSDC or CRYPTO:ZECUSD",
              "evaluation": "later half of previously examined data; sensitivity only, no new OOS claim",
              "sizing": "synthetic 1x equity; no 2x margin or liquidation model",
              "limits": ["OHLC paths do not establish TradingView fill parity",
                         "3.5bps fee is an observed venue snapshot, not historical fee proof",
                         "carry is synthetic, not observed GUM funding",
                         "daily block intervals assume stationary blocks and are descriptive",
                         "spot candles do not prove executable perpetual returns"],
              "code_sha256": code_hashes, "results": run_checks(bars)}
    if digest(args.data) != args.expected_sha256 or code_hashes != {name: digest(path) for name, path in code_paths.items()}:
        raise RuntimeError("input or implementation changed during diagnostics")
    # Exclusive creation preserves earlier evidence and prevents silent replacement.
    with args.output.open("x") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output.resolve()), "sha256": digest(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
