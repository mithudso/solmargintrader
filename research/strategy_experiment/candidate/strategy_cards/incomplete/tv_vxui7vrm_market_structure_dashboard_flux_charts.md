---
id: tv_vxui7vrm_market_structure_dashboard_flux_charts
name: "Market Structure Dashboard | Flux Charts"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Market Structure Dashboard | Flux Charts; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Market Structure Dashboard | Flux Charts

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Market Structure Dashboard is a multi-timeframe market structure analysis indicator. It combines EMA trend detection, swing high/low tracking, market structure labels, Order Block detection, Fair Value Gap detection, liquidity sweep detection, volume analysis, volatility analysis, trading sessions, ICT killzones, a weighted trend bias system, and HTF levels into one unified dashboard. Each component is calculated independently across up to 7 configurable timeframes and displayed together in a single organized view.

> The core idea is that a trade setup becomes more reliable when multiple timeframes agree on direction. A bullish signal on a 5-minute chart carries more weight when the 15-minute, 1-hour, and daily timeframes also show bullish conditions. Analyzing each timeframe separately is both time-consuming and prone to error. The Market Structure Dashboard automates this process by calculating key metrics across all enabled timeframes and presenting them side by side.

> Each component operates independently while sharing the same underlying market structure logic. All features are calculated across up to 7 user-configurable timeframes and displayed in a unified dashboard. Detailed explanations for each component are provided in the sections that follow.

> ◇ Color coding shows green when price is above EMA (bullish) and red when price is below EMA (bearish).

> When a liquidity sweep occurs (price breaks a level then reclaims it), special arrows appear: ⤴ for a swept and reclaimed low, ⤵ for a swept and reclaimed high. A swept and reclaimed swing means price broke beyond the level, likely triggering stop-loss orders resting beyond it, but then reversed back inside the range. This suggests the breakout was a false move and the opposite direction may follow. Liquidity sweeps are explained in detail in the Liquidity Sweep & Reclaim Detection section below.

> ◇ Step 2: When price breaks above a swing high, the indicator identifies a bullish breakout. When price breaks below a swing low, it identifies a bearish breakout.

> ◇ Step 5: Mitigation is applied when price closes through the Order Block. Bullish OBs are mitigated when price closes below the zone. Bearish OBs are mitigated when price closes above the zone.

> ◇ Mitigation occurs when price wicks below the gap bottom for bullish FVGs, or above the gap top for bearish FVGs. Note that FVG mitigation is more sensitive than Order Block mitigation.

> The indicator draws from two established trading methodologies. Smart Money Concepts (SMC) focuses on identifying institutional footprints in price action through patterns like Order Blocks, Fair Value Gaps, and liquidity sweeps. Inner Circle Trader (ICT) methodology emphasizes time-based analysis through specific trading windows called killzones and the importance of previous day, week, and month highs and lows.

> The dashboard calculates a 9-period EMA (configurable) for each enabled timeframe. The EMA Trend column displays both direction and distance.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_fair_value_gap`, `tv_method_liquidity_sweep`, `tv_method_market_structure`, `tv_method_order_blocks`, `tv_method_support_resistance`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/vXui7vrm-Market-Structure-Dashboard-Flux-Charts/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
