---
id: tv_qakfjgfu_liquidity_levels_luxalgo
name: "Liquidity Levels [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Liquidity Levels [LuxAlgo]; not a tested trading strategy."
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
# Liquidity Levels [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Peak Activity Levels indicator displays support and resistance levels from prices accompanied by significant volume. The indicator includes a histogram returning the frequency of closing prices falling between two parallel levels, each bin shows the number of bullish candles within the levels.

> Levels Color Mode: Determines how the levels should be colored. "Relative" will color the levels based on their location relative to the current price. "Random" will apply a random color to each level. "Fixed" will use a single color for each level.

> Histogram Window: Lookback period of the histogram calculation.

> Length: Lookback for the detection of volume peaks.

> In the chart above, we can see that over the most recent 200 bars (determined by Histogram Window) 68 closing prices fall between levels A and B, with 27 bars being bullish.

> If one of the levels was previously tested, we can hypothesize that the level might be used as support/resistance in the future. Additional analysis using volume can be done in order to confirm a potential bounce.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/qAkfJgFu-Liquidity-Levels-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
