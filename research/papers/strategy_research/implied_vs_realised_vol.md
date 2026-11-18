---
id: implied_vs_realised_vol
name: Implied-vs-Realised Volatility Spread
kind: exposure-strategy
status: spec-only
family: volatility
summary: Harvest the variance risk premium when implied minus realised volatility is historically wide.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [options-implied-volatility]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  lookback: {default: 250, type: int, desc: "bars of IV-RV history for the percentile"}
  entry_pct: {default: 0.8, type: float, desc: "IV-RV percentile above which to sell volatility"}
presets: {}
---
# Implied-vs-Realised Volatility Spread

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #27.

## Equation
```
spread_t = IV_t - RV_t
sell volatility when spread_t is above its own high percentile
```

## Why it might work
The variance risk premium is one of the more robust documented premia: implied
volatility exceeds subsequent realised volatility on average, because someone is paying
for insurance.

## What implementing it would take
An options surface. There is no such feed here, and the harness has no options
instrument model — this is not a strategy addition, it is a new asset class.

## Caveats
Selling volatility is short a fat left tail. The premium is compensation for exactly the
risk that a backtest of a calm period will not show.

## Likelihood of success: low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

The variance risk premium is among the more robust documented premia, so the
mechanism is not speculative. Everything else is: there is no SOL options surface
available here, this harness has no options instrument model, and selling volatility
is short a fat left tail that a calm-period backtest will not show. Rated on the
premium's reputation, discounted for being unbuildable and dangerous.

## Data gap
**No options surface for SOL.**
