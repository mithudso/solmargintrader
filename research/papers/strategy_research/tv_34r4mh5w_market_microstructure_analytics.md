---
id: tv_34r4mh5w_market_microstructure_analytics
name: "Market Microstructure Analytics"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Market Microstructure Analytics; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Market Microstructure Analytics

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Every time you buy or sell a financial instrument, you pay a cost that never appears on your brokerage statement. It is not a commission. It is not a fee. It is the spread between the price at which someone is willing to sell to you and the price at which someone is willing to buy from you. That gap, measured in ticks, basis points, or fractions of a percent, is the bid-ask spread. Over a single trade it looks small. Over thousands of trades, across a year, for a fund managing billions, it compounds into one of the most significant sources of performance drag in all of finance.

> The first was by Roll (1984), who noticed something elegant: in an efficient market, the prices of consecutive trades should not be correlated with each other, because any predictability would be arbitraged away. But if you look at actual trade-by-trade price changes, you consistently find negative autocorrelation. Prices bounce back and forth. The reason, Roll argued, is the bid-ask spread itself. Buyers trade at the ask and sellers at the bid, so consecutive trades alternate between two price levels. This bouncing creates a predictable negative covariance in price changes, and the size of th

> The Roll (1984) estimator is the oldest and most widely cited. It computes the rolling covariance between a price change and the price change that came before it, then takes two times the square root of the negative of that covariance. One important detail: Roll's model is defined in terms of absolute price changes, not log-returns. Using log-returns introduces a scaling distortion tied to the price level of the asset, which biases the spread estimate upward at high prices. This implementation correctly uses delta-P throughout.

> The Corwin-Schultz (2012) estimator takes a fundamentally different approach. Rather than looking at the serial structure of price changes, it uses the high-low range of a bar. The core insight is that the high price of any trading period is most likely a transaction that occurred at the ask, while the low price is most likely a transaction at the bid. If you look at a two-period window, the combined high-low range reflects the true price variance over those two periods plus the spread component. A single-period range conflates variance and spread; the two-period structure allows them to be se

> The Abdi-Ranaldo (2017) estimator is the most recent of the three and, in empirical tests, the most stable. For each bar, it computes a quantity called c, defined as the log of the close price minus the average of the log-high and log-low. This is the signed deviation of the close price from the geometric midpoint of the bar's range, expressed in log-space. Abdi and Ranaldo proved that the expected value of the product of c at time t and c at time t plus one equals negative one quarter of the spread squared. This means that by measuring how negatively c correlates with the next period's c, you

> For professional traders and systematic strategy developers, the Kyle lambda signal has specific applications. When lambda is elevated relative to its own history, which the dashboard displays as the adverse selection z-score, it indicates that price changes are disproportionate to the measured order flow. This is consistent with the presence of informed traders, a phenomenon central to the theoretical work of Kyle (1985) and Glosten and Milgrom (1985). Elevated adverse selection is one of the clearest early warning signs of an impending directional move driven by asymmetric information, such

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/34R4Mh5W-Market-Microstructure-Analytics/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
