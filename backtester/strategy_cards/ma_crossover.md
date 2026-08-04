---
id: ma_crossover
name: Moving-Average Crossover
kind: exposure-strategy
status: measured
family: trend
summary: Long while a fast SMA sits above a slow SMA. The canonical trend-following rule.
registry_key: ma_crossover
runner: backtester.cli
warmup_bars: 50
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  fast: {default: 20, type: int, desc: "fast SMA window in bars"}
  slow: {default: 50, type: int, desc: "slow SMA window in bars; must exceed fast"}
  short_when_below: {default: false, type: bool, desc: "if true go short below instead of flat (perp mode only)"}
presets:
  short: {fast: 12, slow: 48}
  medium: {fast: 20, slow: 50}
  long: {fast: 50, slow: 200}
---
# Moving-Average Crossover

## What it is
Long while a fast simple moving average sits above a slow one; flat (or short)
otherwise.

## What it looks for
Persistent directional drift — the premise that trends continue.

## Equation
```
SMA(n)_t = (1/n) * sum_{k=0}^{n-1} c_{t-k}
target_t = 1  if SMA(f)_t > SMA(s)_t  else 0        (f < s)
```
With `short_when_below=True` and `mode=perp`, the else branch is `-1` instead of `0`.

## Implementation
`backtester/core/strategies/ma_crossover.py`.

## Parameters
- **fast / slow** — the ratio is a *cost* decision as much as a signal one, because
  crossover frequency sets turnover and every crossing pays 8 bps round trip.
- **short_when_below** — off by default. Spot mode clamps short exposure to 0 and
  warns, so setting this without `--mode perp` does nothing.

## Works when
Trends persist longer than the slow window. Best in low-noise, high-autocorrelation
regimes.

## Fails when
Range-bound chop. Every oscillation produces a whipsaw pair of fills, and the
strategy is structurally **late**: confirmation requires the averages to have already
crossed.

## Backtest notes
Whipsaw sensitivity makes results strongly parameter-dependent, so report the
parameter scale rather than "MA crossover". `--rebalance-threshold` adds a deadband
and materially changes the fee drag.

## Pairs with
- `obv_trend` — volume confirmation, to filter drifts nobody participated in.
- `sma_regime` — suppress counter-trend entries.
- `breakout` — earlier entry than a crossover can give.

## Measured on SOL
**Best short-horizon single: OOS Sharpe +0.488** (IS -2.490), +3.4% on 29 trades.
Medium (20/50): IS +735.6% -> **OOS -52.3%** on 7 OOS trades — below the evidence floor.

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

## Caveats and limitations
- The short-horizon result is the best in its horizon and still only +3.4% before
  any slippage beyond the modelled 2 bps.
- 7 out-of-sample trades at the medium horizon is not a sample, it is an anecdote.

## How to run
```bash
python3 -m backtester.cli --strategy ma_crossover --interval 1d
```
