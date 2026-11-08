---
id: tv_lper4qca_volume_analysis_heatmap_and_volume_profile
name: "Volume Analysis - Heatmap and Volume Profile"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Volume Analysis - Heatmap and Volume Profile; not a tested trading strategy."
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
# Volume Analysis - Heatmap and Volume Profile

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> I have a new toy for you! Volume Analysis - Heatmap and Volume Profile. Honestly I started to work to develop Volume Heatmap then I decided to improve it and add more features such Volume profile, volume, difference in Buy/Sell volumes etc. I tried to put my abilities into this script and tried to use some new Pine Language™ features (method, force_overlay, enum etc features). I hope the usage of these new features would be an example for Pine Programmers.

> - It calculates the number of the candles to analyze. Number of the candles may change by number of Rows/columns or if any volume / difference in volumes / volume profile is enabled

> - After getting the data it calculates lower time frame to analyze

> - As a new Pine Language™ feature, it can show Volume Profile in the indicator window or in Main chart, shows Value Area, Value Area High (VAH), Value Area Low (VAL), and draw it and POC (Point Of Control) in the indicator window and/or in the main chart

> - Honestly the feature I like is that: For the markets that are not open 24/7, it combines the data from the lower time period without any gaps. For example, if you work for a market that is closed on Saturdays and Sundays, it ensures data integrity by omitting weekends and holidays. so for example if the data is like "ABC---DEF-X---YL-Z" then it makes this data like "ABCDEFXYLZ". In this way, there will be no data breaks in the displayed boxes, there will be no empty colons, and it will appear as if data is coming in at any time.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_volume_delta`.

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

- https://www.tradingview.com/script/lPEr4QCA-Volume-Analysis-Heatmap-and-Volume-Profile/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
