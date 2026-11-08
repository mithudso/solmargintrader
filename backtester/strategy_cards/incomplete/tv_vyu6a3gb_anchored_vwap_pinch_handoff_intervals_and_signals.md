---
id: tv_vyu6a3gb_anchored_vwap_pinch_handoff_intervals_and_signals
name: "Anchored VWAP Pinch & Handoff, Intervals, and Signals"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Anchored VWAP Pinch & Handoff, Intervals, and Signals; not a tested trading strategy."
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
# Anchored VWAP Pinch & Handoff, Intervals, and Signals

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> "Anchored VWAP Pinch & Handoff, Intervals, and Signals" is an AVWAP toolbox for those who like to use various VWAP trading techniques. The indicator is currently comprised of the following three sections:

> • The Pinch & Handoff section (shown above on chart) allows manually setting an upper and lower AVWAP (Pinch) along with an additional AVWAP (Handoff) by entering dates or by dragging the vertical anchor lines to the desired significant events on chart. Each of these three AVWAPs can also be set to show zones above and/or below by a percentage or standard deviation amount. The theory behind this method is that the upper and lower AVWAPs may act as dynamic support and resistance levels, effectively creating a price range or channel. As price moves between these two VWAP levels, it becomes squee

> • The Intervals section (shown above on chart) is comprised of six periodic AVWAPs which cyclically reset. Their default settings are 1 Day, 2 Days, 1 Week, 1 Month, 1 Quarter, and 1 Year. They each may be set to desired period and when they are enabled the VWAPs whose periods are lower than the current chart timeframe are automatically hidden. For example a 1 Day AVWAP is not useful on a 1 Week chart so it would be hidden from that timeframe. When using AVWAPs from higher timeframes it may be helpful to set your chart to "Scale price chart only". This can be enabled by right clicking on your

> • The Auto section (shown above on chart) is comprised of two automatic Anchored VWAPs. There are choices for setting anchors automatically based upon Highest Source, Highest Volume, Lowest Source, Lowest Volume, Pivot High, and Pivot Low. Because these two VWAPs work retroactively they are drawn with lines instead of plots. There is currently a limitation of 500 lines that may be drawn at any given time and the logic within this indicator uses a line for every bar of VWAP that is drawn, so if the combined length of both of these VWAPs exceeds 500 bars the earliest lines would disappear. For t

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/VYu6A3GB-Anchored-VWAP-Pinch-Handoff-Intervals-and-Signals/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
