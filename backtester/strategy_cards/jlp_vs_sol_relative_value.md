---
id: jlp_vs_sol_relative_value
name: JLP-vs-SOL Relative Value
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: JLP realises roughly 0.42-0.53x SOL's short-horizon volatility. Trading the ratio is a dampened SOL expression.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [jlp-price-history]
data_available: false
params:
  window: {default: 168, type: int, desc: "window for the ratio's z-score"}
  entry_z: {default: 2.0, type: float, desc: "ratio z-score at which to act"}
presets: {}
---
# JLP-vs-SOL Relative Value

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #37.

## Equation
```
ratio_t = P_JLP / P_SOL
trade the ratio's deviation from its trailing mean
```

## Why it might work
JLP is roughly 68% crypto by composition and realises about **0.42–0.53x SOL's
short-horizon volatility**. That makes the pair mechanically related with a stable-ish
beta, which is a better cointegration candidate than two unrelated tokens — and it is
the one peer series that is *specific to this venue*.

## What implementing it would take
A JLP price series, which Jupiter's own Price API can supply for the JLP mint
(`27G8MtK7...`, 6 decimals — recorded in
`docs/trading-signals-concept-family.md`). This is the **cheapest peer series to
obtain** of any card in this tier, which makes it the most actionable blocked item.

## Caveats
JLP accrues fees, so its price has a drift component that is not a market view. Treating
the ratio as purely mean-reverting would fight that drift. JLP also holds SOL, so the
two are not independent — the "hedge" is partly a hedge against itself.

## Data gap
**No JLP price history fetched.**
