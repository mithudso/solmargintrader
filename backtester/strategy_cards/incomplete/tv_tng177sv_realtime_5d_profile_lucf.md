---
id: tv_tng177sv_realtime_5d_profile_lucf
name: "Realtime 5D Profile [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Realtime 5D Profile [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, level2-orderbook-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Realtime 5D Profile [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays a realtime profile that can be configured to visualize five dimensions: ​volume, price, time, activity and age. For each price level in a bar or timeframe, you can display total or delta ​volume or ticks. The tick count measures activity on a level. The thickness of each level's line indicates its age, which helps you identify the most recent levels.

> The indicator only works in real time. Contrary to TradingView's line of volume profile indicators, it does not show anything on historical bars or closed markets, and it cannot display ​volume information if none exists for the data feed the chart is using. A realtime indicator such as this one only displays information accumulated while it is running on a chart. The information it calculates cannot be saved on charts, nor can it be recalculated from historical bars. If you refresh the chart, or the script must re-execute for some reason, as when you change inputs, the accumulated information

> ​Volume is slotted in up or down slots depending on whether the price of each new chart update is higher or lower than the previous update's price. When price does not move between chart updates, the last known direction is used. In a perfect world, Pine scripts would have access to bid and ask levels, as this would allow us to know for sure if market orders are being filled on upticks (at the ask) or downticks (at the bid). Comparing the price of successive chart updates provides the most precise way to calculate ​volume delta on TradingView, but it is still a compromise. Order books are in c

> A profile is a tool that displays information organized by price levels. You can select the maximum quantity of levels this indicator displays by using the script's "Levels" input. If the profile's height is small enough for level increments to be less than the symbol's tick size, a smaller quantity of levels is used until the profile's height grows sufficiently to allow your specified quantity of levels to be displayed. The exact position of levels is not tethered to the symbol's tick increments. Activity for one level is that which happens on either side of the level, halfway between its hig

> The profile's horizontal structure is also dynamic. The maximum length of level lines is controlled by the "Maximum line length" input value. This maximum length is always used for the largest level value in the profile, and the length of other levels is determined by their value relative to that maximum.

> Because "Realtime 5D Profile" requires time to accumulate information on the chart, it will be most useful to traders working on small timeframes who trade only one instrument and do not frequently change their chart's symbol or timeframe. Traders working on higher timeframes or constantly changing charts will be better served by TradingView's ​volume profiles. Before using this indicator, please see the "Limitations" section further down for other important information.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_market_profile`, `tv_method_volume_delta`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, level2-orderbook-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/tNG177SV-Realtime-5D-Profile-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
