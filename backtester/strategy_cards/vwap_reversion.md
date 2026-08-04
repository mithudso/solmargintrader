---
id: vwap_reversion
name: Rolling VWAP Reversion
kind: exposure-strategy
status: measured
family: mean-reversion
summary: Buy a discount to rolling volume-weighted average price, exit on reversion.
registry_key: vwap_reversion
runner: backtester.cli
warmup_bars: 20
evaluation: single-split-70-30
data_required: [ohlcv, volume]
data_available: true
params:
  window: {default: 20, type: int, desc: "rolling VWAP window in bars"}
  entry_discount: {default: 0.02, type: float, desc: "fractional discount to VWAP required to enter"}
presets:
  short: {window: 20, entry_discount: 0.01}
  medium: {window: 20, entry_discount: 0.02}
  long: {window: 60, entry_discount: 0.05}
---
# Rolling VWAP Reversion

## What it is
Buy a discount to volume-weighted average price; exit on reversion to it.

## What it looks for
Deviation from the price at which volume actually transacted.

## Equation
```
TP_t   = (H_t + L_t + c_t)/3                          # typical price
VWAP_t = sum(TP_i * V_i, i in window) / sum(V_i, i in window)
enter if c_t < VWAP_t * (1 - discount) ;  exit if c_t >= VWAP_t
```

## Implementation
`backtester/core/strategies/signals.py::VwapReversion`.

## Parameters
- **entry_discount** — 1% hourly, 2% daily, 5% for the slow scale. This is the only
  parameter that decides how often the strategy trades at all.

## Works when
Short-horizon reversion toward a volume-weighted anchor.

## Fails when
Trending markets. Note this is **rolling**, not session-anchored: crypto has no session
open, so this is a fair-value-deviation signal rather than the execution benchmark VWAP
normally serves as. That is a meaningful reinterpretation of the indicator, not a
detail.

## Backtest notes
A zero-volume window must fall back to an unweighted mean rather than dividing by zero.
Exchange-reported crypto volume is unreliable across venues; single-venue volume, as
used here, is at least internally consistent.

## Pairs with
`obv_trend`, to distinguish a discount being accumulated from one being distributed —
`all(vwap_reversion + obv_trend)` measured **OOS +0.186** at the long horizon.

## Measured on SOL
Medium: **OOS -53.9%** (Sharpe -0.532) on 23 OOS trades. Short: **OOS Sharpe -1.516**.
Consistently among the worst measured rows in the sweep.

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
- Volume quality is the hidden variable. A signal built on unreliable volume inherits
  that unreliability and no backtest here can detect it.
- "Rolling VWAP" is not what most literature means by VWAP. Do not import intraday
  session-VWAP intuitions.

## How to run
```bash
python3 -m backtester.cli --strategy vwap_reversion --interval 1d
```
