---
id: tv_o8trzczt_intrabar_efficiency_ratio
name: "Intrabar Efficiency Ratio"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Intrabar Efficiency Ratio; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Intrabar Efficiency Ratio

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays a directional variant of Perry​ Kaufman's​ Efficiency​ Ratio​, designed to gauge the "efficiency" of intrabar price movement by comparing the sum of movements of the lower timeframe bars composing a chart bar with the respective bar's movement on an average basis.

> ER's output is bounded between 0 and 1. A value of 0 indicates that the starting price equals the ending price for the period, which suggests that price movement was maximally inefficient. A value of 1 indicates that price had travelled no more than the distance between the starting price and the ending price for the period, which suggests that price movement was maximally efficient. A value between 0 and 1 indicates that price had travelled a distance greater than the distance between the starting price and the ending price for the period. In other words, some degree of noise was present whic

> As an example, let's say that the price of an asset had moved from $15 to $14 by the end of a period, but the sum of absolute changes for each bar of data was $4. ER would be calculated like so:

> Efficiency Ratio​ was first introduced by Perry Kaufman in his 1995 book, titled "Smarter Trading". It is the ratio of absolute price change to the sum of absolute changes on each bar over a period. This tells us how strong the period's trend is relative to the underlying noise. Simply put, it's a measure of price movement efficiency. This ratio is the modulator utilized in Kaufman's​ Adaptive​ Moving​ Average​ (KAMA​), which is essentially an Exponential​ Moving​ Average​ (EMA​) that adapts its responsiveness to movement efficiency.

> This suggests that the trend was only 25% efficient over the period, as the total distanced travelled by price was four times what was required to achieve the change over the period.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/o8tRZCzT-Intrabar-Efficiency-Ratio/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
