---
id: mvrv_nupl_valuation
name: MVRV / NUPL On-Chain Valuation
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: Market value against realised value as a cycle-position gauge.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [on-chain-cost-basis]
data_available: false
params:
  high_pct: {default: 0.9, type: float, desc: "MVRV percentile treated as expensive"}
  low_pct: {default: 0.1, type: float, desc: "MVRV percentile treated as cheap"}
presets: {}
---
# MVRV / NUPL On-Chain Valuation

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #38.

## Equation
```
MVRV = market_cap / realised_cap      # realised cap values each coin at its last move
NUPL = (market_cap - realised_cap) / market_cap
```

## Why it might work
It is a cycle-position gauge rather than a timing signal, and cycle position is exactly
what every card here is blind to.

## What implementing it would take
Per-coin cost-basis reconstruction from chain history. Heavy indexing.

## Caveats
Realised cap is a construct with debatable definitions, and it behaves differently on a
high-throughput chain with cheap transfers than on Bitcoin, where these metrics were
developed.

## Data gap
**No on-chain cost-basis data.**
