---
id: tv_zsmaleyi_rsi_impact_heat_map_trendoscope
name: "RSI Impact Heat Map [Trendoscope]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RSI Impact Heat Map [Trendoscope]; not a tested trading strategy."
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
# RSI Impact Heat Map [Trendoscope]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Here is a simple tool to measure and display outcome of certain RSI event over heat map.

> Range of the heat map is adjusted automatically based on min and max value of the displacement. In order to filter out or merge extreme values, range is calculated based on certain percentile of the values. This will avoid displaying lots of empty cells which can obscure the actual impact.

> In this script, we have taken RSI as an example to measure impact. But, we can do this for any event. This can be price crossing over/under upper/lower bollinger bands, moving average crossovers or even complex entry or exit conditions. Overall, we can use this to plot and evaluate our trade criteria.

> Heat map is displayed using pine tables. Users can select heat map size - which can vary from 10 to 90. Selecting optimal size is important in order to get right interpretation of data. Having higher number of cells can give more granular data. But, chart may not fit into the window. Having lower size means, stats are combined together to get less granular data which may not give right picture of the results. Default value for size is 50 - meaning data is displayed in 51X51 cells.

> Settings allow users to define their event, impact duration and reference, and few display related properties. The description of these parameters are as below:

> Q1 - If more coloured dots appear on the top right corner of the table, then the event is considered to trigger high volatility and high risk environment.

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

- https://www.tradingview.com/script/zsmaLEyI-RSI-Impact-Heat-Map-Trendoscope/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
