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
success_likelihood: low
success_basis: a-priori
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

## Likelihood of success: low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

One of the few genuine *arbitrages* here rather than a forecast, which is why it
clears very-low despite being unbuildable. But it is a latency business measured in
milliseconds, and this harness is bar-resolution by design — a bar-resolution
backtest of it would be a fiction. It also needs MEV-aware execution modelling before
any number would mean anything.

## Data gap
**No DEX quote history, and no execution model for MEV-aware routing.**
