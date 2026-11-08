---
id: tv_builtin_volume_profile_fixed_range
name: "Volume Profile Fixed Range"
kind: exposure-strategy
status: spec-only
family: volume
summary: "Specification of Volume Profile Fixed Range; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [price-binned-executed-volume]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  first_bar_time: {default: 0, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  last_bar_time: {default: 0, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  row_size: {default: 24, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  rows_layout: {default: "Number Of Rows", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  subscriberealtime: {default: true, type: "bool", desc: "Documented TradingView input; not an optimized strategy setting"}
  value_area_volume: {default: 70, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  volume: {default: "Up/Down", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Volume Profile Fixed Range

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Bin executed volume by price over an explicit start/end range; derive POC and a declared value-area fraction. Do not use the eventual fixed-range endpoint before it was selected/known.

## Documented inputs and source details

TradingView catalog inputs: `first bar time`=0; `last bar time`=0; `row size`=24; `rows layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `subscriberealtime`=true; `value area volume`=70; `volume`=Up/Down [Up/Down, Total, Delta].

Catalog notes: Needs volume. Subject to `volume_profile.max_total_rows` (default 6000). (plots: `developing poc`, `developing va high`, `developing va low`; d.ts L27136).

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

https://www.tradingview.com/support/solutions/43000480324-fixed-range-volume-profile-indicator/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/mH_kGj0rLgA??si=bSjZO4QLoa264OBZ&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>
````

````text
Fixed Range Volume Profile (FRVP) indicator calculates volume data within a specified time period, allowing traders to analyse the volume activity of a particular range instead of the entire price movement of an asset.
````

````text
When calculating Volume Profile Fixed Range, we check a list of timeframes in a sequence until the number of bars in the time interval for which VP is calculated will be fewer than 5000. The sequence of timeframes is: 1, 5, 15, 30, 60, 240, 1D. If the bars that the indicator covers amount in total to 5 minutes or fewer, or if it is used on any second-based timeframe, the indicator will take data from the 1S timeframe for its calculations, regardless of the number of bars covered.
````
