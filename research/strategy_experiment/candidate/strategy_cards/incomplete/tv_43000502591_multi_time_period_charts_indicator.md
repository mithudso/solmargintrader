---
id: tv_43000502591_multi_time_period_charts_indicator
name: "Multi-Time Period Charts indicator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Multi-Time Period Charts indicator; not a tested trading strategy."
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
# Multi-Time Period Charts indicator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Multi-Time Period Charts (MTPC) indicator displays data from higher-timeframe (HTF) bars directly on the chart. It draws color-coded boxes representing HTF ranges based on standard prices or Heikin Ashi values, enabling multi-timeframe bar analysis without the need to change the chart's timeframe or type.

> The indicator calculates bar ranges for an automatically selected timeframe or a specified timeframe, depending on the "Auto-timeframe" input. The table below shows which higher timeframe the indicator selects, based on the chart timeframe, when "Auto-timeframe" is enabled:

> Using standard or Heikin Ashi data for the selected higher timeframe, the indicator draws boxes showing price ranges for successive HTF bars. Each box begins on the chart bar where the HTF period opens, and ends on the bar where the period closes. The ranges that the boxes show for each HTF bar depend on the selected "Calculation" setting:

> If selected, the indicator automatically chooses the higher timeframe of the calculation based on the timeframe of the current chart, using the logic described in the first table from the previous section. If not selected, the indicator uses the timeframe specified by the "Timeframe" input instead.

> The higher timeframe that the indicator uses when "Auto-timeframe" is not selected. This input provides direct control over the calculation timeframe for cases where the automatic selection does not fit your needs.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_heikin_ashi`.

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

- https://www.tradingview.com/support/solutions/43000502591-multi-time-period-charts-indicator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
