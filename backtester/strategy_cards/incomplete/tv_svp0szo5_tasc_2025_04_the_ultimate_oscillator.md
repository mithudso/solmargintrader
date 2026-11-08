---
id: tv_svp0szo5_tasc_2025_04_the_ultimate_oscillator
name: "TASC 2025.04 The Ultimate Oscillator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2025.04 The Ultimate Oscillator; not a tested trading strategy."
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
# TASC 2025.04 The Ultimate Oscillator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements an alternative, refined version of the Ultimate Oscillator (UO) designed to reduce lag and enhance responsiveness in momentum indicators, as introduced by John F. Ehlers in his article "Less Lag In Momentum Indicators, The Ultimate Oscillator" from the April 2025 edition of TASC's Traders' Tips.

> Ehlers explains that the key to removing indicator lag is to combine filters of different types in such a way that the result preserves necessary, useful signals while minimizing delay (lag). His proposed UltimateOscillator aims to maintain responsiveness to a specific frequency range by measuring the difference between two highpass filters' outputs. The oscillator uses the following formula:

> The script plots the UO calculated for the specified "Source" series in a separate pane, with a color based on the chart's foreground color. Positive UO values indicate upward momentum or trends, and negative UO values indicate the opposite.

> In his article, Ehlers states that indicators are essentially filters that remove unwanted noise (i.e., unnecessary information) from market data. Simply put, they process a series of data to place focus on specific information, providing a different perspective on price dynamics. Various filter types attenuate different periodic signals within the data. For instance, a lowpass filter allows only low-frequency signals, a highpass filter allows only high-frequency signals, and a bandpass filter allows signals within a specific frequency range.

> HP2 is another highpass filter that allows only shorter wavelengths than the critical period of HP1.

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

- https://www.tradingview.com/script/sVP0SZo5-TASC-2025-04-The-Ultimate-Oscillator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
