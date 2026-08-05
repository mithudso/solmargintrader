# Conceptual index

**Generated** from `index/CONCEPT-INDEX.json` (2026-08-05T18:03:48+00:00). 21 concepts.

```bash
python3 index/build.py all              # refresh
python3 index/make_concepts_doc.py      # rewrite this file
python3 index/search.py --concepts      # list them
python3 index/search.py --concept cpcv  # files for one
```

## What this is for

A text search finds a word; this finds an *idea* under all the names it goes by in this repo. The evidence floor, for instance, appears as `min_total_trades`, `insufficient`, `DROPPED` and `rankable` in different files, and no single keyword finds all four.

**The concepts are the repo's own vocabulary, not a taxonomy imposed on it.** They are drawn from the `FAMILY` dict in `backtester/core/strategies/__init__.py`, the strategy-card frontmatter, `docs/trading-signals-concept-family.md`, and terms verified to recur in the corpus. A concept matching no file is dropped rather than kept — none were dropped on the last build, so every concept below is real.

## Method concepts

The ideas that decide whether a number in this repo means anything. Ordered by how many files touch them.

### Risk rails and dry-run safety

`risk-rails` · **128 files** · matched on `dry_run`, `dryrun`, `risk`, `rails`, `kill`, `guard`, `confirm`, `fail-closed`

The extension can place real orders. Dry-run is the default, rails live in code and fail closed, and a fresh install must never be able to trade.

Strongest files:

- `docs/FILES.md` (32 hits)
- `extension/README.md` (19 hits)
- `docs/CONCEPTS.md` (18 hits)
- `research/coin-intelligence/eth-ethereum.md` (17 hits)
- `index/build.py` (16 hits)
- `docs/API.md` (16 hits)
- `research/RANKED_LISTS.md` (14 hits)
- `extension/src/core/risk.js` (13 hits)

Full list: `python3 index/search.py --concept risk-rails -n 128`

### Lookahead and fill timing

`lookahead` · **116 files** · matched on `lookahead`, `fill_delay`, `warmup`, `warmup_bars`, `displacement`, `centred`, `shift`

A signal at bar t may use data only through t. Centred indicators, same-bar fills and displaced clouds are the recurring hazards.

Strongest files:

- `research/decide.py` (41 hits)
- `backtester/core/strategies/advanced.py` (32 hits)
- `backtester/core/strategies/signals.py` (26 hits)
- `backtester/tests/test_engine.py` (24 hits)
- `backtester/core/engine.py` (18 hits)
- `backtester/tests/test_decide.py` (16 hits)
- `backtester/cli.py` (15 hits)
- `docs/CONCEPTS.md` (13 hits)

Full list: `python3 index/search.py --concept lookahead -n 116`

### On-chain execution reality

`execution-onchain` · **111 files** · matched on `jupiter`, `jlp`, `oracle`, `priority`, `slippage`, `perps`, `solana`

Oracle-priced perps, priority fees as a product, per-account fee markets, dropped-versus-reverted. Decides whether a strategy is executable at all.

Strongest files:

- `pagesource` (98 hits)
- `docs/trading-signals-concept-family.md` (79 hits)
- `research/coin-intelligence/hype-hyperliquid.md` (68 hits)
- `research/coin-intelligence/sol-solana.md` (58 hits)
- `docs/FILES.md` (46 hits)
- `extension/README.md` (39 hits)
- `backtester/core/gridsim.py` (35 hits)
- `backtester/strategy_cards/jlp_vs_sol_relative_value.md` (26 hits)

Full list: `python3 index/search.py --concept execution-onchain -n 111`

### Evidence floor

`evidence-floor` · **99 files** · matched on `min_total_trades`, `min_rankable_trades`, `insufficient`, `dropped`, `evidence floor`, `rankable`

Below a minimum trade count a result is not eligible to be reported as an improvement. cpcv_evaluate prints DROPPED but still returns paths, which is how a 6-trade Sharpe reached a headline.

Strongest files:

- `research/cross_asset_cpcv.py` (67 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (33 hits)
- `index/build.py` (19 hits)
- `research/cpcv_sweep.py` (18 hits)
- `research/RANKED_LISTS.md` (16 hits)
- `docs/CONCEPTS.md` (14 hits)
- `index/make_concepts_doc.py` (14 hits)
- `research/decide.py` (12 hits)

Full list: `python3 index/search.py --concept evidence-floor -n 99`

### Grid trading

`grid` · **96 files** · matched on `grid`, `gridsim`, `ladder`, `recenter`, `anchor_window`, `levels`

A resting grid converts a sustained trend into a maximum-size losing position; the re-centring gate fired once in 1,875 bars.

Strongest files:

- `backtester/tests/test_gridsim.py` (148 hits)
- `backtester/core/gridsim.py` (100 hits)
- `extension/src/core/grid.js` (59 hits)
- `backtester/strategy_cards/ladder_grid.md` (56 hits)
- `extension/README.md` (52 hits)
- `extension/test/core.test.js` (52 hits)
- `docs/FILES.md` (46 hits)
- `backtester/gridcli.py` (43 hits)

Full list: `python3 index/search.py --concept grid -n 96`

### Data integrity

`data-integrity` · **91 files** · matched on `validate_bars`, `strict_gaps`, `allow_gaps`, `datavalidationerror`, `monotone`, `gap`

Gaps refused rather than filled, columns resolved by name, timestamps monotone. A concatenated XRP series hides a 2.5-year join.

Strongest files:

- `backtester/tests/test_engine.py` (34 hits)
- `backtester/core/data.py` (33 hits)
- `research/STRATEGIES.md` (32 hits)
- `pagesource` (16 hits)
- `backtester/core/universe.py` (11 hits)
- `research/cross_asset_cpcv.py` (11 hits)
- `docs/strategy-optimization-concept-family.md` (11 hits)
- `research/coin-intelligence/btc-bitcoin.md` (10 hits)

Full list: `python3 index/search.py --concept data-integrity -n 91`

### Buy-and-hold benchmark

`benchmark` · **81 files** · matched on `buy_and_hold`, `benchmark`, `baseline`

Zero parameters, and it out-ranked all but one or two strategies on SOL and all five recommended configurations on ZEC.

Strongest files:

- `docs/FILES.md` (29 hits)
- `research/perturb.py` (29 hits)
- `research/RANKED_LISTS.md` (25 hits)
- `backtester/core/deflated_sharpe.py` (21 hits)
- `docs/CONCEPTS.md` (14 hits)
- `backtester/core/gridsim.py` (14 hits)
- `backtester/core/report.py` (13 hits)
- `research/coin-intelligence/eth-ethereum.md` (12 hits)

Full list: `python3 index/search.py --concept benchmark -n 81`

### Combinatorial purged cross-validation

`cpcv` · **73 files** · matched on `cpcv`, `purged`, `combinatorial`, `n_groups`, `k_test`, `path_sharpes`

The repo's primary evaluation method: 8 blocks, k=2, up to 28 paths. Replaced the single 70/30 split, whose in-sample window ended on the highest close in the series.

Strongest files:

- `research/verify_numbers.py` (63 hits)
- `docs/FILES.md` (62 hits)
- `backtester/core/cpcv.py` (60 hits)
- `research/cpcv_sweep.py` (53 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (41 hits)
- `research/RANKED_LISTS.md` (35 hits)
- `research/coin-intelligence/sol-solana.md` (35 hits)
- `research/cross_asset_cpcv.py` (31 hits)

Full list: `python3 index/search.py --concept cpcv -n 73`

### Cost model

`costs` · **71 files** · matched on `fee_bps`, `slippage`, `slippage_bps`, `costconfig`, `break-even`, `borrow`, `financing`

Fees and slippage are never optional and must be applied exactly once. The engine runs fee_bps=6.0, slippage_bps=2.0, fill_delay=1.

Strongest files:

- `backtester/tests/test_engine.py` (58 hits)
- `backtester/core/gridsim.py` (53 hits)
- `backtester/core/engine.py` (45 hits)
- `backtester/README.md` (31 hits)
- `backtester/tests/test_gridsim.py` (28 hits)
- `backtester/core/perps.py` (22 hits)
- `backtester/cli.py` (20 hits)
- `backtester/gridcli.py` (19 hits)

Full list: `python3 index/search.py --concept costs -n 71`

### Overfitting and PBO

`overfitting-pbo` · **57 files** · matched on `pbo`, `overfitting`, `cscv`, `deflated`, `anti-informative`, `multiple-testing`

PBO measured 0.700 at daily horizons against a 0.500 noise line, so in-sample rank is anti-informative. This is the finding that governs how every other number here may be read.

Strongest files:

- `research/cpcv_sweep.py` (98 hits)
- `backtester/tests/test_cpcv.py` (58 hits)
- `research/verify_numbers.py` (39 hits)
- `research/RANKED_LISTS.md` (37 hits)
- `.remember/remember.md` (32 hits)
- `docs/FILES.md` (31 hits)
- `docs/strategy-optimization-concept-family.md` (25 hits)
- `backtester/tests/test_interpret.py` (24 hits)

Full list: `python3 index/search.py --concept overfitting-pbo -n 57`

### Perturbation and robustness

`robustness` · **55 files** · matched on `perturb`, `perturbation`, `ratio_to_iqr`, `sign_flips`, `stability`

Second independent axis beside CPCV: nudge each parameter +/-10% and re-run. A point that collapses is a spike, not a plateau.

Strongest files:

- `docs/FILES.md` (88 hits)
- `research/perturb.py` (53 hits)
- `research/verify_numbers.py` (31 hits)
- `research/RANKED_LISTS.md` (25 hits)
- `.remember/remember.md` (18 hits)
- `research/coin-intelligence/sol-solana.md` (11 hits)
- `docs/CONCEPTS.md` (10 hits)
- `research/results/perturb_all_singles_long.txt` (9 hits)

Full list: `python3 index/search.py --concept robustness -n 55`

### Cross-asset and cross-timeframe transfer

`transfer` · **52 files** · matched on `cross_asset`, `cross-asset`, `transfer`, `doge`, `zec`, `universe`, `top_coins`

The same 25 strategies score 25/25 on BTC daily and 0/25 on SOL hourly. The dataset has repeatedly explained more than the strategy.

Strongest files:

- `research/coin-intelligence/zec-zcash.md` (196 hits)
- `research/coin-intelligence/doge-dogecoin.md` (147 hits)
- `research/CROSS-ASSET-TRANSFER.md` (60 hits)
- `docs/FILES.md` (52 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (46 hits)
- `backtester/tests/test_universe.py` (40 hits)
- `backtester/core/universe.py` (35 hits)
- `research/coin-intelligence/sol-solana.md` (34 hits)

Full list: `python3 index/search.py --concept transfer -n 52`

---

## Strategy families

These are not editorial: each is a value of the `FAMILY` dict in `backtester/core/strategies/__init__.py`, which is what the engine itself uses to decide that two signals measure the same thing (the combination sweep skips same-family pairs for exactly that reason).

The families also carry a measured finding. Of the 25 registered strategies run on five assets, the eight positive on all five are drawn from breakout, trend, momentum, regime-filter and volume-flow — and **not one is from a reversion family**. No reversion-family strategy clears all five. See `research/CROSS-ASSET-TRANSFER.md`.

| Family | Files | Matched on |
|---|---|---|
| `regime-filter` | 103 | `regime`, `sma_regime`, `adx_trend`, `hurst`, `vol_regime` |
| `trend` | 102 | `trend`, `ma_crossover`, `macd`, `ichimoku` |
| `baseline` | 75 | `buy_and_hold`, `baseline` |
| `mean-reversion` | 61 | `mean-reversion`, `zscore`, `bb_reversion`, `vwap_reversion`, `ou_reversion` |
| `breakout` | 52 | `breakout`, `bb_breakout`, `keltner` |
| `oscillator-reversion` | 49 | `rsi`, `stochastic`, `oscillator` |
| `momentum` | 48 | `momentum`, `ts_momentum`, `dual_momentum` |
| `volume-flow` | 44 | `obv`, `volume-flow` |
| `risk-overlay` | 31 | `voltarget`, `atr_sized`, `garch`, `risk-overlay` |

---

## Strategy-card axes

Facts already written in the 46 cards' frontmatter, inverted so a value points back at its cards. Useful for questions the prose does not index — "which specs were never implemented", "which are rated very-low and why".

### `evaluation`

- **single-split-70-30** (18) — `atr_position_sizing`, `bb_reversion`, `breakout`, `buy_and_hold`, `garch_vol_forecast`, `grid`, `ichimoku_cloud`, `keltner`, `ma_crossover`, `ma_ribbon`, `macd`, `pairs_cointegration` and 6 more
- **None** (17) — `avellaneda_stoikov_mm`, `dex_cex_dislocation`, `discount_to_anchor`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence`, `order_book_imbalance`, `social_sentiment` and 5 more
- **cpcv-8-groups-k2** (6) — `adx_filtered_trend`, `bb_breakout`, `dual_momentum_12_1`, `obv_trend`, `vol_regime_hmm`, `zscore`
- **cpcv-8-groups-k2-sol-btc-eth** (2) — `hurst_regime_test`, `ou_half_life_sizing`
- **null** (1) — `jlp_vs_sol_relative_value`
- **real-sol-daily-and-hourly-recentred-blocks** (1) — `ladder_grid`

### `family`

- **mean-reversion** (10) — `bb_reversion`, `discount_to_anchor`, `grid`, `jlp_vs_sol_relative_value`, `kalman_hedge_ratio`, `ladder_grid`, `ou_half_life_sizing`, `pairs_cointegration`, `vwap_reversion`, `zscore`
- **crypto-native** (6) — `exchange_net_flow`, `funding_utilization_extremes`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence`, `staking_ratio_flow`
- **microstructure** (4) — `avellaneda_stoikov_mm`, `dex_cex_dislocation`, `order_book_imbalance`, `trade_flow_imbalance`
- **regime-filter** (4) — `adx_filtered_trend`, `hurst_regime_test`, `sma_regime`, `vol_regime_hmm`
- **trend** (4) — `ichimoku_cloud`, `ma_crossover`, `ma_ribbon`, `macd`
- **breakout** (3) — `bb_breakout`, `breakout`, `keltner`
- **momentum** (3) — `dual_momentum_12_1`, `ts_momentum`, `xs_momentum`
- **risk-overlay** (3) — `atr_position_sizing`, `garch_vol_forecast`, `voltarget`
- **oscillator-reversion** (2) — `rsi`, `stochastic`
- **volatility** (2) — `implied_vs_realised_vol`, `vol_of_vol_term_structure`
- **alt-data** (1) — `social_sentiment`
- **arbitrage** (1) — `triangular_arbitrage`
- **baseline** (1) — `buy_and_hold`
- **volume-flow** (1) — `obv_trend`

### `status`

- **measured** (27) — `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `dual_momentum_12_1`, `garch_vol_forecast`, `grid`, `hurst_regime_test`, `ichimoku_cloud`, `keltner` and 15 more
- **spec-only** (17) — `avellaneda_stoikov_mm`, `dex_cex_dislocation`, `discount_to_anchor`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence`, `order_book_imbalance`, `social_sentiment` and 5 more
- **implemented** (1) — `jlp_vs_sol_relative_value`

### `success_likelihood`

- **low** (24) — `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `funding_utilization_extremes`, `hurst_regime_test`, `ichimoku_cloud`, `implied_vs_realised_vol`, `jlp_vs_sol_relative_value`, `kalman_hedge_ratio` and 12 more
- **very-low** (21) — `avellaneda_stoikov_mm`, `dex_cex_dislocation`, `discount_to_anchor`, `dual_momentum_12_1`, `exchange_net_flow`, `garch_vol_forecast`, `grid`, `keltner`, `liquidation_cascade_proximity`, `ma_ribbon`, `macd`, `mvrv_nupl_valuation` and 9 more
