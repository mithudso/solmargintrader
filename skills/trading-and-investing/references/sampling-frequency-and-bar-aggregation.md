---
name: sampling-frequency-and-bar-aggregation
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-2 re-expansion, CVS 4.05, promoted by its own empirical finding
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  How often you sample the market, and why that choice moves results more than
  most signal rules do. Covers what sampling frequency actually controls
  (signal-to-noise, indicator lag, trade count and therefore fee drag), the
  indicator-period/bar-interval coupling that makes a period number meaningless
  on its own, aliasing and why a faster feed is not a better one, the
  measured evidence that frequency choice dominated parameter selection on SOL,
  bar-type alternatives (time vs tick/volume/dollar bars) with a pointer to the
  ML treatment, and how to choose a frequency without fitting it. Educational
  only — NOT financial advice.
keywords:
  - sampling frequency
  - bar interval
  - timeframe selection
  - bar aggregation
  - resampling
  - time bars
  - tick bars
  - volume bars
  - dollar bars
  - information bars
  - aliasing
  - signal to noise
  - indicator period
  - multi-timeframe
  - fee drag
tags:
  - trading-and-investing
  - backtesting
  - time-series
  - quantitative
  - risk
---

# Sampling Frequency and Bar Aggregation

> **Educational information only — NOT financial, investment, or tax advice.**

Sampling frequency is the most under-examined parameter in retail strategy design. It is usually
picked by habit — "I trade the 1-hour" — then held fixed while enormous effort goes into tuning the
signal rule on top of it. The measured evidence in §4 says that is backwards.

**Scope.**

| For… | Go to |
|---|---|
| Alternative bar *types* in depth (information bars, fractional differentiation, PIT normalization) | `references/ai-and-ml-for-trading.md` |
| Indicator definitions and their period parameters | `references/technical-analysis.md` |
| Backtesting methodology, walk-forward, multiple testing | `references/trading-strategies-and-styles.md` §5 |
| The *other* silently-inherited parameters — walk-forward window and refit cadence | `references/walk-forward-window-length-and-refit-cadence.md` |
| Regime detection (whose detectors are all window-dependent) | `references/regime-detection-and-classification.md` |
| Fee drag arithmetic on high-frequency strategies | `references/grid-trading-strategy.md` §4 |
| Whether bar resolution changes *fill realism* (it barely does) | `references/empirical-backtest-findings-log.md` §9.3 |

## Contents

1. What sampling frequency actually controls
2. The indicator-period / bar-interval coupling
3. Aliasing — why a faster feed is not a better one
4. Measured: frequency dominated signal tuning on SOL
5. Bar types — time, tick, volume, dollar
6. Choosing a frequency without fitting it
7. Anti-patterns

---

## 1. What sampling frequency actually controls

Choosing a bar interval simultaneously sets four things. They are usually reasoned about separately,
which is why the choice goes wrong.

| It controls | Faster sampling → | Slower sampling → |
|---|---|---|
| **Signal-to-noise** | more microstructure noise per observation | more signal per observation, fewer observations |
| **Indicator lag** | reacts sooner, whipsaws more | reacts later, gives back more at turns |
| **Trade count** | more trades → **more fee drag** | fewer trades, each larger |
| **Sample size** | more bars to fit on (and to overfit on) | fewer bars, wider error bars |

**The fee-drag coupling is the one that quietly decides viability.** Doubling sampling frequency
roughly doubles signal crossings and therefore trade count, while the edge per trade does not double.
This is the same arithmetic that kills over-dense grids (`grid-trading-strategy.md` §4) — a strategy
can be *directionally correct more often* at a faster sampling rate and still lose money net of costs.

**Sample size cuts both ways.** More bars looks like more statistical power, and for estimating
volatility it is. For estimating *edge*, faster bars mostly add noise observations, and they inflate
apparent significance because the observations are heavily autocorrelated — 43,000 1-minute bars are
nowhere near 43,000 independent observations.

## 2. The indicator-period / bar-interval coupling

**An indicator period is meaningless without its bar interval.** "EMA(24)" is not a specification. On
1-minute bars it is a 24-minute average; on 4-hour bars it is a 4-day average. These are different
strategies wearing the same number.

This produces a common and expensive confusion: someone tunes `fast`/`slow` extensively, holds the
bar interval fixed by habit, and concludes the strategy is bad — when the interval was the binding
constraint the whole time. §4 is exactly that story, measured.

**The practical consequence:** *lookback in wall-clock time* is the quantity with economic meaning,
and it equals `period × bar_interval`. Two configurations with the same wall-clock lookback but
different (period, interval) splits are close substitutes; two with the same period and different
intervals are not comparable at all. **Sweep the interval alongside the period, or you are sweeping
one dimension of a two-dimensional surface.**

## 3. Aliasing — why a faster feed is not a better one

Sampling a continuous process at interval Δ cannot represent variation faster than ~2Δ; faster
variation does not vanish, it **folds back into the sampled series as spurious low-frequency
structure**. That is aliasing, and it is why "use the highest-resolution data available" is not
automatically right.

Practically, on fast bars a strategy increasingly trades **market microstructure** — bid-ask bounce,
queue dynamics, individual large orders — rather than the price process it was designed for. The
signal it was built to capture may simply not exist at that timescale, while the noise certainly does.

**The corollary that matters for backtesting:** using 1-minute data does not make a daily-horizon
strategy more accurate. It makes it slower to run and adds noise the strategy will happily fit.
Match data resolution to the *decision* horizon, not to what you happen to have downloaded. (Distinct
from *fill realism*, where finer data barely mattered at all — see
`references/empirical-backtest-findings-log.md` §9.3.)

## 4. Measured: frequency dominated signal tuning on SOL

**The evidence that promoted this topic.** An EMA-crossover trend strategy on SOL, identical signal
rule, varying only sampling frequency:

| Sampling | Bear month (2022-01) | Neutral month (2026-07) |
|---|---|---|
| ~hourly | **−19.2%** | **−10.5%** |
| ~4-hourly | **+34.8%** | **+3.1%** |

**A swing of more than 50 percentage points in the bear month, from sampling frequency alone**, with
the signal rule untouched. No `fast`/`slow` tuning at hourly sampling recovered anything close.

**The walk-forward confirms it is not a fluke of those two months.** Over **48 out-of-sample months**
(60 months of 1h SOL bars, 27 configs, 12-month rolling selection window):

> **Hourly sampling was selected in 0 of 48 months.** Selection chose ~4-hourly in 54% of months and
> daily in 46%. Not once did the fastest available sampling win.

Two further observations from the same run: `fast=24` was chosen in **1 of 48** months while `fast=12`
and `fast=48` split the remainder almost evenly — the response surface is **bimodal**, so a mid-range
default can sit in a dead zone; and the winning configuration changed in **36%** of month transitions,
so even a well-chosen frequency is not stable.

**Honest scope:** one asset, one signal family, 48 OOS months. This does **not** establish that 4-hour
sampling is correct in general — it establishes that *frequency was the dominant parameter here*, that
the fastest option was consistently the worst, and that it deserves to be swept rather than assumed.
Full method and caveats: `references/empirical-backtest-findings-log.md` §9.5–§9.6.

## 5. Bar types — time, tick, volume, dollar

Time bars are the default and the least statistically well-behaved, because **market activity is not
uniform in time**. A 1-hour bar covers wildly different amounts of trading depending on session,
weekday, and news.

| Bar type | New bar every… | Property |
|---|---|---|
| **Time** | fixed clock interval | Familiar; samples quiet periods as heavily as active ones |
| **Tick** | N transactions | Samples by activity, not clock |
| **Volume** | N units traded | Closer to constant information per bar |
| **Dollar** | N notional traded | Robust to price level changing over long histories |

Activity-based bars generally produce returns closer to IID with better statistical properties than
time bars. **Crypto sharpens the argument**, because 24/7 trading has no session structure to make
clock time meaningful — a "daily" crypto bar is a pure convention with no open or close behind it.

Depth on information-driven bars, fractional differentiation and PIT normalization lives in
`references/ai-and-ml-for-trading.md`; this section exists to make the *choice* visible rather than to
re-derive the constructions.

## 6. Choosing a frequency without fitting it

1. **Start from the decision horizon, not the data.** How long do you intend to hold? Sample so that a
   typical holding period spans a meaningful number of bars — a handful, not hundreds and not two.
2. **Sweep it as a first-class parameter**, alongside signal periods, and report results *by
   frequency*. If your sweep holds the interval fixed you have not swept the important axis (§2).
3. **Check the fee-drag budget at each frequency** before comparing returns: expected trades per month
   × round-trip cost. A frequency whose costs exceed its gross edge is disqualified regardless of
   backtest return (§1).
4. **Prefer the slowest frequency that still captures the effect.** Slower means fewer trades, less
   fee drag, less overfitting surface, and less exposure to microstructure you did not model.
5. **Validate out-of-sample, treating frequency as part of what was selected.** It is a fitted
   parameter and carries the same multiple-testing cost as any other
   (`trading-strategies-and-styles.md` §5).
6. **Sanity-check against a neighbouring frequency.** If your result collapses when you move from 4h
   to 2h or 8h, you have fitted a knife edge, not found an effect.

## 7. Anti-patterns

1. **Quoting an indicator period without its bar interval.** "EMA(24)" specifies nothing (§2).
2. **Holding the interval fixed while tuning the signal.** The dominant axis, unswept — the exact
   error §4 documents at a 50-point cost.
3. **Assuming higher resolution is more accurate.** For fills it barely helped (§9.3 of the synergy
   spoke); for signals it can actively hurt via aliasing (§3).
4. **Treating N bars as N independent observations.** Heavily autocorrelated; significance is inflated.
5. **Comparing strategies across different intervals without normalising wall-clock lookback.** Not a
   like-for-like comparison.
6. **Ignoring that faster sampling multiplies fee drag**, and comparing gross returns across
   frequencies as though costs were constant.
7. **Picking a mid-range default because it feels safe.** The surface can be bimodal — the middle was
   the dead zone here (§4).
8. **Using clock-based daily bars in crypto without noting the convention.** There is no session; the
   boundary is arbitrary.

## References

Internal: `references/ai-and-ml-for-trading.md` (information bars, fractional differentiation, PIT
normalization); `references/technical-analysis.md` (indicator periods);
`references/trading-strategies-and-styles.md` §5 (backtesting, multiple testing);
`references/grid-trading-strategy.md` §4 (fee-drag arithmetic);
`references/regime-detection-and-classification.md` (window dependence of every detector);
`references/empirical-backtest-findings-log.md` §9.3, §9.5–§9.6 (fill realism; the frequency
finding and its walk-forward).

**Evidence note.** The §4 numbers are **first-party measurements** produced in this repo — reproduce
with `~/Downloads/sol-backtest-data/_scripts/run_book_sweep.py` and `run_walkforward.py` against the
SOL dataset. They are **one asset and one signal family**, so they establish that frequency mattered
enormously *here* and deserves to be swept, not that any particular frequency generalises. The
conceptual material (aliasing, activity-based bar types, autocorrelation inflating significance) is
standard time-series and market-microstructure reasoning; the bar-type constructions are treated
properly in the ML spoke rather than re-derived here. **No performance claim in this reference should
be read as an expected return.**
