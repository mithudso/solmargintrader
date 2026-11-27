"""Can the current strategies make 1% a day? A leveraged, cost-complete, offline backtest.

Run from the repository root (all flags optional; defaults are the owner's venues):

    python3 -m research.scripts.target_1pct_day
    python3 -m research.scripts.target_1pct_day --funding-bps-h 0.5 --out /tmp/t1pd

It reads the committed Coinbase 5m history in ``research/hype-suite/history`` (no network),
replays three things, each from a fresh account at several leverages:

* ``zec-volty`` - Volty(10 x 1.5) 5m stop-and-reverse on ZEC, the frozen rule behind the
  funded GUM owner (TASK-2660). GUM terms: 3.5 bps taker, 100 bps maintenance, 75 bps
  liquidation fee.
* ``hype-rsi`` - RSI(14) < 30 buy, > 55 exit, 1h, long or flat: the live HYPE forward test.
* ``*-hold`` - buy and hold ZEC, HYPE and BTC, the bar every strategy must clear.

Every account pays taker fees and slippage on each fill, a funding charge on held notional
every bar, and is liquidated when its marked equity reaches maintenance margin anywhere on
the bar's assumed path (open, nearer extreme, farther extreme, close). It is a research
model on trade candles, not venue marks; it never signs, sends or reads a wallet.

Why the windows matter: Volty(10 x 1.5) was *selected* on 2026-10-14..11-11 GUM data, so
only February to September (before selection) and after 11-18 are out of sample for it.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "research" / "hype-suite" / "history"
OUT = ROOT / "research" / "json" / "target-1pct-day"
STEP = 300


@dataclass(frozen=True)
class Costs:
    fee_bps: float = 3.5          # taker, per side
    slip_bps: float = 2.0         # per side, on top of the stop/market price
    funding_bps_h: float = 0.1    # paid on |notional| every hour held, whatever the side
    mmr: float = 0.01             # maintenance margin as a fraction of notional
    liq_fee: float = 0.0075       # charged on notional at liquidation


VENUES = {
    # GUM terms captured 2026-11-18 (research/papers/results/zec_gum_5m_10m_replay.md).
    "gum": Costs(),
    # Hyperliquid base tier: 4.5 bps taker, ~0.125 bps/h funding, ~3% maintenance on HYPE.
    "hyperliquid": Costs(fee_bps=4.5, funding_bps_h=0.125, mmr=0.03, liq_fee=0.0),
    # Coinbase spot for 1x holding references: 25 bps taker, no funding, never liquidated.
    "spot": Costs(fee_bps=25.0, slip_bps=2.0, funding_bps_h=0.0, mmr=0.0, liq_fee=0.0),
}


def load(coin: str, history: Path = HISTORY) -> tuple[pd.DataFrame, int]:
    """Contiguous 5m bars; a missing slot becomes a flat zero-volume bar at the last close."""
    with gzip.open(history / f"{coin}-USD_5m.csv.gz", "rt") as handle:
        frame = pd.read_csv(handle)
    frame = frame.set_index("unix").sort_index()
    full = np.arange(frame.index[0], frame.index[-1] + STEP, STEP)
    missing = len(full) - len(frame)
    frame = frame.reindex(full)
    close = frame["close"].ffill()
    for col in ("open", "high", "low"):
        frame[col] = frame[col].fillna(close)
    frame["close"], frame["volume"] = close, frame["volume"].fillna(0.0)
    frame.index.name = "unix"
    return frame[["open", "high", "low", "close", "volume"]], missing


def resample(frame: pd.DataFrame, seconds: int) -> pd.DataFrame:
    key = (frame.index // seconds) * seconds
    grouped = frame.groupby(key)
    return pd.DataFrame({"open": grouped["open"].first(), "high": grouped["high"].max(),
                         "low": grouped["low"].min(), "close": grouped["close"].last(),
                         "volume": grouped["volume"].sum()})


# ---- signals: every array at index i uses information through bar i-1 only -------------

def volty_levels(f: pd.DataFrame, length: int = 10, mult: float = 1.5):
    """Pine Volty Expan Close: stops at the previous close +- SMA(TR, length) x mult."""
    h, lo, c = (f[k].to_numpy() for k in ("high", "low", "close"))
    tr = np.maximum(h[1:] - lo[1:], np.maximum(abs(h[1:] - c[:-1]), abs(lo[1:] - c[:-1])))
    sums = np.r_[0.0, np.cumsum(tr)]
    width = np.full(len(c), np.nan)
    width[length:] = (sums[length:] - sums[:-length]) / length * mult
    return np.r_[np.nan, c[:-1] + width[:-1]], np.r_[np.nan, c[:-1] - width[:-1]]


def rsi_series(close: np.ndarray, period: int = 14) -> np.ndarray:
    delta = np.diff(close, prepend=close[0])
    gain = pd.Series(np.where(delta > 0, delta, 0.0)).ewm(alpha=1 / period, adjust=False).mean()
    loss = pd.Series(np.where(delta < 0, -delta, 0.0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out = (100 - 100 / (1 + rs)).fillna(100.0).to_numpy().copy()
    out[:period] = 50.0
    return out


def rsi_targets(f: pd.DataFrame, period=14, buy=30.0, sell=55.0) -> np.ndarray:
    """Target held from the open of bar i, decided on the close of bar i-1 (fill delay 1)."""
    r = rsi_series(f["close"].to_numpy(), period)
    target, held = np.zeros(len(r)), 0.0
    for i in range(1, len(r)):
        if held == 0 and r[i - 1] < buy:
            held = 1.0
        elif held == 1 and r[i - 1] > sell:
            held = 0.0
        target[i] = held
    return target


def ma_cross_targets(f: pd.DataFrame, fast: int = 20, slow: int = 50) -> np.ndarray:
    """Long while SMA(fast) > SMA(slow) of closes through the previous bar, else flat."""
    c = f["close"]
    on = (c.rolling(fast).mean() > c.rolling(slow).mean()).astype(float).to_numpy()
    return np.r_[0.0, on[:-1]]


# ---- the leveraged account ---------------------------------------------------------------

def simulate(f: pd.DataFrame, step: int, leverage: float, costs: Costs, *, start: int = 0,
             end: int | None = None, stops=None, targets=None, stop_loss: float = 0.0) -> dict:
    """Replay one fresh account. ``stops`` = (up, down) stop-and-reverse levels;
    ``targets`` = desired sign from each bar's open. ``stop_loss`` (fraction of entry, 0 = off)
    flattens a position; the next band crossing re-enters. Size = leverage x equity at entry."""
    o, h, lo, c = (f[k].to_numpy() for k in ("open", "high", "low", "close"))
    ts = f.index.to_numpy()
    end = len(c) if end is None else end
    fee, slip = costs.fee_bps / 1e4, costs.slip_bps / 1e4
    fund = costs.funding_bps_h / 1e4 * step / 3600
    cash, qty, entry = 1.0, 0.0, 0.0
    fees = funding = 0.0
    trades = liqs = 0
    eq = np.empty(end - start)
    dead = False

    def close_pos(raw: float):
        nonlocal cash, qty, fees, trades
        px = raw * (1 - np.sign(qty) * slip)
        paid = abs(qty) * px * fee
        cash += qty * (px - entry) - paid
        fees += paid
        trades += 1
        qty = 0.0

    def open_pos(direction: float, raw: float):
        nonlocal cash, qty, entry, fees
        if cash <= 1e-9:
            return
        px = raw * (1 + direction * slip)
        units = leverage * cash / (px * (1 + leverage * fee))
        paid = units * px * fee
        cash -= paid
        fees += paid
        qty, entry = direction * units, px

    def liq_price() -> float:
        if not qty or costs.mmr <= 0 and leverage <= 1:
            return math.nan
        a = abs(qty)
        if qty > 0:
            x = (a * entry - cash) / (a * (1 - costs.mmr))
            return x if x > 0 else math.nan
        return (cash + a * entry) / (a * (1 + costs.mmr))

    def liquidate(x: float):
        nonlocal cash, qty, liqs, fees
        a = abs(qty)
        penalty = a * x * costs.liq_fee
        cash = max(0.0, cash + qty * (x - entry) - penalty)
        fees += penalty
        qty, liqs = 0.0, liqs + 1

    up, dn = stops if stops is not None else (None, None)
    for i in range(start, end):
        if dead:
            eq[i - start] = 0.0
            continue
        if targets is not None and i > start and np.sign(targets[i]) != np.sign(qty):
            if qty:
                close_pos(o[i])
            if targets[i]:
                open_pos(np.sign(targets[i]), o[i])
        # Path: open, nearer extreme, farther extreme, close (TradingView's OHLC convention).
        first, second = (h[i], lo[i]) if h[i] - o[i] < o[i] - lo[i] else (lo[i], h[i])
        path = (o[i], first, second, c[i])
        fired = set()
        for a, b in pairwise(path):
            lo_seg, hi_seg = min(a, b), max(a, b)
            # Candidate events on this monotone segment, ordered along the direction of travel.
            while True:
                events = []
                lp = liq_price()
                toward = (qty > 0 and b <= a) or (qty < 0 and b >= a)
                if qty and math.isfinite(lp) and lo_seg <= lp <= hi_seg and toward:
                    events.append((abs(lp - a), "liq", lp))
                if qty and math.isfinite(lp) and ((qty > 0 and a <= lp) or (qty < 0 and a >= lp)):
                    events.append((0.0, "liq", a))       # gapped through the liquidation price
                if qty and stop_loss > 0:
                    sl = entry * (1 - stop_loss) if qty > 0 else entry * (1 + stop_loss)
                    adverse = (qty > 0 and b <= a) or (qty < 0 and b >= a)
                    if (qty > 0 and a <= sl) or (qty < 0 and a >= sl):
                        events.append((0.0, "sl", a))
                    elif adverse and lo_seg <= sl <= hi_seg:
                        events.append((abs(a - sl), "sl", sl))
                if stops is not None and i > 0 and math.isfinite(up[i]):
                    if "up" not in fired and qty <= 0 and hi_seg >= up[i] and b >= a:
                        events.append((max(0.0, up[i] - a), "up", max(a, up[i])))
                    if "dn" not in fired and qty >= 0 and lo_seg <= dn[i] and b <= a:
                        events.append((max(0.0, a - dn[i]), "dn", min(a, dn[i])))
                if not events:
                    break
                _, kind, px = min(events, key=lambda e: (e[0], e[1] != "liq"))
                if kind == "liq":
                    liquidate(px)
                    fired.update(("up", "dn"))  # no re-entry on the bar that liquidated
                elif kind == "sl":
                    close_pos(px)
                else:
                    fired.add(kind)
                    if qty:
                        close_pos(px)
                    open_pos(1.0 if kind == "up" else -1.0, px)
                a = px
                lo_seg, hi_seg = min(a, b), max(a, b)
        if qty:
            cost = abs(qty) * c[i] * fund
            cash -= cost
            funding += cost
        value = cash + qty * (c[i] - entry)
        if value <= 1e-9:
            dead, value = True, 0.0
        eq[i - start] = value
    return {"equity": eq, "timestamps": ts[start:end], "trades": trades, "liquidations": liqs,
            "fees": fees, "funding": funding, "ruined": dead or eq[-1] < 0.05}


# ---- metrics -----------------------------------------------------------------------------

def daily_returns(eq: np.ndarray, ts: np.ndarray) -> np.ndarray:
    """Close-to-close UTC-day returns of the account, starting from its 1.0 opening balance."""
    closes = pd.Series(eq, index=ts).groupby(ts // 86400).last().to_numpy()
    prev = np.r_[1.0, closes[:-1]]
    # Days after an account is wiped out have no return; they are dropped, not counted as -100%.
    alive = prev > 0
    return closes[alive] / prev[alive] - 1


def metrics(run: dict, target: float) -> dict:
    eq, ts = run["equity"], run["timestamps"]
    d = daily_returns(eq, ts)
    days = len(np.unique(ts // 86400))
    total = float(eq[-1] - 1)
    geo = (eq[-1]) ** (1 / days) - 1 if days and eq[-1] > 0 else -1.0
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    n = len(d)
    sd = float(np.std(d)) if n > 1 else 0.0
    down = d[d < 0]
    return {"days": days, "days_alive": n, "total_return": total, "geo_daily": float(geo),
            "mean_daily": float(np.mean(d)) if n else 0.0,
            "median_daily": float(np.median(d)) if n else 0.0,
            "share_days_ge_target": float(np.sum(d >= target) / days) if days else 0.0,
            "best_day": float(d.max()) if n else 0.0, "worst_day": float(d.min()) if n else 0.0,
            "max_drawdown": float(np.max(1 - np.divide(eq, peak, out=np.zeros_like(eq), where=peak > 0))),
            "sharpe": float(np.mean(d) / sd * math.sqrt(365)) if sd > 0 else 0.0,
            "sortino": float(np.mean(d) / np.std(down) * math.sqrt(365)) if len(down) > 1 and np.std(down) > 0 else 0.0,
            "trades": run["trades"], "liquidations": run["liquidations"],
            "fees_pct_start": run["fees"] * 100, "funding_pct_start": run["funding"] * 100,
            "ruined": bool(run["ruined"]), "hits_target": bool(geo >= target)}


def bootstrap(d: np.ndarray, target: float, paths: int, horizon: int = 365, block: int = 7,
              seed: int = 7) -> dict:
    """Moving-block bootstrap of daily returns: what a year drawn from this record looks like."""
    if len(d) < block * 2:
        return {}
    rng = np.random.default_rng(seed)
    nblocks = math.ceil(horizon / block)
    starts = rng.integers(0, len(d) - block + 1, size=(paths, nblocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :horizon]
    r = np.clip(d[idx], -1.0, None)
    curve = np.cumprod(1 + r, axis=1)
    peak = np.maximum.accumulate(np.maximum(curve, 1.0), axis=1)
    dd = np.max(1 - curve / peak, axis=1)
    final = curve[:, -1]
    goal = (1 + target) ** horizon
    return {"paths": paths, "horizon_days": horizon, "median_year_multiple": float(np.median(final)),
            "p05_year_multiple": float(np.quantile(final, 0.05)),
            "p95_year_multiple": float(np.quantile(final, 0.95)),
            "p_hit_target": float(np.mean(final >= goal)), "p_loss": float(np.mean(final < 1)),
            "p_drawdown_ge_50": float(np.mean(dd >= 0.5)), "p_ruin_90": float(np.mean(final <= 0.1))}


# ---- the study ---------------------------------------------------------------------------

def windows(ts: np.ndarray, named: dict[str, tuple[str, str]]) -> dict[str, tuple[int, int]]:
    out = {"full": (0, len(ts))}
    cut = int(len(ts) * 0.7)
    out["first-70%"], out["last-30%"] = (0, cut), (cut, len(ts))
    for name, (a, b) in named.items():
        lo = int(np.searchsorted(ts, pd.Timestamp(a, tz="UTC").timestamp()))
        hi = int(np.searchsorted(ts, pd.Timestamp(b, tz="UTC").timestamp()))
        if hi - lo > 288:
            out[name] = (lo, hi)
    return out


VOLTY_WINDOWS = {"oos-before-selection": ("2026-02-05", "2026-09-30"),
                 "selection-window": ("2026-10-14", "2026-11-11"),
                 "oos-after-selection": ("2026-11-18", "2026-11-27")}


def run(args) -> dict:
    zec, zec_gaps = load("ZEC", args.history)
    hype, hype_gaps = load("HYPE", args.history)
    btc, btc_gaps = load("BTC", args.history)
    hype_1h = resample(hype, 3600)
    zec_1h, zec_4h, zec_1d = resample(zec, 3600), resample(zec, 14400), resample(zec, 86400)
    hype_1d, btc_1d = resample(hype, 86400), resample(btc, 86400)
    levels = [float(x) for x in args.leverages.split(",")]
    gum = replace(VENUES["gum"], fee_bps=args.fee_bps, slip_bps=args.slip_bps,
                  funding_bps_h=args.funding_bps_h)
    hl = replace(VENUES["hyperliquid"], slip_bps=args.slip_bps,
                 funding_bps_h=args.funding_bps_h * 1.25)
    specs = [
        ("zec-volty", zec, STEP, gum, {"stops": volty_levels(zec)}, VOLTY_WINDOWS, levels),
        ("hype-rsi", hype_1h, 3600, hl, {"targets": rsi_targets(hype_1h)}, {}, [x for x in levels if x <= 5]),
        ("zec-volty-sl0.8", zec, STEP, gum, {"stops": volty_levels(zec), "stop_loss": 0.008},
         VOLTY_WINDOWS, levels),
        # Experiments, not current strategies: slower bars, maker fills, a daily trend filter.
        ("zec-volty-1h", zec_1h, 3600, gum, {"stops": volty_levels(zec_1h)}, VOLTY_WINDOWS, levels[:4]),
        ("zec-volty-4h", zec_4h, 14400, gum, {"stops": volty_levels(zec_4h)}, VOLTY_WINDOWS, levels[:4]),
        ("zec-volty-5m-maker", zec, STEP, replace(gum, fee_bps=0.5, slip_bps=0.0),
         {"stops": volty_levels(zec)}, VOLTY_WINDOWS, levels[:4]),
        ("zec-ma20/50-1d", zec_1d, 86400, gum, {"targets": ma_cross_targets(zec_1d)}, {}, [1, 2, 3]),
        ("hype-ma20/50-1d", hype_1d, 86400, hl, {"targets": ma_cross_targets(hype_1d)}, {}, [1, 2, 3]),
        ("btc-ma20/50-1d", btc_1d, 86400, gum, {"targets": ma_cross_targets(btc_1d)}, {}, [1, 2, 3]),
        ("zec-hold", zec, STEP, gum, {"targets": np.ones(len(zec))}, VOLTY_WINDOWS, [1, 2, 3]),
        ("hype-hold", hype_1h, 3600, hl, {"targets": np.ones(len(hype_1h))}, {}, [1, 2, 3]),
        ("btc-hold", btc, STEP, gum, {"targets": np.ones(len(btc))}, {}, [1, 2, 3, 5]),
    ]
    rows, mc = [], {}
    for name, frame, step, costs, kw, named, lev_list in specs:
        ts = frame.index.to_numpy()
        for wname, (a, b) in windows(ts, named).items():
            for lev in lev_list:
                result = simulate(frame, step, lev, costs, start=a, end=b, **kw)
                m = metrics(result, args.target)
                rows.append({"strategy": name, "window": wname, "leverage": lev,
                             "start": _iso(ts[a]), "end": _iso(ts[b - 1]), **m})
                if wname == "full":
                    d = daily_returns(result["equity"], result["timestamps"])
                    mc[f"{name}@{lev:g}x"] = bootstrap(d, args.target, args.mc_paths, seed=args.seed)
    # Unlevered spot holding, for the honest "do nothing clever" bar.
    for coin, frame in (("ZEC", zec), ("HYPE", hype), ("BTC", btc)):
        result = simulate(frame, STEP, 1, VENUES["spot"], targets=np.ones(len(frame)))
        ts = frame.index.to_numpy()
        rows.append({"strategy": f"{coin.lower()}-spot-hold", "window": "full", "leverage": 1.0,
                     "start": _iso(ts[0]), "end": _iso(ts[-1]), **metrics(result, args.target)})
    return {"generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_daily": args.target, "target_year_multiple": (1 + args.target) ** 365,
            "costs": {"gum": asdict(gum), "hyperliquid": asdict(hl), "spot": asdict(VENUES["spot"])},
            "inputs": {f"{k}-USD_5m.csv.gz": {"sha256": _sha(args.history / f"{k}-USD_5m.csv.gz"),
                                              "filled_missing_5m_slots": g}
                       for k, g in (("ZEC", zec_gaps), ("HYPE", hype_gaps), ("BTC", btc_gaps))},
            "rows": rows, "bootstrap": mc}


def _iso(t) -> str:
    return datetime.fromtimestamp(int(t), UTC).strftime("%Y-%m-%d %H:%M")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(res: dict) -> str:
    pct = lambda x: f"{x * 100:+.2f}%"
    lines = [f"# 1%/day target check ({res['generated_at']})", "",
             (f"Target: {res['target_daily'] * 100:.2f}% a day compounded = "
              f"{res['target_year_multiple']:.1f}x a year."), "",
             "| Strategy | Window | Lev | Days | Geo/day | Median/day | Days >= target | Total | Max DD | Sharpe | Trades | Liq | Fees % | Funding % |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in res["rows"]:
        lines.append(f"| {r['strategy']} | {r['window']} | {r['leverage']:g}x | {r['days']} | {pct(r['geo_daily'])} | "
                     f"{pct(r['median_daily'])} | {r['share_days_ge_target'] * 100:.0f}% | {pct(r['total_return'])} | "
                     f"{r['max_drawdown'] * 100:.1f}% | {r['sharpe']:.2f} | {r['trades']} | {r['liquidations']} | "
                     f"{r['fees_pct_start']:.1f} | {r['funding_pct_start']:.1f} |")
    lines += ["", "## One-year block bootstrap of the full-period daily returns", "",
              "| Account | Median year | 5th pct | 95th pct | P(hit 1%/day) | P(loss) | P(DD >= 50%) | P(lose 90%) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for k, b in res["bootstrap"].items():
        if b:
            lines.append(f"| {k} | {b['median_year_multiple']:.2f}x | {b['p05_year_multiple']:.2f}x | "
                         f"{b['p95_year_multiple']:.2f}x | {b['p_hit_target'] * 100:.1f}% | {b['p_loss'] * 100:.0f}% | "
                         f"{b['p_drawdown_ge_50'] * 100:.0f}% | {b['p_ruin_90'] * 100:.0f}% |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--history", type=Path, default=HISTORY, help="dir with <COIN>-USD_5m.csv.gz")
    p.add_argument("--out", type=Path, default=OUT, help="output dir (results.json, report.md)")
    p.add_argument("--target", type=float, default=0.01, help="daily target, 0.01 = 1%%")
    p.add_argument("--leverages", default="1,2,3,5,10,25")
    p.add_argument("--fee-bps", type=float, default=3.5, help="GUM taker fee per side")
    p.add_argument("--slip-bps", type=float, default=2.0, help="slippage per side")
    p.add_argument("--funding-bps-h", type=float, default=0.1, help="GUM funding paid per hour on notional")
    p.add_argument("--mc-paths", type=int, default=4000)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args(argv)
    res = run(args)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.out / "report.md").write_text(report(res))
    print(report(res))
    print(f"wrote {args.out / 'results.json'} and {args.out / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
