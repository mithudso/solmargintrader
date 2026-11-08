---
id: tv_c75af3t1_fractional_ema_kalman_filter_d7
name: "Fractional EMA Kalman Filter [D7]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Fractional EMA Kalman Filter [D7]; not a tested trading strategy."
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
# Fractional EMA Kalman Filter [D7]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Fractional EMA Kalman Filter [D7] is an experimental smoothing and state-estimation tool that combines a Kalman filter framework with a fractional EMA input. The objective is to create a filter that remains subdued during ranging conditions while retaining responsiveness when directional structure emerges. By integrating adaptive variance logic and residual-based state control, D7 aims to balance smoothness, reactivity, and structural awareness.

> The difference between the incoming measurement and the current state estimate; the correction signal the filter acts on. Innovation = EMA − X

> The adaptive weighting factor that balances trust between the new measurement and the prior prediction. K = P / (P + R)

> The current filtered estimate of price, updated using a fractional-length EMA measurement input. This is what the filter believes the true underlying value to be at each step.

> Applies a double sub‑integer EMA length (e.g., 0.5‑period) to generate a high‑resolution measurement signal that responds to structural volatility and regime transitions faster than conventional smoothing. The fractional EMA is not intended to estimate price, but to precondition the observation space so that regime changes manifest as large, legible innovations. By transforming the input prior to filtering, the measurement emphasizes moments of structural change rather than steady‑state behavior, improving the responsiveness of adaptive state estimation.

> This script is a research tool for market structure analysis and educational purposes only. It does not constitute financial advice. Trading involves risk.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_kalman_filter`, `tv_method_market_structure`.

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

- https://www.tradingview.com/script/c75aF3t1-Fractional-EMA-Kalman-Filter-D7/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
