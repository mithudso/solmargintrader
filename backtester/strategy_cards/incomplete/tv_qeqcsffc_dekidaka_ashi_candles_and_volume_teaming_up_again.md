---
id: tv_qeqcsffc_dekidaka_ashi_candles_and_volume_teaming_up_again
name: "Dekidaka-Ashi - Candles And Volume Teaming Up (Again)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Dekidaka-Ashi - Candles And Volume Teaming Up (Again); not a tested trading strategy."
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
# Dekidaka-Ashi - Candles And Volume Teaming Up (Again)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The introduction of candlestick methods for market price data visualization might be one of the most important events in the history of technical analysis, as it totally changed the way to see a trading chart. Candlestick charts are extremely efficient, as they allow the trader to visualize the opening, high, low and closing price (OHLC) each at the same time, something impossible with a traditional line chart. Candlesticks are also cleaner than bars charts and make a more efficient use of space. Japanese peoples are always better than everyone at an incredible amount of stuff, look at what th

> However classical candlesticks only include historical market price data, and won't include other type of data such as volume, which is considered by many investors a key information toward effective financial forecasting as volume is an indicator of trading activity. In order to tackle to this problem solutions where proposed, the most common one being to adapt the width of the candle based on the amount of volume, this method is the most commonly accepted one when it comes to visualizing both volume and OHLC data using candlesticks.

> Now why proposing an additional tool for volume data visualization ? Because the classical width approach don't provide usable data regarding volume (as the width is directly related to the volume data). Therefore a new trading tool based on candlesticks that allow the trader to gain access to information about the volume is proposed. The approach is based on rescaling the volume directly to the price without the direct use of user settings. We will also see that this tool allow to create support and resistances as well as providing signals based on a breakout methodology.

> In green body with size 2, in red with size 1. The smooth parameter will smooth the volume data before being used, this allow to create more visible bodies.

> This tool is made so it output two rescaled volume values, with the highest value being denoted as "Dekidaka-high" and the lowest one as "Dekidaka-low". In order to get bands we must use two moving averages, one using the Dekidaka-high as input and the other one using Dekidaka-low, the body size parameter should be fairly high, therefore i will hide the tool as it could cause trouble visualizing the bands.

> The body size of the candle is based on two things : the absolute close/open difference, and the volume, if the absolute close/open difference is high and the volume is high then the body of the candle will be clearly visible, if the volume is high but the absolute close/open difference is low, then the body will be less visible. This approach is used because of the rescaling method used, the volume is divided by the sum between the current volume value and the precedent volume value, this rescale the volume in a (0,1) range, this result is multiplied by the absolute close/open difference and

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_heikin_ashi`, `tv_method_renko`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/QeqcSffc-Dekidaka-Ashi-Candles-And-Volume-Teaming-Up-Again/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
