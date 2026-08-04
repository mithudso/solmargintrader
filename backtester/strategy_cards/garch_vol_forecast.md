---
id: garch_vol_forecast
name: EWMA / GARCH(1,1) Vol-Targeted Trend
kind: exposure-strategy
status: measured
family: risk-overlay
summary: Vol-targeted trend using an EWMA variance forecast instead of a trailing stdev.
registry_key: garch_voltarget
runner: backtester.cli
warmup_bars: 101
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  lam: {default: 0.94, type: float, desc: "EWMA decay; the GARCH(1,1) case omega=0, alpha=1-lam, beta=lam"}
  target_vol: {default: 0.6, type: float, desc: "annualised volatility target, decimal"}
  trend_window: {default: 100, type: int, desc: "SMA window for the trend gate"}
presets:
  short: {lam: 0.94, target_vol: 0.8, trend_window: 168}
  medium: {lam: 0.94, target_vol: 0.6, trend_window: 100}
  long: {lam: 0.97, target_vol: 0.6, trend_window: 200}
---
# EWMA / GARCH(1,1) Vol-Targeted Trend

> **Implemented in this session** from spec-only mechanism #29 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
# EWMA / GARCH(1,1) Vol-Targeted Trend

## What it is
`voltarget.md` with a variance *forecast* in place of a trailing estimate.

## Equation
```
sigma2_t = (1-lam) * r2_{t-1} + lam * sigma2_{t-1}       # GARCH(1,1), omega=0
target_t = min(1, target_vol / sigma_t)   if c_t > SMA(trend_window) else 0
```

## Why fixed lambda rather than fitted GARCH
`lam = 0.94` is the RiskMetrics convention and corresponds to
`alpha = 0.06, beta = 0.94`. Fitted GARCH coefficients are unstable on short samples,
and refitting every bar is both slow and an invitation to look-ahead. The fitted
version stays open work; this is the special case that needs no optimiser.

## Implementation
`backtester/core/strategies/advanced.py::GarchVolTarget`, using the new
`indicators.ewma_vol`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +18.9% | 0.321 | — |
| **Out-of-sample** | **-30.8%** | **-0.551** | **50** |

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

## Likelihood of success: very-low

*Basis: measured-oos.*

The forecast did not help. **-30.8% out-of-sample against `voltarget.md`'s -31.1%** —
the two are the same result to within a third of a percentage point, on 50 trades
against 73. Anticipating volatility clustering rather than measuring it after the
fact changed the trade count and almost nothing else.

That is informative: it says the lag in the volatility estimate was **not** what made
vol-targeted trend-following lose on SOL. The direction call was, and both cards
share the same crude SMA trend gate. Replacing the variance model was the wrong
repair.

## Caveats and limitations
- A variance forecast is not a return forecast. This changes sizing, never direction.
- `lam` fixed at the RiskMetrics value, unswept. A fitted GARCH may behave
  differently, and this card does not speak to it.
- Shares the trend gate with `voltarget.md`, so the two are not independent evidence.

## How to run
```bash
python3 -m backtester.cli --strategy garch_voltarget --interval 1d
```
