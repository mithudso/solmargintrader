---
id: tv_mheetfmn_a_useful_ma_weighting_function_for_controlling_lag_smoothness
name: "A Useful MA Weighting Function For Controlling Lag & Smoothness"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of A Useful MA Weighting Function For Controlling Lag & Smoothness; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# A Useful MA Weighting Function For Controlling Lag & Smoothness

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> So far the most widely used moving average with an adjustable weighting function is the Arnaud Legoux moving average (ALMA), who uses a Gaussian function as weighting function. Adjustable weighting functions are useful since they allow us to control characteristics of the moving average such as lag and smoothness.

> The weighting function of this moving average is derived from the calculation of the beta distribution, advantages of such distribution is that unlike a lot of PDF, the beta distribution is defined within a specific range of values (0,1). Parameters alpha and beta controls the shape of the distribution, with alpha introducing negative skewness and beta introducing positive skewness, while higher values of alpha and beta increase kurtosis.

> Here -Lag is directly associated to beta while +Lag is associated with alpha. When alpha = beta = 1 the distribution is uniform, and as such can be used to compute a simple moving average.

> Here -Lag = +Lag = 3, note that when the impulse response of a moving average is symmetrical its lag is equal to (length-1)/2.

> As for the gradient, the color is determined by the value of an RSI using the moving average as input.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv.
The repository supports OHLCV history. Verify symbol, cadence, timezone and complete bars for the chosen experiment; this is not a claim that every source market is cached.

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

- https://www.tradingview.com/script/mheEtfmN-A-Useful-MA-Weighting-Function-For-Controlling-Lag-Smoothness/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
