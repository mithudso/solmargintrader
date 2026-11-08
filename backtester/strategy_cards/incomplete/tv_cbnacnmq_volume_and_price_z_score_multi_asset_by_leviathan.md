---
id: tv_cbnacnmq_volume_and_price_z_score_multi_asset_by_leviathan
name: "Volume and Price Z-Score [Multi-Asset] - By Leviathan"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Volume and Price Z-Score [Multi-Asset] - By Leviathan; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Volume and Price Z-Score [Multi-Asset] - By Leviathan

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script offers in-depth Z-Score analytics on price and volume for 200 symbols. Utilizing visualizations such as scatter plots, histograms, and heatmaps, it enables traders to uncover potential trade opportunities, discern market dynamics, pinpoint outliers, delve into the relationship between price and volume, and much more.

> Calculates the z-score by comparing current bar’s price and volume data to the mean (moving average with any custom length, default is 20 bars). This indicates how much the current bar’s price and volume data deviates from the average over the specified period. A positive z-score suggests that the current bar's price or volume is above the mean of the last 20 bars (or the custom length set by the user), while a negative z-score means it's below that mean.

> Calculates the custom-length average of symbol's z-score. Think of it as a smoothed version of the Current Z-Score. Instead of just looking at the z-score calculated on the latest bar, it considers the average behavior over the last few bars. By doing this, it helps reduce sudden jumps and gives a clearer, steadier view of the market.

> The "Volume Type" input allows you to choose the nature of volume data that will be factored into the volume z-score calculation. The interpretation of indicator’s data changes based on this input. You can opt between:

> - Volume (Regular Volume): This is the classic measure of trading volume, which represents the volume traded in a given time period - bar.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/CBnACnmq-Volume-and-Price-Z-Score-Multi-Asset-By-Leviathan/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
