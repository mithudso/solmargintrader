# SOL Strategy & Signal Rankings — Three Lists

**AS OF 2026-08-04.** Data runs through 2026-08-04; every figure is tied to that snapshot.
**Primary evaluation method: combinatorial purged cross-validation (CPCV)** — 8 blocks, k=2,
28 paths per configuration. The earlier single 70/30 walk-forward is retained as List 1b,
because the disagreement between the two methods is the most instructive result here.

> **Historical simulation for research and education only. NOT investment advice**, and not a
> recommendation to trade anything. Simulated past performance does not predict future results.
> Every number below came from an executed run and can be reproduced with
> `python3 research/cpcv_sweep.py` and `python3 research/sweep.py`. No figure in this document
> was estimated; `python3 research/verify_numbers.py` enforces that mechanically.

**Method note.** The request asked for a `/dr` (deep-research) pass. Subagent fan-out is
unavailable in this environment, so the taxonomy is grounded in the local citation-backed
corpus (`~/.claude/skills/trading-and-investing/references/`, ~620 KB across 14 references)
plus first-hand measurement on real SOL data. That is a deliberate substitution, stated here
rather than made silently. Literature figures are attributed; everything else is measured.

---

## Read this before the tables

**Under CPCV, over all 25 registered strategies: 75 singles + 1,002 pairs + 210 triples = 1,287
configurations, each across 28 paths.** At the short horizon **not one of the 25 singles has a
positive median path Sharpe**. At the daily horizons singles PBO is **0.700** — well above the
0.500 pure-noise line, so in-sample rank is anti-informative.

**Growing the search from 16 to 25 strategies raised PBO, and I measured how much of that is the
search rather than a coincident change.** The common CPCV block set shrank from 7 blocks to 6 when
the 250-bar-window strategies (OU, Hurst, vol-regime) were added, because they cannot warm up
before block 1 — so two variables moved together. Holding the block set fixed isolates them:

| | Medium | Long |
|---|---|---|
| 16 configs, 7 blocks (the earlier run) | 0.457 | 0.457 |
| 16 configs, **6 blocks** | 0.600 | 0.550 |
| **25 configs**, 6 blocks | **0.700** | **0.700** |
| **attributable to search size** | **+0.100** | **+0.150** |

So searching more configurations *does* raise the probability of backtest overfitting, which is
exactly what Harvey-Liu-Zhu and Bailey et al. predict — but it accounts for only a third to a half
of the move here. Reporting the whole 0.457 → 0.700 rise as a search effect would have been wrong.

**Under the earlier single split: 520 configurations, 311 rankable, 45 (14%) with a positive
out-of-sample Sharpe, 28 (9%) that made money.**

Six findings matter more than any ranking below. Findings 1/1b/1c are the method result — one
split cannot answer this question and PBO quantifies how little in-sample rank tells you.
Findings 2–4 were measured under the single split and are kept because the contrast is the
lesson; finding 4 in particular shows a top-ranked row is noise using a within-mechanism control
that needs no interpretation at all.

### 1. The split ends on the highest close in the series. One split cannot answer this.

| Leg | Daily (medium/long) | Hourly (short) |
|---|---|---|
| In-sample | 2021-06-17 → 2025-01-18, **\$39.25 → \$252.34 (+543%)** | 2025-08-01 → 2026-04-15, \$170.25 → \$83.66 (−51%) |
| Out-of-sample | 2025-01-19 → 2026-08-04, **\$252.34 → \$73.89 (−70.7%)** | 2026-04-15 → 2026-08-04, \$83.66 → \$73.00 (−13%) |

This is worse than "near the top". The **highest close in the entire 1,875-bar series is
\$261.99, on 2025-01-18 — bar 1311, the final bar of the in-sample window.** The split falls on
the very next bar. So a 70/30 split puts essentially the entire bull market in-sample and the
entire bear leg out-of-sample, and any long-biased strategy is *structurally required* to look
excellent in-sample and terrible out-of-sample regardless of predictive content. That column
measured **one regime**, not the future.

**This has now been replaced by CPCV.** Findings 2–4 below were measured under the old single
split and are retained because the contrast is the lesson; the CPCV rankings that supersede them
are in List 1, and they reorder almost completely.

### 1b. Under CPCV the ranking reorders completely, and buy-and-hold stays near the top.

The single split ranked `zscore_20_-2` first at the medium horizon (OOS Sharpe +0.699). Under CPCV
it falls far down the table, and the medium-horizon top two are `hurst_switch` (+0.699, 93% of
paths positive) and **`buy_and_hold` (+0.534)**. At the long horizon buy-and-hold is 3rd behind
`obv_trend_60` and `vol_regime`.

That buy-and-hold sits second and third across 25 strategies is the headline: *on this asset and
this history, holding the asset beat all but one or two of everything tested* — and the ones ahead
of it are separated by less than their own interquartile spread.

CPCV also made the long horizon answerable at all. Under the single split only **4 of 16**
long-horizon configurations cleared the evidence floor; under CPCV **all 25 are evaluable**,
because blocks reuse the whole series instead of one 563-bar tail.

### 1c. PBO says in-sample selection is anti-informative at the daily horizons.

Probability of Backtest Overfitting (Bailey et al., via CSCV), over all 25 strategies:

| Horizon | PBO | splits | configs |
|---|---|---|---|
| Short | **0.343** | 35 | 25 |
| Medium | **0.700** | 20 | 25 |
| Long | **0.700** | 20 | 25 |

Calibrated against constructed controls in the test suite: **pure noise gives mean PBO 0.500**
(over 30 seeds) and **a genuinely ordered signal set gives 0.000**. Both daily horizons sit at
0.700 — *above* the noise line, meaning selecting by in-sample performance is measurably worse
than picking at random. The earlier 16-strategy run measured 0.429 / 0.457 / 0.457; the
decomposition of that rise is in *Read this before the tables* above.

Short horizon needs the same care as any low PBO: 0.343 looks encouraging, but **0 of 25** singles
have a positive median Sharpe there, so in-sample rank generalises reliably as a loser. PBO
measures rank consistency, not profitability — always read it next to the positive count.

### 1d. The top pair survives parameter perturbation — which is a narrower result than it sounds

`all(dual_momentum+vol_regime)` is the best figure in this document (median Sharpe **+1.345**,
87% of paths positive, **+75.1%** median path return). It sits atop a 295-configuration search
whose PBO is 0.650, so the obvious question is whether the number is a property of the mechanism
or of the particular parameters someone picked. `research/perturb.py` answers that by nudging every
parameter ±10% one at a time and re-running the full CPCV evaluation.

**Result: 0 of 12 perturbations flip the sign, and the median never drops below +0.904.**

| Variant | Median Sharpe | Δ | % paths + |
|---|---|---|---|
| baseline | **+1.345** | — | 87% |
| `vol_window` 60→66 | +1.435 | +0.090 | 93% |
| `formation` 24→26 | +1.294 | −0.051 | 93% |
| `trend_window` 200→180 | +1.154 | −0.191 | 80% |
| `formation` 24→22 | +1.019 | −0.327 | 87% |
| `lookback` 250→225 | +0.954 | −0.392 | 71% |
| **geometry: 9 blocks** | **+0.904** | **−0.441** | 95% |

Two things worth noticing. **The largest single move comes from the CPCV geometry, not from any
strategy parameter** — changing 8 blocks to 9 moved the median more (−0.441) than the worst
parameter nudge did (−0.392). The result is more sensitive to how you slice the data than to the
strategy's own settings, which is not what you would guess.

And the sensitivity is **typical, not exceptional**. Measuring the same ratio (max |Δ| over the
baseline's own path IQR) across seven top long-horizon configurations gives 0.13–0.72 with a median
of 0.44. This pair scores 0.44 on parameters alone, 0.50 including geometry — squarely mid-pack:

| Configuration | median Sharpe | ratio | sign flips |
|---|---|---|---|
| `obv_trend` (single) | +0.774 | **0.13** | 0/2 |
| `all(macd+vol_regime)` | +0.991 | 0.30 | 0/12 |
| `any(ou_reversion+obv_trend)` | +1.054 | 0.38 | 0/8 |
| `all(dual_momentum+vol_regime)` | +1.345 | 0.44 | 0/9 |
| `vol_regime` (single) | +0.696 | 0.44 | 0/6 |
| `any(adx_trend+ou_reversion)` | +1.162 | 0.47 | 0/10 |
| `any(hurst_switch+ou_reversion)` | +0.965 | **0.72** | 0/12 |

**Across all seven configurations and 59 perturbations, not one flipped sign.**

> **What this does not establish.** Perturbation stability and multiple testing are *different
> failure modes*. This test asks whether the **parameters** were cherry-picked — answer: no more
> than typical. It cannot ask whether the **configuration** was cherry-picked from 295 candidates,
> and PBO 0.650 says that concern stands undiminished. A robust-under-perturbation row at the top
> of an anti-informative ranking is still a row selected by an anti-informative ranking. The
> honest summary: these numbers are not parameter artifacts, and that is not the same as saying
> they will hold out of sample.

Reproduce with:

```bash
python3 research/perturb.py --horizon long --pair dual_momentum vol_regime --mode all
python3 research/perturb.py --horizon medium --single hurst_switch
```

### 2. In-sample rank does not predict out-of-sample rank. At the medium horizon it inverts.

Spearman rank correlation between in-sample and out-of-sample Sharpe, across rankable configs:

| Slice | n | ρ(IS Sharpe, OOS Sharpe) |
|---|---|---|
| Short horizon | 164 | **−0.139** |
| Medium horizon | 109 | **−0.419** |
| Long horizon | 38 | +0.027 |
| Singles only | 30 | −0.052 |
| Pairs only | 247 | +0.247 |
| All | 311 | +0.116 |

At the medium horizon, picking the strategy that looked best in-sample was **actively worse
than choosing at random**. This is the Harvey-Liu-Zhu / Bailey-PBO problem observed directly
rather than cited: mean Sharpe fell from **+0.806 in-sample to −0.538 out-of-sample** (medium)
and **+0.879 to −0.689** (long). McLean & Pontiff measured 58% out-of-sample decay across 97
published factors; the decay here is larger, because a regime inversion sits on the boundary.

### 3. "Beat the baseline" is nearly meaningless when the baseline lost 71%.

Denominators here are **all rankable configurations at that horizon** — singles, pairs, and
triples pooled. (List 2's counts are pairs-only, so its denominators are smaller: 125/88/34.)

| Horizon | Baseline (buy & hold) OOS | Beat baseline | **Actually made money** |
|---|---|---|---|
| Short | −12.9% | 99/164 | **22/164** |
| Medium | −70.8% | 105/109 | **5/109** |
| Long | −70.8% | 29/38 | **1/38** |

105 of 109 medium-horizon configurations "beat buy-and-hold" — by losing less than 71%.
Five made money. Report the second number, not the first.

### 4. A within-mechanism natural experiment: the top medium-horizon row is noise

This is the strongest single piece of evidence here, and unlike finding 2 it needs **no regime
story at all**. Rows 1 and 2 of the medium-horizon table are, provably from source, *the same
mechanism* separated only by a standard-deviation convention — a **2.6% difference in entry
threshold** (see List 3 for the derivation):

| Configuration | OOS Sharpe | **OOS return** | OOS trades | OOS exposure |
|---|---|---|---|---|
| `zscore_20_-2` | +0.699 | **+41.3%** | 10 | 0.259 |
| `bb_reversion_20_2` | +0.193 | **−4.8%** | 10 | 0.298 |

**Identical trade count. A 46-percentage-point gap in outcome.** A trivial, economically
meaningless perturbation of one threshold flips the top-ranked medium-horizon strategy from
+41% to −5%. Whatever `zscore_20_-2`'s first-place ranking is measuring, it is not a property
of the mechanism.

The contrast completes the argument. Gate both with the regime filter and they become
**numerically identical** — `all(sma_regime+zscore)` and `all(sma_regime+bb_reversion)` both
score OOS Sharpe **+2.5721** on **+9.03%** over **18 trades**, matching to four decimal places,
because the gate suppresses exactly the bars where the threshold difference lived. Ungated, that
difference dominated the entire result.

**Practical rule this implies:** before believing any row in any of these tables, perturb its
parameters slightly and re-run. If the result moves materially, you measured noise. This
document does not do that systematically for all 520 configurations — it should, and that is
item 7 in *What to actually do next*.

### One hypothesis I tested and rejected

The top-ranked rows have small returns on high Sharpe (e.g. `all(sma_regime+zscore)`, OOS
Sharpe 2.572 on +9.0%), which suggested the ranking might just be measuring *how little you
were invested* during a downtrend. It is not: correlation between out-of-sample Sharpe and
out-of-sample exposure fraction is **−0.05 (short), −0.09 (medium), +0.26 (long), +0.02
overall** — essentially none. Sharpe and return agree closely instead (+0.79 to +0.84).
Recorded because the hypothesis was plausible and the data refused it.

---

# List 1 — Single strategies and signals, ranked (CPCV — primary)

Ranked on **median path Sharpe** across 28 CPCV paths (8 blocks, k=2), over **all 25 registered
strategies**. Three columns matter as much as the median: **IQR** (a median of +0.5 with IQR 1.4
straddles zero heavily), **% paths positive** (below ~70% means the sign depends on which regime
you sampled), and **trades**. Tables are generated from `research/results/cpcv_results.csv`; no
figure is transcribed by hand.

## Short horizon (1h bars) — CPCV

**Not one of the 25 has a positive median path Sharpe at this horizon.** The best, `stoch_14_3` at −0.341, still loses.

| # | Strategy | Family | Median Sharpe | IQR | % paths + | Median ret | Trades |
|---|---|---|---|---|---|---|---|
| 1 | `stoch_14_3` | oscillator-reversion | **-0.341** | 2.117 | 38% | -5.2% | 240 |
| 2 | `ou_reversion_250_2.5` | mean-reversion | **-0.595** | 1.333 | 33% | -3.4% | 196 |
| 3 | `keltner_12_7_2` | breakout | **-0.961** | 2.477 | 29% | -4.9% | 88 |
| 4 | `vol_regime_24_0.5` | regime-filter | **-1.048** | 1.677 | 19% | -8.8% | 290 |
| 5 | `zscore_20_-2` | mean-reversion | **-1.152** | 1.213 | 19% | -12.5% | 294 |
| 6 | `bb_reversion_20_2` | mean-reversion | **-1.316** | 1.396 | 14% | -15.4% | 308 |
| 7 | `buy_and_hold` | baseline | **-1.456** | 2.154 | 29% | -22.9% | 16 |
| 8 | `bb_breakout_20_2` | breakout | **-1.487** | 3.114 | 29% | -11.5% | 270 |
| 9 | `obv_trend_24` | volume-flow | **-1.580** | 1.668 | 24% | -18.0% | 852 |
| 10 | `rsi_7_30_55` | oscillator-reversion | **-1.723** | 1.052 | 14% | -19.8% | 328 |
| 11 | `ichimoku_9_26_52` | trend | **-1.877** | 1.174 | 0% | -18.6% | 392 |
| 12 | `breakout_12_6` | breakout | **-1.905** | 2.809 | 14% | -16.9% | 350 |
| 13 | `grid_48_4_0.03` | mean-reversion | **-2.022** | 0.731 | 0% | -12.4% | 4304 |
| 14 | `vwap_reversion_20_0.01` | mean-reversion | **-2.189** | 0.836 | 0% | -24.3% | 398 |
| 15 | `voltarget_168_24_0.8` | risk-overlay | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 16 | `sma_regime_168` | regime-filter | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 17 | `garch_voltarget_0.94_0.8` | risk-overlay | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 18 | `ma_crossover_12_48` | trend | **-2.385** | 3.326 | 10% | -23.5% | 204 |
| 19 | `atr_sized_7_0.01` | risk-overlay | **-2.548** | 2.298 | 5% | -12.4% | 3191 |
| 20 | `ts_momentum_24` | momentum | **-2.564** | 2.018 | 0% | -24.2% | 716 |
| 21 | `ma_ribbon_5x6` | trend | **-2.767** | 2.727 | 5% | -19.5% | 4572 |
| 22 | `macd_6_13_5` | trend | **-3.083** | 2.223 | 0% | -33.4% | 1156 |
| 23 | `hurst_switch_250_0.55_0.45` | regime-filter | **-3.123** | 2.107 | 14% | -12.8% | 170 |
| 24 | `adx_trend_7_25` | regime-filter | **-3.736** | 2.496 | 5% | -27.4% | 680 |
| 25 | `dual_momentum_24_2` | momentum | **-4.633** | 2.094 | 0% | -39.2% | 728 |

> 0 of 25 evaluable have a positive median. PBO **0.343** over 35 splits of 25 configurations (common blocks [1, 2, 3, 4, 5, 6, 7]).

## Medium horizon (1d bars) — CPCV

| # | Strategy | Family | Median Sharpe | IQR | % paths + | Median ret | Trades |
|---|---|---|---|---|---|---|---|
| 1 | `hurst_switch_250_0.55_0.45` | regime-filter | **+0.699** | 1.167 | 93% | +16.7% | 24 |
| 2 | `buy_and_hold` | baseline | **+0.534** | 1.434 | 68% | +9.4% | 16 |
| 3 | `bb_breakout_20_2` | breakout | **+0.481** | 1.694 | 67% | +15.9% | 58 |
| 4 | `ou_reversion_250_2.5` | mean-reversion | **+0.412** | 0.790 | 93% | +10.5% | 26 |
| 5 | `adx_trend_14_25` | regime-filter | **+0.336** | 2.368 | 71% | +7.0% | 44 |
| 6 | `macd_12_26_9` | trend | **+0.321** | 1.277 | 67% | +3.8% | 118 |
| 7 | `rsi_14_30_50` | oscillator-reversion | **+0.238** | 0.664 | 71% | -0.0% | 18 |
| 8 | `keltner_20_14_2` | breakout | **+0.213** | 1.656 | 76% | +2.2% | 38 |
| 9 | `obv_trend_20` | volume-flow | **+0.189** | 1.536 | 67% | -9.8% | 220 |
| 10 | `breakout_20_10` | breakout | **+0.078** | 1.911 | 52% | -6.4% | 52 |
| 11 | `zscore_20_-2` | mean-reversion | **+0.036** | 0.964 | 52% | -10.0% | 50 |
| 12 | `ts_momentum_60` | momentum | **+0.025** | 1.752 | 52% | -19.4% | 142 |
| 13 | `ichimoku_9_26_52` | trend | **+0.023** | 2.055 | 57% | -10.9% | 82 |
| 14 | `voltarget_100_20_0.6` | risk-overlay | **-0.021** | 1.154 | 38% | -14.7% | 645 |
| 15 | `garch_voltarget_0.94_0.6` | risk-overlay | **-0.028** | 1.207 | 48% | -12.2% | 711 |
| 16 | `atr_sized_14_0.01` | risk-overlay | **-0.038** | 1.289 | 48% | -0.3% | 743 |
| 17 | `stoch_14_3` | oscillator-reversion | **-0.043** | 1.175 | 48% | -13.3% | 56 |
| 18 | `sma_regime_100` | regime-filter | **-0.066** | 1.522 | 48% | -16.4% | 96 |
| 19 | `bb_reversion_20_2` | mean-reversion | **-0.114** | 0.910 | 43% | -19.1% | 50 |
| 20 | `grid_50_4_0.05` | mean-reversion | **-0.152** | 0.369 | 29% | -16.7% | 599 |
| 21 | `vol_regime_20_0.5` | regime-filter | **-0.172** | 0.759 | 40% | -18.7% | 94 |
| 22 | `vwap_reversion_20_0.02` | mean-reversion | **-0.265** | 0.587 | 29% | -38.4% | 152 |
| 23 | `dual_momentum_12_1` | momentum | **-0.319** | 1.459 | 43% | -37.2% | 212 |
| 24 | `ma_crossover_20_50` | trend | **-0.334** | 2.186 | 38% | -31.7% | 38 |
| 25 | `ma_ribbon_5x10` | trend | **-0.336** | 1.957 | 43% | -29.0% | 965 |

> 13 of 25 evaluable have a positive median. PBO **0.700** over 20 splits of 25 configurations (common blocks [2, 3, 4, 5, 6, 7]).

## Long horizon (1d bars, slow parameters) — CPCV

| # | Strategy | Family | Median Sharpe | IQR | % paths + | Median ret | Trades |
|---|---|---|---|---|---|---|---|
| 1 | `obv_trend_60` | volume-flow | **+0.774** | 1.571 | 81% | +44.6% | 98 |
| 2 | `vol_regime_60_0.5` | regime-filter | **+0.696** | 0.823 | 80% | +36.1% | 54 |
| 3 | `adx_trend_30_25` | regime-filter | **+0.651** | 2.286 | 57% | +26.2% | 14 |
| 4 | `rsi_30_35_55` | oscillator-reversion | **+0.593** | 0.895 | 71% | +20.8% | 10 |
| 5 | `hurst_switch_250_0.55_0.45` | regime-filter | **+0.558** | 1.505 | 80% | +11.3% | 32 |
| 6 | `buy_and_hold` | baseline | **+0.534** | 1.434 | 68% | +9.4% | 16 |
| 7 | `macd_26_52_18` | trend | **+0.517** | 1.142 | 76% | +16.1% | 50 |
| 8 | `ou_reversion_250_3` | mean-reversion | **+0.412** | 0.806 | 73% | +10.5% | 24 |
| 9 | `dual_momentum_24_1` | momentum | **+0.358** | 1.715 | 57% | +5.5% | 156 |
| 10 | `stoch_40_5` | oscillator-reversion | **+0.316** | 0.752 | 57% | +6.3% | 34 |
| 11 | `voltarget_200_60_0.6` | risk-overlay | **+0.295** | 1.558 | 76% | +5.0% | 661 |
| 12 | `ma_crossover_50_200` | trend | **+0.290** | 1.162 | 52% | +0.0% | 16 |
| 13 | `sma_regime_200` | regime-filter | **+0.254** | 1.620 | 71% | -2.2% | 44 |
| 14 | `ichimoku_18_52_104` | trend | **+0.243** | 0.950 | 71% | +2.5% | 56 |
| 15 | `garch_voltarget_0.97_0.6` | risk-overlay | **+0.239** | 1.558 | 76% | +2.3% | 672 |
| 16 | `ts_momentum_200` | momentum | **+0.200** | 2.341 | 52% | -12.7% | 54 |
| 17 | `ma_ribbon_5x20` | trend | **+0.171** | 1.319 | 57% | -2.6% | 1030 |
| 18 | `atr_sized_30_0.01` | risk-overlay | **+0.156** | 1.715 | 67% | +0.7% | 672 |
| 19 | `breakout_60_30` | breakout | **+0.140** | 1.676 | 62% | -6.6% | 18 |
| 20 | `zscore_60_-2` | mean-reversion | **+0.120** | 0.222 | 76% | -6.0% | 24 |
| 21 | `bb_reversion_60_2` | mean-reversion | **+0.120** | 0.222 | 76% | -6.0% | 24 |
| 22 | `grid_120_4_0.1` | mean-reversion | **+0.095** | 0.869 | 52% | -2.3% | 675 |
| 23 | `keltner_50_30_2` | breakout | **-0.160** | 2.203 | 38% | -17.7% | 34 |
| 24 | `vwap_reversion_60_0.05` | mean-reversion | **-0.162** | 0.420 | 29% | -31.5% | 54 |
| 25 | `bb_breakout_60_2` | breakout | **-0.349** | 1.905 | 43% | -27.1% | 32 |

> 22 of 25 evaluable have a positive median. PBO **0.700** over 20 splits of 25 configurations (common blocks [2, 3, 4, 5, 6, 7]).

---

# List 1b — the same singles under a single 70/30 split (retained as contrast)

**Superseded by List 1.** Kept because the disagreement between the two methods is the lesson:
the single split ranked `zscore_20_-2` first at medium and `ma_crossover_12_48` first at short;
CPCV puts them far lower. Ranked on **out-of-sample Sharpe**, in-sample beside each row.
Rows with fewer than 10 out-of-sample trades are listed but **not ranked**.

## Short horizon (1h bars, fast parameters) — 16 configurations evaluated

| # | Strategy | Family | OOS Sharpe | IS Sharpe | OOS ret | IS ret | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `ma_crossover_12_48` | trend | **+0.488** | −2.490 | +3.4% | −59.7% | −11.8% | 29 |
| 2 | `zscore_20_-2` | mean-reversion | **+0.441** | −1.285 | +2.8% | −37.3% | −19.0% | 48 |
| 3 | `bb_reversion_20_2` | mean-reversion | **+0.086** | −1.274 | −0.9% | −37.3% | −18.0% | 52 |
| 4 | `sma_regime_168` | regime-filter | −0.519 | −2.101 | −7.0% | −51.4% | −15.2% | 49 |
| 5 | `voltarget_168_24_0.8` | risk-overlay | −0.519 | −2.105 | −7.0% | −51.5% | −15.2% | 49 |
| 6 | `rsi_7_30_55` | oscillator-reversion | −0.527 | −1.620 | −7.4% | −45.9% | −23.9% | 49 |
| 7 | `bb_breakout_20_2` | breakout | −0.684 | −0.901 | −6.9% | −23.6% | −15.9% | 50 |
| 8 | `stoch_14_3` | oscillator-reversion | −0.719 | −0.311 | −7.9% | −14.6% | −13.9% | 37 |
| 9 | `grid_48_4_0.03` | mean-reversion | −1.510 | −1.593 | −8.8% | −27.1% | −13.3% | 694 |
| 10 | `vwap_reversion_20_0.01` | mean-reversion | −1.516 | −1.777 | −17.2% | −50.5% | −23.3% | 55 |
| 11 | `ts_momentum_24` | momentum | −1.677 | −2.272 | −18.1% | −57.8% | −23.3% | 126 |
| 12 | `keltner_12_7_2` | breakout | −1.954 | +0.448 | −7.9% | +5.3% | −9.0% | 13 |
| 13 | `breakout_12_6` | breakout | −2.272 | −0.936 | −22.2% | −29.6% | −27.1% | 59 |
| 14 | `obv_trend_24` | volume-flow | −2.331 | −0.499 | −25.8% | −23.3% | −29.4% | 153 |
| 15 | `macd_6_13_5` | trend | −4.621 | −2.016 | −42.4% | −56.4% | −46.0% | 205 |

_Not ranked: `buy_and_hold` (1 trade) — OOS Sharpe −0.523, OOS return −12.9%._

**Reading it:** only three of fifteen rankable short-horizon signals produced a positive
out-of-sample Sharpe, and the best of them returned +3.4% before any funding/borrow cost.
`macd_6_13_5` at −4.62 is the clearest case of a fast trend signal being chewed up by
whipsaw plus 8bps round-trip cost across 205 trades.

## Medium horizon (1d bars, medium parameters) — 16 configurations evaluated

| # | Strategy | Family | OOS Sharpe | IS Sharpe | OOS ret | IS ret | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `zscore_20_-2` | mean-reversion | **+0.699** | −0.170 | **+41.3%** | −64.8% | −52.0% | 10 |
| 2 | `bb_reversion_20_2` | mean-reversion | **+0.193** | −0.152 | −4.8% | −63.9% | −52.0% | 10 |
| 3 | `stoch_14_3` | oscillator-reversion | **+0.024** | +0.153 | −18.1% | −20.2% | −44.4% | 11 |
| 4 | `sma_regime_100` | regime-filter | −0.516 | +0.443 | −35.8% | +34.8% | −43.1% | 13 |
| 5 | `vwap_reversion_20_0.02` | mean-reversion | −0.532 | +0.032 | −53.9% | −58.6% | −61.8% | 23 |
| 6 | `voltarget_100_20_0.6` | risk-overlay | −0.569 | +0.307 | −31.1% | +15.7% | −34.8% | 73 |
| 7 | `grid_50_4_0.05` | mean-reversion | −0.590 | −0.119 | −38.9% | −36.9% | −48.5% | 100 |
| 8 | `macd_12_26_9` | trend | −0.720 | **+1.347** | −52.8% | **+1356.5%** | −59.2% | 21 |
| 9 | `bb_breakout_20_2` | breakout | −0.841 | **+1.837** | −34.9% | **+2843.6%** | −40.9% | 11 |
| 10 | `ts_momentum_60` | momentum | −0.874 | +0.959 | −51.1% | +392.8% | −51.3% | 25 |
| 11 | `obv_trend_20` | volume-flow | −1.383 | **+1.494** | −69.2% | **+1932.1%** | −69.2% | 37 |

_Not ranked (fewer than 10 OOS trades): `breakout_20_10` (7), `rsi_14_30_50` (4),
`keltner_20_14_2` (6), `ma_crossover_20_50` (7), `buy_and_hold` (1)._

**Reading it:** rows 8–11 are the exhibit. `bb_breakout_20_2` returned **+2,844% in-sample and
−34.9% out-of-sample**; `obv_trend_20` **+1,932% → −69.2%**. These are the strategies a
full-sample leaderboard would have crowned. The three positive out-of-sample rows are all
mean-reversion/oscillator entries sitting exactly at the 10-trade evidence floor — treat them
as "not yet disconfirmed" rather than "works".

## Long horizon (1d bars, slow parameters) — 16 configurations evaluated

| # | Strategy | Family | OOS Sharpe | IS Sharpe | OOS ret | IS ret | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `obv_trend_60` | volume-flow | −0.153 | +1.271 | −24.0% | +982.7% | −43.7% | 18 |
| 2 | `grid_120_4_0.1` | mean-reversion | −0.296 | +0.001 | −26.5% | −23.1% | −39.1% | 143 |
| 3 | `voltarget_200_60_0.6` | risk-overlay | −0.395 | +0.975 | −23.6% | +219.9% | −27.9% | 67 |
| 4 | `ts_momentum_200` | momentum | −1.976 | +1.098 | −77.2% | +506.2% | −77.7% | 15 |

_Not ranked (fewer than 10 OOS trades — the dominant outcome at this scale):
`rsi_30_35_55` (2, OOS Sharpe +0.540), `bb_reversion_60_2` (5, +0.225), `zscore_60_-2` (5,
+0.225), `macd_26_52_18` (7, +0.188), `breakout_60_30` (2), `stoch_40_5` (4),
`sma_regime_200` (4), `vwap_reversion_60_0.05` (7), `ma_crossover_50_200` (2),
`keltner_50_30_2` (6), `bb_breakout_60_2` (5), `buy_and_hold` (1)._

**Reading it: not one rankable long-horizon _single_ has a positive out-of-sample Sharpe**
(0 of 4; 5 of 34 rankable long-horizon *pairs* do, see List 2). Twelve of sixteen singles fail
the evidence floor entirely, because slow parameters on a
563-bar out-of-sample window simply do not generate enough trades. **The honest conclusion for
the long horizon is that this dataset cannot answer the question** — 1,875 daily bars is too
short to evaluate 200-day signals out-of-sample. That is a data limitation, not a finding
about the strategies.

## Spec-only tier — ranked by a priori plausibility, never measured

Not implemented, **no performance numbers**, ranked by reasoning only. Each names the data gap
that prevented measurement. Full field detail in `STRATEGIES.md`.

| Rank | Signal | Why plausibly high value for SOL | Blocking data gap |
|---|---|---|---|
| 1 | Perp funding / borrow-rate extremes | Direct positioning gauge; on Jupiter the borrow fee is utilization-driven and always positive, so extremes mark crowding | No funding/borrow-rate history |
| 2 | Realised-vol regime switch (HMM/threshold) | Conditions *which* family to run; this sweep shows trend and reversion invert between regimes | Obtainable — needs implementation, not new data |
| 3 | Cross-sectional momentum vs majors | Strongest documented anomaly family (Jegadeesh-Titman) | No peer universe fetched |
| 4 | Stablecoin-flow / exchange-netflow | Leading indicator of buying power entering the chain | No on-chain data |
| 5 | Cointegration vs ETH/BTC | Engle-Granger/Johansen spread z-score; crypto majors co-move strongly | No peer price series |
| 6 | Order-book imbalance / depth | Highest-frequency edge available | No L2 data |
| 7 | Open-interest divergence | OI rising into flat price marks leverage build-up | No OI history |
| 8 | Implied-vs-realised vol spread | Variance-risk-premium harvest | No options surface |
| 9 | Staking-ratio / validator-flow | SOL-specific float dynamics | No on-chain data |
| 10 | Social/dev-activity sentiment | Documented 1–2 day decay; noisy | No sentiment feed |

---

# List 2 — Most likely pairs to backtest

**This is a hypothesis-generation list, not a findings list.** With ~45 mechanisms there are
~990 possible pairs; ranking that space by measured performance is textbook data-snooping and
its top rows would be predominantly noise. Ranking is therefore by **a priori
complementarity** — does the partner see something the primary is structurally blind to —
with measured results attached where the pair was actually run.

**140 pairs were evaluated per horizon (420 total), all cross-family by construction.**
Combining two trend signals mostly measures the same thing twice, so same-family pairs were
never generated.

## Ranked by mechanical complementarity

| # | Pair | Why they are complementary (mechanism) | Measured |
|---|---|---|---|
| 1 | **regime filter + mean-reversion** (`sma_regime` + `zscore`) | Mean-reversion's fatal mode is buying dips in a downtrend; the regime filter is the only thing that answers "is there a downtrend". Directly patches the primary's failure. | ✅ Best measured short-horizon pair: **OOS Sharpe +2.572** (IS −1.407), +9.0% on 18 trades |
| 2 | **trend + volume confirmation** (`ma_crossover` + `obv_trend`) | Price-based trend cannot distinguish a move on real participation from a drift on none; OBV is price-blind and reads exactly that. | ✅ Evaluated at all horizons |
| 3 | **breakout + volatility-squeeze filter** (`bb_breakout` + low-bandwidth gate) | Breakouts fail most when volatility is already expanded; the squeeze condition selects for contraction-before-expansion. | ⚠️ Squeeze gate implemented but not swept (`squeeze_lookback` defaults to off) |
| 4 | **oscillator + mean-reversion** (`stochastic` + `zscore`) | Two independent statements of "stretched": one on momentum, one on price distance. Agreement raises precision. | ✅ **OOS Sharpe +1.258** short (IS −0.385), 35 trades |
| 5 | **trend + breakout** (`ts_momentum` + `breakout`) | Trend confirms direction, breakout times entry; addresses trend-following's late-entry problem. | ✅ **OOS +0.100** medium, 10 trades |
| 6 | **momentum + oscillator brake** (`macd` + `stochastic`) | Stops momentum from adding exposure into an already-exhausted move. | ✅ **OOS +0.391** medium (IS +0.223), 10 trades |
| 7 | **breakout + reversion exit** (`breakout` + `zscore`, `any` mode) | Breakout for entry, reversion for the exit the breakout rule handles badly. | ✅ **Best measured medium pair: OOS Sharpe +0.584**, **+30.8%**, 16 trades |
| 8 | **vol-target overlay + any directional signal** (`voltarget` × …) | Orthogonal by construction — changes size, not direction. Should reshape the equity curve without touching signal quality. | ⚠️ Swept as a single, not yet as a wrapper |
| 9 | **reversion + volume** (`vwap_reversion` + `obv_trend`) | Distinguishes a discount with accumulation from one with distribution. | ✅ **OOS +0.186** long, 12 trades |
| 10 | **regime filter + grid** (`sma_regime` + `grid`) | Grid is short-volatility and long the range assumption; its catastrophic mode is a sustained trend, which is precisely what a regime filter vetoes. | ❌ Not swept — grid is in the candidate set but this specific pairing was not isolated |

### Measured pair results, for reference

Top rankable pairs per horizon. **Note the pattern: high out-of-sample Sharpe alongside
negative in-sample Sharpe** — the reverse of overfitting, and a direct consequence of the
regime inversion at the split. These are regime-dependent, not fitted.

**Short (140 evaluated, 125 rankable, 16 with positive OOS Sharpe):**

| Pair | OOS Sharpe | IS Sharpe | OOS ret | OOS trades |
|---|---|---|---|---|
| `all(sma_regime+zscore)` | +2.572 | −1.407 | +9.0% | 18 |
| `all(sma_regime+bb_reversion)` | +2.572 | −1.691 | +9.0% | 18 |
| `all(sma_regime+rsi)` | +1.456 | −2.147 | +5.2% | 17 |
| `all(stochastic+zscore)` | +1.258 | −0.385 | +9.7% | 35 |
| `any(ma_crossover+bb_breakout)` | +1.240 | −1.283 | +12.3% | 33 |

**Medium (140 evaluated, 88 rankable, 8 with positive OOS Sharpe):**

| Pair | OOS Sharpe | IS Sharpe | OOS ret | OOS trades |
|---|---|---|---|---|
| `any(breakout+zscore)` | +0.584 | +0.867 | +30.8% | 16 |
| `all(macd+stochastic)` | +0.391 | +0.223 | +9.9% | 10 |
| `any(keltner+zscore)` | +0.305 | +0.776 | +3.9% | 16 |
| `all(ts_momentum+stochastic)` | +0.240 | −0.275 | +4.5% | 10 |

**Long (140 evaluated, 34 rankable, 5 with positive OOS Sharpe):** best is
`any(rsi+obv_trend)` at **+0.226** OOS (IS +1.288) on 15 trades, but **−8.8% return** —
positive Sharpe with a negative return means low, well-behaved exposure, not profit.

> Every one of the eight positive medium-horizon pairs sits at 10–21 out-of-sample trades.
> At that sample size, and with 140 configurations searched per horizon, the Harvey-Liu-Zhu
> bar (t > 3.0) is not remotely cleared by any of them. Treat this table as a shortlist of
> **experiments worth running properly**, on more data and more out-of-sample paths.

---

# List 3 — Most likely multi-signal combinations (3+)

Same framing, more emphatically: the triple space is ~14,000 cross-family combinations. This
sweep deliberately bounded it to combinations drawn from the **top-6 out-of-sample singles per
horizon** — which is itself a selection step, and one that borrows information from the
out-of-sample window. **That makes the measured triple numbers below optimistically biased,
and they are reported only because omitting them would hide the search that happened.**

**52 triples evaluated** (32 short, 20 medium, 0 long — the long horizon had fewer than three
rankable singles to draw from, which is itself the finding from List 1).

## Ranked by a priori structure

| # | Combination | Structural rationale | Measured |
|---|---|---|---|
| 1 | **regime filter + mean-reversion + oscillator confirm** (`sma_regime` + `zscore`/`bb_reversion` + `rsi`) | The full defensive stack: regime says *whether*, reversion says *where*, oscillator says *when*. Each covers a distinct failure of the others. | ✅ **Best measured: `all(bb_reversion+sma_regime+rsi)` OOS Sharpe +2.555** (IS −1.569), +8.9%, 17 trades (short) |
| 2 | **trend + reversion + regime** (`ma_crossover` + `zscore` + `sma_regime`) | Deliberately mixes opposed families under a regime switch, so one is live when the other is wrong. | ✅ `all(ma_crossover+zscore+sma_regime)` **OOS +1.435** (IS +1.026), +2.4%, 11 trades (short) |
| 3 | **trend + breakout + volume** (`ma_crossover` + `bb_breakout` + `obv_trend`) | Three independent confirmations of one directional thesis: slope, range expansion, participation. Raises precision, cuts trade count hard. | ⚠️ Partially — `vote(ma_crossover+sma_regime+bb_breakout)` OOS +0.295, 607 trades |
| 4 | **vol-target × (trend + regime)** | Sizing overlay on a directional core; should improve drawdown without changing hit rate. | ❌ Not swept as a wrapper |
| 5 | **regime + reversion + volume** | Adds "is the dip being accumulated" to the row-1 stack. | ❌ Not swept |
| 6 | Any triple using **`vote` mode across 3 opposed families** | Continuous exposure scaling with agreement, rather than the binary all/none of `all`. | ✅ Swept; **0 of 10 rankable medium triples had positive OOS Sharpe** |

### What the measured triples actually showed

- **Short horizon:** 10 of 24 rankable triples positive. Best two (`all(bb_reversion+sma_regime+rsi)`
  and `all(zscore+sma_regime+rsi)`) are **numerically identical at +2.555**, and the reason is
  a defect in my own strategy set, provable from the source rather than guessed:

  ```
  bb_reversion entry :  close < mean - 2*sd(ddof=0)   <=>  (close-mean)/sd_0 <  -2
  zscore       entry :  (close-mean)/sd(ddof=1) <= -2 <=>  (close-mean)/sd_1 <= -2
  where sd_1 = sd_0 * sqrt(n/(n-1)) = sd_0 * sqrt(20/19) ~ 1.026 * sd_0
  ```

  It is the **same inequality**, differing only in the standard-deviation convention — which
  makes the z-score entry about 2.6% stricter. The exits are exactly equivalent
  (`close > mid` ⟺ `z > 0`). So `zscore_20_-2` and `bb_reversion_20_2` are one mechanism
  entered at two marginally different thresholds, not two signals.

  **That is a warning, not a discovery.** Two rows in List 1 and several "cross-family" pairs
  are double-counting one mechanism, so the diversity implied by the configuration counts is
  overstated. Family labels are not a substitute for measuring pairwise signal correlation,
  which this sweep does not do — see item 3 in *What to actually do next*. It also means the
  two identical `+2.555` triples are one result reported twice, not independent corroboration.
- **Medium horizon: 0 of 10 rankable triples had a positive out-of-sample Sharpe.** Best was
  `vote(zscore+stochastic+sma_regime)` at **−0.002**. Adding a third signal did not help.
- **Long horizon:** no triples ran — insufficient rankable singles.

### The honest summary on combinations

More signals reduced trade count toward the evidence floor faster than they improved
out-of-sample Sharpe. The `all` mode's precision gain is real but buys it with sample size,
which is exactly the wrong trade when out-of-sample evidence is already thin. **Nothing in
List 3 is demonstrated. The top rows are the experiments most worth running on more data.**

---

# Lists 2 & 3 under CPCV — the combination result

**Re-run over all 25 strategies: 334 cross-family pairs per horizon (was 140) and 70 triples.**
The conclusion did not soften — combinations still produce *more* positive-looking results and
*worse* rank generalisation at the same time.

| Configuration type | PBO (short) | PBO (medium) | PBO (long) |
|---|---|---|---|
| Singles (25) | 0.343 | **0.700** | **0.700** |
| **Pairs** (334/horizon) | 0.229 | **0.650** | **0.650** |
| **Triples** (70/horizon) | 0.086 | **0.886** | **0.543** |

Recall the calibration: **0.500 is pure noise, 0.000 is a genuinely ordered signal set.** Every
daily-horizon figure above 0.500 is *anti*-informative — picking the best in-sample is measurably
worse than picking at random.

And the trap is baited harder than before:

| | positive median Sharpe |
|---|---|
| Long pairs | **247 of 295 (84%)** |
| Long triples | **45 of 47 (96%)** |
| Medium pairs | 201 of 297 (68%) |

The single best number anywhere in this document is `all(dual_momentum+vol_regime)` at the long
horizon: median Sharpe **+1.345**, 87% of paths positive, **+75.1%** median path return. It is
also, by the PBO of 0.650 sitting above it, exactly the row you should not trust — it is the top
of a 295-configuration search whose ranking is anti-informative. That tension is the finding.

## List 2 under CPCV — pairs

**SHORT** — 334 evaluated, 320 evaluable, **11** with positive median Sharpe. **PBO = 0.229.**

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(vol_regime+zscore)` | regime-filter+mean-reversion | **+1.091** | 2.726 | 71% | +2.8% | 84 |
| 2 | `all(vol_regime+ou_reversion)` | regime-filter+mean-reversion | **+0.944** | 2.244 | 71% | +1.4% | 68 |
| 3 | `all(ma_crossover+ou_reversion)` | trend+mean-reversion | **+0.919** | 2.168 | 71% | +1.6% | 94 |
| 4 | `all(vol_regime+bb_reversion)` | regime-filter+mean-reversion | **+0.834** | 2.726 | 71% | +1.9% | 84 |
| 5 | `all(ou_reversion+obv_trend)` | mean-reversion+volume-flow | **+0.688** | 3.779 | 52% | +1.4% | 104 |
| 6 | `all(sma_regime+zscore)` | regime-filter+mean-reversion | **+0.681** | 2.584 | 62% | +1.6% | 112 |
| 7 | `all(sma_regime+bb_reversion)` | regime-filter+mean-reversion | **+0.549** | 2.866 | 62% | +1.6% | 112 |
| 8 | `all(vol_regime+rsi)` | regime-filter+oscillator-reversion | **+0.530** | 2.329 | 57% | +1.2% | 100 |

_Top 8 of 320 evaluable._

**MEDIUM** — 334 evaluated, 297 evaluable, **201** with positive median Sharpe. **PBO = 0.650.**

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `any(hurst_switch+ou_reversion)` | regime-filter+mean-reversion | **+1.290** | 0.972 | 100% | +68.9% | 40 |
| 2 | `all(stochastic+ou_reversion)` | oscillator-reversion+mean-reversion | **+1.156** | 0.584 | 93% | +30.1% | 18 |
| 3 | `any(bb_breakout+ou_reversion)` | breakout+mean-reversion | **+1.052** | 1.198 | 87% | +67.1% | 76 |
| 4 | `any(macd+ou_reversion)` | trend+mean-reversion | **+0.996** | 0.929 | 87% | +84.3% | 100 |
| 5 | `any(macd+hurst_switch)` | trend+regime-filter | **+0.925** | 1.083 | 93% | +72.6% | 118 |
| 6 | `any(hurst_switch+bb_breakout)` | regime-filter+breakout | **+0.924** | 1.380 | 87% | +48.3% | 72 |
| 7 | `all(ma_ribbon+hurst_switch)` | trend+regime-filter | **+0.881** | 1.238 | 93% | +7.9% | 25 |
| 8 | `any(hurst_switch+stochastic)` | regime-filter+oscillator-reversion | **+0.875** | 1.080 | 87% | +53.5% | 58 |

_Top 8 of 297 evaluable._

**LONG** — 334 evaluated, 295 evaluable, **247** with positive median Sharpe. **PBO = 0.650.**

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(dual_momentum+vol_regime)` | momentum+regime-filter | **+1.345** | 0.881 | 87% | +75.1% | 52 |
| 2 | `any(adx_trend+ou_reversion)` | regime-filter+mean-reversion | **+1.162** | 1.423 | 67% | +87.6% | 34 |
| 3 | `any(ou_reversion+obv_trend)` | mean-reversion+volume-flow | **+1.054** | 1.180 | 93% | +93.6% | 90 |
| 4 | `all(macd+vol_regime)` | trend+regime-filter | **+0.991** | 0.957 | 87% | +42.0% | 34 |
| 5 | `any(hurst_switch+ou_reversion)` | regime-filter+mean-reversion | **+0.965** | 1.049 | 93% | +42.6% | 46 |
| 6 | `all(dual_momentum+stochastic)` | momentum+oscillator-reversion | **+0.937** | 1.089 | 95% | +23.4% | 66 |
| 7 | `any(vol_regime+rsi)` | regime-filter+oscillator-reversion | **+0.927** | 0.868 | 100% | +57.9% | 60 |
| 8 | `any(hurst_switch+obv_trend)` | regime-filter+volume-flow | **+0.919** | 1.534 | 100% | +63.1% | 88 |

_Top 8 of 295 evaluable._

## List 3 under CPCV — triples

Drawn from a **fixed a-priori set of seven** (one per family), chosen before any CPCV number was
seen, so these carry no selection bias from the singles ranking. Unchanged from the 16-strategy
run, which keeps them comparable across both sweeps.

**SHORT** — 70 evaluated, 61 evaluable, **6** with positive median Sharpe. **PBO = 0.086.**

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(ma_crossover+sma_regime+zscore)` | trend+regime-filter+mean-reversion | **+1.907** | 2.680 | 76% | +2.7% | 62 |
| 2 | `all(sma_regime+zscore+obv_trend)` | regime-filter+mean-reversion+volume-flow | **+1.844** | 2.091 | 81% | +2.3% | 42 |
| 3 | `all(sma_regime+rsi+obv_trend)` | regime-filter+oscillator-reversion+volume-flow | **+0.950** | 2.734 | 67% | +1.8% | 68 |
| 4 | `all(sma_regime+rsi+zscore)` | regime-filter+oscillator-reversion+mean-reversion | **+0.735** | 2.505 | 67% | +1.6% | 100 |
| 5 | `all(ts_momentum+sma_regime+zscore)` | momentum+regime-filter+mean-reversion | **+0.708** | 2.138 | 71% | +0.5% | 26 |
| 6 | `all(ma_crossover+ts_momentum+zscore)` | trend+momentum+mean-reversion | **+0.239** | 1.847 | 62% | +0.2% | 44 |
| 7 | `all(ts_momentum+sma_regime+rsi)` | momentum+regime-filter+oscillator-reversion | **-0.104** | 2.363 | 48% | -0.2% | 58 |
| 8 | `all(ma_crossover+sma_regime+rsi)` | trend+regime-filter+oscillator-reversion | **-0.458** | 1.902 | 38% | -0.9% | 88 |

_Top 8 of 61 evaluable._

**MEDIUM** — 70 evaluated, 51 evaluable, **38** with positive median Sharpe. **PBO = 0.886.**

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(sma_regime+breakout+obv_trend)` | regime-filter+breakout+volume-flow | **+0.380** | 1.880 | 52% | +9.6% | 82 |
| 2 | `all(ts_momentum+breakout+obv_trend)` | momentum+breakout+volume-flow | **+0.369** | 1.582 | 71% | +9.1% | 88 |
| 3 | `vote(breakout+zscore+obv_trend)` | breakout+mean-reversion+volume-flow | **+0.367** | 1.305 | 62% | +8.6% | 1373 |
| 4 | `vote(breakout+rsi+zscore)` | breakout+oscillator-reversion+mean-reversion | **+0.349** | 1.192 | 62% | +7.7% | 1090 |
| 5 | `vote(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **+0.339** | 1.013 | 62% | +7.4% | 1312 |
| 6 | `vote(ts_momentum+breakout+zscore)` | momentum+breakout+mean-reversion | **+0.326** | 1.336 | 57% | +5.4% | 1252 |
| 7 | `vote(ts_momentum+rsi+obv_trend)` | momentum+oscillator-reversion+volume-flow | **+0.311** | 1.455 | 57% | +5.3% | 1372 |
| 8 | `vote(ts_momentum+zscore+obv_trend)` | momentum+mean-reversion+volume-flow | **+0.307** | 1.076 | 62% | +5.2% | 1438 |

_Top 8 of 51 evaluable._

**LONG** — 70 evaluated, 47 evaluable, **45** with positive median Sharpe. **PBO = 0.543.**

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `vote(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **+0.732** | 0.945 | 81% | +20.4% | 1215 |
| 2 | `vote(breakout+rsi+obv_trend)` | breakout+oscillator-reversion+volume-flow | **+0.590** | 1.413 | 81% | +20.0% | 1158 |
| 3 | `vote(sma_regime+rsi+obv_trend)` | regime-filter+oscillator-reversion+volume-flow | **+0.589** | 1.501 | 76% | +19.0% | 1283 |
| 4 | `vote(ma_crossover+rsi+obv_trend)` | trend+oscillator-reversion+volume-flow | **+0.581** | 1.486 | 81% | +18.5% | 1381 |
| 5 | `vote(ts_momentum+rsi+obv_trend)` | momentum+oscillator-reversion+volume-flow | **+0.564** | 1.695 | 71% | +21.4% | 1364 |
| 6 | `vote(sma_regime+zscore+obv_trend)` | regime-filter+mean-reversion+volume-flow | **+0.512** | 1.702 | 76% | +17.6% | 1398 |
| 7 | `all(ma_crossover+sma_regime+obv_trend)` | trend+regime-filter+volume-flow | **+0.507** | 1.397 | 81% | +18.0% | 42 |
| 8 | `all(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **+0.475** | 1.012 | 57% | +0.7% | 10 |

_Top 8 of 47 evaluable._
---

## What to actually do next

Ranked by expected information gain per unit of work, which is a different question from
"which strategy won":

1. ~~Replace the single 70/30 split with CPCV.~~ **Done** — `backtester/core/cpcv.py`, and it
   changed the answer: buy-and-hold went from mid-table to first at the medium horizon, and the
   long horizon became evaluable at all (16/16 versus 4/16). PBO 0.43–0.46 now quantifies what
   the single split could only hint at.
2. **Get more assets. Longer daily history was not obtainable from this environment** —
   Coinbase's backward pagination walked to **2021-06-17** and could make no further progress,
   which is consistent with that being its SOL-USD listing date. *Evidence limit, stated
   precisely:* that conclusion comes from the pagination loop terminating, not from a direct
   observation of an empty response for an earlier window — a direct probe of 2020-04→2021-06 was
   attempted and could not complete, because outbound HTTP to every venue with 2020 SOL history
   (Binance geo-blocked; Kraken, OKX, Gate, KuCoin, Bybit unreachable) hangs from this network.
   **Re-test before treating 2021-06-17 as a hard floor.** CPCV largely absorbed the need
   regardless: it fixed the long-horizon evidence problem the extra history was meant to fix. A
   **peer universe** remains the higher-value data addition, because it unlocks the
   cross-sectional-momentum and cointegration families that are currently spec-only.
3. **Measure pairwise signal correlation before calling a pair orthogonal.** The identical
   `+2.555` triples prove family labels are not enough.
4. **Add funding/borrow-rate history.** It is the highest-ranked spec-only signal and it is
   also a direct input to the perp cost model already implemented in `backtester/core/perps.py`.
5. **Test the vol-target overlay as a wrapper**, not as a standalone strategy. It is the one
   candidate here that is orthogonal by construction rather than by assumption.
6. **Apply a deflated Sharpe ratio** to any survivor, accounting for the 520 trials already run.
7. **Add a parameter-perturbation stability check to the sweep itself.** Finding 4 shows a 2.6%
   threshold change moving an out-of-sample return by 46 percentage points. Every ranked row
   should be re-run at ±10% on each parameter and reported with the spread; rows whose result
   is not stable under that perturbation should be excluded from ranking the way thin-evidence
   rows already are.

## Reproducing every number

```bash
python3 research/cpcv_sweep.py                  # List 1 (primary): CPCV + PBO
python3 research/cpcv_sweep.py --groups 8 --k 2  # tune the block/path geometry
python3 research/sweep.py                       # List 1b/2/3: the single-split sweep
python3 research/verify_numbers.py              # assert every figure here matches the results
python3 -m unittest discover -s backtester/tests -t .   # 103 tests
```

`verify_numbers.py` extracts every performance figure from this document and from
`STRATEGIES.md` and asserts each one appears in `results/sweep_results.csv` within rounding
tolerance. It currently verifies **254 figures** and exits non-zero on any mismatch — so the
claim "no number was estimated" is enforced mechanically rather than promised.

Outputs land in `research/results/`: `sweep_results.csv` (one row per configuration),
`tables.md` (generated tables), `configuration_counts.json` (the denominators).

**Cost model for every number above:** 6bps taker fee + 2bps slippage per fill, charged on
notional at the fill price; signal at bar *t* fills at bar *t+1*'s open; spot mode, no leverage.
Hourly results additionally carry 2 disclosed data gaps (largest 6h, around Oct 2025).

> Educational and research use only. NOT investment advice. Nothing here is evidence that any
> listed strategy is profitable; the measured evidence is that on this asset and window, almost
> none of them were.
