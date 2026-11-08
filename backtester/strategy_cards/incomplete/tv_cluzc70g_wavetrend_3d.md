---
id: tv_cluzc70g_wavetrend_3d
name: "WaveTrend 3D"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of WaveTrend 3D; not a tested trading strategy."
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
# WaveTrend 3D

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> WaveTrend 3D (WT3D) is a novel implementation of the famous WaveTrend (WT) indicator and has been completely redesigned from the ground up to address some of the inherent shortcomings associated with the traditional WT algorithm.

> The WT algorithm appears to have origins in a lesser-known proprietary algorithm called Trading Channel Index (TCI), created by AIQ Systems in 1986 as an integral part of their commercial software suite, TradingExpert Pro. The software’s reference manual states that “TCI identifies changes in price direction” and is “an adaptation of Donald R. Lambert’s Commodity Channel Index (CCI)”, which was introduced to the world six years earlier in 1980. Interestingly, a vestige of this early beginning can still be seen in the source code of LazyBear’s script, where the final EMA calculation is stored i

> In the canonical WT approach, an exponential moving average (EMA) for a given lookback window is used to assess the variability between price and two other EMAs relative to a second lookback window. Since the difference between the average price and its associated EMA is essentially unbounded, an arbitrary scaling factor of 0.015 is typically applied as a crude form of rescaling but still fails to capture 20-30% of values between the range of -100 to 100. Additionally, the trigger signal for the final EMA (i.e., TCI) crossover-based oscillator is a four-bar simple moving average (SMA), which f

> The core idea behind WT3D is to replace the EMA-based crossover system with modern Digital Signal Processing techniques. By assuming that price action adheres approximately to a Gaussian distribution, it is possible to sidestep the scaling nightmare associated with unbounded price differentials of the original WaveTrend method by focusing instead on the alteration of the underlying Probability Distribution Function (PDF) of the input series. Furthermore, using a signal processing filter such as a Butterworth Filter, we can eliminate the need for consecutive exponential moving averages along wi

> Ideally, it is convenient to have the resulting probability distribution oscillate between the values of -1 and 1, with the zero line serving as a median. With this objective in mind, it is possible to borrow a common technique from the field of Machine Learning that uses a sigmoid-like activation function to transform our data set of interest. One such function is the hyperbolic tangent function (tanh), which is often used as an activation function in the hidden layers of neural networks due to its unique property of ensuring the values stay between -1 and 1. By taking the first-order derivat

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_neural_prediction`, `tv_method_oscillator_divergence`.

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

- https://www.tradingview.com/script/clUzC70G-WaveTrend-3D/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
