"""Costed ZEC Volty stop-entry sweep and five expanding walk-forward tests.

Fetching is separate: this command reads observed local CSVs only. A fresh
virtual book starts at each evaluation boundary; preceding bars warm stops.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .core import volty
from .core.volty import VoltyConfig, simulate, validate

STEPS = {"1m": 60, "5m": 300, "10m": 600, "1h": 3600, "1d": 86400}
GRID = list(itertools.product(range(1, 11), (0.25, 0.5, 0.75, 1.0, 1.25)))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact(result):
    return {k: v for k, v in result.items() if k not in ("equity", "fills")}


def aggregate(frame, source_step, target_step):
    """Only complete UTC-aligned buckets; never fill or interpolate gaps."""
    if target_step == source_step:
        return frame.copy()
    groups = frame.groupby(frame.timestamp // target_step * target_step)
    out = groups.agg(timestamp=("timestamp", "min"), open=("open", "first"), high=("high", "max"),
                     low=("low", "min"), close=("close", "last"), volume=("volume", "sum"), count=("timestamp", "size"))
    out = out[(out["count"] == target_step//source_step) & (out.timestamp == out.index)]
    return out.drop(columns="count").reset_index(drop=True)


def prepare(data_dir, output, minute_days):
    source_manifest = data_dir / "manifest.json"
    source_info = json.loads(source_manifest.read_text())
    frames, provenance = {}, {}
    for source_interval in ("1m", "1h"):
        path = data_dir / f"ZEC_{source_interval}.csv"
        actual = digest(path)
        if actual != source_info[source_interval]["sha256"]:
            raise ValueError(f"source checksum mismatch: {path}")
        frame = pd.read_csv(path)
        step = STEPS[source_interval]
        if frame.timestamp.duplicated().any() or np.any(np.diff(frame.timestamp) <= 0):
            raise ValueError("duplicate or unordered source candles")
        now = int(datetime.now(UTC).timestamp())
        frame = frame[frame.timestamp + step <= now].reset_index(drop=True)
        for interval in (("1m", "5m", "10m") if source_interval == "1m" else ("1h", "1d")):
            series = frame
            if source_interval == "1m":
                cutoff = int(frame.timestamp.iloc[-1]) + step - minute_days*86400
                series = series[series.timestamp >= cutoff]
            series = aggregate(series, step, STEPS[interval])
            # Keep the latest contiguous span and expose all discarded history.
            cuts = np.flatnonzero(np.diff(series.timestamp) != STEPS[interval]) + 1
            offset = int(cuts[-1]) if len(cuts) else 0
            used = series.iloc[offset:].reset_index(drop=True)
            if len(used) < 100:
                raise ValueError(f"insufficient latest contiguous history for {interval}")
            arrays = {k: used[k].to_numpy() for k in used.columns}
            validate(arrays, STEPS[interval])
            target = output / f"ZEC_{interval}.csv"
            used.to_csv(target, index=False)
            frames[interval] = arrays
            provenance[interval] = {"source": str(path), "source_sha256": actual,
                "snapshot": str(target), "snapshot_sha256": digest(target),
                "venue": "Binance spot ZECUSDT", "quote_currency": "USDT", "rows": len(used),
                "discarded_aggregate_rows_before_last_gap": offset,
                "first_utc": datetime.fromtimestamp(int(used.timestamp.iloc[0]), UTC).isoformat(),
                "last_bar_open_utc": datetime.fromtimestamp(int(used.timestamp.iloc[-1]), UTC).isoformat()}
    return frames, provenance


def rank(rows):
    # Frozen train-only objective, stable parameter tie breaks.
    return max(rows, key=lambda x: (x["return"], -x["max_drawdown"], -x["length"], -x["atr_mult"]))


def study(frames, output):
    all_rows, winners, folds, forward = [], [], [], []
    for interval, bars in frames.items():
        step, n = STEPS[interval], len(bars["close"])
        boundary = n//2
        configs = [VoltyConfig(length=length, atr_mult=mult) for length, mult in GRID]
        training = []
        for config in configs:
            values = compact(simulate(bars, config, step, end=boundary))
            training.append({"interval": interval, "length": config.length, "atr_mult": config.atr_mult, **values})
            full = compact(simulate(bars, config, step))
            all_rows.append({"interval": interval, "length": config.length, "atr_mult": config.atr_mult,
                             **{f"train_{k}": v for k, v in values.items()}, **{f"full_{k}": v for k, v in full.items()}})
        winner = rank(training)
        selected = VoltyConfig(length=winner["length"], atr_mult=winner["atr_mult"])
        test = compact(simulate(bars, selected, step, start=boundary, keep_fills=True))
        fixed = {"interval": interval, "length": selected.length, "atr_mult": selected.atr_mult,
                 "train_return": winner["return"], **{f"test_{k}": v for k, v in test.items()}}
        # Independent alternate path and doubled fill/carry costs for the frozen winner.
        for name, config, path in (("high_first", selected, "high-first"),
                                   ("low_first", selected, "low-first"),
                                   ("double_cost", replace(selected, fee_bps=20, slippage_bps=4, carry_bps_hour=0.2), "nearest")):
            fixed[f"{name}_return"] = simulate(bars, config, step, start=boundary, path=path)["return"]
        # Costed passive spot comparison uses exactly the same test dates.
        entry, exit_ = bars["open"][boundary]*(1+2/1e4), bars["close"][-1]*(1-2/1e4)
        fixed["buy_hold_test_return"] = float(exit_*(1-10/1e4)/(entry*(1+10/1e4))-1)
        fixed["beats_buy_hold"] = bool(test["return"] > fixed["buy_hold_test_return"])
        winners.append(fixed)
        bounds = np.linspace(boundary, n, 6, dtype=int)
        wealth = 1.0
        for fold, (start, end) in enumerate(itertools.pairwise(bounds), 1):
            candidates = []
            for config in configs:
                result = compact(simulate(bars, config, step, end=int(start)))
                candidates.append({"length": config.length, "atr_mult": config.atr_mult, **result})
            chosen = rank(candidates)
            config = VoltyConfig(length=chosen["length"], atr_mult=chosen["atr_mult"])
            out = compact(simulate(bars, config, step, start=int(start), end=int(end)))
            wealth *= 1+out["return"]
            folds.append({"interval": interval, "fold": fold, "length": config.length,
                          "atr_mult": config.atr_mult, "train_end_exclusive": int(bars["timestamp"][start]),
                          "train_return": chosen["return"], **out})
        fixed["walk_forward_return"] = wealth-1
        final_training = []
        for row in all_rows:
            if row["interval"] == interval:
                final_training.append({"length": row["length"], "atr_mult": row["atr_mult"],
                                       "return": row["full_return"], "max_drawdown": row["full_max_drawdown"]})
        final = rank(final_training)
        forward.append({"interval": interval, "config": asdict(VoltyConfig(length=final["length"], atr_mult=final["atr_mult"])),
                        "status": "prepared_not_running", "paper_only": True,
                        "selection": "best net return using all data available at freeze; no future outcome yet",
                        "activate_after_timestamp": int(bars["timestamp"][-1]+step)})
        pd.DataFrame(all_rows).to_csv(output/"sweep.csv", index=False)
        pd.DataFrame(winners).to_csv(output/"winners.csv", index=False)
        pd.DataFrame(folds).to_csv(output/"walk_forward.csv", index=False)
        print(f"{interval}: 50 configurations, 5 walk-forward folds finished", flush=True)
    (output/"forward_specs.json").write_text(json.dumps({"schema_version": 1, "accounts": forward}, indent=2)+"\n")
    return winners


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minute-days", type=int, default=90)
    args = parser.parse_args(argv)
    if args.minute_days < 10:
        parser.error("minute-days must be at least 10")
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output/"manifest.json").exists():
        parser.error("completed study exists; choose a fresh output directory")
    code_paths = (Path(__file__).resolve(), Path(volty.__file__).resolve())
    code_hashes = {str(p): digest(p) for p in code_paths}
    frames, provenance = prepare(args.data_dir, args.output, args.minute_days)
    results = study(frames, args.output)
    manifest = {"schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
                "strategy": "Volty Expan Close", "trials": 250, "configs_per_interval": 50,
                "selection": "net return on expanding past-only training, five disjoint OOS folds",
                "sizing": "1x current equity on entry, fixed units until reverse, long/short synthetic reference",
                "costs": asdict(VoltyConfig()), "datasets": provenance, "code_sha256": code_hashes,
                "limits": ["OHLC assumed path, no certified Pine broker parity", "Binance spot bars simulate synthetic shorts; no executable short venue proven",
                           "carry is a constant scenario, not observed funding", f"{args.minute_days}-day intraday window versus longer hourly/daily history; compare within interval",
                           "full-bar carry charged on end-of-bar positions; close-mark insolvency guard, no venue margin/liquidation model",
                           "250 searched configurations; exploratory results, no multiplicity-adjusted significance", "historical walk-forward is not prospective paper performance"],
                "artifacts": {p.name: digest(p) for p in args.output.iterdir() if p.is_file()}}
    if code_hashes != {str(p): digest(p) for p in code_paths}:
        raise RuntimeError("implementation changed during the study; rerun from a stable installation")
    rendered = json.dumps(results, indent=2, allow_nan=False)
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
