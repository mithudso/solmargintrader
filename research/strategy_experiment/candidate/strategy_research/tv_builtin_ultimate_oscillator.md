---
id: tv_builtin_ultimate_oscillator
name: "Ultimate Oscillator"
kind: exposure-strategy
status: spec-only
family: momentum
summary: "Specification of Ultimate Oscillator; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  length7: {default: 7, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  length14: {default: 14, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  length28: {default: 28, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Ultimate Oscillator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

BP=C-min(L,C[1]); TR=max(H,C[1])-min(L,C[1]); A_k=sum(BP,k)/sum(TR,k); UO=100*(4*A7+2*A14+A28)/7. Lengths are configurable.

## Documented inputs and source details

TradingView catalog inputs: `length7`=7; `length14`=14; `length28`=28.

Catalog notes: (plots: `uo`; d.ts L26816).

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

https://www.tradingview.com/support/solutions/43000502328-ultimate-oscillator-uo/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/xvE5NIryoyA?&wmode=opaque" frameborder="0" allowfullscreen=""></iframe>
````

````text
The Ultimate Oscillator indicator (UO) indicator is a technical analysis tool used to measure momentum across three varying timeframes. The problem with many momentum oscillators is that after a rapid advance or decline in price, they can form false divergence trading signals. For example, after a rapid rise in price, a bearish divergence signal may present itself, however price continues to rise. The ultimate Oscillator attempts to correct this by using multiple timeframes in its calculation as opposed to just one timeframe which is what is used in most other momentum oscillators.
````

````text
There are three steps to calculating the Ultimate Oscillator. This example uses 7, 14, 28 parameters:
````
