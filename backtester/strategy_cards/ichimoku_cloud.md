---
id: ichimoku_cloud
name: Ichimoku Cloud
kind: exposure-strategy
status: spec-only
family: trend
summary: Multi-component trend and support system. The displaced cloud is a lookahead trap.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  tenkan: {default: 9, type: int, desc: "conversion-line period"}
  kijun: {default: 26, type: int, desc: "base-line period"}
  senkou_b: {default: 52, type: int, desc: "leading span B period"}
  displacement: {default: 26, type: int, desc: "bars the cloud is plotted forward"}
presets: {}
---
# Ichimoku Cloud

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #21.

## Equation
```
Tenkan_t  = (max(H, 9) + min(L, 9)) / 2
Kijun_t   = (max(H, 26) + min(L, 26)) / 2
SenkouA_t = (Tenkan_t + Kijun_t)/2      plotted 26 bars FORWARD
SenkouB_t = (max(H,52) + min(L,52))/2   plotted 26 bars FORWARD
```

## Why it might work
Mechanically it is a bundle of moving-average crossovers plus a displaced channel, which
gives several confirmations from one indicator set.

## Data gap
**None — implementable now.**

## The trap that makes this worth a card of its own
**The cloud is plotted forward and must never be read as a current signal.** The
displacement means `SenkouA` drawn at bar *t+26* was computed at bar *t*; a careless
implementation reads the value drawn *at* the current bar, which was computed from
26 bars in the future. That is textbook lookahead, and this harness would catch it only
if the implementation reached through `BarWindow` — which it cannot, so the error would
instead show up as an index error or a silently shifted series. Implement it by
computing at *t* and comparing against price at *t+displacement*, never the reverse.

## Caveats
Six parameters and heavy component overlap. Attribution between the components would
need separate tests to mean anything.
