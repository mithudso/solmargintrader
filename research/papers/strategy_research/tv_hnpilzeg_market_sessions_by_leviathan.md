---
id: tv_hnpilzeg_market_sessions_by_leviathan
name: "Market Sessions - By Leviathan"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Market Sessions - By Leviathan; not a tested trading strategy."
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
# Market Sessions - By Leviathan

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> A simple indicator to help you keep track of 4 market sessions (default: Tokyo, London, New York, Sydney) in 4 different visual forms (boxes, timeline, zones, colored candles) with many other useful tools.

> 9. “Lookback (Days)” - this input tells the script to only draw sessions for X days back (1 = one day).

> You can choose between 4 different market sessions. The default ones are Tokyo, London, New York and Sydney but you can easily customize the times, names and colors to make the script plot any session you need. Sessions can be viewed in 4 different ways: boxes, zones, timelines, or just colored candles, all with customizable appearances. You can make your chart cleaner by merging sessions overlaps, choosing a custom lookback period and also picking between various additional settings such as viewing session High/Low or Open/Close change in % or pips, hiding weekends, viewing the Open/Close Lin

> Note: The script will plot the correct default Tokyo, London, New York and Sydney sessions automatically, your chart/Tradingview app timezone does not matter! If you wish to tweak the open/close times of sessions, just make sure you input them in UTC (but even this can be changed later in the settings)

> Make sure to read future update logs to keep track of the most recent additions and settings of this script.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- https://www.tradingview.com/script/hNpilzEG-Market-Sessions-By-Leviathan/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
