---
id: tv_fnlmn99w_tasc_2026_09_adaptive_supersmoother
name: "TASC 2026.09 Adaptive SuperSmoother"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2026.09 Adaptive SuperSmoother; not a tested trading strategy."
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
# TASC 2026.09 Adaptive SuperSmoother

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements the Adaptive SuperSmoother by John F. Ehlers, as presented in the "Improved Filter Performance" article from the September 2026 edition of the TASC Traders' Tips. The script demonstrates a simple technique to adapt the SuperSmoother's critical period to improve the filter's responsiveness.

> In his article, Ehlers explains that many adaptive smoothers rely on Exponential Moving Averages (EMAs) at their core. Typically, these smoothers dynamically adjust an EMA's smoothing factor (alpha) based on specific volatility measures, often to reduce sensitivity during periods of volatile or choppy price movements. However, he suggests that EMAs are not great filters; they are first-order smoothers that offer very limited reduction, or attenuation, of high-frequency (low-period) signals in the dataset. For example, for an EMA with a critical period of 12 bars, the maximum gain reduction of

> Ehlers notes that there are many ways to make the SuperSmoother adaptive to market conditions. He demonstrates his preferred method, dubbed the Adaptive SuperSmoother, in the article's code. Rather than tuning the smoothing factor of an EMA based on a volatility measure, the Adaptive SuperSmoother dynamically adjusts the critical period of one SuperSmoother based on the rate of change (ROC) in another. The steps to calculate the filter are as follows:

> Calculate a SuperSmoother filter using a fixed critical period.

> Measure the one-bar ROC in the first filter, and calculate the RMS (Root Mean Square) of the result over a specified length (81 bars by default, as per the article).

> The snapshot below shows the indicator's outputs using default settings on a 1D S&P 500 Futures chart. The Adaptive SuperSmoother responds to market movements more quickly than the fixed-period SuperSmoother, while still smoothing out high-frequency noise in the data:

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

- https://www.tradingview.com/script/FnlMn99W-TASC-2026-09-Adaptive-SuperSmoother/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
