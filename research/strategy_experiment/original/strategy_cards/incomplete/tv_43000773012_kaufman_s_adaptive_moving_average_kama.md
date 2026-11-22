---
id: tv_43000773012_kaufman_s_adaptive_moving_average_kama
name: "Kaufman's Adaptive Moving Average (KAMA)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Kaufman's Adaptive Moving Average (KAMA); not a tested trading strategy."
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
# Kaufman's Adaptive Moving Average (KAMA)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Kaufman's Adaptive Moving Average (KAMA), introduced by Perry J. Kaufman in 1995, is a moving average that dynamically adjusts its smoothing behavior to the relative noise or choppiness in market movements.

> Kaufman designed the indicator as a generalized trend-following solution based on the idea that faster averages are more useful for tracking trends when the market price is moving quickly in one direction, and slower averages are better for avoiding whipsaws during periods of choppiness and volatility. As such, KAMA follows the market price at a faster rate when movements are efficient and directional, and at a slower rate when movements are choppy or inefficient.

> A traditional EMA calculates a fixed smoothing factor of 2 / (length + 1), where the length value controls the period for which the average responds significantly to changes in price.

> KAMA uses Kaufman's Efficiency Ratio (ER) to control its responsiveness. The ratio represents the absolute change in price over a period relative to the total bar-by-bar change (volatility) within that period:

> An ER value near 1 means that the total bar-by-bar change across the period is close to the overall change, indicating efficient price movement in one direction. A value near 0 means that the overall change is much smaller than the total bar-by-bar change, indicating choppy or inefficient movement over the period.

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

- https://www.tradingview.com/support/solutions/43000773012-kaufman-s-adaptive-moving-average-kama/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
