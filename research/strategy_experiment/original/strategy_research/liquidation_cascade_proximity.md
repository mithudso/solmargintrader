---
id: liquidation_cascade_proximity
name: Liquidation-Cascade Proximity
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: Estimate clustered liquidation levels, then fade or follow the cascade.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [open-interest-history, position-distribution]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  cluster_bps: {default: 200.0, type: float, desc: "width of a liquidation cluster in bps"}
presets: {}
---
# Liquidation-Cascade Proximity

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #33.

## Equation
```
estimate liquidation prices from position size, collateral and leverage distribution
proximity_t = distance from price to the nearest large cluster
```

## Why it might work
Cascades are mechanical: forced selling begets forced selling. Knowing where the fuel
sits is genuinely informative.

## What implementing it would take
Position-level data. On Jupiter that means decoding perps position accounts across all
holders — expensive, and the distribution changes continuously.

## Caveats
This is the most crowded trade in crypto analytics; everyone with the data is looking at
the same levels. Also note `backtester/core/perps.py` shows liquidation price **drifts
toward spot as borrow fees accrue**, so a static cluster estimate decays.

## Likelihood of success: very-low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

The mechanism is real — forced selling begets forced selling — but this is the most
crowded trade in crypto analytics: everyone with the data is looking at the same
levels. It also needs position-level data across all holders, and
`core/perps.py` shows liquidation prices **drift toward spot as borrow fees
accrue**, so a static cluster estimate decays as soon as it is built.

## Data gap
**No open-interest or position-distribution data.**
