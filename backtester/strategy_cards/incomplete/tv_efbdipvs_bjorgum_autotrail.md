---
id: tv_efbdipvs_bjorgum_autotrail
name: "Bjorgum AutoTrail"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bjorgum AutoTrail; not a tested trading strategy."
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
# Bjorgum AutoTrail

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Incorporating the new interactive feature, this script is meant as a one time trailing stop for the active trader to manage positional risk of an ongoing trade. As a crypto trader or Fx trader, many may find themselves in a position late into the evening, or perhaps daily life is calling while a trade progresses in their favor. Adding a trailing stop to a position thats trending can help to keep you in the trade and lock in gains if things turn around when you are unable to react.

> A modified version of the TradingView built in SAR equation was used in this script. To provide the value of the SAR on the stop candle, it was necessary to alter the equation to extract this value as the regular SAR “flips” at this point. Thank you to TradingView for supplying access to the built in formula so that this SAR could behave the same as the built-in function outside of these alterations

> Lastly, within the code for more the more technical savvy, is some starting setups for string alerts to be sent to exchanges via 3rd party or custom API applications. Some string manipulation is required for specific providers to meet their requirements, but there is some building block alerts that will take the ticker symbol, recognize the asset your trading (Fx, Crypto, etc) and take input quantity or exchange names from the settings via inputs.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/EfbdipVs-Bjorgum-AutoTrail/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
