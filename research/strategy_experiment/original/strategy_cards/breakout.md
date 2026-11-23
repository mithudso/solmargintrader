---
id: breakout
name: Donchian Channel Breakout
kind: exposure-strategy
status: measured
family: breakout
summary: Long on a new n-bar high, flat on an m-bar low. The Turtle mechanism.
registry_key: breakout
runner: backtester.cli
warmup_bars: 21
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  entry_lookback: {default: 20, type: int, desc: "bars in the entry high channel"}
  exit_lookback: {default: 10, type: int, desc: "bars in the exit low channel"}
presets:
  short: {entry_lookback: 12, exit_lookback: 6}
  medium: {entry_lookback: 20, exit_lookback: 10}
  long: {entry_lookback: 60, exit_lookback: 30}
---
# Donchian Channel Breakout

## What it is
Long on a new *n*-bar high; flat on an *m*-bar low. The Turtle mechanism.

## What it looks for
Range expansion — the start of a new trend leg.

## Equation
```
Upper_t = max(H_{t-n} .. H_{t-1})     # EXCLUDES the current bar
Lower_t = min(L_{t-m} .. L_{t-1})
enter if c_t > Upper_t ;  exit if c_t < Lower_t
```

## Implementation
`backtester/core/strategies/breakout.py`.

## Parameters
- **entry_lookback / exit_lookback** — asymmetric on purpose: enter on a longer
  channel, leave on a shorter one, so exits are faster than entries.

## Works when
Volatility expands out of contraction and the resulting trend runs far enough to pay
for the false starts.

## Fails when
False breakouts dominate. The Turtles' documented win rate was **30–35%** — the profile
depends entirely on a few large winners, so **missing a handful of big moves ruins the
year**. That makes short backtest windows especially unreliable for this family.

## Backtest notes
**The channel must exclude the current bar.** Including the current high makes the
comparison nearly always false and silently guts the strategy — a bug that looks like
a working strategy with poor results. Documented false-breakout filters worth testing:
require two consecutive closes beyond the level; require the breakout candle's body to
exceed 70% of its range; require above-average volume.

## Pairs with
Volume (a genuine breakout shows participation); a volatility-squeeze filter; a
reversion rule for the exit, which a pure breakout rule handles poorly.

## Measured on SOL
Full-sample medium: +620.7%, Sharpe 0.935. Walk-forward: **IS +860.2% (Sharpe 1.265)
-> OOS -7.5%** on only 7 OOS trades — **below the evidence floor**, which is exactly the
low-trade-count problem the Turtle profile predicts.
`any(breakout + zscore)` was the **best measured medium pair: OOS Sharpe +0.584, +30.8%**.

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

OOS -7.5% on **7 trades** cannot be ranked, and a documented 30-35% win rate means any
window short enough to contain few large winners misrepresents this family in either
direction. The reason it is not very-low is `any(breakout+zscore)`, the **best measured
medium pair** (+0.584 Sharpe, +30.8%). The mechanism is documented and durable; this
sample cannot show it.

## Caveats and limitations
- With a 30–35% win rate, any window short enough to contain few large winners will
  misrepresent this strategy in either direction.
- 7 out-of-sample trades cannot rank. This card's headline is the *pair*, not the
  single.

## How to run
```bash
python3 -m backtester.cli --strategy breakout --interval 1d
```
