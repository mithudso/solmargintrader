---
id: tv_odyzzlzu_median_convergence_divergence
name: "Median Convergence Divergence"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Median Convergence Divergence; not a tested trading strategy."
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
# Median Convergence Divergence

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Median Convergence Divergence (MCD) is a derivative of the Moving Average Convergence Divergence (MACD). The difference is the change in the use of the measure of central tendency. In MACD, moving average (mean) is used, whereas, in MCD, the median is used instead. The purpose of using the median is to eliminate the outlying values, which would be calculated for a moving average. The outliers would affect the value of the moving average.

> Signal Line Crossovers: When the MCD line crosses above the Signal line, it's a bullish crossover. When the MCD line crosses below the Signal line, it's a bearish crossover.

> Zero Line Crossovers: It's a bullish crossover when the MCD line crosses above the Zero line. When the MCD line crosses below the Zero Line, it's a bearish crossover.

> Using other indicators in conjunction with the Median Convergence Divergence is recommended to take entry and exit signals.

> The current settings are set to be used for the Daily Time Frame: 5 day period for the fast line, a 20 day period for the slow line, and a 10 day period for the signal line. (5 days represent a trading week, 10 days is two weeks, and 20 days is 4 weeks or a month)

> For the weekly charts, use 4 week period for the fast line, 13 week period for the slow line, and 8 week period for the signal line. (4 weeks represent a month, 8 weeks is two months, and 13 weeks is 3 months or quarterly)

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_oscillator_divergence`.

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

- https://www.tradingview.com/script/odyzZlzU-Median-Convergence-Divergence/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
