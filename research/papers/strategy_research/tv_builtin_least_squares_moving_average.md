---
id: tv_builtin_least_squares_moving_average
name: "Least Squares Moving Average"
kind: exposure-strategy
status: spec-only
family: trend
summary: "Specification of Least Squares Moving Average; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  length: {default: 25, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  offset: {default: 0, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Least Squares Moving Average

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Fit y_i=a+b*i by least squares on the trailing length closes; output a+b*(length-1+offset). Do not fit on future bars.

## Documented inputs and source details

TradingView catalog inputs: `length`=25; `offset`=0.

Catalog notes: (plots: `plot`; d.ts L24585).

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

https://www.tradingview.com/support/solutions/43000599877-least-squares-moving-average/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
Least Squares Moving Average is a curve showing linear regression calculations. On each bar, the indicator displays a linear regression based on the prices for a period that is specified by the Length value in settings.
````

````text
indicator(title = "Least Squares Moving Average", shorttitle="LSMA", overlay=true, timeframe="", timeframe_gaps=true)
````

````text
The Least Squares Moving Average can be used as a trend indicator and reversal indicator. It is used as an alternative to other traditional indicators like the moving average or exponential moving average. The Least Squares Moving Average has a different calculation than both of those moving averages. The indicator displays a linear regression based on the prices for a specific period of time. This period of time can be defined in the indicator settings.
````
