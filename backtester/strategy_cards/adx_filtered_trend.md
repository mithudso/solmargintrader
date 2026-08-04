---
id: adx_filtered_trend
name: ADX-Filtered Trend
kind: exposure-strategy
status: measured
family: regime-filter
summary: Long only while a directional trend is both present (ADX) and up (+DI > -DI).
registry_key: adx_trend
runner: backtester.cli
warmup_bars: 43
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  adx_period: {default: 14, type: int, desc: "Wilder ADX period"}
  adx_threshold: {default: 25.0, type: float, desc: "ADX level above which the market counts as trending"}
presets: {}
---
# ADX-Filtered Trend

> **Implemented in this session** from spec-only mechanism #20 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
## What it is
Direction from `+DI > -DI`, gated on strength from `ADX > threshold`.

## Equation
```
+DM_t = H_t - H_{t-1}  if positive and > (L_{t-1} - L_t), else 0
-DM_t = L_{t-1} - L_t  if positive and > (H_t - H_{t-1}), else 0
+DI = 100 * WilderSmooth(+DM)/ATR ;  -DI = 100 * WilderSmooth(-DM)/ATR
DX  = 100 * |+DI - -DI| / (+DI + -DI)
ADX = WilderSmooth(DX)
target_t = 1 if ADX > threshold and +DI > -DI else 0
```

## Implementation
`backtester/core/strategies/advanced.py::AdxFilteredTrend`, using the new
`indicators.directional_movement`. Warmup is `3 x adx_period + 1` because ADX is a
Wilder smoothing of DX, itself built from smoothed DM and ATR — three nested
recursions deep, and getting that wrong would let it trade on an unsettled estimate.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +1,644.3% | 1.618 | — |
| **Out-of-sample** | **-43.6%** | **-1.165** | **8** |

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

Two things keep this above very-low. First, **8 out-of-sample trades is below the
10-trade evidence floor**, so -43.6% is listed rather than ranked — the sample cannot
carry a verdict either way. Second, the gate did what it was built to do: it traded
eight times where an ungated trend rule traded far more, which is the selectivity
that was the point.

What it did not do is make money, and its in-sample +1,644.3% is the second-largest
figure in the whole study — a decay profile that should be read as a warning rather
than a promise. The mechanism attacks the right failure (chop) with the conventional
tool; on this split it still lost.

## Caveats and limitations
- ADX > 25 is a convention, not a constant. It is a parameter and was not swept.
- ADX is lagging by construction, so it can confirm a trend that is ending.
- 8 trades. Any statement stronger than "unproven" is unsupported.

## How to run
```bash
python3 -m backtester.cli --strategy adx_trend --interval 1d
```
