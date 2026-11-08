---
id: tv_builtin_guppy_multiple_moving_average
name: "Guppy Multiple Moving Average"
kind: exposure-strategy
status: spec-only
family: trend
summary: "Specification of Guppy Multiple Moving Average; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  trader_ema_1_length: {default: 3, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  trader_ema_2_length: {default: 5, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  trader_ema_3_length: {default: 8, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  trader_ema_4_length: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  trader_ema_5_length: {default: 12, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  trader_ema_6_length: {default: 15, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  investor_ema_1_length: {default: 30, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  investor_ema_2_length: {default: 35, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  investor_ema_3_length: {default: 40, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  investor_ema_4_length: {default: 45, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  investor_ema_5_length: {default: 50, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  investor_ema_6_length: {default: 60, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Guppy Multiple Moving Average

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Plot six short EMAs (3,5,8,10,12,15) and six long EMAs (30,35,40,45,50,60). Ribbon separation/compression needs an explicit entry/exit rule. This is not the existing SMA ribbon at different periods.

## Documented inputs and source details

TradingView catalog inputs: `trader ema 1 length`=3; `trader ema 2 length`=5; `trader ema 3 length`=8; `trader ema 4 length`=10; `trader ema 5 length`=12; `trader ema 6 length`=15; `investor ema 1 length`=30; `investor ema 2 length`=35; `investor ema 3 length`=40; `investor ema 4 length`=45; `investor ema 5 length`=50; `investor ema 6 length`=60.

Catalog notes: (plots: `trader ema 1`, `trader ema 2`, `trader ema 3`, `trader ema 4`, `trader ema 5`, `trader ema 6`, `investor ema 1`, `investor ema 2`, `investor ema 3`, `investor ema 4`, `investor ema 5`, `investor ema 6`; d.ts L23977).

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
