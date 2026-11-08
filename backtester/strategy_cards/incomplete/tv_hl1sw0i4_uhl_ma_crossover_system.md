---
id: tv_hl1sw0i4_uhl_ma_crossover_system
name: "Uhl MA Crossover System"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Uhl MA Crossover System; not a tested trading strategy."
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
# Uhl MA Crossover System

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Today proposed indicator is based on the corrected moving average, an indicator originally proposed by Andreas Uhl professor at Salzburg University. This moving average is not the most well known, which is a pity since its design is extremely elegant.

> The corrected moving average (CMA) is an adaptive moving average based on exponential averaging and aim to correct common problems of classical moving averages such as crosses occurring during sideway markets, more details will be introduced in the calculation section. The CMA aim to act as a slow moving average in a moving average crossover system.

> Here a new fast adaptive moving average named corrected trend step (CTS) based on the CMA is introduced in order to provide a full moving average crossover system based on A. Uhl design.

> Even if the code is quite compact, the original idea behind the CMA can be blurry for some users, however it is actually relatively simple to understand. The CMA is based on exponential averaging and a smoothing variable is therefore required, in the CMA the calculation of the smoothing variable is based on the squared distance between the precedent CMA output and a simple moving average, and the rolling variance, where the rolling variance act as threshold.

> The CTS work the same way but instead of using the squared error between a simple moving average and the previous CMA output, we use the squared error between the closing price and the previous CTS output, this allow the CTS to better fit with the closing price. As said before the rolling variance act as threshold, if the squared error is lower than the rolling variance this mean that the CTS is close to the price, which can indicate a sideway market, therefore we should filter the entirety of the current price, therefore on sideways market the CTS is equal to the precedent value of the CTS.

> A moving average crossover system based on the corrected moving average proposed by Andreas Uhl has been presented, a new moving average that aim to produce good fits with the price has been created especially for this system. The logic behind the CMA has also been explained. A possible strategy analysis could be presented in the future.

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

- https://www.tradingview.com/script/Hl1Sw0I4-Uhl-MA-Crossover-System/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
