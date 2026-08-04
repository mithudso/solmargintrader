---
id: staking_ratio_flow
name: Staking-Ratio / Validator Flow
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: SOL-specific float dynamics: a rising staked fraction reduces liquid supply.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [on-chain-staking-data]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  window: {default: 720, type: int, desc: "bars over which to measure the change in staked fraction"}
presets: {}
---
# Staking-Ratio / Validator Flow

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #35.

## Equation
```
staked_fraction_t = total_staked / circulating_supply
signal on the change, not the level
```

## Why it might work
It is one of the few genuinely SOL-specific supply measures, and unlike most on-chain
metrics it is unambiguous — stake is stake.

## What implementing it would take
Epoch-level stake account aggregation. Slow-moving, so daily granularity suffices.

## Caveats
Very slow signal — epochs are ~2–3 days — so it can inform position size or a regime
view, but never entry timing. Liquid-staking tokens (jupSOL, jitoSOL, mSOL) blur the
"reduces liquid supply" logic considerably, since staked SOL becomes tradeable again.

## Likelihood of success: very-low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

One of the few unambiguous SOL-specific supply measures — stake is stake — but
epochs are 2-3 days, so it can inform position size at best and never entry timing.
Liquid-staking tokens (jupSOL, jitoSOL, mSOL) also badly blur the "reduces liquid
supply" logic, since staked SOL becomes tradeable again.

## Data gap
**No on-chain staking data.**
