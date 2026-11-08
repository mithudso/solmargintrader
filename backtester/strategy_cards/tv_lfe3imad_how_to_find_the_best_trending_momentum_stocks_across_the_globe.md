---
id: tv_lfe3imad_how_to_find_the_best_trending_momentum_stocks_across_the_globe
name: "How to find the best trending momentum stocks across the globe"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of How to find the best trending momentum stocks across the globe; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [point-in-time-eligible-stock-universe, constituent-ohlcv]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# How to find the best trending momentum stocks across the globe

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

The source screens across markets using yearly and monthly performance, optionally weekly performance, and looks for prices and moving averages running in a steady parallel uptrend. After a recent pullback, it favors RSI pointing upward between 55 and 65. The performance thresholds, moving-average periods, eligible universe, precise pullback/recovery definition, entry and exit are not disclosed. Preserve the stated screening constraints without supplying invented defaults or implying that RSI 65 establishes fair value.

## Documented inputs and source details

> Have been asked a few times how to find stocks that are in a nice steady uptrend across multiple markets.

> Once you have a list of suitable stocks in your watch list you can then go through them and work out which ones to potentially buy based on your own criteria.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: point-in-time-eligible-stock-universe, constituent-ohlcv.
The full point-in-time input set has not been verified in this repository.
A single OHLCV series cannot supply these inputs; current snapshots cannot replace history.

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

- https://www.tradingview.com/chart/1137/LFe3ImAd-How-to-find-the-best-trending-momentum-stocks-across-the-globe/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Additional bound source rules

The following source passages support the mechanism above. They are author
descriptions, not repository performance evidence.

````text
A super simple way is to use the built in TradingView screener, add some moving averages to your chart, and then set your yearly, monthly, and optionally weekly performance values to filter the list down to a manageable number. Look through the results for stocks where the price and the moving averages are all running together nicely in parallel. The whole slow and steady approach.
````

````text
I typically look for stocks with an RSI pointing up but between 55 ( shows momentum) and 65 (not yet over valued) that have had a bit of a pullback recently, but look like they are heading up again.
````
