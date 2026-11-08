---
id: tv_wp7wwjll_supertrend_ai_clustering_luxalgo
name: "SuperTrend AI (Clustering) [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of SuperTrend AI (Clustering) [LuxAlgo]; not a tested trading strategy."
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
# SuperTrend AI (Clustering) [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The SuperTrend AI indicator is a novel take on bridging the gap between the K-means clustering machine learning method & technical indicators. In this case, we apply K-Means clustering to the famous SuperTrend indicator.

> The proposed indicator rationale is based on the following hypothesis:

> Performing the calculation of the indicator using the best setting at time t would return an indicator whose characteristics adapt based on its performance. However, what if the setting of the best-performing instance and second best-performing instance of the indicator have a high degree of disparity without a high difference in performance?

> The displayed performance metrics displayed on each signal allow for a deeper interpretation of the indicator. Whereas higher values could indicate a higher potential for the market to be heading in the direction of the trend when compared to signals with lower values such as 1 or 0 potentially indicating retracements.

> Even though this specific case is rare its however not uncommon to see that performance can be similar for a group of specific settings (this could be observed in a parameter optimization heatmap), then filtering out desirable settings to only use the best-performing one can seem too strict. We can as such reformulate our first hypothesis:

> where 1 > α > 0, which is the performance memory determining the degree to which older inputs affect the current output. C(t) is the closing price, and S(t, factor) is the SuperTrend signal generating function with multiplicative factor factor.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`, `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/wP7WWjLL-SuperTrend-AI-Clustering-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
