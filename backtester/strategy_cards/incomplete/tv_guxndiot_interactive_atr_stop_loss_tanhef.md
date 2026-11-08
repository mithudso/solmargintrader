---
id: tv_guxndiot_interactive_atr_stop_loss_tanhef
name: "Interactive ATR Stop-Loss [TANHEF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Interactive ATR Stop-Loss [TANHEF]; not a tested trading strategy."
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
# Interactive ATR Stop-Loss [TANHEF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator is "Interactive" which means some inputs can are manually added through the first click after adding the indicator to the chart (ATR Trailing Stop-loss start point). See images below for more explanation.

> The ATR Stop Loss plotted. Note that the trailing value that is considered as the stop loss value is the value of the ATR from the prior candle. The settings for the ATR calculation can be modified within the settings.

> A trailing stop-loss provides an exit when price moves against you but also enables you to move the exit point further into profit when price is moving in the desired direction of a trade. The ATR (Average True Range) which is used to measure volatility, is very effective at functioning as a trailing stop loss.

> Initially when this indicator is added to the chart, you will be prompted to select where to begin the ATR Trailing Stop-loss.

> An optional fixed profit target can be added within the settings. This profit target will only actively be plotted when the ATR Trailing Stop-loss has not be hit hit yet or until the profit target has been hit.

> Here shows that the profit target was hit, then later on the ATR Trailing Stop-loss was hit.

> Note, trailing stop-loss will continue to be plotted until it has been hit regardless of the profit target being hit or not.

> After this indicator is placed, it can be modified via dragging or from within the settings by modifying the time and the price input. Or simply re-add the indicator to the chart.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_atr_trailing`, `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/gUXnDioT-Interactive-ATR-Stop-Loss-TANHEF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
