---
id: tv_asev0vxd_tasc_2022_07_pairs_rotation_with_ehlers_loops
name: "TASC 2022.07 Pairs Rotation With Ehlers Loops"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2022.07 Pairs Rotation With Ehlers Loops; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [synchronized-two-asset-ohlcv]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# TASC 2022.07 Pairs Rotation With Ehlers Loops

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> TASC's July 2022 edition of Traders' Tips includes an article by John Ehlers titled "Pairs Rotation With ​Ehlers Loops". This is the code that implements the Ehlers Loops applied to pairs rotation trading.

> The script uses the following steps to calculate the Ehlers Loops:

> Finally, the scaled data streams are displayed one against another for the selected time interval (defined by the input parameter Loop Segments). In the resulting scatterplot, the thicker line corresponds to the later data points. The fluctuations of the filtered price data of the chart symbol are plotted along the y-axis, and the price changes of the referenced symbol are shown along the x-axis.

> When the prices of two securities (filtered and scaled with a standard deviation for consistent presentation) are plotted against each other, the curvature and direction of rotation on the chart can help guide decisions on long positions. For example, when plotting a stock versus a referenced symbol, a vertical upward movement while rotating clockwise is a sign of going long the stock. Similarly, a horizontal movement to the right while rotating counterclockwise is the sign to go long the reference. A higher probability of a reversal is expected when the price moves more than one or two standa

> The price data of both securities in the pair are individually filtered using identical high-pass and SuperSmoother filters. This results in two band-limited data streams, having a nominally zero mean. The input parameters Low-Pass Period and High-Pass Period control the filter bandwidth and thus can modify the shape of the Ehlers Loops.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: synchronized-two-asset-ohlcv.
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

- https://www.tradingview.com/script/AsEv0Vxd-TASC-2022-07-Pairs-Rotation-With-Ehlers-Loops/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
