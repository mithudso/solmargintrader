---
id: tv_43000773010_price_momentum_oscillator_pmo
name: "Price Momentum Oscillator (PMO)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Price Momentum Oscillator (PMO); not a tested trading strategy."
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
# Price Momentum Oscillator (PMO)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Price Momentum Oscillator (PMO), created by Carl Swenlin, is a momentum indicator that measures the smoothed bar-by-bar rate of change (ROC) in an instrument's price. The indicator applies two stages of smoothing to the ROC, and uses an EMA of the result as a signal line.

> The PMO functions similarly to indicators such as the MACD. Traders typically use it to gauge short-term momentum, identify developing trends or mean reversion opportunities, and find divergences or other patterns. However, because the indicator smooths the single-bar ROC instead of calculating the difference between price averages, it is less sensitive to the absolute magnitude of price movements, often resulting in a more consistent scale across the chart's history.

> The PMO indicator applies two stages of custom exponential smoothing, with different lengths, to the one-bar ROC of market prices. Then, it computes a signal line using a standard EMA. The steps to calculate the PMO and signal values are as follows:

> Apply an EMA with a custom smoothing factor to the ROC series. Instead of the standard smoothing factor of 2 / (length + 1), this EMA uses the factor 2 / length.

> The length for the first stage of exponential smoothing.

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

- https://www.tradingview.com/support/solutions/43000773010-price-momentum-oscillator-pmo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
