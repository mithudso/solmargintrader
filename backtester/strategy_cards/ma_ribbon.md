---
id: ma_ribbon
name: Moving-Average Ribbon
kind: exposure-strategy
status: spec-only
family: trend
summary: Several MAs at once; exposure scales with the fraction in correct order.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  windows: {default: 5, type: int, desc: "number of MAs in the ribbon"}
  base: {default: 10, type: int, desc: "shortest MA window; the rest are multiples"}
presets: {}
---
# Moving-Average Ribbon

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #19.

## Equation
```
target_t = (# adjacent pairs where SMA(short) > SMA(long)) / (windows - 1)
```

## Why it might work
It converts a binary crossover into a graded exposure, which reduces the all-or-nothing
whipsaw of `ma_crossover.md`.

## Data gap
**None — implementable now.**

## What implementing it would take
A loop over windows in `on_bar`. Trivial.

## Caveats
**Low marginal information.** This is a variant of `ma_crossover.md` with more
parameters and the same underlying idea. It is listed for completeness, and it is
honestly the weakest candidate in this tier: more knobs on a mechanism already measured
as regime-dependent is not progress.
