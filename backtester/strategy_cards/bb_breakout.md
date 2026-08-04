---
id: bb_breakout
name: Bollinger Band Breakout
kind: exposure-strategy
status: measured
family: breakout
summary: Long a close above the upper Bollinger band, with an optional volatility-squeeze pre-filter.
registry_key: bb_breakout
runner: backtester.cli
warmup_bars: 20
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  window: {default: 20, type: int, desc: "SMA and stdev window"}
  num_std: {default: 2.0, type: float, desc: "band width in population standard deviations"}
  squeeze_lookback: {default: 0, type: int, desc: "bars of bandwidth history for the squeeze gate; 0 disables it"}
  squeeze_quantile: {default: 0.25, type: float, desc: "bandwidth quantile below which a squeeze is declared"}
presets:
  short: {window: 20, num_std: 2.0}
  medium: {window: 20, num_std: 2.0}
  long: {window: 60, num_std: 2.0}
---
# Bollinger Band Breakout

## What it is
Long a close above the upper band, optionally only after a volatility contraction.

## What it looks for
Statistically unusual strength — and with the squeeze gate on, strength emerging from
quiet.

## Equation
```
mid_t       = SMA(n)_t
sd_t        = POPULATION stdev of last n closes (ddof=0)
upper_t     = mid_t + k*sd_t ;  lower_t = mid_t - k*sd_t
bandwidth_t = (upper_t - lower_t) / mid_t
enter if c_t > upper_t  [and bandwidth_t <= quantile(bandwidth history, q)]
exit  if c_t < mid_t
```

## Implementation
`backtester/core/strategies/signals.py::BollingerBreakout`.

## Parameters
- **window / num_std** — 20 and 2.0 are Bollinger's own conventions.
- **squeeze_lookback** — **0 by default, which disables the squeeze gate entirely**, and
  it was never swept. The gate is the interesting half of this mechanism and it is
  untested here. Treat any measured number below as describing plain band-breakout.
- **squeeze_quantile** — only meaningful when `squeeze_lookback > 0`.

## Works when
Expansion follows contraction. The squeeze gate is the mechanism that tries to select
for exactly that.

## Fails when
Volatility is already elevated, so the band is wide and a breach means little. Also
vulnerable to gaps: a gap compresses close-to-close stdev while *actual* risk rises,
which is precisely the failure Keltner's ATR basis avoids.

## Backtest notes
Bollinger specified the **population** standard deviation (ddof=0), and charting
packages follow him. A ddof=1 implementation will not match published values — and note
that the z-score card deliberately uses ddof=1, which is the only thing separating the
two mechanisms. See `zscore.md`.

## Pairs with
The built-in squeeze filter (off by default); volume confirmation; a trend filter for
direction.

## Measured on SOL
Medium: **IS +2,843.6% (Sharpe 1.837) -> OOS -34.9% (Sharpe -0.841)**.
**This is the largest in-sample number in the entire sweep, and it lost money
out-of-sample.** If you read one row in this directory as a warning about full-sample
leaderboards, read this one.

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

**+2,843.6% in-sample, the largest number in the sweep — and -34.9% out-of-sample.**
That single pair of figures is the strongest evidence in this directory that
full-sample band-breakout results on SOL are artefacts. The squeeze gate that might
add real information is off by default and was never swept, so even the interesting
half is unmeasured.

## Caveats and limitations
- The headline in-sample figure is a trap, not an achievement. It is included because
  deleting it would remove the most instructive number in the study.
- The squeeze gate — the part that might actually add information — is unmeasured.

## How to run
```bash
python3 -m backtester.cli --strategy bb_breakout --interval 1d
```
