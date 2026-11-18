---
id: prediction_markets
name: Prediction Markets (odds as a signal, and the markets as a venue)
kind: exposure-strategy
status: spec-only
family: event
summary: Two distinct ideas to consider: read prediction-market odds as a forward-looking signal for crypto, or trade the markets themselves (cross-venue mispricing, calibration bias). Spec-only: needs a price and resolution history the repo does not have.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [prediction-market-price-history, market-resolution-outcomes]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  min_edge: {default: 0.05, type: float, desc: "required gap between your probability and the market price, after fees, before any position"}
presets: {}
---
# Prediction Markets

Added at the owner's request (2026-11-07) as another item to consider. Nothing here was run, and no figure on this card is a result.

## What it is
A prediction market sells a contract that pays 1 if an event happens and 0 if it does not. The price `p` in [0, 1] is read as the market's implied probability. Two separate ideas hide under this one name, and they need different data and different tests:

1. **Odds as a signal.** Use the implied probability of an event that bears on crypto (a regulatory decision, an ETF outcome, a rate decision, a price-threshold market) as an input to an exposure rule on SOL. The market is information, not the thing traded.
2. **The market as the venue.** Trade the contracts themselves, where the edge would come from a mispricing: outcomes that do not sum to one, the same event priced differently on two venues, or systematic miscalibration (for example, long-shot outcomes priced above their frequency).

## Equation
```
implied probability      p_t = price of the YES contract at time t        (0 <= p <= 1)
buy-YES edge             e   = q - p - fees        q = your probability estimate
Kelly fraction (YES)     f*  = (q - p) / (1 - p)   scale down hard; q is an estimate, not a fact
exhaustive, exclusive set: buy every outcome if  sum_i p_i + fees < 1   (locks a payoff of 1)
calibration check        bucket contracts by p; compare each bucket's p to its realised frequency
signal form              target_t = g(p_t - p_{t-k})  for an event E linked to the asset
```

## Why it is only a card today
- **Signal use needs a link that holds.** An event price moves exposure only if the event moves SOL, and that link must be shown out of sample, not assumed. A few dozen resolved events is a thin sample for any rule built on them.
- **Venue use needs depth and settlement detail.** A last-trade price on a thin book is not an executable price; the executable side, the fee schedule and the resolution rules decide whether an edge survives.
- **Resolution is a lookahead trap.** The time a market resolved, and the time the outcome became public, are different timestamps. A history keyed on resolution time leaks the answer into the test.

## Data gap
`prediction-market-price-history` (timestamped prices, ideally with the order book) and `market-resolution-outcomes` (outcome, resolution time, and the time the outcome was knowable) for the markets used. Neither is in the repo. Which venues to use, and whether this owner may trade on them, are open questions, not facts this card settles.

## Works when
(Hypotheses, unmeasured.) Markets are liquid, the event has a clear link to the asset, and the price moves before the asset reprices.

## Fails when
Books are thin, a contract resolves on a technicality or a disputed source, fees and spreads exceed the edge, access is restricted for the trader's jurisdiction or venue, or the signal is already reflected in the spot price.

## Pairs with
`event_driven` (the same event-study framework, with a market price standing in for the news feed) and `trigger_trade`.

## Measured on SOL
Not measured. No code exists for this card.

## Likelihood of success: very-low

*Basis: a-priori. Nothing was run. The rating follows the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe) and the small number of resolved events any such test could use.*

## Caveats and limitations
- Legal and venue access depend on jurisdiction and the venue's own terms. This card does not assess either; check them before any account is opened or any money moves.
- The repo's rule applies: a backtest must not use a price or outcome that was not knowable at the time. Settle the timestamp question before any data is loaded.
- Cross-venue arbitrage here is not riskless: legs settle separately and rules differ between venues, so "the same event" may not resolve identically on both.

## How to run
No runner. See `event_driven` for the data-source gap that applies here too.
