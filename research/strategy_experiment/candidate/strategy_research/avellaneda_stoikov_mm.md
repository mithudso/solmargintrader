---
id: avellaneda_stoikov_mm
name: Avellaneda-Stoikov Market Making
kind: exposure-strategy
status: spec-only
family: microstructure
summary: Optimal quotes around a reservation price with an inventory penalty. Wrong shape for this harness.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [l2-order-book, maker-rebate-venue]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  gamma: {default: 0.1, type: float, desc: "inventory risk aversion"}
  kappa: {default: 1.5, type: float, desc: "order-arrival intensity parameter"}
presets: {}
---
# Avellaneda-Stoikov Market Making

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #41.

## Equation
```
reservation_price = mid - q * gamma * sigma^2 * (T - t)
half_spread       = gamma * sigma^2 * (T-t) + (2/gamma) * ln(1 + gamma/kappa)
```
where `q` is current inventory.

## Why it might work
It is the canonical solution to the market maker's inventory problem and it is *derived*
rather than fitted.

## What implementing it would take
More than data: **a different harness.** This is an execution strategy that earns the
spread, so it needs a quoting simulator with queue position and fill probability. This
backtester takes positions at bar prices; the shapes do not match.

## Caveats
Listed to close out the microstructure family honestly. It is the one card here where
the right answer is "this repo is the wrong tool", not "fetch more data".

## Likelihood of success: very-low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

Derived rather than fitted, which is rare and good. But it earns the *spread*, so it
needs a quoting simulator with queue position and fill probability, plus a venue with
maker rebates. This backtester takes positions at bar prices. The right answer for
this card is "this repo is the wrong tool", not "fetch more data".

## Data gap
**Needs L2 plus a venue with maker rebates; and it is fundamentally an execution strategy, not a directional signal.**
