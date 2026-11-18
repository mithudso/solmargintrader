---
id: tv_mekxyft0_bias_and_sentiment_strength_bass_indicator_by_mattzab
name: "Bias And Sentiment Strength (BASS) Indicator by mattzab"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bias And Sentiment Strength (BASS) Indicator by mattzab; not a tested trading strategy."
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
# Bias And Sentiment Strength (BASS) Indicator by mattzab

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Bias And Sentiment Strength (BASS) Indicator is designed to be a quick visualization as to the market strength.

> Volume Bias - The Volume Bias is displayed as purple bars, and is calculated by a highly sophisticated and complex algorithmic function called subtraction. It's just the 30 Period Volume-Weighted Moving Average Minus the 30 Simple Moving Average.

> The purple bars are your volume bias. Volume bias can be positive or negative, despite the direction of the overall trend. Positive Volume Bias along with Bullish Blue Sentiment is a great sign! Go Long! If you have Bullish Sentiment and have a negative Volume Bias, be cautious! Price may not be moving with much conviction, and may be subject to reversal!

> Slow Stochastic Histogram - This is a slow stochastic with a 21 Period K, 14 Period D, and 14 Smoothing K. The "oscillator" histogram is formed by subtracting K from D.

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

- https://www.tradingview.com/script/MEKxYFt0-Bias-And-Sentiment-Strength-BASS-Indicator-by-mattzab/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
