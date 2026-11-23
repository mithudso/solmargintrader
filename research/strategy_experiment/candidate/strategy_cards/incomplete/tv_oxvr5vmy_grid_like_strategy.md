---
id: tv_oxvr5vmy_grid_like_strategy
name: "Grid Like Strategy"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Use a symmetric step-through-price process to demonstrate the apparent recovery benefits and real capital/friction problems of martingale and anti-martingale sizing."
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

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Use a symmetric step-through-price process to demonstrate the apparent recovery benefits and real capital/friction problems of martingale and anti-martingale sizing.

## How it works

- Equally spaced levels define one-step targets and stops. After a winning long, the next long starts at the new level; after a losing long, the strategy reverses short.
- A martingale multiplier increases exposure after losses. Anti-martingale instead increases it after wins; multiplier 1 keeps size constant.
- This is a sequential directional grid experiment with position reversals, not the repository's ladder of simultaneous resting buy/sell orders.

## Documented rules and trade lifecycle

- When price crosses the chosen level upward, open long with target one grid level above and stop one below.
- At a profit, close and reopen in the described direction at the next step. At a loss, close and reverse with target/stop one step away.
- Scale size after the relevant losing or winning event according to the selected multiplier and mode.
- The prose explains the long-to-short transition; full mirrored short-state and reset semantics need source-code confirmation.

## Parameters and stated settings

- Point controls level spacing in the instrument price scale; base order size is units/contracts.
- Martingale multiplier and anti-martingale mode are inputs. A multiplier of 1 means constant size; no complete defaults are disclosed.

## Failure modes and caveats

- Geometric exposure needs finite-capital and loss-streak limits; changing size does not create an entry edge.
- Spreads, commissions and stop gaps break the ideal symmetric-payoff recovery argument.
- The author's illustrative 0.5^9 calculation assumes a particular independent fixed-length sequence; it is not a bound on the chance of encountering a long losing streak over repeated trading.

## Missing information and implementation boundary

- Recover grid anchor, crossed-level selection on multi-level bars, full short-side state, size resets and maximum exposure.
- Avoid mapping this directly to ladder_grid or exposure-staircase grid: their order and payoff models differ.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: intent

> The motivations behind posting such a strategy isn't to glorify such systems, but rather to present the problems behind them, many users come to me with their ideas and glorious ways to make money, sometimes they present strategies using the martingale, and it is important to present the flaws of this methodology rather than blindly saying "you shouldn't use it".

### E2: sizing

> The martingale multiplier determines the factor by which the position size is multiplied after a loss, using values higher to 2 will "squarify" your balance, while a value of 1 would use a constant position sizing.
> 
> Finally, the anti-martingale parameter determines whether the strategy uses a reverse martingale or not, if set to true then the position size is multiplied after any wins.

### E3: grid

> The goal of a simple grid strategy is to go long once the price crossover a certain level, a take profit is set at the level above the current one and stop loss is placed at the level below the current one, in a winning scenario the price reach the take profit, the position is closed and a new one is opened with the same setup. In a losing scenario, the price reaches the stop loss level, the position is closed and a short one is opened, the take profit is set at the level below the current one, and a stop loss is set at the level above the current one. Note that all levels are equally spaced.

### E4: cost

> Our first problem is frictional costs, one example being the spread, but this is a common problem for any strategy, however here a martingale is extra sensitive to it, if the strategy does not account for it then we will still double our positions costs but we might not recover all the losses of a losing streak, instead we would be recovering only a proportion of it, under such scenario you would be certain to lose over time.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> It is possible to use progressive position sizing in order to recover from past losses, a well-known position sizing system being the "martingale", which consists of doubling your position size after a loss, this allows you to recover any previous losses in a losing streak + winning an extra. This system has seen a lot of attention from the trading community (mostly from beginners), and many strategies have been designed around the martingale, one of them being "grid trading strategies".

> Now consider how a martingale affects our risk-reward ratio, assuming unity position sizing our martingale sequence can be described by 2^(x-1), using this formula we would get the amount of shares/contracts we need to purchase at the x trade of a losing streak, we would need to purchase 256 contracts in order to recover from a losing streak of size 9, this is enormous when you take into account that your wins are way smaller, the risk-reward ratio is totally unfair.

> You will see a lot of auto-trading strategies that are based on a grid approach, they might even use a martingale. While the backtests will look appealing, you should think twice before using such kind of strategy, remember that frictional costs will be a huge challenge for the strategy, and that it assumes that the trader has an important initial capital. We have also seen that the risk/reward ratio is theoretically the worst you can have on a strategy, having a low reward and a high risk. This does not mean that progressive position sizing is bad, but it should not be pushed to the extreme.

> The goal of a simple grid strategy is to go long once the price crossover a certain level, a take profit is set at the level above the current one and stop loss is placed at the level below the current one, in a winning scenario the price reach the take profit, the position is closed and a new one is opened with the same setup. In a losing scenario, the price reaches the stop loss level, the position is closed and a short one is opened, the take profit is set at the level below the current one, and a stop loss is set at the level above the current one. Note that all levels are equally spaced.

> Another problem are gaps, market price might open under a stop-loss without triggering it, and this is a big no-no.

> You can also simulate the effect of a martingale without doubling your position size by doubling your target profit, if for example you have a 10$ profit-target/stop-loss and lose a trade, you can use a 20$ profit target to recover from the lost trade + gain a profit of 10$. While this approach does not introduce exponential decay in your balance, you are betting on the market reaching your take profits, considering the fact that you are doubling their size you are expecting market volatility to increase drastically over time, as such this approach would not be extremely effective for high los

> Finally, the anti-martingale parameter determines whether the strategy uses a reverse martingale or not, if set to true then the position size is multiplied after any wins.

> Of course, some users might think that a losing streak of size 9 is pretty unlikely, if the probability of winning and losing are both equal to 0.5, then the probability of 9 consecutive losses is equal to 0.5^9, there are approximately 0.2% of chance of having such large losing streak, note however that under a ranging market such case scenario could happen, but we will see later that the length of a losing streak is not the only problem.

> Martingale - Exponential Decays - Risk/Reward

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
