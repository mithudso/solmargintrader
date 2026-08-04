---
id: atr_position_sizing
name: ATR-Normalised Position Sizing
kind: exposure-strategy
status: spec-only
family: risk-overlay
summary: Size so that 1 ATR of adverse move equals a fixed fraction of equity. A risk overlay, not a signal.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  atr_period: {default: 14, type: int, desc: "Wilder ATR period"}
  risk_per_trade: {default: 0.01, type: float, desc: "fraction of equity risked per 1 ATR of adverse move"}
  stop_atr_multiple: {default: 2.0, type: float, desc: "stop distance in ATRs"}
presets: {}
---
# ATR-Normalised Position Sizing

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #28.

## Equation
```
ATR_t    = Wilder smoothing of true range, period p
units    = (risk_per_trade * equity) / (stop_atr_multiple * ATR_t)
target_t = clamp(units * price / equity, 0, 1) * direction_from_some_signal
```

## Why it might work
It normalises *risk* rather than notional, so a fixed rule behaves consistently across
volatility regimes. It is arguably higher value than most entry signals in this
directory, and it is **untested here** — the same gap `voltarget.md` documents from the
other side.

## Data gap
**None — implementable now.** ATR is already in `indicators.py` and used by
`keltner`.

## What implementing it would take
A wrapper strategy that takes a child signal and rescales its exposure. The engine
already accepts continuous exposure in [-1, 1], so no engine change is needed — which is
exactly why not having tested it is a gap rather than a limitation.

## Caveats
- A stop is not modelled by this harness: exposure changes at bar boundaries, so an
  "ATR stop" here means "reduce exposure at the next bar", not "exit intrabar at a
  price". That difference flatters any stop-based system and must be stated whenever
  this is reported.
- Sizing on trailing ATR de-risks after volatility has already arrived.
