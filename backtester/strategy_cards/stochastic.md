---
id: stochastic
name: Stochastic Oscillator with Turn-Up Confirmation
kind: exposure-strategy
status: measured
family: oscillator-reversion
summary: Long when %K is oversold AND already above %D, so the turn has visibly begun.
registry_key: stochastic
runner: backtester.cli
warmup_bars: 18
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  k_period: {default: 14, type: int, desc: "lookback for the %K range"}
  d_period: {default: 3, type: int, desc: "SMA period for %D"}
  oversold: {default: 20.0, type: float, desc: "%K level that permits entry"}
  exit_level: {default: 80.0, type: float, desc: "%K level that triggers exit"}
presets:
  short: {k_period: 14, d_period: 3}
  medium: {k_period: 14, d_period: 3}
  long: {k_period: 40, d_period: 5}
---
# Stochastic Oscillator with Turn-Up Confirmation

## What it is
Long when %K is oversold **and** already above %D.

## What it looks for
Position within the recent range, plus evidence that the turn has actually begun.

## Equation
```
%K_t = 100 * (c_t - min(L_{t-k+1..t})) / (max(H_{t-k+1..t}) - min(L_{t-k+1..t}))
%D_t = SMA(d) of %K
enter if %K < oversold AND %K > %D ;  exit if %K > exit_level
```

## Implementation
`backtester/core/strategies/signals.py::StochasticOversold`.

## Parameters
- **k_period / d_period** — 14/3 is the convention; 40/5 for the slow scale.
- **oversold / exit_level** — 20/80 spans most of the oscillator's range, which keeps
  turnover low.

## Works when
Ranging markets. **The `%K > %D` condition is the meaningful addition** — buying
oversold *alone* is how you get run over in a downtrend.

## Fails when
Sustained trends, exactly as with RSI. Whipsaws on the %K/%D cross in noisy data.

## Backtest notes
Guard the degenerate case: when the *k*-bar range is zero, %K is undefined. This
implementation returns the neutral 50 rather than dividing by something near zero.

## Pairs with
Momentum, as a brake — `all(macd + stochastic)` measured positive. Z-score, as a second
independent statement that price is stretched.

## Measured on SOL
Medium: **OOS Sharpe +0.024** (IS +0.153) on 11 OOS trades — one of only three positive
medium-horizon singles, and barely distinguishable from zero.

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

**OOS Sharpe +0.024** on 11 trades: one of only three positive medium-horizon
singles, and indistinguishable from zero. The `%K > %D` turn-up condition is a
genuine improvement over buying oversold alone, which is why this clears very-low.
It clears nothing else.

## Caveats and limitations
- +0.024 is not an edge. It is the absence of a disaster, which on this split is
  itself unusual.
- 11 trades clears the evidence floor by one trade.

## How to run
```bash
python3 -m backtester.cli --strategy stochastic --interval 1d
```
