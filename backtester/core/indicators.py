"""Trailing-window indicator functions.

Every function here takes an array that the caller has ALREADY truncated to
bars <= now (a `BarWindow` accessor does this by construction) and returns the
value for the latest bar. None of them can see the future, because none of them
are ever handed it.

Two conventions worth knowing:

  * Each returns a scalar for the current bar, not a series. Strategies are
    called once per bar, so a series would be wasted work and would invite
    accidental indexing into a position other than the last.
  * Exponential recursions (EMA, Wilder ATR/RSI) are computed over a **capped**
    lookback of `cap_multiple * span` bars rather than all history, making them
    O(span) per bar instead of O(n). Measured relative error against the
    uncapped recursion, span=20 over 2,000 bars:

        cap  3 -> 1.4e-04      cap  8 -> 1.8e-09
        cap  5 -> 7.2e-07      cap 12 -> 2.4e-13

    `EMA_CAP_MULTIPLE = 12` is the default because 2.4e-13 is close enough to
    double-precision epsilon to be irrelevant to any backtest metric, and the
    cost is ~240 float ops per bar.
"""

from __future__ import annotations

import math

import numpy as np

# Multiple of `span` retained when evaluating an exponential recursion. Chosen
# for accuracy (see module docstring); costs O(cap * span) per bar.
EMA_CAP_MULTIPLE = 12

# Multiple of `span` a strategy should demand as WARM-UP before trading. This is
# deliberately smaller than the accuracy cap: warm-up only needs the indicator
# to be defined and converged enough to act on (worst case ~1e-4 relative on the
# very first tradeable bar, tightening immediately), whereas the cap governs
# steady-state precision. Tying warm-up to the accuracy cap would cost a
# Keltner strategy ~240 bars of tradeable history to buy precision it does not
# need on bar one.
EMA_WARMUP_MULTIPLE = 3


def sma(values: np.ndarray, window: int) -> float:
    """Simple moving average of the last `window` values."""
    if len(values) < window or window < 1:
        return float("nan")
    return float(np.mean(values[-window:]))


def ema(values: np.ndarray, span: int, cap_multiple: int = EMA_CAP_MULTIPLE) -> float:
    """Exponential moving average for the latest bar.

    Uses alpha = 2/(span+1), the standard "span" convention, seeded by the SMA
    of the oldest retained window so the recursion starts from a sane value.
    """
    if span < 1 or len(values) < span:
        return float("nan")
    keep = min(len(values), max(span * cap_multiple, span + 1))
    v = values[-keep:]
    alpha = 2.0 / (span + 1.0)
    out = float(np.mean(v[:span]))
    for x in v[span:]:
        out = alpha * float(x) + (1.0 - alpha) * out
    return out


def ema_series(
    values: np.ndarray, span: int, count: int, cap_multiple: int = EMA_CAP_MULTIPLE
) -> np.ndarray:
    """The last `count` EMA values, computed in ONE recursion.

    Calling `ema()` in a loop to obtain a short history is O(count * cap * span);
    this is O(cap * span + count). MACD needs a history of its own line to seed
    the signal EMA, so without this the indicator is quadratic in the cap and
    dominates the whole sweep's runtime.
    """
    if span < 1 or count < 1 or len(values) < span + count - 1:
        return np.zeros(0, dtype="float64")
    keep = min(len(values), max(span * cap_multiple, span + 1) + count)
    v = values[-keep:]
    alpha = 2.0 / (span + 1.0)
    cur = float(np.mean(v[:span]))
    out = np.empty(len(v) - span + 1, dtype="float64")
    out[0] = cur
    for k, x in enumerate(v[span:], start=1):
        cur = alpha * float(x) + (1.0 - alpha) * cur
        out[k] = cur
    return out[-count:]


def wilder_smooth(values: np.ndarray, period: int) -> float:
    """Wilder's smoothing (alpha = 1/period), seeded by the first SMA."""
    if period < 1 or len(values) < period:
        return float("nan")
    keep = min(len(values), max(period * EMA_CAP_MULTIPLE, period + 1))
    v = values[-keep:]
    out = float(np.mean(v[:period]))
    for x in v[period:]:
        out = (out * (period - 1) + float(x)) / period
    return out


def rsi(closes: np.ndarray, period: int = 14) -> float:
    """Wilder's RSI in [0, 100]. Returns 50.0 (neutral) without enough history."""
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = wilder_smooth(gains, period)
    avg_loss = wilder_smooth(losses, period)
    if not np.isfinite(avg_gain) or not np.isfinite(avg_loss):
        return 50.0
    if avg_loss <= 1e-15:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return float(100.0 - 100.0 / (1.0 + rs))


def macd(
    closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float, float]:
    """(macd_line, signal_line, histogram) for the latest bar.

    The signal line is an EMA *of the MACD line*, so it needs a short series of
    historical MACD values; those are rebuilt from the trailing window.
    """
    if len(closes) < slow + signal:
        return (float("nan"), float("nan"), float("nan"))
    # Rebuild a short history of the MACD line to seed its signal EMA. Both
    # component EMAs come from one recursion each (see ema_series), so this is
    # linear in the cap rather than quadratic.
    n_hist = min(len(closes) - slow, signal * EMA_CAP_MULTIPLE)
    fast_hist = ema_series(closes, fast, n_hist)
    slow_hist = ema_series(closes, slow, n_hist)
    if fast_hist.size != n_hist or slow_hist.size != n_hist:
        return (float("nan"), float("nan"), float("nan"))
    line_hist = fast_hist - slow_hist
    line = float(line_hist[-1])
    sig = ema(line_hist, signal)
    if not np.isfinite(sig):
        sig = float(np.mean(line_hist))
    return (line, float(sig), line - float(sig))


def bollinger(
    closes: np.ndarray, window: int = 20, num_std: float = 2.0
) -> tuple[float, float, float, float]:
    """(mid, upper, lower, bandwidth) for the latest bar.

    `bandwidth = (upper - lower) / mid` is the squeeze measure. Uses the
    population standard deviation (ddof=0), which is the convention Bollinger
    specified and what charting packages display.
    """
    if len(closes) < window:
        return (float("nan"),) * 4
    w = closes[-window:]
    mid = float(np.mean(w))
    sd = float(np.std(w, ddof=0))
    upper, lower = mid + num_std * sd, mid - num_std * sd
    bw = (upper - lower) / mid if mid > 0 else float("nan")
    return (mid, upper, lower, bw)


def true_range(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
    """True range series: max(H-L, |H-prevC|, |L-prevC|). Length n-1."""
    if len(closes) < 2:
        return np.zeros(0, dtype="float64")
    prev_close = closes[:-1]
    h, l = highs[1:], lows[1:]
    return np.maximum(
        h - l, np.maximum(np.abs(h - prev_close), np.abs(l - prev_close))
    )


def atr(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> float:
    """Average True Range (Wilder) for the latest bar."""
    tr = true_range(highs, lows, closes)
    if len(tr) < period:
        return float("nan")
    return wilder_smooth(tr, period)


def stochastic(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[float, float]:
    """(%K, %D) for the latest bar. %D is the SMA of the last d_period %K values."""
    if len(closes) < k_period + d_period:
        return (float("nan"), float("nan"))
    ks = np.empty(d_period, dtype="float64")
    for j in range(d_period):
        end = len(closes) - d_period + j + 1
        hh = float(np.max(highs[end - k_period : end]))
        ll = float(np.min(lows[end - k_period : end]))
        rng = hh - ll
        ks[j] = 50.0 if rng <= 1e-15 else (closes[end - 1] - ll) / rng * 100.0
    return (float(ks[-1]), float(np.mean(ks)))


def obv(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """On-Balance Volume series: cumulative signed volume."""
    if len(closes) < 2:
        return np.zeros(len(closes), dtype="float64")
    direction = np.sign(np.diff(closes))
    signed = direction * volumes[1:]
    return np.concatenate([[0.0], np.cumsum(signed)])


def rolling_vwap(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
    volumes: np.ndarray, window: int = 20,
) -> float:
    """Volume-weighted average typical price over the last `window` bars.

    Typical price is (H+L+C)/3, the standard VWAP input. Falls back to the
    unweighted mean when the window has no volume, which happens on synthetic
    or illiquid series and would otherwise divide by zero.
    """
    if len(closes) < window:
        return float("nan")
    tp = (highs[-window:] + lows[-window:] + closes[-window:]) / 3.0
    v = volumes[-window:]
    total = float(np.sum(v))
    if total <= 1e-15:
        return float(np.mean(tp))
    return float(np.sum(tp * v) / total)


def zscore(values: np.ndarray, window: int = 20) -> float:
    """Z-score of the latest value against its trailing window.

    Sample stdev (ddof=1). Returns 0.0 on a degenerate (zero-dispersion)
    window rather than dividing by ~0 and emitting a huge spurious score.
    """
    if len(values) < window or window < 2:
        return float("nan")
    w = values[-window:]
    sd = float(np.std(w, ddof=1))
    if sd <= 1e-15:
        return 0.0
    return float((w[-1] - np.mean(w)) / sd)


def roc(closes: np.ndarray, window: int = 20) -> float:
    """Rate of change over `window` bars, as a decimal fraction."""
    if len(closes) < window + 1:
        return float("nan")
    past = float(closes[-window - 1])
    if past <= 0:
        return float("nan")
    return float(closes[-1]) / past - 1.0


def rolling_realised_vol(
    closes: np.ndarray, window: int = 20, periods_per_year: float = 365.0
) -> np.ndarray:
    """Realised vol at EVERY bar that has enough history, in one vectorised pass.

    Equivalent to calling `realised_vol(closes[:i+1], window)` for each i, but
    O(n) numpy work instead of O(n) separate numpy calls.

    This exists because a strategy that needs the trailing *distribution* of
    realised vol (to take a quantile of it) was rebuilding ~230 values per bar
    with a Python loop -- roughly 2M numpy calls over 8,823 hourly bars, which
    measured at 16s per backtest against 0.1s for its peers and dominated the
    whole sweep. Same numbers, ~100x less time.

    Returns an array aligned so that element k corresponds to
    `closes[: window + 1 + k]`; it is shorter than `closes` by `window`.
    """
    closes = np.asarray(closes, dtype="float64")
    if len(closes) < window + 1 or window < 2:
        return np.zeros(0, dtype="float64")
    logret = np.diff(np.log(closes))
    # Sliding windows of `window` consecutive log returns.
    views = np.lib.stride_tricks.sliding_window_view(logret, window)
    return views.std(axis=1, ddof=1) * np.sqrt(periods_per_year)


def realised_vol(closes: np.ndarray, window: int = 20, periods_per_year: float = 365.0) -> float:
    """Annualised realised volatility from log returns over `window` bars."""
    if len(closes) < window + 1:
        return float("nan")
    w = closes[-window - 1 :]
    logret = np.diff(np.log(w))
    sd = float(np.std(logret, ddof=1)) if len(logret) > 1 else 0.0
    return sd * np.sqrt(periods_per_year)


def directional_movement(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> tuple[float, float, float]:
    """Wilder's (+DI, -DI, ADX) for the latest bar.

    ADX measures trend *strength* without direction, which is what makes it a
    filter rather than a signal: every trend strategy here fails in chop, and this
    is the conventional measure of whether a trend exists at all.

    Needs `3 * period` bars because ADX is a Wilder smoothing of DX, which is
    itself built from smoothed DM and ATR — three nested recursions deep.
    """
    n = len(closes)
    if n < 3 * period + 1:
        return (float("nan"), float("nan"), float("nan"))

    up_move = highs[1:] - highs[:-1]
    down_move = lows[:-1] - lows[1:]
    # A bar counts toward one direction only: the larger move wins, and a move
    # that is not positive counts as zero rather than negative.
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(highs, lows, closes)

    dx = np.empty(period, dtype="float64")
    for j in range(period):
        end = len(tr) - period + j + 1
        atr_j = wilder_smooth(tr[:end], period)
        if not np.isfinite(atr_j) or atr_j <= 1e-15:
            dx[j] = 0.0
            continue
        pdi = 100.0 * wilder_smooth(plus_dm[:end], period) / atr_j
        mdi = 100.0 * wilder_smooth(minus_dm[:end], period) / atr_j
        total = pdi + mdi
        dx[j] = 0.0 if total <= 1e-15 else 100.0 * abs(pdi - mdi) / total

    atr_now = wilder_smooth(tr, period)
    if not np.isfinite(atr_now) or atr_now <= 1e-15:
        return (float("nan"), float("nan"), float("nan"))
    plus_di = 100.0 * wilder_smooth(plus_dm, period) / atr_now
    minus_di = 100.0 * wilder_smooth(minus_dm, period) / atr_now
    return (float(plus_di), float(minus_di), float(np.mean(dx)))


def variance_ratio(closes: np.ndarray, window: int = 250, lag: int = 5) -> float:
    """Lo-MacKinlay variance ratio on log returns: Var(k-period) / (k * Var(1-period)).

    A random walk gives 1, trending gives > 1, mean-reverting gives < 1. Used in
    preference to a rescaled-range Hurst exponent, which is badly biased on short
    samples — the estimator matters more than the label here.
    """
    if len(closes) < window + 1 or lag < 2:
        return float("nan")
    prices = np.asarray(closes[-(window + 1) :], dtype="float64")
    if np.any(prices <= 0):
        return float("nan")
    rets = np.diff(np.log(prices))
    var_one = float(np.var(rets, ddof=1))
    if var_one <= 1e-18:
        return float("nan")
    # Overlapping k-period sums, which is the standard (and more efficient) form.
    k_sums = np.convolve(rets, np.ones(lag), mode="valid")
    var_k = float(np.var(k_sums, ddof=1))
    return var_k / (lag * var_one)


def hurst_from_variance_ratio(vr: float, lag: int = 5) -> float:
    """Translate a variance ratio into the Hurst-exponent scale readers expect.

    `VR = lag^(2H-1)`, so `H = 0.5 * (1 + log(VR)/log(lag))`. Reported because
    `H < 0.5 / > 0.5` is the vocabulary the literature uses, not because the
    rescaled-range estimator is worth computing.
    """
    if not np.isfinite(vr) or vr <= 0 or lag < 2:
        return float("nan")
    return 0.5 * (1.0 + math.log(vr) / math.log(lag))


def ou_half_life(closes: np.ndarray, window: int = 250) -> float:
    """Half-life of mean reversion in bars, from an AR(1) fit.

    Discretised Ornstein-Uhlenbeck: regress `dX_t` on `X_{t-1}`; the slope is
    `-theta`, and `half_life = ln(2)/theta`. Returns `inf` when the series shows
    no reversion (slope >= 0), which is the honest answer for a trending series
    and the screening rule that should gate any reversion strategy.
    """
    if len(closes) < window + 1:
        return float("nan")
    x = np.asarray(closes[-(window + 1) :], dtype="float64")
    lagged = x[:-1]
    delta = np.diff(x)
    centred = lagged - lagged.mean()
    denom = float(np.dot(centred, centred))
    if denom <= 1e-15:
        return float("inf")
    slope = float(np.dot(centred, delta - delta.mean())) / denom
    if slope >= -1e-12:
        return float("inf")
    return math.log(2.0) / -slope


def ewma_vol(
    closes: np.ndarray, lam: float = 0.94, periods_per_year: float = 365.0
) -> float:
    """Annualised EWMA volatility — the GARCH(1,1) special case with omega=0.

    `sigma2_t = (1-lam) * r2_{t-1} + lam * sigma2_{t-1}`. RiskMetrics' lam=0.94 is
    used rather than fitting alpha and beta, because fitted GARCH parameters are
    unstable on short samples and refitting per bar invites look-ahead.
    """
    if len(closes) < 3 or not 0.0 < lam < 1.0:
        return float("nan")
    prices = np.asarray(closes, dtype="float64")
    if np.any(prices <= 0):
        return float("nan")
    rets = np.diff(np.log(prices))
    var = float(rets[0] ** 2)
    for r in rets[1:]:
        var = (1.0 - lam) * float(r) ** 2 + lam * var
    return math.sqrt(max(var, 0.0)) * math.sqrt(periods_per_year)


def ichimoku(
    highs: np.ndarray,
    lows: np.ndarray,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52,
) -> tuple[float, float, float, float]:
    """(Tenkan, Kijun, SenkouA, SenkouB) computed at the CURRENT bar.

    The cloud is conventionally *plotted* `displacement` bars forward. This
    returns the values as computed now, and it is the caller's job to compare
    them against a later price — never to read a value drawn at the current bar,
    which was computed from future data. That inversion is the classic Ichimoku
    look-ahead trap.
    """
    if len(highs) < senkou_b:
        return (float("nan"),) * 4
    mid = lambda h, l, n: (float(np.max(h[-n:])) + float(np.min(l[-n:]))) / 2.0  # noqa: E731
    t = mid(highs, lows, tenkan)
    k = mid(highs, lows, kijun)
    return (t, k, (t + k) / 2.0, mid(highs, lows, senkou_b))
