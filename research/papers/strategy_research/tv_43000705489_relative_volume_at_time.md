---
id: tv_43000705489_relative_volume_at_time
name: "Relative Volume at Time"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Relative Volume at Time; not a tested trading strategy."
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
# Relative Volume at Time

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Volume is the total amount of assets traded within a specific period of time. The Relative Volume at Time indicator compares the regular or cumulative volume at a particular moment within a period to its average over similar historical time points. This comparison helps identify uncharacteristically large fluctuations in trading activity relative to historical expectations at a given time.

> To understand the logic behind this indicator, one should first understand how it chooses the data points for its calculations. The indicator checks the time offset between the current bar and the start (anchor) of the most recent period, then selects the bars with corresponding time differences from a specified number of historical anchors. The indicator calculates the average volume using the selected data points from each period. The "Anchor Timeframe" input defines the size of each period. A new period begins whenever a new bar opens on the specified timeframe. The "Length" input governs t

> For example, suppose the Anchor Timeframe is one day, the Length is 5, and the chart uses the 30m timeframe. In this scenario, let's say each period starts at 9:30, and let's say the current time is 12:15, meaning the most recent bar's opening time is 12:00. In this case, the indicator will calculate the time offset of the last bar from the start of the current period (12:00 - 9:30 = 2 hours and 30 minutes), then find all bars over the last five days that opened 2.5 hours after the start of their respective periods. After that, it will calculate the average volume from these bars and plot the

> With Cumulative (by default), the indicator uses the total volume accumulated since the last period anchor. In the context of the example above, it would calculate the total volume in the current period from 9:30 to 12:15 and the average volume accumulation from 9:30-12:30 over five days.

> Note the current value will be lower than it should be in both cases, as the most recent bar is not yet closed. The difference is less significant when using Cumulative mode, especially on a period's latter bars, as the value on a bar represents the volume accumulated up to that point within the period. Switching to a lower timeframe can help improve the fidelity of the calculation by decreasing the time that the current bar remains open.

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

- https://www.tradingview.com/support/solutions/43000705489-relative-volume-at-time/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
