---
id: tv_mxn4pesd_htf_volume_spike_imbalance_projection_luxalgo
name: "HTF Volume Spike & Imbalance Projection [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of HTF Volume Spike & Imbalance Projection [LuxAlgo]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# HTF Volume Spike & Imbalance Projection [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The HTF Volume Spike & Imbalance Projection [LuxAlgo] indicator provides a comprehensive multi-timeframe analysis tool that projects higher timeframe (HTF) candle structures, volume spikes, and volume profiles directly onto the current chart. This script aims to bridge the gap between different time horizons, allowing traders to identify institutional interest, supply/demand zones, and significant order flow imbalances within an HTF context without ever switching timeframes.

> to pull granular data. By analyzing volume at this "Spike Granularity," the script can pinpoint specific price levels where volume exceeded a moving average by a user-defined multiplier.

> HTF Anchor Timeframe: Defines the timeframe of the main projection. The "Auto" setting selects a logical HTF based on your current chart.

> Spike Granularity: The lower timeframe used to find individual spikes.Volume Spike Multiplier: The threshold used to define a "spike" relative to the volume average.Volume MA Length: The lookback period for the volume average.

> Show Ghost (Previous) Bar: Toggles the visualization of the previous HTF period.Highlight Stacked Imbalances: Enables detection of price zones with high-frequency aggressive volume.Show Anchor Connection Lines: Toggles lines connecting chart levels to the projection block.Show Bubbles on Chart Candles: Toggles the LTF volume spikes directly on the main chart bars.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/MXn4pESD-HTF-Volume-Spike-Imbalance-Projection-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
