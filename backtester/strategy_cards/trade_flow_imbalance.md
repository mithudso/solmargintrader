---
id: trade_flow_imbalance
name: Trade-Flow Imbalance / Aggressor Ratio
kind: exposure-strategy
status: spec-only
family: microstructure
summary: Signed trade prints. Naive flow-following is systematically picked off.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [tick-trade-prints]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  window: {default: 100, type: int, desc: "trades over which to accumulate signed flow"}
presets: {}
---
# Trade-Flow Imbalance / Aggressor Ratio

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #40.

## Equation
```
flow_t = sum(sign(aggressor) * size) over the last n trades
```

## Why it might work
It measures who is *demanding* liquidity, which is more informative than price alone.

## What implementing it would take
Tick data with aggressor labelling.

## Caveats
**Kyle and Glosten-Milgrom adverse-selection dynamics mean naive flow-following is
systematically picked off.** The informed trader's flow looks identical to the
uninformed trader's until after the fact. This is not an implementation difficulty, it
is an adverse-selection problem that survives any amount of engineering.

## Likelihood of success: very-low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

Measuring who *demands* liquidity is more informative than price alone. But
Kyle and Glosten-Milgrom adverse-selection dynamics mean naive flow-following is
systematically picked off: the informed trader's flow looks identical to the
uninformed trader's until after the fact. That is not an engineering difficulty — it
survives any amount of engineering.

## Data gap
**No trade prints (tick data).**
