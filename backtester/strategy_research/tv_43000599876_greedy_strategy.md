---
id: tv_43000599876_greedy_strategy
name: "Greedy Strategy"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Greedy Strategy; not a tested trading strategy."
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
# Greedy Strategy

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Greedy Strategy opens an initial order if there is a gap between current open and the high or low of the previous bar. If open is greater than previous high, strategy goes long, if open is below the low of the previous bar, it opens a short position. After a position is opened, it will continue filling orders in the same direction as long as the color of the candle is consistent with the open position. If the current position is long, new long orders will be created for every consequent green candle and vice versa. This will proceed until the candle of a different color or until the limit

> strategy("Greedy Strategy", pyramiding = 100, calc_on_order_fills=false, overlay=true)

> maxidf = input(title="Max Intraday Filled Orders", defval=5)

> The limit can be changed in the settings by editing the Max Intraday Filled Orders value. The Tp and Sl settings allow you to set the Stop Loss and Take Profit. The value represents the number of minticks above/below the position price where the TP and SL will be located.

> strategy.entry("GapUp", strategy.long, stop = high[1], when = upGap)

> strategy.entry("Dn", strategy.short, stop = close, when = dn)

> strategy.entry("GapDn", strategy.short, stop = low[1], when = dnGap)

> strategy.entry("Up", strategy.long, stop = close, when = up)

> strategy.risk.max_intraday_filled_orders(maxidf)

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

- https://www.tradingview.com/support/solutions/43000599876-greedy-strategy/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
