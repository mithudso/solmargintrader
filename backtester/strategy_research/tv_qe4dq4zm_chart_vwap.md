---
id: tv_qe4dq4zm_chart_vwap
name: "Chart VWAP"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Chart VWAP; not a tested trading strategy."
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
# Chart VWAP

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays a ​Volume-Weighted Average Price anchored to the leftmost visible bar of the chart. It dynamically recalculates when the chart's visible bars change because you scroll or zoom your chart.

> Load the indicator on an active chart (see the Help Center if you don't know how). By default, it displays the chart's ​VWAP in orange and a simple average of the chart's visible close values in gray. This average can be used as a companion to the ​VWAP, since both are calculated from the same set of bars. The script's settings allow you to hide it.

> You may also use the script's settings to enable the display of the chart's OHLC (open, high, low, close) levels and the values of the high and low. These are also calculated from the range of visible bars. You can complement the high and low lines with their price and their distance in percent from the chart's latest visible close. You can use the levels to quickly identify the distances from extreme points in the visible price range, as well as observe the visible chart's beginning and end prices.

> If you are not already familiar with ​VWAP, our Help Center will get you started. The typical ​VWAP is designed to be used on intraday charts, as it resets at the beginning of the day. Our Rolling ​VWAP, instead, resets on a rolling time window. You may also find the VWAP Auto Anchored built-in indicator worth a try.

> Our script also uses this new `anchor` parameter to reset the ​VWAP at the leftmost visible bar. See how simple the code is for the VisibleChart library's `vVwap()` function.

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

- https://www.tradingview.com/script/QE4dq4ZM-Chart-VWAP/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
