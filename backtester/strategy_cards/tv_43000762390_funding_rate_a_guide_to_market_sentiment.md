---
id: tv_43000762390_funding_rate_a_guide_to_market_sentiment
name: "Funding rate: a guide to market sentiment"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Funding rate: a guide to market sentiment; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, venue-open-interest-and-liquidation-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Funding rate: a guide to market sentiment

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Funding rate is a periodic payment exchanged between traders holding perpetual futures positions. If the rate is positive, traders with long positions pay traders with short positions. If it is negative, shorts pay longs. This mechanism is used in crypto perpetual futures to help keep the contract price aligned with the underlying asset's spot price.

> Note: Some exchanges may apply proprietary adjustments to this formula. Funding rates therefore usually differ across exchanges.

> Since funding rate is calculated across many exchanges, you can choose how to display the data:

> Entry timing: If the next funding payment is unfavorable and is due soon, you may wait for it to pass before opening a position

> Funding rate is a periodic payment between traders holding perpetual futures positions: if it is positive, longs pay shorts, and if it is negative, shorts pay longs. It's used in crypto perpetual futures to keep the contract price close to the underlying asset's spot price.

> Risk management: A positive or negative funding rate can result in either passive gains or additional costs, which can significantly affect large or long-term positions

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_value_investing`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, venue-open-interest-and-liquidation-history.
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

- https://www.tradingview.com/support/solutions/43000762390-funding-rate-a-guide-to-market-sentiment/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
