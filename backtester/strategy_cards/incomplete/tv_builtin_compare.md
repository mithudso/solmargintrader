---
id: tv_builtin_compare
name: "Compare"
kind: exposure-strategy
status: spec-only
family: other
summary: "Specification of Compare; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  source: {default: "close", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Compare

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Display a second series on the same chart, possibly rebased. It is a visualization input; no entry or exit rule is supplied.

## Documented inputs and source details

TradingView catalog inputs: `source`=close [open, high, low, close, hl2, hlc3, ohlc4]; `symbol` (symbol).

Catalog notes: Documented: `createStudy('Compare',false,false,{source:'open',symbol:'IBM'})`. No extend-time-scale or legend logos (docs). (plots: `plot`; d.ts L23269).

These are documented UI inputs, not verified constructor defaults. Standard formulas
are reference definitions; the capture does not establish exact TradingView seed,
smoothing or rendering parity.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: synchronized-point-in-time-universe.
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

- docs/TRADINGVIEW-REFERENCE.md — built-in indicator catalog and standard equations.
- https://www.tradingview.com/charting-library-docs/latest/indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
