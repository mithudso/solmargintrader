---
id: tv_43000591665_inside_bar_strategy
name: "InSide Bar Strategy"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of InSide Bar Strategy; not a tested trading strategy."
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
# InSide Bar Strategy

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The InSide Bar Strategy is a significant candlestick pattern that helps traders time entries with low risk. This strategy can be used to follow and trade with a trend or with reversals. An InSide Bar is a candle that is essentially “covered” by the previous candle. When you see this type of candle, it usually means that there has been reduced volatility within markets. The InSide Bars are not all equal in terms of size and range, and it is important to keep this in mind throughout your analysis. This will be explained further below in our What to look for section.

> Traders use the InSide Bars strategy by waiting for price to make a reversal move and then form an InSide Bar. This way they are able to control their positions based on specific criteria and manage the perfect entry point by waiting for an ideal reversal in the market. In addition, there would then be volatility contraction, allowing the buying pressure to potentially continue if the price were to break out higher. The approach is also less prone to fake outs.

> Entry. Some traders prefer to enter using a stop order and when the price breaks out of the InSide Bar. Many like this method because they enter the trade just as price moves in their favor. Please be mindful, however, that there is a possibility of a false breakout in this case. Traders could also wait for the candle to close, but this comes with the risk of missing a big move in the market. Our suggestion would be to find whichever method works best for you.

> Exit. Depending on what you are trading and what your end goals are, your exits will vary. If you are looking to capture a swing, some traders find it most helpful to exit trades before any opposition starts. If aiming to ride a trend, however, traders tend to trail their stop loss just as the market begins to adjust to their prediction.

> There are limitations to almost every indicator, and those specific to the InSide Bar Strategy would be choosing to trade the breakout of the indicator. We caution traders here because with low probability trades like this example, the market does not have a smooth range and it could prove more trouble than it is worth.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_candlestick_patterns`, `tv_method_inside_bar`, `tv_method_liquidity_sweep`.

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

- https://www.tradingview.com/support/solutions/43000591665-inside-bar-strategy/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
