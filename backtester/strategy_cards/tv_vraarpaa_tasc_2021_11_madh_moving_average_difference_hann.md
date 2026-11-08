---
id: tv_vraarpaa_tasc_2021_11_madh_moving_average_difference_hann
name: "TASC 2021.11 MADH Moving Average Difference, Hann"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2021.11 MADH Moving Average Difference, Hann; not a tested trading strategy."
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
# TASC 2021.11 MADH Moving Average Difference, Hann

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Presented here is code for the "Moving Average Difference, Hann" indicator originally conceived by John ​Ehlers. The code is also published in the November 2021 issue of Trader's Tips by Technical Analysis of Stocks & ​Commodities (TASC) magazine.

> The source price is used in two independent Hann windowed FIR filters having two different periods (lengths) of historical observation for calculation, one being a "Short Length" and the other termed "Dominant Cycle". These are then passed to a "rate of change" calculation and then returned by the reusable function. The secret ​sauce is that a "windowed Hann FIR filter" is superior tp a generic SMA filter, and that ultimately reveals Ehlers' clever enhancement. We'll have to wait and see what ingenuities ​Ehlers has next to unleash. Stay tuned...

> The `madh()` function code was optimized for computational efficiency in Pine, differing visibly from ​Ehlers' original formula, but yielding the same results as ​Ehlers' version.

> By employing a Hann windowed finite impulse response filter (FIR), John ​Ehlers has enhanced the Moving Average Difference (MAD) to provide an oscillator with exceptional smoothness.

> Three values in the script's "Settings/Inputs" provide control over the oscillators behavior:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_fourier_cycle`.

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

- https://www.tradingview.com/script/vraaRpAA-TASC-2021-11-MADH-Moving-Average-Difference-Hann/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
