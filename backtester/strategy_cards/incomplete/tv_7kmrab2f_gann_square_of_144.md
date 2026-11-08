---
id: tv_7kmrab2f_gann_square_of_144
name: "Gann Square of 144"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Gann Square of 144; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Gann Square of 144

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator will create lines on the chart based on W.D. Gann's Square of 144. All the inputs will be detailed below

> Yes, each square point divisible by 6 has information with some options, so the user can create any configuration he wants. Also, it has the advantage of having the square built in seconds and adjusting itself on each new calculation.

> This input will be used when the "Set Upper/Lower Prices and Start Bar Automatically" checkbox is not selected. The indicator will calculate all the line locations on the chart using the selected start date. When selecting this input, change the Manual Max and Min Prices to the better calculation

> When you dig into Gann's books for more information about the square of 144, you find that it was part of his setup with multiple indicators (technical and fundamental, and astrological). It is not a "one indicator" setup, so it's hard to say that you will find entries, exits, stop loss, and take profit in this. Still, it will help see trendiness, support, and resistance levels.

> This input will be used when the "Set Upper/Lower Prices and Start Bar Automatically" checkbox is not selected. The indicator will calculate all the line's locations on the chart using these prices

> Selects if the starting date will be automatically selected by the system or based on the input data. When it's set, the indicator will use the most recent bar as the middle point of the square, using the higher price as the Upper Price and the lowest price as the Lower Price in the latest 72 bars (or more based on the Candles Per Division parameter)

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

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/script/7KmrAB2f-Gann-Square-of-144/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
