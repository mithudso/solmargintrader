# Top 5 strategies — recommendation

**AS OF 2026-08-04.** Every figure below is read programmatically from
`research/results/cpcv_combos_results.csv`, `cpcv_results.csv` and the `perturb_long_*.csv`
files. Nothing is transcribed by hand.

> **Historical simulation for research and education only. NOT investment advice.** Simulated
> past performance does not predict future results. Read the two warnings below before the table;
> they matter more than the ranking.

## Warning 1 — ranking by backtest performance is the operation this dataset invalidates

PBO (probability of backtest overfitting) is **0.700** for singles at both daily horizons,
against a measured pure-noise line of 0.500. Above the noise line means selecting by in-sample
rank is *worse than picking at random*. Spearman ρ(in-sample, out-of-sample Sharpe) is **−0.419**
at the medium horizon: the best-looking strategy was actively the wrong choice.

So a list titled 'top 5 by Sharpe' would be a list of the rows most likely to be noise.

## Warning 2 — the lowest PBO in the study points at the *least* profitable strategies

| Slice | PBO | best median return |
|---|---|---|
| short triples | **0.086** | +2.7% |
| short pairs | 0.229 | +2.8% |
| medium/long pairs | 0.650 | +68.9% / +75.1% |

PBO is low at the short horizon because rank is *stable* there — stably losing. The research doc
says it outright: 'in-sample rank generalises reliably as a loser.' Optimising for the best
overfitting statistic selects +2.7% strategies before funding and borrow costs. Do not do it.

## The selection rule actually used

Of 1,287+ evaluated configurations, only **7** have been tested on *two independent robustness
axes*: the CPCV path distribution **and** ±10% parameter perturbation (`research/perturb.py`).
Ranking outside that set means ranking on the anti-informative axis alone. The five below are
drawn from those seven, and ordered by how many checks they clear — not by Sharpe.

Checks: median Sharpe > 0 · ≥70% of paths positive · median > IQR/2 · positive median return ·
≥10 trades · perturbation-tested with 0 sign flips.

| # | Configuration | Horizon | Median Sharpe | IQR | % paths + | Median ret | Trades | Perturbations | max abs Δ | Sign flips |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `all(dual_momentum+vol_regime)` | long | **+1.345** | 0.881 | 87% (of 15) | +75.1% | 52 | 12 | 0.441 | **0** |
| 2 | `any(hurst_switch+ou_reversion)` | medium | **+1.290** | 0.972 | 100% (of 15) | +68.9% | 40 | 12 | 0.754 | **0** |
| 3 | `any(ou_reversion+obv_trend)` | long | **+1.054** | 1.180 | 93% (of 15) | +93.6% | 90 | 8 | 0.446 | **0** |
| 4 | `obv_trend_60` | long | **+0.774** | 1.571 | 81% (of 21) | +44.6% | 98 | 2 | 0.199 | **0** |
| 5 | `vol_regime_60_0.5` | long | **+0.696** | 0.823 | 80% (of 15) | +36.1% | 54 | 6 | 0.364 | **0** |

**Path counts are 15 or 21, not 28.** C(8,2) is 28 nominally, but warm-up renders 2 blocks
unusable for these slow configurations (1 for `obv_trend_60`), so each percentage above is over
15 or 21 paths as marked — verified 2026-08-05 from `results/cpcv_top5_sol_doge_zec_1d.csv`,
whose `n_paths` column contains no value of 28. Fewer paths is a weaker estimate, and four of
these five rest on fifteen.

**Benchmark that must stay in view:** `buy_and_hold`, zero parameters, medium/long median Sharpe
**+0.534**, 68% of paths positive, +9.4% median return. It ranked **2nd of 25** at the medium
horizon and 6th at long. Any strategy here that does not clearly beat it is not worth its
complexity, and holding the asset beat all but one or two of everything tested.

### Honourable mentions — also perturbation-tested, not in the five

- `any(adx_trend+ou_reversion)` (long) — median +1.162, 67% paths, 10 perturbations, max abs Δ 0.675, 0 flips. Highest parameter sensitivity of the tested set.
- `all(macd+vol_regime)` (long) — median +0.991, 87% paths, 12 perturbations, max abs Δ 0.283, 0 flips.

## The mechanism-level finding, which outranks any individual row

`ou_reversion` and `vol_regime` are not five separate results. `ou_reversion` appears as the
partner in a majority of top combinations across every horizon, and `vol_regime` in the rest.
The transferable claim is **not** 'trade these five configurations' — it is:

1. **A slow mean-reversion signal (`ou_reversion`, 250-bar) is the most productive *partner*
   mechanism in this study.** It is what the top pairs have in common. **Qualified 2026-08-05:**
   its value is partner-dependent. `any(ou_reversion+obv_trend)` transferred to DOGE and ZEC;
   `any(hurst_switch+ou_reversion)` collapsed on DOGE (0 of 15 paths positive).
2. ~~**A volatility- or Hurst-based regime gate is the second.**~~ **DOWNGRADED 2026-08-05 —
   contradicted by the cross-asset test** (`CROSS-ASSET-TRANSFER.md`). The two configurations
   containing `vol_regime` (#1 and #5) suffered the largest degradations off SOL, and
   `vol_regime_60_0.5` goes negative on **both** DOGE and ZEC. As a medium-horizon single,
   `vol_regime` is positive on only 3 of 5 assets and one of those is +0.019. **`obv_trend`
   replaces it as the transfer-supported second mechanism**: it is the only member appearing in
   both surviving configurations (#3, #4) and, as a single, is positive on all five assets with
   the highest path fractions on both new ones (86% DOGE, 90% ZEC).
3. **Combining raises parameter sensitivity ~2.6×** — comparing like with like, since the top
   pairs are long-horizon: long-horizon singles median ratio **0.171** vs top pairs **0.44**.
   (Corrected 2026-08-05: the earlier phrasing paired that 2.6× multiple with the *pooled*
   singles median of 0.208 across all three horizons, which yields 2.1×, not 2.6×. Both numbers
   are real; the mismatched pairing was not.) It also raises PBO. Pairs buy performance with
   fragility; that trade is real and measured.

## What this does not establish

- Perturbation stability answers *were the parameters cherry-picked* (no). It cannot answer
  *was the configuration cherry-picked from 295 candidates* — PBO 0.650 says that stands.
- One asset (SOL), one history. BTC and ETH runs already sank the last surviving moderate result;
  `cpcv_all25_btc_eth_1d.csv` is the record. **Answered 2026-08-05, and the answer is bad for
  this table:** all five configurations were re-run unchanged on DOGE and ZEC, and **all ten
  transfers degraded with none improving** (median −0.821 DOGE, −0.753 ZEC). Only **#3 and #4**
  stayed positive on all three assets — so the ordering 1–5 above should not be read as a
  preference ranking, because the two configurations at the top of it are among the worst
  transfers. On ZEC, zero-parameter `buy_and_hold` (+0.659) beat all five. Full write-up:
  `research/CROSS-ASSET-TRANSFER.md`; reproduce with
  `python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC`.
- The largest single sensitivity found was **CPCV geometry** (8→9 blocks, Δ −0.441), larger than
  any strategy parameter. The result depends more on how the data is sliced than on the strategy.
- No live order has ever been placed by this project.
