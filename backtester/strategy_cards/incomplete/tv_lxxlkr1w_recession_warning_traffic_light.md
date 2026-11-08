---
id: tv_lxxlkr1w_recession_warning_traffic_light
name: "Recession Warning Traffic Light"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Recession Warning Traffic Light; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-macro-and-derivatives-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Recession Warning Traffic Light

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This is an indicator that uses 6 different metrics to determine the combined probability of a recession and compares the high probability warning periods against actual historical periods of recession.

> Precious metals: This indicator calculates the relative prices of Gold & rhodium. Gold is a flight-to-quality asset. Rhodium is the rarest of precious industrial metals and prices spike when the economy is heating up. In front of a recession, the upper relative movement of rhodium precedes gold.

> Federal Reserve: This indicator measures GDP and detects contraction which is technically a recession. This is usually one of the last indicators to enter a Warning state, and it could be 6 months delayed simply confirming what may have already been projected.

> GREEN tells us that the referenced recession indicators are not exhibiting any warning. Observe the long stretches of “all-green” in between recessionary periods in the chart above.

> Actual Recession: Central Bank indicators are published by the Federal Reserve and reflect their own analysis of national and regional economic health, as well as their calculations of the likelihood of a recession. The Federal Reserve has a recession ticker which is used to plot periods of actual recessions on this indicator for comparison.

> RED will show a full-on warning level for that particular recession indicator, signaling that monitoring of this sector is clearly showing a problem – which has in the past, reliably exhibited itself as a forewarning of recessions.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-macro-and-derivatives-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/lxXLkR1w-Recession-Warning-Traffic-Light/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
