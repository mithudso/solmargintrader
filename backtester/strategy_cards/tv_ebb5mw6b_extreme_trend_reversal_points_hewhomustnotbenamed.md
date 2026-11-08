---
id: tv_ebb5mw6b_extreme_trend_reversal_points_hewhomustnotbenamed
name: "Extreme Trend Reversal Points [HeWhoMustNotBeNamed]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Extreme Trend Reversal Points [HeWhoMustNotBeNamed]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, level2-orderbook-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Extreme Trend Reversal Points [HeWhoMustNotBeNamed]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Using moving average crossover for identifying the change in trend is very common. However, this method can give lots of false signals during the ranging markets. In this algorithm, we try to find the extreme trend by looking at fully aligned multi-level moving averages and only look at moving average crossover when market is in the extreme trend - either bullish or bearish. These points can mean long term downtrend or can also cause a small pullback before trend continuation. In this discussion, we will also check how to handle different scenarios.

> In this script, user can select how many levels of moving averages need to be calculated. This is achieved through "recursive moving average" algorithm. Requirement for building such algorithm was initially raised by @loxx

> Strength of fully aligned moving average is calculated based on position of each level with respect to other levels.

> Use the top of the box as stop-entry for long and bottom as stop-entry for short. The other ends of the box can become stop-losses for each side.

> Range and Extreme Range are calculated based on the percentile from median. The brackets are defined as per input parameters - Range Percentile and Extreme Range Percentile by using Percentile History as reference length.

> For bullish side, targets can be placed at certain risk reward levels. In this case, we just use 1:1 for bullish (trend side) and 1:1.5 for bearish side (reversal side)

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_risk_based_sizing`, `tv_method_support_resistance`.

## Data and availability

Required inputs: ohlcv, level2-orderbook-history.
The complete point-in-time input set has not been verified in the repository. Do not substitute current snapshots or inferred values for historical inputs.

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

- https://www.tradingview.com/script/eBB5mW6b-Extreme-Trend-Reversal-Points-HeWhoMustNotBeNamed/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
