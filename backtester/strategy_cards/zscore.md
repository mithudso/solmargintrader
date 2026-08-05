---
id: zscore
name: Z-Score Mean-Reversion
kind: exposure-strategy
status: measured
family: mean-reversion
summary: Buy when price is z sample-stdevs below its trailing mean. Top-ranked medium single, at the evidence floor.
registry_key: zscore
runner: backtester.cli
warmup_bars: 20
evaluation: cpcv-8-groups-k2
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  window: {default: 20, type: int, desc: "trailing window for mean and stdev"}
  entry_z: {default: -2.0, type: float, desc: "z-score at or below which to enter"}
  exit_z: {default: 0.0, type: float, desc: "z-score at or above which to exit"}
presets:
  short: {window: 20, entry_z: -2.0}
  medium: {window: 20, entry_z: -2.0}
  long: {window: 60, entry_z: -2.0}
---
# Z-Score Mean-Reversion

## What it is
Buy when price sits *z* sample standard deviations below its trailing mean.

## What it looks for
Normalised distance from fair value — the same construction used for cointegration
spreads, applied here to raw price.

## Equation
```
z_t = (c_t - mean(c_{t-n+1..t})) / stdev_sample(c_{t-n+1..t})     # ddof=1
enter if z_t <= entry_z ;  exit if z_t >= exit_z
```

## Implementation
`backtester/core/strategies/signals.py::ZScoreReversion`.

## Read this together with bb_reversion
`bb_reversion.md` is **the same inequality** at a 2.6% different threshold (ddof=0 vs
ddof=1). Treat them as one mechanism when reasoning about diversification.

Measured bar by bar at the shipped presets: exposure differs on **0 of 1,875 BTC daily
bars**, 30 (1.60%) on SOL and 16 (0.85%) on ETH. On BTC they are literally the same
strategy. Full table and the reasoning in `bb_reversion.md`; the relationship is pinned by
`tests/test_strategy_duplication.py`.

## Works when
Stationary or range-bound series. **Raw price is not stationary**, which is this card's
central theoretical weakness: the technique properly applies to a *cointegrated spread*
whose stationarity has been tested. This is the degenerate single-asset case — see
`pairs_cointegration.md` for the rigorous version.

## Fails when
Trending markets, where the z-score simply keeps making new lows and the strategy keeps
buying them.

## Backtest notes
Zero-dispersion windows must return 0 rather than dividing by something near zero and
emitting a huge spurious score. Properly, test the series for stationarity (ADF) before
trusting this at all — which nothing here does.

## Pairs with
A regime filter (measured best-in-class); a breakout for the exit —
`any(breakout + zscore)` was the top medium pair.

## Measured on SOL
**Top-ranked medium single: OOS Sharpe +0.699, OOS return +41.3%** (IS -64.8%) on 10 OOS
trades — **exactly at the evidence floor**, so read it as "not yet disconfirmed" rather
than "works". Short: **OOS +0.441** on 48 trades.

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

The **top-ranked medium single** (OOS Sharpe +0.699, +41.3%) — on exactly **10
trades**, the evidence floor. `RANKED_LISTS.md` records a within-mechanism natural
experiment finding this row consistent with noise. Against it stands a known
theoretical error: the z-score assumes stationarity and raw price is not stationary.
Read as "not yet disconfirmed", never as "works".

## Re-evaluated under CPCV

Combinatorial purged cross-validation (`core/cpcv.py`), 8 groups, k=2, on the same
1,875 daily bars — 28 out-of-sample paths where the series allows, instead of one
arbitrary split. Full run for all 25 registered configurations:
`research/results/cpcv_all25_1d.csv`.

| Statistic | zscore | buy_and_hold |
|---|---|---|
| Median path Sharpe | +0.036 | +0.534 |
| Q1 path Sharpe | −0.539 | −0.095 |
| Paths with positive Sharpe | **52%** | 68% |
| Median path return | **−10.0%** | +9.4% |
| Total trades | 50 | 16 |

**Downgraded from low to very-low.** The single split made this the top-ranked medium
single (+0.699 Sharpe, +41.3%) on exactly 10 trades. Across 21 CPCV paths the median
Sharpe is **+0.036** — a coin flip, 52% of paths positive — and the median path
*loses 10%*.

`RANKED_LISTS.md` already suspected this row was noise on a within-mechanism test. CPCV
says so directly: the earlier figure was a property of where the split landed, not of
the mechanism. The theoretical objection stands unchanged — a stationarity-dependent
method applied to non-stationary raw price — and `ou_half_life_sizing.md` is what the
same idea looks like with the assumption actually tested.

## Caveats and limitations
- The top-ranked medium row rests on exactly 10 trades. `RANKED_LISTS.md` records that
  a within-mechanism natural experiment found this row consistent with noise.
- Applying a stationarity-dependent method to a non-stationary series is a known
  theoretical error, not a subtlety. The measured result does not repair it.

## How to run
```bash
python3 -m backtester.cli --strategy zscore --interval 1d
```
