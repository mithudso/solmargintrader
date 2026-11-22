---
id: tv_yg0rpnzo_efficient_work_lucf
name: "Efficient Work [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Efficient Work [LucF]; not a tested trading strategy."
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
# Efficient Work [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Efficient Work measures the ratio of price movement from close to close (resulting work) over the distance traveled to the high and low before settling down at the close (total work). The closer the two values are, the more Efficient Work approaches its maximum value of +1 for an up move or -1 for a down move. When price does not change, Efficient Work is zero.

> Higher values of Efficient Work indicate more efficient price travel between the close of two successive bars, which I interpret to be more significant, regardless of the move's amplitude. Because it measures the direction and strength of price changes rather than their amplitude, Efficient Work may be thought of as a sentiment indicator.

> Two progressively higher timeframes are used to calculate larger-context values for the oscillator. The rationale underlying the use of timeframes higher than the chart's is that, while they change less frequently than the values calculated at the chart's resolution, they are more meaningful because more work (trader activity) is required to calculate them. Combining the immediacy of values calculated at the chart's resolution to higher timeframe values achieves a compromise between responsiveness and reliability.

> • Bull/bear markers can be displayed. They occur whenever a new bull/bear state is determined by the "Main Line Coloring Conditions".

> • An alert can be defined for the script. The alert will trigger whenever a bull/bear marker appears in the indicator's display.

> • An invisible plot named "BTE Signal" is provided. It can be used as an entry signal when connected to the PineCoders Backtesting & Trading Engine as an external input.

> It will generate an entry whenever a marker is displayed.

> • An aggregate line calculated using a weighed average of the three previous lines (see the Aggregate Weights section of Inputs to configure the weights).

> • The color of lines 2 and 3 are fixed but can be set in the "Colors" section of Inputs.

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

- https://www.tradingview.com/script/yG0rpNzO-Efficient-Work-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
