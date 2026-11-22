---
id: tv_43000773990_held_tokens_in_addresses_x_usd
name: "Held tokens in addresses ≥ X (USD)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Held tokens in addresses ≥ X (USD); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Held tokens in addresses ≥ X (USD)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> What is "Held tokens in addresses ≥ X (USD)"?

> Held tokens in addresses ≥ X (USD) measures the total amount of native cryptocurrency held by addresses worth at least X US dollars, representing the economically meaningful portion of total supply. The default value is X = $100, but users can select from multiple thresholds including $1, $10, $100, $1K, $10K, $100K, $1M, and $10M to analyze supply distribution across different economic segments.

> This metric separates economically meaningful supply from dust and abandoned balances. At the default $100 threshold, it measures supply held by active participants, excluding micro-balances and lost coins. Lower thresholds ($1-$10) capture nearly all live supply, showing maximum distribution. Mid-range thresholds ($1K-$100K) reveal concentration among investors with meaningful stakes. Higher thresholds ($1M+) show whale-controlled supply. High supply percentages even at elevated thresholds signal concerning centralization. Healthy distribution shows most supply only at very low thresholds (ma

> Held tokens in addresses ≥ X (USD) is calculated by summing balances from all addresses where (balance × current USD price) ≥ X. Users can adjust the X parameter in the indicator settings to analyze supply concentration at different economic levels.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/support/solutions/43000773990-held-tokens-in-addresses-x-usd/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
