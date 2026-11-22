---
id: tv_zkbuifk7_delta_volume_channels_lucf
name: "Delta Volume Channels [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Delta Volume Channels [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Delta Volume Channels [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays on-chart visuals aimed at making the most of delta ​volume information. It can color bars and display two channels: one for delta ​volume, another calculated from the price levels of bars where delta ​volume divergences occur. Markers and alerts can also be configured using key conditions, and filtered in many different ways. The indicator caters to traders who prefer chart visuals over raw values. It will work on historical bars and in real time, using intrabar analysis to calculate delta ​volume in both conditions.

> ​The ​volume delta concept divides a bar's ​volume in "up" and "down" ​volumes. The delta is calculated by subtracting down ​volume from up ​volume. Many calculation techniques exist to isolate up and down ​volume within a bar. The simplest techniques use the polarity of interbar price changes to assign their ​volume to up or down slots, e.g., On Balance Volume or the Klinger Oscillator. Others such as Chaikin Money Flow use assumptions based on a bar's OHLC values. The most precise calculation method uses tick data and assigns the ​volume of each tick to the up or down slot depending on wheth

> This indicator uses intrabar analysis to achieve a compromise between the simplest and most precise methods of calculating ​volume delta. In the context where historical tick data is not yet available on TradingView, intrabar analysis is the most precise technique to calculate ​volume delta on historical bars on our charts. TradingView's Volume Profile built-in indicators use it, as do the CVD - Cumulative ​Volume Delta Candles and CVD - Cumulative Volume Delta (Chart) indicators published from the TradingView account. My Volume Delta Columns Pro indicator also uses intrabar analysis. Other ​v

> In this section, you can also enable a mode where an attempt is made to estimate the channel's bias before price breaches the channel. When it is enabled, successive increases/decreases of the channel's top and bottom levels are counted as new divergences occur. When one count is greater than the other, a bull/bear bias is inferred from it.

> The aim of the ​DV channel is to provide a visual representation of the buying/selling pressure calculated using delta ​volume. The simplest characteristic of the channel is its bull/bear state. One can then distinguish between its bull and strong bull states, as transitions from strong bull to bull states will generally happen when buyers are losing steam. While one should not infer a reversal from such transitions, they can be a good place to tighten stops. Only time will tell if a reversal will occur. One or more divergences will often occur before reversals.

> At its simplest, one way to use this indicator would be to look for overlaps of the strong bull/bear colors in both the ​DV channel and a divergence channel, as these identify points where price is breaching the divergence channel when buy/sell pressure is consistent with the direction of the breach. I have highlighted all those points in the chart below. Not all of them would have produced profitable trades, but nothing is perfect in the markets. Also, keep in mind that the circles identify the visual you would be looking for — not the trade's entry level.

> The ​​DV channel is the space between two moving averages: the reference line and a DV%-weighted version of that reference. The reference line is a moving average of a type, source and length which you select. The DV%-weighted line uses the same settings, but it averages the DV%-weighted price source.

> The default settings use an Arnaud-Legoux moving average on the close and a length of 20 bars. The DV%-weighted version of it uses a combination of DV% and relative ​volume to calculate the ultimate weight applied to the reference. The DV%-weighted line is capped to 5 standard deviations of the reference. The lower timeframe used to access intrabars automatically adjusts to the chart's timeframe and achieves optimal balance between the number of intrabars inspected in each chart bar, and the number of chart bars covered by the script's calculations.

> Markers only appear on bar closes, so they will not repaint. Keep in mind, when looking at markers on historical bars, that they are positioned on the bar when it closes — NOT when it opens.

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

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/zkBuiFk7-Delta-Volume-Channels-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
