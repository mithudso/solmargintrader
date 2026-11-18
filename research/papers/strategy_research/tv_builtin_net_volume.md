---
id: tv_builtin_net_volume
name: "Net Volume"
kind: exposure-strategy
status: spec-only
family: volume
summary: "Specification of Net Volume; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Net Volume

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

A conventional estimate assigns +V to an up close and -V to a down close, with a declared tie rule. It is not exchange aggressor buy volume minus sell volume unless true trade-side data is supplied.

## Documented inputs and source details

TradingView catalog inputs: none listed.

Catalog notes: (plots: `plot`; d.ts L25533).

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

https://www.tradingview.com/support/solutions/43000589192-net-volume/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
Net volume is calculated by deducting the uptick volume of a security or asset by the security’s downtick volume over a period of time chosen by the trader. It separates itself from other volume indicators because it makes a clear distinction between whether a market is bullish or bearish. Traders will most likely see net volume displayed below the price chart and bars will display its value for each given period that is plotted on the chart.
````

````text
Net volume can be used to gauge, measure, and determine the strength and volume of buying or selling pressure. It is a different way to visualize where the buyers and sellers are putting the most money to work at any given moment. Net volume can be compared and contrasted volume, which just shows total shares traded. However, Net volume is different in its calculation using uptick and downtick and its presentation on the chart.
````

````text
Traders usually use the net volume indicator to determine market direction and sentiment apart from standard volume values. A positive net volume may show that uptick and buying pressure is exceeding downtick and selling pressure in an asset. A negative net volume may show the opposite. Net volume is meant to gauge the selling or buying pressure of an asset during a specific period of time.
````
