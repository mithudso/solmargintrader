---
id: tv_43000773991_held_tokens_in_addresses_x_tokens
name: "Held tokens in addresses ≥ X (tokens)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Held tokens in addresses ≥ X (tokens); not a tested trading strategy."
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
# Held tokens in addresses ≥ X (tokens)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> What is "Held tokens in addresses ≥ X (tokens)"?

> Held tokens in addresses ≥ X (tokens) represent the total cryptocurrency held by addresses with at least X native units, capturing supply distribution among holders of different sizes. The default value is X = 1 token, but users can select from multiple thresholds ,including 0.001, 0.01, 0.1, 1, 10, 100, 1K, 10K, 100K, and 1M tokens to analyze supply concentration across different holder tiers.

> How is "Held tokens in addresses ≥ X (tokens)" calculated?

> This metric reveals token distribution breadth, indicating retail participation versus whale dominance. At the default 1 token threshold, it shows supply held by minimally invested participants, excluding trivial dust. Lower thresholds (0.001-0.1) include the smallest holders, revealing supply fragmentation. Mid-range thresholds (10-1K) show engaged retail investors. Higher thresholds (10K-1M+) show only large holders and whales. Significant supply only at high thresholds signals concentration. Traders compare supply across thresholds to assess organic distribution among smaller investors vers

> Held tokens in addresses ≥ X (tokens) is calculated by summing balances from addresses where balance ≥ X native units. Users can adjust the X parameter in the indicator settings to analyze supply distribution across different holder size categories.

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

- https://www.tradingview.com/support/solutions/43000773991-held-tokens-in-addresses-x-tokens/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
