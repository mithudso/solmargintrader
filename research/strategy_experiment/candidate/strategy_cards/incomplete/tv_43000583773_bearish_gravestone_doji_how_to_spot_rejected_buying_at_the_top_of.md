---
id: tv_43000583773_bearish_gravestone_doji_how_to_spot_rejected_buying_at_the_top_of
name: "Bearish Gravestone Doji: how to spot rejected buying at the top of a move"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bearish Gravestone Doji: how to spot rejected buying at the top of a move; not a tested trading strategy."
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
# Bearish Gravestone Doji: how to spot rejected buying at the top of a move

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Gravestone Doji is a single-candle pattern in which the open, close, and low are at or near the same price, and a long upper shadow extends above them. It shows that buyers pushed prices higher during the session but could not hold the gains. When it appears after an uptrend, traders often read it as a possible bearish reversal.

> Trend filter: In the indicator settings, choose how the prior trend is detected (based on SMA 50, or SMA 50 and SMA 200), or turn trend detection off.

> Like any candlestick pattern, the Gravestone Doji describes what has happened, not what will happen. The uptrend can resume after the candle forms, especially in a strong market. Dojis are also common on lower timeframes and in quiet markets, where they often mean nothing more than a pause. Traders often combine it with stop-loss levels, for example above the high of the upper shadow, to limit losses if the reversal fails.

> Length of the upper shadow: A longer upper shadow shows a larger rejection of higher prices.

> After an uptrend, this suggests that buyers are losing their hold on the market: the higher prices attracted enough selling to erase the whole move. Many traders read this rejection of higher prices as an early warning that the uptrend may be ending.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_doji`, `tv_method_shooting_star`.

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

- https://www.tradingview.com/support/solutions/43000583773-bearish-gravestone-doji-how-to-spot-rejected-buying-at-the-top-of-a-move/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
