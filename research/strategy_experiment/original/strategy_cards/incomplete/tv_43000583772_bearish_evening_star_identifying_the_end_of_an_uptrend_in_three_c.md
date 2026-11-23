---
id: tv_43000583772_bearish_evening_star_identifying_the_end_of_an_uptrend_in_three_c
name: "Bearish Evening star: identifying the end of an uptrend in three candles"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bearish Evening star: identifying the end of an uptrend in three candles; not a tested trading strategy."
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
# Bearish Evening star: identifying the end of an uptrend in three candles

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Evening star is a three-candle bearish reversal pattern that appears after an uptrend. A long bullish candle is followed by a small-bodied candle that gaps above it, and then by a long bearish candle that closes deep into the body of the first candle. The pattern shows buying momentum fading and sellers taking control.

> Trend filter: In the indicator settings, choose how the prior trend is detected (based on SMA 50, or SMA 50 and SMA 200), or turn trend detection off.

> Like any candlestick pattern, the Evening star describes what has happened, not what will happen. The uptrend can resume after the pattern completes. Because the third candle has already moved a long way down, much of the price move may be over by the time the pattern is complete. Gaps between bodies are also rare in markets that trade around the clock, such as crypto and forex. Traders often place a stop-loss above the high of the star to limit losses if the reversal fails.

> The two patterns differ only in the middle candle. In an Evening star, the star has a small but visible body. In an Evening Doji star, the star is a Doji, with almost no body at all. Many traders consider the Doji version a slightly stronger warning, because it shows complete indecision. When the middle candle is separated from both neighbors by full gaps, including the shadows, the pattern becomes an Abandoned baby. The Morning star is the bullish counterpart of the Evening star.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_doji`, `tv_method_morning_evening_star`.

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

- https://www.tradingview.com/support/solutions/43000583772-bearish-evening-star-identifying-the-end-of-an-uptrend-in-three-candles/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
