---
id: sma_regime
name: Slow-MA Regime Filter
kind: exposure-strategy
status: measured
family: regime-filter
summary: Long above a slow moving average, flat below it. The most valuable partner in the set.
registry_key: sma_regime
runner: backtester.cli
warmup_bars: 200
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  window: {default: 200, type: int, desc: "SMA window in bars"}
presets:
  short: {window: 168}
  medium: {window: 100}
  long: {window: 200}
---
# Slow-MA Regime Filter

## What it is
Fully long above a slow moving average, flat below it.

## What it looks for
A one-line answer to "is this a bull or a bear regime".

## Equation
```
target_t = 1 if c_t > SMA(n)_t else 0
```

## Implementation
`backtester/core/strategies/signals.py::Sma200Regime`.

## Parameters
- **window** — 168 hourly (one week), 100 or 200 daily. Longer means later turns and
  fewer of them.

## Works when
Regimes are persistent. Its value is less in returns than in *avoiding* the worst
drawdowns.

## Fails when
Price oscillates around the average, producing repeated entries and exits at the worst
possible points. Late by construction at every regime turn.

## Backtest notes
This is the strategy every more elaborate signal should be measured against. If an
eight-parameter system cannot beat "price above its 200-day average", the extra
parameters are not earning their keep.

## Pairs with
**This is the single most valuable partner in the whole set.** Mean reversion's fatal
mode is buying dips inside a downtrend, and this is the only component here that
answers "is there a downtrend". Measured as the top short-horizon pair and the top
triple.

## Measured on SOL
Standalone medium (100): IS +34.8% -> **OOS -35.8%**, 13 OOS trades.
**As a partner it is transformative:** `all(sma_regime + zscore)` reached **OOS Sharpe
+2.572** at the short horizon, against +0.441 for `zscore` alone. `all(sma_regime +
rsi)` reached **+1.456**.

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
- Standalone it lost money out-of-sample. Its case rests almost entirely on what it
  does for *other* signals, which is a different claim and should not be blurred.
- A pair result built on the same hostile split inherits the same fragility. The
  partner effect is mechanically plausible — it vetoes the exact failure mode — but
  +2.572 is one number from one split.

## How to run
```bash
python3 -m backtester.cli --strategy sma_regime --interval 1d
```
