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
evaluation: cpcv-8-groups-k2
data_required: [ohlcv]
data_available: true
success_likelihood: low
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

## Likelihood of success: low

*Basis: measured-oos. There is no 'high' rating in this scheme — across 311 rankable
configurations, 14% had a positive out-of-sample Sharpe and 9% made money.*

**+2,843.6% in-sample, the largest number in the sweep — and -34.9% out-of-sample.**
That single pair of figures is the strongest evidence in this directory that
full-sample band-breakout results on SOL are artefacts. The squeeze gate that might
add real information is off by default and was never swept, so even the interesting
half is unmeasured.

## Re-evaluated under CPCV

Combinatorial purged cross-validation (`core/cpcv.py`), 8 groups, k=2, on the same
1,875 daily bars — 28 out-of-sample paths where the series allows, instead of one
arbitrary split. Full run for all 25 registered configurations:
`research/results/cpcv_all25_sol_doge_zec_1d.csv` (SOL column; this replaced
`cpcv_all25_1d.csv`, deleted 2026-08-05 because it carried one long-horizon `sma_regime` row
in an otherwise medium-horizon file — this card's figures are unaffected, since 24 of the 25
rows were identical and none of them is `sma_regime`).

| Statistic | bb_breakout | buy_and_hold |
|---|---|---|
| Median path Sharpe | +0.481 | +0.534 |
| Q1 path Sharpe | −0.068 | −0.095 |
| Paths with positive Sharpe | 67% | 68% |
| Median path return | +15.9% | +9.4% |
| Total trades | 58 | 16 |

**Upgraded from very-low to low**, and this card is the cleanest illustration in the
directory of why the single split was condemned. That split produced the largest
in-sample figure in the study (+2,843.6%) and a −34.9% out-of-sample loss, which read as
a pure overfitting artifact. Across 21 CPCV paths it is **third of 25 by median path
Sharpe** with a **+15.9% median return** — better than holding the asset — on a
respectable 58 trades.

It stays at low, not moderate, for two reasons. Its Q1 is still slightly negative
(−0.068), so the conservative read is a small loss rather than a gain; and the squeeze
gate that supplies the mechanism's actual premise is **off by default and still never
swept**, so what was measured is a plain band breakout.

## Caveats and limitations
- The headline in-sample figure is a trap, not an achievement. It is included because
  deleting it would remove the most instructive number in the study.
- The squeeze gate — the part that might actually add information — is unmeasured.

## How to run
```bash
python3 -m backtester.cli --strategy bb_breakout --interval 1d
```
