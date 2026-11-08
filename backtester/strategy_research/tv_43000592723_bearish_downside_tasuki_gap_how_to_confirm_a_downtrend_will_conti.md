---
id: tv_43000592723_bearish_downside_tasuki_gap_how_to_confirm_a_downtrend_will_conti
name: "Bearish Downside Tasuki gap: how to confirm a downtrend will continue"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bearish Downside Tasuki gap: how to confirm a downtrend will continue; not a tested trading strategy."
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
# Bearish Downside Tasuki gap: how to confirm a downtrend will continue

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Downside Tasuki gap is a three-candle continuation pattern that appears during a downtrend. Two bearish candles are separated by a gap down, and a bullish third candle moves back into that gap without closing it. The failure of buyers to fill the gap suggests that sellers are still in control and the decline may continue.

> Trend filter: In the indicator settings, choose how the prior trend is detected (based on SMA 50, or SMA 50 and SMA 200), or turn trend detection off.

> Like any candlestick pattern, the Downside Tasuki gap describes what has happened, not what will happen. A bounce that stops short of the gap can still develop into a reversal on the following candles. The pattern also needs a gap between bodies, which is rare in markets that trade around the clock, such as crypto and forex. Traders often place a stop-loss above the top of the gap to limit losses if the downtrend does not continue.

> How does the Downside Tasuki gap differ from a Falling window?

> A Falling window is simply a gap down between two candles, with no overlap between the high of the second candle and the low of the first. The Downside Tasuki gap starts with a gap between the bodies and then adds a test of that gap by a bullish candle. The bullish counterpart of this pattern is the Upside Tasuki gap.

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

- https://www.tradingview.com/support/solutions/43000592723-bearish-downside-tasuki-gap-how-to-confirm-a-downtrend-will-continue/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
