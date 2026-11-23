---
id: tv_builtin_correlation_coefficient
name: "Correlation Coefficient"
kind: exposure-strategy
status: spec-only
family: other
summary: "Specification of Correlation Coefficient; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  length: {default: 20, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Correlation Coefficient

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

rho = cov(A,B)/(stdev(A)*stdev(B)) over trailing synchronized observations. Levels and returns are different experiments; refuse zero variance.

## Documented inputs and source details

TradingView catalog inputs: `sym` (symbol); `length`=20.

Catalog notes: (plots: `plot`; d.ts L23419).

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

## Official help clarification

https://www.tradingview.com/support/solutions/43000502022-correlation-coefficient-cc/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/xgxyWqlq-6A?&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>Definition
````

````text
The Correlation Coefficient calculation uses Closing Prices. The below example will be made using the Closing Prices over 12 periods for the SPY and JPM:
````

````text
1. First, every period needs to be squared for both securities.
````
