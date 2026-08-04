---
id: vol_of_vol_term_structure
name: Volatility-of-Volatility / Vol Term Structure
kind: exposure-strategy
status: spec-only
family: volatility
summary: Trade the shape and instability of the volatility surface.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [options-implied-volatility, term-structure]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  front: {default: 7, type: int, desc: "near tenor in days"}
  back: {default: 30, type: int, desc: "far tenor in days"}
presets: {}
---
# Volatility-of-Volatility / Vol Term Structure

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #30.

## Equation
```
slope_t = IV(back)_t - IV(front)_t      # contango vs backwardation
vol_of_vol_t = stdev(IV changes)
```

## Why it might work
Term-structure shape carries positioning and stress information that spot volatility
does not.

## What implementing it would take
A full surface across tenors, plus an options pricing and position model. The furthest
of any card here from what this repo can do.

## Caveats
Listed for completeness of the taxonomy rather than as a candidate.

## Likelihood of success: very-low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

Listed to close out the volatility family honestly. It needs a full surface across
tenors plus an options pricing and position model — the furthest of any card here
from what this repo can do — and there is no evidence base to rate the mechanism on
for SOL specifically.

## Data gap
**No options surface for SOL.**
