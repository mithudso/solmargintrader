---
id: ou_half_life_sizing
name: Ornstein-Uhlenbeck Half-Life Hold Cap
kind: exposure-strategy
status: spec-only
family: mean-reversion
summary: Fit a mean-reverting process, derive its half-life, and cap holds at 2-3x it. The missing piece in both reversion cards.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  fit_window: {default: 250, type: int, desc: "bars used to fit theta"}
  hold_multiple: {default: 2.5, type: float, desc: "cap the hold at this multiple of the half-life"}
  max_half_life_bars: {default: 30, type: int, desc: "above this, treat the series as not mean-reverting"}
presets: {}
---
# Ornstein-Uhlenbeck Half-Life Hold Cap

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #23.

## Equation
```
dX = theta*(mu - X)dt + sigma*dW
half_life = ln(2) / theta
exit unconditionally after hold_multiple * half_life bars
if half_life > max_half_life_bars: do not trade this series at all
```

## Why it might work
**This is the named gap in both `bb_reversion.md` and `zscore.md`: neither has a hold
cap.** A mean-reversion trade whose thesis has not played out within a few half-lives is
no longer the trade that was entered; it is an unbounded bet that the mean will come
back. The half-life supplies a principled exit that does not depend on the signal
recovering.

It also supplies a *screening* rule: a half-life beyond 30 days means the series is not
mean-reverting in any tradeable sense, which would have disqualified raw SOL price
before either reversion card was run.

## Data gap
**None — implementable now.** Fitting theta needs only the close series (OLS on the
lagged difference, or the discrete AR(1) estimate).

## What implementing it would take
An estimator in `indicators.py`, plus a hold-counter in the two reversion strategies.
The engine already supports stateful strategies (`rsi.py` holds between signals).

## Caveats
Theta estimated on a trending series is meaningless, which is the point of the
screening rule — but it means the fit window choice is load-bearing, not cosmetic.
