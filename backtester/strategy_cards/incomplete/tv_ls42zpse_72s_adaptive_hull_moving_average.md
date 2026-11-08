---
id: tv_ls42zpse_72s_adaptive_hull_moving_average
name: "72s: Adaptive Hull Moving Average+"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of 72s: Adaptive Hull Moving Average+; not a tested trading strategy."
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
# 72s: Adaptive Hull Moving Average+

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> One challenging issue for beginner traders is to differentiate market conditions, whether or not the current market is giving best possibility to stack profits, as earliest, in shortest time possible, or not.

> On intraday, we've seen some big actions by big banks are somewhat can be defined --or circling around-- by HMA 200. I've been thinking on to make the visuals more conform to price dynamics (separating major movement and minor noise) to get clearer signs of when it starts to happen. So it will be easier to see in a glance when the strength starts really taken place, with less cluttered chart.

> This Adaptive HMA is using the new Pine Script's feature which now support Dynamic Length arguments for several Pine functions. ( read: https://www.tradingview.com/blog/en/pine-functions-support-dynamic-length-arguments-20554/). It hasn't support the built-in HMA() directly, but thankfully we can use its wma() formula to construct. (Note: I tweaked a bit HMA formula already popular here by using plain int() instead of round() on its wma's length, since I find it precisely match tradingview's built-in HMA).

> Very very nice BUY entry to catch big up-movement if:

> Clear SELL entry signal is same as above, just the opposite.

> For exit/take-profit point, you can use a second faster period static HMA. Or you can also use RSI. Here's an example:

> You can choose which aspect the Adaptive HMA period will adapt to.

> In this study I present it with two options: Volume and Volatility. It will "moves" faster or slower depends on which situation the aspect is currently into. ie: When volume is generally low or volatile readings is not there, price won't move very much, so the adapting MA will slow down by dynamically lengthen the lookback period, and vice versa, and so on.

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

- https://www.tradingview.com/script/ls42zPSE-72s-Adaptive-Hull-Moving-Average/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
