---
id: xs_momentum
name: Cross-Sectional Momentum
kind: exposure-strategy
status: spec-only
family: momentum
summary: Rank a universe by trailing return and hold the top decile. Needs peers this repo does not have.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [peer-universe-ohlcv, survivorship-free-constituents]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  formation: {default: 90, type: int, desc: "formation window in bars"}
  top_k: {default: 3, type: int, desc: "number of assets held"}
presets: {}
---
# Cross-Sectional Momentum

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #17.

## Equation
```
R_i = c_{i,t}/c_{i,t-n} - 1     for each asset i
long the top-k by rank, rebalance each period
```

## Why it might work
The most-documented anomaly family there is (Jegadeesh & Titman 1993: 3–12 month
formation, 1-month hold). Critically, **the cross-sectional form is the one the
literature supports**; `ts_momentum.md` is the weaker single-asset cousin.

## What implementing it would take
A multi-asset engine. This harness is single-asset by design — `run_backtest` takes one
`arrays` dict — so this is not a strategy addition, it is an engine change.

## Caveats
Survivorship bias inflates long-only equity backtest returns by an estimated
**1.5–2.0% annually**, and a crypto universe is far worse: the dead tokens are most of
the sample. A universe assembled today from surviving tokens would produce a
spectacular, entirely fictional result.

## Likelihood of success: low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

The **cross-sectional** form is the one the momentum literature actually supports,
which is a real point in its favour — but it needs a multi-asset engine this harness
does not have, and a survivorship-free crypto universe, where the dead tokens are
most of the sample. A universe assembled today from survivors would produce a
spectacular fiction. Rated low rather than moderate because the implementation risk
*is* the main risk: the most likely outcome of building this carelessly is a wrong
number, not a losing one.

## Data gap
**No peer universe fetched. Would also require survivorship-free constituent history.**
