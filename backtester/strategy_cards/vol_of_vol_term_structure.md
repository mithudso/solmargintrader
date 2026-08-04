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

## Data gap
**No options surface for SOL.**
