---
id: open_interest_divergence
name: Open-Interest Divergence
kind: exposure-strategy
status: spec-only
family: crypto-native
summary: Open interest rising while price is flat marks leverage build-up and liquidation risk.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [open-interest-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  window: {default: 72, type: int, desc: "bars over which to compare OI and price change"}
presets: {}
---
# Open-Interest Divergence

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #32.

## Equation
```
divergence_t = pct_change(OI, window) - |pct_change(price, window)|
high divergence => leverage accumulating without price progress
```

## Why it might work
Leverage build-up without price movement is a well-documented precursor to violent
resolution, in either direction.

## What implementing it would take
An OI time series. Same collection problem as utilization: it must be archived
prospectively.

## Caveats
Direction-agnostic. It forecasts *volatility*, not sign, which makes it a sizing input
rather than an entry rule.

## Likelihood of success: low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

Leverage building without price progress is a documented precursor to violent
resolution, and that is a real mechanism. But it is **direction-agnostic** — it
forecasts volatility, not sign — which makes it a sizing input rather than an entry
rule, and this harness has no OI history to test it against.

## Data gap
**No open-interest history.**
