---
id: exchange_net_flow
name: Exchange Net-Flow / Stablecoin Flow
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: Stablecoins moving onto exchanges as a proxy for incoming buying power.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [on-chain-flows]
data_available: false
params:
  window: {default: 168, type: int, desc: "bars over which to sum net flow"}
presets: {}
---
# Exchange Net-Flow / Stablecoin Flow

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #34.

## Equation
```
net_flow_t = inflow_t - outflow_t   (stablecoins to exchange wallets)
```

## Why it might work
It is a direct measure of dry powder arriving, rather than an inference from price.

## What implementing it would take
Labelled exchange wallet sets plus an indexer. Wallet labelling is the hard part and it
is never complete.

## Caveats
Attribution is unreliable — internal transfers, custody reshuffles and bridge movements
all look like flow. On Solana, much of the interesting activity never touches a
centralised exchange at all.

## Data gap
**No on-chain flow data.**
