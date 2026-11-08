---
id: tv_gjpxvoub_education_excerpt_sma_lwma_gma_tma_ema
name: "Education Excerpt: SMA, LWMA, GMA, TMA, EMA"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Education Excerpt: SMA, LWMA, GMA, TMA, EMA; not a tested trading strategy."
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
# Education Excerpt: SMA, LWMA, GMA, TMA, EMA

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> We decided to publish second part of the paper on moving averages. The first part detailed Simple Moving Average. In the second part we decided to present: linearly weighted moving average (LWMA), geometric moving average (GMA), triangular moving average (TMA) and exponentially smoothed moving average (EMA).

> The Linearly Weighted Moving Average (LWMA) is very similar to the Simple Moving Average (SMA) we introduced in our previous education excerpt. But while SMA gives each time period involved in the calculation same weight LWMA differentiates between the weight linked to each time interval. Normally, 10-day SMA calculation would be conducted by summing up each value per time period and then dividing this result by total number of time intervals (which would be 10 in this particular example). In this calculation each time period (each day) would have 10% weight. However, as mentioned before, LWMA

> LWMA = [(Pn * W1) + (Pn-1 * W2) + (Pn-2 * W3)] / summation of W

> The moving average can be used as simple tool to determine prevailing trend. Simplest way to determine current trend using moving average is to compare current value of security to current value of moving average. If value of moving average is below price of the security, then trend is considered to be upward. Contrary to that when value of moving average is above price of the security then trend is considered to be downward. Another method of determining trend is to use two same moving averages but with different length (different number of hours or days, etc.). These two moving averages woul

> Graph above depicts General Motors on daily time frame. It is visible that when price deviated too far from its 10-day SMA then retracement followed. However, it is not a rule that price will retrace full length back to moving average once it deviated too far from it.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`.

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

- https://www.tradingview.com/chart/AAPL/GJPxVOub-Education-Excerpt-SMA-LWMA-GMA-TMA-EMA/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
