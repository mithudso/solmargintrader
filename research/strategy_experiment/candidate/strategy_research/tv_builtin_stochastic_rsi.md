---
id: tv_builtin_stochastic_rsi
name: "Stochastic RSI"
kind: exposure-strategy
status: spec-only
family: momentum
summary: "Specification of Stochastic RSI; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  lengthrsi: {default: 14, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  lengthstoch: {default: 14, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  smoothk: {default: 3, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  smoothd: {default: 3, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Stochastic RSI

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

raw=(RSI-min(RSI,lengthstoch))/(max(RSI,lengthstoch)-min(RSI,lengthstoch)); K=SMA(raw,smoothk); D=SMA(K,smoothd). Freeze 0..1 versus 0..100 scaling and zero-range behavior.

## Documented inputs and source details

TradingView catalog inputs: `lengthrsi`=14; `lengthstoch`=14; `smoothk`=3; `smoothd`=3.

Catalog notes: Input ids lengthrsi/lengthstoch/smoothk/smoothd. (plots: `upperlimit`, `lowerlimit`, `%k`, `%d`; d.ts L26530).

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

https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/anoCSnDIwWU??si=z_f3541zRGhOlACn&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>
````

````text
The Stochastic RSI indicator (Stoch RSI) is essentially an indicator of an indicator. It is used in technical analysis to provide a stochastic calculation to the RSI indicator. This means that it is a measure of RSI relative to its own high/low range over a user defined period of time. The Stochastic RSI is an oscillator that calculates a value between 0 and 1 which is then plotted as a line. This indicator is primarily used for identifying overbought and oversold conditions.
````

````text
Stoch RSI = (RSI - Lowest Low RSI) / (Highest High RSI - Lowest Low RSI)
````
