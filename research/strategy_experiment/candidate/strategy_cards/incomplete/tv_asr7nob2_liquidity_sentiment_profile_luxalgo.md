---
id: tv_asr7nob2_liquidity_sentiment_profile_luxalgo
name: "Liquidity Sentiment Profile [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Liquidity Sentiment Profile [LuxAlgo]; not a tested trading strategy."
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
# Liquidity Sentiment Profile [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Liquidity Sentiment Profile is an advanced charting tool that measures by combining PRICE and VOLUME data over specified anchored periods and highlights within a sequence of profiles the distribution of the liquidity and the market sentiment at specific price levels.

> The Liquidity Sentiment Profile allows traders to reveal significant price levels, dominant market sentiment, support and resistance levels, supply and demand zones, liquidity availability levels, liquidity gaps, consolidation zones, and more based on price and volume data.

> The Liquidity Sentiment Profiles aim to present Value Areas based on the significance of price levels, thus allowing users to identify value areas that can be formed more than once within the range of a single profile.

> The script takes into account user-defined parameters and plots the profiles, where detailed usage for each user-defined input parameter in indicator settings is provided with the related input's tooltip.

> Anchor Period: The indicator resolution is set by the input of the Anchor Period, the default option is AUTO.

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

- https://www.tradingview.com/script/asr7nOb2-Liquidity-Sentiment-Profile-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
