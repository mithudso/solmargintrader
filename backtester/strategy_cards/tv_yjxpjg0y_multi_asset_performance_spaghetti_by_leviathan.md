---
id: tv_yjxpjg0y_multi_asset_performance_spaghetti_by_leviathan
name: "Multi-Asset Performance [Spaghetti] - By Leviathan"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Multi-Asset Performance [Spaghetti] - By Leviathan; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, venue-open-interest-and-liquidation-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Multi-Asset Performance [Spaghetti] - By Leviathan

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator visualizes the cumulative percentage changes or returns of 30 symbols over a given period and offers a unique set of tools and data analytics for deeper insight into the performance of different assets.

> Start by selecting a time period (e.g., 1 DAY) to set the interval for when data is reset. This will provide insight into how price, open interest, and on-balance volume change over your chosen period. In the settings, asset selection is fully customizable, allowing you to create three groups of up to 30 tickers each. These tickers can be displayed in a variety of styles and colors. Additional script settings offer a range of options, including smoothing values with a Simple Moving Average (SMA), highlighting the top or bottom performers, plotting the group mean, applying heatmap/gradient colo

> 🔸 RSI (Measures the speed and change of price movements and is used to identify overbought or oversold conditions of each asset. The RSI ranges from 0 to 100 and is typically used with a time period of 14. Generally, an RSI above 70 indicates that an asset may be overbought, while RSI below 30 signals that an asset may be oversold.)

> Multi Asset Performance indicator (also called “Spaghetti”) makes it easy to monitor the changes in Price, Open Interest, and On Balance Volume across multiple assets simultaneously, distinguish assets that are overperforming or underperforming, observe the relative strength of different assets or currencies, use it as a tool for identifying mean reversion opportunities and even for constructing pairs trading strategies, detect "risk-on" or "risk-off" periods, evaluate statistical relationships between assets through metrics like correlation and beta, construct hedging strategies, trade rotati

> 🔸 Percentage Change (Represents the return or the percentage increase or decrease in Price/OI/OBV over the current selected period)

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `xs_momentum`.

## Data and availability

Required inputs: ohlcv, venue-open-interest-and-liquidation-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/yJxpjg0Y-Multi-Asset-Performance-Spaghetti-By-Leviathan/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
