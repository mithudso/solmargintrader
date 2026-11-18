---
id: tv_builtin_rank_correlation_index
name: "Rank Correlation Index"
kind: exposure-strategy
status: spec-only
family: momentum
summary: "Specification of Rank Correlation Index; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  length: {default: 12, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Rank Correlation Index

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

RCI=100*(1-6*sum((price_rank_i-time_rank_i)^2)/(n*(n*n-1))) without ties. With ties use corrected Spearman correlation; freeze orientation of time ranks.

## Documented inputs and source details

TradingView catalog inputs: `length`=12.

Catalog notes: (plots: `zero line`, `rci`; d.ts L25762).

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

https://www.tradingview.com/support/solutions/43000765570-rank-correlation-index-rci/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
The Rank Correlation Index (RCI) is an oscillator that helps traders gauge the directional consistency of price movements. It evaluates how closely prices follow a monotonic trend within a given lookback period. Unlike momentum oscillators that rely on differences in price levels, the RCI measures the correlation between bar indices and price ranks, making it sensitive to the relative ordering of prices rather than their absolute values.
````

````text
The RCI represents a scaled version of Spearman's rank correlation coefficient between prices and bar indices over a lookback period. To calculate the RCI value, the indicator:
````

````text
The source series that the indicator uses to calculate the RCI. By default, it uses the symbol's closing prices.
````
