---
id: tv_bvyz1cdf_bernoulli_process_binary_entropy_function
name: "Bernoulli Process - Binary Entropy Function"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bernoulli Process - Binary Entropy Function; not a tested trading strategy."
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
# Bernoulli Process - Binary Entropy Function

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator is the Bernoulli Process or Wikipedia - Binary Entropy Function. Within Information Theory, Entropy is the measure of available information, here we use a binary variable 0 or 1 (P) and (1-P) (Bernoulli Function/Distribution), and combined with the Shannon Entropy measurement. As you can see below, it produces some wonderful charts and signals, using price, volume, or both summed together. The chart below shows you a couple of options and some critical details on the indicator. The best part about this is the simplicity, all of this information in a couple of lines of code.

> The longer the Entropy measurement the more information you are capturing, so the analogy is, the shorter the signal, the less information you have available to utilize. You'll run into your Nyquist frequencies below a length of 5. I've found values between 9 and 22 work well to gather enough measurements. You also have an averaging summation that measures the weight or importance of the information over the summation period. This is also used for highlighting when you have an information signal above the 5% level (2 sigma) and then can be adjusted using the Percent Rank Variable. Finally, you

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

- https://www.tradingview.com/script/bvYZ1CdF-Bernoulli-Process-Binary-Entropy-Function/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
