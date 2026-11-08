# Conceptual index

**Generated** from `index/CONCEPT-INDEX.json` (2026-11-08T09:58:49+00:00). 21 concepts.

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

`risk-rails` · **336 files** · matched on `dry_run`, `dryrun`, `risk`, `rails`, `kill`, `guard`, `confirm`, `fail-closed`

The extension can place real orders. Dry-run is the default, rails live in code and fail closed, and a fresh install must never be able to trade.

Strongest files:

- `skills/trading-and-investing/references/jlp-risk-profile-and-anti-patterns.md` (86 hits)
- `skills/trading-and-investing/references/trading-risk-management.md` (84 hits)
- `docs/FILES.md` (73 hits)
- `llms-full.txt` (67 hits)
- `skills/trading-and-investing/references/strategies-and-risk.md` (54 hits)
- `docs/TRADINGVIEW-REFERENCE.md` (52 hits)
- `skills/trading-and-investing/SKILL.md` (51 hits)
- `soltui/tui.py` (43 hits)

Full list: `python3 index/search.py --concept risk-rails -n 336`

### On-chain execution reality

`execution-onchain` · **329 files** · matched on `jupiter`, `jlp`, `oracle`, `priority`, `slippage`, `perps`, `solana`

Oracle-priced perps, priority fees as a product, per-account fee markets, dropped-versus-reverted. Decides whether a strategy is executable at all.

Strongest files:

- `skills/trading-and-investing/references/jupiter-jlp-pool.md` (163 hits)
- `docs/FILES.md` (150 hits)
- `skills/trading-and-investing/references/jupiter-swap-routing-and-orders.md` (127 hits)
- `skills/trading-and-investing/references/jupiter-perps-trading.md` (125 hits)
- `skills/trading-and-investing/references/jlp-risk-profile-and-anti-patterns.md` (124 hits)
- `skills/trading-and-investing/SKILL.md` (109 hits)
- `llms-full.txt` (102 hits)
- `pagesource` (98 hits)

Full list: `python3 index/search.py --concept execution-onchain -n 329`

### Grid trading

`grid` · **219 files** · matched on `grid`, `gridsim`, `ladder`, `recenter`, `anchor_window`, `levels`

A resting grid converts a sustained trend into a maximum-size losing position; the re-centring gate fired once in 1,875 bars.

Strongest files:

- `backtester/tests/test_gridsim.py` (167 hits)
- `llms-full.txt` (129 hits)
- `skills/trading-and-investing/references/grid-trading-strategy.md` (128 hits)
- `backtester/core/gridsim.py` (102 hits)
- `docs/FILES.md` (75 hits)
- `extension/src/core/grid.js` (66 hits)
- `backtester/strategy_cards/ladder_grid.md` (57 hits)
- `extension/README.md` (56 hits)

Full list: `python3 index/search.py --concept grid -n 219`

### Cost model

`costs` · **213 files** · matched on `fee_bps`, `slippage`, `slippage_bps`, `costconfig`, `break-even`, `borrow`, `financing`

Fees and slippage are never optional and must be applied exactly once. The engine runs fee_bps=6.0, slippage_bps=2.0, fill_delay=1.

Strongest files:

- `research/ratio_rotation.py` (89 hits)
- `skills/trading-and-investing/references/jupiter-perps-trading.md` (61 hits)
- `backtester/tests/test_engine.py` (58 hits)
- `backtester/core/gridsim.py` (55 hits)
- `backtester/core/engine.py` (54 hits)
- `llms-full.txt` (46 hits)
- `backtester/core/dcasim.py` (37 hits)
- `backtester/tests/test_engine_audit.py` (34 hits)

Full list: `python3 index/search.py --concept costs -n 213`

### Data integrity

`data-integrity` · **206 files** · matched on `validate_bars`, `strict_gaps`, `allow_gaps`, `datavalidationerror`, `monotone`, `gap`

Gaps refused rather than filled, columns resolved by name, timestamps monotone. A concatenated XRP series hides a 2.5-year join.

Strongest files:

- `soltui/bots.py` (39 hits)
- `backtester/tests/test_engine.py` (34 hits)
- `backtester/core/data.py` (33 hits)
- `research/STRATEGIES.md` (32 hits)
- `extension/src/ui/ui.css` (28 hits)
- `docs/FILES.md` (26 hits)
- `docs/SCRIPTS.md` (24 hits)
- `research/CANDLE-GAP-AUDIT.md` (23 hits)

Full list: `python3 index/search.py --concept data-integrity -n 206`

### Lookahead and fill timing

`lookahead` · **192 files** · matched on `lookahead`, `fill_delay`, `warmup`, `warmup_bars`, `displacement`, `centred`, `shift`

A signal at bar t may use data only through t. Centred indicators, same-bar fills and displaced clouds are the recurring hazards.

Strongest files:

- `research/decide.py` (44 hits)
- `backtester/core/strategies/advanced.py` (32 hits)
- `docs/TRADINGVIEW-REFERENCE.md` (31 hits)
- `backtester/core/strategies/signals.py` (26 hits)
- `backtester/core/engine.py` (25 hits)
- `llms-full.txt` (24 hits)
- `backtester/tests/test_engine.py` (24 hits)
- `backtester/tests/test_engine_audit.py` (17 hits)

Full list: `python3 index/search.py --concept lookahead -n 192`

### Evidence floor

`evidence-floor` · **171 files** · matched on `min_total_trades`, `min_rankable_trades`, `insufficient`, `dropped`, `evidence floor`, `rankable`

Below a minimum trade count a result is not eligible to be reported as an improvement. cpcv_evaluate prints DROPPED but still returns paths, which is how a 6-trade Sharpe reached a headline.

Strongest files:

- `research/cross_asset_cpcv.py` (67 hits)
- `soltui/cumulative.py` (40 hits)
- `research/CANDLE-GAP-AUDIT.md` (36 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (33 hits)
- `research/ratio_rotation.py` (22 hits)
- `docs/FILES.md` (19 hits)
- `index/build.py` (19 hits)
- `research/cpcv_sweep.py` (18 hits)

Full list: `python3 index/search.py --concept evidence-floor -n 171`

### Cross-asset and cross-timeframe transfer

`transfer` · **169 files** · matched on `cross_asset`, `cross-asset`, `transfer`, `doge`, `zec`, `universe`, `top_coins`

The same 25 strategies score 25/25 on BTC daily and 0/25 on SOL hourly. The dataset has repeatedly explained more than the strategy.

Strongest files:

- `research/coin-intelligence/zec-zcash.md` (196 hits)
- `research/coin-intelligence/doge-dogecoin.md` (147 hits)
- `docs/FILES.md` (64 hits)
- `research/results/frontier-2026-11-07.json` (62 hits)
- `research/CROSS-ASSET-TRANSFER.md` (60 hits)
- `research/results/minute_sweep_x1_common.txt` (54 hits)
- `docs/SCRIPTS.md` (50 hits)
- `research/five-minute-perps-suite/inherited-evidence-receipt.json` (47 hits)

Full list: `python3 index/search.py --concept transfer -n 169`

### Buy-and-hold benchmark

`benchmark` · **159 files** · matched on `buy_and_hold`, `benchmark`, `baseline`

Zero parameters, and it out-ranked all but one or two strategies on SOL and all five recommended configurations on ZEC.

Strongest files:

- `docs/FILES.md` (34 hits)
- `research/perturb.py` (29 hits)
- `research/RANKED_LISTS.md` (25 hits)
- `backtester/core/deflated_sharpe.py` (21 hits)
- `memory.md` (16 hits)
- `backtester/core/dcasim.py` (15 hits)
- `docs/CONCEPTS.md` (14 hits)
- `backtester/core/gridsim.py` (14 hits)

Full list: `python3 index/search.py --concept benchmark -n 159`

### Combinatorial purged cross-validation

`cpcv` · **129 files** · matched on `cpcv`, `purged`, `combinatorial`, `n_groups`, `k_test`, `path_sharpes`

The repo's primary evaluation method: 8 blocks, k=2, up to 28 paths. Replaced the single 70/30 split, whose in-sample window ended on the highest close in the series.

Strongest files:

- `docs/FILES.md` (77 hits)
- `research/verify_numbers.py` (63 hits)
- `backtester/core/cpcv.py` (60 hits)
- `research/cpcv_sweep.py` (54 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (41 hits)
- `research/RANKED_LISTS.md` (37 hits)
- `research/coin-intelligence/sol-solana.md` (35 hits)
- `research/cross_asset_cpcv.py` (31 hits)

Full list: `python3 index/search.py --concept cpcv -n 129`

### Overfitting and PBO

`overfitting-pbo` · **111 files** · matched on `pbo`, `overfitting`, `cscv`, `deflated`, `anti-informative`, `multiple-testing`

PBO measured 0.700 at daily horizons against a 0.500 noise line, so in-sample rank is anti-informative. This is the finding that governs how every other number here may be read.

Strongest files:

- `research/cpcv_sweep.py` (99 hits)
- `backtester/tests/test_cpcv.py` (58 hits)
- `research/RANKED_LISTS.md` (42 hits)
- `research/verify_numbers.py` (39 hits)
- `docs/FILES.md` (34 hits)
- `mongo/queries/06-experiments-and-pbo.js` (27 hits)
- `docs/strategy-optimization-concept-family.md` (25 hits)
- `backtester/tests/test_interpret.py` (24 hits)

Full list: `python3 index/search.py --concept overfitting-pbo -n 111`

### Perturbation and robustness

`robustness` · **94 files** · matched on `perturb`, `perturbation`, `ratio_to_iqr`, `sign_flips`, `stability`

Second independent axis beside CPCV: nudge each parameter +/-10% and re-run. A point that collapses is a spike, not a plateau.

Strongest files:

- `docs/FILES.md` (98 hits)
- `research/perturb.py` (54 hits)
- `research/verify_numbers.py` (31 hits)
- `research/RANKED_LISTS.md` (25 hits)
- `soltui/compound.py` (16 hits)
- `research/coin-intelligence/sol-solana.md` (11 hits)
- `research/triggers.py` (10 hits)
- `research/results/perturb_all_singles_long.txt` (9 hits)

Full list: `python3 index/search.py --concept robustness -n 94`

---

## Strategy families

These are not editorial: each is a value of the `FAMILY` dict in `backtester/core/strategies/__init__.py`, which is what the engine itself uses to decide that two signals measure the same thing (the combination sweep skips same-family pairs for exactly that reason).

The families also carry a measured finding. Of the 25 registered strategies run on five assets, the eight positive on all five are drawn from breakout, trend, momentum, regime-filter and volume-flow — and **not one is from a reversion family**. No reversion-family strategy clears all five. See `research/CROSS-ASSET-TRANSFER.md`.

| Family | Files | Matched on |
|---|---|---|
| `trend` | 197 | `trend`, `ma_crossover`, `macd`, `ichimoku` |
| `regime-filter` | 192 | `regime`, `sma_regime`, `adx_trend`, `hurst`, `vol_regime` |
| `baseline` | 135 | `buy_and_hold`, `baseline` |
| `oscillator-reversion` | 114 | `rsi`, `stochastic`, `oscillator` |
| `breakout` | 101 | `breakout`, `bb_breakout`, `keltner` |
| `mean-reversion` | 91 | `mean-reversion`, `zscore`, `bb_reversion`, `vwap_reversion`, `ou_reversion` |
| `momentum` | 91 | `momentum`, `ts_momentum`, `dual_momentum` |
| `volume-flow` | 74 | `obv`, `volume-flow` |
| `risk-overlay` | 38 | `voltarget`, `atr_sized`, `garch`, `risk-overlay` |

---

## Strategy-card axes

Facts already written in the 46 cards' frontmatter, inverted so a value points back at its cards. Useful for questions the prose does not index — "which specs were never implemented", "which are rated very-low and why".

### `evaluation`

- **None** (20) — `avellaneda_stoikov_mm`, `day_trading`, `dex_cex_dislocation`, `discount_to_anchor`, `event_driven`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence` and 8 more
- **single-split-70-30** (18) — `atr_position_sizing`, `bb_reversion`, `breakout`, `buy_and_hold`, `garch_vol_forecast`, `grid`, `ichimoku_cloud`, `keltner`, `ma_crossover`, `ma_ribbon`, `macd`, `pairs_cointegration` and 6 more
- **cpcv-8-groups-k2** (6) — `adx_filtered_trend`, `bb_breakout`, `dual_momentum_12_1`, `obv_trend`, `vol_regime_hmm`, `zscore`
- **null** (3) — `dca_bot`, `jlp_vs_sol_relative_value`, `triangular_arbitrage`
- **cpcv-8-groups-k2-sol-btc-eth** (2) — `hurst_regime_test`, `ou_half_life_sizing`
- **real-sol-daily-and-hourly-recentred-blocks** (1) — `ladder_grid`

### `family`

- **mean-reversion** (12) — `bb_reversion`, `dca_bot`, `discount_to_anchor`, `fib_retracement`, `grid`, `jlp_vs_sol_relative_value`, `kalman_hedge_ratio`, `ladder_grid`, `ou_half_life_sizing`, `pairs_cointegration`, `vwap_reversion`, `zscore`
- **crypto-native** (6) — `exchange_net_flow`, `funding_utilization_extremes`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence`, `staking_ratio_flow`
- **trend** (6) — `ema_crossover`, `ichimoku_cloud`, `ma_crossover`, `ma_ribbon`, `macd`, `ppo`
- **microstructure** (5) — `avellaneda_stoikov_mm`, `dex_cex_dislocation`, `order_book_imbalance`, `scalping`, `trade_flow_imbalance`
- **breakout** (4) — `bb_breakout`, `breakout`, `keltner`, `swing_confluence`
- **sma-gated** (4) — `atr_position_sizing`, `garch_vol_forecast`, `sma_regime`, `voltarget`
- **leverage-tier** (3) — `lev_high`, `lev_low`, `lev_medium`
- **momentum** (3) — `dual_momentum_12_1`, `ts_momentum`, `xs_momentum`
- **regime-filter** (3) — `adx_filtered_trend`, `hurst_regime_test`, `vol_regime_hmm`
- **baseline** (2) — `buy_and_hold`, `dca`
- **event** (2) — `event_driven`, `prediction_markets`
- **oscillator-reversion** (2) — `rsi`, `stochastic`
- **volatility** (2) — `implied_vs_realised_vol`, `vol_of_vol_term_structure`
- **alt-data** (1) — `social_sentiment`
- **arbitrage** (1) — `triangular_arbitrage`
- **intraday** (1) — `day_trading`
- **trigger** (1) — `trigger_trade`
- **volume-flow** (1) — `obv_trend`

### `status`

- **measured** (27) — `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `dual_momentum_12_1`, `garch_vol_forecast`, `grid`, `hurst_regime_test`, `ichimoku_cloud`, `keltner` and 15 more
- **spec-only** (20) — `avellaneda_stoikov_mm`, `day_trading`, `dex_cex_dislocation`, `discount_to_anchor`, `event_driven`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence` and 8 more
- **implemented** (12) — `dca`, `dca_bot`, `ema_crossover`, `fib_retracement`, `jlp_vs_sol_relative_value`, `lev_high`, `lev_low`, `lev_medium`, `ppo`, `swing_confluence`, `triangular_arbitrage`, `trigger_trade`

### `success_likelihood`

- **very-low** (34) — `avellaneda_stoikov_mm`, `day_trading`, `dca`, `dex_cex_dislocation`, `discount_to_anchor`, `dual_momentum_12_1`, `ema_crossover`, `event_driven`, `exchange_net_flow`, `fib_retracement`, `garch_vol_forecast`, `grid` and 22 more
- **low** (25) — `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `dca_bot`, `funding_utilization_extremes`, `hurst_regime_test`, `ichimoku_cloud`, `implied_vs_realised_vol`, `jlp_vs_sol_relative_value` and 13 more
