---
id: tv_43000583766_bullish_abandoned_baby_how_to_catch_a_reversal_at_the_bottom_of_a
name: "Bullish Abandoned baby: how to catch a reversal at the bottom of a downtrend"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bullish Abandoned baby: how to catch a reversal at the bottom of a downtrend; not a tested trading strategy."
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
# Bullish Abandoned baby: how to catch a reversal at the bottom of a downtrend

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The bullish Abandoned baby is a three-candle reversal pattern that appears after a downtrend. A strong bearish candle is followed by a Doji that gaps below it, and then by a bullish candle that gaps above the Doji. The isolated Doji in the middle, "abandoned" by gaps on both sides, shows that selling momentum has stalled and buyers have taken over.

> Trend filter: In the indicator settings, choose how the prior trend is detected (based on SMA 50, or SMA 50 and SMA 200), or turn trend detection off.

> Like any candlestick pattern, the bullish Abandoned baby describes what has happened, not what will happen. The downtrend can resume after the pattern completes, especially in a weak market. Because the pattern is rare, there is also a risk of reading too much into a near-match, such as a Doji with a small overlap that does not meet the definition. Traders often combine it with stop-loss levels, for example below the low of the Doji, to limit losses if the reversal fails.

> The Abandoned baby is considered one of the stronger reversal signals among candlestick patterns, but it is also rare. Full gaps on both sides of the Doji are uncommon in markets that trade around the clock, such as crypto and forex, where one session's close is usually the next session's open. The pattern appears more often in stocks and futures, where overnight gaps are common.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_doji`.

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

- https://www.tradingview.com/support/solutions/43000583766-bullish-abandoned-baby-how-to-catch-a-reversal-at-the-bottom-of-a-downtrend/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
