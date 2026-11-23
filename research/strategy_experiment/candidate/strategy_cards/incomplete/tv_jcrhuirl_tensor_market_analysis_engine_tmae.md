---
id: tv_jcrhuirl_tensor_market_analysis_engine_tmae
name: "Tensor Market Analysis Engine (TMAE)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Tensor Market Analysis Engine (TMAE); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Tensor Market Analysis Engine (TMAE)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> ## Advanced Multi-Dimensional Mathematical Analysis System

> The TMAE employs a sophisticated Hawkes process approximation for detecting self-exciting market jumps. Unlike traditional volatility measures that treat price movements as independent events, the Hawkes process recognizes that market shocks cluster and exhibit memory effects.

> The engine calculates volatility jumps using multi-dimensional Mahalanobis distance across up to 5 volatility dimensions:

> - **Quality Degradation:** Exits when signal strength deteriorates

> - **Early Entry:** Enter on regime transition rather than confirmation

> - **Faster Exits:** Take profits more quickly

> - **Stop Loss Non-Negotiable:** Every trade must have predefined risk parameters

> Where market jumps at times Tᵢ increase the probability of future jumps through the decay function α, controlled by the Hawkes Decay parameter (0.5-0.99).

> Unlike static implementations, the TMAE uses adaptive windowing that adjusts to market conditions:

> Transfer entropy measures the directional flow of information between price and volume, revealing lead-lag relationships that indicate future price movements:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_intermarket_correlation`, `tv_method_liquidity_sweep`, `tv_method_market_structure`, `tv_method_risk_based_sizing`, `tv_method_support_resistance`, `tv_method_trailing_stop`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/jcRhuIRl-Tensor-Market-Analysis-Engine-TMAE/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
