---
id: tv_pkhv9soh_auto_fib_speed_resistance_fans_by_dgt
name: "Auto Fib Speed Resistance Fans by DGT"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Auto Fib Speed Resistance Fans by DGT; not a tested trading strategy."
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
# Auto Fib Speed Resistance Fans by DGT

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Fibonacci Speed and Resistance Fan is an analytical drawing tool used to indicate the support and resistance levels of an existing trend and the price level at which possible changes in the trend may occur.

> A Fibonacci Speed Resistance Fan consists of a trend line drawn between two extreme points - a trough and opposing peak or a peak and opposing trough - on which a set of sequential speed resistance lines are drawn above (which represents time) and below (which represents price). These lines are drawn based on time/price percentages of the distance between the beginning and the end of the trend line.

> The script is for informational and educational purposes only. Use of the script does not constitute professional and/or financial advice. You alone have the sole responsibility of evaluating the script output and risks associated with the use of the script. In exchange for using the script, you agree not to hold dgtrd TradingView user liable for any possible claim for damages arising from any decision you make based on use of the script

> - Pivot threshold can be adjusted via “Deviation” and “Depth” input options

> Traders can use the lines of the Fibonacci Speed and Resistance Fan to predict key points of resistance or support, at which they might expect price trends to reverse. Once a trader identifies patterns within a chart, they can use those patterns to predict future price movements and future levels of support and resistance. Traders use the predictions to time their trades. Key support and resistance levels tend to occur frequently at the 61.8-percent level on both uptrends and downtrends.

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

- https://www.tradingview.com/script/pKhv9SoH-Auto-Fib-Speed-Resistance-Fans-by-DGT/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
