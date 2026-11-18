---
id: tv_43000591664_zigzag_indicator
name: "Zigzag indicator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Zigzag indicator; not a tested trading strategy."
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
# Zigzag indicator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Zigzag indicator is a charting tool that highlights significant price swings and filters out smaller price fluctuations. It analyzes high and low pivot points, drawing straight lines to connect the points at the tops and bottoms of swings that meet or exceed a specified percentage threshold.

> The Zigzag indicator draws straight, solid lines connecting only the confirmed pivot points at the alternating tops and bottoms of significant price swings. A swing is considered significant if the reversal percentage meets or exceeds the threshold defined by the "Price deviation for reversals (%)" input.

> This indicator can optionally display projected pivots when calculating on realtime bars. If the "Calculate projected pivots" input is selected, the indicator searches the bars after the last valid point in the Zigzag's structure to find and display the next potential, but unconfirmed pivot that the Zigzag can use. This behavior allows the Zigzag to actively update its structure in response to the latest price updates rather than strictly waiting for the confirmation of a new pivot point.

> The "Pivot legs" input defines the total number of bars required to confirm a pivot point. The indicator divides the value by two, rounding down if necessary, to specify the required left and right bars. For example, if the value is 10, a bar's high represents a confirmed pivot high only if the price is greater than the highest price over the latest five bars to the left and greater than or equal to the highest high across the next five bars to the right.

> If a new pivot point is in the opposite direction from the last saved point, and the reversal distance from the previous point to the new point is greater than or equal to the required percentage, the indicator draws a new line connecting the two points. For example, if the last point is a pivot high and the percentage threshold is 5%, the indicator draws a new solid line after confirming a pivot low whose price is at least 5% below the last point's price.

> The Zigzag indicator has a few distinct limitations due to the way it calculates and represents its information:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_elliott_wave`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/support/solutions/43000591664-zigzag-indicator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
