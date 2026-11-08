---
id: tv_uvby6vlf_mad_gann_o_maticus
name: "[MAD] Gann o Maticus"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of [MAD] Gann o Maticus; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, level2-orderbook-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# [MAD] Gann o Maticus

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Gannomat — Full Automated Gann Grids & Astro Cycles

> Gannomat draws a Gann quadrant box on your chart — a rectangle where the width represents a time period and the height represents a price range. Inside each box, it projects geometric arc curves from all four corners at multiple proportional levels (1x0 through 5x0, plus diagonal variants 1x1 through 5x1). These arcs create a web of curved support and resistance lines based on the time–price geometry of the quadrant.

> Astrocycles — The box width is no longer a fixed timeframe. Instead, each new box begins when a specific planetary event occurs (configured in Astro Settings). The box width varies from cycle to cycle based on the actual interval between consecutive events.

> Each time a new period begins — either a new timeframe candle or a new astronomical event — the box resets and a fresh set of arcs is drawn.

> Cleanup Old Drawings (Default: On) — When enabled, previous box and arc drawings are removed when a new period starts. Turn off if you want to keep all historical boxes visible.

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

Required inputs: ohlcv, level2-orderbook-history.
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

- https://www.tradingview.com/script/UVBy6VlF-MAD-Gann-o-Maticus/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
