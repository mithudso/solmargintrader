---
id: vol_regime_hmm
name: Volatility-Regime HMM
kind: exposure-strategy
status: spec-only
family: regime-filter
summary: A two- or three-state hidden Markov model on realised volatility, switching the active family.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  states: {default: 2, type: int, desc: "number of hidden states"}
  vol_window: {default: 20, type: int, desc: "realised-volatility window"}
  fit_window: {default: 500, type: int, desc: "bars used to fit the model"}
presets: {}
---
# Volatility-Regime HMM

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #26.

## Equation
```
observed:  sigma_t = stdev(log returns, vol_window)
latent:    s_t in {calm, stressed[, crisis]} with transition matrix A
switch the active strategy family on argmax P(s_t | observations <= t)
```

## Why it might work
Volatility clusters, so a state model has something real to find. It attacks the same
problem as `hurst_regime_test.md` from a different direction — one estimates a memory
exponent, the other a latent state.

## Data gap
**None — implementable now**, though fitting an HMM without a dependency means writing
Baum-Welch by hand or accepting a simpler two-state threshold model.

## What implementing it would take
Honestly: either a new dependency (`hmmlearn`/`statsmodels`) which the requirements file
deliberately resists, or a hand-rolled EM. A **thresholded volatility-tercile model**
captures most of the benefit for a fraction of the machinery and should be tried first.

## Caveats
- The filtered state estimate must use only data through *t*. A smoothed
  (Viterbi-over-the-whole-sample) state is a lookahead violation that would look like a
  spectacular result.
- More states means more parameters fitted on the same series.
