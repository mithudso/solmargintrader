---
id: macd
name: MACD Crossover
kind: exposure-strategy
status: measured
family: trend
summary: Long while the MACD line is above its signal line. Momentum of the gap between two EMAs.
registry_key: macd
runner: backtester.cli
warmup_bars: 53
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  fast: {default: 12, type: int, desc: "fast EMA span"}
  slow: {default: 26, type: int, desc: "slow EMA span"}
  signal: {default: 9, type: int, desc: "span of the EMA applied to the MACD line"}
presets:
  short: {fast: 6, slow: 13, signal: 5}
  medium: {fast: 12, slow: 26, signal: 9}
  long: {fast: 26, slow: 52, signal: 18}
---
# MACD Crossover

## What it is
The gap between two EMAs, compared against an EMA of that gap.

## What it looks for
Acceleration in trend, earlier than a raw moving-average cross.

## Equation
```
EMA(s)_t = a*c_t + (1-a)*EMA(s)_{t-1},   a = 2/(s+1)
MACD_t   = EMA(fast)_t - EMA(slow)_t
Signal_t = EMA(sig) applied to the MACD SERIES
Hist_t   = MACD_t - Signal_t
target_t = 1 if MACD_t > Signal_t else 0
```

## Implementation
`backtester/core/strategies/signals.py::MacdCross`. Note the signal line is an EMA
*of the MACD line*, so a history of MACD values is needed — see
`indicators.ema_series`.

## Parameters
- **fast / slow / signal** — the classic 12/26/9 is a daily-bar convention, not a law.
  At the short horizon 6/13/5 was used, and it behaved like a different strategy.

## Works when
Directional moves with steady acceleration.

## Fails when
Chop produces constant sign flips. **This is the worst measured row in the entire
sweep at the short horizon:** `macd_6_13_5` scored **OOS Sharpe -4.621 across 205
trades**. That number is what fast-parameter whipsaw plus 8 bps round-trip cost looks
like, and it is the single most useful row here for calibrating how much damage
turnover does.

## Backtest notes
Naively recomputing MACD history each bar is O(signal*cap * slow*cap) and once
dominated total sweep runtime. The single-pass `ema_series` reduces it to
O(cap*slow + count). Worth knowing before extending this.

## Pairs with
`stochastic` as an oscillator brake, to stop MACD adding into an exhausted move —
measured as one of only eight positive medium-horizon pairs.

## Measured on SOL
Medium (12/26/9): **IS +1,356.5% (Sharpe 1.347) -> OOS -52.8% (Sharpe -0.720)**,
21 OOS trades. One of the starkest decay rows in the sweep.
Short (6/13/5): **OOS Sharpe -4.621**, 205 trades.

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
- A four-figure in-sample return next to a negative out-of-sample Sharpe is the
  clearest illustration in this directory of why full-sample leaderboards are
  worthless.
- Turnover is the dominant term at fast parameters. Do not read the short-horizon
  result as "MACD does not work"; read it as "MACD at 6/13/5 on hourly SOL bars pays
  more in fees than it earns in signal".

## How to run
```bash
python3 -m backtester.cli --strategy macd --interval 1d
```
