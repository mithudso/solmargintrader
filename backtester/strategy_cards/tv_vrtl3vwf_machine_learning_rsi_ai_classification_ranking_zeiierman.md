---
id: tv_vrtl3vwf_machine_learning_rsi_ai_classification_ranking_zeiierman
name: "Machine Learning RSI | AI Classification & Ranking (Zeiierman)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Machine Learning RSI | AI Classification & Ranking (Zeiierman); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Machine Learning RSI | AI Classification & Ranking (Zeiierman)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Machine Learning RSI | AI Classification & Ranking (Zeiierman) is an adaptive RSI intelligence system that combines momentum analysis, historical analog recognition, machine learning classification, confidence scoring, and dynamic trend management into a single framework.

> Each confirmed bar is stored with its feature snapshot and a future outcome label. The label is based on whether price moved up or down after a fixed horizon, scaled by ATR. That is the learning dataset.

> This is one of the most sophisticated parts. The script uses a Fisher-discriminant-style calculation to determine which RSI features currently best separate bullish vs. bearish outcomes. Then it rescales those weights and smooths them over time.

> • When the Supertrend flips bullish, the model considers the market to be operating in an uptrend regime.

> • When the Supertrend flips bearish, the model considers the market to be operating in a downtrend regime.

> Rather than interpreting RSI solely through traditional overbought and oversold thresholds, the indicator examines how similar RSI environments have behaved historically and uses those observations to classify current market conditions.

> Input features → labeled memory → nearest-neighbor search → weighted classification → confidence scoring → adaptive output.

> The script transforms RSI into a multi-dimensional feature space, stores historical market behavior, identifies the closest historical analogs, and allows those analogs to vote on future directional bias.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_knn_prediction`, `tv_method_market_structure`, `tv_method_neural_prediction`, `tv_method_trailing_stop`.

## Data and availability

Required inputs: ohlcv, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/VrTL3VwF-Machine-Learning-RSI-AI-Classification-Ranking-Zeiierman/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
