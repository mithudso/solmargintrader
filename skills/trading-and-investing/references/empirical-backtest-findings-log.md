---
name: empirical-backtest-findings-log
# provenance: split from strategy-failure-modes-and-synergy 2026-08-04 (§9 had grown to 54% of that file)
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  The measured-results log behind this skill family — every backtest run against
  the SOL/BTC dataset, including the ones that FALSIFIED claims made elsewhere in
  the library. Covers the shape-selected adversarial month matrix, the closed-trade
  illusion measured (100% win rate while the account lost 37.5%), two caveats this
  data falsified (bar fills were not optimistic; a trend prediction was wrong), a
  240-config parameter sweep where zero configs rescued the bear month, walk-forward
  evidence quantifying selection bias, the out-of-sample result that reversed an
  earlier in-sample rejection of the convex/concave pairing, and the cross-asset
  test on matched windows. Read alongside the conceptual material it tests.
  Educational only — NOT financial advice.
keywords:
  - backtest results
  - measured findings
  - closed-trade illusion
  - parameter sweep
  - walk-forward
  - out-of-sample
  - selection bias
  - falsified claims
  - shape-selected months
  - cross-asset test
  - SOL backtest
  - BTC backtest
tags:
  - trading-and-investing
  - backtesting
  - empirical
  - validation
---

# Empirical Backtest Findings Log

> **Educational information only — NOT financial, investment, or tax advice.** Every number here is a
> backtest on a single dataset. None is an expected return.

**What this is.** The measured-results log for the strategy material in this hub. It was split out of
`strategy-failure-modes-and-synergy.md` when it grew to over half that file — the conceptual claims and
the evidence testing them are now separate artifacts that cite each other.

**Why it is worth reading in full.** Several sections record claims made elsewhere in this library that
this data **falsified** — including two of my own predictions and one conclusion that reversed
completely when the test was redone properly. Those are kept, with the errors visible, because the
error is usually more instructive than the correction.

| For… | Go to |
|---|---|
| The conceptual framework these results test | `references/strategy-failure-modes-and-synergy.md` |
| Grid mechanics and failure modes | `references/grid-trading-strategy.md` |
| Generalisation methodology and the rung ladder | `references/cross-asset-generalisation-testing.md` |
| Sleeve weighting and objective choice | `references/sleeve-weighting-and-objective-selection.md` |
| Sampling frequency as a dominant parameter | `references/sampling-frequency-and-bar-aggregation.md` |
| The dataset and scripts | `~/Downloads/sol-backtest-data/README.md`, `_scripts/` |

---

## 9. A concrete stress-test matrix (SOL, 2021–2026)

Five months were selected quantitatively by path shape (quadratic fit on normalized price/time) and
tick data pulled for each — they form a natural adversarial suite, because each one is designed to
break a different component. Data: `~/Downloads/sol-backtest-data/`.

### 9.1 Measured results

These are **backtested, not asserted**. Method: 1-minute spot bars; 20-level arithmetic grid;
$10,000; **grid range taken from the PRIOR month's high/low so there is no lookahead**; fills require
a bar to *trade through* a level, not merely touch it; 0.10%/side fees on both legs; equity always
marked to market including open inventory. Trend = EMA(24/72) crossover, long/short, 1h bars.
Reproduce with `_scripts/grid_backtest.py`.

| Month | Shape | **Grid total** | Grid *closed* P&L | Unrealized | Cycles | Buy & hold | Trend |
|---|---|---|---|---|---|---|---|
| 2021-08 | Bull | **+12.1%** | +$245 | +$960 | 21 | **+194.7%** | +111.5% |
| 2022-01 | Bear | **−37.5%** | **+$95** | **−$3,840** | 6 | −41.5% | **+8.7%** |
| 2026-07 | Neutral | **+2.1%** | +$477 | −$269 | 35 | −1.1% | **−10.5%** |
| 2023-06 | U-shaped | −4.0% | +$360 | −$755 | 50 | −9.4% | **+14.0%** |
| 2025-09 | Mountain | +3.7% | +$413 | −$42 | 43 | +4.0% | +1.7% |

> **Implementation-sensitivity warning.** A second, independently written engine
> (`_scripts/engine.py`, exact price-path crossing detection rather than a per-bar
> low/high test) reproduces the *signs, ranking and every qualitative conclusion*
> above, but not all magnitudes — most notably the bull month, where it returns
> **+2.9%** rather than +12.1%. The bear (−39.4% vs −37.5%), neutral (+2.3% vs
> +2.1%) and mountain (+4.2% vs +3.7%) months agree closely; the bull month does
> not. Two defensible implementations of "a 20-level grid" disagree by 9 points on
> one month. **Treat single-configuration grid magnitudes as implementation-dependent
> and rely on the direction and the cross-month pattern, not the decimal.** The
> §9.3 sweep is the more reliable read for that reason.

**The three findings that matter:**

1. **The closed-trade illusion is real and measurable.** In the bear month the grid's *closed-trade*
   P&L was **positive (+$95) with a 100% win rate**, while the account lost **37.5%**. Every closed
   trade was a winner; the −$3,840 sat in unrealized inventory the log never showed. This is §5.3 of
   `grid-trading-strategy.md` reproduced on real data — and it is the single strongest argument for
   never judging a grid on realized P&L.
2. **The grid's bull-market failure is opportunity cost, and it is enormous.** +12.1% against buy &
   hold's **+194.7%** — the grid captured about 6% of the move, because it sold its inventory into
   strength and finished in cash. Note this is the grid's *best-looking* month by closed P&L logic and
   still its worst decision.
3. **The neutral month is the only one where the grid beat everything** — +2.1% versus trend's
   **−10.5%** and buy & hold's −1.1%, a 12.6-point spread over trend. Grid and trend swapped places
   completely between the neutral month and the bear month (−37.5% vs +8.7%, a 46-point spread in the
   other direction). **That inversion is §1 made concrete**, and it is the empirical case for the
   convex overlay in §6.2.

Fee sensitivity was minor at this grid density: dropping fees from 0.10% to 0.02% per side moved
results by only 0.1–0.4 points. At *tighter* spacing it would dominate (§4 of the grid spoke).

### 9.2 A prediction this data falsified

An earlier draft of this table predicted that trend-following would **"fail twice"** in the U-shaped
month — stopped out at the bottom, re-entering late. **It did not. Trend returned +14.0% in
2023-06, its second-best month of the five.**

Why the prediction was wrong: a U is only a whipsaw trap if the reversal is *sharp*. June 2023's
recovery was a sustained multi-week leg, which is exactly what an EMA crossover is built to capture.
The whipsaw failure needs **repeated** direction changes, not one smooth reversal — which is why the
*neutral* month (−10.5%), not the U month, is where trend actually broke.

Corrected reading: **shape alone does not determine which strategy wins — the number and sharpness of
direction changes does.** A single reversal, however large, is tradeable by a trend follower. Chop is
not. Treat the §3 and §4 atlases as hypotheses to test on your own data, exactly as this one was
tested and partly refuted.

Read the matrix: **no single row is good at everything, and the columns fail in complementary rows.**
A gating scheme (§6.1) should be judged on the mountain and neutral months specifically, because those
are where a lagging classifier does its worst.

### 9.3 A second caveat this data falsified — bar fills were NOT optimistic

The standing warning (here and in `grid-trading-strategy.md` §7.1) was that OHLC bars *overstate* grid
performance, because a bar tells you a level was touched, not that you filled — so 1-minute results
should be read as an optimistic bound and only tick data settles it.

**Tested directly against 46.1M tick prints.** The same grid was run three ways per month: 1m bars;
raw ticks (every print, uncapped); and ticks with the identical one-fill-per-level-per-minute cap
applied, which isolates fill realism from the cap itself.

| Month | Bars | Ticks (capped) | Ticks (raw) | Gap (bars − ticks) |
|---|---|---|---|---|
| 2021-08 Bull | +2.93% | +2.93% | +3.11% | **−0.18pp** |
| 2022-01 Bear | −39.38% | −39.38% | −39.38% | 0.00pp |
| 2026-07 Neutral | +2.29% | +2.29% | +2.29% | 0.00pp |
| 2023-06 U-shaped | −4.35% | −4.30% | −4.20% | **−0.15pp** |
| 2025-09 Mountain | +4.15% | +4.15% | +4.15% | 0.00pp |

**Maximum deviation across all five months: 0.18 percentage points — and every non-zero gap is
NEGATIVE, meaning the bar run was slightly *pessimistic*, not optimistic.**

The warning was aimed at the wrong thing. It is correct for a **touch-fill** rule (fill whenever
`low ≤ level ≤ high`). It does **not** apply once you require the path to *trade through* a level and
cap one fill per level per bar — that conservatism already absorbs the intra-bar ambiguity. Corrected
guidance: **the fill rule matters; the data resolution barely does.** A conservative 1m backtest of a
20-level grid is within a fifth of a point of tick truth, so tick data is not required for this
question — spend it on questions that genuinely need print-level sequencing.

Validity check: tick cycle counts were ≥ bar cycle counts in all five months (26≥25, 7, 38, 54≥51,
49), confirming the turning-point compression did not silently merge oscillations.

### 9.4 Parameter sweep — 240 configurations

Levels {10, 20, 40, 80} × spacing {arithmetic, geometric} × range width {0.75, 1.0, 1.5 × the prior
month's range} × fee {0.10%, 0.02%}, on all five months. Distribution, not just the winner:

| Month | Median | Best | Worst | % of configs profitable |
|---|---|---|---|---|
| Bull | +4.03% | +21.93% | +1.75% | 100% |
| **Bear** | **−39.03%** | **−34.01%** | **−40.78%** | **0%** |
| Neutral | +2.02% | +3.43% | +0.43% | 100% |
| **U-shaped** | −4.32% | −0.93% | −7.41% | **0%** |
| Mountain | +3.61% | +4.76% | +1.40% | 100% |

**No parameter configuration rescues the bear month. Zero of 48.** The best case still loses 34%.
This is the strongest available statement of §5.2/§3.1: the trend-breakout failure is **structural,
not parametric**. You cannot tune your way out of it — which is exactly why the fix has to be a
different payoff shape (§6.2), not a better grid.

**Cross-month stability** (mean rank across all five months, 1 = best that month):

| Levels | Spacing | Width | Fee | Mean rank |
|---|---|---|---|---|
| **10** | arithmetic | **1.50** | 0.02% | **5.6** |
| 10 | arithmetic | 1.50 | 0.10% | 7.0 |
| 20 | arithmetic | 1.50 | 0.02% | 13.0 |
| … | | | | |
| 80 | arithmetic | 0.75 | 0.10% | 43.4 |

**Fewest levels, widest range, lowest fee is the robust corner; densest grids are the worst.** That is
§4's fee-drag argument recovered empirically from the sweep — tight spacing multiplies fills and hands
the edge to the venue.

**The overfitting check, which is the most useful number here.** The configuration that *wins* the
neutral month (10 levels, arithmetic, width 0.75, 0.02% fee) returns **+3.43% in neutral and −40.64%
in bear** — *worse than the bear median of −39.03%*. Optimizing on the favourable regime actively
degraded the unfavourable one. Any grid parameter set selected on range-bound data should be assumed
to carry this property until tested otherwise (§8).

### 9.5 The in-sample test rejected the pairing — and was itself wrong (see §9.7)

> **⚠️ Superseded conclusion, retained because the error is instructive.** This section's headline
> finding — that no blend beats the best single sleeve — is an **artifact of in-sample selection**. It
> compares blends against a cherry-picked best-of-27 trend config. Redone with **both sleeves selected
> out-of-sample** (§9.7), the pairing beats both sleeves' worst months at nearly every weight. **Read
> §9.7 for the corrected result.** What remains valid here is the §9.1 trend-tuning correction below.

§6.2 argues for pairing a concave sleeve with a convex one. That was tested directly: **567
combinations** of sleeve weight (grid 0–100% in 5% steps) × trend parameters (fast × slow × sampling
frequency), across all five months. Because the sleeves are independent, book return is linear in the
weights, so each sleeve is simulated once and the weight axis swept analytically.

**Result (in-sample, and therefore misleading): no blend beat the best single sleeve.**

| | worst month | mean |
|---|---|---|
| Pure grid (w = 1.00) | −39.38% | −6.87% |
| **Best pure trend** (fast 48, slow 144, ~4h sampling) | **+3.11%** | **+42.28%** |
| Any blend | strictly between | strictly between |

Adding grid to a well-tuned trend sleeve **strictly reduced both** worst month and mean — grid's worst
month (−39.4%) sits far below trend's (+3.1%), and mixing in a worse sleeve can only drag the blend
down. On *this* evidence the convex/concave pairing appears not to improve on simply holding the
convex sleeve — **but that comparison is against an in-sample cherry-pick, and §9.7 shows the
conclusion reverses once both sleeves are selected honestly.**

**Two corrections this forces.**

1. **§9.1's trend column was one arbitrary, badly-chosen parameterization.** At ~hourly sampling trend
   returned −10.5% in the neutral month and −19.2% in the bear. At ~4h sampling the *same strategy*
   returns **+3.1% neutral and +34.8% bear** — profitable in all five months. Trend's bear-month result
   swung by more than 50 points on sampling frequency alone. **Do not cite the §9.1 trend figures as a
   property of trend-following.** They are a property of one setting.
2. **The §1 thesis is not refuted here — and §9.7 later demonstrates it directly** (sleeve correlation
   −0.11 out-of-sample). "Lose at different times"
   requires the sleeves to actually fail in different months. At hourly sampling, in the bear month,
   *both* lost. The mechanism may hold for a genuinely complementary pair; this pair, on this data,
   did not show it.

**The magnitude is not trustworthy; the mechanism is.** +42% mean is the **best of 27 trend configs
over 5 months** — textbook selection bias, exactly what §7.4 and §8 warn about. What *is* credible is
the payoff **shape**: that config took **3–7 trades per month at a 17–33% win rate**, with profit
concentrated in a few large moves (+156% in the bull month; +34.8% shorting the bear while buy-and-hold
lost 41.5%). **That is the convex profile of §1 behaving exactly as described** — a low win rate where
rare large winners pay for many small losers. Trust the shape; discount the number.

**What this does not license.** Concluding "trend beats grid, use trend" would repeat the very error
this section documents — 5 months, one asset, best-of-27. The defensible takeaways are narrower:
single-configuration comparisons between strategy families are close to worthless; **sampling frequency
deserves as much scrutiny as the signal rule**; and a pairing must be demonstrated against the
**best-tuned** version of each sleeve, never against a mis-tuned one.

Reproduce with `~/Downloads/sol-backtest-data/_scripts/run_book_sweep.py`.

### 9.6 Walk-forward — how much of the "best config" edge is real?

§9.5's +42% came from picking the best of 27 configs on 5 months. The honest test is whether selecting
on the past predicts anything about the future. Protocol: **60 months of 1h bars, 27 configs, a
12-month rolling train window**; each month, pick the config with the best mean return over the prior
12 months, then record that config's return on the *next* month — strictly out-of-sample. 48 OOS months.

| | mean | median | worst | % profitable |
|---|---|---|---|---|
| **SELECTED** (chosen on past 12 months) | **+4.24%** | −1.02% | −38.26% | 48% |
| MEDIAN (picking blind) | −2.64% | −4.53% | −41.63% | 35% |
| FIXED (one config, never re-selected) | +1.95% | **+2.86%** | −41.30% | **54%** |
| *ORACLE (best config that month — unattainable)* | *+22.50%* | *+16.95%* | *−14.06%* | *90%* |
| Buy & hold | **+5.64%** | −1.07% | −56.52% | 44% |

**Four conclusions, and they do not all point the same way.**

1. **Selection carries real signal — more than I expected.** SELECTED beat blind picking by
   **+6.88pp mean**, won **67% of out-of-sample months** (vs 50% for a coin flip), and achieved a mean
   OOS rank of **10.7 of 27** where blind picking gives 14.0. Parameter search is not pure noise here.
2. **But it does not beat buy-and-hold on return.** +4.24% vs **+5.64%**. What it does buy is a much
   better worst month (−38.3% vs −56.5%) — that is a risk improvement, not an alpha one, and it should
   be described that way.
3. **And it does not clearly beat just fixing one config.** FIXED had a *better median* (+2.86% vs
   −1.02%) and a *higher win rate* (54% vs 48%). Monthly re-selection bought mean return and lost
   consistency. **If you re-select parameters, benchmark against never re-selecting** — that comparison
   is skipped almost universally and it is the one that matters.
4. **The 5-month +42% was overwhelmingly selection bias, and this quantifies it.** The same selection
   procedure yields **+4.24%** out-of-sample — an order of magnitude less. ORACLE at +22.50% shows most
   of the theoretically achievable edge is simply *not reachable* by selecting on past performance.

**Two supporting observations.** The winning config changed in **36% of month transitions** — the
"best" parameters are unstable, which is itself evidence against over-trusting any single one. And
`fast=24` was selected in **1 of 48** months while `fast=12` and `fast=48` split the rest almost evenly
— the response surface is bimodal, so a mid-range default can sit in a dead zone.

**Standing caveat:** 48 OOS months on **one asset**. Better than 5 months, still not a sample that
supports a strong claim.

Reproduce with `~/Downloads/sol-backtest-data/_scripts/run_walkforward.py`.

### 9.7 Out-of-sample, the pairing DOES earn its claim — §9.5 was itself selection bias

§9.5 rejected the convex/concave pairing. **That rejection was wrong, and it was wrong for exactly the
reason §9.6 identified.** §9.5 compared blends against a *cherry-picked best-of-27* trend config whose
worst month was +3.11% — a number no blend could beat, because it was not a real out-of-sample number.

Re-run with **both sleeves selected honestly** — same 12-month rolling walk-forward applied to grid
*and* trend, 18 grid configs and 54 trend configs (now including `position_fraction`), 4,320
simulations, 48 out-of-sample months:

| | mean | median | **worst month** | % profitable |
|---|---|---|---|---|
| Grid alone (OOS-selected) | +0.14% | **+1.81%** | **−47.27%** | **65%** |
| Trend alone (OOS-selected) | **+4.49%** | −1.02% | **−38.26%** | 48% |
| **Blend @ w_grid = 0.65** | +1.66% | +1.22% | **−18.50%** | 54% |
| Buy & hold | +5.64% | −1.07% | −56.52% | 44% |

**Every weight from 0.05 to 0.85 beat both sleeves' worst months.** The best (w_grid = 0.65) cut the
worst month to **−18.50%** against −38.26% for the better sleeve alone — a **~20-point improvement in
the tail**.

**And the mechanism checks out — but not via the number you would reach for.** Pooled correlation of
the two sleeves' out-of-sample monthly returns is **−0.11**. Slightly negative, which looks like §1's
premise confirmed.

**That correlation estimate is not stable, and should not be leaned on.** Split into non-overlapping
12-month blocks it reads **+0.06, −0.01, −0.51, −0.50**; on a rolling 12-month window it ranges from
**−0.58 to +0.68** with a standard deviation of **0.34**, negative in only 68% of windows. The pooled
−0.11 is an average over a quantity that swings across the entire plausible range. **Anyone sizing a
book off an estimated correlation coefficient is building on sand.**

**The benefit survives anyway, and that is the finding.** In *all four* blocks — including the one
where correlation was mildly **positive** — the w_grid=0.65 blend still beat both sleeves' worst months:

| Block | Grid worst | Trend worst | Blend worst | Beats both |
|---|---|---|---|---|
| 2022-08 → 2023-07 | −47.27% | −29.19% | **−17.31%** | ✅ |
| 2023-08 → 2024-07 | −15.92% | −19.94% | **−11.68%** | ✅ |
| 2024-08 → 2025-07 | −27.79% | −35.86% | **−18.50%** | ✅ |
| 2025-08 → 2026-07 | −23.20% | −38.26% | **−13.90%** | ✅ |

**Why it works without stable negative correlation.** The tail benefit does not require the sleeves to
be reliably anti-correlated. It requires only that **their worst months do not coincide** — a weaker
and far more robust condition. Notice the columns swap: grid had the worse tail in the first block,
trend in the last two. Whichever sleeve is being punished, the other is not being punished as hard *at
that moment*, and the blend inherits neither full drawdown.

**The practical rule:** state the premise as *"their bad months land in different places"*, not
*"they are negatively correlated"*. The first is what you can rely on; the second is an unstable
estimate that will mislead you about how much diversification you have.

**What the pairing actually buys, stated precisely.** It is a **tail trade, not a return trade**:
blending *reduced* mean return (+4.49% → +1.66%) while roughly halving the worst month. If you are
optimising mean, hold trend alone. If you are optimising survival — and a −47% month can end a
strategy that a −18% month does not — the blend dominates both. Say which objective you are
optimising before quoting either number.

**The methodological lesson is the durable part.** Two runs of the *same comparison* reached opposite
conclusions purely because one selected a sleeve in-sample and the other did not. **A pairing must be
judged with every component selected out-of-sample.** Comparing a blend against a cherry-picked sleeve
will reject diversification that genuinely works — which is exactly what §9.5 did, and what this
section corrects.

**Standing caveats:** 48 OOS months, one asset. Grid alone still had the best *median* (+1.81%) and
the highest hit rate (65%), so the blend is not dominant on every metric. Config instability persists —
the selected grid changed in 12 of 47 transitions and trend in 19 of 47.

**Robustness check — the result replicates on a second instrument.** The identical protocol run on
**SOL perpetual futures** instead of spot (different microstructure, different participants, funding
and leverage available), 47 OOS months:

| | SOL spot (48 mo) | SOL perp (47 mo) |
|---|---|---|
| Grid worst month | −47.27% | −47.03% |
| Trend worst month | −38.26% | −39.30% |
| **Best blend** | w_grid 0.65 → **−18.50%** | w_grid 0.60 → **−22.08%** |
| Beats both sleeves | ✅ | ✅ |
| Sleeve correlation | −0.107 | −0.112 |

The optimal weight (0.65 vs 0.60) and the correlation (−0.107 vs −0.112) land almost on top of each
other, and the blend beats both sleeves in both instruments. That the *weight* replicates matters more
than that the *returns* do — it suggests the plateau is a property of pairing these payoff shapes
rather than of one price series.

**Be precise about what this does and does not establish.** Spot and perp track the **same underlying
asset**, so the two price series are highly correlated. This is an **instrument-robustness check, not a
cross-asset test** — it rules out the result being an artifact of spot microstructure specifically, and
it does **not** show the finding generalises to a different asset. **Cross-asset test (rung 3) — run on matched 48-month windows, and it largely replicates.** The
identical protocol on **BTCUSDT** over the same 2022-08 → 2026-07 OOS window:

| | SOL (48 OOS) | BTC (48 OOS) | Agrees? |
|---|---|---|---|
| **Blend beats both sleeves** | ✅ | ✅ | **YES** |
| Modal trend sampling | 4-hourly | 4-hourly | **YES** |
| **Modal grid level count** | **10 (35/48)** | **10 (48/48)** | **YES** |
| Sleeve correlation | −0.107 | −0.131 | **YES** |
| Best blend weight | 0.65 | 0.75 | close |
| Trend standalone mean | **+4.49%** | **−1.00%** | **NO — sign flips** |

**Four structural findings travelled**: the blend beat both sleeves on both assets, 4-hourly sampling
was modal on both, a 10-level grid was modal on both (winning all 48 BTC months), and the sleeve
correlation agreed closely. **One did not: trend's standalone edge inverted** — profitable on SOL,
unprofitable on BTC. The *pairing* survived while a *component's* profitability did not, which is the
argument for holding the book rather than the sleeve.

**A correction this data forced.** An earlier run on only **31 months** of BTC (all that was
downloaded at the time) reported the sleeve correlation as **+0.198 — positive** — and I wrote that up
as a genuine cross-asset sign flip, and as evidence that the benefit survives *despite* correlation
going the other way. **The full sample falsified that: correlation is −0.131, agreeing with SOL.** The
sign flip was an artifact of 17 missing months. The reframing above (non-coincident bad months rather
than negative correlation) still stands on the SOL sub-period evidence, but **it no longer has the
cross-asset sign-flip confirmation I claimed for it.** Truncated samples do not just add noise — they
produce confident, coherent, wrong conclusions. See `cross-asset-generalisation-testing.md` §5c.

Method and the full rung ladder: `references/cross-asset-generalisation-testing.md` §5b.

Reproduce with `~/Downloads/sol-backtest-data/_scripts/run_walkforward_book.py`.

## References

Internal: `references/strategy-failure-modes-and-synergy.md` (the conceptual framework under test);
`references/grid-trading-strategy.md`; `references/cross-asset-generalisation-testing.md`;
`references/sleeve-weighting-and-objective-selection.md`;
`references/sampling-frequency-and-bar-aggregation.md`;
`references/trading-strategies-and-styles.md` §5 (backtesting methodology, multiple testing).

**Evidence note.** Every figure in this log is a **first-party measurement** against the dataset at
`~/Downloads/sol-backtest-data/`, reproducible with the scripts in its `_scripts/` directory
(`run_experiments.py`, `run_book_sweep.py`, `run_walkforward.py`, `run_walkforward_book.py`,
`grid_backtest.py`). Scope throughout: **two assets (SOL, BTC), one venue (Binance), 2021-2026, two
strategy families.** That is enough to falsify claims and to demonstrate methodological points; it is
**not** enough to establish any strategy, parameter or weight as generally correct. Where a result
later proved to be an artifact of sample truncation or in-sample selection, the original claim and the
correction are both retained deliberately.
