---
id: tv_eolvuvxl_market_manipulation_index_mmi
name: "Market Manipulation Index (MMI)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Market Manipulation Index (MMI); not a tested trading strategy."
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
# Market Manipulation Index (MMI)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Composite Manipulation Index (CMI) is a structural integrity tool that quantifies how chaotic or orderly current market conditions are, with the aim of detecting potentially manipulated or unstable environments. It blends two distinct mathematical models that assess price behavior in terms of both structural rhythm and predictability.

> This component assumes that ideal, low-manipulation price behavior resembles a smooth oscillation, such as a sine wave. It generates a synthetic sine wave using a user-defined period and compares it to actual price movement over an adaptive window. The error between the real price and this synthetic wave—normalized by price variance—forms the Sine-Based Manipulation Index. A high error indicates deviation from natural rhythm, suggesting structural disorder.

> Both components are calculated using an adaptive smoothing window based on the Average True Range (ATR). This allows the indicator to respond proportionally to market volatility. During high volatility, the analysis window expands to avoid over-sensitivity; during calm periods, it contracts for better responsiveness.

> The second component estimates how well current price can be predicted using recent price lags. A two-variable rolling linear regression is computed between the current price and two lagged inputs (close[1] and close[2]). If the predicted price diverges from the actual price, this error—also normalized by price variance—reflects unpredictability. High prediction error implies a more manipulated or erratic environment.

> CMI 0.3–0.7: Transitional zone. Caution or reduced risk may be warranted.

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

- https://www.tradingview.com/script/EOLvUvxl-Market-Manipulation-Index-MMI/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
