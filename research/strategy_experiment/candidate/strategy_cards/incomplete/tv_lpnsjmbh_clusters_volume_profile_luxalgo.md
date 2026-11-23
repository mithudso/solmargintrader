---
id: tv_lpnsjmbh_clusters_volume_profile_luxalgo
name: "Clusters Volume Profile [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Clusters Volume Profile [LuxAlgo]; not a tested trading strategy."
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
# Clusters Volume Profile [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Clusters Volume Profile [LuxAlgo] indicator utilizes K-Means clustering to categorize historical price action into distinct groups and generates individual volume profiles for each detected cluster. This tool provides a unique perspective on volume distribution by isolating price behaviors based on proximity rather than strictly chronological order.

> The indicator identifies "clusters" of price activity within a user-defined lookback period. Each cluster is assigned a unique color and its own horizontal volume profile, allowing traders to see where liquidity is most concentrated within specific price regimes.

> Iteratively assigning each price bar to the nearest centroid based on the HLC2 (median) price.

> Cluster boundaries and POC lines provide concrete levels for trade management. An entry can be sought when price retests a high-volume cluster POC, while stops can be placed outside the total price range of that specific cluster (the area covered by its volume profile). Conversely, targets can be set at the POC of the next major cluster above or below current price action.

> Initializing "centroids" across the price range of the lookback period.

> Lookback Period: Determines the number of recent bars used for the clustering analysis.

> Traders can use the Point of Control (POC) of high-volume clusters to identify significant institutional interest. Because the K-Means algorithm groups price action by density rather than time, a cluster's POC often represents a "fair value" level where significant exchange occurred. These dashed POC lines frequently act as robust support or resistance levels when price returns to them in the future.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/lpnsjMbH-Clusters-Volume-Profile-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
