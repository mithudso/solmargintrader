---
id: tv_builtin_anchored_vwap
name: "Anchored VWAP"
kind: exposure-strategy
status: spec-only
family: volume
summary: "Specification of Anchored VWAP; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  start_time: {default: 0, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  bands_calculation_mode: {default: "Standard Deviation", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  bands_multiplier_1: {default: 1, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  bands_multiplier_2: {default: 2, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  bands_multiplier_3: {default: 3, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  source: {default: "hlc3", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Anchored VWAP

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

AVWAP_t=sum(TP*V,anchor..t)/sum(V,anchor..t). Choose the anchor using only information available when it is selected; specify how bands accumulate variance or percentage distance.

## Documented inputs and source details

TradingView catalog inputs: `start time`=0; `bands calculation mode`=Standard Deviation [Standard Deviation, Percentage]; `bands multiplier #1`=1; `bands multiplier #2`=2; `bands multiplier #3`=3; `source`=hlc3 (source).

Catalog notes: Not in the Indicators list; present in d.ts (`AnchoredVWAPIndicatorOverrides`, `StudyOverrides`). UI display name not given; verify via `getStudiesList()`. (plots: `vwap`, `lower band #1`, `lower band #2`, `lower band #3`, `upper band #1`, `upper band #2`, `upper band #3`; d.ts L22481).

These are documented UI inputs, not verified constructor defaults. Standard formulas
are reference definitions; the capture does not establish exact TradingView seed,
smoothing or rendering parity.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- docs/TRADINGVIEW-REFERENCE.md — built-in indicator catalog and standard equations.
- https://www.tradingview.com/charting-library-docs/latest/indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
