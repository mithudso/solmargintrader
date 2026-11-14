"""Reliable-trigger miner: which conjunctions of conditions predict direction, and how well.

    python3 -m research.triggers --asset SOL --interval 1d
    python3 -m research.triggers --asset SOL --interval 1h
    python3 -m research.triggers --asset SOL --interval 1d --backtest

Simulation and research only: no network, no keys, no orders.

A TRIGGER is a conjunction (depth 1 to 3) of conditions, each computed from data up
to and including bar t. When it fires at the close of bar t, the trade is entered
at the OPEN of bar t+1 and judged at the CLOSE of bar t+h, h in (1, 2, 3, 5, 10).
That is exactly what `trigger_trade` does, so a mined edge and a backtested edge
are the same measurement.

Honesty gates (a trigger is "reliable" only if it passes ALL of them OUT OF SAMPLE):

  1. Discovery period only: exact one-sided binomial p against the BASE RATE for
     the same horizon and period, Benjamini-Hochberg FDR q=0.05 over EVERY
     hypothesis tested, and a Harvey-Liu-Zhu style |z| > 3.
  2. At least 30 de-duplicated events (non-overlapping windows) in each period.
  3. A fixed validation period AFTER the split, never used to choose anything:
     same direction, BH q=0.05 across the discovery survivors, and the Wilson 95%
     lower bound of the hit rate above the validation base rate.
  4. Stability: the hit rate beats the base rate in at least 75% of the calendar
     years (quarters for hourly) holding 8 or more events.
  5. Cross-asset replication on the other coins' DAILY data (at least 3 coins
     with 15+ events, 60% beating their base rate). Hourly triggers cannot be
     replicated (no hourly history for other coins) so they cannot qualify.

Events whose forward window crosses the split are dropped from discovery (purge)
and the validation period starts one maximum horizon after it (embargo).
The number of hypotheses is counted exactly and printed.
"""

from __future__ import annotations

import argparse
import itertools
import warnings
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT = REPO / "research" / "results"
HORIZONS = (1, 2, 3, 5, 10)
H_MAX = max(HORIZONS)
MIN_EVENTS = 30
FDR_Q = 0.05
HLZ_Z = 3.0
DISCOVERY_FRACTION = 0.60
STABILITY_MIN_EVENTS = 8
STABILITY_SHARE = 0.75
REPL_MIN_ASSETS = 3
REPL_MIN_EVENTS = 15
REPL_SHARE = 0.60
REPLICATION_ASSETS = ("BTC", "ETH", "BNB", "DOGE", "HYPE", "XRP", "ZEC")
MAX_DEPTH = 3
DEFAULT_MAX_COMBOS = 80_000

from backtester.core.trigger_conditions import (  # noqa: E402
    BASE_CONDITIONS, FUNDING_CONDITIONS, GROUPS, compute_conditions,
)

# --------------------------------------------------------------------------
# Forward outcomes: enter at open[t+1], judged at close[t+h]
# --------------------------------------------------------------------------

@dataclass
class Forward:
    ret: dict[int, np.ndarray]      # h -> long return open[t+1] -> close[t+h]; NaN if unavailable
    adverse_long: dict[int, np.ndarray]    # min low[t+1..t+h]/entry - 1
    favour_long: dict[int, np.ndarray]     # max high[t+1..t+h]/entry - 1
    path: np.ndarray                # (n, H_MAX) cum long return close[t+k]/open[t+1]-1


def forward_outcomes(ts, o, h, l, c, step: int) -> Forward:
    warnings.filterwarnings("ignore", message="All-NaN slice")
    n = len(c)
    entry = np.full(n, np.nan); entry[:-1] = o[1:]
    path = np.full((n, H_MAX), np.nan)
    lows = np.full((n, H_MAX), np.nan); highs = np.full((n, H_MAX), np.nan)
    for k in range(1, H_MAX + 1):
        ok = np.zeros(n, bool); ok[: n - k] = (ts[k:] - ts[: n - k]) == k * step
        # a window must be contiguous in time from t to t+k, or it spans a data gap
        if k + 1 < n:
            exit_ok = (ts[k + 1:] - ts[:n-k-1]) == (k + 1) * step
            path[:n-k-1, k - 1] = np.where(exit_ok & ok[:n-k-1], o[k + 1:] / entry[:n-k-1] - 1.0, np.nan)
        lows[: n - k, k - 1] = np.where(ok[: n - k], l[k:] / entry[: n - k] - 1.0, np.nan)
        highs[: n - k, k - 1] = np.where(ok[: n - k], h[k:] / entry[: n - k] - 1.0, np.nan)
    # bar t+1 itself must also be contiguous: ok at k=1 already; path[:,k-1] needs every step valid
    valid = np.isfinite(path).cumprod(axis=1).astype(bool)
    path = np.where(valid, path, np.nan)
    lows = np.where(valid, lows, np.nan); highs = np.where(valid, highs, np.nan)
    ret, adv, fav = {}, {}, {}
    for hh in HORIZONS:
        ret[hh] = path[:, hh - 1]
        adv[hh] = np.nanmin(lows[:, :hh], axis=1) if hh else None
        fav[hh] = np.nanmax(highs[:, :hh], axis=1)
        adv[hh] = np.where(np.isfinite(ret[hh]), adv[hh], np.nan)
        fav[hh] = np.where(np.isfinite(ret[hh]), fav[hh], np.nan)
    return Forward(ret, adv, fav, path)


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------

def binom_sf(k: int, n: int, p: float) -> float:
    """Exact P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if n <= 0 or k > n:
        return 0.0 if k > n else 1.0
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    lg = math.lgamma
    terms = [lg(n + 1) - lg(i + 1) - lg(n - i + 1) + i * lp + (n - i) * lq for i in range(k, n + 1)]
    m = max(terms)
    return min(1.0, math.exp(m) * sum(math.exp(t - m) for t in terms))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def zscore(k: int, n: int, p0: float) -> float:
    if n == 0 or p0 <= 0 or p0 >= 1:
        return float("nan")
    return (k / n - p0) / math.sqrt(p0 * (1 - p0) / n)


def bh_reject(pvals: np.ndarray, q: float = FDR_Q) -> np.ndarray:
    """Benjamini-Hochberg step-up: boolean mask of rejected hypotheses."""
    m = len(pvals)
    if m == 0:
        return np.zeros(0, bool)
    order = np.argsort(pvals)
    thresh = q * (np.arange(1, m + 1) / m)
    below = pvals[order] <= thresh
    out = np.zeros(m, bool)
    if below.any():
        out[order[: np.max(np.nonzero(below)[0]) + 1]] = True
    return out


def dedup(idx: np.ndarray, h: int) -> np.ndarray:
    """Keep events at least h bars apart so overlapping windows count once."""
    keep, last = [], -10**9
    for i in idx:
        if i - last >= h:
            keep.append(i); last = i
    return np.asarray(keep, dtype=int)


# --------------------------------------------------------------------------
# Mining
# --------------------------------------------------------------------------

@dataclass
class Dataset:
    asset: str
    interval: str
    ts: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    funding: np.ndarray | None
    step: int
    cond: dict = field(default_factory=dict)
    fwd: Forward | None = None


def load_funding(asset: str, ts: np.ndarray, interval: str, data_dir: Path) -> np.ndarray | None:
    path = data_dir / f"{asset}_funding_1h.csv"
    if not path.exists():
        return None
    f = pd.read_csv(path).sort_values("timestamp")
    ft, fr = f["timestamp"].to_numpy("int64"), f["funding_rate"].to_numpy(float)
    if (len(ft) == 0 or not np.isfinite(fr).all() or f.timestamp.duplicated().any()
            or np.any(ft % 3600)):
        return np.full(len(ts), np.nan)
    step = 86400 if interval == "1d" else 3600
    if interval == "1d":
        # funding settled inside day t is known by its close
        out = np.zeros(len(ts)); hit = np.zeros(len(ts), bool)
        for p, timestamp, r in zip(np.searchsorted(ts, ft, side="right") - 1, ft, fr):
            if 0 <= p < len(ts) and ts[p] <= timestamp < ts[p] + step:
                out[p] += r; hit[p] = True
        out[~hit] = np.nan
        out = pd.Series(out).ffill().to_numpy()
        return out
    idx = np.searchsorted(ft, ts, side="right") - 1
    out = np.where(idx >= 0, fr[np.clip(idx, 0, None)], np.nan)
    return out


def load_dataset(asset: str, interval: str, data_dir: Path | None = None, with_funding: bool = True) -> Dataset:
    from research.sweep import data_dir as _dd
    data_dir = data_dir or _dd()
    df = pd.read_csv(data_dir / f"{asset}_{interval}.csv").sort_values("timestamp").drop_duplicates("timestamp")
    ts = df["timestamp"].to_numpy("int64")
    step = 86400 if interval == "1d" else 3600
    fund = load_funding(asset, ts, interval, data_dir) if with_funding else None
    ds = Dataset(asset, interval, ts, *(df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume")), fund, step)
    ds.cond = compute_conditions(ds.o, ds.h, ds.l, ds.c, ds.v, ds.funding)
    ds.fwd = forward_outcomes(ts, ds.o, ds.h, ds.l, ds.c, step)
    return ds


def split_index(ds: Dataset) -> int:
    return int(len(ds.ts) * DISCOVERY_FRACTION)


def period_masks(n: int, split: int):
    """Event-bar masks. Discovery events must finish before the split (purge); validation starts H_MAX later (embargo)."""
    disc = np.zeros(n, bool); disc[: split - H_MAX] = True
    val = np.zeros(n, bool); val[split + H_MAX:] = True
    return disc, val


def stats_for(ds: Dataset, event_idx: np.ndarray, h: int, direction: int, period: np.ndarray):
    """Hit rate etc. for a set of event bars, direction +1 long / -1 short."""
    fw = ds.fwd
    ok = period & np.isfinite(fw.ret[h])
    base_mask = ok
    r_all = fw.ret[h][base_mask]
    base = float(np.mean(np.sign(r_all) == direction)) if r_all.size else float("nan")
    ev = dedup(event_idx[ok[event_idx]], h)
    n = len(ev)
    if n == 0:
        return dict(n=0, hits=0, hit=float("nan"), base=base, p=1.0, z=float("nan"), lo=float("nan"), hi=float("nan"),
                    mean=float("nan"), median=float("nan"), mae_med=float("nan"), mae_p10=float("nan"),
                    mfe_med=float("nan"), events=ev)
    r = direction * fw.ret[h][ev]
    hits = int(np.sum(r > 0))
    adv = fw.adverse_long[h][ev] if direction == 1 else -fw.favour_long[h][ev]
    fav = fw.favour_long[h][ev] if direction == 1 else -fw.adverse_long[h][ev]
    lo, hi = wilson(hits, n)
    return dict(n=n, hits=hits, hit=hits / n, base=base, p=binom_sf(hits, n, base), z=zscore(hits, n, base),
                lo=lo, hi=hi, mean=float(np.mean(r)), median=float(np.median(r)),
                mae_med=float(np.median(adv)), mae_p10=float(np.percentile(adv, 10)),
                mfe_med=float(np.median(fav)), events=ev)


def profile(ds: Dataset, ev: np.ndarray, direction: int) -> list[float]:
    p = direction * ds.fwd.path[ev]
    p = p[np.isfinite(p).all(axis=1)]
    return [float(x) for x in np.mean(p, axis=0)] if len(p) else []


def enumerate_conjunctions(ds: Dataset, disc_mask: np.ndarray, max_combos: int):
    """Apriori-pruned conjunctions of depth 1..3 with >= MIN_EVENTS raw discovery events."""
    names = [k for k in BASE_CONDITIONS if k in ds.cond]
    cnt = {k: int((ds.cond[k] & disc_mask).sum()) for k in names}
    singles = [k for k in names if cnt[k] >= MIN_EVENTS]
    combos = [(k,) for k in singles]
    pair_ok = {}
    for a, b in itertools.combinations(singles, 2):
        if GROUPS[a] == GROUPS[b]:
            continue
        m = int((ds.cond[a] & ds.cond[b] & disc_mask).sum())
        if m >= MIN_EVENTS:
            pair_ok[(a, b)] = True
            combos.append((a, b))
    seen_masks = {}
    pruned_depth3 = 0
    for a, b, c in itertools.combinations(singles, 3):
        if len({GROUPS[a], GROUPS[b], GROUPS[c]}) < 3:
            continue
        if not (pair_ok.get((a, b)) and pair_ok.get((a, c)) and pair_ok.get((b, c))):
            pruned_depth3 += 1
            continue
        if int((ds.cond[a] & ds.cond[b] & ds.cond[c] & disc_mask).sum()) >= MIN_EVENTS:
            combos.append((a, b, c))
        if len(combos) >= max_combos:
            break
    # identical event sets restate one hypothesis: keep the simplest
    unique, dup = [], 0
    for combo in sorted(combos, key=len):
        m = ds.cond[combo[0]].copy()
        for k in combo[1:]:
            m &= ds.cond[k]
        key = (m & disc_mask).tobytes()
        if key in seen_masks:
            dup += 1
            continue
        seen_masks[key] = combo
        unique.append(combo)
    return unique, dict(singles=len(singles), duplicates_removed=dup, depth3_pruned_by_pairs=pruned_depth3,
                        capped=len(combos) >= max_combos)


def conj_mask(cond: dict, combo) -> np.ndarray:
    m = cond[combo[0]].copy()
    for k in combo[1:]:
        m &= cond[k]
    return m


def stability(ds: Dataset, ev: np.ndarray, h: int, direction: int):
    """Share of calendar years (quarters for 1h) with >= 8 events whose hit rate beats that year's base rate."""
    if ds.interval == "1d":
        key = pd.to_datetime(ds.ts, unit="s").year.to_numpy()
    else:
        d = pd.to_datetime(ds.ts, unit="s")
        key = (d.year * 10 + d.quarter).to_numpy()
    r = ds.fwd.ret[h]
    good = tot = 0
    detail = {}
    for g in np.unique(key[ev]) if len(ev) else []:
        e = ev[key[ev] == g]
        if len(e) < STABILITY_MIN_EVENTS:
            continue
        allr = r[(key == g) & np.isfinite(r)]
        base = float(np.mean(np.sign(allr) == direction)) if allr.size else float("nan")
        hit = float(np.mean(direction * r[e] > 0))
        tot += 1; good += int(hit > base)
        detail[int(g)] = round(hit, 3)
    return (good / tot if tot else float("nan")), tot, detail


def mine(asset: str, interval: str, max_combos: int = DEFAULT_MAX_COMBOS, data_dir: Path | None = None,
         near_miss_k: int = 300):
    ds = load_dataset(asset, interval, data_dir)
    n = len(ds.ts)
    split = split_index(ds)
    disc, val = period_masks(n, split)
    combos, prune = enumerate_conjunctions(ds, disc, max_combos)

    rows = []
    n_tested = 0
    for combo in combos:
        m = conj_mask(ds.cond, combo)
        idx_all = np.nonzero(m)[0]
        for h in HORIZONS:
            for direction in (1, -1):
                n_tested += 1
                s = stats_for(ds, idx_all, h, direction, disc)
                rows.append((combo, h, direction, s))
    p_all = np.array([r[3]["p"] if r[3]["n"] >= MIN_EVENTS else 1.0 for r in rows])
    reject = bh_reject(p_all)

    # Strict survivors (BH + HLZ) are the only route to "reliable". The best
    # NEAR_MISS_K by discovery p-value are evaluated out of sample as well so the
    # report can show near-misses, but they carry disc_bh_hlz=False and can never
    # qualify.
    strict = [i for i, ((combo, h, d, s), rej) in enumerate(zip(rows, reject))
              if rej and s["n"] >= MIN_EVENTS and s["hit"] > s["base"] and s["z"] > HLZ_Z]
    rest = sorted((i for i, (_, _, _, s) in enumerate(rows)
                   if s["n"] >= MIN_EVENTS and s["hit"] > s["base"] and i not in set(strict)),
                  key=lambda i: rows[i][3]["p"])[:near_miss_k]
    strict_set = set(strict)
    cands = [(rows[i][0], rows[i][1], rows[i][2], rows[i][3]) for i in strict + rest]
    cand_strict = [i in strict_set for i in strict + rest]

    # validation, fixed split, only for discovery survivors
    vrows = []
    for combo, h, direction, s in cands:
        idx_all = np.nonzero(conj_mask(ds.cond, combo))[0]
        v = stats_for(ds, idx_all, h, direction, val)
        vrows.append(v)
    pv = np.array([v["p"] if v["n"] >= MIN_EVENTS else 1.0 for v in vrows])
    vrej = bh_reject(pv)

    others = {}
    if interval == "1d":
        for a in REPLICATION_ASSETS:
            if a.upper() == asset.upper():
                continue
            try:
                others[a] = load_dataset(a, "1d", data_dir, with_funding=a in ("BTC", "ETH"))
            except FileNotFoundError:
                continue

    out = []
    for (combo, h, direction, s), v, vr, is_strict in zip(cands, vrows, vrej, cand_strict):
        idx_all = np.nonzero(conj_mask(ds.cond, combo))[0]
        ev_full = dedup(idx_all[np.isfinite(ds.fwd.ret[h])[idx_all]], h)
        stab, stab_n, stab_detail = stability(ds, ev_full, h, direction)
        # replication
        rep_n = rep_good = 0
        rep_detail = {}
        for a, od in others.items():
            if any(k not in od.cond for k in combo):
                continue
            st = stats_for(od, np.nonzero(conj_mask(od.cond, combo))[0], h, direction, np.ones(len(od.ts), bool))
            if st["n"] >= REPL_MIN_EVENTS:
                rep_n += 1; rep_good += int(st["hit"] > st["base"])
                rep_detail[a] = round(st["hit"] - st["base"], 3)
        rep_ok = rep_n >= REPL_MIN_ASSETS and rep_good / rep_n >= REPL_SHARE
        win = direction * ds.fwd.ret[h][s["events"]] > 0
        stop = float(-np.percentile(np.where(direction == 1, ds.fwd.adverse_long[h][s["events"]],
                                             -ds.fwd.favour_long[h][s["events"]])[win], 20)) if win.any() else float("nan")
        gates = {
            "disc_bh_hlz": is_strict,
            "oos_n30": v["n"] >= MIN_EVENTS,
            "oos_direction": bool(v["n"] and v["hit"] > v["base"]),
            "oos_bh": bool(vr),
            "oos_wilson_above_base": bool(v["n"] and v["lo"] > v["base"]),
            "stable": bool(stab == stab and stab >= STABILITY_SHARE and stab_n >= 2),
            "replicates": bool(rep_ok) if interval == "1d" else False,
        }
        out.append({
            "conditions": "&".join(combo), "depth": len(combo), "direction": "long" if direction == 1 else "short",
            "horizon": h,
            "is_n": s["n"], "is_hit": s["hit"], "is_base": s["base"], "is_p": s["p"], "is_z": s["z"],
            "is_ci_lo": s["lo"], "is_ci_hi": s["hi"], "is_mean_ret": s["mean"], "is_median_ret": s["median"],
            "oos_n": v["n"], "oos_hit": v["hit"], "oos_base": v["base"], "oos_p": v["p"],
            "oos_ci_lo": v["lo"], "oos_ci_hi": v["hi"], "oos_mean_ret": v["mean"], "oos_median_ret": v["median"],
            "oos_mae_median": v["mae_med"], "oos_mae_p10": v["mae_p10"], "oos_mfe_median": v["mfe_med"],
            "decay_hit": (v["hit"] - s["hit"]) if v["n"] else float("nan"),
            "stop_frac": stop, "stable_share": stab, "stable_periods": stab_n,
            "stable_detail": json.dumps(stab_detail), "repl_assets": rep_n, "repl_beating": rep_good,
            "repl_detail": json.dumps(rep_detail),
            "path_is": json.dumps([round(x, 4) for x in profile(ds, s["events"], direction)]),
            "path_oos": json.dumps([round(x, 4) for x in profile(ds, v["events"], direction)]) if v["n"] else "[]",
            "reliable": all(gates.values()), "failed_gates": ",".join(k for k, ok in gates.items() if not ok),
            "uses_funding": any(k in FUNDING_CONDITIONS for k in combo),
        })
    columns = ("conditions", "depth", "direction", "horizon", "is_n", "is_hit", "is_base", "is_p", "is_z", "is_ci_lo", "is_ci_hi", "is_mean_ret", "is_median_ret", "oos_n", "oos_hit", "oos_base", "oos_p", "oos_ci_lo", "oos_ci_hi", "oos_mean_ret", "oos_median_ret", "oos_mae_median", "oos_mae_p10", "oos_mfe_median", "decay_hit", "stop_frac", "stable_share", "stable_periods", "stable_detail", "repl_assets", "repl_beating", "repl_detail", "path_is", "path_oos", "reliable", "failed_gates", "uses_funding")
    df = pd.DataFrame(out, columns=columns)
    meta = {
        "asset": asset, "interval": interval, "bars": n,
        "first_bar_utc": str(pd.Timestamp(ds.ts[0], unit="s")), "last_bar_utc": str(pd.Timestamp(ds.ts[-1], unit="s")),
        "discovery_start": str(pd.Timestamp(ds.ts[0], unit="s")),
        "discovery_events_end": str(pd.Timestamp(ds.ts[split - H_MAX - 1], unit="s")),
        "split_utc": str(pd.Timestamp(ds.ts[split], unit="s")),
        "validation_events_start": str(pd.Timestamp(ds.ts[split + H_MAX], unit="s")),
        "validation_end": str(pd.Timestamp(ds.ts[-1], unit="s")),
        "conditions": len([k for k in BASE_CONDITIONS if k in ds.cond]),
        "conjunctions_tested": len(combos), "hypotheses_tested": n_tested,
        "horizons": list(HORIZONS), "directions": 2, "min_events": MIN_EVENTS, "fdr_q": FDR_Q, "hlz_z": HLZ_Z,
        "bh_discovery_survivors": len(strict), "near_miss_candidates": len(rest), "depth_counts": {str(d): sum(1 for c in combos if len(c) == d) for d in (1, 2, 3)}, "reliable": int(df["reliable"].sum()) if len(df) else 0,
        "replication_assets": sorted(others), "pruning": prune,
        "funding_available": ds.funding is not None,
    }
    return df, meta, ds


def near_misses(df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    """Discovery survivors that did not qualify but were directionally right out of sample."""
    if df.empty:
        return df
    nm = df[(~df["reliable"]) & (df["oos_n"] >= 10) & (df["oos_hit"] > df["oos_base"])].copy()
    nm["edge"] = nm["oos_hit"] - nm["oos_base"]
    nm["n_failed"] = nm["failed_gates"].str.count(",") + 1
    return nm.sort_values(["n_failed", "oos_p"], ascending=[True, True]).head(limit)


def write_results(df: pd.DataFrame, meta: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"triggers_{meta['asset'].lower()}_{meta['interval']}"
    df.to_csv(OUT / f"{stem}.csv", index=False)
    (OUT / f"{stem}.json").write_text(json.dumps(meta, indent=2))
    return OUT / f"{stem}.csv"


GATES = ("disc_bh_hlz", "oos_n30", "oos_direction", "oos_bh", "oos_wilson_above_base", "stable", "replicates")
GATE_TEXT = {
    "disc_bh_hlz": "discovery: BH FDR 5% and z > 3",
    "oos_n30": "validation: at least 30 de-duplicated events",
    "oos_direction": "validation: hit rate above the validation base rate",
    "oos_bh": "validation: BH FDR 5% across the survivors",
    "oos_wilson_above_base": "validation: Wilson 95% lower bound above the base rate",
    "stable": "hit rate beats base in 75% of years (quarters for 1h)",
    "replicates": "cross-asset replication on other coins' daily data",
}


def _pct(x) -> str:
    return "n/a" if x != x else f"{100 * x:.1f}%"


def _row(r) -> str:
    return (f"| `{r.conditions}` | {r.direction} | {r.horizon} | {_pct(r.is_hit)} | "
            f"{_pct(r.oos_hit)} ({_pct(r.oos_ci_lo)} to {_pct(r.oos_ci_hi)}) | {_pct(r.oos_base)} | "
            f"{int(r.oos_n)} | {100 * r.decay_hit:+.1f} pt | {r.failed_gates or 'none'} |")


def build_report() -> Path:
    """Compose research/RELIABLE_SIGNALS.md from the result files that exist."""
    parts = ["""# Reliable signals: which triggers hold up out of sample

Generated by `python3 -m research.triggers` (`build_report`). Simulation only. Not investment advice.

A **trigger** is a conjunction of 1 to 3 conditions, each computed from bars up to and including bar t.
When it fires at the close of bar t the trade enters at the open of bar t+1 and is judged at the close
of bar t+h (h = 1, 2, 3, 5, 10). The **hit rate** is the share of de-duplicated, non-overlapping events
that moved in the predicted direction. It is compared with the **base rate**: how often any bar of the same
period moved that way. A trigger is listed as reliable only if it passes every gate **out of sample**.

Gates: (1) discovery period only, exact one-sided binomial p vs the base rate, Benjamini-Hochberg FDR 5%
over every hypothesis tested, and z > 3 (Harvey-Liu-Zhu); (2) at least 30 de-duplicated events in each
period; (3) a fixed later validation period with the same direction, BH FDR 5% across the survivors, and
a Wilson 95% lower bound above the validation base rate; (4) the hit rate beats the base rate in 75% of
calendar years (quarters for hourly) with 8 or more events; (5) replication on the other coins' daily data
(3 or more coins with 15 or more events, 60% beating their base rate). Discovery events whose forward window
crosses the split are purged and validation starts 10 bars after it. Prior work this respects:
Stele KNOW-632 (every spec strategy looked good in sample and lost out of sample), KNOW-561 and KNOW-596
(PBO 0.700, in-sample rank is anti-informative), KNOW-617 (purge/embargo, HLZ t > 3, cost on fill).
"""]
    for interval in ("1d", "1h"):
        jp, cp = OUT / f"triggers_sol_{interval}.json", OUT / f"triggers_sol_{interval}.csv"
        if not (jp.exists() and cp.exists()):
            continue
        m = json.loads(jp.read_text()); df = pd.read_csv(cp)
        parts.append(f"\n## SOL {interval}\n")
        parts.append(f"- Bars: {m['bars']:,}, {m['first_bar_utc'][:10]} to {m['last_bar_utc'][:10]}.")
        parts.append(f"- Discovery events: {m['discovery_start'][:10]} to {m['discovery_events_end'][:10]}. "
                     f"Validation events: {m['validation_events_start'][:10]} to {m['validation_end'][:10]} "
                     f"(split {m['split_utc'][:10]}).")
        parts.append(f"- Conditions: {m['conditions']}. Conjunctions with 30 or more raw discovery events: "
                     f"{m['conjunctions_tested']} (depth 1: {m['depth_counts']['1']}, depth 2: {m['depth_counts']['2']}, "
                     f"depth 3: {m['depth_counts']['3']}).")
        parts.append(f"- **Hypotheses tested: {m['hypotheses_tested']:,}** "
                     f"({m['conjunctions_tested']} conjunctions x 5 horizons x 2 directions).")
        parts.append(f"- Survived discovery (BH 5% and z > 3): **{m['bh_discovery_survivors']}**. "
                     f"Reliable out of sample: **{m['reliable']}**.")
        if interval == "1h":
            parts.append("- Hourly triggers cannot qualify: the other coins have no hourly history, so the replication gate "
                         "cannot be run. They are reported as near-misses at best.")
        if m["reliable"] == 0:
            parts.append("\n**No trigger qualified as reliable.** Nothing on this page should be traded as a reliable signal.")
        rel = df[df["reliable"]]
        if len(rel):
            parts.append("\n### Reliable (all gates passed out of sample)\n")
            parts.append("| Conditions | Direction | h | In-sample hit | Out-of-sample hit (95% CI) | OOS base rate | n | Decay | Failed gates |\n|---|---|---|---|---|---|---|---|---|")
            parts += [_row(r) for r in rel.sort_values("oos_p").head(15).itertuples()]
        parts.append("\n### Gate funnel\n")
        parts.append("| Gate | Passed |\n|---|---|")
        for g in GATES:
            ok = int((~df["failed_gates"].fillna("").str.split(",").apply(lambda x: g in x)).sum()) if len(df) else 0
            parts.append(f"| {GATE_TEXT[g]} | {ok} of {len(df)} evaluated |")
        nm = near_misses(df, 15)
        if len(nm):
            parts.append("\n### Near-misses (NOT reliable; exploratory)\n")
            parts.append("Ranked by gates failed, then validation p-value. These were chosen after seeing the validation "
                         "period, so their out-of-sample numbers are optimistic.\n")
            parts.append("| Conditions | Direction | h | In-sample hit | Out-of-sample hit (95% CI) | OOS base rate | n | Decay | Failed gates |\n|---|---|---|---|---|---|---|---|---|")
            parts += [_row(r) for r in nm.itertuples()]
    bp = OUT / "trigger_backtest_sol_1d.csv"
    if bp.exists():
        b = pd.read_csv(bp)
        label = b["label"].iloc[0].upper()
        parts.append(f"\n## Trigger strategy backtest ({label})\n")
        parts.append("`trigger_trade` run on the validation period only, with fees, slippage, borrow carry and liquidation "
                     "(PR 1 tiers). Near-misses here are ranked by discovery p-value, not by validation results. "
                     "Return is the compounded validation-block return; CPCV = 4 validation blocks, 6 paths.\n")
        parts.append("| Conditions | Dir | h | Tier | Trades | Return | Sharpe | Liq | CPCV median Sharpe | CPCV paths > 0 |\n|---|---|---|---|---|---|---|---|---|---|")
        for r in b.itertuples():
            parts.append(f"| `{r.conditions}` | {r.direction} | {r.horizon} | {r.tier} | {r.oos_trades} | {_pct(r.oos_return)} | "
                         f"{r.oos_sharpe:.2f} | {r.oos_liquidations} | {r.cpcv_median_sharpe:.2f} | {_pct(r.cpcv_pct_positive)} |")
    parts.append("""
## Reading this honestly

- Out-of-sample hit rates near the base rate are what noise looks like. A 55% hit rate on 40 events has a 95% interval of about 40% to 70%.
- Fees and carry cost about 16 bps round trip before slippage on a 1 to 3 day hold; a trigger must move farther than that on average, not just more often.
- Replication assets share one market regime, so replication is weaker evidence than it sounds.
- The conditions are classic indicators. Their predictive content, if any, is small and unstable on this asset and window, which matches Stele KNOW-632.
""")
    path = REPO / "research" / "RELIABLE_SIGNALS.md"
    path.write_text("\n".join(parts))
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--asset", default="SOL")
    ap.add_argument("--interval", default="1d", choices=("1d", "1h"))
    ap.add_argument("--max-combos", type=int, default=DEFAULT_MAX_COMBOS)
    ap.add_argument("--backtest", action="store_true", help="also run the trigger strategy through the leverage tiers")
    a = ap.parse_args(argv)
    df, meta, ds = mine(a.asset.upper(), a.interval, a.max_combos)
    path = write_results(df, meta)
    print(f"{meta['asset']} {meta['interval']}: {meta['hypotheses_tested']} hypotheses "
          f"({meta['conjunctions_tested']} conjunctions x {len(HORIZONS)} horizons x 2 directions), "
          f"{meta['bh_discovery_survivors']} survived discovery, {meta['reliable']} reliable out of sample")
    print(f"discovery {meta['discovery_start']} .. {meta['discovery_events_end']}; "
          f"validation {meta['validation_events_start']} .. {meta['validation_end']}")
    nm = near_misses(df)
    if len(nm):
        print(nm[["conditions", "direction", "horizon", "is_hit", "oos_hit", "oos_base", "oos_n", "failed_gates"]].round(3).to_string(index=False))
    print(f"wrote {path}")
    if a.backtest:
        from research import trigger_backtest
        trigger_backtest.run(a.asset.upper(), a.interval, df, meta)
    print(f"wrote {build_report()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
