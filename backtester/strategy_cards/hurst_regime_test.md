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
evaluation: cpcv-8-groups-k2-daily-and-hourly
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  window: {default: 250, type: int, desc: "bars used to estimate the variance ratio"}
  lag: {default: 5, type: int, desc: "aggregation horizon for the variance ratio"}
  trend_threshold: {default: 0.55, type: float, desc: "H above this selects the trend rule"}
  revert_threshold: {default: 0.45, type: float, desc: "H below this selects the reversion rule"}
  trend_window: {default: 50, type: int, desc: "SMA window for the trend rule"}
  entry_z: {default: -2.0, type: float, desc: "z-score entry for the reversion rule"}
presets:
  short: {window: 250, lag: 5, trend_window: 168}
  medium: {window: 250, lag: 5, trend_window: 100}
  long: {window: 250, lag: 10, trend_window: 200}
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

## Likelihood of success: low

*Basis: measured-oos. **Downgraded from moderate after the hourly test below.***

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

## Re-evaluated under CPCV

Combinatorial purged cross-validation (`core/cpcv.py`), 8 groups, k=2, on the same
1,875 daily bars — 28 out-of-sample paths where the series allows, instead of one
arbitrary split. Full run for all 25 registered configurations:
`research/results/cpcv_all25_1d.csv`.

| Statistic | hurst_switch | buy_and_hold | zscore |
|---|---|---|---|
| Median path Sharpe | **+0.699** | +0.534 | +0.036 |
| Q1 path Sharpe (the conservative read) | **+0.609** | −0.095 | −0.539 |
| Paths with positive Sharpe | **93%** | 68% | 52% |
| Median path return | **+16.7%** | +9.4% | −10.0% |
| Total trades | 24 | 16 | 50 |

**It ranks first of all 25 configurations by median path Sharpe**, and it is the only
one whose 25th-percentile path is comfortably positive — Lopez de Prado's recommended
conservative statistic. It also has **no negative block**: per-block Sharpes are
+0.86, +2.67, 0.00, 0.00, +0.99, +0.29.

**Adding it to the set *lowered* the Probability of Backtest Overfitting.** On the six
blocks every configuration shares, PBO across the original 16 is 0.600; adding
hurst_switch gives 0.400. So it is not the artifact that in-sample selection latches
onto — it makes selection more reliable. (Both figures sit above the prior study's
0.429–0.457 because restricting to six common blocks leaves only 20 CSCV splits; treat
the *direction* of the change as the signal, not the level.)

### Downgraded from moderate: the hourly series

The moderate rating was explicitly conditional — "worth the next experiment, not works,
and the next experiment is CPCV". CPCV on daily passed. The follow-up test was the
hourly series, chosen because trade count was the binding constraint. **It failed.**

Same mechanism at the sweep's pre-registered short-horizon scaling (window 250, lag 5,
trend_window 168) on 8,823 hourly bars, 8 groups, k=2
(`research/results/cpcv_all25_1h.csv`):

| | daily | hourly |
|---|---|---|
| Rank by median path Sharpe | **1st of 25** | **23rd of 25** |
| Median path Sharpe | +0.699 | **−3.123** |
| Q1 path Sharpe | +0.609 | −3.878 |
| Paths positive | 93% | 14% |
| Median path return | +16.7% | −12.8% |
| Trades | 24 | 170 |

Seven times the trades, and the rank inverted from first to third-from-last. That is the
single strongest piece of evidence available about this mechanism, and it says the daily
result was **scale-specific at best**.

**One honest confound, which does not rescue it.** The hourly file covers
2025-08→2026-08 only, and that year was brutal: **zero of 25 configurations** had a
positive median path Sharpe, and buy-and-hold itself lost 22.9%. So the hourly test is a
different *period* as well as a different scale, and "everything lost" is partly the
market. But rank is period-invariant by construction — every configuration faced the
same bars — and hurst_switch went from best to nearly worst *relative to its peers*. It
also lost more than buy-and-hold's Sharpe while trading 170 times.

The repo's own headline finding is that in-sample rank does not predict out-of-sample
rank. This card is now a demonstration of the same effect **across horizons**, which is
a more uncomfortable version of it: the rank was not stable across a change of scale
either.

### What would change the rating back
A third independent test that it passes — a peer universe, or a different asset's daily
series. Not another look at the daily SOL bars, which it has now been fitted to by
selection whether or not anyone intended that.

### The trade-count caveat that applied even on daily

The trade count. **24 trades across six blocks**, and two of those blocks traded
**zero** times — their 0.00 Sharpes are "never lost", not "usually won", which inflates
the 93%-positive figure. Block 3's headline +2.669 rests on **two trades**. A mechanism
that abstains most of the time and is right when it acts is the profile you want, but it
is also the profile that a small sample cannot distinguish from luck.

So: the pre-registered prediction survived the harder test, the rating stays at
**moderate**, and the next honest step is more data rather than more confidence —
either the hourly series or a peer universe, both of which multiply the trade count
without re-using this one.

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
