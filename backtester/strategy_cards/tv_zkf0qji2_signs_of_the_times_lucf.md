---
id: tv_zkf0qji2_signs_of_the_times_lucf
name: "Signs of the Times [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Signs of the Times [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Signs of the Times [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This oscillator calculates the directional strength of bars using a primitive weighing mechanism based on a small number of what I consider to be fundamental properties of a bar. It does not consider the amplitude of price movements, so can be used as a complement to momentum-based oscillators. It thus belongs to the same family of indicators as my Bar Balance, ​Volume Ticks, Efficient work, ​Volume Buoyancy or my Delta ​Volume indicators.

> The calculations underlying Signs of the Times (SOTT) use a simple, oft-explored concept: measure bar attributes, assign a weight to them, and aggregate results to provide an evaluation of a bar's directional strength. Bull and bear weights are added independently, then subtracted and divided by the maximum possible weight, so the final calculation looks like this:[pine]

> You can see the code used to calculate SOTT in my ta library's `sott()` function.

> • An Arnaud-Legoux moving average of length 20 of the instant SOTT value. This is the signal line.

> • A channel between the signal line and its MA (a simple MA of length 20), which can be one of four colors:

> Remember that Signs of the Times evaluates directional bar strength — not price movement. Its highs and lows do not reflect price, but the strength of chart bars. The fact that SOTT knows nothing of how far price moves or of trends is easy to forget. As such, I think SOTT is best used as a confirmation tool. Chart movements may appear to be easy to read when looking at historical bars, but when you have to make go-no-go decisions on the last bar, the landscape often becomes murkier. By providing a quantitative evaluation of the strength of the last few bars, which is not always easily discerni

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history.
The complete point-in-time input set has not been verified in the repository. Do not substitute current snapshots or inferred values for historical inputs.

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

- https://www.tradingview.com/script/ZKF0qji2-Signs-of-the-Times-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
