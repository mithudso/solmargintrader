---
id: tv_tjzklojn_wyckoff_theultimator5
name: "Wyckoff [theUltimator5]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Wyckoff [theUltimator5]; not a tested trading strategy."
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
# Wyckoff [theUltimator5]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator was designed to be a comprehensive, intuitive, overly engineered algorithm that plots Wyckoff accumulation and distribution patterns on the chart as they arise. It shows the current status of the regime on a side panel, while also overlaying the accumulation or distribution schematic over the chart for added visual aid. While most indicators use pivot points to create the structure, this indicator uses a complex algorithm to map the progress through numerous checks and structural matching techniques.

> I designed this indicator to be both instructional and actionable, so people unfamiliar with the Wyckoff Method can jump in and learn about the phases with a clean and intuitive user interface and also make informed decisions based on the structure of the chart. People who have used the Wyckoff Method for years can use this indicator as confluence.

> Phase D - Trend within the range. The evidence tips decisively. A Sign of Strength (SOS) drives across the range on expanding volume, or a Sign of Weakness (SOW) does the opposite. Price then pulls back to a Last Point of Support (LPS) or rallies to a Last Point of Supply (LPSY), holding above the broken resistance or failing below the broken support. This is the classic entry location because the risk point is well defined.

> The chart will display a label for an entry (buy or sell) when the schematic reaches a certain level that is defined within the algorithm. It generally happens within phase C, but it is calculated based on a confidence score. The strictness of the entry points can be adjusted in the user settings. The point of entry will also be shown on the label.

> Alerts available for entry conditions and events

> 2) Debug table - This table shows the individual requirements for the current phase in order to progress to the next phase. It gives you the exact checks that the indicator is looking for in order to keep progressing. This indicator uses numerous requirements to progress phases rather than simple pivot points. It provides weights to the requirements and has some requirements be hard, and some soft. Hard requirements must be met in order to progress to the next phase, while soft requirements must meet a minimum cumulative threshold.

> Higher timeframe searching can be disabled, so you are only looking at the current timeframe on for patterns. It is enabled by default because chart patterns don't always follow set lengths.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`, `tv_method_wyckoff`.

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

- https://www.tradingview.com/script/tJzKloJn-Wyckoff-theUltimator5/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
