---
id: tv_s40vmzm4_asset_rotation_system_investorunknown
name: "Asset Rotation System [InvestorUnknown]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Asset Rotation System [InvestorUnknown]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [synchronized-six-asset-and-crosspair-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Asset Rotation System [InvestorUnknown]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This system creates a comprehensive trend "matrix" by analyzing the performance of six assets against both the US Dollar and each other. The objective is to identify and hold the asset that is currently outperforming all others, thereby focusing on maintaining an investment in the most "optimal" asset at any given time.

> Calculates an equity curve for each asset and for the system itself, which assumes holding only the asset deemed optimal at any time.

> The equity curve is dynamically colored based on the asset held at each point, with this coloring also reflected on the chart via barcolor().

> Users can customize the trend analysis by selecting all indicators or choosing a single one via the "Trend Classification Method" input setting.

> RSI Length: Set the period for the RSI calculation.

> Supports alerts for when a new, confirmed optimal asset is identified. However, due to TradingView limitations, the specific asset cannot be included in the alert message.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: synchronized-six-asset-and-crosspair-history.
The full point-in-time input set has not been verified in this repository.
A single OHLCV series cannot supply these inputs; current snapshots cannot replace history.

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

- https://www.tradingview.com/script/s40vmZM4-Asset-Rotation-System-InvestorUnknown/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
