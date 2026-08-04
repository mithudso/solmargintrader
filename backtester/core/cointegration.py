"""Engle-Granger cointegration and an Augmented Dickey-Fuller test.

This is the machinery `zscore` should have had. A z-score trade assumes the
series is stationary; raw SOL price is not, so applying it there is a known
theoretical error that no measured result repairs. A **cointegrated spread** is
constructed to be stationary, and — the part that matters — the assumption is
*tested* rather than hoped for.

No `statsmodels`. `requirements.txt` is deliberately minimal, so the OLS is a
closed-form two-parameter fit and the ADF critical values are the standard
MacKinnon table, interpolated by sample size. That is enough to answer the only
question being asked of it: is this residual plausibly stationary at 5%?

**What this does not do.** It fits one beta over one window. A hedge ratio that
drifts needs a state-space model (see `kalman_hedge_ratio.md`), and the
practitioner rule of requiring cointegration across 3-, 6- and 12-month windows
is left to the caller. `adf_pvalue` is an interpolation of a lookup table, not an
exact p-value; treat 0.04 and 0.06 as the same answer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# MacKinnon (1994/2010) critical values for the ADF t-statistic, constant, no
# trend, at the 1%/5%/10% levels. Keyed by sample size; interpolated between.
# The asymptotic row is what large samples converge to.
_ADF_CRITICAL = {
    25: (-3.75, -3.00, -2.63),
    50: (-3.58, -2.93, -2.60),
    100: (-3.51, -2.89, -2.58),
    250: (-3.46, -2.88, -2.57),
    500: (-3.44, -2.87, -2.57),
    100_000: (-3.43, -2.86, -2.57),
}
_ADF_LEVELS = (0.01, 0.05, 0.10)


@dataclass(frozen=True)
class AdfResult:
    """Outcome of an Augmented Dickey-Fuller test on one series."""

    statistic: float
    pvalue: float
    lags: int
    nobs: int
    critical: dict[str, float]

    @property
    def stationary_at_5pct(self) -> bool:
        """True when the unit-root null is rejected at 5%."""
        return self.statistic < self.critical["5%"]


@dataclass(frozen=True)
class CointegrationResult:
    """Engle-Granger two-step outcome for `x ~ beta * y`."""

    beta: float
    intercept: float
    adf: AdfResult
    spread: np.ndarray

    @property
    def cointegrated_at_5pct(self) -> bool:
        """True when the residual is plausibly stationary at 5%."""
        return self.adf.stationary_at_5pct


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Closed-form slope and intercept for `x = slope*y + intercept`."""
    y_mean, x_mean = float(np.mean(y)), float(np.mean(x))
    yc = y - y_mean
    denom = float(np.dot(yc, yc))
    if denom <= 1e-15:
        return (0.0, x_mean)
    slope = float(np.dot(yc, x - x_mean)) / denom
    return (slope, x_mean - slope * y_mean)


def _interp_critical(nobs: int) -> dict[str, float]:
    """Critical values for `nobs`, linearly interpolated across the table."""
    sizes = sorted(_ADF_CRITICAL)
    if nobs <= sizes[0]:
        row = _ADF_CRITICAL[sizes[0]]
    elif nobs >= sizes[-1]:
        row = _ADF_CRITICAL[sizes[-1]]
    else:
        hi = next(s for s in sizes if s >= nobs)
        lo = max(s for s in sizes if s <= nobs)
        if hi == lo:
            row = _ADF_CRITICAL[hi]
        else:
            w = (nobs - lo) / (hi - lo)
            row = tuple(
                _ADF_CRITICAL[lo][i] + w * (_ADF_CRITICAL[hi][i] - _ADF_CRITICAL[lo][i])
                for i in range(3)
            )
    return {"1%": row[0], "5%": row[1], "10%": row[2]}


def adf_pvalue(statistic: float, nobs: int) -> float:
    """Approximate p-value by interpolating the critical-value table.

    Deliberately coarse — clamped to [0.01, 0.99] and flat outside the table's
    range. It answers "is this near the 5% line?" and nothing finer, which is all
    the strategy above it asks.
    """
    crit = _interp_critical(nobs)
    stats = (crit["1%"], crit["5%"], crit["10%"])
    if statistic <= stats[0]:
        return 0.01
    if statistic >= stats[2]:
        # Beyond the 10% value the null is comfortably not rejected; report a
        # value that says so without pretending to precision.
        return min(0.99, 0.10 + (statistic - stats[2]) * 0.10)
    for i in range(2):
        hi_stat, lo_stat = stats[i], stats[i + 1]
        if hi_stat <= statistic <= lo_stat:
            span = lo_stat - hi_stat
            w = 0.0 if span <= 1e-12 else (statistic - hi_stat) / span
            return _ADF_LEVELS[i] + w * (_ADF_LEVELS[i + 1] - _ADF_LEVELS[i])
    return 0.10


def adf_test(series: np.ndarray, lags: int | None = None) -> AdfResult:
    """Augmented Dickey-Fuller test with a constant and no trend.

    Regresses `dy_t` on `y_{t-1}` plus `lags` lagged differences, and reports the
    t-statistic on the `y_{t-1}` coefficient. A sufficiently negative statistic
    rejects the unit-root null, i.e. argues the series is stationary.
    """
    y = np.asarray(series, dtype="float64")
    n = y.size
    if n < 20:
        raise ValueError(f"ADF needs at least 20 observations, got {n}")
    if lags is None:
        # Schwert's rule, the usual default.
        lags = int(math.floor(12 * (n / 100.0) ** 0.25))
        lags = max(0, min(lags, (n - 10) // 4))

    dy = np.diff(y)
    rows = dy.size - lags
    if rows < 10:
        raise ValueError(f"too few usable rows ({rows}) after {lags} lags")

    # Design: [y_{t-1}, 1, dy_{t-1}, ..., dy_{t-lags}]
    cols = [y[lags : lags + rows], np.ones(rows)]
    for k in range(1, lags + 1):
        cols.append(dy[lags - k : lags - k + rows])
    x = np.column_stack(cols)
    target = dy[lags : lags + rows]

    coef, *_ = np.linalg.lstsq(x, target, rcond=None)
    resid = target - x @ coef
    dof = rows - x.shape[1]
    if dof <= 0:
        raise ValueError("ADF regression has no degrees of freedom")
    sigma2 = float(np.dot(resid, resid)) / dof
    try:
        xtx_inv = np.linalg.inv(x.T @ x)
    except np.linalg.LinAlgError as exc:  # pragma: no cover - singular design
        raise ValueError("ADF design matrix is singular") from exc
    se = math.sqrt(max(sigma2 * float(xtx_inv[0, 0]), 0.0))
    stat = float("-inf") if se <= 1e-18 else float(coef[0]) / se

    return AdfResult(
        statistic=stat,
        pvalue=adf_pvalue(stat, rows),
        lags=lags,
        nobs=rows,
        critical=_interp_critical(rows),
    )


def engle_granger(
    x: np.ndarray, y: np.ndarray, lags: int | None = None
) -> CointegrationResult:
    """Two-step Engle-Granger: regress `x` on `y`, then ADF-test the residual.

    Step order matters and is not symmetric — `engle_granger(x, y)` and
    `engle_granger(y, x)` can disagree, which is exactly why Johansen is preferred
    for three or more assets. With two series, pick the dependent variable
    deliberately and say which you picked.
    """
    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    if x.size != y.size:
        raise ValueError(f"series lengths differ: {x.size} vs {y.size}")
    beta, intercept = _ols(x, y)
    spread = x - beta * y - intercept
    return CointegrationResult(
        beta=beta, intercept=intercept, adf=adf_test(spread, lags), spread=spread
    )
