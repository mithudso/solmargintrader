---
id: tv_vfzck3hx_tasc_2026_08_an_ag_selling_model
name: "TASC 2026.08 An Ag Selling Model"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2026.08 An Ag Selling Model; not a tested trading strategy."
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
# TASC 2026.08 An Ag Selling Model

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific strategy named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This strategy implements the "Ag Selling Model" as presented by Perry J. Kaufman in the August 2026 edition of the TASC Traders' Tips "Identifying The Best Price Levels For Selling Commodity Futures". The article describes a long-hold selling strategy for agricultural commodity futures based around the seasonal harvest timing of crops, mainly US grains traded on the CBOT and KCBOT, both which have been acquired by CME.

> The core idea is that if there is only one crop per year, crop prices will be lowest around harvest and highest around peak growing season. Based on this timing, the strategy spaces out its sell orders up to three times throughout the year, and covers its position at harvest.

> With these two figures, the volatility is added to the average based on a multiplication factor.

> ATR factor: Factor by which to multiply ATR when calculating selling level. 2.5 to 3.5 is generally recommended but higher has been seen for more volatile grains.

> Avoid selling immediately after harvest, as a long period of low prices typically follows.

> IMPORTANT NOTE: The strategy parameters have been adjusted specifically for Corn Futures (ZC1!). This ticker operates in Cents (USX) rather than Dollars (USD); all the strategy values have been translated to account for this. To apply this strategy to other markets it is important to properly adjust the strategy parameters to simulate realistic conditions.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_risk_based_sizing`, `tv_method_seasonality`.

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

- https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
