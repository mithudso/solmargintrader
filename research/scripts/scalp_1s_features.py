"""Causal indicator features on one-second oracle bars.

Every function reads one contiguous segment of 1s bars and returns arrays aligned
to it. The value at index t uses bars 0..t only; ``NaN`` marks warm-up. The same
definitions are ported to ``extension/src/1000x/scalp-indicators.js`` and checked
against a fixture written by ``research.scalp_1s_study --fixture``.

A positive value always means "price has been rising" (trend sense). Whether a
feature is followed or faded for the next 30 seconds is decided by the fitted
sign in the study, never by this module.
"""

from __future__ import annotations

import itertools
import math

import numpy as np

# An EMA seeded with the first close is exposed after this many spans, when the
# seed's remaining weight is below e^-6 (0.25%).
EMA_WARMUP_SPANS = 3
# Below this magnitude a reading casts no vote, so summation order cannot turn an
# exact tie into a direction. The extension uses the same constant.
VOTE_EPSILON = 1e-9


def vote(values):
    """+1, -1 or 0 per reading; NaN stays NaN."""
    values = np.asarray(values, dtype=np.float64)
    out = np.where(
        values > VOTE_EPSILON, 1.0, np.where(values < -VOTE_EPSILON, -1.0, 0.0)
    )
    out[~np.isfinite(values)] = np.nan
    return out


def second_bars(times_s, prices, max_gap_s: int = 3):
    """Aggregate ticks to 1s OHLC segments.

    ``times_s`` are exchange timestamps in seconds (float), increasing. A second
    with no tick repeats the previous close (the oracle did not publish), up to
    ``max_gap_s`` seconds; a longer silence starts a new segment, so no feature
    is computed across an unobserved stretch.
    """
    times_s = np.asarray(times_s, dtype=np.float64)
    prices = np.asarray(prices, dtype=np.float64)
    if times_s.size == 0:
        return []
    if (
        np.any(np.diff(times_s) < 0)
        or np.any(~np.isfinite(prices))
        or np.any(prices <= 0)
    ):
        raise ValueError("ticks must be time-ordered with positive finite prices")
    sec = np.floor(times_s).astype(np.int64)
    starts = np.flatnonzero(np.r_[True, sec[1:] != sec[:-1]])
    ends = np.r_[starts[1:], sec.size]
    bar_sec = sec[starts]
    o = prices[starts]
    c = prices[ends - 1]
    h = np.maximum.reduceat(prices, starts)
    lo = np.minimum.reduceat(prices, starts)
    segments, begin = [], 0
    breaks = np.flatnonzero(np.diff(bar_sec) > max_gap_s + 1) + 1
    for stop in [*breaks.tolist(), bar_sec.size]:
        t0, t1 = int(bar_sec[begin]), int(bar_sec[stop - 1])
        n = t1 - t0 + 1
        idx = bar_sec[begin:stop] - t0
        seg = {k: np.full(n, np.nan) for k in ("open", "high", "low", "close")}
        seg["open"][idx], seg["high"][idx] = o[begin:stop], h[begin:stop]
        seg["low"][idx], seg["close"][idx] = lo[begin:stop], c[begin:stop]
        filled = np.isnan(seg["close"])
        last = np.maximum.accumulate(np.where(filled, -1, np.arange(n)))
        carry = seg["close"][last]
        for k in ("open", "high", "low", "close"):
            seg[k] = np.where(filled, carry, seg[k])
        seg["time"] = np.arange(t0, t1 + 1, dtype=np.int64)
        seg["filled"] = filled
        segments.append(seg)
        begin = stop
    return segments


def ema(values, span: int):
    """adjust=False recurrence seeded with the first value; NaN during warm-up."""
    values = np.asarray(values, dtype=np.float64)
    out = np.empty_like(values)
    alpha = 2.0 / (span + 1.0)
    prev = values[0]
    for i, v in enumerate(values):
        prev = v if i == 0 else alpha * v + (1.0 - alpha) * prev
        out[i] = prev
    out[: min(values.size, EMA_WARMUP_SPANS * span - 1)] = np.nan
    return out


def _ema_raw(values, span: int):
    out = np.empty(len(values))
    alpha = 2.0 / (span + 1.0)
    prev = values[0]
    for i, v in enumerate(values):
        prev = v if i == 0 else alpha * v + (1.0 - alpha) * prev
        out[i] = prev
    return out


def rolling_sum(values, window: int):
    """Window sums taken on the window itself, so a window of zeros sums to exactly zero."""
    values = np.asarray(values, dtype=np.float64)
    out = np.full(values.size, np.nan)
    if values.size >= window:
        out[window - 1 :] = np.lib.stride_tricks.sliding_window_view(
            values, window
        ).sum(axis=1)
    return out


def rolling_mean(values, window: int):
    return rolling_sum(values, window) / window


def rolling_max(values, window: int):
    values = np.asarray(values, dtype=np.float64)
    out = np.full(values.size, np.nan)
    if values.size >= window:
        out[window - 1 :] = np.lib.stride_tricks.sliding_window_view(
            values, window
        ).max(axis=1)
    return out


def rolling_min(values, window: int):
    values = np.asarray(values, dtype=np.float64)
    out = np.full(values.size, np.nan)
    if values.size >= window:
        out[window - 1 :] = np.lib.stride_tricks.sliding_window_view(
            values, window
        ).min(axis=1)
    return out


def rolling_std(values, window: int):
    """Sample standard deviation, computed on the window itself (no cancellation drift)."""
    values = np.asarray(values, dtype=np.float64)
    out = np.full(values.size, np.nan)
    if values.size >= window:
        out[window - 1 :] = np.lib.stride_tricks.sliding_window_view(
            values, window
        ).std(axis=1, ddof=1)
    return out


def roc_bps(close, n: int):
    close = np.asarray(close, dtype=np.float64)
    out = np.full(close.size, np.nan)
    out[n:] = (close[n:] / close[:-n] - 1.0) * 1e4
    return out


def ema_cross_bps(close, fast: int, slow: int):
    return (ema(close, fast) - ema(close, slow)) / np.asarray(close) * 1e4


def macd_hist_bps(close, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD histogram in basis points of price: the fast EMA less the slow one, less its own signal EMA."""
    close = np.asarray(close, dtype=np.float64)
    line = _ema_raw(close, fast) - _ema_raw(close, slow)
    hist = (line - _ema_raw(line, signal)) / close * 1e4
    hist[: min(close.size, EMA_WARMUP_SPANS * slow - 1)] = np.nan
    return hist


def slope_t(close, window: int):
    """t-statistic of the least-squares slope of close on time over the window."""
    close = np.asarray(close, dtype=np.float64)
    out = np.full(close.size, np.nan)
    if close.size < window:
        return out
    win = np.lib.stride_tricks.sliding_window_view(close, window)
    x = np.arange(window, dtype=np.float64) - (window - 1) / 2.0
    sxx = float(np.sum(x * x))
    centered = win - win.mean(axis=1, keepdims=True)
    slope = centered @ x / sxx
    resid = centered - slope[:, None] * x[None, :]
    sse = np.sum(resid * resid, axis=1)
    se = np.sqrt(sse / (window - 2) / sxx)
    scale = np.abs(win).max(axis=1) * 1e-12
    t = np.where(se > scale, slope / np.where(se > scale, se, 1.0), 0.0)
    out[window - 1 :] = np.clip(t, -50.0, 50.0)
    return out


# The slope ladder shown in the extension, in seconds.
SLOPE_WINDOWS = (5, 10, 20, 30, 60, 300)


def slope_bps(close, window: int):
    """Least-squares slope of close on time over the window, in basis points of price per second."""
    close = np.asarray(close, dtype=np.float64)
    out = np.full(close.size, np.nan)
    if close.size < window:
        return out
    win = np.lib.stride_tricks.sliding_window_view(close, window)
    x = np.arange(window, dtype=np.float64) - (window - 1) / 2.0
    out[window - 1 :] = (
        (win - win.mean(axis=1, keepdims=True))
        @ x
        / float(np.sum(x * x))
        / win[:, -1]
        * 1e4
    )
    return out


def curvature_bps(close, window: int):
    """Second derivative of a least-squares parabola through the window, in basis points per second squared.

    Positive means the slope is increasing. With time centred on the window the
    quadratic term is orthogonal to the linear one, so this is twice the
    projection of close on (x^2 - mean(x^2)).
    """
    close = np.asarray(close, dtype=np.float64)
    out = np.full(close.size, np.nan)
    if close.size < window:
        return out
    win = np.lib.stride_tricks.sliding_window_view(close, window)
    x = np.arange(window, dtype=np.float64) - (window - 1) / 2.0
    q = x * x - float(np.mean(x * x))
    out[window - 1 :] = (
        2.0
        * ((win - win.mean(axis=1, keepdims=True)) @ q)
        / float(np.sum(q * q))
        / win[:, -1]
        * 1e4
    )
    return out


def sign_runs(values):
    """Completed runs of one slope sign: a list of (sign, seconds).

    A run starts at the first second whose vote is the opposite of the previous
    run's sign and ends at the second before the next flip; a zero or missing
    vote neither starts nor ends a run. The first run (its start was not seen)
    and the last (still open) are left out, so every reported length is whole.
    """
    votes = vote(values)
    runs, sign, start, seen_flip = [], 0.0, 0, False
    for i, v in enumerate(votes):
        if not np.isfinite(v) or v == 0 or v == sign:
            continue
        if sign != 0:
            if seen_flip:
                runs.append((int(sign), i - start))
            seen_flip = True
        sign, start = v, i
    return runs


def donchian_pos(high, low, close, window: int):
    """Position of the close in the window's high-low range, in [-0.5, 0.5]."""
    hi, lo = rolling_max(high, window), rolling_min(low, window)
    span = hi - lo
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = np.where(
            span > 0,
            (np.asarray(close) - lo) / np.where(span > 0, span, 1.0) - 0.5,
            0.0,
        )
    pos[np.isnan(hi)] = np.nan
    return pos


def zscore(close, window: int):
    close = np.asarray(close, dtype=np.float64)
    mean, sd = rolling_mean(close, window), rolling_std(close, window)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(
            sd > close * 1e-12, (close - mean) / np.where(sd > 0, sd, 1.0), 0.0
        )
    z[np.isnan(mean)] = np.nan
    return z


def rsi_centered(close, n: int):
    """Wilder RSI with an SMA seed, mapped to [-1, 1]; flat windows read 0."""
    close = np.asarray(close, dtype=np.float64)
    out = np.full(close.size, np.nan)
    if close.size <= n:
        return out
    delta = np.diff(close)
    gain, loss = np.maximum(delta, 0.0), np.maximum(-delta, 0.0)
    ag, al = gain[:n].mean(), loss[:n].mean()
    for i in range(n, close.size):
        if i > n:
            ag = (ag * (n - 1) + gain[i - 1]) / n
            al = (al * (n - 1) + loss[i - 1]) / n
        total = ag + al
        out[i] = 0.0 if total <= 0 else (ag - al) / total
    return out


def stoch_centered(high, low, close, n: int):
    return donchian_pos(high, low, close, n) * 2.0


def efficiency_ratio(close, window: int):
    """Kaufman efficiency ratio times the direction of the window's net change."""
    close = np.asarray(close, dtype=np.float64)
    out = np.full(close.size, np.nan)
    if close.size <= window:
        return out
    path = rolling_sum(np.abs(np.diff(close)), window)
    net = close[window:] - close[:-window]
    p = path[window - 1 :]
    out[window:] = np.where(p > 0, net / np.where(p > 0, p, 1.0), 0.0)
    return out


def bop_sma(open_, high, low, close, n: int):
    span = np.asarray(high) - np.asarray(low)
    raw = np.where(
        span > 0,
        (np.asarray(close) - np.asarray(open_)) / np.where(span > 0, span, 1.0),
        0.0,
    )
    return rolling_mean(raw, n)


def true_range(high, low, close):
    high, low, close = (np.asarray(v, dtype=np.float64) for v in (high, low, close))
    prev = np.r_[close[0], close[:-1]]
    return np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))


def keltner_pos(high, low, close, n: int):
    """(close - EMA_n) in units of the n-bar mean true range."""
    close = np.asarray(close, dtype=np.float64)
    atr = rolling_mean(true_range(high, low, close), n)
    mid = ema(close, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(
            atr > close * 1e-12, (close - mid) / np.where(atr > 0, atr, 1.0), 0.0
        )
    out[np.isnan(atr) | np.isnan(mid)] = np.nan
    return np.clip(out, -20.0, 20.0)


def di_diff(high, low, close, n: int):
    """Wilder +DI minus -DI (percent of smoothed true range), in [-100, 100]."""
    high, low, close = (np.asarray(v, dtype=np.float64) for v in (high, low, close))
    out = np.full(close.size, np.nan)
    if close.size <= n:
        return out
    up, down = np.diff(high), -np.diff(low)
    plus = np.where((up > down) & (up > 0), up, 0.0)
    minus = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(high, low, close)[1:]
    sp, sm, st = plus[:n].sum(), minus[:n].sum(), tr[:n].sum()
    for i in range(n, close.size):
        if i > n:
            sp = sp - sp / n + plus[i - 1]
            sm = sm - sm / n + minus[i - 1]
            st = st - st / n + tr[i - 1]
        out[i] = 0.0 if st <= 0 else 100.0 * (sp - sm) / st
    return out


def psar_dir(high, low, close, start=0.02, step=0.02, cap=0.2):
    """Parabolic SAR state: +1 while the stop is below price, -1 above."""
    high, low, close = (np.asarray(v, dtype=np.float64) for v in (high, low, close))
    n = close.size
    out = np.full(n, np.nan)
    if n < 2:
        return out
    up = close[1] >= close[0]
    sar = low[0] if up else high[0]
    ext = max(high[0], high[1]) if up else min(low[0], low[1])
    af = start
    out[1] = 1.0 if up else -1.0
    for i in range(2, n):
        sar = sar + af * (ext - sar)
        if up:
            sar = min(sar, low[i - 1], low[i - 2])
            if low[i] < sar:
                up, sar, ext, af = False, ext, low[i], start
            elif high[i] > ext:
                ext, af = high[i], min(cap, af + step)
        else:
            sar = max(sar, high[i - 1], high[i - 2])
            if high[i] > sar:
                up, sar, ext, af = True, ext, high[i], start
            elif low[i] < ext:
                ext, af = low[i], min(cap, af + step)
        out[i] = 1.0 if up else -1.0
    return out


def supertrend_dir(high, low, close, n: int = 10, mult: float = 3.0):
    high, low, close = (np.asarray(v, dtype=np.float64) for v in (high, low, close))
    atr = rolling_mean(true_range(high, low, close), n)
    out = np.full(close.size, np.nan)
    upper = lower = math.nan
    direction = 1.0
    for i in range(close.size):
        if math.isnan(atr[i]):
            continue
        mid = (high[i] + low[i]) / 2.0
        bu, bl = mid + mult * atr[i], mid - mult * atr[i]
        if math.isnan(upper):
            upper, lower = bu, bl
        else:
            upper = bu if (bu < upper or close[i - 1] > upper) else upper
            lower = bl if (bl > lower or close[i - 1] < lower) else lower
            if direction < 0 and close[i] > upper:
                direction = 1.0
            elif direction > 0 and close[i] < lower:
                direction = -1.0
        out[i] = direction
    return out


def zigzag_leg(close, threshold_bps: float):
    """Current swing leg from a close-only ZigZag.

    Returns (direction, extension_bps, age_s): +1 after a confirmed low, the
    signed move from that pivot, and seconds since the pivot bar. NaN before the
    first confirmation.
    """
    close = np.asarray(close, dtype=np.float64)
    n = close.size
    direction = np.full(n, np.nan)
    ext = np.full(n, np.nan)
    age = np.full(n, np.nan)
    frac = threshold_bps / 1e4
    state = 0
    hi_v, hi_i, lo_v, lo_i = close[0], 0, close[0], 0
    piv_v, piv_i = math.nan, -1
    for i in range(n):
        v = close[i]
        if state == 0:
            if v > hi_v:
                hi_v, hi_i = v, i
            if v < lo_v:
                lo_v, lo_i = v, i
            if v >= lo_v * (1 + frac):
                state, piv_v, piv_i, hi_v, hi_i = 1, lo_v, lo_i, v, i
            elif v <= hi_v * (1 - frac):
                state, piv_v, piv_i, lo_v, lo_i = -1, hi_v, hi_i, v, i
        elif state == 1:
            if v > hi_v:
                hi_v, hi_i = v, i
            elif v <= hi_v * (1 - frac):
                state, piv_v, piv_i, lo_v, lo_i = -1, hi_v, hi_i, v, i
        else:
            if v < lo_v:
                lo_v, lo_i = v, i
            elif v >= lo_v * (1 + frac):
                state, piv_v, piv_i, hi_v, hi_i = 1, lo_v, lo_i, v, i
        if state:
            direction[i] = state
            ext[i] = (v / piv_v - 1.0) * 1e4
            age[i] = i - piv_i
    return direction, ext, age


def heikin_ashi_streak(open_, high, low, close, cap: int = 20):
    """Signed run length of same-colour Heikin-Ashi bars, capped."""
    open_, high, low, close = (
        np.asarray(v, dtype=np.float64) for v in (open_, high, low, close)
    )
    out = np.zeros(close.size)
    ha_open = (open_[0] + close[0]) / 2.0
    prev_close = 0.0
    run = 0.0
    for i in range(close.size):
        ha_close = (open_[i] + high[i] + low[i] + close[i]) / 4.0
        if i:
            ha_open = (ha_open + prev_close) / 2.0
        colour = 1.0 if ha_close > ha_open else -1.0 if ha_close < ha_open else 0.0
        run = 0.0 if colour == 0 else (run + colour if run * colour > 0 else colour)
        out[i] = max(-cap, min(cap, run))
        prev_close = ha_close
    return out


def ribbon(close, spans=(5, 10, 20, 40)):
    """Share of adjacent EMA pairs stacked bullish minus bearish, in [-1, 1]."""
    lines = [ema(close, s) for s in spans]
    score = np.zeros(len(close))
    for a, b in itertools.pairwise(lines):
        score += np.sign(a - b)
    score /= len(spans) - 1
    score[np.isnan(lines[-1])] = np.nan
    return score


def breakout(high, low, close, window: int):
    """+1 when the close exceeds the prior window's high, -1 below its low."""
    high, low, close = (np.asarray(v, dtype=np.float64) for v in (high, low, close))
    out = np.full(close.size, np.nan)
    if close.size > window:
        hi = rolling_max(high, window)[:-1]
        lo = rolling_min(low, window)[:-1]
        c = close[1:]
        v = np.where(c > hi, 1.0, np.where(c < lo, -1.0, 0.0))
        v[np.isnan(hi)] = np.nan
        out[1:] = v
    return out


def two_bar(time_s, open_, close, step: int):
    """Repository two-bar reversal on epoch-aligned ``step``-second bars.

    Two completed down bars read +1 (watch up), two up bars -1; anything else 0.
    The value at second t uses only buckets whose last second is at or before t.
    The segment is contiguous, so a bucket is complete when all of its seconds
    lie inside the segment.
    """
    time_s = np.asarray(time_s, dtype=np.int64)
    open_, close = (
        np.asarray(open_, dtype=np.float64),
        np.asarray(close, dtype=np.float64),
    )
    n = close.size
    out = np.full(n, np.nan)
    if n == 0:
        return out
    t0 = int(time_s[0])
    colours = {}
    first = -(-t0 // step)
    last = (int(time_s[-1]) + 1) // step - 1
    for k in range(first, last + 1):
        d = close[k * step + step - 1 - t0] - open_[k * step - t0]
        colours[k] = 1 if d > 0 else -1 if d < 0 else 0
    for i in range(n):
        s = int(time_s[i])
        done = s // step if s % step == step - 1 else s // step - 1
        a, b = colours.get(done - 1), colours.get(done)
        if a is None or b is None:
            continue
        out[i] = 1.0 if (a < 0 and b < 0) else -1.0 if (a > 0 and b > 0) else 0.0
    return out


def realized_vol_bps(close, window: int):
    """Sample standard deviation of 1s log returns over the window, in bps."""
    close = np.asarray(close, dtype=np.float64)
    r = np.r_[np.nan, np.diff(np.log(close))] * 1e4
    out = np.full(close.size, np.nan)
    if close.size > window:
        out[window:] = np.lib.stride_tricks.sliding_window_view(r[1:], window).std(
            axis=1, ddof=1
        )
    return out


def feature_table(seg) -> dict:
    """All candidate features for one segment, keyed by name."""
    o, h, lo, c, t = seg["open"], seg["high"], seg["low"], seg["close"], seg["time"]
    f = {}
    for n in (1, 2, 3, 5, 10, 20, 30, 60, 120, 300):
        f[f"roc_{n}"] = roc_bps(c, n)
    for a, b in ((3, 10), (5, 20), (10, 30), (20, 60), (30, 120), (60, 300)):
        f[f"emax_{a}_{b}"] = ema_cross_bps(c, a, b)
    for k in (1, 2, 5):
        f[f"macdh_{k}"] = macd_hist_bps(c, 12 * k, 26 * k, 9 * k)
    for w in (15, 30, 60, 120):
        f[f"slope_{w}"] = slope_t(c, w)
    for w in SLOPE_WINDOWS:
        f[f"lsl_{w}"] = slope_bps(c, w)
        f[f"acc_{w}"] = curvature_bps(c, w)
    for w in (20, 60, 120, 300):
        f[f"don_{w}"] = donchian_pos(h, lo, c, w)
        f[f"z_{w}"] = zscore(c, w)
        f[f"brk_{w}"] = breakout(h, lo, c, w)
    for n in (7, 14, 30, 60):
        f[f"rsi_{n}"] = rsi_centered(c, n)
    for n in (14, 30, 60):
        f[f"di_{n}"] = di_diff(h, lo, c, n)
    for w in (10, 30, 60):
        f[f"er_{w}"] = efficiency_ratio(c, w)
    for n in (5, 15, 30):
        f[f"bop_{n}"] = bop_sma(o, h, lo, c, n)
    for n in (20, 60):
        f[f"kelt_{n}"] = keltner_pos(h, lo, c, n)
    f["psar"] = psar_dir(h, lo, c)
    for n in (10, 30):
        f[f"super_{n}"] = supertrend_dir(h, lo, c, n)
    for bps in (1, 2, 5):
        d, e, a = zigzag_leg(c, bps)
        f[f"zzdir_{bps}"], f[f"zzext_{bps}"] = d, e
    f["ha"] = heikin_ashi_streak(o, h, lo, c)
    f["ribbon"] = ribbon(c)
    for s in (5, 10, 30):
        f[f"twobar_{s}"] = two_bar(t, o, c, s)
    for w in (30, 120, 300):
        f[f"rv_{w}"] = realized_vol_bps(c, w)
    return f


FAMILIES = {
    "Momentum (rate of change)": "roc_",
    "EMA cross": "emax_",
    "MACD histogram": "macdh_",
    "Regression slope": "slope_",
    "Slope ladder": "lsl_",
    "Slope change (2nd derivative)": "acc_",
    "Donchian position": "don_",
    "Z-score": "z_",
    "Breakout": "brk_",
    "RSI": "rsi_",
    "Directional movement": "di_",
    "Efficiency ratio": "er_",
    "Balance of power": "bop_",
    "Keltner position": "kelt_",
    "Parabolic SAR": "psar",
    "Supertrend": "super_",
    "ZigZag leg": "zzdir_",
    "ZigZag extension": "zzext_",
    "Heikin-Ashi streak": "ha",
    "EMA ribbon": "ribbon",
    "Two-bar reversal": "twobar_",
}


# ---------------------------------------------------------------------------
# The Experiments tab's grid: every setting it keeps testing, defined once here
# and exported to the extension by the study. `kind` selects the reader on both
# sides; `params` are that reader's arguments. Horizons are seconds ahead.
EXPERIMENT_HORIZONS = (3, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300)


def _variant(kind, label, need, **params):
    tag = "_".join(str(v).replace(".", "p") for v in params.values())
    return {
        "id": f"{kind}_{tag}" if tag else kind,
        "kind": kind,
        "label": label,
        "need": need,
        "params": params,
    }


# Readings with more than one parameter get a grid over all of them: these are the
# ones where a single hand-picked setting says least about the family.
MACD_SIGNALS = (5, 9, 13)
MACD_PAIRS = tuple(
    (fast, slow)
    for fast in (3, 5, 8, 12, 16, 20)
    for slow in (10, 13, 17, 21, 26, 34, 45, 60, 90)
    if slow > 1.6 * fast
)
EMA_PAIRS = tuple(
    (fast, slow)
    for fast in (2, 3, 5, 8, 10, 13, 20, 30)
    for slow in (5, 8, 10, 13, 20, 30, 45, 60, 90, 120)
    if slow >= 2 * fast
)
SAR_GRID = tuple(
    (start, step, cap)
    for start in (0.005, 0.01, 0.02, 0.05)
    for step in (0.005, 0.01, 0.02, 0.05)
    for cap in (0.1, 0.2, 0.4)
)
SUPERTREND_GRID = tuple(
    (n, mult) for n in (5, 7, 10, 14, 20, 30, 45, 60) for mult in (1, 1.5, 2, 3, 4)
)

VARIANTS = (
    *[
        _variant("roc", f"Momentum {n}s", n + 1, n=n)
        for n in (
            1,
            2,
            3,
            4,
            5,
            6,
            8,
            10,
            13,
            16,
            21,
            26,
            34,
            45,
            60,
            75,
            90,
            120,
            180,
            300,
        )
    ],
    *[
        _variant("breakout", f"Breakout {w}s", w + 1, w=w)
        for w in (5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 300, 450, 600)
    ],
    _variant("heikin", "Heikin-Ashi run", 60),
    *[
        _variant("bop", f"Balance of power {n}s", n, n=n)
        for n in (2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 45, 60)
    ],
    *[
        _variant("zigzag", f"ZigZag {bps} bp", 60, bps=bps)
        for bps in (0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 7.5, 10, 15)
    ],
    *[
        _variant("donchian", f"Range position {w}s", w, w=w)
        for w in (5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300, 600)
    ],
    *[
        _variant("efficiency", f"Efficiency {w}s", w + 1, w=w)
        for w in (5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300)
    ],
    *[
        _variant("slope", f"Slope {w}s", w, w=w)
        for w in (5, 8, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300)
    ],
    *[
        _variant("rsi", f"RSI {n}", max(60, n + 1), n=n)
        for n in (3, 5, 7, 9, 10, 14, 21, 30, 45, 60, 90, 120)
    ],
    *[
        _variant("zscore", f"Z-score {w}", w, w=w)
        for w in (5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300, 600)
    ],
    *[
        _variant(
            "macd",
            f"MACD {f}/{sl}/{sig}",
            EMA_WARMUP_SPANS * sl,
            fast=f,
            slow=sl,
            signal=sig,
        )
        for f, sl in MACD_PAIRS
        for sig in MACD_SIGNALS
    ],
    *[
        _variant("psar", f"SAR {a}/{b}/{c}", 60, start=a, step=b, cap=c)
        for a, b, c in SAR_GRID
    ],
    *[
        _variant("supertrend", f"Supertrend {n}x{m}", max(60, n), n=n, mult=m)
        for n, m in SUPERTREND_GRID
    ],
    *[
        _variant("emacross", f"EMA {f}/{sl}", EMA_WARMUP_SPANS * sl, fast=f, slow=sl)
        for f, sl in EMA_PAIRS
    ],
)
# The variant each grid tile starts on, by tile key.
TILE_VARIANTS = {
    "impulse": "roc_2",
    "momentum5": "roc_5",
    "momentum60": "roc_60",
    "breakout20": "breakout_20",
    "breakout60": "breakout_60",
    "heikin": "heikin",
    "bop": "bop_5",
    "zigzag": "zigzag_1",
    "donchian": "donchian_60",
    "efficiency": "efficiency_60",
    "slope": "slope_60",
    "rsi": "rsi_7",
    "zscore": "zscore_20",
    "macd": "macd_12_26_9",
    "psar": "psar_0p02_0p02_0p2",
    "supertrend": "supertrend_10_3",
}
# Ids a setting had in an earlier grid, so a saved live record follows it to its new name.
VARIANT_ALIASES = {
    "macd_1": "macd_12_26_9",
    "psar_0p02_0p2": "psar_0p02_0p02_0p2",
    "psar_0p01_0p1": "psar_0p01_0p01_0p1",
}


def variant_values(seg, variant):
    """The reading of one experiment variant on a segment; NaN before its `need` bars."""
    o, h, lo, c = seg["open"], seg["high"], seg["low"], seg["close"]
    kind, p = variant["kind"], variant["params"]
    if kind == "roc":
        out = roc_bps(c, p["n"])
    elif kind == "breakout":
        out = breakout(h, lo, c, p["w"])
    elif kind == "heikin":
        out = heikin_ashi_streak(o, h, lo, c)
    elif kind == "bop":
        out = bop_sma(o, h, lo, c, p["n"])
    elif kind == "zigzag":
        out = zigzag_leg(c, p["bps"])[0]
    elif kind == "donchian":
        out = donchian_pos(h, lo, c, p["w"])
    elif kind == "efficiency":
        out = efficiency_ratio(c, p["w"])
    elif kind == "slope":
        out = slope_t(c, p["w"])
    elif kind == "rsi":
        out = rsi_centered(c, p["n"])
    elif kind == "zscore":
        out = zscore(c, p["w"])
    elif kind == "macd":
        out = macd_hist_bps(c, p["fast"], p["slow"], p["signal"])
    elif kind == "psar":
        out = psar_dir(h, lo, c, p["start"], p["step"], p["cap"])
    elif kind == "supertrend":
        out = supertrend_dir(h, lo, c, p["n"], p["mult"])
    elif kind == "emacross":
        out = ema_cross_bps(c, p["fast"], p["slow"])
    else:
        raise ValueError(f"unknown variant kind {kind}")
    out = np.array(out, dtype=np.float64)
    out[: min(out.size, variant["need"] - 1)] = np.nan
    return out
