---
id: tv_builtin_mass_index
name: "Mass Index"
kind: exposure-strategy
status: spec-only
family: volatility
summary: "Specification of Mass Index; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  length: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Mass Index

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

A conventional Mass Index sums EMA(H-L,9)/EMA(EMA(H-L,9),9) over 25 bars. The catalog exposes a single length=10 input instead; recover its actual meaning before claiming parity.

## Documented inputs and source details

TradingView catalog inputs: `length`=10.

Catalog notes: (plots: `plot`; d.ts L24874).

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

## Official help clarification

https://www.tradingview.com/support/solutions/43000589169-mass-index/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
Mass index is a technical analysis indicator that is used to examine the differences between high and low stock prices over a specific period of time. The index proposes that a trend reversal may be imminent when there is a larger difference between stock prices, and then this difference recedes.
````

````text
The mass index was developed and introduced by Donald Dorsey in the beginning of the 1990s. Dorsey initially thought that when the calculation resulted in a figure above 27 and then dropped a point and a half below (to 26.5), the stock would be ready to change direction. This result would create a “bulge” of sorts. It has been determined that an index of 27 showcases stock volatility, causing some traders to lower their baseline when expecting a price bulge.
````

````text
To calculate the mass index, check the formula below.
````
