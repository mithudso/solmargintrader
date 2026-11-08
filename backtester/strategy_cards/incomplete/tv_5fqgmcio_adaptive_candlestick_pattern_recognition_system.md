---
id: tv_5fqgmcio_adaptive_candlestick_pattern_recognition_system
name: "Adaptive Candlestick Pattern Recognition System"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Adaptive Candlestick Pattern Recognition System; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Adaptive Candlestick Pattern Recognition System

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Nearly three years in the making, intermittently worked on in the few spare hours of weekends and time off, this is a passion project I undertook to flesh out my skills as a computer programmer. This script currently recognizes 85 different candlestick patterns ranging from one to five candles in length. It also performs statistical analysis on those patterns to determine prior performance and changes the coloration of those patterns based on that performance. In searching TradingView's script library for scripts similar to this one, I had found a handful. However, when I reviewed the ones whi

> CLASSIC: In this mode, candlestick patterns will be identified whenever they appear. The user has a wide variety of inputs to manipulate that can change how certain patterns are identified and even enable alerts to notify themselves when these patterns appear. Each pattern selected to appear will have their Profit or Loss (P/L) calculated starting from the first candle open succeeding the pattern to a candle close specified some number of candles ahead. These P/L calculations are then collected for each pattern, and split among partitions of prior price action of the asset the script is curren

> BREAKOUT: In this mode, P/L calculations are held off until a breakout direction has been confirmed. The user may specify the number of candles ahead of a pattern's appearance (from one to five) that a pattern has to confirm a breakout in either an upward or downward direction. A breakout is constituted when there is a candle following the appearance of the pattern that closes above/at the highest high of the pattern, or below/at its lowest low. Only then will percent return calculations be performed for the pattern that's been identified, and these percent returns are broken up not only by th

> Candlestick Theory - This script focuses solely on the concept of Candlestick Theory: arrangements of candlesticks may form certain patterns that can potentially influence the future price action of assets which experience those patterns. A full list of patterns (grouped by pattern length) will be in its own section of this description. This script contains two modes of operation for identifying candlestick patterns, 'CLASSIC' and 'BREAKOUT'.

> Trend Direction - Many of the patterns require a trend direction prior to their appearance. Noting TradingView's own publication of candlestick patterns, I utilize a similar method for determining trend direction. Moving Averages are used to determine which trend is currently taking place for candlestick patterns to be sought out. The user has access to two Moving Averages which they may individually modify the following for each: Moving Average type (list of 9), their length, width, source values, and all variables associated with two special Moving Averages (Least Squares and Arnaud Legoux).

> Important Functionality Note: These patterns are only searched for at the most recently closed candle, not on the currently closing candle, which creates an offset of one for this script's execution. (SEE LIMITATIONS)

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_doji`, `tv_method_engulfing`, `tv_method_hammer`, `tv_method_morning_evening_star`, `tv_method_shooting_star`, `tv_method_three_soldiers_crows`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/script/5FQgMCiO-Adaptive-Candlestick-Pattern-Recognition-System/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
