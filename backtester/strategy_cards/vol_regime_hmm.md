---
id: vol_regime_hmm
name: Volatility-Regime Switch (tercile, not HMM)
kind: exposure-strategy
status: measured
family: regime-filter
summary: Trend-follow in calm volatility, stand aside when volatility is elevated.
registry_key: vol_regime
runner: backtester.cli
warmup_bars: 251
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  vol_window: {default: 20, type: int, desc: "realised-volatility window"}
  lookback: {default: 250, type: int, desc: "bars of vol history for the quantile"}
  calm_quantile: {default: 0.5, type: float, desc: "vol quantile below which the regime counts as calm"}
  trend_window: {default: 100, type: int, desc: "SMA window for the trend rule"}
presets: {}
---
# Volatility-Regime Switch (tercile, not HMM)

> **Implemented in this session** from spec-only mechanism #26 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
# Volatility-Regime Switch

## What it is
Classify the current realised volatility against its own trailing distribution;
trend-follow when calm, hold nothing when elevated.

## Why this is a tercile and not a hidden Markov model
The original spec proposed a two-or-three-state HMM. That needs either a new
dependency — which `requirements.txt` deliberately resists — or a hand-rolled
Baum-Welch, and a **volatility quantile captures most of the benefit for a fraction
of the machinery**. The latent-state version remains genuinely open; this is the
cheap approximation of it, and the name says so.

## Equation
```
sigma_t = stdev(log returns, vol_window) * sqrt(periods_per_year)
cutoff  = quantile(trailing sigma distribution, calm_quantile)
target_t = (1 if c_t > SMA(trend_window) else 0)  if sigma_t <= cutoff  else 0
```

The distribution is rebuilt each bar from visible bars only. **A smoothed
whole-sample state estimate would be a look-ahead violation that looked like a
spectacular result** — that is the specific trap in any regime model.

## Implementation
`backtester/core/strategies/advanced.py::VolRegimeSwitch`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | -58.5% | -0.495 | — |
| **Out-of-sample** | **-21.2%** | **-0.377** | **15** |

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

**The only mechanism here that lost money in-sample as well as out** (-58.5% IS,
-21.2% OOS). It de-risked into SOL's biggest up-moves, because in crypto volatility
rises *with* price as often as against it — the same failure `voltarget.md` shows
from the other direction, and a more damaging one here because this rule goes fully
flat rather than merely trimming.

Losing less than buy-and-hold out-of-sample (-21.2% against -70.8%) is not a defence:
a rule that is mostly flat will usually beat a falling market, and this one was flat
for the wrong reason.

The honest reading is that **volatility level is the wrong regime variable for this
market**. `hurst_regime_test.md` conditions on serial correlation instead and made
money on the same split, which is the more informative comparison this card provides.

## Caveats and limitations
- A quantile is not a state model. If the latent-state version behaves differently,
  this card does not tell you.
- `calm_quantile` at 0.5 means half of all bars are "elevated", which is a strong
  prior nobody tested.

## How to run
```bash
python3 -m backtester.cli --strategy vol_regime --interval 1d
```
