---
id: tv_dh3cpnga_doubled_numbered_square_of_nine_progression_regression
name: "Doubled Numbered Square of Nine Progression | Regression"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Doubled Numbered Square of Nine Progression | Regression; not a tested trading strategy."
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
# Doubled Numbered Square of Nine Progression | Regression

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Doubled Number Square of Nine Progression | Regression Indicator enables forecasting of support and resistance levels using the SQ9 progression or regression from a user-selected pivot price. The indicator also plots adjustable pivots on both the chart and the Square of Nine.

> 4. Plot Levels: Select a Square of Nine angle to plot the support and resistance levels based on the selected increments. These levels auto expand and decrease depending on the number of rotations in step 3. The price values from each of the selected diagonal or cardinal cross are applied to the chart with labels on both left and right. Left labels represent the cell the time variable and the right label is price.

> In the image above, I'm progressing from the significant low at a rate of $200 per cell. Based on the plotted pivots, I've selected the 315-degree angle on the diagonal cross as it aligns with a few recent pivots. Now, I've drawn a vertical line to show that as we add rungs to the Square of Nine, we introduce support and resistance levels based on the identified angle that aligns with these early pivots from the low.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_gann`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/dh3Cpnga-Doubled-Numbered-Square-of-Nine-Progression-Regression/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
