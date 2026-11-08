---
id: tv_zsgx4esy_smart_trader_episode_06_isotropic_trend_lines
name: "Smart Trader, Episode 06, Isotropic Trend Lines"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Smart Trader, Episode 06, Isotropic Trend Lines; not a tested trading strategy."
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
# Smart Trader, Episode 06, Isotropic Trend Lines

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> ST-EP06 is a multi-scale structural trend channel indicator built on a σ-normalized coordinate system. It is designed to solve one of the oldest unaddressed problems in technical analysis:

> In ICS, price is expressed in natural logarithmic form and scaled by a volatility estimate (σ) derived from the Yang-Zhang (2000) method — a drift-invariant estimator that incorporates Open, High, Low, and Close data. The resulting vertical axis is dimensionless: one unit equals one standard deviation of recent realized price behavior. When trend angles are measured in this space, 45° indicates approximately one σ of movement per bar — whether the chart shows a penny stock, a major currency pair, or a commodity index.

> Traditional chart coordinates assign no fixed relationship between the price axis and the time axis. Resizing the chart window changes the visual slope of the same price movement — a compressed view may show 52° while a stretched view of the same data shows 25°. The angle is a display artifact, not a market property. The Isotropic Coordinate System (ICS) addresses this by normalizing log-price by realized volatility (σ). In this space, the trend angle is designed to remain constant regardless of how the chart is displayed — because it measures price displacement in units of σ per bar, not in p

> A trend line drawn on a chart appears to carry a measurable angle — yet that angle is an artifact of the display window, not a property of the market. Resize the chart horizontally and the slope flattens; compress it and the slope steepens. A given price movement on Gold daily and Bitcoin 1-hour may produce visually identical slopes on screen while reflecting entirely different structural conditions. This happens because traditional charts use a coordinate space where the vertical axis (price) and the horizontal axis (time) share no fixed dimensional relationship.

> ST-EP06 operates as a deterministic sequential pipeline. Yang-Zhang volatility (σ) provides the normalization constant that flows into every downstream stage. Price history is partitioned into structural blocks, each reduced to a geometric mean. The longest monotonic segment determines direction, and its slope in σ-normalized space yields the ICS angle. Four price extremes define the channel boundaries. This complete pipeline runs independently at six scales — 3, 7, 13, 19, 29, and 47 bars per block — all prime numbers, chosen to minimize harmonic overlap so that multiple scales are unlikely t

> Live Bar mode (default): the anchor is the current forming bar. Values update with each incoming tick. This is standard TradingView behavior and means the indicator may exhibit intra-bar repaint — the live bar's data enters all computations as it evolves.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_liquidity_sweep`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/ZSgx4eSy-Smart-Trader-Episode-06-Isotropic-Trend-Lines/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
