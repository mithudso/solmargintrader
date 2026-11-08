---
id: tv_ewwysggk_smooth_theil_sen
name: "Smooth Theil-Sen"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Smooth Theil-Sen; not a tested trading strategy."
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
# Smooth Theil-Sen

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> I wanted to build a Theil-Sen estimator that could run on more than one bar and produce smoother output than the standard implementation. Theil-Sen regression is a non-parametric method that calculates the median slope between all pairs of points in your dataset, which makes it extremely robust to outliers. The problem is that median operations produce discrete jumps, especially when you're working with limited sample sizes. Every time the median shifts from one value to another, you get a step change in your regression line, which creates visual choppiness that can be distracting even though

> There are variance tradeoffs with this approach since you're no longer using the pure median, but they're minimal in practice. The kernel weighting stays concentrated enough around the center that you retain most of the outlier resistance that makes Theil-Sen useful in the first place. What you gain is a regression line that updates smoothly instead of jumping discretely, which makes it easier to spot genuine trend changes versus just the statistical noise of median recalculation. The smoothness is particularly noticeable when you're running the estimator over longer lookback periods where the

> Running Theil-Sen on multiple bars means calculating slopes between all pairs of points across your lookback window, sorting those slopes, and then applying the Gaussian kernel to find the weighted center of that sorted distribution. This is computationally more expensive than simple moving averages or even standard linear regression, but Pine Script handles it well enough for reasonable lookback lengths. The benefit is that you get a trend estimate that doesn't get thrown off by individual spikes or anomalies in your price data, which is valuable when working with noisy instruments or during

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

- https://www.tradingview.com/script/ewWysgGk-Smooth-Theil-Sen/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
