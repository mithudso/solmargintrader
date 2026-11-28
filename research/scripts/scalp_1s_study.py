"""Which 1s-bar indicators say anything about the next 30 seconds?

Reads recorded Jupiter Pyth oracle ticks (the price the 1000x product settles
against), builds one-second bars, computes every candidate in
``research.scalp_1s_features`` and scores each against the sign and size of the
return over the following 30 seconds. One parameter set per indicator family is
chosen on the first 60% of the base recording, the composite is fitted there,
and everything is then read on data it never saw: the later 20% + 20% of the
same recording and a separate live recording made on another day.

Nothing here places, signs or simulates an order. The 1000x payout table at the
end uses the saved frontend arithmetic in ``oracle_leverage.exit50`` to show
what a correct or wrong 30 second call is worth after the product's fees.

    python -m research.scalp_1s_study --base <dual-quotes dir> --live <ticks.jsonl> --out <dir>
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from oracle_leverage.exit50 import quote_position
from research import scalp_1s_experiments as X
from research import scalp_1s_features as F

HORIZON = 30
ENTRY_DELAY = (
    2  # seconds between a decision and the recorded fill, per the product docs
)
MAX_LOOKBACK = 120  # the extension warms up from live ticks only; keep that wait short
SPLIT = (0.6, 0.8)
# Seconds ahead at which the average move after a call is measured, for the chart's most-likely line.
PATH_STEPS = (5, 10, 15, 20, 25, 30)
# The extension grid. Every tile votes +1, -1 or 0 with the sign of its feature
# ("follow": a rising reading votes up). The set was fixed after reading the
# base recording: one parameter set per family, at most 90 s of warm-up, kept
# only when following its sign was right more than half the time on both the
# train and the validation slice. The separate live recording played no part.
TILES = (
    ("impulse", "roc_2", "Impulse 2s"),
    ("momentum5", "roc_5", "Momentum 5s"),
    ("momentum60", "roc_60", "Momentum 60s"),
    ("breakout20", "brk_20", "Breakout 20s"),
    ("breakout60", "brk_60", "Breakout 60s"),
    ("heikin", "ha", "Heikin-Ashi run"),
    ("bop", "bop_5", "Balance of power"),
    ("zigzag", "zzdir_1", "ZigZag leg"),
    ("donchian", "don_60", "Range position"),
    ("efficiency", "er_60", "Efficiency"),
    ("slope", "slope_60", "Slope 60s"),
    ("rsi", "rsi_7", "RSI 7"),
    ("zscore", "z_20", "Z-score 20"),
    ("macd", "macdh_1", "MACD hist"),
    ("psar", "psar", "Parabolic SAR"),
    ("supertrend", "super_10", "Supertrend"),
)
TILE_WARMUP = 90
# Net votes out of len(TILES): below LEAN the grid is mixed, from STRONG on it is one-sided.
LEAN, STRONG = 6, 12


def read_base(directory: Path) -> dict:
    """Jupiter oracle rows from the hourly dual-quote captures, per asset."""
    out: dict[str, list] = {}
    for path in sorted(directory.glob("dual-quotes-*.jsonl.gz")):
        try:
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                for line in stream:
                    if '"venue":"jupiter"' not in line:
                        continue
                    row = json.loads(line)
                    out.setdefault(row["asset"], []).append(
                        (float(row["exchange_at"]), float(row["price"]))
                    )
        except (EOFError, OSError):
            # An hour file cut short by a recorder restart keeps the rows already read.
            continue
    return {a: _dedupe(rows) for a, rows in out.items()}


def input_receipt(base: Path, live: Path | None) -> dict:
    """Names, sizes and hashes of the tick files read, so a rerun can prove it saw the same data."""
    files = sorted(base.glob("dual-quotes-*.jsonl.gz"))
    listing = hashlib.sha256()
    for path in files:
        listing.update(
            f"{path.name}:{path.stat().st_size}:{hashlib.sha256(path.read_bytes()).hexdigest()}\n".encode()
        )
    out = {
        "base_files": len(files),
        "base_bytes": sum(path.stat().st_size for path in files),
        "base_listing_sha256": listing.hexdigest(),
    }
    if live:
        raw = (
            gzip.decompress(live.read_bytes())
            if live.suffix == ".gz"
            else live.read_bytes()
        )
        out.update(
            {
                "live_file": live.name,
                "live_rows": raw.count(b"\n"),
                "live_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return out


def read_live(path: Path) -> dict:
    out: dict[str, list] = {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # the recorder may still be appending the last line
            out.setdefault(row["a"], []).append((row["e"] / 1000.0, float(row["p"])))
    return {a: _dedupe(rows) for a, rows in out.items()}


def _dedupe(rows):
    rows.sort(key=lambda r: r[0])
    t = np.array([r[0] for r in rows])
    p = np.array([r[1] for r in rows])
    keep = np.r_[True, np.diff(t) > 0]
    return t[keep], p[keep]


def frames(ticks) -> list:
    """One dict per contiguous segment: features, forward return and path extremes."""
    result = []
    t, p = ticks
    for seg in F.second_bars(t, p):
        n = seg["close"].size
        if n < 600:
            continue
        feats = F.feature_table(seg)
        c = seg["close"]
        fwd = np.full(n, np.nan)
        fwd[: n - HORIZON] = (c[HORIZON:] / c[:-HORIZON] - 1.0) * 1e4
        # Move to each intermediate step, kept as pseudo-features so the same split and masks apply.
        for step in PATH_STEPS:
            ahead = np.full(n, np.nan)
            ahead[: n - step] = (c[step:] / c[:-step] - 1.0) * 1e4
            feats[f"ahead_{step}"] = ahead
        result.append(
            {
                "time": seg["time"],
                "open": seg["open"],
                "close": c,
                "high": seg["high"],
                "low": seg["low"],
                "fwd": fwd,
                "features": feats,
                "filled": seg["filled"],
            }
        )
    return result


def stack(frame_list, names, lo=0.0, hi=1.0, span=None):
    """Rows whose time falls in the [lo, hi) share of ``span`` (first, last second)."""
    xs, ys, ts = [], [], []
    for fr in frame_list:
        t = fr["time"]
        if span is None:
            mask = np.ones(t.size, dtype=bool)
        else:
            a = span[0] + lo * (span[1] - span[0])
            b = span[0] + hi * (span[1] - span[0])
            # Keep the label window inside the split so no test bar's outcome is seen in training.
            mask = (t >= a) & (t + HORIZON < b)
        x = (
            np.column_stack([fr["features"][nm] for nm in names])
            if names
            else np.empty((t.size, 0))
        )
        ok = mask & np.isfinite(fr["fwd"]) & np.all(np.isfinite(x), axis=1)
        xs.append(x[ok])
        ys.append(fr["fwd"][ok])
        ts.append(t[ok])
    if not xs:
        return np.empty((0, len(names))), np.empty(0), np.empty(0, dtype=np.int64)
    return np.vstack(xs), np.concatenate(ys), np.concatenate(ts)


def score(x, y) -> dict:
    """Directional reading of one feature against the next-30s return.

    Bars overlap, so the standard error uses n / HORIZON independent samples.
    """
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = int(x.size)
    if n < 2000 or np.std(x) == 0:
        return {"n": n}
    ic = float(np.corrcoef(x, y)[0, 1])
    v = F.vote(x)
    active = (v != 0) & (y != 0)
    agree = v[active] == np.sign(y[active])
    n_eff = max(1.0, active.sum() / HORIZON)
    hit = float(agree.mean()) if active.any() else float("nan")
    signed = v * y
    return {
        "n": n,
        "ic": ic,
        "ic_t": ic * math.sqrt(max(1.0, n / HORIZON - 2)),
        "coverage": float(active.mean()),
        "hit_follow": hit,
        "hit_se": math.sqrt(0.25 / n_eff),
        "mean_follow_bps": float(signed[v != 0].mean())
        if (v != 0).any()
        else float("nan"),
        "mean_abs_fwd_bps": float(np.abs(y).mean()),
    }


def payout_pct(move_bps: float, leverage: int = 1000) -> float:
    """Net result of a closed 1000x position, % of collateral, for a favourable (+) or adverse (-) move."""
    margin = 10_000_000
    entry = 100_000_000_000_000
    mark = entry + round(entry * move_bps / 1e4)
    q = quote_position(margin, margin * leverage, entry, mark, "LONG")
    return (q["payout"] - margin) / margin * 100.0


def write_fixture(
    path: Path,
    frame,
    names,
    digest: str,
    model: dict,
    experiments: dict,
    bars: int = 720,
    start: int = 5000,
) -> None:
    """Real 1s bars and the tile readings computed on exactly that window, for the JS port."""
    cols = {k: frame[k][start : start + bars] for k in ("time", "high", "low", "close")}
    opens = frame["open"][start : start + bars]
    seg = {**cols, "open": opens}
    feats = F.feature_table(seg)
    rows = [
        [
            int(seg["time"][i]),
            float(opens[i]),
            float(seg["high"][i]),
            float(seg["low"][i]),
            float(seg["close"][i]),
        ]
        for i in range(bars)
    ]
    ladder = [f"{kind}_{w}" for w in F.SLOPE_WINDOWS for kind in ("lsl", "acc")]
    expected = {
        nm: [None if not math.isfinite(v) else float(v) for v in feats[nm][-120:]]
        for nm in [*names, "rv_30", *ladder]
    }
    net = [
        None
        if not all(math.isfinite(feats[nm][i]) for nm in names)
        else int(sum(F.vote(feats[nm][i : i + 1])[0] for nm in names))
        for i in range(bars - 120, bars)
    ]
    payout = {
        str(m): payout_pct(m) for m in (-12, -9.8, -5, -1, 0, 0.2, 1, 3, 10, 50, 400)
    }
    # The same window as one frame, scored by the experiment module, with the priors the extension ships.
    window = {**seg, "fwd": np.full(bars, np.nan)}
    X.variant_votes([window])
    call_at = experiments["horizons"].index(experiments["call_horizon_s"])
    shipped = {
        variant["id"]: variant["prior"][call_at]
        if variant["prior"][call_at] is not None
        else 0.5
        for variant in experiments["variants"]
    }
    rule = X.rule_fixture(
        window,
        shipped,
        [slot["variant"] for slot in experiments["slots"]],
        experiments["call_horizon_s"],
    )
    variant_votes = {
        variant["id"]: [
            int(v) if math.isfinite(v) else None
            for v in F.vote(F.variant_values(seg, variant))[-40:]
        ]
        for variant in F.VARIANTS
    }
    runs = {
        str(w): [[sign, length] for sign, length in F.sign_runs(feats[f"lsl_{w}"])]
        for w in F.SLOPE_WINDOWS
    }
    ranges = {
        str(w): {
            kind: [
                float(np.nanmin(feats[f"{kind}_{w}"])),
                float(np.nanmax(feats[f"{kind}_{w}"])),
            ]
            for kind in ("lsl", "acc")
        }
        for w in F.SLOPE_WINDOWS
    }
    path.write_text(
        json.dumps(
            {
                "source": "research.scalp_1s_study",
                "model_sha256": digest,
                "model": model,
                "bars": rows,
                "tail": 120,
                "expected": expected,
                "net": net,
                "payout_pct": payout,
                "slope_runs": runs,
                "variant_votes": variant_votes,
                "rule": rule,
                "slope_ranges": ranges,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--live", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, help="write the JS parity fixture here")
    parser.add_argument(
        "--js", type=Path, help="write the extension's model constants here"
    )
    parser.add_argument(
        "--experiments-js",
        type=Path,
        help="write the extension's experiment grid and recorded priors here",
    )
    parser.add_argument(
        "--extra-live",
        type=Path,
        action="append",
        help="further live recordings, scored for the streak and fade studies only",
    )
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    base = {a: frames(t) for a, t in read_base(args.base).items()}
    live = {a: frames(t) for a, t in read_live(args.live).items()} if args.live else {}
    all_base = [fr for frs in base.values() for fr in frs]
    X.variant_votes(all_base)
    X.variant_votes([fr for frs in live.values() for fr in frs])
    span = (
        min(fr["time"][0] for fr in all_base),
        max(fr["time"][-1] for fr in all_base),
    )
    names = sorted(all_base[0]["features"])
    directional = [n for n in names if not n.startswith(("rv_", "ahead_"))]

    def lookback(name):
        tail = [int(p) for p in name.split("_")[1:] if p.isdigit()]
        if name.startswith("macdh_"):
            return 26 * tail[0] * F.EMA_WARMUP_SPANS
        if name.startswith(("emax_", "kelt_")):
            return max(tail) * F.EMA_WARMUP_SPANS
        if name == "ribbon":
            return 40 * F.EMA_WARMUP_SPANS
        if name.startswith("twobar_"):
            return 3 * tail[0]
        return max(tail) if tail and not name.startswith("zz") else 0

    table = {}
    for nm in directional:
        row = {"lookback_s": lookback(nm)}
        for part, (lo, hi) in (
            ("train", (0.0, SPLIT[0])),
            ("valid", (SPLIT[0], SPLIT[1])),
            ("test", (SPLIT[1], 1.0)),
        ):
            x, y, _ = stack(all_base, [nm], lo, hi, span)
            row[part] = score(x[:, 0], y)
        if live:
            x, y, _ = stack([fr for frs in live.values() for fr in frs], [nm])
            row["live"] = score(x[:, 0], y)
        table[nm] = row

    # Evidence per family, for the write-up: best member by mean train/valid hit rate.
    chosen = []
    for family, prefix in F.FAMILIES.items():
        members = [
            n
            for n in directional
            if (n == prefix or n.startswith(prefix))
            and table[n]["lookback_s"] <= TILE_WARMUP
            and "hit_follow" in table[n]["train"]
            and "hit_follow" in table[n]["valid"]
        ]
        if not members:
            continue
        best = max(
            members,
            key=lambda n: (
                table[n]["train"]["hit_follow"] + table[n]["valid"]["hit_follow"]
            ),
        )
        chosen.append(
            {
                "family": family,
                "feature": best,
                "train_hit": table[best]["train"]["hit_follow"],
                "valid_hit": table[best]["valid"]["hit_follow"],
                "kept": table[best]["train"]["hit_follow"] > 0.5
                and table[best]["valid"]["hit_follow"] > 0.5,
            }
        )
    grid_names = [t[1] for t in TILES]
    for _, nm, _ in TILES:
        if not (
            table[nm]["train"]["hit_follow"] > 0.5
            and table[nm]["valid"]["hit_follow"] > 0.5
        ):
            raise SystemExit(
                f"tile {nm} no longer meets the train/valid rule; revise TILES"
            )

    live_frames = [fr for frs in live.values() for fr in frs]
    slices = {
        "train": (all_base, 0.0, SPLIT[0], span),
        "valid": (all_base, SPLIT[0], SPLIT[1], span),
        "test": (all_base, SPLIT[1], 1.0, span),
    }
    for asset, frs in base.items():
        slices[f"base_{asset}"] = (frs, 0.0, 1.0, span)
    if live_frames:
        slices["live_all"] = (live_frames, 0.0, 1.0, None)
        for asset, frs in live.items():
            if frs:
                slices[f"live_{asset}"] = (frs, 0.0, 1.0, None)

    def net_of(frame_list, lo, hi, sp):
        x, y, _ = stack(frame_list, grid_names + ["rv_30"], lo, hi, sp)
        return F.vote(x[:, : len(grid_names)]).sum(axis=1), y, x[:, -1]

    def tier_stats(net, y, floor, ceil=None):
        mask = (np.abs(net) >= floor) & (y != 0)
        if ceil is not None:
            mask &= np.abs(net) < ceil
        n = int(mask.sum())
        if n < 300:
            return {"n": n}
        right = np.sign(net[mask]) == np.sign(y[mask])
        return {
            "n": n,
            "share": float(mask.mean()),
            "hit": float(right.mean()),
            "hit_se": math.sqrt(0.25 / max(1.0, n / HORIZON)),
            "mean_follow_bps": float((np.sign(net[mask]) * y[mask]).mean()),
        }

    vote_eval = {}
    for label, (frs, lo, hi, sp) in slices.items():
        net, y, _ = net_of(frs, lo, hi, sp)
        if y.size < 2000:
            vote_eval[label] = {"n": int(y.size)}
            continue
        vote_eval[label] = {
            "n": int(y.size),
            "base_up": float((y > 0).mean()),
            "mean_abs_fwd_bps": float(np.abs(y).mean()),
            "any": tier_stats(net, y, 1),
            "mixed": tier_stats(net, y, 1, LEAN),
            "lean": tier_stats(net, y, LEAN, STRONG),
            "strong": tier_stats(net, y, STRONG),
            "by_net": {
                str(k): tier_stats(net, y, k, k + 2)
                for k in range(2, len(TILES) + 1, 2)
            },
        }
        if "brk_60" in grid_names:
            x, yy, _ = stack(frs, ["brk_60"], lo, hi, sp)
            vote_eval[label]["breakout60"] = tier_stats(x[:, 0], yy, 1)

    def vote_trades(frame_list, floor):
        """Observed-path result of following the vote at 1000x, one decision per 30 s."""
        out = {}
        for label, fixed in (
            ("vote", None),
            ("always_long", 1.0),
            ("always_short", -1.0),
        ):
            res = []
            for fr in frame_list:
                x = np.column_stack([fr["features"][nm] for nm in grid_names])
                c, hi, lo = fr["close"], fr["high"], fr["low"]
                net = F.vote(x).sum(axis=1)
                for i in range(0, c.size - HORIZON - 2 * ENTRY_DELAY - 1, HORIZON):
                    if not np.all(np.isfinite(x[i])):
                        continue
                    if fixed is None and abs(net[i]) < floor:
                        continue
                    side = fixed if fixed is not None else float(np.sign(net[i]))
                    a, b = i + ENTRY_DELAY, i + 2 * ENTRY_DELAY + HORIZON
                    entry = c[a]
                    worst = (
                        (lo[a + 1 : b + 1].min() / entry - 1) * 1e4
                        if side > 0
                        else -(hi[a + 1 : b + 1].max() / entry - 1) * 1e4
                    )
                    final = side * (c[b] / entry - 1) * 1e4
                    res.append(
                        -100.0 if payout_pct(worst) <= -100.0 else payout_pct(final)
                    )
            if res:
                arr = np.array(res)
                out[label] = {
                    "trades": int(arr.size),
                    "mean_pct_of_collateral": float(arr.mean()),
                    "median_pct": float(np.median(arr)),
                    "win_rate": float((arr > 0).mean()),
                    "liquidated": float((arr <= -100.0).mean()),
                    "se": float(arr.std(ddof=1) / math.sqrt(arr.size))
                    if arr.size > 1
                    else float("nan"),
                }
        return out

    cut = span[0] + SPLIT[1] * (span[1] - span[0])
    test_frames = []
    for fr in all_base:
        m = fr["time"] >= cut
        if m.sum() > 600:
            test_frames.append(
                {
                    k: (
                        v[m]
                        if isinstance(v, np.ndarray)
                        else {kk: vv[m] for kk, vv in v.items()}
                    )
                    for k, v in fr.items()
                }
            )
    trades = {
        "test_any": vote_trades(test_frames, 1),
        "test_strong": vote_trades(test_frames, STRONG),
    }
    if live_frames:
        trades["live_any"] = vote_trades(live_frames, 1)
        trades["live_strong"] = vote_trades(live_frames, STRONG)

    # The extension recomputes path-dependent tiles (SAR, Supertrend, ZigZag, Heikin-Ashi,
    # RSI, MACD) on a rolling window; measure how often a 600 s window gives the same vote.
    longest = max(all_base, key=lambda fr: fr["close"].size)
    agree, total = 0, 0
    for end in range(3000, min(longest["close"].size, 40_000), 997):
        seg = {
            k: longest[k][end - 600 : end]
            for k in ("time", "open", "close", "high", "low")
        }
        window = F.feature_table(seg)
        for nm in grid_names:
            total += 1
            agree += int(
                F.vote(window[nm][-1:])[0]
                == F.vote(longest["features"][nm][end - 1 : end])[0]
            )
    window_agreement = agree / total if total else float("nan")

    # 30 s cone: realized |move| against sqrt(30) x the 30 s sigma of 1 s returns.
    cone = {}
    for win in (30, 120):
        x, y, _ = stack(all_base, [f"rv_{win}"], 0.0, SPLIT[1], span)
        pred = x[:, 0] * math.sqrt(HORIZON)
        ok = pred > 0
        ratio = np.abs(y[ok]) / pred[ok]
        cone[f"rv_{win}"] = {
            "p50": float(np.median(ratio)),
            "p68": float(np.quantile(ratio, 0.68)),
            "p90": float(np.quantile(ratio, 0.90)),
            "p95": float(np.quantile(ratio, 0.95)),
        }
    cone_check = {}
    for label in ("test", "live_all"):
        if label in slices:
            frs, lo, hi, sp = slices[label]
            x, y, _ = stack(frs, ["rv_30"], lo, hi, sp)
            pred = x[:, 0] * math.sqrt(HORIZON)
            ok = pred > 0
            if ok.sum() > 2000:
                ratio = np.abs(y[ok]) / pred[ok]
                cone_check[label] = {
                    "inside_p68": float((ratio <= cone["rv_30"]["p68"]).mean()),
                    "inside_p90": float((ratio <= cone["rv_30"]["p90"]).mean()),
                }

    payout = {
        str(m): round(payout_pct(m), 3)
        for m in (
            -10,
            -8,
            -5,
            -3,
            -2,
            -1,
            -0.5,
            0,
            0.5,
            1,
            2,
            3,
            5,
            8,
            10,
            15,
            20,
            30,
            50,
        )
    }
    breakeven = {}
    for m in (1, 2, 3, 5, 8, 10):
        win, loss = payout_pct(m), payout_pct(-m)
        breakeven[str(m)] = None if win <= 0 else round(-loss / (win - loss), 4)

    moves = {}
    for asset, frs in {
        **{f"base_{a}": f for a, f in base.items()},
        **{f"live_{a}": f for a, f in live.items()},
    }.items():
        y = (
            np.concatenate([fr["fwd"][np.isfinite(fr["fwd"])] for fr in frs])
            if frs
            else np.empty(0)
        )
        if y.size:
            moves[asset] = {
                "seconds": int(sum(fr["close"].size for fr in frs)),
                "median_abs_bps": float(np.median(np.abs(y))),
                "p90_abs_bps": float(np.quantile(np.abs(y), 0.9)),
                "sd_bps": float(y.std()),
            }

    # Slope ladder: for each window, does the slope's sign, the sign of its change, or the
    # two together say anything about the next 30 s? "accelerating" = both signs agree.
    def ladder_stats(frame_list, lo, hi, sp, w):
        x, y, _ = stack(frame_list, [f"lsl_{w}", f"acc_{w}"], lo, hi, sp)
        if y.size < 2000:
            return {"n": int(y.size)}
        sl, ac = F.vote(x[:, 0]), F.vote(x[:, 1])

        def follow(call, mask):
            m = mask & (call != 0) & (y != 0)
            n = int(m.sum())
            if n < 300:
                return {"n": n}
            return {
                "n": n,
                "share": float(m.mean()),
                "hit": float((call[m] == np.sign(y[m])).mean()),
                "hit_se": math.sqrt(0.25 / max(1.0, n / HORIZON)),
                "mean_follow_bps": float((call[m] * y[m]).mean()),
            }

        every = np.ones(y.size, dtype=bool)
        return {
            "n": int(y.size),
            "slope": follow(sl, every),
            "change": follow(ac, every),
            "accelerating": follow(sl, sl == ac),
            "fading": follow(sl, sl == -ac),
        }

    ladder_eval = {
        label: {str(w): ladder_stats(frs, lo, hi, sp, w) for w in F.SLOPE_WINDOWS}
        for label, (frs, lo, hi, sp) in slices.items()
    }

    def pooled_ladder(w, key):
        rows = [
            ladder_eval[k][str(w)][key]
            for k in ("train", "valid", "test")
            if "hit" in ladder_eval[k][str(w)].get(key, {})
        ]
        n = sum(r["n"] for r in rows)
        return (
            {
                "hit": sum(r["hit"] * r["n"] for r in rows) / n,
                "mean_follow_bps": sum(r["mean_follow_bps"] * r["n"] for r in rows) / n,
            }
            if n
            else None
        )

    # Reversal timing: how long a window's slope keeps one sign before it flips,
    # and the range its slope and second derivative moved in. Whole runs only.
    def run_stats(lengths):
        if not lengths:
            return {"count": 0}
        a = np.array(lengths, dtype=np.float64)
        return {
            "count": int(a.size),
            "mean_s": float(a.mean()),
            "median_s": float(np.median(a)),
            "p90_s": float(np.quantile(a, 0.9)),
            "max_s": float(a.max()),
        }

    def ladder_runs(frame_list, w):
        up, down = [], []
        for fr in frame_list:
            for sign, length in F.sign_runs(fr["features"][f"lsl_{w}"]):
                (up if sign > 0 else down).append(length)
        return {
            "all": run_stats(up + down),
            "up": run_stats(up),
            "down": run_stats(down),
        }

    def ladder_range(frame_list, w):
        out = {}
        for key, name in (("slope", f"lsl_{w}"), ("change", f"acc_{w}")):
            v = np.concatenate(
                [
                    fr["features"][name][np.isfinite(fr["features"][name])]
                    for fr in frame_list
                ]
            )
            out[key] = {
                "min": float(v.min()),
                "p1": float(np.quantile(v, 0.01)),
                "p99": float(np.quantile(v, 0.99)),
                "max": float(v.max()),
            }
        return out

    ladder_history = {
        label: {
            str(w): {"runs": ladder_runs(frs, w), "range_bps": ladder_range(frs, w)}
            for w in F.SLOPE_WINDOWS
        }
        for label, frs in {
            **{f"base_{a}": f for a, f in base.items()},
            **{f"live_{a}": f for a, f in live.items() if f},
        }.items()
    }
    ladder_model = [
        {
            "window_s": w,
            **{
                key: pooled_ladder(w, key)
                for key in ("slope", "change", "accelerating", "fading")
            },
            "runs": ladder_runs(all_base, w)["all"],
        }
        for w in F.SLOPE_WINDOWS
    ]

    # Swing reading of the same data: fade a close more than two standard deviations from its 20 s mean.
    fade_eval = {}
    for label, (frs, lo, hi, sp) in slices.items():
        x, y, _ = stack(frs, ["z_20"], lo, hi, sp)
        m = (np.abs(x[:, 0]) > 2.0) & (y != 0)
        if m.sum() >= 300:
            fade_eval[label] = {
                "n": int(m.sum()),
                "share": float(m.mean()),
                "hit": float((-np.sign(x[m, 0]) == np.sign(y[m])).mean()),
                "hit_se": math.sqrt(0.25 / max(1.0, m.sum() / HORIZON)),
            }

    measured = {}
    pooled = [k for k in ("train", "valid", "test") if "any" in vote_eval.get(k, {})]
    for tier in ("mixed", "lean", "strong"):
        n = sum(vote_eval[k][tier]["n"] for k in pooled if "hit" in vote_eval[k][tier])
        if n:
            measured[tier] = {
                "hit": sum(
                    vote_eval[k][tier]["hit"] * vote_eval[k][tier]["n"]
                    for k in pooled
                    if "hit" in vote_eval[k][tier]
                )
                / n,
                "mean_follow_bps": sum(
                    vote_eval[k][tier]["mean_follow_bps"] * vote_eval[k][tier]["n"]
                    for k in pooled
                    if "hit" in vote_eval[k][tier]
                )
                / n,
                "share": sum(
                    vote_eval[k][tier]["share"] * vote_eval[k]["n"]
                    for k in pooled
                    if "hit" in vote_eval[k][tier]
                )
                / sum(vote_eval[k]["n"] for k in pooled),
            }
    # The average move in the direction of the call at each step ahead, per tier, on the base recording.
    # This is the chart's most-likely line: where price went on average after a grid like this one.
    ahead_names = [f"ahead_{step}" for step in PATH_STEPS]
    xa, _, _ = stack(all_base, grid_names + ahead_names, 0.0, 1.0, span)
    net_all = F.vote(xa[:, : len(grid_names)]).sum(axis=1)
    for tier, (floor, ceil) in (
        ("mixed", (1, LEAN)),
        ("lean", (LEAN, STRONG)),
        ("strong", (STRONG, len(TILES) + 1)),
    ):
        mask = (np.abs(net_all) >= floor) & (np.abs(net_all) < ceil)
        if tier in measured and mask.sum() >= 300:
            signed = np.sign(net_all[mask])[:, None] * xa[mask][:, len(grid_names) :]
            measured[tier]["path_bps"] = [
                [step, float(signed[:, k].mean())] for k, step in enumerate(PATH_STEPS)
            ]
    # The live recording is the only sample that played no part in choosing the tiles.
    for tier, row in measured.items():
        live_row = vote_eval.get("live_all", {}).get(tier, {})
        if "hit" in live_row:
            row["live"] = {
                "hit": live_row["hit"],
                "hit_se": live_row["hit_se"],
                "n": live_row["n"],
            }
    # Experiments: every variant at every horizon. The prior the extension ships is the whole
    # base recording: a starting point for live testing, not a held-out result. The weighted
    # aggregate is replayed with a prior from the first 60% only and read on what follows.
    experiments_all = X.experiment_table(all_base)
    experiments_train = X.experiment_table(all_base, 0.0, SPLIT[0], span)
    experiments_late = X.experiment_table(all_base, SPLIT[0], 1.0, span)
    experiments_live = X.experiment_table(live_frames) if live_frames else {}
    train_prior = {
        key: (rows[HORIZON][0] if rows[HORIZON][0] is not None else 0.5)
        for key, rows in experiments_train.items()
    }
    slot_ids = [F.TILE_VARIANTS[key] for key, _, _ in TILES]
    weighted = {
        "base_after_60pct": X.replay(
            list(base.values()), slot_ids, train_prior, HORIZON, SPLIT[0], 1.0, span
        )
    }
    if live_frames:
        weighted["live_all"] = X.replay(
            list(live.values()), slot_ids, train_prior, HORIZON
        )
    # Consecutive strong calls, and what betting against a reading under 50% returns. Extra live
    # recordings are scored here only: the model's own figures keep their one live file.
    whole_prior = {
        key: (rows[HORIZON][0] if rows[HORIZON][0] is not None else 0.5)
        for key, rows in experiments_all.items()
    }
    extra = {}
    for path in args.extra_live or []:
        extra_groups = [frames(t) for t in read_live(path).values()]
        for frame_list in extra_groups:
            X.variant_votes(frame_list)
        extra[path.name] = extra_groups
    streak_study = {
        "base_after_60pct": X.streaks(
            X.call_series(list(base.values()), slot_ids, train_prior, HORIZON),
            HORIZON,
            SPLIT[0],
            1.0,
            span,
        )
    }
    fade_study = {
        "base_after_60pct": X.fade(
            list(base.values()), slot_ids, HORIZON, SPLIT[0], 1.0, span
        ),
        "base_all": X.fade(list(base.values()), slot_ids, HORIZON),
    }
    live_sets = ({"live_all": list(live.values())} if live_frames else {}) | extra
    for name, groups in live_sets.items():
        streak_study[name] = X.streaks(
            X.call_series(
                groups,
                slot_ids,
                whole_prior if name != "live_all" else train_prior,
                HORIZON,
            ),
            HORIZON,
        )
        fade_study[name] = X.fade(groups, slot_ids, HORIZON)
    signed_extra = {
        name: X.replay(groups, slot_ids, whole_prior, HORIZON)
        for name, groups in extra.items()
    }

    measured_by_name = {
        name: X.measured_tiers(
            weighted["base_after_60pct"], weighted.get("live_all"), name
        )
        for name in X.REPLAY_NAMES
    }
    # A setting that was usually wrong on the first 60%: does betting against it pay afterwards?
    inverse_study = {
        "base_after_60pct": X.inverse_study(experiments_train, experiments_late)
    }
    if live_frames:
        inverse_study["live_all"] = X.inverse_study(experiments_all, experiments_live)
    for name, groups in extra.items():
        inverse_study[name] = X.inverse_study(
            experiments_all,
            X.experiment_table([fr for frames_ in groups for fr in frames_]),
        )

    experiments_model = X.experiments_model(
        [key for key, _, _ in TILES],
        experiments_all,
        HORIZON,
        measured_by_name,
        weighted["base_after_60pct"],
        inverse_study["base_after_60pct"][str(HORIZON)]["under_50"],
    )
    model = {
        "version": 4,
        "horizon_s": HORIZON,
        "warmup_s": TILE_WARMUP,
        "lean": LEAN,
        "strong": STRONG,
        # Each tile's own record: how often following its sign alone was right, per slice.
        "tiles": [
            {
                "key": k,
                "feature": nm,
                "label": lab,
                "hit": {
                    part: table[nm][part]["hit_follow"]
                    for part in ("train", "valid", "test", "live")
                    if "hit_follow" in table[nm].get(part, {})
                },
            }
            for k, nm, lab in TILES
        ],
        "measured": measured,
        "cone": cone["rv_30"],
        "slopes": ladder_model,
    }
    digest = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
    summary = {
        "inputs": input_receipt(args.base, args.live),
        "horizon_s": HORIZON,
        "entry_delay_s": ENTRY_DELAY,
        "tile_warmup_s": TILE_WARMUP,
        "split": SPLIT,
        "base_span": [int(span[0]), int(span[1])],
        "moves": moves,
        "features": table,
        "families": chosen,
        "model": model,
        "model_sha256": digest,
        "vote_eval": vote_eval,
        "ladder_eval": ladder_eval,
        "ladder_history": ladder_history,
        "experiments": {
            "base": experiments_all,
            "base_first_60pct": experiments_train,
            "base_after_60pct": experiments_late,
            "live": experiments_live,
        },
        "weighted_vote": weighted,
        "weighted_vote_extra_live": signed_extra,
        "consecutive_strong": streak_study,
        "fade_below_half": fade_study,
        "inverse_settings": inverse_study,
        "fade_z20_beyond_2": fade_eval,
        "trades_1000x": trades,
        "window_agreement": window_agreement,
        "cone": cone,
        "cone_check": cone_check,
        "payout_pct_by_move_bps": payout,
        "breakeven_hit_rate_by_move_bps": breakeven,
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out / "model.json").write_text(
        json.dumps(model, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.fixture:
        write_fixture(
            args.fixture, longest, grid_names, digest, model, experiments_model
        )
    (args.out / "experiments.json").write_text(
        json.dumps(experiments_model, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.experiments_js:
        body = json.dumps(experiments_model, indent=1, sort_keys=True)
        args.experiments_js.write_text(
            "// Generated by `python -m research.scalp_1s_study --experiments-js`. Do not edit by hand.\n"
            "// Every setting the Experiments tab keeps testing, with its hit rate on the base recording per horizon.\n"
            f"export const SCALP_EXPERIMENTS = Object.freeze({body});\n",
            encoding="utf-8",
        )
    if args.js:
        body = json.dumps({**model, "sha256": digest}, indent=2, sort_keys=True)
        args.js.write_text(
            "// Generated by `python -m research.scalp_1s_study --js`. Do not edit by hand:\n"
            "// test/1000x-scalp.test.js compares it with the study's fixture.\n"
            f"export const SCALP_MODEL = Object.freeze({body});\n",
            encoding="utf-8",
        )
    brief = {
        k: {t: v[t] for t in ("any", "mixed", "lean", "strong", "breakout60") if t in v}
        for k, v in vote_eval.items()
    }
    print(
        json.dumps(
            {
                "families": chosen,
                "vote": brief,
                "trades": trades,
                "breakeven": breakeven,
                "moves": moves,
                "cone": cone,
                "cone_check": cone_check,
                "window_agreement": window_agreement,
                "measured": measured,
                "ladder": {
                    k: {
                        w: {
                            kk: (round(vv["hit"], 4), round(vv.get("share", 0), 2))
                            for kk, vv in row.items()
                            if isinstance(vv, dict) and "hit" in vv
                        }
                        for w, row in v.items()
                    }
                    for k, v in ladder_eval.items()
                    if k in ("train", "valid", "test", "live_all")
                },
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
