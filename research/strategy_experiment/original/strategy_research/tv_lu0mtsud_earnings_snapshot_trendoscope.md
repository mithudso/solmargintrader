---
id: tv_lu0mtsud_earnings_snapshot_trendoscope
name: "Earnings Snapshot [Trendoscope]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Earnings Snapshot [Trendoscope]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Earnings Snapshot [Trendoscope]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Earnings Snapshot [Trendoscope®] is a custom indicator designed to provide traders and investors with a quick, visual overview of a stock's earnings performance and its impact on price action. This tool automates the analysis of earnings reports by fetching historical and future earnings data, calculating growth metrics for both earnings and price changes, and presenting the information in an intuitive table format on the chart. It also adds interactive labels at key earnings dates for detailed breakdowns.

> Growth Calculations: Computes percentage changes in earnings and price compared to the previous quarter (Last), year-over-year (Y2Y, based on 4 quarters back), and future estimates.

> On-Chart Infomration: Based on the settings, users can enable presentation of earnings, price and the growth data on chart.

> Tabular data presents the growth of Earnings and Price based on last quarter as well as Y2Y along with growth of estimated earnings. The table can be hidden through input settings.

> This script eliminates the tedium of manual data gathering and visualization. It focuses on key metrics like actual vs. estimated earnings, year-over-year (Y2Y) comparisons, and future estimates, while highlighting how these events correlate with price movements. Currently, the script handles earnings per share (EPS) data effectively, but revenue details are not included due to ongoing technical challenges with the available data interfaces in Pine Script. Future updates may incorporate revenue analysis once we find an effective way to present this data.

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

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/script/lu0MTsuD-Earnings-Snapshot-Trendoscope/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
