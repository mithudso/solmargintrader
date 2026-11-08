---
id: tv_kjj8hddk_dynamic_dots_dashboard_a_cloud_zlema_composite
name: "Dynamic Dots Dashboard (a Cloud/ZLEMA Composite)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Dynamic Dots Dashboard (a Cloud/ZLEMA Composite); not a tested trading strategy."
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
# Dynamic Dots Dashboard (a Cloud/ZLEMA Composite)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The purpose of this indicator is to provide an easy-to-read binary dashboard of where the current price is relative to key dynamic supports and resistances. The concept is simple, if a dynamic s/r is currently acting as a resistance, the indicator plots a dot above the histogram in the red box. If a dynamic s/r is acting as support, a dot is plotted in the green box below.

> There is an option (off by default, shown in the headline image above) to fill the bar colors based on how many dynamic s/r's are above or below the current price. This can make things easier for some users, confusing for others. I defaulted them to off as I don't want colors to confuse the primary value proposition of the indicators, which is the dot heat map. You can turn on colored bars in the settings.

> Developers: I created this originally as a starting point for more complex algos I'm working on. One algo is reading this dot dashboard and taking a position size relative to the s/r's above and below. Another cloud algo is using the results as inputs to spot good setups.

> Alternatively, you can add your preferred linear SR's, fibs, etc. to the chart and quickly glance at the dashboard to gauge how dynamic SR's may be contributing to the risk of your trade.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_risk_based_sizing`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/kjj8hdDK-Dynamic-Dots-Dashboard-a-Cloud-ZLEMA-Composite/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
