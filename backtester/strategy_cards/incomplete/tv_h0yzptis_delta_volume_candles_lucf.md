---
id: tv_h0yzptis_delta_volume_candles_lucf
name: "Delta Volume Candles [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Delta Volume Candles [LucF]; not a tested trading strategy."
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
# Delta Volume Candles [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator plots on-chart volume delta information using candles that can replace your normal candles, tops and bottoms appended to normal candles, optional MAs of those tops and bottoms levels, a divergence channel and a chart background. The indicator calculates volume delta using intrabar analysis, meaning that it uses the lower timeframe bars constituting each chart bar.

> ​The ​volume delta concept divides a bar's ​volume in "up" and "down" ​volumes. The delta is calculated by subtracting down ​volume from up ​volume. Many calculation techniques exist to isolate up and down ​volume within a bar. The simplest use the polarity of interbar price changes to assign their ​volume to up or down slots, e.g., On Balance Volume or the Klinger Oscillator. Others such as Chaikin Money Flow use assumptions based on a bar's OHLC values. The most precise calculation method uses tick data and assigns the ​volume of each tick to the up or down slot depending on whether the tran

> This indicator uses intrabar analysis to achieve a compromise between the simplest and most precise methods of calculating ​volume delta. It is currently the most precise method usable on TradingView charts. TradingView's Volume Profile built-in indicators use it, as do the CVD - Cumulative ​Volume Delta Candles and CVD - Cumulative Volume Delta (Chart) indicators published from the TradingView account. My Delta Volume Channels and Volume Delta Columns Pro indicators also use intrabar analysis. Other ​volume delta indicators such as my Realtime 5D Profile use realtime chart updates to calculat

> Buying or selling volume are misnomers, as every unit of volume transacted is both bought and sold by two different traders. While this does not keep me from using the terms, there is no such thing as “buy only” or “sell only” volume. Trader lingo is riddled with peculiarities. Without access to order book information, traders work with the assumption that when price moves up during a bar, there was more buying pressure than selling pressure, just as when buy market orders take out limit ask orders in the order book at successively higher levels. The built-in volume indicator available on Trad

> This indicator automatically calculates an appropriate lower timeframe using the chart's timeframe and the settings you use in the script's "Intrabars" section of the inputs. As it can access lower timeframes as small as seconds when available, the indicator can be used on charts at relatively small timeframes such as 1min, provided the market is active enough to produce bars at second timeframes.

> an SMA of twice the period used for the "Average Balance" EMAs. The difference for the up side is subtracted from the difference for the down side,

> Rightly or wrongly, volume delta is considered by many a useful complement to the interpretation of price action. I use it extensively in an attempt to find convergence between my read of volume delta and price movement — not so much as a predictor of future price movement. No system or person can predict the future. Accordingly, I consider people who speak or act as if they know the future with certainty to be dangerous to themselves and others; they are charlatans, imprudent or blissfully ignorant.

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

- https://www.tradingview.com/script/h0yZPTiS-Delta-Volume-Candles-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
