---
id: tv_jdw7ww2g_technical_ratings
name: "Technical Ratings"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Technical Ratings; not a tested trading strategy."
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
# Technical Ratings

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator calculates TradingView's well-known "Strong Buy", "Buy", "Neutral", "Sell" or "Strong Sell" states using the aggregate biases of 26 different technical indicators.

> • Choose the timeframe you want calculations to be made on.

> • When using both MAs and Oscillators groups to calculate the rating, you can vary the weight of each group in the calculation. The default is 50/50.

> The "Strong Buy", "Buy", "Neutral", "Sell" or "Strong Sell" state of the last calculated value is displayed to the right of the last bar for each of the three groups: All, MAs and Oscillators. The first value always reflects your selection in the "Rating uses" field and is the one used to display the signal. A "Strong Buy" or "Strong Sell" state appears when the signal is above/below the 0.5/-0.5 level. A "Buy" or "Sell" state appears when the signal is above/below the 0.1/-0.1 level. The "Neutral" state appears when the signal is between 0.1 and -0.1 inclusively.

> Because the markers never repaint, their logic adapts to the repainting setting used for the signal. When the signal repaints, markers will only appear at the close of a realtime bar. When the signal does not repaint (or if you use a higher timeframe), alerts will appear at the beginning of the realtime bar, since they are calculated on values that already do not repaint.

> Because the MAs group uses longer periods for some of its components, its value is not as jumpy as the Oscillators value.

> The calculated rating is displayed as columns, but you can change the style in the inputs. The color of the signal can be one of three colors: bull, bear, or neutral. You can choose from a few presets, or check one and edit its color. The color is determined from the rating's value. Between 0.1 and -0.1 it is in the neutral color. Above/below 0.1/-0.1 it will appear in the bull/bear color. The intensity of the bull/bear color is determined by cumulative advances/declines in the rating. It is capped to 5, so there are five intensities for each of the bull/bear colors.

> • This version allows control over repainting of the signal when you do not use a higher timeframe. Higher timeframe (HTF) information from this version does not repaint.

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

- https://www.tradingview.com/script/Jdw7wW2g-Technical-Ratings/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
