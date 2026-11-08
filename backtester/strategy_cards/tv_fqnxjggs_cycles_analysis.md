---
id: tv_fqnxjggs_cycles_analysis
name: "Cycles Analysis"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Cycles Analysis; not a tested trading strategy."
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
# Cycles Analysis

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> I strongly believe in cycles, so I wanted to create something that would give a visual representation of bull/bear markets and give a prediction based on the previous data. It's up to you how to decide what is a bull/bear cycle. There is no single rule for all assets because 20% drop in SP500 starts a bear market in traditional markets, while 35% drop for Bitcoin is a Tuesday. You have two options on how to decide when markets turn: either by a % change (traditional definition) or if there is no new high/low after X days. A softer version to show periods of no new highs/lows is to use the Stag

> The script also draws a possible "predictions" zone where the current cycle might end up. There is no magic here, it just takes previous cycles' size to draw the possible boundaries. If you decide to use percentiles then the box area will be taken from the percentiles calculations, otherwise it will come from the full data. "x" in the predictions zone represents a target mean (average) value, "o" represents a target median value.

> - it doesn't work with replays as it does calculations only once on the last candle.

> - this script is not supposed to be used in trading. It was created for analysis. It repaints. And when I say "it repaints" - it might like repaint the last 6 months of data if a new low comes and we are in a stagnation period (aka not a financial advice).

> - you need at least 3 periods to be able to calculate percentiles. And after this it will remove at least 1 period on each side. Which means that 90 percentile will not be a real 90 percentile until you have enough periods for it to be (20 in this specific case).

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

- https://www.tradingview.com/script/fqnXJggs-Cycles-Analysis/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
