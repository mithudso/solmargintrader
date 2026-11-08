---
id: tv_builtin_session_volume_profile
name: "Session Volume Profile"
kind: exposure-strategy
status: spec-only
family: volume
summary: "Specification of Session Volume Profile; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [price-binned-executed-volume]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  rows_layout: {default: "Number Of Rows", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  row_size: {default: 24, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  volume: {default: "Up/Down", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  sessions: {default: "All", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  custom_session: {default: "0930-1600", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  customsessiontz: {default: "Exchange", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  value_area_volume: {default: 70, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  extend_poc_right: {default: false, type: "bool", desc: "Documented TradingView input; not an optimized strategy setting"}
  extend_vah_right: {default: false, type: "bool", desc: "Documented TradingView input; not an optimized strategy setting"}
  extend_val_right: {default: false, type: "bool", desc: "Documented TradingView input; not an optimized strategy setting"}
  subscriberealtime: {default: true, type: "bool", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Session Volume Profile

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Bin volume by price within each declared session; POC is the maximum-volume bin, and value area depends on the selected expansion rule. OHLCV alone cannot recover exact executed volume at each price.

## Documented inputs and source details

TradingView catalog inputs: `rows layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `row size`=24; `volume`=Up/Down [Up/Down, Total, Delta]; `sessions`=All [All, Each (pre-market, market, post-market), Pre-market only, Market only, Post-market only, Custom]; `custom session`=0930-1600; `customsessiontz`=Exchange [Exchange, Etc/UTC, named tz]; `value area volume`=70; `extend poc right`=false; `extend vah right`=false; `extend val right`=false; `subscriberealtime`=true.

Catalog notes: Marked Trading Platform only in the docs list. See the Session Volume Profile section. (plots: `developing poc`, `developing va high`, `developing va low`; d.ts L26155).

These are documented UI inputs, not verified constructor defaults. Standard formulas
are reference definitions; the capture does not establish exact TradingView seed,
smoothing or rendering parity.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: price-binned-executed-volume.
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

- docs/TRADINGVIEW-REFERENCE.md — built-in indicator catalog and standard equations.
- https://www.tradingview.com/charting-library-docs/latest/indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Official help clarification

https://www.tradingview.com/support/solutions/43000557450-session-volume-profile-hd/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/sLOmfOjOM_c??si=DQkXQsXLR7BwOxcO&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>
````

````text
Session Volume Profile HD (SVP HD) indicator calculates volume data within a specified session or a sub-session, allowing traders to analyze the intraday volume activity of one specific part of the session. Additionally, unlike the regular Session Volume Profile, it automatically adjusts the level of detail as you zoom the chart. When fewer bars appear on the chart, more levels are displayed.
````

````text
Session Volume HD consists of two different calculations: a rough one and a detailed one. The detailed calculation applies to the visible part of the chart and adjusts the number of rows in all visible Volume Profiles automatically. For this calculation, the lower timeframe data is selected based on the same logic as with Visible Range (with the exception of all second-based timeframes, which use 1S data).
````


## Official help clarification

https://www.tradingview.com/support/solutions/43000703072-session-volume-profile/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/jYv_HKxEcVw??si=XEHWu_A3HVZHvnXW&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>
````

````text
Session Volume Profile (SVP) indicator calculates volume data within a specified session or a sub-session, allowing traders to analyze the intraday volume activity of one specific part of the session. You can find SVP in the Indicators, metrics, and strategies menu, or just open a ready-made chart: read more on the Session Volume Profile charts to use them effectively.
````

````text
To calculate Session Volume Profile, the indicator uses a table that selects a lower timeframe based on the timeframe currently selected on the chart:
````
