---
id: dex_cex_dislocation
name: DEX-vs-CEX Price Dislocation
kind: exposure-strategy
status: spec-only
family: microstructure
summary: Cross-venue basis as both a signal and an arbitrage.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [dex-quote-history, cex-quote-history]
data_available: false
params:
  threshold_bps: {default: 30.0, type: float, desc: "dislocation in bps required to act"}
presets: {}
---
# DEX-vs-CEX Price Dislocation

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #36.

## Equation
```
basis_t = (P_dex - P_cex) / P_cex
act when |basis_t| exceeds threshold plus round-trip cost
```

## Why it might work
It is one of the few edges here that is a genuine arbitrage rather than a forecast.

## What implementing it would take
Synchronised quote history from both venue types, and — critically — **MEV-aware
execution modelling**. `docs/trading-signals-concept-family.md` covers the relevant
machinery: private RPC, Jito bundles, and the sandwich exposure a naive public-mempool
arb walks into.

## Caveats
This is a latency business. A bar-resolution backtest of an arbitrage that lives in
milliseconds would be a fiction, and this harness is bar-resolution by design.

## Data gap
**No DEX quote history, and no execution model for MEV-aware routing.**
