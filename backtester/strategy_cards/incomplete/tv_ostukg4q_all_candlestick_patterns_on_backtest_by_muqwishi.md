---
id: tv_ostukg4q_all_candlestick_patterns_on_backtest_by_muqwishi
name: "All Candlestick Patterns on Backtest [By MUQWISHI]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of All Candlestick Patterns on Backtest [By MUQWISHI]; not a tested trading strategy."
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
# All Candlestick Patterns on Backtest [By MUQWISHI]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The “All Candlestick Patterns on Backtest” indicator generates a table that offers a clear visualization of the historical return percentages for each candlestick pattern strategy over a specified time period. This table serves as an organized resource, serving as a launching point for in-depth research into candle formations. It may help to rectify any misconceptions surrounding candlestick patterns, refine trading approaches, and it could be foundation to make informed decisions in trading journey.

> Note: If the datetime of the first candle on the chart is after the entreated datetime, the calculation will start from the first candle on the chart.

> (5) Cancel Entry Within Bars: This option is applicable with {Entry Mode = Breakout High (Low for Short)}, to cancel the Entry Order if it's not executed within certain selected number of bars.

> - “At Close”: Execute entry order as soon as the candle confirmed.

> - “Breakout High (Low for Short)”: Stop limit buy order, entry order will be executed as soon as the next candle breakout the high of last pattern’s candle (low for short)

> (7) Risk:Reward: the calculation of risk:reward range start from entry price level. For example: A pattern triggered with range 10 points, and entry price is 100.

> - For 1:1~risk:reward would the stoploss at 90 and takeprofit at 110.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_risk_based_sizing`.

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

- https://www.tradingview.com/script/OsTuKG4q-All-Candlestick-Patterns-on-Backtest-By-MUQWISHI/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
