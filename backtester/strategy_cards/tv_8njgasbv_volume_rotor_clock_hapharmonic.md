---
id: tv_8njgasbv_volume_rotor_clock_hapharmonic
name: "Volume Rotor Clock [hapharmonic]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Volume Rotor Clock [hapharmonic]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Volume Rotor Clock [hapharmonic]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Volume Rotor Clock is an indicator that separates buy and sell volume, compiling these volumes over a recent number of bars or a specified past period, as defined by the user. This helps to reveal accumulation (buying) or distribution (selling) behavior, showing which side has superior volume. With its unique and beautiful display, the Volume Rotor Clock is more than just a timepiece; it's a dynamic dashboard that visualizes the buying and selling pressure of your favorite symbols, all wrapped in an elegant and fully customizable interface.

> Green Circles (Bulls - Upper Half): These represent symbols from your list where the total buy volume is greater than the total sell volume over the defined "Lookback" period. They are considered to be under bullish accumulation. The size of the circle and its text grows larger as the buy percentage becomes more dominant. The percentage shown within the circle represents the buy volume's share of the total volume, calculated over the 'Lookback (Bars)' you've set.

> Red Circles (Bears - Lower Half): These represent symbols where the total sell volume is greater than the total buy volume. They are considered to be under bearish distribution or selling pressure. The size of the circle indicates the dominance of the sell-side volume. The percentage shown within the circle represents the sell volume's share of the total volume, calculated over the 'Lookback (Bars)' you've set.

> What it Means: A symbol appears here when it shows signs of sustained, high-volume buying interest. It's a way to filter out noise and focus on assets with potentially significant accumulation phases.

> (You can configure `X` (Volume MA Length) and `Y` (Consecutive Days Above MA) in the settings.)

> The Volume Rotor Clock is highly customizable. Here’s a detailed walkthrough of every setting available in the "Inputs" tab.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_volume_delta`.

## Data and availability

Required inputs: ohlcv, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/8nJGAsbV-Volume-Rotor-Clock-hapharmonic/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
