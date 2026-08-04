---
id: rsi
name: RSI Mean-Reversion
kind: exposure-strategy
status: measured
family: oscillator-reversion
summary: Buy when Wilder's RSI is oversold, exit when it recovers past a midline. Stateful hold between.
registry_key: rsi
runner: backtester.cli
warmup_bars: 15
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  period: {default: 14, type: int, desc: "Wilder RSI period"}
  oversold: {default: 30.0, type: float, desc: "RSI level that triggers entry"}
  exit_level: {default: 50.0, type: float, desc: "RSI level that triggers exit"}
presets:
  short: {period: 7, oversold: 30.0, exit_level: 55.0}
  medium: {period: 14, oversold: 30.0, exit_level: 50.0}
  long: {period: 30, oversold: 35.0, exit_level: 55.0}
---
# RSI Mean-Reversion

## What it is
Buy when Wilder's RSI is oversold; exit when it recovers past a midline. The position
is **held statefully** between those events, so this is not a per-bar recomputation.

## What it looks for
Short-term exhaustion of selling pressure.

## Equation
```
gain_t, loss_t   = max(dC_t, 0), max(-dC_t, 0)
avgGain, avgLoss = Wilder smoothing with period p
RS   = avgGain / avgLoss
RSI  = 100 - 100/(1 + RS)
enter if RSI < oversold ;  exit if RSI > exit_level
```

## Implementation
`backtester/core/strategies/rsi.py`.

## Parameters
- **period** — 7 hourly, 14 daily, 30 for the slow scale.
- **oversold / exit_level** — the gap between them sets the minimum round trip. Setting
  `exit_level` near `oversold` produces a high-frequency, cost-dominated strategy.

## Works when
Range-bound, mean-reverting conditions.

## Fails when
**In a strong trend RSI stays oversold for weeks, and the reading becomes a
trend-continuation indicator rather than a reversal signal.** Mean-reversion families
show attractive 60–80% win rates that conceal rare catastrophic losses — picking up
nickels in front of a steamroller.

## Backtest notes
**Judge this family on the tail, not the win rate.** A 75%-win-rate equity curve with
one -60% trade is not a good strategy, and average-based metrics hide it. Report max
drawdown and the worst single trade, both of which this harness computes.

## Pairs with
A regime filter — arguably mandatory, since it patches the exact failure mode. Volume,
to distinguish accumulation from distribution.

## Measured on SOL
Medium: IS -9.6% -> OOS -21.9% on only 4 OOS trades (below the floor).
Short (period 7): **OOS Sharpe -0.527**.
`all(sma_regime + rsi)` reached **OOS +1.456** — the filter did the work, not the RSI.

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

*Basis: measured-oos. There is no 'high' rating in this scheme — across 311 rankable
configurations, 14% had a positive out-of-sample Sharpe and 9% made money.*

4 out-of-sample trades at the medium horizon is not a sample, and the short horizon
scored -0.527. The known failure mode is decisive here: in a strong trend RSI stays
oversold for weeks and becomes a trend-continuation indicator. SOL's out-of-sample
leg was exactly that trend. `all(sma_regime+rsi)` reached +1.456 — but the filter
did the work.

## Caveats and limitations
- 4 out-of-sample trades is not evidence of anything.
- The pair result is the interesting one, and it belongs as much to `sma_regime.md` as
  to this card.

## How to run
```bash
python3 -m backtester.cli --strategy rsi --interval 1d
```
