---
id: tv_3jkrk2at_vqzl_z_score
name: "VQZL Z-Score"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of VQZL Z-Score; not a tested trading strategy."
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
# VQZL Z-Score

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Volatility Qaulity Zero Line attempts to keep a trader out of ranging markets, but the original calculation on TradingView had to be adjusted for each instrument. To avoid this issue, I have applied a z-score calculation to the VQZL so the result is standardized for all instruments. A Z-Score is simply a value's relationship to the mean (average) of a group of values, measured in terms of standard deviations from the mean.

> This calculation allows us to compare current volatility to the mean (moving average) of the population (Z-Length). The closer the VQZL Z-Score is to the mean, the closer it will be to the Zero Line and therefore price is likely consolidating and choppy. The farther VQZL Z-Score is from the mean, the more likely price is trending.

> The MA Mode determines the Moving Average used to calculate VQZL itself. The Z-Score is ALWAYS calculated with a simple moving average (as that is the standard calculation for Z-Score).

> The Threshold Levels are the levels at which VQZL Z-Score will change from gray to yellow, orange, green (bullish), or red (bearish). These levels can be adjusted but you should adjust the Threshold Lines as well (in the style section), so they line up with your adjusted values.

> Statistically speaking, confidence levels in relation to Z-Score are noted below. The built in Threshold Levels are the positive and negative values for 90%, 95%, and 99%. This would indicate when volatility is greater than these values they are out of the ordinary from the standard range. You may wish to adjust these levels for VQZL Z-Score to be more responsive to your trading need

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- https://www.tradingview.com/script/3JKrk2at-VQZL-Z-Score/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
