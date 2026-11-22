---
id: tv_6tsfpe3w_reflex_trendflex
name: "Reflex & Trendflex"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Reflex & Trendflex; not a tested trading strategy."
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
# Reflex & Trendflex

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Reflex and Trendflex are zero-lag oscillators that decompose price into independent cycle and trend components using SuperSmoother filtering. These indicators isolate each component separately, providing clearer identification of cyclical reversals (Reflex) versus trending movements (Trendflex).

> Based on Dr. John F. Ehlers' "Reflex: A New Zero-Lag Indicator" article (February 2020, TASC), both oscillators use normalized slope deviation analysis to minimize lag while maintaining signal clarity. The SuperSmoother filter removes high-frequency noise, then deviations from linear regression (Reflex) or current value (Trendflex) are measured and normalized by RMS for consistent amplitude across instruments and timeframes.

> Both oscillators begin with a two-pole Butterworth low-pass filter that smooths price data without the excessive lag of simple moving averages. The filter uses exponential decay coefficients and cosine modulation based on the cutoff period, providing aggressive smoothing while preserving signal timing.

> • Reflex reversal with Trendflex agreement: Cyclical turn within established trend (entry/exit timing)

> Reflex isolates cyclical price behavior by measuring deviation from a linear regression line fitted through the SuperSmoother output. For each bar, the filter calculates a linear slope over the lookback period, then sums how much the smoothed price deviates from this trendline. These deviations represent pure cyclical movement - price oscillations around the dominant trend. The result is normalized by RMS (root mean square) to produce consistent amplitude regardless of volatility or timeframe.

> Trendflex extracts trending behavior by measuring cumulative deviation from the current SuperSmoother value. Instead of comparing to a regression line, it simply sums the differences between the current smoothed value and all past values in the period. This captures sustained directional movement rather than oscillations. Like Reflex, normalization by RMS ensures comparable readings across different instruments.

> Six built-in alerts trigger on bar close (no repainting):

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_fourier_cycle`, `tv_method_risk_based_sizing`.

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

- https://www.tradingview.com/script/6tSfPE3W-Reflex-Trendflex/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
