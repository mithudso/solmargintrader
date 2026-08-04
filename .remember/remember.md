# Handoff — 2026-08-04

## Where the work lives

Branch **`worktree-cpcv-and-longer-history`** in `.claude/worktrees/cpcv-and-longer-history`.
Four commits, not merged to the default branch:

| Commit | What |
|---|---|
| `84ea17d` | Initial commit: backtester, strategy research, pre-existing Jupiter extension |
| `feef1f9` | CPCV + PBO (`backtester/core/cpcv.py`), 23 tests |
| `3b74e1a` | CPCV becomes the primary ranking; single split retained as List 1b |
| `1a399d4` | ddo pass: stale counts, spec-drift note |

**103 tests pass. 495 document figures verified against results CSVs.**

## The headline result

Evaluation is now **CPCV** (8 blocks, k=2, 28 paths per configuration), not one 70/30 split.

- **PBO = 0.429 / 0.457 / 0.457** (short/medium/long). Calibrated against controls in the test
  suite: **pure noise → 0.500** (mean over 30 seeds), **genuinely ordered signal → 0.000**. SOL
  sits far closer to noise. Selecting by in-sample performance is barely better than random.
- **`buy_and_hold` ranks 1st at the medium horizon** (median path Sharpe +0.534). Nothing beat
  holding the asset.
- **All 16 short-horizon configurations have a negative median path Sharpe.**
- `zscore_20_-2`, which the single split ranked **1st**, falls to **8th** (52% of paths positive
  — a coin flip). `ma_crossover_12_48` goes 1st → 14th.
- **`obv_trend_60` is the only genuinely interesting row anywhere:** +0.774 median Sharpe, **81%
  of paths positive**, +44.6% median path return, 98 trades. First candidate for a
  parameter-perturbation check, precisely because it looks good.

## Three things worth remembering

1. **The single split was structurally doomed.** Its in-sample window ends on bar 1311 — the
   **highest close in the entire 1,875-bar series** (\$261.99). It separated the bull market from
   the bear leg to within one bar, so any long-biased strategy *had* to look great in-sample and
   terrible out-of-sample. I originally wrote "almost exactly on the top"; the fact-check showed
   that was an *under*statement.
2. **CPCV purge/embargo is degenerate here, and the code says so.** Classic CPCV purges training
   observations to protect *fitted* parameters. These strategies fit nothing. What CPCV actually
   buys is the path distribution and PBO. The real leakage vector for fixed-parameter strategies
   is **warm-up**, so `evaluate_block` warms from bars preceding each block and measures only the
   in-block region. Don't let anyone "restore" purge/embargo thinking it was missing.
3. **`zscore_20_-2` and `bb_reversion_20_2` are the same mechanism.** Identical inequality; only
   the stdev `ddof` differs (~2.6% threshold gap). They produce identical CPCV rows at the long
   horizon (+0.120, IQR 0.222) and near-identical elsewhere. Family labels are not a substitute
   for measuring pairwise signal correlation.

## Blocked, and why

**Longer daily history was not obtainable from this environment.** Coinbase's backward pagination
walked to **2021-06-17** and could make no further progress, consistent with that being its
SOL-USD listing date. Binance is geo-blocked; Kraken, OKX, Gate, KuCoin and Bybit hang on DNS.
CoinGecko's `days=max` OHLC is pro-gated and its free `market_chart` is close-only, which cannot
build OHLC bars for breakout/Keltner/stochastic/ATR strategies.

> **Know the limit of this evidence.** The 2021-06-17 floor is inferred from the pagination loop
> terminating, **not** from a direct empty response for an earlier window. I attempted that direct
> probe three times; all three were killed or timed out because outbound HTTP degraded to
> unreachable partway through the session. **Re-test before treating 2021-06-17 as a hard floor** —
> one completed request for `start=2020-04-01&end=2021-06-16` settles it either way.

CPCV absorbed the underlying need: the long horizon went from **4/16 evaluable to 16/16**,
because blocks reuse the whole series instead of one 563-bar tail.

## Open

- Branch is **unmerged** and there is **no remote**. Merge or open a PR when ready.
- `research/results/` and `data/` are gitignored; regenerate with `cpcv_sweep.py` / `sweep.py`
  and `backtester.core.fetch`.
- `/cdo` outstanding on the newer modules (indicators, signals, composite, cpcv, both sweeps).
- **Next highest-value work**, in order: (1) parameter-perturbation stability check on every
  ranked row — start with `obv_trend_60`; (2) measure pairwise signal correlation instead of
  trusting family labels; (3) re-run Lists 2 and 3 under CPCV (they are still single-split);
  (4) fetch a **peer universe** — unlocks cross-sectional momentum and cointegration, and is a
  bigger win than more SOL history; (5) deflated Sharpe accounting for the trials already run.
