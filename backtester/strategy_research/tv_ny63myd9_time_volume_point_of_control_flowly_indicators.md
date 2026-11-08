---
id: tv_ny63myd9_time_volume_point_of_control_flowly_indicators
name: "Time & volume point of control / Flowly Indicators"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Time & volume point of control / Flowly Indicators; not a tested trading strategy."
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
# Time & volume point of control / Flowly Indicators

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> TPOC (time point of control) and VPOC (volume point of control) are points in price where highest amount of time/volume was traded. This is considered key information in a market profile, as it shows where market participant interest was highest. Unlike full fledged market profile that shows total time/volume distribution, this script shows the points of control for each candle, plotted with a line (time) and a dot (volume). The script hides your candles/bars by default and forms a line in the middle representing candle range. In case of candles, borders will still be visible. This feature can

> Timeframe settings can be changed via input menu. The lower the timeframe, the more precision you get but with the cost of less historical data and slower loading time. Users can also choose which source to use for determining price for points of control, e.g. using close as source, the point of control is set to match the value of lower timeframe candle close. This could be replaced with OHLC4 for example, resulting in a point of control based on OHLC average.

> VPOC is defined by fetching lower timeframe candle with the most amount of volume traded and using its close (by default) as a mark for point of control. For TPOC, each candle is divided into 10 lots which are used for calculating amount of closes taking place within the bracket values. The lot with highest amount of closes will be considered a point of control. This mark is displayed in the middle point of a lot:

> To identify more profound points of market participant interest, TPOC & VPOC as percentage of total time/volume thresholds can be set via input menu. When a point of control is equal to or greater than the set percentage threshold, visual elements will be highlighted in a different color, e.g. 50% VPOC threshold will activate a highlight whenever volume traded at VPOC is equal to or greater than 50% of total volume. All colors are customizable.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_market_profile`.

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

- https://www.tradingview.com/script/nY63MyD9-Time-volume-point-of-control-Flowly-Indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
