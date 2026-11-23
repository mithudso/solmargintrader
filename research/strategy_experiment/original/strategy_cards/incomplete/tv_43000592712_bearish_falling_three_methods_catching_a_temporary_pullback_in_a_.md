---
id: tv_43000592712_bearish_falling_three_methods_catching_a_temporary_pullback_in_a_
name: "Bearish Falling three methods: catching a temporary pullback in a downtrend"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bearish Falling three methods: catching a temporary pullback in a downtrend; not a tested trading strategy."
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
# Bearish Falling three methods: catching a temporary pullback in a downtrend

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Falling three methods is a five-candle continuation pattern that appears during a downtrend. A long bearish candle is followed by three small bullish candles that stay within its range, and then by another long bearish candle that closes below the first. The pattern describes a short rest in the decline, after which sellers resume control.

> Trend filter: In the indicator settings, choose how the prior trend is detected (based on SMA 50, or SMA 50 and SMA 200), or turn trend detection off.

> The first candle shows strong selling. The three small candles that follow show a pause: some sellers take profits and a few buyers step in, but the bounce is weak and stays inside the first candle's range. Buyers never gain enough strength to change the direction.

> Like any candlestick pattern, the Falling three methods describes what has happened, not what will happen. A downtrend can still end shortly after the pattern completes. Because the pattern requires five candles that match strict conditions, near-matches are common, and it can be tempting to treat a looser consolidation as the same signal. By the time the fifth candle closes, the price has also moved a long way, which affects where a stop-loss can be placed. Traders often set one above the high of the first candle to limit losses if the continuation fails.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`.

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

- https://www.tradingview.com/support/solutions/43000592712-bearish-falling-three-methods-catching-a-temporary-pullback-in-a-downtrend/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
