---
id: tv_i8qanszp_tasc_2025_01_linear_predictive_filters
name: "TASC 2025.01 Linear Predictive Filters"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2025.01 Linear Predictive Filters; not a tested trading strategy."
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
# TASC 2025.01 Linear Predictive Filters

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements a suite of tools for identifying and utilizing dominant cycles in time series data, as introduced by John Ehlers in the "Linear Predictive Filters And Instantaneous Frequency" article featured in the January 2025 edition of TASC's Traders' Tips. Dominant cycle information can help traders adapt their indicators and strategies to changing market conditions.

> After filtering the series to produce band-limited data, Ehlers applies a linear predictive filter to predict future values a few bars ahead. The filter, calculated based on the techniques proposed by Lloyd Griffiths, adaptively minimizes the error between the latest data point and prediction, successively adjusting its coefficients to align with the band-limited series. The filter's coefficients can then be applied to generate an adaptive estimate of the band-limited data's structure in the frequency domain and identify the dominant cycle.

> This tool calculates a linear predictive filter to forecast future data points in band-limited price data. The crosses between the prediction and signal lines can provide potential trade signals.

> Conventional technical indicators and strategies often rely on static, unchanging parameters, which may fail to account for the dynamic nature of market data. In his article, John Ehlers applies digital signal processing principles to address this issue, introducing linear predictive filters to identify cyclic information for adapting indicators and strategies to evolving market conditions.

> This approach treats market data as a complex series in the time domain. Analyzing the series in the frequency domain reveals information about its cyclic components. To reduce the impact of frequencies outside a range of interest and focus on a specific range of cycles, Ehlers applies second-order highpass and lowpass filters to the price data, which attenuate or remove wavelengths outside the desired range. This band-limited analysis isolates specific parts of the frequency spectrum for various trading styles, e.g., longer wavelengths for position trading or shorter wavelengths for swing tra

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

- https://www.tradingview.com/script/i8qanSzP-TASC-2025-01-Linear-Predictive-Filters/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
