---
id: tv_1nhvl40i_fibonacci_time_price_zones
name: "Fibonacci Time-Price Zones"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Fibonacci Time-Price Zones; not a tested trading strategy."
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
# Fibonacci Time-Price Zones

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> 🟩 Fibonacci Time-Price Zones is a chart visualization tool that combines Fibonacci ratios with time-based and price-based geometry to analyze market behavior. Unlike typical Fibonacci indicators that focus solely on horizontal price levels, this indicator incorporates time into the analysis, providing a more dynamic perspective on price action.

> The indicator offers multiple ways to visualize Fibonacci relationships. Drawing segmented circles creates a unique perspective on price action by incorporating time into the analysis. These segmented circles, similar to TradingView's built-in Fibonacci Circles, are derived from Fibonacci time and price levels, allowing traders to identify potential turning points based on the dynamic interaction between price and time.

> By combining these distinct methods—circles, orthogonal patterns, sloped projections, and horizontal levels—the indicator provides a comprehensive approach to Fibonacci analysis based on both time and price relationships. Each visualization method offers a unique perspective on market structure while maintaining the core principle of time-price interaction.

> The Circular shape's partial circles are calculated and scaled to align with TradingView's built-in Fibonacci Circles. These circles are plotted from the second swing point onward. This approach ensures consistent and accurate visualization across all market types, including those with gaps or closed sessions, which unlike 24/7 markets, do not have a direct one-to-one correspondence between bar indices and time. To maintain accurate geometric proportions across varying chart scales, the indicator calculates an aspect ratio by normalizing the proportional difference between vertical (price) and

> Comparison of Fibonacci Time-Price Zones (Shape: Horizontal) with TradingView's Built-in Retracement and Extension Tools (overlaid): This example demonstrates how the Horizontal structure aligns with TradingView’s retracement and extension levels, allowing users to integrate multiple tools seamlessly. The Fibonacci circle connects retracement and extension zones, highlighting the potential relationship between past retracements and future extensions.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_fib_extensions`, `tv_method_market_structure`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/1NHVL40I-Fibonacci-Time-Price-Zones/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
