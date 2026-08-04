---
id: dual_momentum_12_1
name: Dual Momentum (12-1)
kind: exposure-strategy
status: spec-only
family: momentum
summary: Trailing 12-period return excluding the most recent period, to skip short-term reversal.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  formation: {default: 12, type: int, desc: "formation window in periods"}
  skip: {default: 1, type: int, desc: "most recent periods to exclude"}
presets: {}
---
# Dual Momentum (12-1)

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #18.

## Equation
```
R_t = c_{t-skip} / c_{t-formation} - 1
target_t = 1 if R_t > 0 else 0
```

## Why it might work
The 12-1 construction is standard in the momentum literature precisely because the most
recent period tends to *reverse*, so including it dilutes the signal. This is the
cheapest available upgrade to `ts_momentum.md`.

## Data gap
**None — implementable now.** Needs code, not data.

## What implementing it would take
A near-copy of `TsMomentum` with a `skip` offset applied to the numerator. Roughly ten
lines plus a test that the skip window is actually excluded.

## Caveats
Single-asset momentum remains the weak form of the anomaly; skipping a period does not
supply the cross-sectional ranking that carries most of the published edge.
