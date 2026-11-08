---
id: tv_3xe8qqfr_directional_volume_shapes_zeiierman
name: "Directional Volume Shapes (Zeiierman)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Directional Volume Shapes (Zeiierman); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Directional Volume Shapes (Zeiierman)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Directional Volume Shapes (Zeiierman) is a regime-classification oscillator that reframes volume analysis around a different question: not simply “how much volume traded,” but “what statistical shape has directional pressure been forming, and which way is it leaning?”

> Most volume tools show exactly what happened: green bar up, red bar down, and taller bar equals more volume. This indicator uses a two-stage process: classify, then synthesize.

> Instead of using a simple “close above open equals bullish” rule, the indicator models the candle’s high-low range as a triangular probability distribution centered at the close.

> When the EMA is above or equal to zero, polarity is Bull. When it is below zero, polarity is Bear.

> Instead of plotting raw buy and sell volume bar by bar, the indicator scores each candle for directional pressure using a triangular intrabar distribution model. It collects those scores in a rolling window, classifies the pattern into one of seven distribution shapes, and displays a smooth synthetic template of the detected shape.

> This gives high-volume bars more influence over the rolling shape-classification window. When disabled, the classifier uses directional pressure alone.

> The content provided in my scripts, indicators, ideas, algorithms, and systems is for educational and informational purposes only. It does not constitute financial advice, investment recommendations, or a solicitation to buy or sell any financial instruments. I will not accept liability for any loss or damage, including without limitation any loss of profit, which may arise directly or indirectly from the use of or reliance on such information.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_oscillator_divergence`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/3XE8qqfr-Directional-Volume-Shapes-Zeiierman/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
