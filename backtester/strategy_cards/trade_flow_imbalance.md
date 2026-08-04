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

## Data gap
**No trade prints (tick data).**
