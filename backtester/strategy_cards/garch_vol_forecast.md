---
id: garch_vol_forecast
name: GARCH(1,1) Volatility Forecast
kind: exposure-strategy
status: spec-only
family: risk-overlay
summary: Feed vol targeting with a forecast instead of a trailing estimate.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  omega: {default: 1e-06, type: float, desc: "long-run variance constant"}
  alpha: {default: 0.1, type: float, desc: "weight on the last squared shock"}
  beta: {default: 0.85, type: float, desc: "weight on the last variance estimate"}
presets: {}
---
# GARCH(1,1) Volatility Forecast

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #29.

## Equation
```
sigma2_t = omega + alpha * eps2_{t-1} + beta * sigma2_{t-1}
```
with `alpha + beta < 1` for stationarity; the pair together sets persistence.

## Why it might work
`voltarget.md` reacts with a lag equal to its vol window. A forecast that anticipates
clustering rather than measuring it after the fact removes part of that lag, which is
the mechanism's main weakness.

## Data gap
**None — implementable now.** Returns only.

## What implementing it would take
Either maximum-likelihood fitting (needs an optimiser) or accepting **fixed
RiskMetrics-style parameters** — `alpha=0.06, beta=0.94` is the classic EWMA
special case and needs no fitting at all. Start there; it is a one-line change to the
existing vol estimate.

## Caveats
- Fitted GARCH parameters are unstable on short samples, and refitting each bar is both
  slow and a source of lookahead if done carelessly.
- A variance forecast is not a return forecast. This changes sizing, never direction.
