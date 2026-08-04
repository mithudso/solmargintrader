---
id: ts_momentum
name: Time-Series Momentum
kind: exposure-strategy
status: measured
family: momentum
summary: Long when the trailing n-bar return is positive. The Moskowitz/Ooi/Pedersen time-series form.
registry_key: ts_momentum
runner: backtester.cli
warmup_bars: 61
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  window: {default: 60, type: int, desc: "formation window in bars"}
  threshold: {default: 0.0, type: float, desc: "minimum trailing return to go long"}
presets:
  short: {window: 24}
  medium: {window: 60}
  long: {window: 200}
---
# Time-Series Momentum

## What it is
Long when the trailing *n*-bar return is positive.

## What it looks for
The sign of past return predicting the next period. This is the **time-series** form
(Moskowitz, Ooi & Pedersen), distinct from **cross-sectional** momentum, which ranks a
universe and therefore needs peers this repo does not have — see
`xs_momentum.md`.

## Equation
```
ROC(n)_t = c_t / c_{t-n} - 1
target_t = 1 if ROC(n)_t > threshold else 0
```

## Implementation
`backtester/core/strategies/signals.py::TsMomentum`.

## Parameters
- **window** — 24 hourly, 60 daily and 200 daily behave like three different
  strategies. This is the parameter most worth *not* tuning on the data you report.
- **threshold** — 0.0 by default; raising it demands stronger drift before committing.

## Works when
Momentum is the most-documented anomaly family in the literature (Jegadeesh & Titman
1993: 3–12 month formation, 1-month hold in equities).

## Fails when
**Momentum crashes** — the family's defining risk. Sharp reversals arrive exactly when
the signal is most crowded, and a single-asset version has no cross-sectional
diversification to soften the blow.

## Backtest notes
Highly sensitive to the formation window. Do not tune the window on the same data you
report; that is the fastest route to a beautiful number that does not survive.

## Pairs with
A breakout for entry timing; an oscillator to avoid adding at exhaustion.

## Measured on SOL
Long (200): **IS +506.2% (Sharpe 1.098) -> OOS -77.2% (Sharpe -1.976)** — the worst
rankable long-horizon row. Medium (60): IS +392.8% -> OOS -51.1%.

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
- Single-asset momentum is the weakest form of a strong anomaly. The published edge
  comes largely from cross-sectional ranking, which is unavailable here.
- A -1.976 out-of-sample Sharpe on the slowest parameter set is consistent with the
  split landing on the top: a 200-bar formation window commits hardest, latest.

## How to run
```bash
python3 -m backtester.cli --strategy ts_momentum --interval 1d
```
