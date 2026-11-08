---
id: tv_43000773988_addresses_with_balance_x_usd
name: "Addresses with balance ≥ X (USD)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Addresses with balance ≥ X (USD); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, point-in-time-onchain-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Addresses with balance ≥ X (USD)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Addresses with balance ≥ X (USD) tracks the total count of unique addresses holding at least X US dollars worth of cryptocurrency at current market prices. The default value is X = $100, but users can select from multiple thresholds, including $1, $10, $100, $1K, $10K, $100K, $1M, and $10M to analyze different economic holder segments.

> How is "Addresses with balance ≥ X (USD)" calculated?

> Addresses with balance ≥ X (USD) is calculated by counting unique addresses where (balance × current USD price) ≥ X. Users can adjust the X parameter in the indicator settings to analyze different economic holder tiers.

> This metric enables blockchain adoption comparisons regardless of unit prices. At the default $100 threshold, it counts economically active participants, filtering out dust wallets. Lower thresholds ($1-$10) include nearly all holders, revealing the total user base and grassroots adoption. Mid-range thresholds ($1K-$100K) show addresses with notable balances. High thresholds ($1M+) show only the largest addresses. Growing address counts signal increasing confidence; declining counts may indicate capitulation or consolidation. This metric considers only native units, excluding Layer 2 tokens.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, point-in-time-onchain-history.
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

- https://www.tradingview.com/support/solutions/43000773988-addresses-with-balance-x-usd/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
