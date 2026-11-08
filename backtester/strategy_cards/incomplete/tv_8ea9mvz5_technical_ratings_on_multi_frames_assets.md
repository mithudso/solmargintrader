---
id: tv_8ea9mvz5_technical_ratings_on_multi_frames_assets
name: "Technical Ratings on Multi-frames / Assets"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Technical Ratings on Multi-frames / Assets; not a tested trading strategy."
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
# Technical Ratings on Multi-frames / Assets

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator is a modified version of TECHNICAL RATING v1.0 available in the public library to provide a quick overview of consolidated technical ratings performed on 12 assets in 3 timeframes.The purpose of the indicator is to provide a quick overview of the current status of the custom 12 (24) assets and to help focus on the appropriate asset.

> This indicator calculates TradingView's well-known "Strong Buy", "Buy", "Neutral", "Sell" or "Strong Sell" states using the aggregate biases of 26 different technical indicators.

> This version is similar, but not identical, to our recently published "Technical Ratings" built-in, which reproduces our "Technicals" ratings displayed as a gauge in the right panel of charts, or in the "Rating" indicator available in the TradingView Screener. This is a fork and refactoring of the code base used in the "Technical Ratings" built-in. Its calculations will not always match those of the built-in, but it provides options not available in the built-in. Up to you to decide which one you prefer to use.

> The "Strong Buy", "Buy", "Neutral", "Sell" or "Strong Sell" state of the last calculated value is displayed to the right of the last bar for each of the three groups: All, MAs and Oscillators. The first value always reflects your selection in the "Rating uses" field and is the one used to display the signal. A "Strong Buy" or "Strong Sell" state appears when the signal is above/below the 0.5/-0.5 level. A "Buy" or "Sell" state appears when the signal is above/below the 0.1/-0.1 level. The "Neutral" state appears when the signal is between 0.1 and -0.1 inclusively.

> - The position, colors and parameters of the table can be widely customized in the settings.

> Because the MAs group uses longer periods for some of its components, its value is not as jumpy as the Oscillators value.

> - Due to the limitation on maximum number of security (40), the results of 12 assets evaluated in 3 different time frames can be shown at the same time.

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

- https://www.tradingview.com/script/8EA9MvZ5-Technical-Ratings-on-Multi-frames-Assets/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
