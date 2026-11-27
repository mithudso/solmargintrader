"""Long-history pattern, support-level and strategy checks for one coin set.

python -m research.coin_levels --history /absolute/path/history --coins HYPE ZEC BTC --output /absolute/path/levels

Reads the CSV.gz files that research.coin_history wrote and binds their manifest.
Missing bars are never filled. Each cadence is reduced to its longest contiguous
run before any return or indicator is computed, and the run is reported.

Three checks, all on the same protocol as the 31-day suite:
  patterns  next-bar direction after two-bar sign patterns, Holm-corrected;
  levels    confirmed swing-pivot support/resistance versus an unstructured
            moving-average control touched the same way;
  strategy  a small long-flat family, next-open fills, 10/25/60 bps per fill plus
            the 2 bps execution allowance, chronological 60/20/20 split, selection on
            validation only (at least 10 validation exits), test reported once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

CADENCES = {"5m": 300, "1h": 3600}
BARS_PER_HOUR = {"5m": 12, "1h": 1}
COSTS_BPS = (10, 25, 60)
ALLOWANCE_BPS = 2
MIN_VALIDATION_EXITS = 10
PATTERN_MIN_N = 30


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_frame(history: Path, coin: str, label: str) -> tuple[pd.DataFrame, dict]:
    path = history / f"{coin}-USD_{label}.csv.gz"
    frame = (
        pd.read_csv(path, compression="gzip", usecols=["unix", "open", "high", "low", "close", "volume"])
        .set_index("unix")
        .sort_index()
    )
    frame = frame[~frame.index.duplicated(keep="first")]
    step = CADENCES[label]
    stamps = frame.index.to_numpy()
    expected = (int(stamps[-1]) - int(stamps[0])) // step + 1
    breaks = np.flatnonzero(np.diff(stamps) != step)
    starts = np.r_[0, breaks + 1]
    ends = np.r_[breaks + 1, len(stamps)]
    best = int(np.argmax(ends - starts))  # earliest run wins ties
    sub = frame.iloc[starts[best] : ends[best]]
    info = {
        "path": str(path),
        "bars_present": len(frame),
        "expected_slots": int(expected),
        "missing_slots": int(expected - len(frame)),
        "contiguous_runs": len(starts),
        "longest_run_bars": len(sub),
        "longest_run_start": iso(int(sub.index[0])),
        "longest_run_end": iso(int(sub.index[-1])),
        "zero_volume_bars": int((frame["volume"] == 0).sum()),
    }
    return sub, info


def two_sided_p_proportion(k: int, n: int) -> float:
    z = (k - n / 2) / math.sqrt(n / 4)
    return math.erfc(abs(z) / math.sqrt(2))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    m = len(pvalues)
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvalues[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted


def patterns(frame: pd.DataFrame) -> list[dict]:
    close = frame["close"].to_numpy(float)
    log_ret = np.diff(np.log(close))
    sign = np.sign(log_ret)
    rows = []
    for a in (1, -1):
        for b in (1, -1):
            mask = (sign[:-2] == a) & (sign[1:-1] == b) & (sign[2:] != 0)
            outcome = sign[2:][mask]
            forward = log_ret[2:][mask]
            name = ("U" if a > 0 else "D") + ("U" if b > 0 else "D")
            n = int(outcome.size)
            row = {"pattern": name, "n": n}
            if n >= PATTERN_MIN_N:
                down = int((outcome < 0).sum())
                row.update(
                    {
                        "p_next_down": down / n,
                        "p_next_down_ci95": wilson(down, n),
                        "p_value_vs_half": two_sided_p_proportion(down, n),
                        "mean_next_return_bps": float(forward.mean() * 1e4),
                        "t_next_return": float(forward.mean() / (forward.std(ddof=1) / math.sqrt(n))),
                    }
                )
            rows.append(row)
    return rows


def pivot_indices(values: np.ndarray, k: int, kind: str) -> np.ndarray:
    windows = np.lib.stride_tricks.sliding_window_view(values, 2 * k + 1)
    centre = values[k : len(values) - k]
    extreme = windows.min(axis=1) if kind == "low" else windows.max(axis=1)
    return np.flatnonzero(centre == extreme) + k


def _accept_non_overlapping(events: list[tuple[int, float]], horizon: int) -> list[tuple[int, float]]:
    accepted: list[tuple[int, float]] = []
    last = -10**9
    for stamp_index, level in sorted(events):
        if stamp_index - last >= horizon:
            accepted.append((stamp_index, level))
            last = stamp_index
    return accepted


def level_test(frame: pd.DataFrame, label: str) -> dict:
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    close = frame["close"].to_numpy(float)
    n = len(close)
    k = 6 if label == "1h" else 3
    horizon = 24 if label == "1h" else 5
    band, break_pct = 0.005, 0.01
    result: dict = {"pivot_k": k, "horizon_bars": horizon, "band": band, "break_pct": break_pct}

    def outcome_break(index: int, level: float, side: str) -> bool:
        future = close[index + 1 : index + 1 + horizon]
        if side == "support":
            return bool((future < level * (1 - break_pct)).any())
        return bool((future > level * (1 + break_pct)).any())

    for side, kind in (("support", "low"), ("resistance", "high")):
        values = low if side == "support" else high
        pivots = pivot_indices(values, k, kind)
        real: list[tuple[int, float]] = []
        for pivot in pivots:
            confirmed = pivot + k
            level = values[pivot]
            later = np.arange(confirmed + 1, n - horizon)
            if side == "support":
                hit = later[low[later] <= level * (1 + band)]
            else:
                hit = later[high[later] >= level * (1 - band)]
            if hit.size:
                real.append((int(hit[0]), float(level)))
        real = _accept_non_overlapping(real, horizon)
        real_breaks = [outcome_break(t, lvl, side) for t, lvl in real if t + horizon < n]

        sma = pd.Series(close).rolling(horizon).mean().to_numpy()
        control: list[tuple[int, float]] = []
        for t in range(horizon + 1, n - horizon):
            ref = sma[t]
            if side == "support" and low[t] <= ref * (1 + band) and close[t - 1] > ref * (1 + band):
                control.append((t, float(ref)))
            if side == "resistance" and high[t] >= ref * (1 - band) and close[t - 1] < ref * (1 - band):
                control.append((t, float(ref)))
        control = _accept_non_overlapping(control, horizon)
        control_breaks = [outcome_break(t, lvl, side) for t, lvl in control if t + horizon < n]

        n_real, n_control = len(real_breaks), len(control_breaks)
        k_real, k_control = sum(real_breaks), sum(control_breaks)
        p_real = k_real / n_real if n_real else float("nan")
        p_control = k_control / n_control if n_control else float("nan")
        pooled = (k_real + k_control) / (n_real + n_control) if n_real + n_control else float("nan")
        se = math.sqrt(pooled * (1 - pooled) * (1 / n_real + 1 / n_control)) if n_real and n_control and 0 < pooled < 1 else float("nan")
        z = (p_real - p_control) / se if se and not math.isnan(se) else float("nan")
        result[side] = {
            "pivots": len(pivots),
            "real_events": n_real,
            "control_events": n_control,
            "break_rate_real": p_real,
            "break_rate_control": p_control,
            "difference_real_minus_control": p_real - p_control,
            "z": z,
            "p_value": math.erfc(abs(z) / math.sqrt(2)) if not math.isnan(z) else float("nan"),
        }
    return result


def sma(values: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(values).rolling(window).mean().to_numpy()


def ema(values: np.ndarray, span: int) -> np.ndarray:
    return pd.Series(values).ewm(span=span, adjust=False).mean().to_numpy()


def hysteresis(enter: np.ndarray, leave: np.ndarray) -> np.ndarray:
    pos = np.zeros(len(enter), dtype=np.int8)
    state = 0
    for t in range(len(enter)):
        if state == 0 and enter[t]:
            state = 1
        elif state == 1 and leave[t]:
            state = 0
        pos[t] = state
    return pos


def rsi(close: np.ndarray, period: int) -> np.ndarray:
    delta = pd.Series(close).diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return (100 - 100 / (1 + gain / loss)).to_numpy()


def strategy_configs(frame: pd.DataFrame, label: str) -> dict[str, np.ndarray]:
    scale = BARS_PER_HOUR[label]
    close = frame["close"].to_numpy(float)
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    n = len(close)
    positions: dict[str, np.ndarray] = {"buy_hold": np.ones(n, dtype=np.int8)}
    for fast_h, slow_h in ((12, 48), (24, 96), (24, 168), (48, 168)):
        f, s = ema(close, fast_h * scale), ema(close, slow_h * scale)
        positions[f"ema_cross_{fast_h}h_{slow_h}h"] = (f > s).astype(np.int8)
    for hours in (24, 72, 168):
        win = hours * scale
        upper = pd.Series(high).shift(1).rolling(win).max().to_numpy()
        lower = pd.Series(low).shift(1).rolling(max(1, win // 2)).min().to_numpy()
        positions[f"donchian_{hours}h"] = hysteresis(close > upper, close < lower)
    for period_h, enter, leave in ((14, 30, 55), (14, 25, 50)):
        value = rsi(close, period_h * scale)
        positions[f"rsi_{period_h}h_{enter}_{leave}"] = hysteresis(value < enter, value > leave)
    for window_h in (20,):
        win = window_h * scale
        mid, sd = sma(close, win), pd.Series(close).rolling(win).std().to_numpy()
        positions[f"bollinger_{window_h}h_2sd"] = hysteresis(close < mid - 2 * sd, close > mid)
    for lookback_h in (24, 168):
        lag = lookback_h * scale
        pos = np.zeros(n, dtype=np.int8)
        pos[lag:] = close[lag:] > close[:-lag]
        positions[f"momentum_{lookback_h}h"] = pos
    return positions


def net_returns(pos: np.ndarray, opens: np.ndarray, cost: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    held = pos[:-2].astype(float)
    ret = opens[2:] / opens[1:-1] - 1
    prev = np.r_[0, pos[:-1]][:-2]
    entries = ((pos[:-2] == 1) & (prev == 0)).astype(float)
    net = held * ret - np.abs(pos[:-2] - prev) * cost
    return net, entries, held


def summarize(net: np.ndarray, entries: np.ndarray) -> dict:
    curve = np.cumprod(1 + net)
    peak = np.maximum.accumulate(np.r_[1.0, curve])[1:]
    drawdown = float(np.min(curve / peak - 1)) if curve.size else 0.0
    return {"return": float(curve[-1] - 1) if curve.size else 0.0, "exits": int(entries.sum()), "max_drawdown": drawdown}


def strategy_test(frame: pd.DataFrame, label: str) -> dict:
    opens = frame["open"].to_numpy(float)
    positions = strategy_configs(frame, label)
    m = len(opens) - 2
    cut_val, cut_test = int(0.6 * m), int(0.8 * m)
    rows = []
    for name, pos in positions.items():
        for fee in COSTS_BPS:
            cost = (fee + ALLOWANCE_BPS) / 1e4
            net, entries, _ = net_returns(pos, opens, cost)
            val = summarize(net[cut_val:cut_test], entries[cut_val:cut_test])
            test = summarize(net[cut_test:], entries[cut_test:])
            rows.append({"policy": name, "fee_bps": fee, "validation": val, "test": test})
    selected = {}
    for fee in COSTS_BPS:
        eligible = [r for r in rows if r["fee_bps"] == fee and r["validation"]["exits"] >= MIN_VALIDATION_EXITS]
        best = max(eligible, key=lambda r: r["validation"]["return"]) if eligible else None
        buy_hold = next(r for r in rows if r["fee_bps"] == fee and r["policy"] == "buy_hold")
        selected[str(fee)] = {
            "selected_policy": best["policy"] if best else None,
            "validation": best["validation"] if best else None,
            "test": best["test"] if best else None,
            "buy_hold_test": buy_hold["test"],
            "configs_tested": len(positions),
        }
    return {"segment_bars": len(opens), "selected": selected, "all": rows}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(history: Path, coins: list[str], output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = history / "manifest.json"
    summary: dict = {
        "schema": "coin-levels/v1",
        "history_manifest_sha256": file_sha256(manifest_path),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coins": {},
    }
    pattern_pvals: list[tuple[str, str, dict]] = []
    for coin in coins:
        coin_out: dict = {"cadences": {}}
        for label in CADENCES:
            frame, info = load_frame(history, coin.upper(), label)
            pats = patterns(frame)
            for row in pats:
                if "p_value_vs_half" in row:
                    pattern_pvals.append((coin.upper(), label, row))
            entry = {"data": info, "patterns": pats}
            if label == "1h":
                entry["levels"] = level_test(frame, label)
            entry["strategy"] = strategy_test(frame, label)
            coin_out["cadences"][label] = entry
        summary["coins"][coin.upper()] = coin_out
    adjusted = holm([row["p_value_vs_half"] for _, _, row in pattern_pvals])
    for (coin, label, row), p_adj in zip(pattern_pvals, adjusted):
        row["p_value_holm"] = p_adj
        row["holm_family_size"] = len(pattern_pvals)
    (output / "coin-levels.json").write_text(json.dumps(summary, indent=2, default=float) + "\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--coins", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.history.resolve(), args.coins, args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
