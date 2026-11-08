---
id: tv_43000736064_performance
name: "Performance"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Performance; not a tested trading strategy."
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
# Performance

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Performance indicator displays the current percentage change in prices of one or more symbols, over a set of chosen time periods, in a heatmap-style table. The indicator features text inputs where you can supply comma-separated lists to customize the symbols and timeframes for which it displays performance data.

> The indicator requests daily close prices for each symbol from the user-defined symbol list, then calculates the percentage change in those prices (the performance value) across each time period specified in the timeframe list. Each row in the table corresponds to a symbol, and each column corresponds to a timeframe. The cell at the intersection of a row and column shows the relative amount by which a specific symbol's price increased or decreased over one of the time periods.

> For each listed timeframe and symbol, the indicator determines an anchor time for the performance calculation based on the opening time of the symbol's latest daily bar. The anchor time calculation depends on the type of timeframe:

> For day-based or week-based timeframes, the indicator subtracts the specified number of 24-hour or 7-day periods from the current daily bar's opening time. For example, if the symbol's current bar opens on Oct 10, 2025, the anchor time for the "1W" timeframe is on Oct 3, 2025.

> For example, if the symbol's latest price is 215.00 and the "1M" anchor bar's closing price is 193.00, the resulting performance value is 100 * (215 - 193) / 193 = 11.40%. This value indicates that the symbol's price increased by over eleven percent across the latest one-month period.

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

- https://www.tradingview.com/support/solutions/43000736064-performance/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
