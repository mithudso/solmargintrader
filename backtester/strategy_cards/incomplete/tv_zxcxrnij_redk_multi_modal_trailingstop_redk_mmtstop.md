---
id: tv_zxcxrnij_redk_multi_modal_trailingstop_redk_mmtstop
name: "RedK Multi-Modal TrailingStop (RedK MMTStop)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK Multi-Modal TrailingStop (RedK MMTStop); not a tested trading strategy."
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
# RedK Multi-Modal TrailingStop (RedK MMTStop)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> RedK MMTStop is a Multi-Modal Trailing Stop indicator - Let's quickly explore the "trailing stop" concept first as a refresher - then explain what a multi-modal trailing stop indicator does.

> The "Status Line" measures the gap between price and the stop in ATR units, then colors it:

> The colored bands sit between the stop and price on the chart. Band borders can be shown or hidden separately from the colored fill. The Safe Zone is calculated based on (user-adjustable) ATR value, so it is "volatility-aware" - It uses its own ATR setting (regardless of the selected Trailing Stop method) to ensure it works the same across all five methods — including the ones with no ATR setting of their own.

> This is an analysis and risk-management tool, not a signal service and not trade advice. Also a trailing stop is a mechanism that helps you manage an existing position — it does not tell you what or when to buy or sell. Test any settings on your own instruments and timeframes before trading them.

> Note: A numeric flip signal is also exposed in the Data Window for use with the Pine Screener.

> A Trailing Stop is a core function for effective position & risk management, and there are various methods to implement a trailing stop. Regardless of the trailing stop method, the basic premise is the same: this mechanism is what enables the trader to maximize their position profit, and is the key to avoiding situations where profitable positions reverse into losses - which can happen to any trader, regardless of experience level - it's just the nature of trading. For that reason, there are so many Trailing Stop indicators out there, and many of them are of high quality.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/ZxCXrnij-RedK-Multi-Modal-TrailingStop-RedK-MMTStop/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
