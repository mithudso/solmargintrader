---
id: tv_wvcqygsx_mtf_oscillator_framework_pinecoders
name: "MTF Oscillator Framework [PineCoders]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of MTF Oscillator Framework [PineCoders]; not a tested trading strategy."
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
# MTF Oscillator Framework [PineCoders]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This framework allows Pine coders to quickly build a complete multi-timeframe oscillator from any calculation producing values around a centerline, whether the values are bounded or not. Insert your calculation in the script and you have a ready-to-publish MTF Oscillator offering a plethora of presentation options and features.

> 1 — Insert your calculation in the `f_signal()` function at the top of the "Helper Functions" section of the script.

> 4 — If you want to publish the script, copy/paste the following description in your new publication's description and replace the "OVERVIEW" section with a description of your calculations.

> • Bull/bear markers can be displayed. They occur whenever a new bull/bear state is determined by the "Main Line Coloring Conditions".

> • An alert can be defined for the script. The alert will trigger whenever a bull/bear marker appears in the indicator's display.

> • An invisible plot named "BTE Signal" is provided. It can be used as an entry signal when connected to the PineCoders Backtesting & Trading Engine as an external input.

> It will generate an entry whenever a marker is displayed.

> The True Range calculation appeared for the first time in J. Welles Wilder's New Concepts in Technical Trading Systems book published in 1978. Wilder's objective was to provide a reliable measure of the effective movement—or range—between two bars, to measure volatility. True Range is also the building block used to calculate ATR (Average True Range), which calculates the average of True Range values over a given period using the `rma` averaging method—the same used in the calculation of another of Wilder's remarkable creations: RSI.

> • An aggregate line calculated using a weighed average of the three previous lines (see the Aggregate Weights section of Inputs to configure the weights).

> • Repainting can be controlled separately for the chart's value and the higher timeframe values.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

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

- https://www.tradingview.com/script/Wvcqygsx-MTF-Oscillator-Framework-PineCoders/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
