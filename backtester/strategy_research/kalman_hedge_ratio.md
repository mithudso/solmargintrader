---
id: kalman_hedge_ratio
name: Kalman-Filtered Dynamic Hedge Ratio
kind: exposure-strategy
status: spec-only
family: mean-reversion
summary: Let the hedge ratio evolve as a state variable instead of fixing it per window.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [peer-price-series]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  process_var: {default: 1e-05, type: float, desc: "state process variance"}
  obs_var: {default: 0.001, type: float, desc: "observation variance"}
presets: {}
---
# Kalman-Filtered Dynamic Hedge Ratio

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #24.

## Equation
```
state:       beta_t = beta_{t-1} + w_t      w ~ N(0, process_var)
observation: X_t    = beta_t * Y_t + v_t    v ~ N(0, obs_var)
```

## Why it might work
Static hedge ratios are documented as unstable, and re-estimating per window produces
jumps at window boundaries. A filter makes the ratio a smoothly evolving estimate, which
is both more honest and less prone to boundary artifacts.

## What implementing it would take
A peer series plus a scalar Kalman filter — perhaps forty lines, no dependency.

## Caveats
Two variance parameters tune how fast beta moves, and they are usually chosen by
eyeballing the result, which is fitting by another name. A filter that adapts quickly
enough will track any relationship, including one that has genuinely broken.

## Likelihood of success: low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

A filtered hedge ratio is a genuine improvement on refitting per window, which jumps
at boundaries. But it inherits every risk of `pairs_cointegration.md` and adds two
variance parameters usually chosen by eyeballing the output — which is fitting by
another name. A filter that adapts fast enough will track any relationship, including
one that has genuinely broken.

## Data gap
**No peer series fetched.**
