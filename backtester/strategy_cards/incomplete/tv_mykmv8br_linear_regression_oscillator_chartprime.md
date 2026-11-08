---
id: tv_mykmv8br_linear_regression_oscillator_chartprime
name: "Linear Regression Oscillator [ChartPrime]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Linear Regression Oscillator [ChartPrime]; not a tested trading strategy."
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
# Linear Regression Oscillator [ChartPrime]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Linear Regression Oscillator is a custom TradingView indicator designed to provide insights into potential mean reversion and trend conditions. By calculating a linear regression on the closing prices over a user-defined period, this oscillator helps identify overbought and oversold levels and highlights trend changes. The indicator also offers visual cues and color-coded price bars to aid in quick decision-making.

> Description: Determines the period over which the linear regression is calculated. A longer period smooths the oscillator but may lag, while a shorter period is more responsive but may be noisier.

> Description: Option to color the price bars based on the oscillator's value, providing a visual representation of market conditions. Bars turn cyan for positive oscillator values and blue for negative.

> Pay attention to the symbols and labels on the chart indicating mean reversion and trend changes. These signals are designed to highlight potential entry and exit points.

> Use the plotted invalidation levels as stop-loss or signal invalidation points. If the price moves beyond these levels, the current trend signal is likely invalid.

> Description: Define the upper and lower bounds for identifying overbought and oversold conditions. Values outside these thresholds suggest potential reversals.

> Tracks the highest and lowest prices over a recent period to set levels where the current trend signal would be considered invalidated.

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

- https://www.tradingview.com/script/MyKmv8br-Linear-Regression-Oscillator-ChartPrime/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
