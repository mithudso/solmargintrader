---
id: ema_crossover
name: EMA Crossover (golden cross)
kind: exposure-strategy
status: implemented
family: trend
summary: Long while the fast EMA is above the slow EMA. At 50/200 this is the golden cross the guides describe.
registry_key: ema_crossover
runner: backtester.cli
warmup_bars: 200
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  fast: {default: 50, type: int, desc: "fast EMA span"}
  slow: {default: 200, type: int, desc: "slow EMA span"}
presets:
  short: {fast: 10, slow: 30}
  medium: {fast: 20, slow: 50}
  long: {fast: 50, slow: 200}
---
# EMA Crossover (golden cross)

## What it is
Long while `EMA(fast) > EMA(slow)`. The EMA twin of `ma_crossover`: recent closes weigh more, so it turns earlier and whipsaws more.

## What it looks for
A change of trend. The guides call a short MA crossing above a long MA bullish (golden cross at 50/200) and the reverse bearish (death cross).

## Equation
```
alpha    = 2 / (span + 1)
EMA_t    = alpha * close_t + (1 - alpha) * EMA_{t-1}
target_t = 1 if EMA(fast)_t > EMA(slow)_t else 0
```

## Implementation
`backtester/core/strategies/textbook.py::EmaCrossover`, over `indicators.ema`. Long/flat; it never shorts.

## Parameters
- **fast / slow** with `fast < slow`. 50/200 is a daily-bar convention; the short and medium presets exist because it produces only a handful of trades on daily SOL.

## Works when
Sustained directional moves long enough to outlast the slow EMA's lag.

## Fails when
Chop. The slow EMA at span 200 reacts months late, so the cross confirms a move that has already largely happened.

## Backtest notes
Warm-up is the slow span. At 50/200 only a few round trips occur in five years, so any single result is below the 10-trade evidence floor.

## Pairs with
A volatility or regime filter; on its own it is highly correlated with `ma_crossover` and `ma_ribbon`.

## Measured on SOL
Smoke run only, not a sweep row: `python3 -m backtester.cli --split 0.7 --interval 1d`, SOL daily 2021-06-17..2026-08-04, default parameters, 8 bps round-trip costs, one 70/30 split. The split is structurally hostile to long-biased rules (see `research/RANKED_LISTS.md`), so read it as one regime transition, not an estimate. The queue (`soltui/bgqueue.py`) will produce the evaluated numbers; this card stays `implemented` until a sweep supplies them.

Full sample: +61.85% (Sharpe 0.445, only 4 trades) vs buy-and-hold +87.61%. 70/30 split: IS +335.0% (Sharpe 0.988) -> OOS -60.99% (Sharpe -0.926). Four trades is below the evidence floor, so this row would be listed and never ranked.

## Likelihood of success: very-low

*Basis: base-rate. A moving-average cross is the most-tested rule in the sweep, and the trend family it sits in measured poorly out of sample.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
python3 -m backtester.cli --strategy ema_crossover --interval 1d --split 0.7
```
