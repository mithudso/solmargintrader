"""Deflated Sharpe Ratio: the haircut a Sharpe owes to the size of the search.

PBO answers "is this leaderboard informative?" The Deflated Sharpe Ratio answers a
different question that PBO leaves open: **given that N configurations were tried, how
much of this particular Sharpe is simply the expected maximum of N draws?**

Comparing a best-of-N Sharpe against zero is the mistake. Under the null of no skill,
the *maximum* of N trial Sharpes is well above zero and grows with N: at N=1,000 with
unit cross-sectional variance the expected maximum is ≈3.26 even when every strategy's
true Sharpe is zero. So the benchmark to beat is that expected maximum, not zero.

Method: Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection
Bias, Backtest Overfitting and Non-Normality". Two pieces:

    SR_0 = E[max SR_n] ≈ E[SR_n] + sqrt(V[SR_n]) * ( (1-γ)·Z⁻¹[1 - 1/N]
                                                     + γ·Z⁻¹[1 - 1/(N·e)] )

    DSR  = PSR(SR_0)   = Z[ (SR - SR_0)·sqrt(T-1)
                            / sqrt(1 - γ₃·SR + ((γ₄-1)/4)·SR²) ]

with γ the Euler–Mascheroni constant, Z the standard normal CDF, Z⁻¹ its inverse, γ₃
the skewness and γ₄ the **non-excess** kurtosis of the returns (3 for a normal), and T
the number of return observations.

**Verified against the paper's own worked figure** before this was written: N=1,000 with
unit variance and zero mean gives 3.2551, and the paper states 3.26. That check lives in
`tests/test_deflated_sharpe.py` so the formula cannot drift silently.

Two traps this module refuses to let you walk into:

1. **Sharpe must be per-observation, not annualized.** The `sqrt(T-1)` scaling assumes
   it. Passing an annualized Sharpe with T bars inflates the DSR badly. Use
   `deannualise()`, and keep `SR` and `V[SR_n]` in the same units.
2. **N counts *independent* trials.** Two registry entries computing one rule are one
   trial wearing two names, so a raw configuration count overstates N and therefore
   *understates* the haircut. This repository has a proven case: `bb_reversion` is
   `zscore` up to a ddof convention, identical on all 1,875 BTC daily bars — see
   `tests/test_strategy_duplication.py`. `effective_trials()` exists to make that
   discount explicit rather than silent.

No scipy: `statistics.NormalDist` supplies both the CDF and its inverse, which keeps
this file inside the project's stdlib-first dependency rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Sequence

import numpy as np

# Euler–Mascheroni constant, to double precision.
EULER_MASCHERONI = 0.5772156649015329

_NORMAL = NormalDist()


class DeflatedSharpeError(ValueError):
    """Raised when an input cannot produce a meaningful deflated Sharpe."""


@dataclass(frozen=True)
class DsrResult:
    """A deflated Sharpe and every intermediate a reader needs to check it."""

    sharpe: float               # observed, per-observation
    benchmark_sharpe: float     # SR_0, the expected maximum under the null
    deflated_sharpe: float      # DSR in [0, 1]: P(true Sharpe > 0 | the search)
    n_trials: float
    n_obs: int
    trial_sharpe_variance: float
    skew: float
    kurtosis: float

    @property
    def survives(self) -> bool:
        """Whether the observed Sharpe clears the expected maximum at all.

        A DSR below 0.5 means the observed Sharpe did not even reach the benchmark
        the search alone would have produced.
        """
        return self.sharpe > self.benchmark_sharpe

    @property
    def haircut(self) -> float:
        """How much Sharpe the multiple-testing benchmark consumes."""
        return self.benchmark_sharpe

    def to_dict(self) -> dict[str, float]:
        return {
            "sharpe": self.sharpe,
            "benchmark_sharpe": self.benchmark_sharpe,
            "deflated_sharpe": self.deflated_sharpe,
            "n_trials": self.n_trials,
            "n_obs": self.n_obs,
            "trial_sharpe_variance": self.trial_sharpe_variance,
            "skew": self.skew,
            "kurtosis": self.kurtosis,
            "survives": self.survives,
        }


def deannualise(annual_sharpe: float, periods_per_year: float) -> float:
    """Convert an annualized Sharpe to the per-observation Sharpe the DSR needs."""
    if not math.isfinite(annual_sharpe):
        raise DeflatedSharpeError(f"annual_sharpe must be finite, got {annual_sharpe!r}")
    if not periods_per_year > 0:
        raise DeflatedSharpeError(f"periods_per_year must be > 0, got {periods_per_year!r}")
    return annual_sharpe / math.sqrt(periods_per_year)


def expected_max_sharpe(
    n_trials: float, trial_variance: float, trial_mean: float = 0.0
) -> float:
    """`SR_0`: the Sharpe the best of `n_trials` is expected to post under the null.

    `trial_variance` is the **cross-sectional** variance of the trial Sharpes, in the
    same units as the Sharpe you will compare against it. `trial_mean` defaults to 0,
    which is the null of no skill anywhere in the search.

    Requires `n_trials >= 2`: at N=1 the inverse normal CDF is evaluated at 0 and the
    expected maximum of one draw is not a multiple-testing correction at all.
    """
    if not math.isfinite(n_trials) or n_trials < 2:
        raise DeflatedSharpeError(
            f"n_trials must be a finite number >= 2, got {n_trials!r}; "
            "a single trial carries no selection bias to correct"
        )
    if not math.isfinite(trial_variance) or trial_variance < 0:
        raise DeflatedSharpeError(f"trial_variance must be finite and >= 0, got {trial_variance!r}")
    if not math.isfinite(trial_mean):
        raise DeflatedSharpeError(f"trial_mean must be finite, got {trial_mean!r}")

    g = EULER_MASCHERONI
    hi = _NORMAL.inv_cdf(1.0 - 1.0 / n_trials)
    lo = _NORMAL.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return trial_mean + math.sqrt(trial_variance) * ((1.0 - g) * hi + g * lo)


def probabilistic_sharpe_ratio(
    sharpe: float,
    n_obs: int,
    *,
    benchmark: float = 0.0,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """`PSR(benchmark)`: P(true Sharpe > benchmark), given skew, kurtosis and length.

    `sharpe` and `benchmark` must both be **per-observation**. `kurtosis` is the
    non-excess kurtosis (3 for a normal distribution), matching the paper.

    With `skew=0, kurtosis=3` the denominator reduces to `sqrt(1 + SR²/2)`, which is
    Lo's (2002) standard error for the Sharpe ratio — a useful sanity anchor.
    """
    if n_obs < 2:
        raise DeflatedSharpeError(f"n_obs must be >= 2 to estimate a standard error, got {n_obs}")
    for name, value in (("sharpe", sharpe), ("benchmark", benchmark), ("skew", skew),
                        ("kurtosis", kurtosis)):
        if not math.isfinite(value):
            raise DeflatedSharpeError(f"{name} must be finite, got {value!r}")

    variance = 1.0 - skew * sharpe + ((kurtosis - 1.0) / 4.0) * sharpe**2
    if variance <= 0:
        # Possible with a strongly skewed, low-kurtosis input; refusing beats
        # returning a probability derived from a negative variance.
        raise DeflatedSharpeError(
            f"implied Sharpe variance is not positive ({variance:.6g}); "
            f"skew={skew!r}, kurtosis={kurtosis!r}, sharpe={sharpe!r} are jointly unusable"
        )
    return _NORMAL.cdf((sharpe - benchmark) * math.sqrt(n_obs - 1) / math.sqrt(variance))


def deflated_sharpe_ratio(
    sharpe: float,
    n_obs: int,
    n_trials: float,
    trial_variance: float,
    *,
    trial_mean: float = 0.0,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> DsrResult:
    """The Deflated Sharpe Ratio: a PSR whose benchmark is the expected maximum.

    All Sharpe quantities must be **per-observation** and in the same units.
    """
    benchmark = expected_max_sharpe(n_trials, trial_variance, trial_mean)
    dsr = probabilistic_sharpe_ratio(
        sharpe, n_obs, benchmark=benchmark, skew=skew, kurtosis=kurtosis
    )
    return DsrResult(
        sharpe=sharpe,
        benchmark_sharpe=benchmark,
        deflated_sharpe=dsr,
        n_trials=n_trials,
        n_obs=n_obs,
        trial_sharpe_variance=trial_variance,
        skew=skew,
        kurtosis=kurtosis,
    )


def effective_trials(n_configs: int, duplicate_groups: Sequence[int] = ()) -> float:
    """Discount a raw configuration count for known duplicate hypotheses.

    `duplicate_groups` gives the size of each group of configurations that compute the
    same rule; a group of `k` contributes 1 independent trial, not `k`. So 25 configs
    with one proven duplicate pair is 24 effective trials.

    This is a **floor on the correction, not a full independence adjustment.** Highly
    correlated but non-identical strategies still inflate N, and nothing here measures
    pairwise correlation. Reporting a smaller N understates the haircut, so it is the
    conservative direction to leave un-modelled.
    """
    if n_configs < 1:
        raise DeflatedSharpeError(f"n_configs must be >= 1, got {n_configs}")
    removed = 0
    for k in duplicate_groups:
        if k < 2:
            raise DeflatedSharpeError(f"a duplicate group must contain >= 2 members, got {k}")
        removed += k - 1
    if removed >= n_configs:
        raise DeflatedSharpeError(
            f"duplicate groups remove {removed} of {n_configs} configurations, "
            "leaving nothing to correct"
        )
    return float(n_configs - removed)


def trial_sharpe_variance(sharpes: Sequence[float] | np.ndarray) -> float:
    """Cross-sectional variance of the trial Sharpes, ignoring non-finite entries.

    Sample variance (ddof=1): these are a sample of the trials that were run.
    """
    arr = np.asarray(list(sharpes), dtype="float64")
    finite = arr[np.isfinite(arr)]
    if finite.size < 2:
        raise DeflatedSharpeError(
            f"need >= 2 finite trial Sharpes to estimate their variance, got {finite.size}"
        )
    return float(np.var(finite, ddof=1))
