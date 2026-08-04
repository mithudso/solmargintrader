---
id: hurst_regime_test
name: Variance-Ratio / Hurst Regime Switch
kind: exposure-strategy
status: measured
family: regime-filter
summary: A meta-signal: measure whether the series trends or reverts, then run the matching rule.
registry_key: hurst_switch
runner: backtester.cli
warmup_bars: 251
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: moderate
success_basis: measured-oos
params:
  window: {default: 250, type: int, desc: "bars used to estimate the variance ratio"}
  lag: {default: 5, type: int, desc: "aggregation horizon for the variance ratio"}
  trend_threshold: {default: 0.55, type: float, desc: "H above this selects the trend rule"}
  revert_threshold: {default: 0.45, type: float, desc: "H below this selects the reversion rule"}
  trend_window: {default: 50, type: int, desc: "SMA window for the trend rule"}
  entry_z: {default: -2.0, type: float, desc: "z-score entry for the reversion rule"}
presets: {}
---
# Variance-Ratio / Hurst Regime Switch

> **Implemented in this session** from spec-only mechanism #25 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
# Variance-Ratio / Hurst Regime Switch

## What it is
Not a directional signal — **a selector**. It estimates whether the series is
trending or mean-reverting, then runs the matching rule, and holds nothing when
neither regime is established.

## Equation
```
VR  = Var(k-period returns) / (k * Var(1-period returns))     # Lo-MacKinlay
H   = 0.5 * (1 + ln(VR)/ln(k))                                # the familiar scale

if H > trend_threshold:   target = 1 if c_t > SMA(trend_window) else 0
if H < revert_threshold:  target = 1 if z_t <= entry_z else 0
otherwise:                target = 0          # "I cannot tell" is a position
```

A variance ratio is used rather than a rescaled-range Hurst estimator, which is badly
biased on short samples; the H figure is reported only because it is the vocabulary
the literature uses.

## Why this mechanism was singled out before it was run
Every other strategy in this repo bets that one of trend or reversion is present, and
**none of them checks which**. The measured sweep shows the two inverting between
regimes — that is the failure dominating all sixteen original results. A selector
addresses it directly instead of adding a seventeenth directional opinion.

## Implementation
`backtester/core/strategies/advanced.py::HurstRegimeSwitch`, using the new
`indicators.variance_ratio` and `indicators.hurst_from_variance_ratio`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +126.2% | 0.984 | — |
| **Out-of-sample** | ****+15.6%**** | ****+0.564**** | **10** |

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

## Likelihood of success: moderate

*Basis: measured-oos. This is the only card in the directory rated moderate.*

Four things support it, and one caveat bounds it.

1. **It made money out-of-sample: +15.6% at a +0.564 Sharpe**, through the leg that
   cost buy-and-hold 70.8%. Of everything measured in this repo across 311 rankable
   configurations, positive-and-profitable is a 9% event.
2. **It clears the evidence floor at exactly 10 trades** — the same standing as
   `zscore`, the previously top-ranked medium single.
3. **Its in-sample number is modest (+126.2%)**, which is a point in its favour here.
   The rows that collapsed hardest out-of-sample were the ones with four-figure
   in-sample returns; this one never claimed much.
4. **The mechanism was predicted to be the most valuable unimplemented item before
   any measurement existed**, on the structural argument above. Getting a positive
   result from a pre-registered prediction is worth more than finding one by search.

The caveat: **10 trades is 10 trades**, and this is still one number from the same
hostile split that inverted every other ranking. `RANKED_LISTS.md` found the
previous top-ranked row consistent with noise on a within-mechanism test, and nothing
here rules out the same verdict. Moderate means "worth the next experiment", not
"works" — and the next experiment is CPCV, not another split.

## Caveats and limitations
- Estimating H on a rolling window is noisy, and the estimate is itself
  regime-dependent — the snake eats its tail.
- A selector multiplies the strategy space and therefore the multiple-testing
  problem. It should be evaluated under CPCV before any weight is put on it.
- Six parameters, none swept. The thresholds 0.55/0.45 are conventional, not fitted,
  which is the honest choice but also an unexamined one.
- The child rules are deliberately crude (an SMA and a z-score). A better result may
  reflect the selector or may reflect the children; this experiment cannot separate them.

## How to run
```bash
python3 -m backtester.cli --strategy hurst_switch --interval 1d
```
