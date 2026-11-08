---
id: tv_oxvr5vmy_grid_like_strategy
name: "Grid Like Strategy"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Grid Like Strategy; not a tested trading strategy."
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
# Grid Like Strategy

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific strategy named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> It is possible to use progressive position sizing in order to recover from past losses, a well-known position sizing system being the "martingale", which consists of doubling your position size after a loss, this allows you to recover any previous losses in a losing streak + winning an extra. This system has seen a lot of attention from the trading community (mostly from beginners), and many strategies have been designed around the martingale, one of them being "grid trading strategies".

> Now consider how a martingale affects our risk-reward ratio, assuming unity position sizing our martingale sequence can be described by 2^(x-1), using this formula we would get the amount of shares/contracts we need to purchase at the x trade of a losing streak, we would need to purchase 256 contracts in order to recover from a losing streak of size 9, this is enormous when you take into account that your wins are way smaller, the risk-reward ratio is totally unfair.

> You will see a lot of auto-trading strategies that are based on a grid approach, they might even use a martingale. While the backtests will look appealing, you should think twice before using such kind of strategy, remember that frictional costs will be a huge challenge for the strategy, and that it assumes that the trader has an important initial capital. We have also seen that the risk/reward ratio is theoretically the worst you can have on a strategy, having a low reward and a high risk. This does not mean that progressive position sizing is bad, but it should not be pushed to the extreme.

> The goal of a simple grid strategy is to go long once the price crossover a certain level, a take profit is set at the level above the current one and stop loss is placed at the level below the current one, in a winning scenario the price reach the take profit, the position is closed and a new one is opened with the same setup. In a losing scenario, the price reaches the stop loss level, the position is closed and a short one is opened, the take profit is set at the level below the current one, and a stop loss is set at the level above the current one. Note that all levels are equally spaced.

> Another problem are gaps, market price might open under a stop-loss without triggering it, and this is a big no-no.

> You can also simulate the effect of a martingale without doubling your position size by doubling your target profit, if for example you have a 10$ profit-target/stop-loss and lose a trade, you can use a 20$ profit target to recover from the lost trade + gain a profit of 10$. While this approach does not introduce exponential decay in your balance, you are betting on the market reaching your take profits, considering the fact that you are doubling their size you are expecting market volatility to increase drastically over time, as such this approach would not be extremely effective for high los

> Finally, the anti-martingale parameter determines whether the strategy uses a reverse martingale or not, if set to true then the position size is multiplied after any wins.

> Of course, some users might think that a losing streak of size 9 is pretty unlikely, if the probability of winning and losing are both equal to 0.5, then the probability of 9 consecutive losses is equal to 0.5^9, there are approximately 0.2% of chance of having such large losing streak, note however that under a ranging market such case scenario could happen, but we will see later that the length of a losing streak is not the only problem.

> Martingale - Exponential Decays - Risk/Reward

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_martingale_sizing`, `tv_method_risk_based_sizing`.

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

- https://www.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
