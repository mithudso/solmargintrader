---
id: tv_tnq7fvvw_trend_target_ribbon_boswaves
name: "Trend Target Ribbon [BOSWaves]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Trend Target Ribbon [BOSWaves]; not a tested trading strategy."
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
# Trend Target Ribbon [BOSWaves]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Trend Target Ribbon [BOSWaves] - ALMA Conviction Trend Detection with Integrated Structure-Based Position Planning and R-Multiple Target Tracking

> Instead of simply marking trend direction, each trend flip immediately produces a fully structured trade plan anchored to the current bar's close as entry and the recent swing structure as stop loss. Risk is calculated dynamically from the swing extreme within the configured lookback, clamped between ATR-based minimum and maximum bounds, and used to project equally-spaced R-multiple targets that extend forward for the configured projection length. As price develops, targets glow brighter as price approaches them, mark with a checkmark when reached, and the entire position freezes with a histor

> This creates a trend system that bridges signal generation and trade planning within a single indicator. The ALMA gradient ribbon communicates conviction intensity through its width and opacity, adapting continuously to the strength of the slope and the distance of price from the baseline. The candle gradient reinforces conviction on every bar. And the position framework provides an immediate, fully calculated trade structure from entry through all targets without requiring manual level calculation on each new trend signal.

> Trend Target Ribbon [BOSWaves] is an ALMA-based trend identification system that combines slope-normalized momentum confirmation with standard deviation band validation to determine trend state, and automatically generates a complete position planning framework on each trend flip including a structure-derived stop loss, up to four R-multiple take profit targets with proximity highlighting, and a risk zone visualization that tracks target hits and stop events throughout the position's active lifecycle.

> Trend Target Ribbon is founded on the principle that a trend system should do more than identify direction — it should translate each directional signal into a complete, immediately actionable trade framework where entry, risk, and target levels are derived from measurable market characteristics rather than arbitrary fixed distances.

> Traditional trend indicators produce a signal that the trader must then manually convert into a trade plan by selecting entry price, calculating stop placement, and choosing target distances. This framework eliminates that gap by automating the complete transition from signal to trade plan on each flip, using swing structure for stop placement and the resulting risk distance as the universal unit for all target projections. Every parameter of the trade plan is therefore grounded in the instrument's actual price behavior rather than fixed indicator values.

> Each trend flip should immediately generate a complete position framework with structure-derived stop loss, R-multiple targets, and active tracking of target proximity and hit status, translating the directional signal into a fully structured trade plan without manual intervention.

> The indicator combines Arnaud Legoux Moving Average calculation for trend baseline, standard deviation band construction for displacement confirmation, ATR-normalized slope scoring for momentum significance, conviction scoring from slope and distance for gradient scaling, swing structure lookback for stop loss derivation with ATR clamping, and a multi-array position management system that tracks active and historical positions with target proximity gradients and hit state tracking.

> The ALMA provides a low-lag weighted baseline with configurable offset and sigma parameters that control the balance between responsiveness and smoothness. Slope is measured as the ALMA change over the configured bar count normalized by ATR, producing a dimensionless score that reflects momentum strength independently of the instrument's price scale. The trend flip requires slope to exceed the minimum threshold in the signal direction while price simultaneously closes beyond the ALMA plus deviation band, ensuring both momentum and displacement conditions are satisfied. The conviction score com

> ALMA Trend Engine: Calculates the ALMA with configurable length, offset, and sigma, measures the normalized slope over the configured lookback, derives deviation bands for displacement confirmation, and flips trend state when both slope and displacement conditions are simultaneously satisfied.

> Price is therefore evaluated not just for its directional trend state but for its position within a dynamically constructed risk-reward framework that updates automatically with each new trend confirmation.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_risk_based_sizing`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/tnQ7FvvW-Trend-Target-Ribbon-BOSWaves/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
