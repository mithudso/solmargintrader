---
id: tv_43000592713_bearish_falling_window_interpreting_a_price_gap_within_a_downtren
name: "Bearish Falling window: interpreting a price gap within a downtrend"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bearish Falling window: interpreting a price gap within a downtrend; not a tested trading strategy."
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
# Bearish Falling window: interpreting a price gap within a downtrend

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The bearish Falling window is a two-candle continuation pattern that forms during a downtrend. It is defined by a price gap, called a "window," between the low of the first candle and the high of the second candle. The gap shows that sellers pushed prices lower without any trading in between, and many traders read it as a sign that the downtrend may continue.

> Trend filter: In the indicator settings, choose how the prior trend is detected (based on SMA 50, or SMA 50 and SMA 200), or turn trend detection off.

> Like any candlestick pattern, the bearish Falling window describes what has happened, not what will happen. Gaps can be filled quickly, especially in volatile markets. True gaps are also rare in markets that trade around the clock, such as crypto and forex, where one candle's close is usually the next candle's open, so the pattern appears more often in stocks and futures. A gap caused by a one-off event, such as an earnings report, may not reflect the broader trend. Traders often combine the pattern with stop-loss levels, for example above the top of the window, to limit losses if the downtren

> What does a bearish Falling window look like?

> The window: The empty space between the first candle's low and the second candle's high. No part of the two candles, including their shadows, overlaps.

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

- https://www.tradingview.com/support/solutions/43000592713-bearish-falling-window-interpreting-a-price-gap-within-a-downtrend/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
