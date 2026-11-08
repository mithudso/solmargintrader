---
id: tv_ctjx82hp_extrapolated_pivot_connector_lets_make_support_and_resistances
name: "Extrapolated Pivot Connector - Lets Make Support And Resistances"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Extrapolated Pivot Connector - Lets Make Support And Resistances; not a tested trading strategy."
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
# Extrapolated Pivot Connector - Lets Make Support And Resistances

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The support and resistance methodology remain the most used one in technical analysis, this is mainly due to its simplicity, and unlike lots of techniques used in technical analysis support and resistances have a certain logic, price can sometimes appear moving into a channel, support and resistances allow the trader to estimate such channel and project it into the future in order to spot points where price might reverse direction.

> In this script a simple linear support and resistance indicator is proposed, the indicator is made by connecting past pivot high's/low's to more recent ones and extrapolating the resulting connection. The indicator is also able to make support and resistances by using other indicators as input.

> The indicator include various settings, the first one being the length setting who determine the sensitivity of the pivot high/low detection, low values of length will detect the pivot high/low of noisy variations, while higher values will detect the pivot high/low of longer term variations.

> The code make heavy use of the new features that where integrated on the v4 of pine, such features are really focused on making figures and labels, things i don't really work with, but it is nice to step out my short codes habits, and i don't exclude working with figures in pine in the future.

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

- https://www.tradingview.com/script/CtjX82Hp-Extrapolated-Pivot-Connector-Lets-Make-Support-And-Resistances/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
