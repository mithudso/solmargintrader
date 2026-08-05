---
id: voltarget
name: Volatility-Targeted Trend
kind: exposure-strategy
status: measured
family: sma-gated
summary: Trend entry sized inversely to realised volatility. Continuous exposure, not binary.
registry_key: voltarget
runner: backtester.cli
warmup_bars: 101
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  trend_window: {default: 100, type: int, desc: "SMA window for the trend gate"}
  vol_window: {default: 20, type: int, desc: "window for realised volatility"}
  target_vol: {default: 0.6, type: float, desc: "annualised volatility target, decimal"}
presets:
  short: {trend_window: 168, vol_window: 24, target_vol: 0.8}
  medium: {trend_window: 100, vol_window: 20, target_vol: 0.6}
  long: {trend_window: 200, vol_window: 60, target_vol: 0.6}
---
# Volatility-Targeted Trend

## What it is
A trend entry, sized inversely to realised volatility. The only card here whose
exposure is **continuous** rather than 0/1.

## What it looks for
Constant *risk* rather than constant *notional*.

## Equation
```
sigma_t  = stdev(log returns over n bars) * sqrt(periods_per_year)
target_t = min(1, target_vol / sigma_t)   if c_t > SMA(trend)_t   else 0
```

## Implementation
`backtester/core/strategies/signals.py::VolTargetTrend`.

## Parameters
- **target_vol** — 0.6 means a 60% annualised volatility target, which is modest for
  SOL and therefore usually binds.
- **vol_window** — sets the lag with which the sizing reacts.

## Works when
Volatility is persistent, which it is in crypto — volatility clusters. This changes the
*shape* of the equity curve rather than the direction of the bet.

## Fails when
Volatility spikes and price rises together, so it de-risks into strength. It also
reacts with a lag equal to the vol window.

## Backtest notes
**This should be tested as a wrapper around other signals, not as a standalone
strategy — and that is exactly what was not done here.** It is the only candidate in
the set that is orthogonal to direction *by construction* rather than by assumption, so
the untested wrapper configuration is the most obvious gap in the whole sweep.

Note the degeneracy: when `sigma < target_vol` the cap binds at 1.0 and this becomes
the plain regime filter. At the short horizon its numbers were near-identical to
`sma_regime_168` for precisely that reason.

## Pairs with
Everything, multiplicatively — that is the whole idea, and it is untested.

## Measured on SOL
Medium: IS +15.7% -> **OOS -31.1%** on 73 OOS trades. Short: OOS -0.519, numerically
near-identical to `sma_regime_168`.

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

OOS -31.1% standalone, and at the short horizon it degenerates into `sma_regime`
whenever the vol cap binds. The rating is **low** rather than very-low only because
it was measured in the one configuration that wastes it: this belongs as a *wrapper*
around another signal, which is the most obvious untested gap in the sweep.

### The hourly run exposed a three-way degeneracy

On 8,823 hourly bars at short-horizon scaling, `voltarget`, `garch_voltarget` and
`sma_regime` produced **numerically identical** results — median path Sharpe −2.282,
median return −19.9%, 292 trades, all three. That is not a coincidence and it is not a
bug: at `target_vol` 0.8 on hourly SOL the volatility cap binds on essentially every
bar, so `min(1, target/sigma)` collapses to 1.0 and both vol-targeted rules degenerate
into the plain trend gate they share with the regime filter.

The caveat was written on these cards before it was observed. Seeing three separate
"strategies" return one identical row is the cleanest demonstration available that a
sweep's configuration count overstates how many distinct ideas are in it.

## Caveats and limitations
- Measured in the one configuration that wastes it. Read the numbers as "vol-targeted
  trend-following on SOL", not as a verdict on vol targeting.
- The degeneracy into `sma_regime` when the cap binds means the standalone result is
  partly a duplicate of another card.

## How to run
```bash
python3 -m backtester.cli --strategy voltarget --interval 1d
```
