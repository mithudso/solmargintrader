---
id: tv_builtin_arnaud_legoux_moving_average
name: "Arnaud Legoux Moving Average"
kind: exposure-strategy
status: spec-only
family: trend
summary: "Specification of Arnaud Legoux Moving Average; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  window_size: {default: 9, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  offset: {default: 0.85, type: "float", desc: "Documented TradingView input; not an optimized strategy setting"}
  sigma: {default: 6, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Arnaud Legoux Moving Average

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

ALMA = sum(w_i*x_i)/sum(w_i), w_i=exp(-(i-m)^2/(2*s^2)), m=offset*(n-1), s=n/sigma, i=0..n-1.

## Documented inputs and source details

TradingView catalog inputs: `window size`=9; `offset`=0.85; `sigma`=6.

Catalog notes: (plots: `plot`; d.ts L22644).

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

https://www.tradingview.com/support/solutions/43000594683-arnaud-legoux-moving-average/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
The Arnaud Legoux Moving Average (ALMA) is different from other moving averages because of its specific design to use Gaussian distribution that is shifted with a calculated offset in order for the average to be biased towards more recent days, instead of more evenly centered on the window. Built on the generalized Moving Average Framework, ALMA is able to use various indicators in conjunction with its own capabilities and run on multiple time frames, with the inclusion of custom bar types.
````

````text
To calculate the Arnaud Legoux Moving Average (ALMA) you’ll first need to compute a weighted sum of the window's size using your input series and weights given by a Gaussian function with a peak value determined by the offset, and a width determined by sigma.
````

````text
Window: This element is the period. By default, the window is set to 9 periods, but it can be customized to fit any trading style.
````
