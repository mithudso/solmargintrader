---
id: tv_6qwqyut8_tasc_2025_07_laguerre_filters
name: "TASC 2025.07 Laguerre Filters"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2025.07 Laguerre Filters; not a tested trading strategy."
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
# TASC 2025.07 Laguerre Filters

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements the Laguerre filter and oscillator described by John F. Ehlers in the article "A Tool For Trend Trading, Laguerre Filters" from the July 2025 edition of TASC's Traders' Tips. The new Laguerre filter utilizes the UltimateSmoother filter in place of an exponential moving average (EMA) in its calculation, offering improved responsiveness and reduced lag.

> As Ehlers explains in his article, the Laguerre filter is a form of transversal filter. A transversal filter calculates an output signal using a tapped delay line. It creates multiple delayed versions of an input signal, applies weight to each delay, and then calculates their sum to generate the filtered result.

> The Laguerre filter's structure relies on Laguerre polynomials — solutions to a differential equation solved by Edmond Laguerre in the 1800s. When Ehlers analyzed the formula for these polynomials on discrete systems (e.g., financial time series), he found that the first term's expression corresponds to an EMA response, and all subsequent terms correspond to an all-pass response. In contrast to other filter types, an all-pass filter produces phase shift (i.e., delay) in an input signal's components without affecting its amplitude.

> Users can control the behavior of the filter and oscillator with the inputs in the "Settings/Inputs" tab:

> The "Period" input defines the critical period of the UltimateSmoother used in the Laguerre filter and oscillator calculations. Its default value is 30.

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

- https://www.tradingview.com/script/6QWQYUT8-TASC-2025-07-Laguerre-Filters/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
