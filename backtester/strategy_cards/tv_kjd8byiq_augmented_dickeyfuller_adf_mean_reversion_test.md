---
id: tv_kjd8byiq_augmented_dickeyfuller_adf_mean_reversion_test
name: "Augmented Dickey–Fuller (ADF) mean reversion test"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Augmented Dickey–Fuller (ADF) mean reversion test; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-macro-and-derivatives-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Augmented Dickey–Fuller (ADF) mean reversion test

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The augmented Dickey-Fuller test (ADF) is a statistical test for the tendency of a price series sample to mean revert.

> Mathematically, the mean reversion property means that the price change in the next time period is proportional to the difference between the average price and the current price. The purpose of the ADF test is to check if this proportionality constant is zero. Accordingly, the ADF test statistic is defined as the estimated proportionality constant divided by the corresponding standard error.

> In this script, the ADF test is applied in a rolling window with a user-defined lookback length. The calculated values ​​of the ADF test statistic are plotted as a time series. The more negative the test statistic, the stronger the rejection of the hypothesis that there is no mean reversion. If the calculated test statistic is less than the critical value calculated at a certain confidence level (90%, 95%, or 99%), then the hypothesis of a mean reversion is accepted (strictly speaking, the opposite hypothesis is rejected).

> Length - The number of points in the rolling lookback window. The larger sample length makes the ADF test results more reliable.

> The VIX volatility index is known to exhibit mean reversion properties (volatility spikes tend to fade out quickly). Accordingly, the statistics of the ADF test tend to stay below the critical value of 90% for long time periods.

> It should be noted that the ADF test tells us only about the properties of the price series now and in the past. It does not directly say whether the mean-reverting behavior will retain in the future.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_vix_timing`.

## Data and availability

Required inputs: ohlcv, point-in-time-macro-and-derivatives-history.
The complete point-in-time input set has not been verified in the repository. Do not substitute current snapshots or inferred values for historical inputs.

## Implementation and validation

No runner or registry key is assigned. Before implementation, freeze the numerical
formula, seeds, missing-value policy, warm-up and parameter domains. Where the source
does not disclose an algorithm or default, recover it rather than guessing. Specify
entry, exit, stop, holding horizon, exposure and costs separately from the indicator.
Record which choices come from the publication and which define a new experiment.

Compute with closed bars and trailing data only. Confirm pivots and higher-timeframe
values before use; never backdate a signal to a pivot that needed later bars. Test
prefix invariance, flat/zero inputs, unavailable data and one-bar-delayed execution.
Evaluate chronologically out of sample, deduct transaction and financing costs and compare with
buy-and-hold and simpler component rules. Record all searched configurations.

## Failure modes and caveats

An author description is not source code or independent validation. Visual styling,
retrospective drawing anchors, repainting pivots and fitted full-history models can
produce unavailable historical signals. A rule can be numerically correct and lose
after costs. Venue, session, data and asset differences limit transfer to SOL.

## Measured results

Not measured in this repository. Publication examples, advertised accuracy and
screenshots are not repository backtest results.

## Likelihood of success: low

Basis: a-priori. The mechanism has no confirming out-of-sample result here. This rating
does not promote the source author's claims into evidence of profitability.

## Sources

- https://www.tradingview.com/script/KjD8ByIQ-Augmented-Dickey-Fuller-ADF-mean-reversion-test/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
