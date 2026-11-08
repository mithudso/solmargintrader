---
id: tv_djr8hv4v_waindrops_makit0
name: "Waindrops [Makit0]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Waindrops [Makit0]; not a tested trading strategy."
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
# Waindrops [Makit0]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Plot waindrops (custom volume profiles) on user defined periods, for each period you get high and low, it slices each period in half to get independent vwap, volume profile and the volume traded per price at each half.

> You can think of each waindrop as an user defined candlestick or bar with four key values:

> The indicator performance is highly related to the underlying volatility (tick wise), the script takes each candlestick or bar and for each tick in it stores the price and volume, if the ticker in your chart has thousands and thousands of ticks per bar the indicator will throw an error for sure, it can not calculate in time such amount of ticks.

> • GREEN: when the right vwap is higher than the left vwap (bullish sentiment )

> • RED: when the right vwap is lower than the left vwap (bearish sentiment )

> As example you can setup unbalanced periods to get independent volume profiles for the overnight and cash sessions on the futures market, or 24H periods to get the full session volume profile of EURUSD

> plotted as a vertical histogram for each half of a custom period. By default the period is 60 so it plots an independent volume profile each 30m

> What all of that means? Simply put, this will throw error on the BITCOIN pair BTCUSD (high volatility with tick size 0.01) because it has too many ticks per bar, but lucky you it will work just fine on the futures contract BTC1! (tick size 5) because it has a lot less ticks per bar

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- https://www.tradingview.com/script/dJr8hv4v-Waindrops-Makit0/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
