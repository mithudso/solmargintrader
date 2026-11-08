---
id: tv_oqttrc35_tasc_2025_02_autocorrelation_indicator
name: "TASC 2025.02 Autocorrelation Indicator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2025.02 Autocorrelation Indicator; not a tested trading strategy."
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
# TASC 2025.02 Autocorrelation Indicator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements the Autocorrelation Indicator introduced by John Ehlers in the "Drunkard's Walk: Theory And Measurement By Autocorrelation" article from the February 2025 edition of TASC's Traders' Tips. The indicator calculates the autocorrelation of a price series across several lags to construct a periodogram, which traders can use to identify market cycles, trends, and potential reversal patterns.

> Autocorrelation measures the correlation of a time series with a delayed copy, or lag, of itself. The autocorrelation function (ACF) is a method that evaluates autocorrelation across a range of lags, which can help to identify patterns, trends, and cycles in stochastic market data. Analysts often use ACF to detect and characterize long-range dependence in a time series.

> This script calculates the Autocorrelation Indicator on an input "Source" series, smoothed by Ehlers' UltimateSmoother filter, and plots several color-coded lines to represent the periodogram's information. Each line corresponds to an analyzed lag, with the shortest lag's line at the bottom of the pane. Green hues in the line indicate a positive correlation for the lag, red hues indicate a negative correlation (anticorrelation), and orange or yellow hues mean the correlation is near zero.

> John Ehlers explains that many recent academic studies affirm that market data has a pink spectrum, meaning the power spectral density of the data is proportional to the wavelengths it contains, like pink noise. A random walk with a pink spectrum suggests that the states of the random variable are correlated and not independent. In other words, the random variable exhibits long-range dependence with respect to previous states.

> The Autocorrelation Indicator evaluates the ACF of market prices over a fixed range of lags, expressing the results as a color-coded heatmap representing a dynamic periodogram. Ehlers suggests the information from the periodogram can help traders identify different market behaviors, including:

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

- https://www.tradingview.com/script/OQtTRc35-TASC-2025-02-Autocorrelation-Indicator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
