---
id: tv_1cv4puad_redk_indicator_amplifier_redk_i_amp
name: "RedK Indicator Amplifier (RedK i-Amp)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK Indicator Amplifier (RedK i-Amp); not a tested trading strategy."
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
# RedK Indicator Amplifier (RedK i-Amp)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> RedK i-Amp is not an indicator in itself - it's a "wrapper" utility that "amplifies" another "source" indicator by improving its visual and alerting capabilities.

> RedK i-Amp needs to be very flexible to be able to work with as many indicators as possible. The following guide will help you choose the best settings based on the "source" indicator:

> - Does the indicator have fixed (boundary) limits? Yes = Bounded. No = Unbounded.

> Dealing with unbounded oscillators is a bit tricky - because we can't predict the value range (classic MACD is a good example) - RedK i-Amp is designed to give you the ability to let it automatically scale the value relative to an observed window of recent values (lookback) or match the source indicator using manual scaling (Block Size) based on the Lookback setting - here's how this works:

> Risk & Responsibility. Trading involves substantial risk of loss and is not for everyone. All decisions, interpretation, and risk and money management are yours alone. Past behavior does not predict future results. The author accepts no liability for any loss or consequence arising from use of this tool.

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

- https://www.tradingview.com/script/1cv4PUad-RedK-Indicator-Amplifier-RedK-i-Amp/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
