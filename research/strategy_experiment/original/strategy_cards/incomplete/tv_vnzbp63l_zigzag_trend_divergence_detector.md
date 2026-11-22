---
id: tv_vnzbp63l_zigzag_trend_divergence_detector
name: "Zigzag Trend/Divergence Detector"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Zigzag Trend/Divergence Detector; not a tested trading strategy."
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
# Zigzag Trend/Divergence Detector

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Pullbacks are always hardest part of the trade and when it happen, we struggle to make decision on whether to continue the trade and wait for recovery or cut losses. Similarly, when an instrument is trending well, it is often difficult decision to make if we want to take some profit off the table. This indicator is aimed to make these decisions easier by providing a combined opinion of sentiment based on trend and possible divergence.

> Oscillators does not always make pivots at same bar as price. Due to this some the divergence calculation may not be correct. Hence visual inspection is always recommended.

> Enhance divergence calculation. Possible options include using oscillator based zigzag as primary or using close prices based zigzag instead of high/low.

> ▶ Zigzag parameters : These let you chose zigzag properties. If you check "Use confirmed pivots", then unconfirmed pivot will be ignored in the table and in the chart

> ▶ Oscillator parameters : Lets you select different oscillators and settings. Available oscillators involve

> ▶ Trend bias : Supertrend is used for trend bias. Coloring option color candles in the direction of supertrend. More option for trend bias can be added in future.

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

- https://www.tradingview.com/script/vnzbp63L-Zigzag-Trend-Divergence-Detector/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
