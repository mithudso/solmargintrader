"""The Bots tab: grid, triangular-arbitrage and DCA bots. Backtest, forward test, auto-optimize.

Every bot here is a simulation. Nothing in this module places an order, holds a key or talks to
a venue's trading API; the only network reads are public market data (the recorded Coinbase
stream in `pricefeed`, and Coinbase candles for the triangle candle proxy).

The three bots and the simulator each one runs:

| bot      | simulator                            | backtest data                   | forward data            |
|----------|--------------------------------------|---------------------------------|-------------------------|
| grid     | `backtester.core.gridsim` (the ladder the extension trades) | cached 1h bars | recorded 1m bars |
| triangle | `backtester.core.trianglesim`        | recorded bid/ask, else candle proxy | recorded bid/ask    |
| dca      | `backtester.core.dcasim`             | cached 1h bars                  | recorded 1m bars        |

**Backtest** answers "had I started this bot at that moment": the bot reads the price at the
start bar's close and sets itself up from it (the grid's ladder around that price, the DCA bot's
base order and safety ladder), then the simulator runs it forward over the following bars with
the repo's pessimistic fill rules and costs. The result shows what it set and what it made,
beside buy-and-hold of the same capital.

**Forward test** is the same bot run in dry-run on the future: it starts now, and every refresh
replays what the price stream has recorded since. Nothing is assumed about time the recorder
did not see; a gap longer than `MAX_FORWARD_GAP_MIN` minutes ends the forward test's coverage
at the gap and says so.

**Auto-optimize** uses `experiment_runner`: it freezes configurations and chronological
windows, stores each candidate/coin/window measurement, and chooses on train evidence
only. Validation evidence supports inspection. The newest half remains sealed until
one candidate is frozen and fresh final dates are reserved. Earlier exploration and
spent final dates cannot be relabelled as fresh by changing search settings. The
existing one-sided sign test (p < 0.05), minimum decided-cell count and positive
median improvement still gate adoption. Every path remains a simulation.

"""

from __future__ import annotations

import fcntl
import itertools
import json
import math
import threading
import time
import uuid
import zlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from backtester.core.dcasim import DcaConfig, run_dca_backtest
from backtester.core.gridsim import SPACINGS, GridConfig, grid_levels, run_grid_backtest
from backtester.core.trianglesim import (
    SOURCE_CANDLE_PROXY,
    SOURCE_RECORDED,
    TriangleConfig,
    TriangleReplay,
    parse_snapshot_line,
    snapshots_from_closes,
    triangles_from_products,
)
from backtester.core.types import CostConfig

from . import config as config_mod
from . import pricefeed

BOTS = ("grid", "triangle", "dca")
# The recurring scheduler may promote grid/DCA only when this capability is present.
# Per-coin adoption uses an atomic mode and baseline check in save_config.
PER_COIN_OPTIMIZE_ADOPTION_SAFE = True
LABELS = {"grid": "Grid bot", "triangle": "Triangle arbitrage bot", "dca": "DCA bot"}
ABOUT = {
    "grid": "Resting ladder of limit buys below the price and paired sells one rung above each fill "
            "(the strategy the extension trades). At its start it centres the ladder on the price: "
            "range_pct either side, rungs levels, capital_usd split evenly across them. Earns the rung "
            "width in a range; accumulates losing inventory in a trend.",
    "triangle": "Watches every USD triangle with a Coinbase cross pair (e.g. USD-SOL-ETH) at the best bid "
                "and ask, and executes a three-leg cycle when its net edge after three taker fees beats "
                "min_edge_bps, at the quotes latency_s later. Needs the recorded stream: candle closes "
                "carry no bid or ask, so a candle backtest is a labelled proxy.",
    "dca": "Buys a base order, rests deeper and (optionally) larger safety orders below it, and sells "
           "everything at take_profit_pct above the average entry; then starts again. Wins most deals by "
           "construction and holds the bag in a downtrend; compare it with buy-and-hold, not its win rate.",
}

GRID_DEFAULTS: dict[str, Any] = {"range_pct": 15.0, "rungs": 7, "capital_usd": 1000.0, "spacing": "geom",
                                 "deadband_bps": 25.0}
DEFAULTS: dict[str, dict[str, Any]] = {
    "grid": GRID_DEFAULTS,
    "triangle": TriangleConfig().to_dict(),
    "dca": DcaConfig().to_dict(),
}

# The representative grids auto-optimize searches. Small on purpose: every extra configuration is
# another trial, and more trials make a lucky winner likelier, not a better one.
SPACE: dict[str, dict[str, list[Any]]] = {
    "grid": {"range_pct": [5.0, 10.0, 15.0, 25.0], "rungs": [5, 9, 15], "spacing": ["geom", "arith"]},
    "triangle": {"min_edge_bps": [5.0, 15.0, 35.0, 60.0], "latency_s": [0.5, 1.0, 2.0]},
    "dca": {"price_deviation_pct": [1.0, 2.0, 3.5], "take_profit_pct": [1.0, 2.0, 4.0],
            "max_safety_orders": [3, 6], "volume_scale": [1.0, 1.5]},
}

BACKTEST_INTERVAL = "1h"
BAR_SECONDS = 3600
MAX_BRIDGE_BARS = 48  # missing hours bridged with flat bars; a longer gap ends a run
MAX_BRIDGED_FRACTION = 0.02  # an optimize window may be at most this share bridged
MIN_BACKTEST_BARS = 24
MIN_HOUR_MINUTES = 30  # an hour resampled from 1m needs this many minutes, or it counts as missing
MAX_FORWARD_GAP_MIN = 2
MAX_FORWARD_QUOTE_AGE_S = 5.0
OPTIMIZE_WINDOWS = 6
PER_COIN_OPTIMIZE_WINDOWS = 6  # half are holdout; incremental decisions are labeled tentative
PER_COIN_MIN_DECIDED_CELLS = 3
OPTIMIZE_WINDOW_DAYS = 30
PER_COIN_OPTIMIZE_WINDOW_DAYS = 3  # incremental tuning; reports small-sample confidence
SIGN_TEST_ALPHA = 0.05
MIN_DECIDED_CELLS = 10
TRIANGLE_MIN_SNAPSHOTS = 60
TRIANGLE_WINDOW_S = 3600
TRIANGLE_OPT_DAYS = 2  # 13 candidates x 10 triangles x 86,400 snapshots a day is already minutes of work
PROXY_MAX_DAYS = 3
PROXY_HALF_SPREAD_BPS = {"USD": 2.0, "cross": 10.0}
EQUITY_POINTS = 200


class BotError(ValueError):
    """A user-facing bot failure: bad config, no data, too little data."""


# -- files -------------------------------------------------------------------------------------


def home() -> Path:
    return config_mod.CONFIG_DIR / "bots"


def config_path() -> Path:
    return home() / "config.json"


def results_path() -> Path:
    return home() / "results.jsonl"


def forward_path() -> Path:
    return home() / "forward.json"


def optimize_path(bot: str) -> Path:
    return home() / f"optimize-{bot}.json"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        raise BotError(f"unreadable {path}: {exc}") from exc


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    try:
        tmp.write_text(json.dumps(_json_safe(data), indent=2, allow_nan=False), encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _json_safe(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.floating, np.integer)):
        return _json_safe(value.item())
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _bot(bot: Any) -> str:
    name = str(bot or "").strip().lower()
    if name not in BOTS:
        raise BotError(f"unknown bot {bot!r}; expected one of {', '.join(BOTS)}")
    return name


# -- configuration -----------------------------------------------------------------------------


def _coerce(bot: str, key: str, value: Any) -> Any:
    default = DEFAULTS[bot][key]
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(default, int):
        if isinstance(value, bool):
            raise BotError(f"{key} must be an integer")
        number = float(value)
        if not number.is_integer():
            raise BotError(f"{key} must be an integer, got {value!r}")
        return int(number)
    if isinstance(default, float):
        if isinstance(value, bool):
            raise BotError(f"{key} must be a number")
        number = float(value)
        if not math.isfinite(number):
            raise BotError(f"{key} must be finite")
        return number
    return str(value)


def validate(bot: str, values: dict[str, Any]) -> dict[str, Any]:
    """Defaults overlaid with `values`, coerced, and proven buildable. Unknown keys are refused."""
    bot = _bot(bot)
    unknown = sorted(set(values) - set(DEFAULTS[bot]))
    if unknown:
        raise BotError(f"unknown {bot} setting(s): {', '.join(unknown)}; "
                       f"known: {', '.join(DEFAULTS[bot])}")
    out = dict(DEFAULTS[bot])
    try:
        for key, value in values.items():
            out[key] = _coerce(bot, key, value)
        if bot == "grid":
            grid_sim_config(out, 100.0)
        elif bot == "dca":
            DcaConfig(**out)
        else:
            TriangleConfig(**out)
    except (TypeError, ValueError) as exc:
        raise BotError(f"{bot}: {exc}") from exc
    return out


def grid_sim_config(cfg: dict[str, Any], price: float) -> GridConfig:
    """The absolute ladder a relative grid config sets at `price`."""
    rng = float(cfg["range_pct"])
    if not 0 < rng < 95:
        raise ValueError("range_pct must be in (0, 95)")
    rungs = int(cfg["rungs"])
    capital = float(cfg["capital_usd"])
    if not capital > 0:
        raise ValueError("capital_usd must be > 0")
    if rungs < 2:
        raise ValueError("rungs must be at least 2")
    notional = capital / rungs
    if notional < 10.0:
        raise ValueError(f"capital_usd / rungs is ${notional:,.2f}, below the $10 venue minimum per rung")
    if cfg["spacing"] not in SPACINGS:
        raise ValueError(f"spacing must be one of {SPACINGS}")
    return GridConfig(lower=price * (1 - rng / 100.0), upper=price * (1 + rng / 100.0), rungs=rungs,
                      notional_per_rung_usd=notional, spacing=cfg["spacing"],
                      deadband_bps=float(cfg["deadband_bps"]))


def _all_configs() -> dict[str, Any]:
    raw = _read_json(config_path(), {})
    return raw if isinstance(raw, dict) else {}


def get_config(bot: str, coin: str | None = None) -> dict[str, Any]:
    bot = _bot(bot)
    all_configs = _all_configs()
    saved = all_configs.get(bot) or {}
    if coin is not None and bot != "triangle":
        symbol = _config_coin(coin)
        saved = (all_configs.get("per_coin", {}).get(bot, {}).get(symbol) or saved)
    try:
        return validate(bot, {k: v for k, v in saved.items() if k in DEFAULTS[bot]})
    except BotError:
        return dict(DEFAULTS[bot])  # a stale saved config never blocks the tab; defaults stand in


@contextmanager
def _config_lock():
    home().mkdir(parents=True, exist_ok=True)
    with (home() / "config.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _config_coin(coin: str) -> str:
    symbol = str(coin).strip().upper()
    if not symbol or not symbol.isalnum() or len(symbol) > 20:
        raise BotError("coin must be a valid asset symbol")
    return symbol


def config_mode(bot: str, coin: str | None = None) -> str:
    bot = _bot(bot)
    raw = _all_configs()
    global_mode = raw.get("modes", {}).get(bot, "auto")
    mode = (raw.get("per_coin_modes", {}).get(bot, {}).get(_config_coin(coin), global_mode)
            if coin is not None and bot != "triangle" else global_mode)
    if mode not in ("auto", "manual"):
        raise BotError("saved bot mode is invalid")
    return mode


def save_config(bot: str, values: dict[str, Any], *, merge: bool = True, reason: str = "edited",
                expected: dict[str, Any] | None = None, coin: str | None = None,
                mode: str | None = None) -> dict[str, Any]:
    """Atomically save one bot without losing another process's settings edit."""
    bot = _bot(bot)
    if mode is not None and mode not in ("auto", "manual"):
        raise BotError("mode must be auto or manual")
    with _config_lock():
        coin = _config_coin(coin) if coin is not None and bot != "triangle" else None
        current = get_config(bot, coin)
        if reason.startswith("experiment ") and config_mode(bot, coin) == "manual":
            raise BotError("manual mode is enabled; automatic adoption refused")
        if expected is not None and current != expected:
            raise BotError("baseline changed since this experiment; adoption refused")
        base = current if merge else {}
        cfg = validate(bot, {**base, **values})
        raw = _all_configs()
        if coin is None:
            if values or not merge:
                raw[bot] = cfg
            if mode is not None:
                raw.setdefault("modes", {})[bot] = mode
        else:
            if values or not merge:
                raw.setdefault("per_coin", {}).setdefault(bot, {})[coin] = cfg
            if mode is not None:
                raw.setdefault("per_coin_modes", {}).setdefault(bot, {})[coin] = mode
        history = raw.setdefault("history", [])
        history.append({"at": time.time(), "bot": bot, "coin": coin, "reason": reason, "config": cfg})
        raw["history"] = history[-50:]
        _write_json(config_path(), raw)
        return cfg


def reset_config(bot: str, coin: str | None = None) -> dict[str, Any]:
    bot = _bot(bot)
    if coin is not None and bot != "triangle":
        coin = _config_coin(coin)
        with _config_lock():
            raw = _all_configs()
            raw.get("per_coin", {}).get(bot, {}).pop(coin, None)
            raw.get("per_coin_modes", {}).get(bot, {}).pop(coin, None)
            inherited = validate(bot, raw.get(bot) or {})
            history = raw.setdefault("history", [])
            history.append({"at": time.time(), "bot": bot, "coin": coin,
                            "reason": "reset to global settings", "config": inherited})
            raw["history"] = history[-50:]
            _write_json(config_path(), raw)
            return inherited
    return save_config(bot, DEFAULTS[bot], merge=False, reason="reset to defaults", coin=coin, mode="auto")


def parse_kv(text: str) -> dict[str, str]:
    """"range_pct=10 rungs=9" -> {"range_pct": "10", "rungs": "9"}."""
    out: dict[str, str] = {}
    for token in str(text or "").replace(",", " ").split():
        key, sep, value = token.partition("=")
        if not sep or not key or value == "":
            raise BotError(f"expected name=value, got {token!r}")
        out[key.strip()] = value.strip()
    return out


# -- price data --------------------------------------------------------------------------------


def data_dir(settings: Any = None) -> Path:
    from backtester.core.data import resolve_data_dir

    configured = Path(getattr(settings, "data_dir", "") or "")
    if configured.is_absolute() and configured.exists():
        return configured
    if str(configured) not in ("", ".") and configured.exists() and any(configured.glob("*_1[mh].csv")):
        return configured.resolve()
    return resolve_data_dir()


def available_coins(settings: Any = None) -> list[str]:
    """Every coin with cached 1h or 1m bars, which is what "all the coins" means here."""
    base = data_dir(settings)
    if not base.exists():
        return []
    coins = {p.name.split("_", 1)[0].upper() for p in base.glob("*_1h.csv")}
    coins |= {p.name.split("_", 1)[0].upper() for p in base.glob("*_1m.csv")}
    return sorted(coins)


_HOURLY_CACHE: dict[tuple, dict[str, np.ndarray]] = {}


def _load_hourly(path: Path, how: str) -> dict[str, np.ndarray]:
    import pandas as pd

    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size)
    if key in _HOURLY_CACHE:
        return _HOURLY_CACHE[key]
    df = pd.read_csv(path)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    if how != "1h":
        df["hour"] = (df["timestamp"] // BAR_SECONDS) * BAR_SECONDS
        g = df.groupby("hour").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                   close=("close", "last"), volume=("volume", "sum"),
                                   minutes=("open", "size"))
        df = g[g["minutes"] >= MIN_HOUR_MINUTES].reset_index().rename(columns={"hour": "timestamp"})
    arrays = {"ts": df["timestamp"].to_numpy(dtype="int64"),
              "open": df["open"].to_numpy(dtype="float64"), "high": df["high"].to_numpy(dtype="float64"),
              "low": df["low"].to_numpy(dtype="float64"), "close": df["close"].to_numpy(dtype="float64")}
    ok = (arrays["low"] > 0) & np.isfinite(arrays["close"]) & (arrays["high"] >= arrays["low"])
    arrays = {k: v[ok] for k, v in arrays.items()}
    if len(_HOURLY_CACHE) > 60:
        _HOURLY_CACHE.clear()
    _HOURLY_CACHE[key] = arrays
    return arrays


def hourly(asset: str, settings: Any = None) -> dict[str, Any]:
    """Hourly OHLC for `asset` (gaps kept, never filled), from as far back as the caches reach.

    The 1h files start in 2023 while several 1m caches reach back to 2019, so "from the
    beginning of the data" uses the minutes resampled to hours before the 1h file starts, and
    the native hours from then on.
    An hour resampled from minutes needs `MIN_HOUR_MINUTES` of them; a thinner hour is dropped,
    which leaves a gap, because an hour built from five minutes has the wrong high and low.
    """
    a = str(asset).upper()
    base = data_dir(settings)
    h_path, m_path = base / f"{a}_1h.csv", base / f"{a}_1m.csv"
    h = _load_hourly(h_path, "1h") if h_path.exists() else None
    m = _load_hourly(m_path, "1m->1h") if m_path.exists() else None
    h = h if h is not None and h["ts"].size else None
    m = m if m is not None and m["ts"].size else None
    if h is None and m is None:
        raise BotError(f"no usable cached bars for {a} (sources missing or empty): expected {h_path} or {a}_1m.csv. "
                       f"Fetch: python -m backtester.core.fetch --asset {a} --interval 1h --start 2024-01-01")
    if h is None or not h["ts"].size:
        return {**m, "source": "1m->1h"}
    if m is None or not m["ts"].size or m["ts"][0] >= h["ts"][0]:
        return {**h, "source": "1h"}
    # Native hours wherever they exist; minutes resampled to hours only before them.
    early = m["ts"] < h["ts"][0]
    return {**{k: np.concatenate([m[k][early], h[k]]) for k in h}, "source": "1m->1h, then 1h"}


def bridged(arrays: dict[str, Any], start_index: int = 0, max_bars: int | None = None,
            step: int = BAR_SECONDS) -> dict[str, Any]:
    """The run of bars from `start_index` with short gaps bridged, ending at the first long gap.

    A gap of up to MAX_BRIDGE_BARS missing bars is filled with flat bars at the last close:
    nothing can fill during it, and the first real bar after it fills whatever its range
    crosses. That is pessimistic for the bot (a level crossed and recrossed inside an outage
    is missed) and it is reported. A longer gap ends the run there, because pretending a
    multi-day outage was flat would be a story, not data. `max_bars` counts hours of time.

    Returns {"bars": arrays, "bridged": bool per bar, "bridged_bars", "bridged_gaps", "stopped_at_gap"}.
    """
    ts = arrays["ts"]
    gaps = np.diff(ts[start_index:]) // step - 1
    long_gap = np.nonzero(gaps > MAX_BRIDGE_BARS)[0]
    end = ts.size if not long_gap.size else start_index + int(long_gap[0]) + 1
    stopped = int(ts[end - 1]) if long_gap.size else None
    real = slice(start_index, end)
    t0 = int(ts[start_index])
    grid_ts = np.arange(t0, int(ts[end - 1]) + step, step, dtype="int64")
    if max_bars is not None and grid_ts.size > max_bars:
        grid_ts = grid_ts[:max_bars]
        stopped = None
    pos = (ts[real] - t0) // step
    keep = pos < grid_ts.size
    pos = pos[keep]
    src = np.full(grid_ts.size, -1, dtype="int64")
    src[pos] = np.arange(start_index, end)[keep]
    is_bridge = src < 0
    filled = np.maximum.accumulate(np.where(is_bridge, -1, src))  # last real bar at or before each slot
    close = arrays["close"][filled]
    out = {"ts": grid_ts}
    for name in ("open", "high", "low"):
        out[name] = np.where(is_bridge, close, arrays[name][filled])
    out["close"] = close
    n_gaps = int(np.count_nonzero(np.diff(is_bridge.astype("int8")) == 1))
    return {"bars": out, "bridged": is_bridge, "bridged_bars": int(is_bridge.sum()), "bridged_gaps": n_gaps,
            "stopped_at_gap": stopped}


def usable_start(arrays: dict[str, Any], step: int = BAR_SECONDS) -> int:
    """Index of the first bar after the last gap too long to bridge (0 when there is none)."""
    gaps = np.nonzero(np.diff(arrays["ts"]) // step - 1 > MAX_BRIDGE_BARS)[0]
    return int(gaps[-1]) + 1 if gaps.size else 0


def contiguous(arrays: dict[str, Any], start_index: int, max_bars: int | None = None,
               step: int = BAR_SECONDS) -> tuple[dict[str, np.ndarray], int | None]:
    """The gap-free run of bars from `start_index` (at most `max_bars`); and the gap's ts, if one ended it."""
    ts = arrays["ts"]
    n = ts.size
    end = n if max_bars is None else min(n, start_index + max_bars)
    gaps = np.nonzero(np.diff(ts[start_index:end]) != step)[0]
    gap_at = None
    if gaps.size:
        end = start_index + int(gaps[0]) + 1
        gap_at = int(ts[end - 1])
    return {k: arrays[k][start_index:end] for k in ("ts", "open", "high", "low", "close")}, gap_at


def _start_ts(start: Any, default_days: int, last_ts: int) -> int:
    if start in (None, ""):
        return int(last_ts - default_days * 86_400)
    if isinstance(start, (int, float)) and not isinstance(start, bool):
        return int(start)
    text = str(start).strip()
    try:
        return int(float(text))
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BotError(f"start must be a UTC date like 2026-06-01 or epoch seconds, got {start!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _costs(settings: Any) -> CostConfig:
    return CostConfig(fee_bps=float(getattr(settings, "fee_bps", 6.0)),
                      slippage_bps=float(getattr(settings, "slippage_bps", 2.0)))


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _curve(ts: np.ndarray, equity: np.ndarray, hold: np.ndarray) -> list[list[float]]:
    n = ts.size
    if n == 0:
        return []
    idx = np.unique(np.linspace(0, n - 1, min(EQUITY_POINTS, n)).astype(int))
    return [[int(ts[i]), float(equity[i]), float(hold[i])] for i in idx]


# -- running one bot over bars -------------------------------------------------------------------


def run_bars(bot: str, cfg: dict[str, Any], seg: dict[str, np.ndarray], interval: str,
             costs: CostConfig) -> dict[str, Any]:
    """Run the grid or DCA bot over a gap-free bar slice; what it set and what it made."""
    price = float(seg["close"][0])
    if bot == "grid":
        gcfg = grid_sim_config(cfg, price)
        r = run_grid_backtest(gcfg, seg, initial_capital=float(cfg["capital_usd"]), interval=interval,
                              costs=costs)
        m, b = r.metrics, r.baseline_metrics
        setup = {"start_price": price, "lower": gcfg.lower, "upper": gcfg.upper, "rungs": gcfg.rungs,
                 "levels": grid_levels(gcfg), "notional_per_rung_usd": gcfg.notional_per_rung_usd,
                 "rung_width_bps": r.rung_width_bps, "capital_usd": float(cfg["capital_usd"])}
        detail = {"round_trips": r.round_trips, "buys": r.buys_filled, "sells": r.sells_filled,
                  "gross_captured_usd": r.gross_captured_usd, "realized_pnl_usd": r.realized_pnl_usd,
                  "costs_usd": r.fees_paid_usd + r.slippage_paid_usd,
                  "bars_above": r.bars_above_grid, "bars_below": r.bars_below_grid,
                  "forced_exit_qty": r.forced_exit_qty}
        equity, hold = r.equity, r.baseline_equity
    elif bot == "dca":
        dcfg = DcaConfig(**cfg)
        r = run_dca_backtest(dcfg, seg, interval=interval, costs=costs)
        m, b = r.metrics, r.baseline_metrics
        # start_price is the close the bot decided on; base_price is its base order's fill at the
        # next bar's open.
        setup = {"start_price": price, **(r.first_plan or {})}
        detail = {"deals_completed": r.deals_completed, "deals_stopped": r.deals_stopped,
                  "safety_orders_filled": r.safety_orders_filled, "max_safety_used": r.max_safety_used,
                  "realized_pnl_usd": r.realized_pnl_usd, "costs_usd": r.fees_paid_usd + r.slippage_paid_usd,
                  "open_deal_at_end": r.open_deal_at_end, "avg_deal_bars": r.avg_deal_bars,
                  "skipped": r.skipped}
        equity, hold = r.equity, r.baseline_equity
    else:
        raise BotError(f"{bot} does not run on bars")
    return {
        "set": setup,
        "results": {"total_return": m.total_return, "hold_return": b.total_return,
                    "excess_return": m.total_return - b.total_return, "sharpe": m.sharpe,
                    "max_drawdown": m.max_drawdown, "hold_max_drawdown": b.max_drawdown,
                    "final_equity": m.final_equity, "trades": m.trade_count, "win_rate": m.win_rate,
                    "bars": m.bars, **detail},
        "equity": _curve(seg["ts"], equity, hold),
    }


# -- backtest ------------------------------------------------------------------------------------


def _record(row: dict[str, Any]) -> dict[str, Any]:
    row = _json_safe(row)
    home().mkdir(parents=True, exist_ok=True)
    with results_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, allow_nan=False) + "\n")
    return row


def backtest(bot: str, asset: str, settings: Any = None, *, start: Any = None, days: Any = None,
             config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Start the bot at `start` (UTC date or epoch) and run it `days` days; default from the
    beginning of the usable data to its end."""
    bot = _bot(bot)
    cfg = validate(bot, config) if config else get_config(bot, asset)
    days_n = None if days in (None, "", 0) else float(days)
    if days_n is not None and not days_n > 0:
        raise BotError("days must be positive")
    if bot == "triangle":
        return _backtest_triangle(cfg, settings, start, days_n)
    arrays = hourly(asset, settings)
    ts = arrays["ts"]
    if ts.size < MIN_BACKTEST_BARS:
        raise BotError(f"{asset}: only {ts.size} cached bars")
    note = None
    if start in (None, ""):
        i = usable_start(arrays)
        if i:
            note = (f"the data before {_iso(int(ts[i]))} has gaps longer than {MAX_BRIDGE_BARS} h, so the "
                    "backtest starts after the last one")
    else:
        start_ts = _start_ts(start, 0, int(ts[-1]))
        i = int(np.searchsorted(ts, start_ts))
        if i >= ts.size:
            raise BotError(f"{asset}: no cached bar at or after {_iso(start_ts)}; data ends {_iso(int(ts[-1]))}")
    run = bridged(arrays, i, None if days_n is None else int(days_n * 24))
    seg = run["bars"]
    if seg["ts"].size < MIN_BACKTEST_BARS:
        raise BotError(f"{asset}: only {seg['ts'].size} bars from {_iso(int(ts[i]))} before a gap longer "
                       f"than {MAX_BRIDGE_BARS} h (after {_iso(run['stopped_at_gap'])}); pick a later start")
    out = run_bars(bot, cfg, seg, BACKTEST_INTERVAL, _costs(settings))
    return _record({"id": uuid.uuid4().hex[:12], "kind": "backtest", "bot": bot, "asset": str(asset).upper(),
                    "at": time.time(), "start_ts": int(seg["ts"][0]), "end_ts": int(seg["ts"][-1]),
                    "start": _iso(seg["ts"][0]), "end": _iso(seg["ts"][-1]), "interval": BACKTEST_INTERVAL,
                    "data_source": arrays["source"], "stopped_at_gap": _iso(run["stopped_at_gap"]),
                    "bridged_bars": run["bridged_bars"], "bridged_gaps": run["bridged_gaps"], "start_note": note,
                    "config": cfg, "fee_bps": _costs(settings).fee_bps,
                    "slippage_bps": _costs(settings).slippage_bps, **out})


def _coin_list(coins: Any, settings: Any) -> list[str]:
    if coins in (None, "", []):
        return [str(getattr(settings, "asset", "SOL")).upper()]
    if isinstance(coins, str):
        coins = [c for c in coins.replace(",", " ").split() if c]
    names = [str(c).upper() for c in coins]
    if names == ["ALL"]:
        return available_coins(settings)
    return list(dict.fromkeys(names))


def backtest_many(bot: str, coins: Any, settings: Any = None, *, start: Any = None, days: Any = None,
                  progress: Callable[[float, str], None] | None = None) -> dict[str, Any]:
    """The same bot and start on several coins: one saved backtest each, and a per-coin summary.

    A coin that cannot run (no data, start past its data) is listed under `errors` with the
    reason, never silently dropped. The triangle bot watches every triangle at once, so it runs once.
    """
    bot = _bot(bot)
    names = ["ALL"] if bot == "triangle" else _coin_list(coins, settings)
    runs, errors, summary = [], {}, []
    for k, coin in enumerate(names):
        if progress:
            progress(k / max(1, len(names)), f"{coin} ({k + 1}/{len(names)})")
        try:
            r = backtest(bot, coin, settings, start=start, days=days)
        except (BotError, ValueError, RuntimeError) as exc:
            errors[coin] = str(exc)
            continue
        runs.append(r)
        res = r["results"]
        summary.append({"coin": r["asset"], "start": r["start"], "end": r["end"], "bars": res.get("bars"),
                        "total_return": res.get("total_return"), "hold_return": res.get("hold_return"),
                        "excess_return": res.get("excess_return"), "max_drawdown": res.get("max_drawdown"),
                        "trades": res.get("trades", res.get("executed")), "pnl_usd": res.get("pnl_usd"),
                        "bridged_bars": r.get("bridged_bars", 0), "data_source": r["data_source"],
                        "id": r["id"]})
    beat = [row for row in summary if (row.get("excess_return") or 0) > 0]
    return {"bot": bot, "coins": names, "runs": runs, "errors": errors, "summary": summary,
            "beat_hold": len(beat), "ran": len(summary)}


def _iter_recorded(start_ts: float, end_ts: float | None, *, last_days: int | None = None):
    """Recorded snapshots from `start_ts`, streamed file by file (optionally only the newest days)."""
    from backtester.core.trianglesim import iter_snapshot_files

    first_day = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d")
    files = [p for p in pricefeed.recorded_files() if p.name[:10] >= first_day]
    if last_days is not None:
        files = files[-last_days:]
    return iter_snapshot_files(files, start_ts=start_ts, end_ts=end_ts)


def proxy_half_spreads(products: Iterable[str]) -> dict[str, float]:
    """Half-spread per product for the candle proxy: the recorded one when known, else a cautious default."""
    latest = pricefeed.read_latest() or {}
    quotes = latest.get("q") or {}
    out = {}
    for p in products:
        q = quotes.get(p)
        default = PROXY_HALF_SPREAD_BPS["USD" if p.endswith("-USD") else "cross"]
        try:
            bid, ask = float(q[0]), float(q[1])
            out[p] = max(default / 4, 5_000.0 * (ask - bid) / ((ask + bid) / 2))
        except (TypeError, ValueError, IndexError, ZeroDivisionError):
            out[p] = default
    return out


def _proxy_snapshots(products: Sequence[str], start_ts: int, end_ts: int,
                     fetch: Callable[..., Any] | None = None) -> tuple[list[tuple[float, dict]], list[str]]:
    """Coinbase 1m closes for every leg, cached under bots/cache, as spread-padded snapshots;
    and the legs with no candle at all in the window (no trade, so no proxy quote)."""
    import pandas as pd

    from backtester.core.fetch import FetchError, fetch_coinbase

    fetch = fetch or fetch_coinbase
    cache = home() / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    closes: dict[str, list[tuple[float, float]]] = {}
    missing: list[str] = []
    for product in products:
        path = cache / f"{product}_1m_{start_ts}_{end_ts}.csv"
        if path.exists():
            df = pd.read_csv(path)
        else:
            try:
                df = fetch(product, _stamp(start_ts), _stamp(end_ts), "1m", verbose=False)
            except FetchError as exc:
                if "no candles" not in str(exc):
                    raise BotError(f"candle proxy: could not fetch {product} 1m candles: {exc}") from exc
                df = pd.DataFrame({"timestamp": [], "close": []})  # no trade in the window: no candle
            df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)]
            df.to_csv(path, index=False)
        if df.empty:
            missing.append(product)
            continue
        closes[product] = list(zip(df["timestamp"].astype(float), df["close"].astype(float)))
    return snapshots_from_closes(closes, proxy_half_spreads(products)), missing


def _stamp(ts: float) -> str:
    """A naive UTC ISO time, which `fetch_coinbase` reads as UTC (it is never in the future here)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _triangle_products() -> list[str]:
    latest = pricefeed.read_latest() or {}
    products = latest.get("products") or []
    try:
        products = products or pricefeed.stream_products()
    except Exception:  # noqa: BLE001 - the fallback list below covers every failure
        products = []
    return list(products or pricefeed.FALLBACK_PRODUCTS)


def _triangle_summary(result: Any) -> dict[str, Any]:
    s = result.summary()
    observed = [r for r in s["per_triangle"].values() if r["best_edge_bps"] is not None]
    return {"executed": s["executed"], "wins": s["wins"], "pnl_usd": s["pnl_usd"],
            "snapshots": s["snapshots"], "triangles_observed": len(observed),
            "best_net_edge_bps": max((r["best_edge_bps"] for r in observed), default=None),
            "per_triangle": s["per_triangle"], "cycles": s["cycles"]}


def _backtest_triangle(cfg: dict[str, Any], settings: Any, start: Any, days: float | None) -> dict[str, Any]:
    tcfg = TriangleConfig(**cfg)
    tris = triangles_from_products(_triangle_products())
    now = time.time()
    first_file = pricefeed.recorded_files()[:1]
    recorded_from = None
    if first_file:
        recorded_from = datetime.strptime(first_file[0].name[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    default_start = recorded_from if recorded_from is not None else now - 86_400
    start_ts = _start_ts(start, 1, int(now)) if start not in (None, "") else int(default_start)
    end_ts = None if days is None else start_ts + days * 86_400
    source = SOURCE_RECORDED
    missing_legs: list[str] = []
    replay = TriangleReplay(tcfg, tris, source=source)
    for t, q in _iter_recorded(start_ts, end_ts):
        replay.feed(t, q)
    if replay.snapshots < TRIANGLE_MIN_SNAPSHOTS:
        span = min(days or 1.0, PROXY_MAX_DAYS)
        end = int(min(now - 120, start_ts + span * 86_400))
        if end - start_ts < 3600:
            raise BotError(f"only {replay.snapshots} recorded snapshots from {_iso(start_ts)} and too little "
                           "history for a candle proxy; start the recorder and backtest later")
        legs = sorted({leg for t in tris for leg in t.products})
        snaps, missing_legs = _proxy_snapshots(legs, int(start_ts), end)
        source = SOURCE_CANDLE_PROXY
        # One-minute candles: a cycle seen in one minute executes at the next one, and a leg
        # with no candle in a minute did not trade in it, so its quote is a minute stale.
        tcfg = TriangleConfig(**{**cfg, "latency_s": max(tcfg.latency_s, 60.0),
                                 "max_quote_age_s": max(tcfg.max_quote_age_s, 1.0)})
        replay = TriangleReplay(tcfg, tris, source=source)
        for t, q in snaps:
            replay.feed(t, q)
    result = replay.result()
    summary = _triangle_summary(result)
    setup = {"triangles": [t.name for t in tris], "min_edge_bps": tcfg.min_edge_bps,
             "legs_without_candles": missing_legs if source == SOURCE_CANDLE_PROXY else [],
             "taker_fee_bps": tcfg.taker_fee_bps, "break_even_gross_bps": 10_000 * (1 / (1 - tcfg.taker_fee_bps / 1e4) ** 3 - 1),
             "latency_s": tcfg.latency_s, "notional_usd": tcfg.notional_usd}
    return _record({"id": uuid.uuid4().hex[:12], "kind": "backtest", "bot": "triangle", "asset": "ALL",
                    "at": time.time(), "start_ts": result.start_ts, "end_ts": result.end_ts,
                    "start": _iso(result.start_ts), "end": _iso(result.end_ts), "interval": "snapshots",
                    "data_source": source, "stopped_at_gap": None, "config": cfg, "set": setup,
                    "results": summary, "equity": []})


def latest_results(bot: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    path = results_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines()[-500:]:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if bot is None or row.get("bot") == bot:
            rows.append(row)
    return rows[-limit:][::-1]


# -- forward test ---------------------------------------------------------------------------------


class SnapshotCursor:
    """Reads only what the recorder appended since the last call.

    Every recorder flush is a complete gzip member, so the byte offset after the last complete
    member is a safe place to resume. A member still being written fails to decompress to its
    end and is left for the next call.
    """

    CHUNK = 16_384

    def __init__(self, start_ts: float, root: Path | None = None) -> None:
        self.start_ts = float(start_ts)
        self.root = root
        self.offsets: dict[str, int] = {}
        self._committed = 0
        self._pending: list[tuple[float, dict]] = []

    def _complete_members(self, data: bytes) -> list[str]:
        """Lines of every complete gzip member in `data`; sets `_committed` to the end of the last.

        Fed in fixed chunks so the work is linear in the file: handing the decompressor the whole
        remainder once per member would copy that remainder once per member, which on a full day
        file (thousands of members) is quadratic.
        """
        view = memoryview(data)
        lines: list[str] = []
        self._committed = 0
        d = zlib.decompressobj(wbits=31)
        parts: list[bytes] = []
        base = 0
        feed: bytes | memoryview = view[0:self.CHUNK]
        base = len(feed)
        while len(feed):
            try:
                parts.append(d.decompress(feed))
            except zlib.error:
                break
            if d.eof:
                leftover = d.unused_data
                self._committed = base - len(leftover)
                lines.extend(b"".join(parts).decode("utf-8", errors="replace").splitlines())
                d, parts = zlib.decompressobj(wbits=31), []
                if leftover:
                    feed = leftover
                    continue
            if base >= len(data):
                break
            feed = view[base:base + self.CHUNK]
            base += len(feed)
        return lines

    def read_new(self, end_ts: float | None = None) -> list[tuple[float, dict]]:
        out = [r for r in self._pending if end_ts is None or r[0] <= end_ts]
        self._pending = [r for r in self._pending if end_ts is not None and r[0] > end_ts]
        first_day = datetime.fromtimestamp(self.start_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        for path in pricefeed.recorded_files(self.root):
            if path.name[:10] < first_day:
                continue
            offset = self.offsets.get(path.name, 0)
            try:
                with path.open("rb") as fh:
                    fh.seek(offset)
                    data = fh.read()
            except OSError:
                continue
            for line in self._complete_members(data):
                parsed = parse_snapshot_line(line, require_quote_time=True)
                if parsed is None or parsed[0] < self.start_ts:
                    continue
                if end_ts is not None and parsed[0] > end_ts:
                    self._pending.append(parsed)
                    continue
                out.append(parsed)
            pos = self._committed
            self.offsets[path.name] = offset + pos
        out.sort(key=lambda r: r[0])
        return out


class MinuteBars:
    """One product's one-minute mid-price bars, built from one-second snapshots."""

    def __init__(self, product: str) -> None:
        self.product = product
        self.bars: dict[int, list[float]] = {}

    def feed(self, t: float, quotes: dict[str, Any]) -> None:
        q = quotes.get(self.product)
        if q is None or len(q) != 5:
            return
        try:
            bid, ask, quote_time = float(q[0]), float(q[1]), float(q[4])
        except (TypeError, ValueError):
            return
        if (not all(math.isfinite(v) for v in (t, bid, ask, quote_time))
                or not 0 < bid <= ask or not 0 <= t - quote_time <= MAX_FORWARD_QUOTE_AGE_S):
            return
        mid = bid + (ask - bid) / 2.0
        minute = int(t // 60) * 60
        bar = self.bars.get(minute)
        if bar is None:
            self.bars[minute] = [mid, mid, mid, mid]
        else:
            bar[1] = max(bar[1], mid)
            bar[2] = min(bar[2], mid)
            bar[3] = mid

    def arrays(self, before: float) -> tuple[dict[str, np.ndarray], int | None, int]:
        """Completed bars before `before`, from the first, bridging gaps of up to MAX_FORWARD_GAP_MIN
        missing minutes with flat bars at the last close; a longer gap ends the series there.
        Returns (arrays, gap_start_ts or None, bridged minutes)."""
        cutoff = int(before // 60) * 60
        minutes = sorted(m for m in self.bars if m < cutoff)
        rows: list[list[float]] = []
        gap_at = None
        bridged = 0
        for m in minutes:
            if rows:
                missing = (m - int(rows[-1][0])) // 60 - 1
                if missing > MAX_FORWARD_GAP_MIN:
                    gap_at = int(rows[-1][0])
                    break
                last = rows[-1][4]
                for k in range(1, missing + 1):
                    rows.append([rows[-1][0] + 60, last, last, last, last])
                bridged += max(0, missing)
            o, h, low, c = self.bars[m]
            rows.append([m, o, h, low, c])
        if rows and gap_at is None:
            missing = (cutoff - int(rows[-1][0])) // 60 - 1
            if missing > MAX_FORWARD_GAP_MIN:
                gap_at = int(rows[-1][0])
            else:
                last = rows[-1][4]
                for _ in range(max(0, missing)):
                    rows.append([rows[-1][0] + 60, last, last, last, last])
                bridged += max(0, missing)
        arr = np.asarray(rows, dtype="float64").reshape(-1, 5)
        return ({"ts": arr[:, 0].astype("int64"), "open": arr[:, 1], "high": arr[:, 2], "low": arr[:, 3],
                 "close": arr[:, 4]}, gap_at, bridged)


@dataclass
class ForwardSession:
    """In-memory replay state for one forward test, fed incrementally from the recording."""

    run_id: str
    cursor: SnapshotCursor
    bars: MinuteBars | None = None
    replay: TriangleReplay | None = None
    last_ts: float | None = None
    snapshots: int = 0


@dataclass
class BotRuntime:
    """What outlives one command call in a long-lived process (the console)."""

    sessions: dict[str, ForwardSession] = field(default_factory=dict)
    progress: dict[str, dict[str, Any]] = field(default_factory=dict)
    # A forward refresh feeds a session's replay; two at once (the timer and a button) would
    # feed it from two threads.
    lock: threading.RLock = field(default_factory=threading.RLock)


_RUNTIME = BotRuntime()


def runtime() -> BotRuntime:
    return _RUNTIME


def _forward_all() -> dict[str, Any]:
    raw = _read_json(forward_path(), {})
    return raw if isinstance(raw, dict) else {}


@contextmanager
def _forward_lock():
    home().mkdir(parents=True, exist_ok=True)
    with (home() / "forward.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def forward_start(bot: str, asset: str, settings: Any = None, *, ensure_recorder: bool = True,
                  now: float | None = None) -> dict[str, Any]:
    """Start (or restart) the bot's forward test now, on the current config."""
    bot = _bot(bot)
    now = time.time() if now is None else now
    a = "ALL" if bot == "triangle" else str(asset).upper()
    if bot != "triangle" and f"{a}-USD" not in _triangle_products():
        raise BotError(f"{a}-USD is not in the recorded stream; forward tests need a Coinbase USD market")
    recorder = pricefeed.ensure_recorder() if ensure_recorder else {"running": None}
    with runtime().lock, _forward_lock():
        raw = _forward_all()
        raw[bot] = {"id": uuid.uuid4().hex[:12], "bot": bot, "asset": a, "config": get_config(bot, a),
                    "started_at": now, "stopped_at": None, "fee_bps": _costs(settings).fee_bps,
                    "slippage_bps": _costs(settings).slippage_bps}
        _write_json(forward_path(), raw)
        runtime().sessions.pop(bot, None)
    return {"forward": raw[bot], "recorder": recorder}


def forward_stop(bot: str, *, now: float | None = None) -> dict[str, Any]:
    bot = _bot(bot)
    with runtime().lock, _forward_lock():
        raw = _forward_all()
        rec = raw.get(bot)
        if not rec:
            return {"stopped": False, "message": f"no {bot} forward test is running"}
        if rec.get("stopped_at") is None:
            rec["stopped_at"] = time.time() if now is None else now
            _write_json(forward_path(), raw)
    return {"stopped": True, "forward": rec}


def forward_status(bot: str, settings: Any = None, *, now: float | None = None,
                   root: Path | None = None) -> dict[str, Any]:
    """Replay everything recorded since the forward test started through the bot, in dry-run."""
    bot = _bot(bot)
    now = time.time() if now is None else now
    rec = _forward_all().get(bot)
    stream = pricefeed.status(root, now)
    stream_brief = {k: stream[k] for k in ("running", "live", "snapshot_age_s", "recorded_days", "last_error")}
    if not rec:
        return {"bot": bot, "running": False, "message": "no forward test; press Start forward test",
                "recorder": stream_brief}
    end = rec.get("stopped_at") or now
    with runtime().lock:
        return _forward_replay(bot, rec, end, settings, stream_brief, root)


def _forward_replay(bot: str, rec: dict[str, Any], end: float, settings: Any, stream_brief: dict[str, Any],
                    root: Path | None) -> dict[str, Any]:
    sess = runtime().sessions.get(bot)
    if sess is None or sess.run_id != rec["id"]:
        sess = ForwardSession(rec["id"], SnapshotCursor(float(rec["started_at"]), root))
        cfg = rec["config"]
        if bot == "triangle":
            sess.replay = TriangleReplay(TriangleConfig(**cfg), triangles_from_products(_triangle_products()))
        else:
            sess.bars = MinuteBars(f"{rec['asset']}-USD")
        runtime().sessions[bot] = sess
    for t, q in sess.cursor.read_new(end_ts=end):
        if sess.last_ts is not None and t <= sess.last_ts:
            continue  # a snapshot already fed (files are append-only, but stay idempotent)
        sess.last_ts = t
        sess.snapshots += 1
        if sess.replay is not None:
            sess.replay.feed(t, q)
        elif sess.bars is not None:
            sess.bars.feed(t, q)
    base = {"bot": bot, "running": rec.get("stopped_at") is None, "forward": rec,
            "started": _iso(rec["started_at"]), "stopped": _iso(rec.get("stopped_at")),
            "snapshots": sess.snapshots, "last_snapshot": _iso(sess.last_ts), "recorder": stream_brief}
    if bot == "triangle":
        result = sess.replay.result() if sess.replay else None
        return {**base, "results": _triangle_summary(result) if result else {}}
    assert sess.bars is not None
    arrays, gap_at, bridged = sess.bars.arrays(before=end)
    base.update({"bars": int(arrays["ts"].size), "bridged_minutes": bridged, "stopped_at_gap": _iso(gap_at)})
    if arrays["ts"].size < 2:
        return {**base, "message": "waiting for the stream: fewer than two completed minutes recorded"}
    costs = CostConfig(fee_bps=float(rec.get("fee_bps", 6.0)), slippage_bps=float(rec.get("slippage_bps", 2.0)))
    out = run_bars(bot, rec["config"], arrays, "1m", costs)
    return {**base, **out, "last_price": float(arrays["close"][-1])}


# -- auto-optimize --------------------------------------------------------------------------------


# Where each setting may roam when a re-run widens the search: (kind, low, high, scale).
DOMAINS: dict[str, dict[str, tuple]] = {
    "grid": {"range_pct": ("float", 2.0, 60.0, "log"), "rungs": ("int", 3, 40, "log"),
             "spacing": ("choice", ("geom", "arith")), "deadband_bps": ("float", 0.0, 100.0, "lin")},
    "dca": {"price_deviation_pct": ("float", 0.3, 10.0, "log"), "take_profit_pct": ("float", 0.3, 10.0, "log"),
            "max_safety_orders": ("int", 0, 12, "lin"), "volume_scale": ("float", 1.0, 2.5, "lin"),
            "step_scale": ("float", 0.8, 2.0, "lin"), "stop_loss_pct": ("float", 0.0, 40.0, "lin"),
            "cooldown_bars": ("int", 0, 48, "lin")},
    "triangle": {"min_edge_bps": ("float", 0.0, 100.0, "lin"), "latency_s": ("float", 0.2, 5.0, "log"),
                 "max_quote_age_s": ("float", 1.0, 20.0, "log"), "cooldown_s": ("float", 0.0, 60.0, "lin")},
}
RANDOM_PER_RUN = 12
MAX_CANDIDATES = 97


def _cfg_key(cfg: dict[str, Any]) -> str:
    return json.dumps(cfg, sort_keys=True)


def history_path(bot: str, coin: str | None = None) -> Path:
    suffix = f"-{_config_coin(coin)}" if coin else ""
    return home() / f"optimize-history-{bot}{suffix}.json"


def optimize_history(bot: str, coin: str | None = None) -> dict[str, Any]:
    raw = _read_json(history_path(_bot(bot), coin), {})
    if not isinstance(raw, dict):
        raw = {}
    return {"runs": int(raw.get("runs") or 0), "tried": list(raw.get("tried") or []), "log": list(raw.get("log") or [])}


def _sample(bot: str, current: dict[str, Any], rng: np.random.Generator, spread: float) -> dict[str, Any]:
    """One configuration around `current`: each setting moves with some probability, by up to
    `spread` (a fraction of its whole domain, log-scaled where the setting is multiplicative)."""
    out = dict(current)
    for key, dom in DOMAINS[bot].items():
        if rng.random() > min(1.0, 0.35 + spread):
            continue
        if dom[0] == "choice":
            out[key] = str(rng.choice(dom[1]))
            continue
        kind, lo, hi, scale = dom
        value = float(current[key])
        if scale == "log":
            llo, lhi = math.log(lo), math.log(hi)
            centre = math.log(min(max(value, lo), hi))
            x = math.exp(min(lhi, max(llo, centre + rng.uniform(-1, 1) * spread * (lhi - llo))))
        else:
            x = min(hi, max(lo, value + rng.uniform(-1, 1) * spread * (hi - lo)))
        out[key] = int(round(x)) if kind == "int" else round(float(x), 3)
    return out


def candidates(bot: str, current: dict[str, Any], run: int = 1,
               tried: Iterable[str] = ()) -> list[dict[str, Any]]:
    """The configurations one auto-optimize run tests, current settings first.

    Run 1 is the fixed representative grid in SPACE. Every later run widens the search: it
    skips configurations earlier runs already tried, adds every one-setting neighbour of the
    current settings, and fills up to RANDOM_PER_RUN more configurations than the first run per
    run number with random samples whose reach grows with the run number until it covers each
    setting's whole domain. The sampler is seeded
    by bot and run, so a run's candidate list is reproducible.
    """
    bot = _bot(bot)
    seen = {_cfg_key(current)}
    skip = set(tried)
    out = [current]

    def add(values: dict[str, Any]) -> None:
        if len(out) >= MAX_CANDIDATES:
            return
        try:
            cfg = validate(bot, values)
        except BotError:
            return
        key = _cfg_key(cfg)
        if key in seen or (run > 1 and key in skip):
            return
        seen.add(key)
        out.append(cfg)

    keys = list(SPACE[bot])
    for combo in itertools.product(*(SPACE[bot][k] for k in keys)):
        add({**current, **dict(zip(keys, combo))})
    if run <= 1:
        return out
    for key, dom in DOMAINS[bot].items():  # one-setting neighbours of the current settings
        if dom[0] == "choice":
            for choice in dom[1]:
                add({**current, key: choice})
            continue
        kind, lo, hi, scale = dom
        value = float(current[key])
        for factor in (0.5, 0.8, 1.25, 2.0):
            x = value * factor if scale == "log" or value else lo + (hi - lo) * (factor - 0.5) / 4
            x = min(hi, max(lo, x))
            add({**current, key: int(round(x)) if kind == "int" else round(x, 3)})
    rng = np.random.default_rng(zlib.crc32(f"{bot}|{run}".encode()))
    spread = min(1.0, 0.15 * run)
    # Each run tests more configurations than the one before: the first run's grid size plus
    # RANDOM_PER_RUN more per run, filled with fresh samples.
    grid_size = math.prod(len(v) for v in SPACE[bot].values()) + 1
    target = min(MAX_CANDIDATES, grid_size + RANDOM_PER_RUN * (run - 1))
    attempts = 0
    while len(out) < target and attempts < 50 * RANDOM_PER_RUN * run:
        attempts += 1
        add(_sample(bot, current, rng, spread))
    return out


def windows_for(arrays: dict[str, Any], count: int, bars: int) -> list[dict[str, np.ndarray]]:
    """Up to `count` non-overlapping windows of `bars` hours from the most recent history, oldest first.

    Short gaps are bridged (see `bridged`); a window may be at most MAX_BRIDGED_FRACTION bridged,
    and no window spans a gap too long to bridge.
    """
    ts = arrays["ts"]
    if ts.size == 0:
        return []
    # Split at the long gaps, newest segment first.
    long_gaps = np.nonzero(np.diff(ts) // BAR_SECONDS - 1 > MAX_BRIDGE_BARS)[0]
    starts = [0] + [int(g) + 1 for g in long_gaps]
    out: list[dict[str, np.ndarray]] = []
    for s0 in reversed(starts):
        run = bridged(arrays, s0)
        seg, flags = run["bars"], run["bridged"]
        end = seg["ts"].size
        while end - bars >= 0 and len(out) < count:
            lo = end - bars
            if flags[lo:end].mean() <= MAX_BRIDGED_FRACTION:
                out.append({k: v[lo:end] for k, v in seg.items()})
                end = lo
            else:
                end -= max(1, bars // 4)
        if len(out) >= count:
            break
    return out[::-1]


def sign_test_p(wins: int, losses: int) -> float:
    """One-sided P(X >= wins) for X ~ Binomial(wins + losses, 1/2); 1.0 when nothing was decided."""
    n = wins + losses
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n)


def _ranks(scores: list[float]) -> list[float]:
    """Rank 1 = best (highest); ties share the average rank."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def _changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"setting": k, "before": before.get(k), "after": v} for k, v in after.items() if before.get(k) != v]


def optimize(bot: str, settings: Any = None, *, coins: Sequence[str] | None = None,
             windows: int = OPTIMIZE_WINDOWS, window_days: int = OPTIMIZE_WINDOW_DAYS, adopt: bool = True,
             progress: Callable[[float, str], None] | None = None) -> dict[str, Any]:
    """Run the durable native experiment engine and guarded final validation.

    This compatibility route shares the workbench's immutable evidence, cell
    checkpoints and spent-date ledger. Re-running a search never refreshes its
    final test dates.
    """
    from .experiment_runner import optimize as run_optimize

    bot = _bot(bot)
    if bot == "triangle":
        return run_optimize(bot, settings, coins=coins, windows=windows, window_days=window_days,
                            adopt=adopt, progress=progress)
    names = _coin_list(coins if coins is not None else "all", settings)
    reports: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for index, coin in enumerate(names):
        def coin_progress(fraction: float, message: str) -> None:
            if progress:
                progress((index + fraction) / max(1, len(names)), f"{coin}: {message}")
        try:
            reports[coin] = run_optimize(bot, settings, coins=[coin], windows=windows, window_days=window_days,
                                         adopt=adopt, progress=coin_progress, config_coin=coin)
            report = reports[coin]
            if coin not in (report.get("coins_used") or []):
                skipped = report.get("skipped") or {}
                errors[coin] = str(skipped.get(coin) or "No usable evaluation windows for this coin")
        except Exception as exc:  # one failed coin must not silently cancel the others
            errors[coin] = f"{type(exc).__name__}: {exc}"[:300]
    per_coin = [row | {"verdict": report.get("verdict", {})} for report in reports.values()
                for row in report.get("per_coin", [])]
    saved = sum(bool(report.get("verdict", {}).get("saved")) for report in reports.values())
    complete = bool(names) and not errors and len(reports) == len(names) and all(
        r.get("status") in ("completed", "explored") for r in reports.values())
    used = [coin for coin, report in reports.items() if coin in (report.get("coins_used") or [])]
    result = {"bot": bot, "source": "per_coin_ledger_v1", "status": "completed" if complete else "partial", "at": time.time(),
              "run": max((int(r.get("run", 1)) for r in reports.values()), default=1), "coins_requested": names,
              "coins_used": used, "skipped": errors, "reports": reports, "per_coin": per_coin,
              "candidates": sum(int(r.get("candidates", 0)) for r in reports.values()),
              "train_cells": sum(int(r.get("train_cells", 0)) for r in reports.values()),
              "validation_cells": sum(int(r.get("validation_cells", 0)) for r in reports.values()),
              "test_cells": sum(int(r.get("test_cells", 0)) for r in reports.values()),
              "seconds": sum(float(r.get("seconds", 0)) for r in reports.values()),
              "universe": "independent searches and holdouts per coin", "table": [],
              "verdict": {"saved": bool(saved), "adopted": bool(saved),
                          "reliable": any(bool(r.get("verdict", {}).get("reliable")) for r in reports.values()), "changes": [],
                          "reason": f"{saved} coin-specific setting(s) saved; {len(errors)} coin(s) failed. "
                                    "Each coin must independently pass the evidence floor."}}
    _write_json(optimize_path(bot), result)
    return result


def latest_optimize(bot: str) -> dict[str, Any] | None:
    return _read_json(optimize_path(_bot(bot)), None)


def overview(settings: Any = None) -> dict[str, Any]:
    """Everything the tab shows at a glance, for every bot."""
    rows = []
    forward = _forward_all()
    for bot in BOTS:
        last = latest_results(bot, 1)
        opt = None
        try:
            opt = latest_optimize(bot)
        except BotError:
            pass
        rows.append({"bot": bot, "label": LABELS[bot], "about": ABOUT[bot], "config": get_config(bot),
                     "defaults": DEFAULTS[bot], "space": SPACE[bot],
                     "last_backtest": last[0] if last else None, "forward": forward.get(bot),
                     "optimize": (opt or {}).get("verdict"), "optimized_at": (opt or {}).get("at"),
                     "progress": runtime().progress.get(bot)})
    return {"bots": rows, "coins": available_coins(settings)}
