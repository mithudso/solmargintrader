---
id: pairs_cointegration
name: Pairs Trading / Cointegration vs ETH or BTC
kind: exposure-strategy
status: spec-only
family: mean-reversion
summary: The rigorous version of zscore: trade a spread whose stationarity has actually been tested.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [peer-price-series]
data_available: false
success_likelihood: moderate
success_basis: a-priori
params:
  entry_z: {default: 2.0, type: float, desc: "spread z-score at which to enter"}
  exit_z: {default: 0.0, type: float, desc: "spread z-score at which to exit"}
  stop_z: {default: 3.0, type: float, desc: "spread z-score at which to stop out"}
  adf_p: {default: 0.05, type: float, desc: "maximum ADF p-value to accept a cointegrating relation"}
presets: {}
---
# Pairs Trading / Cointegration vs ETH or BTC

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #22.

## Equation
```
Engle-Granger two-step:
  1. regress X = beta*Y + eps
  2. ADF-test eps for stationarity; if p < 0.05 a cointegrating relation exists
Spread = X - beta*Y ;  trade its z-score: enter +-2.0, exit toward 0, stop +-3.0
```
Johansen is preferred for three or more assets, being order-invariant.

## Why it might work
**This is what `zscore.md` should have been.** The z-score technique assumes
stationarity; raw SOL price is not stationary, so applying it there is a known
theoretical error. A cointegrated spread is constructed to be stationary and the
assumption is *tested* rather than hoped for.

## What implementing it would take
A second price series and an ADF implementation. The practitioner heuristic is to
require cointegration across 3-, 6- and 12-month rolling windows before trading, which
is a meaningful amount of validation code.

## Caveats
The primary risk is **convergence failure**: the relation breaks and the spread keeps
diverging while both legs are held. Cointegration is a property of a sample, not a
promise about the future.

## Likelihood of success: moderate

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

The only spec card besides `hurst_regime_test` rated moderate, and for a structural
reason: it is what `zscore.md` should have been. The z-score method assumes
stationarity; raw SOL price is not stationary, and a cointegrated spread is
*constructed* to be, with the assumption **tested** rather than hoped for.

The peer series is also the cheapest gap in this tier to close — Coinbase serves
BTC-USD and ETH-USD keyless, the same source as the SOL data already here. Held to
moderate rather than higher by convergence risk: the relation breaks and the spread
keeps diverging while both legs are held, which is the documented way this strategy
loses badly rather than slightly.

## Data gap
**No peer price series fetched.**
