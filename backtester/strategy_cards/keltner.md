---
id: keltner
name: Keltner Channel Breakout
kind: exposure-strategy
status: measured
family: breakout
summary: Breakout of an ATR-width channel around an EMA. Like Bollinger, but its volatility measure sees gaps.
registry_key: keltner
runner: backtester.cli
warmup_bars: 61
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  ema_span: {default: 20, type: int, desc: "EMA span for the channel centre"}
  atr_period: {default: 14, type: int, desc: "Wilder ATR period"}
  mult: {default: 2.0, type: float, desc: "channel half-width in ATRs"}
presets:
  short: {ema_span: 12, atr_period: 7, mult: 2.0}
  medium: {ema_span: 20, atr_period: 14, mult: 2.0}
  long: {ema_span: 50, atr_period: 30, mult: 2.0}
---
# Keltner Channel Breakout

## What it is
Breakout of an ATR-width channel around an EMA.

## What it looks for
The same thing as a Bollinger breakout, measured with a volatility estimate that
includes gaps.

## Equation
```
TR_t  = max(H_t - L_t, |H_t - c_{t-1}|, |L_t - c_{t-1}|)
ATR_t = Wilder smoothing of TR with period p:  ATR_t = (ATR_{t-1}*(p-1) + TR_t)/p
enter if c_t > EMA(s)_t + m*ATR_t ;  exit if c_t < EMA(s)_t
```

## Implementation
`backtester/core/strategies/signals.py::KeltnerBreakout`.

## Parameters
- **ema_span / atr_period / mult** — `mult` at 2.0 is conventional; it is also the knob
  that trades entry frequency against false starts.

## Works when
Trending markets with expanding true range.

## Fails when
The same chop problem as any breakout. Its one genuine advantage over Bollinger is
**gap handling**: true range includes the gap, close-to-close stdev does not.

## Backtest notes
ATR is also the documented **sizing and stop** unit: stops at 1.5–2 ATR, position sized
so that 1 ATR of adverse move equals about 1% of the account. That risk-overlay use is
arguably more valuable than the entry signal, and **it is not tested here** — see
`atr_position_sizing.md`.

## Pairs with
Trend confirmation; volume.

## Measured on SOL
Medium: IS +880.7% (Sharpe 1.391) -> **OOS -26.4%** on 6 OOS trades (below the evidence
floor). Short: **OOS Sharpe -1.954** on 13 trades despite a positive in-sample result.

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
- 6 out-of-sample trades at the medium horizon cannot support a ranking.
- The gap-handling advantage over Bollinger is real but was not isolated by any
  experiment here; both simply lost out-of-sample.

## How to run
```bash
python3 -m backtester.cli --strategy keltner --interval 1d
```
