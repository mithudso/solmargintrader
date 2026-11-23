---
id: tv_nlm312nk_cvd_cumulative_volume_delta_candles
name: "CVD - Cumulative Volume Delta Candles"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of CVD - Cumulative Volume Delta Candles; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# CVD - Cumulative Volume Delta Candles

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays cumulative ​volume delta in candle form. It uses intrabar information to obtain more precise ​volume delta information than methods using only the chart's timeframe.

> The ​volume delta concept divides a bar's ​volume in "up" and "down" ​volumes. The delta is calculated by subtracting down ​volume from up ​volume. Many calculation techniques exist to isolate up and down ​volume within a bar. The simplest techniques use the polarity of interbar price changes to assign their ​volume to up or down slots, e.g., On Balance Volume or the Klinger Oscillator. Others such as Chaikin Money Flow use assumptions based on a bar's OHLC values. The most precise calculation method uses tick data and assigns the ​volume of each tick to the up or down slot depending on whethe

> This indicator uses intrabar analysis to achieve a compromise between the simplest and most precise methods of calculating ​volume delta. In the context where historical tick data is not yet available on TradingView, intrabar analysis is the most precise technique to calculate ​volume delta on historical bars on our charts. Our Volume Profile indicators use it. Other ​volume delta indicators in our Community Scripts such as the Realtime 5D Profile use realtime chart updates to achieve more precise ​volume delta calculations, but that method cannot be used on historical bars, so those indicator

> Cumulative ​Volume Delta Candles present ​volume delta information as it evolves during a period of time.

> • open: Each candle's' open level is the cumulative ​volume delta for the current period at the start of the bar.

> Traders using ​volume information should understand the ​volume data they are using: where it originates and what transactions it includes, as this can vary with instruments, sectors, exchanges, timeframes, and between historical and realtime bars. The information used to build a chart's bars and display ​volume comes from data providers (exchanges, brokers, etc.) who often maintain distinct feeds for intraday and ​end-of-day (​EOD) timeframes. How ​volume data is assembled for the two feeds depends on how instruments are traded in that sector and/or the ​volume reporting policy for each feed.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_doji`, `tv_method_volume_delta`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/NlM312nK-CVD-Cumulative-Volume-Delta-Candles/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
