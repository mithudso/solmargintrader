---
id: tv_builtin_klinger_oscillator
name: "Klinger Oscillator"
kind: exposure-strategy
status: spec-only
family: volume
summary: "Specification of Klinger Oscillator; not a tested trading strategy."
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
# Klinger Oscillator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

KO = EMA(volume_force,fast)-EMA(volume_force,slow); signal=EMA(KO,signal_length). Volume-force sign, cumulative measurement and reset conventions must be recovered; none are supplied by the captured catalog.

## Documented inputs and source details

TradingView catalog inputs: none listed.

Catalog notes: (plots: `plot`, `signal`; d.ts L24456).

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

https://www.tradingview.com/support/solutions/43000589157-klinger-oscillator/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
Its goal is to show the differences in two moving averages that are not only based on price, but on other factors as well. These moving averages are also based on timeframe and the periods that are most commonly analyzed remain periods 34 and 55. Traders and investors watch the oscillator closely for indicator divergence that may point towards security price reversals in the market.
````

````text
The formula for the Klinger oscillator and the steps on how to calculate it are as follows.
````

````text
When an asset or security is above its 100-period moving average and the oscillator is above (or is on its way to moving above) zero, this is a good example of an uptrend. Traders and investors might feel more inclined to buy when the oscillator moves above the signal line from below. It’s worth noting that Stephen Klinger himself found it most beneficial to take a long position when a stock was in an uptrend and then dropped to below zero only to move above the signal line yet again. This can often point towards a fall in prices. Keep this in mind when analyzing the markets with the Klinger o
````
