---
id: tv_builtin_know_sure_thing
name: "Know Sure Thing"
kind: exposure-strategy
status: spec-only
family: momentum
summary: "Specification of Know Sure Thing; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  roclen1: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  roclen2: {default: 15, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  roclen3: {default: 20, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  roclen4: {default: 30, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  smalen1: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  smalen2: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  smalen3: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  smalen4: {default: 15, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  siglen: {default: 9, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Know Sure Thing

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

KST = 1*SMA(ROC(C,r1),s1)+2*SMA(ROC(C,r2),s2)+3*SMA(ROC(C,r3),s3)+4*SMA(ROC(C,r4),s4); signal=SMA(KST,siglen).

## Documented inputs and source details

TradingView catalog inputs: `roclen1`=10; `roclen2`=15; `roclen3`=20; `roclen4`=30; `smalen1`=10; `smalen2`=10; `smalen3`=10; `smalen4`=15; `siglen`=9.

Catalog notes: Inputs roclen1..4, smalen1..4, siglen. (plots: `zero`, `kst`, `signal`; d.ts L24484).

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

https://www.tradingview.com/support/solutions/43000502329-know-sure-thing-kst/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
The Know Sure Thing indicator (KST) is a momentum based oscillator. KST is based on Rate of Change (ROC). Know Sure Thing takes four different timeframes of ROC and smooth's them out using Simple Moving Averages. KST then calculates a final value that fluctuates between positive and negative values above and below a Zero Line. There is also a signal line which is an SMA of the KST line itself. Essentially, the Know Sure Thing Indicator measures the momentum of four separate price cycles. Technical Analysts use this information to spot divergences, overbought and oversold conditions and crossov
````

````text
This calculation is using the default parameters in Tradingview of 10,15,20,30,10,10,10,15,9.
````

````text
The final number (9) is the SMA length to be used in calculating the signal line.
````
