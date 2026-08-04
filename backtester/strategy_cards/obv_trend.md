---
id: obv_trend
name: On-Balance Volume Trend
kind: exposure-strategy
status: measured
family: volume-flow
summary: Long while cumulative signed volume is above its own moving average. Price-blind by construction.
registry_key: obv_trend
runner: backtester.cli
warmup_bars: 22
evaluation: single-split-70-30
data_required: [ohlcv, volume]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  ma_window: {default: 20, type: int, desc: "SMA window applied to the OBV series"}
presets:
  short: {ma_window: 24}
  medium: {ma_window: 20}
  long: {ma_window: 60}
---
# On-Balance Volume Trend

## What it is
Long while cumulative signed volume sits above its own moving average.

## What it looks for
Accumulation against distribution — whether volume is arriving on up-bars or down-bars.

## Equation
```
OBV_t    = OBV_{t-1} + sign(c_t - c_{t-1}) * V_t
target_t = 1 if OBV_t > SMA(n) of OBV else 0
```

## Implementation
`backtester/core/strategies/signals.py::ObvTrend`.

## Works when
Volume genuinely leads price. **This signal is price-blind by construction**, which is
exactly what makes it a good *partner*: it sees something no price-based signal can.

## Fails when
Volume data is unreliable or venue-fragmented — a real crypto problem. OBV is also a
running cumulative sum, so it is **path-dependent and level-arbitrary**: only its slope
relative to its own average carries information.

## Backtest notes
Because OBV accumulates from an arbitrary origin, its absolute level is meaningless and
every comparison must be to its own history. **Splitting the series restarts the
accumulation**, so walk-forward legs are not directly comparable on OBV level — a
subtlety worth knowing before interpreting the numbers below.

## Pairs with
Any price-based trend or breakout signal. This is its highest and best use.

## Measured on SOL
Medium: **IS +1,932.1% (Sharpe 1.494) -> OOS -69.2% (Sharpe -1.383)**.
Long: IS +982.7% -> OOS -24.0%, and `any(rsi + obv_trend)` was the **best long-horizon
pair (OOS +0.226)** — though at -8.8% return, which means low well-behaved exposure
rather than profit.

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

IS +1,932.1% to **OOS -69.2%** is a textbook decay row. Its best result anywhere —
`any(rsi+obv_trend)`, the top long-horizon pair at +0.226 Sharpe — still *lost*
8.8%. Being price-blind makes it a good partner in principle; nothing here shows it
paying.

## Caveats and limitations
- The best long-horizon pair still lost money. A positive Sharpe on a negative return
  describes a strategy that mostly stayed out of the way.
- The accumulation restart across split boundaries is a genuine measurement artifact
  here, not a hypothetical.

## How to run
```bash
python3 -m backtester.cli --strategy obv_trend --interval 1d
```
