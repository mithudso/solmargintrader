---
id: tv_xdwgv3fx_ttrades_daily_bias_tfo
name: "TTrades Daily Bias [TFO]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TTrades Daily Bias [TFO]; not a tested trading strategy."
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
# TTrades Daily Bias [TFO]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Inspired by @TTrades_edu video on daily bias, this indicator aims to develop a higher timeframe bias and collect data on its success rate. While a handful of concepts were introduced in said video, this indicator focuses on one specific method that utilizes previous highs and lows. The following description will outline how the indicator works using the daily timeframe as an example, but the weekly timeframe is also an included option that functions in the exact same manner.

> The table indicates the success rate of price hitting the levels provided by each period's bias, followed by the success rate of price closing through said levels after reaching them, as well as the sample size of data collected for each scenario.

> Alerts can be configured to indicate the bias for a new period, and/or when price hits its previous highs and lows. Simply enable the alerts you want from the indicator's settings and create a new alert with this indicator as the condition. There will be options to use "Any alert() function call" which will alert whatever is selected from the settings, or you can use more specific alerts for bullish/bearish bias, whether price hit PDH/PDL, etc.

> In the above crude oil futures (CL1!) 30m chart, we can glean a lot of information from the table in the top right. First we may note that the "PDH" cell is red, which indicates that the current day's bias was targeting PDH and it has already traded through that level. We might also note that the "PWH" cell is blue, which indicates that the weekly bias is targeting the previous week high (PWH) but price has yet to reach that level.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_inside_bar`.

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

- https://www.tradingview.com/script/xdwgV3Fx-TTrades-Daily-Bias-TFO/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
