"""Backtest a scorecard configuration on 5m bars: direction accuracy and net P&L, IS vs OOS.

    from backtester.core.compound import run_compound, load_bars_5m
    report = run_compound("SOL", config)

Two different questions, answered separately because they disagree at 5m:

  * **Does the call predict the next bar?** `forecast_stats` scores every bar's call against
    sign(close[t+1] - close[t]). A hit rate above the base rate is necessary, not sufficient.
  * **Does trading it make money after costs?** The precomputed target path (with entry/exit
    hysteresis) is fed to the existing engine (`engine.run_backtest`, perp mode, Hyperliquid fees,
    borrow, liquidation at the bar's low/high), so there is one execution model, not two.

The sample is split by time: the first `1 - oos_fraction` of bars is in-sample, the rest
out-of-sample. Nothing is fitted here, so "in-sample" only means "the period a person tuning
weights in the tab would have looked at"; ranking uses OOS.

Gaps: each contiguous run of bars is evaluated on its own (see `scorecard.contiguous_segments`)
and its P&L stitched by returns. No missing bar is invented.

No network. Data comes from the gitignored cache written by the explicit fetch step.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from . import scorecard as sc
from .data import describe_data_error, resolve_data_dir, validate_bars
from .engine import EngineConfig, run_backtest
from .types import BarWindow, CostConfig, Mode

BARS_PER_YEAR = 365 * 288
# Segments shorter than this are dropped: indicators would never leave warm-up.
MIN_SEGMENT_BARS = 300
# Below these an OOS row is listed but not ranked (a hit rate on 40 calls is noise).
MIN_OOS_CALLS = 200
MIN_OOS_TRADES = 30


class CompoundDataError(RuntimeError):
    """No usable 5m data for an asset."""


def _read(path: Path, interval: str = "5m") -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        return validate_bars(df, interval, strict_gaps=False)
    except (ValueError, OSError) as exc:
        raise CompoundDataError(f"compound source {path}: {describe_data_error(exc)}") from exc


def resample_complete(df_1m: pd.DataFrame, minutes: int = 5) -> pd.DataFrame:
    """Aggregate 1m bars into `minutes` bars from the minutes present, counting them.

    A bucket with no 1m candle stays a gap; nothing is invented. A bucket with SOME minutes
    missing is kept, because requiring all five discards most of a thin market (DOGE, ZEC had
    no contiguous run of 300 bars that way). It is not a clean bar, though: Coinbase's candle
    endpoint drops minutes that DID trade (84% of sampled gaps, research/CANDLE-GAP-AUDIT.md),
    so such a bucket can carry a wrong close and an understated high/low -- what liquidation
    checks read. The `minutes` column records how many 1m candles each bar was built from, and
    the backtest reports the incomplete share per coin so a reader can discount it.
    """
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1:
        raise CompoundDataError("resample interval must be a positive whole minute")
    try:
        d = validate_bars(df_1m, "1m", strict_gaps=False)
    except ValueError as exc:
        raise CompoundDataError(f"compound minute source: {describe_data_error(exc)}") from exc
    if (d["timestamp"] % 60).any():
        raise CompoundDataError("compound source minutes must align to their UTC minute grid")
    step = minutes * 60
    d["bucket"] = (d["timestamp"] // step) * step
    g = d.groupby("bucket", sort=True)
    return pd.DataFrame({
        "timestamp": g["timestamp"].first().index.astype("int64"),
        "open": g["open"].first().to_numpy(),
        "high": g["high"].max().to_numpy(),
        "low": g["low"].min().to_numpy(),
        "close": g["close"].last().to_numpy(),
        "volume": g["volume"].sum().to_numpy(),
        "minutes": g["timestamp"].count().to_numpy(),
    }).reset_index(drop=True)


def candidate_files(asset: str, data_dir: Path) -> list[tuple[Path, str]]:
    """(path, how) in preference order: native 5m first, then 1m resampled."""
    a = asset.upper()
    return [
        (data_dir / f"{a}_5m.csv", "5m"),
        (data_dir / f"{a}_5m_last30d.csv", "5m"),
        (data_dir / f"{a}_1m.csv", "1m->5m"),
        (data_dir / f"{a}_1m_last30d.csv", "1m->5m"),
    ]


def load_bars_5m(asset: str, data_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    """The longest available 5m series for `asset`, and a description of where it came from."""
    data_dir = Path(data_dir) if data_dir else resolve_data_dir()
    best: tuple[pd.DataFrame, str] | None = None
    for path, how in candidate_files(asset, data_dir):
        if not path.exists():
            continue
        df = _read(path, "1m" if how == "1m->5m" else "5m")
        if how == "1m->5m":
            df = resample_complete(df)
        if best is None or len(df) > len(best[0]):
            label = f"{path.name} ({how})"
            sidecar = path.with_name(path.stem + ".source.json")
            if sidecar.exists():  # a non-Coinbase venue: say which, and that it is a USDT pair
                try:
                    meta = json.loads(sidecar.read_text())
                    if isinstance(meta, dict):
                        label = f"{path.name} ({how}, {meta.get('venue')} {meta.get('pair')})"
                except (OSError, ValueError):
                    pass
            best = (df, label)
    if best is None or len(best[0]) < MIN_SEGMENT_BARS:
        raise CompoundDataError(
            f"no usable 5m data for {asset.upper()} in {data_dir}. Fetch it:\n"
            f"  python3 -m backtester.core.fetch --asset {asset.upper()} --interval 5m "
            f"--start <YYYY-MM-DD> --allow-gaps --out {data_dir / (asset.upper() + '_5m.csv')}")
    return best


def available_assets(data_dir: Path | None = None) -> list[str]:
    """Assets with any 5m-capable file in the cache."""
    data_dir = Path(data_dir) if data_dir else resolve_data_dir()
    found = set()
    for path in data_dir.glob("*_*m*.csv"):
        name = path.name
        asset = name.split("_", 1)[0]
        if any(name == c.name for c, _ in candidate_files(asset, data_dir)):
            found.add(asset)
    from .assets import filter_removed_assets

    return sorted(filter_removed_assets(found))


def load_funding(asset: str, data_dir: Path | None = None) -> dict[str, np.ndarray] | None:
    """Settled funding history, if cached. Timestamps are when each rate was known."""
    data_dir = Path(data_dir) if data_dir else resolve_data_dir()
    path = data_dir / f"{asset.upper()}_funding_1h.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "timestamp" not in df or "funding_rate" not in df:
        return None
    df = df.dropna(subset=["timestamp", "funding_rate"])
    return {"ts": df["timestamp"].to_numpy(dtype="int64"), "rate": df["funding_rate"].to_numpy(dtype="float64")}


def aligned_reference(bars: pd.DataFrame, ref: pd.DataFrame | None) -> np.ndarray | None:
    """Reference closes on the asset's own timestamps; NaN where the reference has no bar."""
    if ref is None:
        return None
    s = pd.Series(ref["close"].to_numpy(dtype="float64"), index=ref["timestamp"].to_numpy(dtype="int64"))
    return s.reindex(bars["timestamp"].to_numpy(dtype="int64")).to_numpy(dtype="float64")


class PrecomputedTargets:
    """Engine Strategy that replays a target path computed from causal score series.

    `on_bar` reads only `targets[history.i]`, the decision made with bars <= i. The engine
    fills it at bar i+1's open (fill_delay=1). `scorecard`'s prefix-invariance tests are what
    guarantee targets[i] itself never used bar i+1.
    """

    def __init__(self, targets: np.ndarray, label: str = "compound") -> None:
        self.targets = np.asarray(targets, dtype="float64")
        self.name = label
        self.params: dict[str, Any] = {}

    def warmup_bars(self) -> int:
        return 0

    def on_bar(self, history: BarWindow) -> float:
        return float(self.targets[history.i])


# Hyperliquid perp max leverage per coin (research/results/top50-screen-2026-11-07.json). Hyperliquid's
# maintenance margin is half the initial margin at max leverage, so a 10x-max coin is liquidated
# at 5% of notional, not the 0.2% the engine's Jupiter default (max_lev_constant 500) assumes. At 5x
# that moves liquidation from about 19.7% away to about 15% away. A coin not listed here keeps the
# Jupiter default. Hyperliquid changes these caps; re-pull the screen when it does.
HYPERLIQUID_MAX_LEVERAGE: dict[str, float] = {
    "BTC": 40, "ETH": 25, "SOL": 20, "XRP": 20, "HYPE": 10,
    "DOGE": 10, "LINK": 10, "NEAR": 10, "SUI": 10, "AVAX": 10,
}


def maintenance_fraction(asset: str | None) -> float | None:
    """Hyperliquid maintenance margin as a fraction of notional, or None (engine default)."""
    max_lev = HYPERLIQUID_MAX_LEVERAGE.get((asset or "").upper())
    return None if max_lev is None else 1.0 / (2.0 * max_lev)


def engine_config(cfg: Mapping[str, Any], asset: str | None = None) -> EngineConfig:
    ex, agg = cfg["execution"], cfg["aggregate"]
    maint = maintenance_fraction(asset)
    extra = {} if maint is None else {"max_lev_constant": 1.0 / maint}
    costs = CostConfig(perp_base_fee_bps=ex["fee_bps"], slippage_bps=ex["slippage_bps"],
                       fee_bps=ex["fee_bps"], liquidation_forfeits_collateral=True, **extra)
    lev = float(ex["leverage"])
    # A perp position is held at a fixed size, not re-levered every 5m bar. With the engine's default
    # threshold of 0 every bar's drift counted as a trade (only:rsi on SOL: 68,200 "trades", 13,561 real
    # entries and exits). Re-lever only when exposure drifts 10% from target.
    return EngineConfig(mode=Mode.PERP, leverage=lev, interval="5m", allow_short=bool(agg["allow_short"]),
                        fill_delay=1, costs=costs, rebalance_threshold=0.1 * lev)


@dataclass
class _Slice:
    returns: np.ndarray
    trades: int
    wins: float
    fees: float
    borrow: float
    liquidations: int
    exposure_bars: float


def _run_slice(arrays: dict[str, np.ndarray], targets: np.ndarray, cfg: Mapping[str, Any],
               asset: str | None = None) -> _Slice | None:
    if arrays["close"].size < 3:
        return None
    res = run_backtest(PrecomputedTargets(targets), arrays, engine_config(cfg, asset))
    eq = res.equity
    # After a wipeout equity stays at 0 and the next returns are 0/0. _stitch drops those NaNs and
    # its cumulative product stays at 0, so a ruined run still reports -100%; only the warning goes.
    with np.errstate(divide="ignore", invalid="ignore"):
        rets = eq[1:] / eq[:-1] - 1.0
    m = res.metrics
    start = res.equity[0] if res.equity.size else 1.0
    return _Slice(rets, int(m.trade_count), float(m.win_rate or 0.0) * int(m.trade_count),
                  float(m.total_fees) / start, float(m.total_borrow_fees) / start,
                  int(res.liquidation_count), float(np.count_nonzero(res.exposure)))


def _stitch(slices: Sequence[_Slice | None]) -> dict[str, Any]:
    kept = [s for s in slices if s is not None]
    if not kept:
        return {"bars": 0, "trades": 0}
    r = np.concatenate([s.returns for s in kept])
    r = r[np.isfinite(r)]
    equity = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(np.concatenate(([1.0], equity)))[1:]
    dd = float((equity / peak - 1.0).min()) if equity.size else 0.0
    sd = float(r.std(ddof=0)) if r.size else 0.0
    trades = sum(s.trades for s in kept)
    return {
        "bars": int(r.size),
        "total_return": round(float(equity[-1] - 1.0), 6) if equity.size else 0.0,
        "sharpe": None if sd == 0 else round(float(r.mean() / sd * math.sqrt(BARS_PER_YEAR)), 3),
        "max_drawdown": round(dd, 6),
        "trades": trades,
        "win_rate": None if trades == 0 else round(sum(s.wins for s in kept) / trades, 4),
        "fees_pct": round(float(100.0 * sum(s.fees for s in kept)), 4),
        "borrow_pct": round(float(100.0 * sum(s.borrow for s in kept)), 4),
        "liquidations": sum(s.liquidations for s in kept),
        "time_in_market": round(sum(s.exposure_bars for s in kept) / max(1, r.size), 4),
    }


def _hash_frame(df: pd.DataFrame) -> str:
    # Include every OHLCV/quality column; wick and volume changes can alter
    # liquidations and signals even when every timestamp/close is unchanged.
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    columns += sorted(set(df.columns) - set(columns))
    h = hashlib.sha256()
    h.update(json.dumps(columns, separators=(",", ":")).encode())
    h.update(pd.util.hash_pandas_object(df[columns], index=False).to_numpy(dtype="<u8").tobytes())
    return h.hexdigest()



def _hash_auxiliary(value: Any) -> str:
    def encode(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"unsupported auxiliary input type: {type(item).__name__}")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=encode)
    return hashlib.sha256(canonical.encode()).hexdigest()

def prepare(asset: str, data_dir: Path | None = None, *, bars: pd.DataFrame | None = None,
            source: str = "") -> dict[str, Any]:
    """Load an asset's bars and auxiliary series once, for many configurations."""
    data_dir = Path(data_dir) if data_dir else resolve_data_dir()
    if bars is None:
        bars, source = load_bars_5m(asset, data_dir)
    ref = None
    if asset.upper() != "BTC":
        try:
            ref, _ = load_bars_5m("BTC", data_dir)
        except CompoundDataError:
            ref = None
    return {"asset": asset.upper(), "bars": bars, "source": source, "funding": load_funding(asset, data_dir),
            "btc": aligned_reference(bars, ref), "data_hash": _hash_frame(bars),
            "incomplete_pct": incomplete_pct(bars)}


def incomplete_pct(bars: pd.DataFrame, minutes: int = 5) -> float | None:
    """Percent of 5m bars built from fewer than five 1m candles; None for native 5m candles
    (which the venue corrupts the same way, but there is nothing to count)."""
    if "minutes" not in bars or not len(bars):
        return None
    return round(100.0 * float((bars["minutes"] < minutes).mean()), 3)


def run_compound(asset: str, config: Mapping[str, Any] | None = None, *, label: str = "compound",
                 data_dir: Path | None = None, oos_fraction: float = 0.3,
                 events: Sequence[Mapping[str, Any]] | None = None,
                 prepared: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate one configuration on one asset. Returns a JSON-ready report."""
    if not 0.0 < oos_fraction < 1.0:
        raise ValueError("oos_fraction must be between 0 and 1")
    cfg = sc.normalise_config(config)
    prep = prepared or prepare(asset, data_dir)
    df: pd.DataFrame = prep["bars"]
    ts_all = df["timestamp"].to_numpy(dtype="int64")
    split_ts = int(ts_all[int(len(ts_all) * (1.0 - oos_fraction))])
    arrays_all = {
        "ts": ts_all, "open": df["open"].to_numpy(dtype="float64"), "high": df["high"].to_numpy(dtype="float64"),
        "low": df["low"].to_numpy(dtype="float64"), "close": df["close"].to_numpy(dtype="float64"),
        "volume": df["volume"].to_numpy(dtype="float64"),
    }
    evals: list[sc.Evaluation] = []
    is_slices: list[_Slice | None] = []
    oos_slices: list[_Slice | None] = []
    segments = [s for s in sc.contiguous_segments(ts_all) if s[1] - s[0] >= MIN_SEGMENT_BARS]
    errors: dict[str, str] = {}
    for a, b in segments:
        seg = {k: v[a:b] for k, v in arrays_all.items()}
        aux: dict[str, Any] = {"events": list(events or [])}
        if maintenance_fraction(prep["asset"]) is not None:
            aux["maintenance_fraction"] = maintenance_fraction(prep["asset"])
        if prep.get("funding") is not None:
            aux["funding"] = prep["funding"]
        if prep.get("btc") is not None:
            aux["btc_close"] = prep["btc"][a:b]
        ev = sc.evaluate(sc.Bars.from_mapping(seg), cfg, aux)
        errors.update(ev.errors)
        evals.append(ev)
        targets = sc.target_path(ev)
        cut = int(np.searchsorted(seg["ts"], split_ts, side="left"))
        if cut > 0:
            is_slices.append(_run_slice({k: v[:cut] for k, v in seg.items()}, targets[:cut], cfg, prep["asset"]))
        if cut < b - a:
            oos_slices.append(_run_slice({k: v[cut:] for k, v in seg.items()}, targets[cut:], cfg, prep["asset"]))
    if not evals:
        raise CompoundDataError(f"{asset}: no contiguous run of {MIN_SEGMENT_BARS}+ bars")
    enabled = sorted(c for c, e in cfg["components"].items() if e["enabled"])
    auxiliary_hashes = {"funding": _hash_auxiliary(prep.get("funding")),
                        "btc_close": _hash_auxiliary(prep.get("btc")),
                        "events": _hash_auxiliary(list(events or []))}
    data_hash = _hash_frame(df)
    input_hash = _hash_auxiliary({"bars": data_hash, "source": prep.get("source", ""),
                                  "auxiliary": auxiliary_hashes})
    report = {
        "asset": prep["asset"], "label": label, "config_hash": sc.config_hash(cfg),
        "enabled": enabled, "source": prep.get("source", ""), "data_hash": data_hash,
        "input_hash": input_hash, "auxiliary_hashes": auxiliary_hashes,
        "from_ts": int(ts_all[0]), "to_ts": int(ts_all[-1]), "split_ts": split_ts,
        "segments": len(segments), "bars": int(len(ts_all)), "errors": errors,
        "data_incomplete_pct": prep.get("incomplete_pct"),
        "leverage": cfg["execution"]["leverage"],
        "is": {"forecast": sc.forecast_stats(evals, None, split_ts), "pnl": _stitch(is_slices)},
        "oos": {"forecast": sc.forecast_stats(evals, split_ts, None), "pnl": _stitch(oos_slices)},
    }
    # Buying and holding the coin over the same window, unlevered: a long-biased call that only
    # matches this has shown no skill, just the coin's drift.
    close = arrays_all["close"]
    cut_all = int(np.searchsorted(ts_all, split_ts, side="left"))
    report["is"]["buy_hold_return"] = round(float(close[cut_all - 1] / close[0] - 1.0), 6) if cut_all > 1 else None
    report["oos"]["buy_hold_return"] = round(float(close[-1] / close[cut_all] - 1.0), 6) if cut_all < close.size else None
    report["ranked"] = is_rankable(report)
    return report


def is_rankable(report: Mapping[str, Any]) -> bool:
    """The evidence floor: enough OOS calls and trades for a number to mean something."""
    oos = report.get("oos") or {}
    return (int((oos.get("forecast") or {}).get("calls", 0)) >= MIN_OOS_CALLS
            and int((oos.get("pnl") or {}).get("trades", 0)) >= MIN_OOS_TRADES)


# The frontier sweep's holding periods (5m bars: 1 h, 4 h, 24 h) and its entry quantile (top 2%).
FRONTIER_HOLDS = (12, 48, 288)
FRONTIER_QUANTILE = 0.98


def variants(cfg: Mapping[str, Any], *, standalone: bool = True, perturb: bool = False,
             aggregate_grid: bool = False, frontier: bool = False) -> list[tuple[str, dict[str, Any]]]:
    """(label, config) pairs: the compound itself, each enabled score component alone,
    one-at-a-time parameter perturbations, and aggregate-setting variations.

    Perturbations mirror the background queue's tiers (x0.75/x1.5, then x0.5/x2) and vary ONE
    number at a time; a joint grid explodes combinatorially. Every label is unique so the count
    printed is the true number of configurations tried (the multiple-testing denominator).
    """
    base = sc.normalise_config(cfg)
    out: list[tuple[str, dict[str, Any]]] = [("compound", base)]
    seen = {sc.config_hash(base)}

    def add(label: str, c: dict[str, Any]) -> None:
        try:
            c = sc.normalise_config(c)
        except sc.ScorecardError:
            return
        h = sc.config_hash(c)
        if h not in seen:
            seen.add(h)
            out.append((label, c))

    scores = [cid for cid, e in base["components"].items()
              if e["enabled"] and sc.BY_ID[cid].kind == "score" and not sc.BY_ID[cid].forward_only]
    if standalone:
        for cid in scores:
            add(f"only:{cid}", sc.standalone_config(base, cid))
    if perturb:
        for cid in scores:
            solo = sc.standalone_config(base, cid)
            for spec in sc.BY_ID[cid].params:
                for factor in (0.75, 1.5, 0.5, 2.0):
                    v = solo["components"][cid]["params"][spec.name] * factor
                    v = int(round(v)) if spec.kind == "int" else round(v, 6)
                    v = min(max(v, spec.lo), spec.hi)
                    c = sc.normalise_config(solo)
                    c["components"][cid]["params"][spec.name] = v
                    add(f"only:{cid} {spec.name}={v:g}", c)
    if frontier:
        # Every historical metric, enabled or not, alone: only its strongest 2% of readings (by its own
        # trailing record), held 1 h / 4 h / 24 h. One round trip then has to beat a bigger move,
        # which is the only way a 5m reading can pay a 13 bps toll (research/COMPOUND-FRONTIER.md).
        for comp in sc.COMPONENTS:
            if comp.kind != "score" or comp.forward_only:
                continue
            solo = sc.standalone_config(base, comp.id)
            for hold in FRONTIER_HOLDS:
                c = sc.normalise_config(solo)
                c["aggregate"].update(hold=hold, entry_quantile=FRONTIER_QUANTILE)
                # Unlevered: a 24 h hold at 5x is mostly volatility drag; 1x measures the edge itself.
                c["execution"]["leverage"] = 1.0
                add(f"frontier:{comp.id} hold={hold} top2% 1x", c)
    if aggregate_grid:
        gates = [c.id for c in sc.COMPONENTS if c.kind == "gate"]
        no_gates = sc.normalise_config(base)
        for g in gates:
            no_gates["components"][g]["enabled"] = False
        add("compound no-gates", no_gates)
        adaptive_on = sc.normalise_config(base)
        adaptive_on["aggregate"]["adaptive"] = 1 - int(base["aggregate"]["adaptive"])
        add(f"compound adaptive={adaptive_on['aggregate']['adaptive']}", adaptive_on)
        flipped = sc.normalise_config(base)
        flipped["aggregate"].update(adaptive=1, adaptive_flip=1)
        add("compound adaptive=1 flip=1", flipped)
        tuned = sc.normalise_config(base)
        tuned["aggregate"]["tune"] = 1 - int(base["aggregate"]["tune"])
        add(f"compound tune={tuned['aggregate']['tune']}", tuned)
        for key, value in (("regime_weighting", 0), ("dedupe_families", 0)):
            c = sc.normalise_config(base)
            c["aggregate"][key] = value
            add(f"compound {key}={value}", c)
        for entry in (0.15, 0.35, 0.5):
            c = sc.normalise_config(base)
            c["aggregate"]["entry"] = entry
            c["aggregate"]["exit"] = min(c["aggregate"]["exit"], entry)
            add(f"compound entry={entry:g}", c)
        for lev in (1.0, 20.0):
            c = sc.normalise_config(base)
            c["execution"]["leverage"] = lev
            add(f"compound leverage={lev:g}", c)
    return out


def leaderboard(rows: Sequence[Mapping[str, Any]], top: int = 20) -> list[Mapping[str, Any]]:
    """Ranked rows first (by OOS Sharpe), then unranked ones; never ranks on in-sample."""
    def key(r: Mapping[str, Any]) -> tuple[int, float]:
        sharpe = ((r.get("oos") or {}).get("pnl") or {}).get("sharpe")
        return (0 if r.get("ranked") else 1, -(sharpe if sharpe is not None else -1e9))
    return sorted(rows, key=key)[:top]
