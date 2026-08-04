---
id: hurst_regime_test
name: Variance-Ratio / Hurst Exponent Regime Test
kind: exposure-strategy
status: spec-only
family: regime-filter
summary: A meta-signal that selects WHICH family to run. The highest-value unimplemented item in this tier.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
params:
  window: {default: 250, type: int, desc: "bars used to estimate H"}
  trend_threshold: {default: 0.55, type: float, desc: "H above this selects the trend family"}
  revert_threshold: {default: 0.45, type: float, desc: "H below this selects the reversion family"}
presets: {}
---
# Variance-Ratio / Hurst Exponent Regime Test

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #25.

## Equation
```
H < 0.5  -> mean-reverting
H = 0.5  -> random walk
H > 0.5  -> trending
(equivalently, a variance ratio test: Var(k-period returns) / (k * Var(1-period returns)))
```

## Why this is the most valuable card in this tier
**The entire measured sweep shows trend and reversion inverting between regimes.** Every
Tier-1 card is a bet on one of those two behaviours being present, and none of them
checks which one is actually present. A meta-signal that answers "which family should be
running right now" addresses the failure that dominates all sixteen measured results,
rather than adding a seventeenth directional opinion.

It is also the natural companion to the CPCV finding that in-sample rank does not
predict out-of-sample rank: if rank inverts with regime, then knowing the regime is
worth more than knowing the rank.

## Data gap
**None — implementable now.** Close series only.

## What implementing it would take
A variance-ratio estimator (simpler and better-behaved than rescaled-range Hurst), then
a selector that routes to an existing strategy. `Composite` supports combining, not
switching, so the selector would be a small new strategy class holding two child
strategies and delegating to one.

## Caveats
- Estimating H on a short window is noisy, and the estimate is itself regime-dependent —
  the snake eats its tail.
- Rescaled-range Hurst is biased on short samples; prefer the variance-ratio form and
  report a confidence interval.
- A regime *selector* multiplies the strategy space, which multiplies the
  multiple-testing problem. It should be evaluated under CPCV, not a single split.
