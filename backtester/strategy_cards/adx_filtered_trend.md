---
id: adx_filtered_trend
name: ADX-Filtered Trend
kind: exposure-strategy
status: spec-only
family: regime-filter
summary: Gate a trend signal on Wilder's ADX, so it only trades when trend strength is present.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  adx_period: {default: 14, type: int, desc: "Wilder ADX period"}
  adx_threshold: {default: 25.0, type: float, desc: "ADX level above which the market counts as trending"}
presets: {}
---
# ADX-Filtered Trend

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #20.

## Equation
```
+DM_t = H_t - H_{t-1}  if positive and > (L_{t-1} - L_t), else 0
-DM_t = L_{t-1} - L_t  if positive and > (H_t - H_{t-1}), else 0
+DI = 100 * WilderSmooth(+DM)/ATR ;  -DI = 100 * WilderSmooth(-DM)/ATR
DX  = 100 * |+DI - -DI| / (+DI + -DI)
ADX = WilderSmooth(DX)
trade the trend signal only while ADX > threshold
```

## Why it might work
Every trend card here fails the same way: chop. ADX is the conventional measure of
whether a trend exists at all, so it targets the failure mode directly rather than
adding another directional opinion.

## Data gap
**None — implementable now.** High, low and close are all available.

## What implementing it would take
Wilder smoothing already exists in `indicators.py` for ATR and RSI. The work is the
directional-movement pair, then a composite that ANDs it with an existing trend card.
`Composite` in `core/strategies/composite.py` already supports that shape.

## Caveats
ADX > 25 is a convention, not a constant of nature; it is a parameter and should be
swept. ADX is also lagging by construction, so it can confirm a trend that is ending.
