---
id: tv_qetnobdk_half_causal_estimator
name: "Half Causal Estimator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Half Causal Estimator; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Half Causal Estimator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Half Causal Estimator is a specialized filtering method that provides responsive averages of market variables (volume, true range, or price change) with significantly reduced time delay compared to traditional moving averages. It employs a hybrid approach that leverages both historical data and time-of-day patterns to create a timely representation of market activity while maintaining smooth output.

> Traditional moving averages suffer from time lag, which can delay signals and reduce their effectiveness for real-time decision making. The Half Causal Estimator addresses this limitation by using a non-causal filtering method that incorporates recent historical data (the causal component) alongside expected future behavior based on time-of-day patterns (the non-causal component).

> The indicator operates through several coordinated steps. First, it stores and organizes market data by specific times of day (minutes/hours). Then it builds a profile of typical behavior for each time period. For calculations, it creates a filtering window where half consists of recent actual data and half consists of expected future values based on historical time-of-day patterns. Finally, it applies a kernel-based smoothing function to weight the values in this composite window.

> This dual approach allows the filter to respond more quickly to changing market conditions while maintaining smoothness. The name "Half Causal" refers to this hybrid methodology—half of the data window comes from actual historical observations, while the other half is derived from time-of-day patterns observed over multiple days. By incorporating these "future" values from past patterns, the estimator can reduce the inherent lag present in traditional moving averages.

> The benefit of using this "average future data" approach is that it counteracts the lag inherent in traditional moving averages. In a standard moving average, recent price action is underweighted because older data points hold equal influence. By incorporating time-of-day averages for future periods, the Half Causal Estimator essentially shifts the center of the filter window closer to the current bar, resulting in more timely outputs while maintaining smoothing benefits.

> This approach is particularly effective because market variables like volume, true range, and price changes tend to follow recognizable intraday patterns (they are positive values without DC components). By leveraging these patterns, the indicator doesn't try to predict future values in the traditional sense, but rather incorporates the average historical behavior at those future times into the current estimate.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_seasonality`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/script/QETnobDk-Half-Causal-Estimator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
