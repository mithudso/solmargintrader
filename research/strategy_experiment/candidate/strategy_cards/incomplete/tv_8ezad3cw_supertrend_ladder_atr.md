---
id: tv_8ezad3cw_supertrend_ladder_atr
name: "Supertrend - Ladder ATR"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Supertrend - Ladder ATR; not a tested trading strategy."
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
# Supertrend - Ladder ATR

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This is a supertrend with slight twisted concept which can be very benefecial in strong trending markets to reduce stop loss distance and exit slightly quicker.

> ▶ When the instrument is trending up, regular ATR shows high values if there are big green candles. This affect the stoploss distance in regular supertrend which leads to wide stops or delayed lagging. When you are in long trade, what matters for stoploss is how much a negative candle can move within bar. Hence, using ATR derived only based on red candles is more beneficial for trailing stops on long signals. Same applies to short trades where using ATR derived from only green candles is more efficient than overall ATR.

> ▶ ATR will be minimal when the volatility is less and ATR will increase with volatility. That means, once you are in trade, the trailing of stoploss also will vary based on ATR (or volatility). With regular ATR and supertrend, chances of stop loss distance widening is high with increased volatility even though stoploss levels will not move down. This again poses the risk of higher drawdown during trade closure and also keeps in the trade during ranging market. To avoid this, the second trick we are using here is only to reduce the atr stoploss difference when in trade. That is, when in long tr

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_atr_trailing`, `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/8EZaD3CW-Supertrend-Ladder-ATR/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
