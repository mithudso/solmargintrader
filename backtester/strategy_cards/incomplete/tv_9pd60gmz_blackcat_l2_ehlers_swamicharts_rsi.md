---
id: tv_9pd60gmz_blackcat_l2_ehlers_swamicharts_rsi
name: "[blackcat] L2 Ehlers SwamiCharts RSI"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of [blackcat] L2 Ehlers SwamiCharts RSI; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, level2-orderbook-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# [blackcat] L2 Ehlers SwamiCharts RSI

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> John F. Ehlers introuced SwamiCharts RSI in his "Cycle Analytics for Traders" chapter 16 on 2013.

> Since the MyRSI is computed for all values over the range of lookback periods, it must be an array in Pine v4.0 rather than a variable. The RSI is computed relative to the output of the roofing filter rather than price closes to eliminate the effects of Spectral Dilation. After the computation of the ratio, the indicator is smoothed in a SuperSmoother filter, so we must create the three most recent instances ourselves in the code. This is because Pine v4.0 retains historical values for variables but not for arrays. In fact, ratio must be an array also for the same reasons. The coefficients for

> Level 3 : comprehensive indicator/strategy. They are simple trading systems based on my strategies. They are commonly containing several or all of entry signal, close signal, stop loss, take profit, re-entry, risk management, and position sizing techniques. Even some interesting fundamental and mass psychological aspects are incorporated.

> SwamiCharts retain the core functionality of the technical indicators with which you're already familiar, while packing much more information into an easy-to interpret heat map chart. With SwamiCharts, you now visualize each indicator over a range of lookback periods

> to reveal a better view of the indicator's truer meaning in context. SwamiCharts provide a better solution because you can now visualize context over a wide range of lookback periods. Trends and cycles emerge more succinctly, while continuation patterns and reversals become

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_risk_based_sizing`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, level2-orderbook-history.
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

- https://www.tradingview.com/script/9Pd60GmZ-blackcat-L2-Ehlers-SwamiCharts-RSI/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
