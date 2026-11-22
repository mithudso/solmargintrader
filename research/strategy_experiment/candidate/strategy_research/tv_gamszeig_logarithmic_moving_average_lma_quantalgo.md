---
id: tv_gamszeig_logarithmic_moving_average_lma_quantalgo
name: "Logarithmic Moving Average (LMA) [QuantAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Logarithmic Moving Average (LMA) [QuantAlgo]; not a tested trading strategy."
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
# Logarithmic Moving Average (LMA) [QuantAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Logarithmic Moving Average (LMA) uses advanced logarithmic weighting to create a dynamic trend-following indicator that prioritizes recent price action while maintaining statistical significance. Unlike traditional moving averages that use linear or exponential weights, this indicator employs logarithmic decay functions to create a more sophisticated price averaging system that adapts to market volatility and momentum conditions.

> The indicator's core innovation lies in its logarithmic weighting system, where weights are calculated using the formula: [pine]w = 1.0 / math.pow(math.log(i + steepness), 2)[/pine] The steepness parameter controls how aggressively recent data is prioritized over historical data, creating a dynamic weight decay that can be fine-tuned for different trading styles. This logarithmic approach provides more nuanced weight distribution compared to exponential moving averages, offering better responsiveness while maintaining stability.

> The LMA calculation combines multiple sophisticated components. First, it calculates the logarithmic weighted average of closing prices. Then it measures the slope of this average over a 10-period lookback: [pine]lmaSlope = (lma - lma[10]) / lma[10] * 100[/pine] The system also incorporates trend quality assessment using R-squared correlation analysis of log-transformed prices, measuring how well the price data fits a linear trend model over the specified period.

> The final signal generation uses the formula: [pine]signal = lmaSlope * (0.5 + rSquared * 0.5)[/pine] which combines the LMA slope with trend quality weighting. When momentum confirmation is enabled, the indicator calculates annualized log-return momentum and applies a multiplier when the momentum direction aligns with the signal direction, strengthening confirmed signals while filtering out weak or counter-trend movements.

> Long Entry Threshold Zone: Area above positive threshold (default 0.5) indicating confirmed bullish signals suitable for long positions

> Short Entry Threshold Zone: Area below negative threshold (default -0.5) indicating confirmed bearish signals suitable for short positions

> Momentum Weight Factor: When short-term log-return momentum aligns with LMA signal direction, the signal receives additional weight confirmation

> Scalping: Highly responsive setup with shorter period and higher steepness for ultra-short-term trades on 1-15 minute charts, optimized for quick momentum shifts.

> Swing Trading: Extended period with moderate steepness and increased smoothing for multi-day positions, designed to filter noise while capturing larger price swings on 1-4 hour and daily charts.

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

- https://www.tradingview.com/script/gaMszEIG-Logarithmic-Moving-Average-LMA-QuantAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
