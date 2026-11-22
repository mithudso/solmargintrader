---
id: tv_ksmls0hh_supertrend_parameter_sensitivity_3d_luxalgo
name: "Supertrend Parameter Sensitivity 3D [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Supertrend Parameter Sensitivity 3D [LuxAlgo]; not a tested trading strategy."
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
# Supertrend Parameter Sensitivity 3D [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Supertrend Parameter Sensitivity 3D [LuxAlgo] indicator is a powerful optimization tool that executes 100 simultaneous Supertrend backtests bar-by-bar to visualize how different ATR Lengths and Multipliers impact performance across various metrics.

> Gold Highlight: Marks the absolute "Best" parameter combination based on the selected metric.

> The script manages 100 independent Supertrend states simultaneously. On every bar, it calculates the ATR and trailing stop levels for every combination in the sensitivity matrix. It simulates "Always-in-Market" trades (flipping long/short on direction changes) to track performance data without needing a separate strategy execution.

> By projecting this data onto a 3D surface and a heatmap dashboard, it allows traders to identify "stable" parameter zones and avoid over-optimized "peaks" that may lead to curve-fitting.

> This tool is designed to help traders find the most robust settings for the Supertrend indicator on any given timeframe or asset. Instead of manually guessing settings, users can see a holistic view of the parameter space.

> Reward/Risk Ratio: The average win divided by the average loss.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/kSMLs0Hh-Supertrend-Parameter-Sensitivity-3D-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
