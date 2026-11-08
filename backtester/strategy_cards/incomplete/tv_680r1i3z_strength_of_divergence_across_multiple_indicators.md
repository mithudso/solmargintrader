---
id: tv_680r1i3z_strength_of_divergence_across_multiple_indicators
name: "Strength of Divergence Across Multiple Indicators"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Strength of Divergence Across Multiple Indicators; not a tested trading strategy."
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
# Strength of Divergence Across Multiple Indicators

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> One-stop shop for all your divergence needs, including:

> (3) Fully customizable, including inputs for pivot lengths, divergence types, and weights for every component of the divergence strength calculation. This allows you to quickly and easily optimize the output for any chart. Don't worry, the default settings will have you covered if you're not interested in what's going on under the hood.

> |ΔIndicator| = |indicator_value_1 - indicator_value_2| / 2 * StDev(indicator_series,100)

> The total divergence strength value is the sum of the divergence strengths of all indicators for which divergence was detected at a given bar. Each indicator's individual divergence strength is comprised of two basic components: (1) |ΔPrice| - the magnitude of the change in price over the divergence period (pivot-to-pivot), and (2) |ΔIndicator| - the magnitude of the change in indicator value over the divergence period.

> All components of the calculation are weighted and can be modified on the Inputs page in settings (weights are simply multipliers). For example, if you think hidden divergence should carry less weight than regular divergence, you can assign it a lesser weight. Or if you think RSI divergence is worth more than OBV divergence, you can adjust their weights accordingly. List of weights:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_oscillator_divergence`, `tv_method_rsi_divergence`.

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

- https://www.tradingview.com/script/680R1I3Z-Strength-of-Divergence-Across-Multiple-Indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
