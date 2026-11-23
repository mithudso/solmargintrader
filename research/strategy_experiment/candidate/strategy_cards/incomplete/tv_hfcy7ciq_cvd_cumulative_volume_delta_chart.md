---
id: tv_hfcy7ciq_cvd_cumulative_volume_delta_chart
name: "CVD - Cumulative Volume Delta (Chart)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of CVD - Cumulative Volume Delta (Chart); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# CVD - Cumulative Volume Delta (Chart)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays cumulative ​volume delta (​CVD) as an on-chart oscillator. It uses intrabar analysis to obtain more precise ​volume delta information compared to methods that only use the chart's timeframe.

> Volume delta is a measure that separates ​volume​ into "up" and "down" parts, then takes the difference to estimate the net demand for the asset. This approach gives traders a more detailed insight when analyzing volume​ and market sentiment. There are several methods for determining whether an asset's volume​ belongs in the "up" or "down" category. Some indicators, such as On Balance Volume​ and the Klinger Oscillator, use the change in price between bars to assign ​volume​ values to the appropriate category. Others, such as Chaikin Money Flow, make assumptions based on open, high, low, and c

> In the context where historical tick data is not yet available on TradingView, intrabar analysis is the most precise technique to calculate ​volume delta on historical bars on our charts. This indicator uses intrabar analysis to achieve a compromise between simplicity and accuracy in calculating ​volume delta on historical bars. Our Volume Profile indicators use it as well. Other ​volume delta indicators in our Community Scripts, such as the Realtime 5D Profile, use real-time chart updates to achieve more precise ​volume delta calculations. However, these indicators aren't suitable for analyzi

> The "cumulative" part of the indicator's name stems from the fact that calculations accumulate during a period of time. By periodically resetting the volume​ delta accumulation, we can analyze the progression of ​volume delta across manageable chunks, which is often more useful than looking at ​volume delta accumulated from the beginning of a chart's history.

> You can configure the reset period using the "CVD Resets" input, which offers the following selections:

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

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/hFcy7CIq-CVD-Cumulative-Volume-Delta-Chart/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
