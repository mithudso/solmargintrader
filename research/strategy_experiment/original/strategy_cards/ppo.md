---
id: ppo
name: Percentage Price Oscillator cross
kind: exposure-strategy
status: implemented
family: trend
summary: Long while the PPO line is above its signal line. MACD divided by the slow EMA, so readings are comparable across price levels.
registry_key: ppo
runner: backtester.cli
warmup_bars: 37
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  fast: {default: 12, type: int, desc: "fast EMA span"}
  slow: {default: 26, type: int, desc: "slow EMA span"}
  signal: {default: 9, type: int, desc: "span of the EMA applied to the PPO line"}
presets:
  short: {fast: 6, slow: 13, signal: 5}
  medium: {fast: 12, slow: 26, signal: 9}
  long: {fast: 26, slow: 52, signal: 18}
---
# Percentage Price Oscillator cross

## What it is
MACD expressed as a percentage of the slow EMA, compared with an EMA of itself.

## What it looks for
Acceleration in trend, in units that do not depend on the price level: a PPO of 2.5 means the same at $20 and $200.

## Equation
```
PPO_t    = 100 * (EMA(fast)_t - EMA(slow)_t) / EMA(slow)_t
Signal_t = EMA(signal) applied to the PPO SERIES
target_t = 1 if PPO_t > Signal_t else 0
```

## Implementation
`backtester/core/strategies/textbook.py::PpoCross`, over `indicators.ppo`, which rebuilds the PPO history with `ema_series` exactly as `indicators.macd` does.

## Parameters
- **fast / slow / signal** follow MACD's 12/26/9 convention and horizon presets.

## Works when
Directional moves with steady acceleration, the same regime as MACD.

## Fails when
Chop, with the same constant sign flips as `macd`. Fast presets pay more in fees than they earn.

## Backtest notes
Because PPO = MACD / slow EMA, the PPO-vs-signal cross sits at nearly the same bars as the MACD cross on one asset. This card will probably measure as a near-duplicate of `macd`; `research/signal_redundancy.py` is the test of that, and the family label `trend` is a prior, not a finding. If the redundancy score confirms it, the right outcome is to keep the card as documented evidence of redundancy, not to count it as a second bet.

## Pairs with
A volume-flow signal (`obv_trend`), not another trend signal.

## Measured on SOL
Smoke run only, not a sweep row: `python3 -m backtester.cli --split 0.7 --interval 1d`, SOL daily 2021-06-17..2026-08-04, default parameters, 8 bps round-trip costs, one 70/30 split. The split is structurally hostile to long-biased rules (see `research/RANKED_LISTS.md`), so read it as one regime transition, not an estimate. The queue (`soltui/bgqueue.py`) will produce the evaluated numbers; this card stays `implemented` until a sweep supplies them.

Full sample: +822.84% (Sharpe 0.971, 68 trades, fees $8,490 on a $10,000 start) vs buy-and-hold +87.61%. 70/30 split: IS +1,948.5% (Sharpe 1.499) -> OOS -53.30% (Sharpe -0.754). The same in-sample-triumph-then-OOS-loss shape as `macd` (+1,356.5% IS -> -52.8% OOS).

## Likelihood of success: very-low

*Basis: base-rate. A rescaled MACD adds no new hypothesis. The nearest card, `macd`, measured among the worst in the sweep out of sample.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
python3 -m backtester.cli --strategy ppo --interval 1d --split 0.7
```
