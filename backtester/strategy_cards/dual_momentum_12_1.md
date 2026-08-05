---
id: dual_momentum_12_1
name: Dual Momentum (12-1)
kind: exposure-strategy
status: measured
family: momentum
summary: Trailing formation-window return excluding the most recent bars, to skip short-term reversal.
registry_key: dual_momentum
runner: backtester.cli
warmup_bars: 13
evaluation: cpcv-8-groups-k2
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  formation: {default: 12, type: int, desc: "formation window in bars"}
  skip: {default: 1, type: int, desc: "most recent bars excluded from the return"}
presets:
  short: {formation: 24, skip: 2}
  medium: {formation: 12, skip: 1}
  long: {formation: 24, skip: 1}
---
# Dual Momentum (12-1)

> **Implemented in this session** from spec-only mechanism #18 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
## What it is
Long when the return from `t-formation` to `t-skip` is positive. The skip is the
whole point: the most recent period tends to *reverse*, so including it dilutes the
signal.

## Equation
```
R_t = c_{t-skip} / c_{t-formation} - 1
target_t = 1 if R_t > 0 else 0
```

## Implementation
`backtester/core/strategies/advanced.py::DualMomentum`. The skipped tail is excluded
from **both** ends of the return, so this is genuinely a 12-1 measurement rather than
a shifted full-window one — there is a test that fails if the skip stops binding.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +776.5% | 1.176 | — |
| **Out-of-sample** | **-65.3%** | **-1.303** | **37** |

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

The 12-1 construction is well documented, and it did **not** help: -65.3% and a
-1.303 Sharpe out-of-sample, slightly worse than `ts_momentum` at the medium horizon
(-51.1%). Skipping a bar cannot supply what single-asset momentum is missing, which
is the cross-sectional ranking that carries most of the published edge. On 37 trades
this clears the evidence floor, so it is a real result rather than an anecdote — and
the real result is that it lost.

## Re-evaluated under CPCV

`research/results/cpcv_results.csv`, 8 groups, k=2, 28 paths, all 25 registered configurations.

| Horizon | Median path Sharpe | Paths positive | Median path return | Trades | Rank |
|---|---|---|---|---|---|
| short | −4.633 | 0% | −39.2% | 728 | **25 of 25 — last** |
| medium | −0.319 | 43% | −37.2% | 212 | 23 of 25 |
| long | +0.358 | 57% | +5.5% | 156 | 9 of 25 |

**As a single strategy this is weak and the rating stands.** Zero of 28 paths positive at the short
horizon is the worst result in the study.

### The exception, which matters more than the row above

Paired with `vol_regime` in `all` mode at the long horizon, this is **the single best configuration
measured anywhere in this project**: median path Sharpe **+1.345**, **87%** of 28 paths positive,
median path return **+75.1%** over 52 trades (`research/results/cpcv_combos_results.csv`). It
survives ±10% perturbation on every parameter — **12 variants, 0 sign flips**, median never below
+0.904 (`research/perturb.py --horizon long --pair dual_momentum vol_regime --mode all`).

Both components are mediocre alone at that horizon (+0.358 here, +0.696 for `vol_regime`) and strong
together, which is the complementarity the pairing was chosen for: dual momentum states a direction,
the volatility regime states whether to act on it.

**This does not raise the rating of this card.** The pair sits atop a 295-configuration search whose
PBO is 0.650; a robust-under-perturbation row at the top of an anti-informative ranking is still a
row selected by an anti-informative ranking. The pair is documented here so the single's poor
standing is not mistaken for the mechanism being useless in combination.

## Caveats and limitations
- Momentum-crash risk survives the skip intact.
- Tested at one formation length. The window is the parameter that matters most and
  tuning it on this data would be the exact error `research/STRATEGIES.md` warns about.

## How to run
```bash
python3 -m backtester.cli --strategy dual_momentum --interval 1d
```
