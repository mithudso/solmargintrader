---
id: tv_aapsyqft_gann_box_zeiierman
name: "Gann Box (Zeiierman)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Gann Box (Zeiierman); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Gann Box (Zeiierman)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Gann Box (Zeiierman) is an indicator that provides visual insights using the principles of W.D. Gann's trading methods. Gann's techniques are based on geometry, astronomy, and astrology, and are used to predict important price levels and market trends. This indicator helps traders identify potential support and resistance levels, and forecast future price movements.

> The indicator operates by identifying high and low points within a visible range on the chart and drawing a Gann Box between these points. The box is divided into segments based on selected percentages, which represent key levels for observing market reactions. It includes options to display labels, a Gann fan, and Gann angles for analysis. Advanced features allow extending the box into the future for predictive analysis and reversing its orientation for alternative viewpoints.

> Gann Fan: This feature draws lines at a significant price angle, helping traders identify potential support and resistance levels based on the theory that prices move in predictable patterns.

> Gann used angles and various geometric constructions to divide time and price into proportionate parts. Gann indicators are often used to predict areas of support and resistance, key tops and bottoms, and future price moves.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_gann`, `tv_method_support_resistance`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/aaPsyqft-Gann-Box-Zeiierman/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
