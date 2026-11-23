---
id: tv_xh8tldte_realtime_delta_volume_action_lucf
name: "Realtime Delta Volume Action [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Realtime Delta Volume Action [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, level2-orderbook-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Realtime Delta Volume Action [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays on-chart, realtime, delta volume​ and delta ticks information for each bar. It aims to provide traders who trade price action on small timeframes with volume​ and tick information gathered as updates come in the chart's feed. It builds its own candles, which are optimized to display volume​ delta information. It only works in realtime.

> The information calculated by the indicator cannot be saved on charts, nor can it be recalculated from historical bars.

> This script monitors each realtime update of the chart's feed. It first determines if price has moved up or down since the last update. The polarity of the price change, in turn, determines the polarity of the volume​​ and tick for that specific update. If price does not move between consecutive updates, then the last known polarity is used. Using this method, we can calculate a running volume​ delta and ticks delta for the bar, which becomes the bar's final​ delta values when the bar closes (you can inspect values of elapsed realtime bars in the Data Window or the indicator's values). Note th

> What are strong bars? They are an attempt to identify significance. They are like a default marker, except that instead of displaying "Mx▲/▼" below/above the bar, the candle's body is outlined in bright​ bull/bear color when one is detected. Strong bars require a respectable amount of conditions to be met (you can see and re-configure them in the inputs). Think of them as pushes rather than indications of an upcoming, strong and multi-bar move. Pushes do, for sure, often occur at the beginning of strong trends. You will often see a few strong bars occur at 2-3 bar intervals at the beginning or

> To traders who will ask why I publish an indicator designed for small timeframes, let me say that my main purpose here is to showcase what can be done with Pine. I often see comments by coders who are obviously not aware of what Pine is capable of in 2021. Since its humble beginnings seven years ago, Pine has grown and become a serious programming language. TradingView's growing popularity and its ongoing commitment to keep Pine accessible to newcomers to programming is gradually making Pine more and more of a standard in indicator and strategy programming. The technical barriers to entry for

> 3. The bright-colored borders of the candle bodies occur on "strong bars", i.e., bars meeting the criteria selected in the script's inputs, which you can configure.

> The script's inputs provide many ways to personalize all the components: what is displayed, the colors used to display the information, and the marker conditions. Tooltips provide details for many of the inputs; I leave their exploration to you.

> You can configure alerts on this script. They will trigger whenever one of the configured markers triggers. Alerts do not repaint, so they trigger at the bar's close—which is also when the markers will appear.

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

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, level2-orderbook-history.
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

- https://www.tradingview.com/script/Xh8tLDTe-Realtime-Delta-Volume-Action-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
