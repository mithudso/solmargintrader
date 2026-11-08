---
id: tv_bdk3oefq_tasc_2025_11_the_points_and_line_chart
name: "TASC 2025.11 The Points and Line Chart"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2025.11 The Points and Line Chart; not a tested trading strategy."
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
# TASC 2025.11 The Points and Line Chart

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements the Points and Line Chart described by Mohamed Ashraf Mahfouz and Mohamed Meregy in the November 2025 edition of the TASC Traders' Tips, "Efficient Display of Irregular Time Series”. This novel chart type interprets regular time series chart data to create an irregular time series chart.

> The Points and Line (P&L) chart operates similarly to a P&F chart, using price change to determine when to plot points. However, instead of plotting the price in points, the P&L chart (by default) plots the closing price from RTS data. In other words, the P&L chart plots its points at the actual RTS close, as opposed to (price) intervals based on point size. This approach creates an ITS while still maintaining a reference to the RTS data, allowing us to gain a better understanding of time while consolidating the chart into an ITS format.

> Because the P&L chart forms bars based on price action instead of time, it displays displays significantly more history than a typical RTS chart. With this view, we are able to more easily spot support and resistance levels, which we could use when looking to place trades.

> ITS charts display data only after certain conditions are met. Since they do not plot at a consistent time period, they are called “irregular”.

> Typically, ITS charts, such as Point and Figure (P&F) and Renko charts, focus on price change, plotting only when a certain threshold of change occurs.

> Technical Note: Due to drawing limitations, this indicator has the following display limits:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_renko`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/BDk3oEFQ-TASC-2025-11-The-Points-and-Line-Chart/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
