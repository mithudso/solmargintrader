---
id: tv_tmlc5wma_adaptive_market_profile_auto_detect_dynamic_activity_zones
name: "Adaptive Market Profile – Auto Detect & Dynamic Activity Zones"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Adaptive Market Profile – Auto Detect & Dynamic Activity Zones; not a tested trading strategy."
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
# Adaptive Market Profile – Auto Detect & Dynamic Activity Zones

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Adaptive Market Profile is an advanced indicator that automatically detects and displays the most relevant trend channel and market profile for any asset and timeframe. Unlike standard regression channel tools, this script uses a fully adaptive approach to identify the optimal period, providing you with the channel that best fits the current market dynamics. The calculation is based on maximizing the statistical significance of the trend using Pearson’s R coefficient, ensuring that the most relevant trend is always selected.

> Within the selected channel, the indicator generates a dynamic market profile, breaking the price range into configurable zones and displaying the most active areas based on volume or the number of touches. This allows you to instantly identify high-activity price levels and potential support/resistance zones. The “most active lines” are plotted in real-time and always stay parallel to the channel, dynamically adapting to market structure.

> - Automatic detection of the optimal regression period: The script scans a wide range of lengths and selects the channel that statistically represents the strongest trend.

> - Manual override: Optionally, users can select their own channel period for full control.

> - Suitable for all assets and timeframes (crypto, stocks, forex, futures).

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_market_profile`, `tv_method_market_structure`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/TMLC5Wma-Adaptive-Market-Profile-Auto-Detect-Dynamic-Activity-Zones/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
