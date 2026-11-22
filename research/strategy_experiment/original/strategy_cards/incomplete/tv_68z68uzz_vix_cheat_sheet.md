---
id: tv_68z68uzz_vix_cheat_sheet
name: "VIX Cheat Sheet"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of VIX Cheat Sheet; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-macro-and-derivatives-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# VIX Cheat Sheet

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator - "VIX Cheat Sheet" - performs several calculations for $VIX against the asset on your chart. However, using $VIX as a risk proxy or volatility metric often fails beyond large-cap U.S equities. To remedy this, the VixFix indicator is included in the script; you can select whether the script performs calculations for an asset against $VIX or against VixFix (i.e. Forex, Crypto)

> Also illustrated is a red label that appears when $VIX or VixFix closes above the upper Bollinger Band. The indicator will calculate and display the performance of the asset for the subsequent 10 sessions, to which the red label will disappear and all data stored as a tooltip in the blue labels stating "VIX Closed Above Upper Band" or "VixFix Closed Above Upper Band".

> Displayed in the example image is a box incorporating $VIX price data alongside an upper Bollinger Band and lower Bollinger Band. The data isn't cast to its own price scale but is helpful for quick interpretation of $VIX fluctuations. You can select to plot VixFix data in the box in the user inputs table.

> To reduce chart clutter, a label and line combination marking all $VIX closes above the upper Bollinger Band was not included. Instead, bar color changes were added. When "$VIX" is selected in the user inputs table the indicator will mark all sessions in which $VIX closed above the upper band as blue, in addition to plotting $VIX price data in the dynamic black box. When "VixFix" is selected, the indicator will mark all sessions where VixFix closed above the upper band as purple; the VixFix indicator will be plotted in the black box.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_vix_timing`.

## Data and availability

Required inputs: ohlcv, point-in-time-macro-and-derivatives-history.
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

- https://www.tradingview.com/script/68Z68uZZ-VIX-Cheat-Sheet/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
