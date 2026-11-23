---
id: ma_ribbon
name: Moving-Average Ribbon
kind: exposure-strategy
status: measured
family: trend
summary: Exposure scales with the fraction of adjacent MA pairs in correct order.
registry_key: ma_ribbon
runner: backtester.cli
warmup_bars: 50
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  windows: {default: 5, type: int, desc: "number of MAs in the ribbon"}
  base: {default: 10, type: int, desc: "shortest MA window; the rest are multiples of it"}
presets:
  short: {windows: 5, base: 6}
  medium: {windows: 5, base: 10}
  long: {windows: 5, base: 20}
---
# Moving-Average Ribbon

> **Implemented in this session** from spec-only mechanism #19 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
## What it is
Several SMAs at once; exposure is the fraction of adjacent pairs in the correct
order. A graded version of `ma_crossover.md`.

## Equation
```
spans    = [base, 2*base, ..., windows*base]
target_t = (# adjacent pairs where SMA(shorter) > SMA(longer)) / (windows - 1)
```

## Implementation
`backtester/core/strategies/advanced.py::MaRibbon`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +452.0% | 1.119 | — |
| **Out-of-sample** | **-54.0%** | **-1.242** | **160** |

For reference on the same split: buy-and-hold made **+565.2% (Sharpe 1.030)**
in-sample and **-70.8% (Sharpe -0.651)** out. That row reproduces the figure the
existing cards document exactly, which is how these new numbers are known to be
comparable to them.


The figures below come from a **single 70/30 walk-forward split**, and
`research/RANKED_LISTS.md` documents why that split is structurally hostile: its
in-sample window ends within one bar of the highest close in the entire series
($261.99 on bar 1311 of 1875). It separated a bull market from a bear leg almost
exactly, so any long-biased rule *had* to look excellent in-sample and terrible
out-of-sample. In-sample rank did not predict out-of-sample rank — the medium-horizon
Spearman correlation was **-0.419**, actively inverted.

Read these numbers as evidence about **one regime transition**, not as a performance
estimate. Across the whole sweep, 45 of 311 rankable configurations (14%) had a
positive out-of-sample Sharpe and 28 (9%) made money. The evidence floor is 10
out-of-sample trades: fewer than that and a row is listed, never ranked.

## Likelihood of success: very-low

*Basis: measured-oos.*

The card written before implementation called this "the weakest candidate in this
tier — more knobs on a mechanism already measured as regime-dependent is not
progress." The measurement agrees: **-54.0% on 160 trades**, worse than
`ma_crossover` at the same horizon (-52.3%), with 23x the trade count.

Grading the exposure did smooth the whipsaw — 160 trades against a binary rule's 7
means it was rarely fully in or out — but smoothing the entry to a losing signal
produces a smoother loss. There is no mechanism here that `ma_crossover` lacks.

## Caveats and limitations
- 160 trades at 8 bps round trip is roughly 1.3% of notional in costs.
- Two parameters that jointly determine five windows, none of them swept.

## How to run
```bash
python3 -m backtester.cli --strategy ma_ribbon --interval 1d
```
