---
id: atr_position_sizing
name: ATR-Normalised Position Sizing
kind: exposure-strategy
status: measured
family: risk-overlay
summary: Trend entry sized so one ATR of adverse move costs a fixed fraction of equity.
registry_key: atr_sized
runner: backtester.cli
warmup_bars: 101
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  atr_period: {default: 14, type: int, desc: "Wilder ATR period"}
  risk_per_trade: {default: 0.01, type: float, desc: "fraction of equity risked per stop distance"}
  stop_atr_multiple: {default: 2.0, type: float, desc: "stop distance in ATRs"}
  trend_window: {default: 100, type: int, desc: "SMA window for the trend gate"}
presets:
  short: {atr_period: 7, trend_window: 168}
  medium: {atr_period: 14, trend_window: 100}
  long: {atr_period: 30, trend_window: 200}
---
# ATR-Normalised Position Sizing

> **Implemented in this session** from spec-only mechanism #28 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
# ATR-Normalised Position Sizing

## What it is
A risk overlay, not a signal. Exposure is set so that `stop_atr_multiple` ATRs of
adverse movement costs `risk_per_trade` of the account.

## Equation
```
ATR_t          = Wilder smoothing of true range, period p
stop_fraction  = stop_atr_multiple * ATR_t / price
target_t       = min(1, risk_per_trade / stop_fraction)   if c_t > SMA(trend) else 0
```

## What this harness cannot model, stated plainly
**A real ATR stop exits intrabar at a price. Exposure here changes only at bar
boundaries**, so `stop_atr_multiple` sizes the position and never triggers an exit.
Any comparison against a stop-based system elsewhere therefore flatters that system.
The sizing half is what was measured; the stop half was not.

## Implementation
`backtester/core/strategies/advanced.py::AtrSizedTrend`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +5.8% | 0.377 | — |
| **Out-of-sample** | **-2.6%** | **-0.454** | **93** |

For reference on the same split: buy-and-hold made **+565.2% (Sharpe 1.030)**
in-sample and **-70.8% (Sharpe -0.651)** out. That row reproduces the figure the
existing cards document exactly, which is how these new numbers are known to be
comparable to them.


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

*Basis: measured-oos.*

**The smallest losses in the directory, in both legs** (+5.8% IS, -2.6% OOS) — and
that is the point rather than a disappointment. With `risk_per_trade` at 1% and SOL's
ATR, the sizing rule holds a very small position: it is risk-normalising, so on a
high-volatility asset it normalises down to near-nothing.

That makes this the one card whose *shape* behaved as designed. It did not lose much
because it was barely exposed, on 93 trades, which is the honest description of a
constant-risk rule applied to an asset far more volatile than the target implies.

Rated low, not very-low, because the mechanism is sound and untested in the
configuration that matters: as a **wrapper around a signal with an edge**. It has no
edge of its own and does not claim one — pairing it with something directional is the
open experiment, exactly as with `voltarget.md`.

## Caveats and limitations
- The stop is not modelled. Do not read this as a test of ATR stops.
- At 1% risk per trade the position is small enough that transaction costs dominate
  the result; 93 trades at 8 bps is meaningful against a 5.8% gross.
- Sizing on trailing ATR de-risks after volatility has already arrived.

## How to run
```bash
python3 -m backtester.cli --strategy atr_sized --interval 1d
```
