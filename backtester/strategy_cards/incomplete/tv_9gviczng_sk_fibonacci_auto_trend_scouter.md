---
id: tv_9gviczng_sk_fibonacci_auto_trend_scouter
name: "[SK] Fibonacci Auto Trend Scouter"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of [SK] Fibonacci Auto Trend Scouter; not a tested trading strategy."
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
# [SK] Fibonacci Auto Trend Scouter

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The FATS - Fibonacci Auto Trend Scouter automatically draws active trends from 2 different timeframes along with Fibonacci Support and Resistance levels. It also has a Sights feature for each timeframe which points from it's middle towards the current price. The tool is also highly customizable for you to take this indicator over 9000. If you like the tool and it adds value to you - share the love on the like button and visit my profile to check out my other indicators and subscribe, so you're notified of my next scripts and ideas!

> As the values change with price movement, the lines are updated. They are color coded for uptrend and downtrend based on the direction of each individual line. Trend lines can be set up to color with only the default value on the configurations panel.

> The tool has a very useful feature to automatically detect the highest and lowest value from the short timeframe to calculate Fibonacci support and resistant levels. To keep the chart area clean, the lines are drawn short by default towards the right side of the price but provide inputs to increase the size of the level lines towards the left and right direction. A triangle label appears to the side of each line which holds the Fibonacci level and price data inside the tooltip, hover over them to activate.

> This is a neat feature that may help you get a better feel for the direction the current movement is heading towards in correlation with the short or medium length timeframe trends. The sight draws a line from the middle vertical point of the trend coordinates towards the current price. They are toggled off by default but can be enabled in the configurations panel.

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

- https://www.tradingview.com/script/9GviCznG-SK-Fibonacci-Auto-Trend-Scouter/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
