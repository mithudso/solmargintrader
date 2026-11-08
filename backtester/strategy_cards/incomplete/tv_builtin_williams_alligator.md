---
id: tv_builtin_williams_alligator
name: "Williams Alligator"
kind: exposure-strategy
status: spec-only
family: trend
summary: "Specification of Williams Alligator; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  jaw_length: {default: 21, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  teeth_length: {default: 13, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  lips_length: {default: 8, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  jaw_offset: {default: 8, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  teeth_offset: {default: 5, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  lips_offset: {default: 3, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Williams Alligator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Jaw, teeth and lips are smoothed median-price averages with their respective lengths and positive display offsets. Read only values actually known at decision time; do not treat a shifted drawing as a future forecast.

## Documented inputs and source details

TradingView catalog inputs: `jaw length`=21; `teeth length`=13; `lips length`=8; `jaw offset`=8; `teeth offset`=5; `lips offset`=3.

Catalog notes: (plots: `jaw`, `teeth`, `lips`; d.ts L27392).

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

https://www.tradingview.com/support/solutions/43000592305-williams-alligator/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
The Williams Alligator indicator uses the Simple Moving Average (SMA) indicator in its calculation to add more smoothed averages to the result that generally slow down indicator turns. The indicator uses three smoothed Moving Averages (MAs) set at periods that are Fibonacci numbers: five, eight, and 13.
````

````text
The calculation for the Williams Alligator indicator is represented below by the following formula:
````

````text
SUM1: The sum of closing prices for n amount of periods
````
