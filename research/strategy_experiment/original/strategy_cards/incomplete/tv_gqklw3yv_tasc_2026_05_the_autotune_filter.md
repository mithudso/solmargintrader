---
id: tv_gqklw3yv_tasc_2026_05_the_autotune_filter
name: "TASC 2026.05 The AutoTune Filter"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2026.05 The AutoTune Filter; not a tested trading strategy."
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
# TASC 2026.05 The AutoTune Filter

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements the AutoTune Filter described by John F. Ehlers in the article "A Rolling Autocorrelation Function" from the May 2026 edition of the TASC Traders' Tips. The script analyzes rolling autocorrelation in filtered price data to calculate a band-pass filter that dynamically adjusts to apparent dominant cycles.

> Autocorrelation measures the correlation of a time series with a lagged version of itself. The autocorrelation function (ACF) evaluates autocorrelation across a range of lags to gauge the extent to which values in a series vary jointly with previous values at different offsets.

> However, he also observed that at specific lags, anticorrelation (negative correlation) can emerge, where the current values in the series move in one direction while past values move in the opposite direction. Based on this observation, he suggests that a lag with strong anticorrelation can indicate a significant cycle in the market data, where the cycle length is twice that of the analyzed lag.

> In other words, a pure sine wave with a given period has perfect anticorrelation with a delayed version of itself that is offset by half of that period.

> While market data does not typically behave like a pure sine wave, the same underlying principle applies: if the current prices exhibit a strong anticorrelation with previous prices at a given offset, a dominant cycle with a length of twice that offset is likely present in the current data.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_fourier_cycle`.

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

- https://www.tradingview.com/script/GqKlw3yv-TASC-2026-05-The-AutoTune-Filter/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
