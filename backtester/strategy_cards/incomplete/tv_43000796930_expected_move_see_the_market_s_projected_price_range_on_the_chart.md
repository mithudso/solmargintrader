---
id: tv_43000796930_expected_move_see_the_market_s_projected_price_range_on_the_chart
name: "Expected Move: see the market's projected price range on the chart"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Expected Move: see the market's projected price range on the chart; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [atm-implied-volatility-by-expiry]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Expected Move: see the market's projected price range on the chart

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Expected Move is an options indicator on Supercharts that shows the price range the options market expects an underlying asset to trade within by a given expiration date. The range is calculated from the at-the-money (ATM) implied volatility of each option series and is drawn directly on the chart, so you can see the market's volatility expectations without an options calculator, an options chain, or manual math.

> Suppose you follow Apple and want to know how far the options market expects AAPL to move over the next month. Expected Move plots an upper and a lower bound for every listed expiration within that period, forming a cone that widens over time.

> The settings are split into three tabs: Inputs, Style, and Visibility.

> Horizon defines how far into the future the cone extends. Available options: Nearest, 1 week, 2 weeks, 1 month, 2 months, 3 months, 6 months, 9 months, 1 year, and All. The selected horizon includes all points that come before it:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: atm-implied-volatility-by-expiry.
The full point-in-time input set has not been verified in this repository.
OHLCV alone cannot supply these inputs; current snapshots cannot replace history.

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

- https://www.tradingview.com/support/solutions/43000796930-expected-move-see-the-market-s-projected-price-range-on-the-chart/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
