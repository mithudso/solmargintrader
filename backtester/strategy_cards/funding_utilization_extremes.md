---
id: funding_utilization_extremes
name: Perp Borrow-Rate / Utilization Extremes
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: On Jupiter there is no funding rate. The tradeable signal is pool UTILIZATION. Highest-ranked spec-only signal.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [borrow-rate-history, pool-utilization-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  lookback: {default: 720, type: int, desc: "bars of utilization history for the percentile"}
  high_pct: {default: 0.9, type: float, desc: "utilization percentile treated as crowded"}
presets: {}
---
# Perp Borrow-Rate / Utilization Extremes

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #31.

## Equation
```
utilization    = custody.assets.locked / custody.assets.owned
hourlyBorrowRate = max_hourly_rate * utilization        # NOT a funding rate
signal: fade positioning when utilization sits in its top decile
```

## Why this card matters more than its neighbours
**On most venues funding is a signed transfer whose extremes mark crowded positioning.
On Jupiter specifically there is no funding rate — there is a borrow fee**, charged on
notional to **both** sides and floor-bounded at zero. So the familiar "funding is deeply
negative, shorts are crowded" signal **does not exist here**. The equivalent information
lives in **utilization**, the one input that drives the rate.

This matters beyond signals: `backtester/core/perps.py` already models the borrow fee
and takes utilization as a *constant input*, and `backtester/README.md` records that
governance has documented SOL utilization sitting at 100% for sustained periods, which
more than doubles borrow cost against the 0.5 default. Utilization history would
therefore improve **every leveraged backtest in this repo**, not just this signal.

## What implementing it would take
A fetcher that archives custody-account utilization over time. It is read from on-chain
perps accounts, so it needs an RPC and a schedule — nobody publishes the history.

## Caveats
- Utilization is a *pool* state, not a directional positioning measure. Inferring
  crowding from it is an extra assumption, not a reading.
- Highest-ranked spec-only signal in `RANKED_LISTS.md`, which reflects plausibility and
  usefulness, not evidence.

## Likelihood of success: low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

The highest-ranked spec-only signal in `RANKED_LISTS.md`, and the reasoning is
Jupiter-specific: there is **no funding rate** on this venue, only a borrow fee
charged to both sides, so the familiar crowded-positioning signal does not exist and
**utilization** is the equivalent input.

Rated low rather than moderate for two reasons. Utilization is a *pool* state, not a
directional positioning measure, so reading crowding from it is an extra assumption.
And nobody publishes the history — it must be archived prospectively from on-chain
custody accounts, which means the earliest possible test is months away.

Worth noting separately: utilization history would improve **every leveraged backtest
in this repo**, because `core/perps.py` currently takes it as a constant.

## Data gap
**No borrow-rate or utilization history is fetched or archived anywhere in this repo.**
