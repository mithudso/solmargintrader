---
id: bb_reversion
name: Bollinger Mean-Reversion
kind: exposure-strategy
status: measured
family: mean-reversion
summary: Buy a close below the lower Bollinger band, exit on reversion to the mid. Same inequality as zscore.
registry_key: bb_reversion
runner: backtester.cli
warmup_bars: 20
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  window: {default: 20, type: int, desc: "SMA and stdev window"}
  num_std: {default: 2.0, type: float, desc: "entry distance below the mean, in population stdevs"}
presets:
  short: {window: 20, num_std: 2.0}
  medium: {window: 20, num_std: 2.0}
  long: {window: 60, num_std: 2.0}
---
# Bollinger Mean-Reversion

## What it is
Buy a close below the lower band; exit on reversion to the mid.

## What it looks for
Statistically extreme downside deviation.

## Equation
```
enter if c_t < mid_t - k*sd_t ;  exit if c_t > mid_t        # sd is ddof=0
```

## The defect you must know about
**This is the same inequality as `zscore.md`**, differing only in the standard-deviation
convention: `ddof=0` here against `ddof=1` there, a factor of `sqrt(n/(n-1)) ~ 1.026` at
n=20. The exits are exactly equivalent (`c > mid` iff `z > 0`).

**These are one mechanism at two thresholds, not two signals.** Because both are in the
sweep, several "cross-family" pairs and two identical `+2.555` triples are
double-counting a single idea. Verified from source, not assumed. Family labels are not
a substitute for measuring pairwise signal correlation.

## Implementation
`backtester/core/strategies/signals.py::BollingerReversion`.

## Works when
Range-bound regimes with a stable mean.

## Fails when
**The mean itself shifts.** Regime change is the primary killer: buying oversold in a
secular bear compounds losses. Measured full-sample medium: **-65.64%**.

## Backtest notes
**Bound the hold.** The Ornstein-Uhlenbeck half-life gives the natural cap — exit at
2–3x half-life regardless of signal, and a half-life beyond 30 days means the series is
not mean-reverting in any tradeable sense. **This implementation has no such cap**,
which is a real gap rather than a stylistic choice. See `ou_half_life_sizing.md`.

## Pairs with
A regime filter (essential); volume.

## Measured on SOL
Medium: IS -63.9% -> **OOS Sharpe +0.193** (-4.8% return) on 10 OOS trades.
`all(sma_regime + bb_reversion)`: **OOS Sharpe +2.572** at the short horizon.

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

*Basis: measured-oos. There is no 'high' rating in this scheme — across 311 rankable
configurations, 14% had a positive out-of-sample Sharpe and 9% made money.*

**OOS Sharpe +0.193 on a -4.8% return** — a positive Sharpe with a negative return
means low, well-behaved exposure, not profit. Full-sample was -65.64%. It also has
no hold cap, which `ou_reversion` exists to fix, and it is the same inequality as
`zscore` so any pair combining the two double-counts one idea.

## Caveats and limitations
- A positive Sharpe with a negative return means low, well-behaved exposure — not profit.
- Any pair or triple combining this with `zscore` is double-counting one mechanism.

## How to run
```bash
python3 -m backtester.cli --strategy bb_reversion --interval 1d
```
