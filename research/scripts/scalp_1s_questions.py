"""Follow-up questions about the 1s scalp read-out, answered on the recorded ticks.

1. Do some readings, taken together, agree with the next 30 seconds more often?
2. Is a call backed by more agreement (more readings, more strong calls in a row,
   more markets) right more often than a lone one?
3. Does anything point the right way before a large move?
4. Does the top of the Coinbase order book, which the base capture also holds,
   say where the oracle price goes next?

Every figure is a count over recorded prices. Nothing here trades, and nothing
reads the network: the inputs are the tick files the main study reads.

What was seen when. Rankings, thresholds and fitted weights are learned on the
first 60% of the base recording and read on the last 40%, as the main study does.
That later part is not a clean test: the sixteen tiles themselves were chosen
with the whole base recording in view (scalp_1s_study.TILES). The live
recordings are the only samples that played no part in any choice, and they are
short. Treat a base figure as an upper bound and the live ones as the check.
"""

from __future__ import annotations

import argparse
import gzip
import itertools
import json
import math
import zlib
from pathlib import Path

import numpy as np

from research import scalp_1s_experiments as X
from research import scalp_1s_features as F
from research import scalp_1s_study as S

HORIZON = S.HORIZON
# A combination must speak on at least this share of seconds to be ranked: one that
# agrees once an hour can be right by luck and is of no use as a read-out.
MIN_SHARE = {1: 0.05, 2: 0.05, 3: 0.03}
TOP = 10
# A hit rate is reported only over at least this many calls (ten horizons' worth).
MIN_CALLS = 300
# A "large" move is one of a market's biggest twentieth of 30 second moves. A fixed size in
# basis points would be an ordinary move for ZEC and a rare one for BTC.
LARGE_QUANTILE = 0.95
BOOK_STALE_S = 3
BOOK_HORIZONS = (3, 5, 10, 30)
BOOK_DELAYS = (0, S.ENTRY_DELAY)


def standard_error(seconds: float, horizon: int = HORIZON) -> float:
    """The error of a hit rate over calls made in `seconds` distinct seconds of clock time.

    Seconds overlap: `horizon` consecutive calls share most of one outcome, so they count
    as seconds / horizon independent looks. And markets move together: calls that two
    markets make in the same second are counted as one second, not two. For one market
    this is the main study's rule (calls / horizon); for several it does not let a
    second market that moves with the first halve the error.
    """
    return math.sqrt(0.25 / max(1.0, seconds / horizon))


def looks(seconds, horizon: int = HORIZON) -> float:
    """How many independent looks a set of clock seconds makes when the seconds were
    picked out by what followed them (the seconds before a large move).

    Seconds no more than `horizon` apart are one run. A run counts as its seconds
    over `horizon`, like any stretch, but never as less than one look: the few seconds
    before one move are one look at it, wherever a clock-aligned block boundary falls.
    """
    times = np.sort(np.fromiter(seconds, dtype=np.int64, count=len(seconds)))
    if not times.size:
        return 0.0
    run = np.r_[0, np.cumsum(np.diff(times) > horizon)]
    return float(np.maximum(1.0, np.bincount(run) / horizon).sum())


def _keep(fr, horizon, lo, hi, span):
    sign = X.forward_sign(fr["close"], horizon)
    return sign, (sign != 0) & X._window(fr, horizon, lo, hi, span)


# ----------------------------------------------------------------- combinations


def agreement_counts(frame_list, members, size, slices, span, horizon=HORIZON):
    """For every `size`-subset of `members`: how often all of them voted the same
    way, and how often that way was right, inside each time slice.

    Returns (combos, hits[slice][combo], calls[slice][combo], seconds[slice],
    spoken[slice][combo]). `spoken` is for the error bar: the seconds of clock time the
    combination spoke in, counting a second once however many markets spoke in it. It is
    kept per `horizon`-second stretch as the most any one market spoke there, which is
    exact when markets speak in the same seconds and never more than the true count.
    """
    combos = list(itertools.combinations(range(len(members)), size))
    hits = np.zeros((len(slices), len(combos)))
    calls = np.zeros((len(slices), len(combos)))
    seconds = np.zeros(len(slices))
    origin = min((int(fr["time"][0]) for fr in frame_list), default=0) // horizon
    last = max((int(fr["time"][-1]) for fr in frame_list), default=0) // horizon
    width = last - origin + 1
    most = np.zeros((len(slices), len(combos), width), dtype=np.int16)
    for fr in frame_list:
        sign = X.forward_sign(fr["close"], horizon)
        masks = [
            (sign != 0) & X._window(fr, horizon, lo, hi, span) for lo, hi in slices
        ]
        if not any(mask.any() for mask in masks):
            continue
        stretch = fr["time"] // horizon - origin
        votes = np.column_stack([fr["variants"][key] for key in members])
        up, down = votes > 0, votes < 0
        right_up, right_down = sign > 0, sign < 0
        for k, combo in enumerate(combos):
            cols = list(combo)
            all_up = up[:, cols].all(axis=1)
            all_down = down[:, cols].all(axis=1)
            said = all_up | all_down
            right = (all_up & right_up) | (all_down & right_down)
            for s, mask in enumerate(masks):
                counted = said & mask
                calls[s, k] += counted.sum()
                hits[s, k] += (right & mask).sum()
                np.maximum(
                    most[s, k],
                    np.bincount(stretch[counted], minlength=width),
                    out=most[s, k],
                    casting="unsafe",
                )
        for s, mask in enumerate(masks):
            seconds[s] += mask.sum()
    return combos, hits, calls, seconds, most.sum(axis=2, dtype=np.int64)


def combination_study(frame_list, members, span, split=S.SPLIT[0], extra=None) -> dict:
    """Rank agreeing pairs and triples on the first part of the recording, then read
    the same ones on the rest (and on each sample in ``extra``, a name -> frames map).

    Which combinations are ranked, and their order, depend on the first slice alone.
    What matters is the "later" column: the best of hundreds of combinations on one
    sample overstates itself. A later hit rate is given only over MIN_CALLS calls.
    """
    slices = [(0.0, split), (split, 1.0)]
    out = {"members": list(members), "min_share": MIN_SHARE, "sizes": {}}
    for size in (1, 2, 3):
        combos, hits, calls, seconds, spoken = agreement_counts(
            frame_list, members, size, slices, span
        )
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = hits / calls
            share = calls / seconds[:, None]
        eligible = share[0] >= MIN_SHARE[size]
        measured = eligible & (calls[1] >= MIN_CALLS)
        order = [
            k for k in np.argsort(-np.nan_to_num(rate[0], nan=-1.0)) if eligible[k]
        ]
        chosen = order[:TOP]
        other = {}
        for name, frames in (extra or {}).items():
            _, h, c, sec, b = agreement_counts(
                frames, members, size, [(0.0, 1.0)], None
            )
            other[name] = (h[0], c[0], sec[0], b[0])
        rows = []
        for k in chosen:
            row = {
                "members": [members[i] for i in combos[k]],
                "first": {
                    "hit": float(rate[0, k]),
                    "share": float(share[0, k]),
                    "se": standard_error(spoken[0, k]),
                },
                "later": {
                    "hit": float(rate[1, k]),
                    "share": float(share[1, k]),
                    "se": standard_error(spoken[1, k]),
                    "calls": int(calls[1, k]),
                }
                if measured[k]
                else {"calls": int(calls[1, k])},
            }
            for name, (h, c, sec, b) in other.items():
                if c[k] >= MIN_CALLS:
                    row[name] = {
                        "hit": float(h[k] / c[k]),
                        "share": float(c[k] / sec),
                        "se": standard_error(b[k]),
                    }
            rows.append(row)
        later = rate[1][measured]
        kept = [k for k in chosen if measured[k]]
        out["sizes"][str(size)] = {
            "tried": len(combos),
            "eligible": int(eligible.sum()),
            "measured_later": int(measured.sum()),
            "top": rows,
            # How the ones picked on the first slice did afterwards, against every eligible one.
            "top_first_mean": float(np.mean(rate[0][kept])) if kept else None,
            "top_later_mean": float(np.mean(rate[1][kept])) if kept else None,
            "all_later_median": float(np.median(later)) if later.size else None,
            "all_later_best": float(np.max(later)) if later.size else None,
        }
    return out


def fitted_vote(
    frame_list, members, span, split=S.SPLIT[0], ridge=10.0, top_share=0.2, extra=None
) -> dict:
    """A ridge fit of the next move's sign on the members' votes. The weights, and the
    size of score that marks its most confident `top_share` of seconds, are learned
    on the first slice and applied unchanged to every later sample. The window's
    strong call speaks on about a fifth of seconds, hence the default share."""

    def gather(frames, lo, hi, sp):
        xs, ys, stretches = [], [], []
        for fr in frames:
            sign, keep = _keep(fr, HORIZON, lo, hi, sp)
            if keep.any():
                xs.append(
                    np.column_stack([fr["variants"][key] for key in members])[keep]
                )
                ys.append(sign[keep])
                stretches.append(fr["time"][keep])
        if not xs:
            return (
                np.zeros((0, len(members))),
                np.zeros(0),
                np.zeros(0, dtype=np.int64),
            )
        return (
            np.vstack(xs).astype(np.float64),
            np.concatenate(ys).astype(np.float64),
            np.concatenate(stretches),
        )

    x, y, _ = gather(frame_list, 0.0, split, span)
    if not y.size:
        raise ValueError("no scored second in the first slice to fit on")
    weights = np.linalg.solve(x.T @ x + ridge * np.eye(len(members)), x.T @ y)
    threshold = float(np.quantile(np.abs(x @ weights), 1.0 - top_share))

    def read(xs, ys, stretches):
        score = xs @ weights
        said = score != 0
        # A score of zero says nothing, however low the threshold has fallen.
        top = said & (np.abs(score) >= threshold)

        def rate(mask):
            if not mask.any():
                return None
            return float((np.sign(score[mask]) == ys[mask]).mean())

        def error(mask):
            return standard_error(np.unique(stretches[mask]).size)

        return {
            "all": {"hit": rate(said), "n": int(said.sum()), "se": error(said)},
            "top": {
                "hit": rate(top),
                "share": float(top.mean()) if top.size else 0.0,
                "se": error(top),
            },
        }

    out = {
        "members": len(members),
        "ridge": ridge,
        "top_share": top_share,
        "first": read(*gather(frame_list, 0.0, split, span)),
        "later": read(*gather(frame_list, split, 1.0, span)),
        "largest_weights": [
            [members[k], float(weights[k])] for k in np.argsort(-np.abs(weights))[:8]
        ],
    }
    for name, frames in (extra or {}).items():
        xs, ys, stretches = gather(frames, 0.0, 1.0, None)
        if ys.size:
            out[name] = read(xs, ys, stretches)
    return out


# ------------------------------------------------------------------- agreement


def _bucket(value: int, edges) -> str:
    for low, high in edges:
        if low <= value <= high:
            return str(low) if low == high else f"{low}-{high}"
    return f"{edges[-1][1] + 1}+"


NET_EDGES = ((1, 3), (4, 7), (8, 11), (12, 13), (14, 15), (16, 16))
DENSITY_EDGES = ((1, 1), (2, 5), (6, 15), (16, 30))


def _rated(tally: dict) -> dict:
    """{key: [hits, calls, set of clock seconds]} as rates, for keys with MIN_CALLS calls."""
    return {
        key: {"hit": hits / n, "n": n, "se": standard_error(len(seconds))}
        for key, (hits, n, seconds) in tally.items()
        if n >= MIN_CALLS
    }


def by_net_votes(frame_list, slot_ids, lo=0.0, hi=1.0, span=None) -> dict:
    """Hit rate of the grid's plain vote by how many readings net out one way."""
    warm = max(v["need"] for v in F.VARIANTS if v["id"] in slot_ids)
    tally = {}
    for fr in frame_list:
        sign, keep = _keep(fr, HORIZON, lo, hi, span)
        net = np.sum([fr["variants"][key] for key in slot_ids], axis=0)
        keep &= (np.arange(net.size) + 1 >= warm) & (net != 0)
        for t in np.flatnonzero(keep):
            row = tally.setdefault(_bucket(abs(int(net[t])), NET_EDGES), [0, 0, set()])
            row[0] += int(np.sign(net[t]) == sign[t])
            row[1] += 1
            row[2].add(int(fr["time"][t]))
    return _rated(tally)


def strong_direction(series_row) -> np.ndarray:
    score = series_row["weighted"]
    return np.where(
        series_row["ready"] & (np.abs(score) >= X.WEIGHTED_STRONG), np.sign(score), 0.0
    )


def strong_density(series, lo=0.0, hi=1.0, span=None, window=30) -> dict:
    """Hit rate of a strong call by how many strong calls the same way were made in
    the `window` seconds up to and including it."""
    tally = {}
    for row in series:
        direction = strong_direction(row)
        n = direction.size
        inside = X._window({"time": row["time"]}, HORIZON, lo, hi, span)
        for side in (1.0, -1.0):
            same = np.cumsum(direction == side)
            count = same - np.r_[np.zeros(window), same[:-window]][:n]
            picked = (direction == side) & (row["sign"] != 0) & inside
            for t in np.flatnonzero(picked):
                bucket = tally.setdefault(
                    _bucket(int(count[t]), DENSITY_EDGES), [0, 0, set()]
                )
                bucket[0] += int(row["sign"][t] == side)
                bucket[1] += 1
                bucket[2].add(int(row["time"][t]))
    return _rated(tally)


def across_markets(series, lo=0.0, hi=1.0, span=None) -> dict:
    """Hit rate of a strong call by what the other markets' calls said that second:
    alone, with at least one other market strong the same way, or against one."""
    by_time = {}
    for row in series:
        direction = strong_direction(row)
        for t in np.flatnonzero(row["ready"]):
            by_time.setdefault(int(row["time"][t]), {})[row["group"]] = direction[t]
    tally = {key: [0, 0, set()] for key in ("alone", "with_another", "against_another")}
    for row in series:
        direction = strong_direction(row)
        inside = X._window({"time": row["time"]}, HORIZON, lo, hi, span)
        for t in np.flatnonzero((direction != 0) & (row["sign"] != 0) & inside):
            others = [
                value
                for group, value in by_time[int(row["time"][t])].items()
                if group != row["group"]
            ]
            if not others:
                continue  # no other market was being read that second
            key = (
                "against_another"
                if any(value == -direction[t] for value in others)
                else "with_another"
                if any(value == direction[t] for value in others)
                else "alone"
            )
            tally[key][0] += int(row["sign"][t] == direction[t])
            tally[key][1] += 1
            # Two markets agreeing in the same second are one look at the market, not two.
            tally[key][2].add(int(row["time"][t]))
    return _rated(tally)


# ------------------------------------------------------------------ large moves


def large_edges(groups, lo=0.0, hi=1.0, span=None) -> list:
    """Per market, the size in basis points of a large 30 second move: the
    LARGE_QUANTILE of absolute moves in the given slice of the recording."""
    edges = []
    for frames in groups:
        sizes = [
            np.abs(fr["fwd"][X._window(fr, HORIZON, lo, hi, span)]) for fr in frames
        ]
        sizes = np.concatenate(sizes) if sizes else np.zeros(0)
        sizes = sizes[np.isfinite(sizes)]
        edges.append(
            float(np.quantile(sizes, LARGE_QUANTILE)) if sizes.size else math.inf
        )
    return edges


def volatility_edges(groups, lo=0.0, hi=1.0, span=None) -> list:
    """Per market, the four cuts that split its 30 second volatility into fifths, taken
    from the given slice of the recording."""
    edges = []
    for frames in groups:
        values = [
            fr["features"]["rv_30"][X._window(fr, HORIZON, lo, hi, span)]
            for fr in frames
        ]
        values = np.concatenate(values) if values else np.zeros(0)
        values = values[np.isfinite(values)]
        edges.append(
            [float(v) for v in np.quantile(values, [0.2, 0.4, 0.6, 0.8])]
            if values.size
            else [math.inf] * 4
        )
    return edges


def large_moves(groups, series, edges, vol_edges, lo=0.0, hi=1.0, span=None) -> dict:
    """What the read-outs said just before a large 30 second move (``edges``, one size
    per market), beside what they said before any move. Choosing seconds by what
    happened next is hindsight: this asks whether a pointer exists, not whether one
    can be traded. The last block is the usable form: how often a large move
    followed, and how the strong call did, by how volatile the last 30 seconds had
    been (``vol_edges``, one set of cuts per market, learned beforehand)."""
    flat = [fr for frames in groups for fr in frames]
    readers = {
        "strong_call": lambda fr, row: strong_direction(row),
        "any_call": lambda fr, row: np.where(
            row["ready"], np.sign(row["weighted"]), 0.0
        ),
        "breakout_60": lambda fr, row: fr["variants"]["breakout_60"].astype(float),
        "momentum_60": lambda fr, row: fr["variants"]["roc_60"].astype(float),
        "momentum_5": lambda fr, row: fr["variants"]["roc_5"].astype(float),
        "zscore_20": lambda fr, row: fr["variants"]["zscore_20"].astype(float),
    }
    kinds = ("large", "all")
    tally = {which: {name: [0, 0, 0] for name in readers} for which in kinds}
    # Counted per reading: one that spoke before few large moves must not borrow the
    # error bar of one that spoke before all. Clock seconds, so that two markets moving
    # together in the same seconds are one look.
    before_large = {name: set() for name in readers}
    seconds = {"large": 0, "all": 0}
    large_seconds = set()
    # Per volatility fifth: seconds, large moves, strong calls, strong hits, stretches with a strong call.
    by_fifth = [[0, 0, 0, 0, set()] for _ in range(5)]
    spoken = {name: set() for name in readers}  # seconds of clock time, over all moves
    for fr, row in zip(flat, series, strict=True):
        inside = (
            X._window(fr, HORIZON, lo, hi, span) & (row["sign"] != 0) & row["ready"]
        )
        size = np.abs(fr["fwd"])
        # A market that never moved has an edge of zero, and nothing in it is large.
        large = inside & (size >= edges[row["group"]]) & (size > 0)
        seconds["all"] += int(inside.sum())
        seconds["large"] += int(large.sum())
        large_seconds.update(fr["time"][large].tolist())
        for name, read in readers.items():
            vote = read(fr, row)
            for which, mask in (("large", large), ("all", inside)):
                spoke = mask & (vote != 0)
                cell = tally[which][name]
                cell[0] += int((vote[spoke] == row["sign"][spoke]).sum())
                cell[1] += int(spoke.sum())
                cell[2] += int(mask.sum())
                (before_large if which == "large" else spoken)[name].update(
                    fr["time"][spoke].tolist()
                )
        vol = fr["features"]["rv_30"]
        ok = inside & np.isfinite(vol)
        fifth = np.searchsorted(vol_edges[row["group"]], vol, side="right")
        call = strong_direction(row)
        for q in range(5):
            mine = ok & (fifth == q)
            said = mine & (call != 0)
            by_fifth[q][0] += int(mine.sum())
            by_fifth[q][1] += int((mine & large).sum())
            by_fifth[q][2] += int(said.sum())
            by_fifth[q][3] += int((call[said] == row["sign"][said]).sum())
            by_fifth[q][4].update(fr["time"][said].tolist())
    out = {
        "edges_bps": list(edges),
        "seconds": seconds,
        "large_share": seconds["large"] / max(1, seconds["all"]),
        "large_independent": max(1.0, looks(large_seconds)),
    }
    for which in kinds:
        out[which] = {
            name: {
                "hit": hits / n,
                "spoke_share": n / total,
                # Before a large move a reading speaks for a few seconds of each move, so the
                # moves it spoke before are the count; over all seconds the usual rule applies.
                "se": math.sqrt(0.25 / max(1.0, looks(before_large[name])))
                if which == "large"
                else standard_error(len(spoken[name])),
            }
            for name, (hits, n, total) in tally[which].items()
            if n >= 100
        }
    out["by_volatility_quintile"] = [
        {
            "quintile": q + 1,
            "seconds_share": total / max(1, seconds["all"]),
            "large_share": big / total if total else None,
            "strong_hit": hits / said if said >= MIN_CALLS else None,
            "strong_se": standard_error(len(seconds_said)),
            "strong_share": said / total if total else None,
        }
        for q, (total, big, said, hits, seconds_said) in enumerate(by_fifth)
    ]
    return out


# ------------------------------------------------------------------ order book


def read_book(directory: Path) -> tuple:
    """Coinbase top-of-book rows from the hourly captures, per asset: one row per
    second, the last one received in it (mid, bid size, ask size, spread).

    Also returns, per asset, how long the oracle's own ticks took to arrive
    (receive time less the oracle's time, in seconds). The book is placed on the
    local receive clock and the oracle bars on the oracle's clock, so that delay
    is what the two clocks disagree by: see ``book_features``.
    """
    last, delays = {}, {}
    for path in sorted(directory.glob("dual-quotes-*.jsonl.gz")):
        try:
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                        asset = row["asset"]
                        received = float(row["received_at"])
                        if row["venue"] == "jupiter":
                            delays.setdefault(asset, []).append(
                                received - float(row["exchange_at"])
                            )
                            continue
                        if row["venue"] != "coinbase":
                            continue
                        values = (
                            received,
                            (float(row["bid"]) + float(row["ask"])) / 2.0,
                            float(row["bid_size"]),
                            float(row["ask_size"]),
                            float(row["ask"]) - float(row["bid"]),
                        )
                    except (KeyError, TypeError, ValueError):
                        continue  # a cut-off or malformed line is skipped, not fatal
                    if not all(math.isfinite(v) for v in values) or values[1] <= 0:
                        continue
                    second = int(received)
                    seen = last.setdefault(asset, {})
                    if second not in seen or seen[second][0] <= received:
                        seen[second] = values
        except (EOFError, OSError, zlib.error):
            # An hour file cut short by a recorder restart keeps the rows already read.
            continue
    books = {}
    for asset, seen in last.items():
        seconds = np.array(sorted(seen), dtype=np.int64)
        table = np.array([seen[s] for s in seconds])
        books[asset] = {
            "second": seconds,
            "mid": table[:, 1],
            "bid_size": table[:, 2],
            "ask_size": table[:, 3],
            "spread": table[:, 4],
        }
    latency = {}
    for asset, values in delays.items():
        values = np.array(values)
        values = values[np.isfinite(values)]
        if values.size:
            latency[asset] = {
                "ticks": int(values.size),
                **{f"p{q}": float(np.quantile(values, q / 100)) for q in (1, 50, 99)},
            }
    return books, latency


def _rolling_mean(values, window: int):
    """Mean of the last `window` values including the current one; NaN before that or
    where the window holds a missing value."""
    out = np.full(values.size, np.nan)
    if values.size >= window:
        out[window - 1 :] = np.lib.stride_tricks.sliding_window_view(
            values, window
        ).mean(axis=1)
    return out


def book_features(fr, book, lag: int = 0) -> dict:
    """Top-of-book readings known when the oracle bar of second t closes: only rows
    received before the end of second t - lag, and none more than BOOK_STALE_S older
    than that. A positive reading means "the book says up".

    The book is on the local receive clock and the bar on the oracle's clock. The
    oracle's ticks reached the recorder a fraction of a second after their own
    time (``read_book`` reports it), so at lag 0 the book row was in hand before the
    bar was. ``lag=1`` holds the book back a further second, as a check that a lead
    is not an artefact of the two clocks.
    """
    time, close = fr["time"], fr["close"]
    known = time - lag
    index = np.searchsorted(book["second"], known, side="right") - 1
    at = np.maximum(index, 0)
    fresh = (index >= 0) & (known - book["second"][at] <= BOOK_STALE_S)
    mid = np.where(fresh, book["mid"][at], np.nan)
    bid, ask = book["bid_size"][at], book["ask_size"][at]
    with np.errstate(invalid="ignore", divide="ignore"):
        imbalance = np.where(fresh & (bid + ask > 0), (bid - ask) / (bid + ask), np.nan)
    basis = (mid / close - 1.0) * 1e4
    out = {
        # Coinbase above its usual distance from the oracle: the oracle has catching up to do.
        "basis_dev": basis - _rolling_mean(basis, 300),
        "imbalance": imbalance,
        "spread_bps": np.where(fresh, book["spread"][at] / close * 1e4, np.nan),
    }
    for n in (2, 5):
        lead = np.full(close.size, np.nan)
        lead[n:] = (mid[n:] / mid[:-n] - close[n:] / close[:-n]) * 1e4
        out[f"lead_{n}"] = lead
        move = np.full(close.size, np.nan)
        move[n:] = (mid[n:] / mid[:-n] - 1.0) * 1e4
        out[f"book_roc_{n}"] = move
    return out


def delayed_sign(close, horizon: int, delay: int):
    """Sign of the move from `delay` seconds after each close to `horizon` seconds after
    that: what a position filled `delay` seconds late would see."""
    out = np.zeros(close.size, dtype=np.int8)
    reach = horizon + delay
    if close.size > reach:
        start = close[delay : close.size - horizon]
        out[: close.size - reach] = np.sign(close[reach:] - start).astype(np.int8)
    return out


def book_study(groups, books, series, span, split=S.SPLIT[0], lag: int = 0) -> dict:
    """Does the Coinbase book lead the oracle? Hit rate of each book reading's sign
    against the oracle's later move, at several horizons and with and without the
    two second fill delay, on the first and the later part of the recording.

    ``groups`` and ``books`` are aligned lists (frames of one market, its book), and
    ``series`` holds one row per frame in the same order. ``lag`` holds the book
    back that many seconds (``book_features``)."""
    names = ("basis_dev", "lead_2", "lead_5", "book_roc_2", "imbalance")
    parts = {"first": (0.0, split), "later": (split, 1.0)}
    tally = {}
    strong = {part: {} for part in parts}
    flat_series = iter(series)
    # For the error bars: which seconds of clock time each cell spoke in, counted once
    # however many markets spoke in them.
    start = int(span[0])
    width = int(span[1]) - start + 1

    def spoke_in(seconds, when):
        seconds[when - start] = True

    for frames, book in zip(groups, books, strict=True):
        rows = [next(flat_series) for _ in frames]
        if not frames:
            continue
        feats = [book_features(fr, book, lag) for fr in frames]
        # "Large" basis deviations are the top fifth by size, with the edge learned on the first part.
        first = np.concatenate(
            [
                np.abs(f["basis_dev"][X._window(fr, HORIZON, 0.0, split, span)])
                for fr, f in zip(frames, feats, strict=True)
            ]
        )
        first = first[np.isfinite(first)]
        edge = float(np.quantile(first, 0.8)) if first.size else math.inf
        for fr, f, row in zip(frames, feats, rows, strict=True):
            for delay in BOOK_DELAYS:
                for horizon in BOOK_HORIZONS:
                    sign = delayed_sign(fr["close"], horizon, delay)
                    for part, (lo, hi) in parts.items():
                        inside = (sign != 0) & X._window(
                            fr, horizon + delay, lo, hi, span
                        )
                        for name in names:
                            vote = np.nan_to_num(F.vote(f[name]), nan=0.0)
                            spoke = inside & (vote != 0)
                            cell = tally.setdefault(
                                (name, delay, horizon, part),
                                [0, 0, 0, np.zeros(width, dtype=bool)],
                            )
                            cell[0] += int((vote[spoke] == sign[spoke]).sum())
                            cell[1] += int(spoke.sum())
                            cell[2] += int(inside.sum())
                            spoke_in(cell[3], fr["time"][spoke])
                        if horizon != HORIZON:
                            continue
                        # The strong call with the book: agreeing, disagreeing, and the book alone when its
                        # deviation is large.
                        call = strong_direction(row)
                        book_vote = np.nan_to_num(F.vote(f["basis_dev"]), nan=0.0)
                        big = np.abs(np.nan_to_num(f["basis_dev"], nan=0.0)) >= edge
                        cases = {
                            "strong_call": (call != 0, call),
                            "strong_call_book_agrees": (
                                (call != 0) & (book_vote == call),
                                call,
                            ),
                            "strong_call_book_disagrees": (
                                (call != 0) & (book_vote == -call),
                                call,
                            ),
                            "book_large_deviation": (big & (book_vote != 0), book_vote),
                            "book_large_and_strong_call_agree": (
                                big & (call != 0) & (book_vote == call),
                                call,
                            ),
                        }
                        for key, (mask, vote) in cases.items():
                            spoke = inside & mask
                            cell = strong[part].setdefault(
                                (key, delay),
                                [0, 0, 0, 0.0, np.zeros(width, dtype=bool)],
                            )
                            cell[0] += int((vote[spoke] == sign[spoke]).sum())
                            cell[1] += int(spoke.sum())
                            cell[2] += int(inside.sum())
                            spoke_in(cell[4], fr["time"][spoke])
                            ahead = np.full(fr["close"].size, 0.0)
                            reach = horizon + delay
                            ahead[: fr["close"].size - reach] = (
                                fr["close"][reach:]
                                / fr["close"][delay : fr["close"].size - horizon]
                                - 1.0
                            ) * 1e4
                            cell[3] += float((vote[spoke] * ahead[spoke]).sum())
    out = {"readings": {}, "with_the_call": {part: {} for part in parts}}
    for (name, delay, horizon, part), (hits, n, total, seconds) in tally.items():
        if n < MIN_CALLS:
            continue
        out["readings"].setdefault(name, {}).setdefault(
            f"delay_{delay}", {}
        ).setdefault(str(horizon), {})[part] = {
            "hit": hits / n,
            "spoke_share": n / total,
            "se": standard_error(int(seconds.sum()), horizon),
        }
    for part, cells in strong.items():
        for (key, delay), (hits, n, total, moved, seconds) in cells.items():
            if n < MIN_CALLS:
                continue
            out["with_the_call"][part].setdefault(key, {})[f"delay_{delay}"] = {
                "hit": hits / n,
                "share": n / total,
                "se": standard_error(int(seconds.sum())),
                "mean_follow_bps": moved / n,
            }
    return out


# ------------------------------------------------------------------------ main


def members_for(train_table) -> list:
    """The sixteen starting tiles, plus the best setting of each kind on the first slice.
    A setting needs MIN_CALLS independent calls' worth there to be called the best."""
    starting = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
    best = {}
    for variant in F.VARIANTS:
        rate, calls = train_table[variant["id"]][HORIZON]
        if rate is None or calls < MIN_CALLS * HORIZON:
            continue
        if rate > best.get(variant["kind"], (0.0, None))[0]:
            best[variant["kind"]] = (rate, variant["id"])
    extra = [key for _, key in best.values() if key not in starting]
    return starting + sorted(extra)


def _clean(value):
    """JSON has no NaN or infinity: a figure that could not be computed is null."""
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--base", type=Path, required=True, help="folder of hourly dual-quote captures"
    )
    parser.add_argument(
        "--live",
        type=Path,
        action="append",
        default=[],
        help="a live tick recording (JSON lines, may be gzipped); repeatable",
    )
    parser.add_argument("--out", type=Path, required=True, help="summary JSON to write")
    args = parser.parse_args(argv)
    if not args.base.is_dir():
        parser.error(f"--base {args.base} is not a folder")

    base = {a: S.frames(t) for a, t in S.read_base(args.base).items()}
    all_base = [fr for frs in base.values() for fr in frs]
    if not all_base:
        parser.error(f"--base {args.base} holds no stretch of 600 seconds or more")
    X.variant_votes(all_base)
    span = (
        min(fr["time"][0] for fr in all_base),
        max(fr["time"][-1] for fr in all_base),
    )
    lives = {}
    for path in args.live:
        live = {a: S.frames(t) for a, t in S.read_live(path).items()}
        X.variant_votes([fr for frs in live.values() for fr in frs])
        lives[path.name] = live
    live_flat = {
        name: [fr for frs in live.values() for fr in frs]
        for name, live in lives.items()
    }

    train = X.experiment_table(all_base, 0.0, S.SPLIT[0], span)
    whole = X.experiment_table(all_base)

    def prior(table):
        return {
            key: (rows[HORIZON][0] if rows[HORIZON][0] is not None else 0.5)
            for key, rows in table.items()
        }

    slot_ids = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
    members = members_for(train)
    first = (0.0, S.SPLIT[0], span)
    later = (S.SPLIT[0], 1.0, span)

    assets = list(base)
    base_groups = list(base.values())
    base_series = X.call_series(base_groups, slot_ids, prior(train), HORIZON)
    live_series = {
        name: X.call_series(list(live.values()), slot_ids, prior(whole), HORIZON)
        for name, live in lives.items()
    }
    books, latency = read_book(args.base)
    booked = [asset for asset in assets if asset in books]

    def book(lag):
        return book_study(
            [base[asset] for asset in booked],
            [books[asset] for asset in booked],
            [row for row in base_series if assets[row["group"]] in books],
            span,
            lag=lag,
        )

    summary = {
        "horizon_s": HORIZON,
        "base_span": [int(span[0]), int(span[1])],
        "inputs": S.input_receipt(args.base, None),
        "live": sorted(lives),
        "what_was_seen_when": (
            "Rankings, thresholds and fits are learned on the first 60% of the base recording and"
            " read on the last 40%. The sixteen tiles were chosen with the whole base recording in"
            " view, so that later part is not a clean test. Only the live recordings are untouched."
        ),
        "combinations": combination_study(all_base, members, span, extra=live_flat),
        "fitted_vote": {
            "tiles": fitted_vote(all_base, slot_ids, span, extra=live_flat),
            "all_settings": fitted_vote(
                all_base,
                [v["id"] for v in F.VARIANTS],
                span,
                ridge=100.0,
                extra=live_flat,
            ),
        },
        "net_votes": {
            "base_first_60pct": by_net_votes(all_base, slot_ids, *first),
            "base_after_60pct": by_net_votes(all_base, slot_ids, *later),
            **{
                name: by_net_votes(frames, slot_ids)
                for name, frames in live_flat.items()
            },
        },
        "strong_density": {
            "base_after_60pct": strong_density(base_series, *later),
            **{name: strong_density(rows) for name, rows in live_series.items()},
        },
        "across_markets": {
            "base_after_60pct": across_markets(base_series, *later),
            **{name: across_markets(rows) for name, rows in live_series.items()},
        },
        "large_moves": {
            # What counts as large, and the volatility fifths, are learned on the first 60%.
            "base_after_60pct": large_moves(
                base_groups,
                base_series,
                large_edges(base_groups, *first),
                volatility_edges(base_groups, *first),
                *later,
            ),
            # A live recording is too short to split: its own largest twentieth and its own
            # volatility fifths, both in hindsight.
            **{
                name: large_moves(
                    list(lives[name].values()),
                    rows,
                    large_edges(list(lives[name].values())),
                    volatility_edges(list(lives[name].values())),
                )
                for name, rows in live_series.items()
            },
        },
        "order_book": {
            "markets": booked,
            "book_seconds": {
                asset: int(books[asset]["second"].size) for asset in booked
            },
            # How long the oracle's own ticks took to reach the recorder, in seconds.
            "oracle_arrival_delay_s": {
                asset: latency[asset] for asset in booked if asset in latency
            },
            **(book(0) if booked else {}),
            # The same with the book held back one second: a lead that is real survives it.
            "book_one_second_late": book(1) if booked else {},
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(_clean(summary), indent=1, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"written": str(args.out), "members": len(members), "book_markets": booked}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
