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
evaluation: cpcv-8-groups-k2
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  adx_period: {default: 14, type: int, desc: "Wilder ADX period"}
  adx_threshold: {default: 25.0, type: float, desc: "ADX level above which the market counts as trending"}
presets:
  short: {adx_period: 7, adx_threshold: 25.0}
  medium: {adx_period: 14, adx_threshold: 25.0}
  long: {adx_period: 30, adx_threshold: 25.0}
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

## Re-evaluated under CPCV

Combinatorial purged cross-validation (`core/cpcv.py`), 8 groups, k=2, on the same
1,875 daily bars — 28 out-of-sample paths where the series allows, instead of one
arbitrary split. Full run for all 25 registered configurations:
`research/results/cpcv_all25_sol_doge_zec_1d.csv` (SOL column; this replaced
`cpcv_all25_1d.csv`, deleted 2026-08-05 because it carried one long-horizon `sma_regime` row
in an otherwise medium-horizon file — this card's figures are unaffected, since 24 of the 25
rows were identical and none of them is `sma_regime`).

| Statistic | adx_trend | buy_and_hold |
|---|---|---|
| Median path Sharpe | +0.336 | +0.534 |
| Q1 path Sharpe | −0.603 | −0.095 |
| Paths with positive Sharpe | 71% | 68% |
| Median path return | +7.0% | +9.4% |
| Total trades | 44 | 16 |

**The single-split figure was unrepresentative, exactly as that split's critics
predicted.** One split gave −43.6% on 8 unrankable trades; 21 CPCV paths give a
*positive* median Sharpe of +0.336, 71% of paths positive and a +7.0% median return on
44 trades.

The rating stays **low** rather than rising, because the Q1 path Sharpe is **−0.603** —
the conservative quarter of regime mixes still loses meaningfully, and the interquartile
spread of 2.368 is the widest of any configuration measured. That is the signature of a
result that depends heavily on which regime you land in, which is the opposite of
robustness even when the median looks respectable.

## Cross-asset transfer and parameter stability (2026-08-05)

Run because this is the **only configuration in the repository that clears both the Deflated
Sharpe haircut and the evidence floor** — `research/dso_audit.py` flagged it, on ZEC.

### It transfers in sign across every daily asset

`adx_trend`, unchanged at the medium preset, on all five coins with a daily history:

| Asset | Median path Sharpe | Q1 | % paths + | Median return | Trades | Clears its own DSR benchmark? |
| --- | --- | --- | --- | --- | --- | --- |
| **ZEC** | **+1.037** | **+0.371** | 81% | +50.3% | 60 | **yes — DSR 0.571** |
| BTC | +0.575 | +0.130 | 86% | +15.1% | 50 | no (0.321, benchmark +0.987) |
| ETH | +0.495 | +0.281 | 76% | +15.0% | 52 | no (0.289) |
| SOL | +0.336 | −0.603 | 71% | +7.0% | 44 | no (0.267) |
| DOGE | +0.188 | −0.721 | 67% | −7.3% | 54 | no (0.214) |

**Five of five daily assets have a positive median**, and three of five have a positive Q1. That is a
different kind of evidence from the DSR: the DSR asks whether one magnitude beats a search benchmark,
while sign consistency across assets asks whether the mechanism shows up at all outside the series it
was found on. Both are worth having, and this is the only strategy here to pass the second.

**Do not read the five as five independent trials.** BTC, ETH, SOL and DOGE are strongly correlated
crypto majors; they are closer to one observation than four. ZEC is the least correlated of the five —
and is also the only one whose magnitude clears its benchmark, which cuts both ways (see below).

### The parameters are a plateau, not a spike

`python3 research/perturb.py --horizon medium --single adx_trend --asset ZEC`

| Variant | Median | Δ |
| --- | --- | --- |
| baseline | +1.037 | — |
| `adx_period` 14→15 | +0.883 | −0.154 |
| `adx_threshold` 25→27.5 | +0.692 | −0.345 |
| `adx_period` 14→13 | +0.639 | −0.398 |
| `adx_threshold` 25→22.5 | +0.614 | −0.423 |

**Zero of seven perturbations flip the sign**, and every variant stays above +0.61. Max
|Δ median Sharpe| is 0.423 against a baseline path IQR of 1.743, a ratio of 0.24. Verdict: STABLE.
For contrast the same test on SOL flips 1 of 7. So the ZEC figure is not a knife-edge parameter fit.

### What still argues against it

1. **It does not survive a timeframe change.** On SOL hourly the same configuration posts a median
   path Sharpe of **−3.736** with **4.8% of paths positive** on 680 trades. Whatever it captures on
   daily bars is absent or inverted at one hour. No hourly history exists for ZEC to test whether
   that is a SOL effect or a timeframe effect — **this is the open question**, and until it is
   answered the daily result rests on one interval.
2. **A trend filter on the one asset with a big sustained trend is the obvious alternative
   explanation.** ADX gates for trend strength, so a single long ZEC trend inside 2,043 bars would
   produce exactly this table. That ZEC is simultaneously the best performer and the least correlated
   asset is consistent with genuine diversification *and* with a single lucky regime.
3. **DSR 0.571 is barely above the 0.5 coin-flip line.** It means roughly a 57% probability the true
   Sharpe exceeds the search's own benchmark. It is the absence of disconfirmation, not a result.
4. **One asset, one history, no live order ever placed.**

**It is not just beta.** On ZEC it beats buy-and-hold on Sharpe (+1.037 vs +0.659), on Q1 (+0.371 vs
+0.151) and on return (+50.3% vs +20.2%), at similar path-positive rates (81% vs 82%). It ranks 1 of
25 on ZEC.

**Rating unchanged at `low`.** Passing three tests that most configurations fail is the strongest
evidence in this repository, and it is still one asset on one timeframe with a DSR a whisker over a
coin flip. The rating moves when an hourly ZEC history, or a second uncorrelated asset, agrees.

## Caveats and limitations
- ADX > 25 is a convention, not a constant. It is a parameter and was not swept.
- ADX is lagging by construction, so it can confirm a trend that is ending.
- 8 trades. Any statement stronger than "unproven" is unsupported.

## How to run
```bash
python3 -m backtester.cli --strategy adx_trend --interval 1d
```
