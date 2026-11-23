---
id: tv_8os1nbr8_inwcoin_martingale_strategy_for_bitcoin
name: "inwCoin Martingale Strategy ( for Bitcoin )"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Demonstrate how long-only averaging down can produce repeated recoveries while accumulating a ruinous tail exposure; the author presents it as a martingale failure experiment."
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
# inwCoin Martingale Strategy ( for Bitcoin )

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Demonstrate how long-only averaging down can produce repeated recoveries while accumulating a ruinous tail exposure; the author presents it as a martingale failure experiment.

## How it works

- A selectable indicator opens the initial long. If price falls sufficiently below the average entry, additional exposure grows by a user-selected multiplier.
- The intended recovery mechanism is a lower blended entry price and a percentage profit target on that average. More capital is committed precisely when the position is losing.
- The author explicitly describes portfolio failure in a large adverse move. Attractive historical recoveries are not evidence that capital can cover an unbounded adverse path.

## Documented rules and trade lifecycle

- Choose an initial-entry condition: the source's "MACD signal > 0" wording, Stochastic RSI crossing up from 20, or price crossing above a 2.3-ATR channel condition. The MACD line definition is not clarified.
- Begin averaging down when the selected adverse percentage relative to average entry is reached. Multiply the added position size according to the martingale setting.
- Take profit at the selected percentage from average entry, according to the parameter description. The later prose mentions an equity-line exit instead; this discrepancy needs source-code resolution.
- The publication says remaining positions close if equity is below zero. Treat that as a simulated failure condition, not a stop that bounds real losses.

## Parameters and stated settings

- Martingale multiplier is stated to default to 2.
- Initial size can be fixed units or a percentage of initial capital.
- Profit percentage, adverse averaging threshold, selected entry mode and date range are configurable; their complete defaults are missing.

## Failure modes and caveats

- Geometric sizing exhausts finite capital; a recovery is conditional on surviving the drawdown and financing every addition.
- Fees, gaps, liquidation and unavailable liquidity invalidate a cost-free recovery argument. The source itself records a liquidation example.

## Missing information and implementation boundary

- Recover the exact MACD condition, ATR-channel anchor, addition sequence, maximum additions, size reset and order timing.
- Resolve the conflicting average-entry versus equity-line take-profit wording. No numerical performance claim is independently reproduced here.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: intent

> inwCoin Martingale Strategy is the proof of concept strategy that in the end, anyone who using martingale strategy will kaboom their portfolio.

### E2: entries

> Start Position Logic = condition to enter first trade
> - MACD singal > 0 : Self explanatory, default macd value
> - Stochastic RSI cross up : enter when sto line cross up from bottom ( 20 )
> - ATR channel : enter trade if price cross above 2.3 ATR
> Take Profit Percent = take profit target % from average entry
> Start martingale ..= if price compare to average position entry less than this %, it will start to double down ( martingale )
> Martingale Multiplier = you can specific how big you'll double down, default is 2
> Trade Direction = long only for now

### E3: failure

> If equity less than 0, it will close any remaining positions ( It's mean your position got liquidated )
> If price > equity line for "take profit percent" it will close any remaining positions.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> ** Same as my previous martingale script but this version = opensource **

> 2nd loss = bet 2$ : if win, get 2$ / real profit = 1$ ( 2-1 )

> 3rd loss = bet 4$ : if win, get 4$ / real profit = 1$ ( 4 - ( 2+1) )

> For those who don't know what is "martingale".. it's a simple double down strategy in the hope to cover the loss in previous entry.

> Take Profit Percent = take profit target % from average entry

> Start martingale ..= if price compare to average position entry less than this %, it will start to double down ( martingale )

> If price > equity line for "take profit percent" it will close any remaining positions.

> Fixed position size option = if uncheck, the "Start position size" parameter will be % of your initial capital. If checked, it will fixed position size ( like 1 BTC )

> But in reality, this strategy will destroy your whole portfolio eventually some time in the future. Because there will be some "Blackswan event" in market at some point in time. And one who ignore this fact, will lose everything.

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/8OS1nbr8-inwCoin-Martingale-Strategy-for-Bitcoin/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
