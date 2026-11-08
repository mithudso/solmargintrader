# Conceptual index

**Generated** from `index/CONCEPT-INDEX.json` (2026-11-08T09:59:05+00:00). 21 concepts.

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

### Cost model

`costs` · **1299 files** · matched on `fee_bps`, `slippage`, `slippage_bps`, `costconfig`, `break-even`, `borrow`, `financing`

Fees and slippage are never optional and must be applied exactly once. The engine runs fee_bps=6.0, slippage_bps=2.0, fill_delay=1.

Strongest files:

- `research/ratio_rotation.py` (89 hits)
- `skills/trading-and-investing/references/jupiter-perps-trading.md` (61 hits)
- `backtester/tests/test_engine.py` (58 hits)
- `backtester/core/gridsim.py` (55 hits)
- `research/tradingview-card-coverage.json` (55 hits)
- `backtester/core/engine.py` (54 hits)
- `llms-full.txt` (46 hits)
- `backtester/core/dcasim.py` (37 hits)

Full list: `python3 index/search.py --concept costs -n 1299`

### Risk rails and dry-run safety

`risk-rails` · **467 files** · matched on `dry_run`, `dryrun`, `risk`, `rails`, `kill`, `guard`, `confirm`, `fail-closed`

The extension can place real orders. Dry-run is the default, rails live in code and fail closed, and a fresh install must never be able to trade.

Strongest files:

- `research/tradingview-card-coverage.json` (1637 hits)
- `docs/FILES.md` (87 hits)
- `skills/trading-and-investing/references/jlp-risk-profile-and-anti-patterns.md` (86 hits)
- `skills/trading-and-investing/references/trading-risk-management.md` (84 hits)
- `llms-full.txt` (62 hits)
- `skills/trading-and-investing/references/strategies-and-risk.md` (54 hits)
- `skills/trading-and-investing/SKILL.md` (51 hits)
- `soltui/tui.py` (39 hits)

Full list: `python3 index/search.py --concept risk-rails -n 467`

### Grid trading

`grid` · **370 files** · matched on `grid`, `gridsim`, `ladder`, `recenter`, `anchor_window`, `levels`

A resting grid converts a sustained trend into a maximum-size losing position; the re-centring gate fired once in 1,875 bars.

Strongest files:

- `research/tradingview-card-coverage.json` (800 hits)
- `backtester/tests/test_gridsim.py` (167 hits)
- `llms-full.txt` (129 hits)
- `skills/trading-and-investing/references/grid-trading-strategy.md` (128 hits)
- `backtester/core/gridsim.py` (102 hits)
- `docs/FILES.md` (102 hits)
- `extension/src/core/grid.js` (66 hits)
- `backtester/strategy_cards/ladder_grid.md` (57 hits)

Full list: `python3 index/search.py --concept grid -n 370`

### On-chain execution reality

`execution-onchain` · **337 files** · matched on `jupiter`, `jlp`, `oracle`, `priority`, `slippage`, `perps`, `solana`

Oracle-priced perps, priority fees as a product, per-account fee markets, dropped-versus-reverted. Decides whether a strategy is executable at all.

Strongest files:

- `skills/trading-and-investing/references/jupiter-jlp-pool.md` (163 hits)
- `docs/FILES.md` (152 hits)
- `skills/trading-and-investing/references/jupiter-swap-routing-and-orders.md` (127 hits)
- `skills/trading-and-investing/references/jupiter-perps-trading.md` (125 hits)
- `skills/trading-and-investing/references/jlp-risk-profile-and-anti-patterns.md` (124 hits)
- `skills/trading-and-investing/SKILL.md` (109 hits)
- `llms-full.txt` (102 hits)
- `pagesource` (98 hits)

Full list: `python3 index/search.py --concept execution-onchain -n 337`

### Data integrity

`data-integrity` · **258 files** · matched on `validate_bars`, `strict_gaps`, `allow_gaps`, `datavalidationerror`, `monotone`, `gap`

Gaps refused rather than filled, columns resolved by name, timestamps monotone. A concatenated XRP series hides a 2.5-year join.

Strongest files:

- `research/tradingview-card-coverage.json` (267 hits)
- `docs/FILES.md` (52 hits)
- `soltui/bots.py` (39 hits)
- `backtester/tests/test_engine.py` (34 hits)
- `backtester/core/data.py` (33 hits)
- `research/STRATEGIES.md` (32 hits)
- `docs/TRADINGVIEW-CARD-FILES.md` (28 hits)
- `extension/src/ui/ui.css` (28 hits)

Full list: `python3 index/search.py --concept data-integrity -n 258`

### Cross-asset and cross-timeframe transfer

`transfer` · **223 files** · matched on `cross_asset`, `cross-asset`, `transfer`, `doge`, `zec`, `universe`, `top_coins`

The same 25 strategies score 25/25 on BTC daily and 0/25 on SOL hourly. The dataset has repeatedly explained more than the strategy.

Strongest files:

- `research/coin-intelligence/zec-zcash.md` (196 hits)
- `research/coin-intelligence/doge-dogecoin.md` (147 hits)
- `research/results/frontier-2026-11-07.json` (62 hits)
- `research/results/minute_sweep_x1_common.txt` (54 hits)
- `docs/FILES.md` (53 hits)
- `research/CROSS-ASSET-TRANSFER.md` (51 hits)
- `docs/SCRIPTS.md` (45 hits)
- `backtester/tests/test_universe.py` (44 hits)

Full list: `python3 index/search.py --concept transfer -n 223`

### Evidence floor

`evidence-floor` · **180 files** · matched on `min_total_trades`, `min_rankable_trades`, `insufficient`, `dropped`, `evidence floor`, `rankable`

Below a minimum trade count a result is not eligible to be reported as an improvement. cpcv_evaluate prints DROPPED but still returns paths, which is how a 6-trade Sharpe reached a headline.

Strongest files:

- `research/cross_asset_cpcv.py` (67 hits)
- `soltui/cumulative.py` (40 hits)
- `research/CANDLE-GAP-AUDIT.md` (36 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (33 hits)
- `research/tradingview-card-coverage.json` (33 hits)
- `research/ratio_rotation.py` (22 hits)
- `docs/FILES.md` (19 hits)
- `index/build.py` (19 hits)

Full list: `python3 index/search.py --concept evidence-floor -n 180`

### Buy-and-hold benchmark

`benchmark` · **175 files** · matched on `buy_and_hold`, `benchmark`, `baseline`

Zero parameters, and it out-ranked all but one or two strategies on SOL and all five recommended configurations on ZEC.

Strongest files:

- `research/tradingview-card-coverage.json` (112 hits)
- `docs/FILES.md` (34 hits)
- `research/perturb.py` (29 hits)
- `research/RANKED_LISTS.md` (25 hits)
- `backtester/core/deflated_sharpe.py` (21 hits)
- `memory.md` (15 hits)
- `backtester/core/dcasim.py` (15 hits)
- `docs/CONCEPTS.md` (14 hits)

Full list: `python3 index/search.py --concept benchmark -n 175`

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

### Lookahead and fill timing

`lookahead` · **124 files** · matched on `lookahead`, `fill_delay`, `warmup`, `warmup_bars`, `displacement`, `centred`, `shift`

A signal at bar t may use data only through t. Centred indicators, same-bar fills and displaced clouds are the recurring hazards.

Strongest files:

- `research/tradingview-card-coverage.json` (63 hits)
- `docs/TRADINGVIEW-REFERENCE.md` (31 hits)
- `research/decide.py` (21 hits)
- `backtester/tests/test_engine.py` (17 hits)
- `skills/trading-and-investing/references/indicator-signal-implementation-and-backtesting.md` (17 hits)
- `backtester/core/trigger_conditions.py` (16 hits)
- `backtester/core/strategies/advanced.py` (14 hits)
- `skills/trading-and-investing/references/signal-pairing-volume-and-pattern-signal-sets.md` (14 hits)

Full list: `python3 index/search.py --concept lookahead -n 124`

### Overfitting and PBO

`overfitting-pbo` · **112 files** · matched on `pbo`, `overfitting`, `cscv`, `deflated`, `anti-informative`, `multiple-testing`

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

Full list: `python3 index/search.py --concept overfitting-pbo -n 112`

### Perturbation and robustness

`robustness` · **103 files** · matched on `perturb`, `perturbation`, `ratio_to_iqr`, `sign_flips`, `stability`

Second independent axis beside CPCV: nudge each parameter +/-10% and re-run. A point that collapses is a spike, not a plateau.

Strongest files:

- `docs/FILES.md` (98 hits)
- `research/perturb.py` (54 hits)
- `research/verify_numbers.py` (31 hits)
- `research/RANKED_LISTS.md` (25 hits)
- `research/tradingview-card-coverage.json` (23 hits)
- `soltui/compound.py` (16 hits)
- `research/coin-intelligence/sol-solana.md` (11 hits)
- `research/triggers.py` (10 hits)

Full list: `python3 index/search.py --concept robustness -n 103`

---

## Strategy families

These are not editorial: each is a value of the `FAMILY` dict in `backtester/core/strategies/__init__.py`, which is what the engine itself uses to decide that two signals measure the same thing (the combination sweep skips same-family pairs for exactly that reason).

The families also carry a measured finding. Of the 25 registered strategies run on five assets, the eight positive on all five are drawn from breakout, trend, momentum, regime-filter and volume-flow — and **not one is from a reversion family**. No reversion-family strategy clears all five. See `research/CROSS-ASSET-TRANSFER.md`.

| Family | Files | Matched on |
|---|---|---|
| `trend` | 452 | `trend`, `ma_crossover`, `macd`, `ichimoku` |
| `oscillator-reversion` | 267 | `rsi`, `stochastic`, `oscillator` |
| `regime-filter` | 210 | `regime`, `sma_regime`, `adx_trend`, `hurst`, `vol_regime` |
| `momentum` | 197 | `momentum`, `ts_momentum`, `dual_momentum` |
| `baseline` | 148 | `buy_and_hold`, `baseline` |
| `breakout` | 144 | `breakout`, `bb_breakout`, `keltner` |
| `mean-reversion` | 95 | `mean-reversion`, `zscore`, `bb_reversion`, `vwap_reversion`, `ou_reversion` |
| `volume-flow` | 85 | `obv`, `volume-flow` |
| `risk-overlay` | 40 | `voltarget`, `atr_sized`, `garch`, `risk-overlay` |

---

## Strategy-card axes

Facts already written in the 46 cards' frontmatter, inverted so a value points back at its cards. Useful for questions the prose does not index — "which specs were never implemented", "which are rated very-low and why".

### `evaluation`

- **null** (1086) — `dca_bot`, `jlp_vs_sol_relative_value`, `triangular_arbitrage`, `tv_06gcx5ql_innovation_adaptive_kalman_filter_oscillator`, `tv_0enoetmo_smartphase_analyzer`, `tv_0ghsw1kr_moving_regression`, `tv_0j7owdat_flowscope_hapharmonic`, `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc`, `tv_0nz4m9e7_holographic_market_microstructure_alphanatt`, `tv_0s4usqeb_nasan_risk_score_postion_size_estimator`, `tv_0sbntaqj_trading_abc`, `tv_0x1dgqjw_xabcd_harmonic_pattern_custom_range_interactive` and 1074 more
- **None** (20) — `avellaneda_stoikov_mm`, `day_trading`, `dex_cex_dislocation`, `discount_to_anchor`, `event_driven`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence` and 8 more
- **single-split-70-30** (18) — `atr_position_sizing`, `bb_reversion`, `breakout`, `buy_and_hold`, `garch_vol_forecast`, `grid`, `ichimoku_cloud`, `keltner`, `ma_crossover`, `ma_ribbon`, `macd`, `pairs_cointegration` and 6 more
- **cpcv-8-groups-k2** (6) — `adx_filtered_trend`, `bb_breakout`, `dual_momentum_12_1`, `obv_trend`, `vol_regime_hmm`, `zscore`
- **cpcv-8-groups-k2-sol-btc-eth** (2) — `hurst_regime_test`, `ou_half_life_sizing`
- **real-sol-daily-and-hourly-recentred-blocks** (1) — `ladder_grid`

### `family`

- **source-defined** (934) — `tv_06gcx5ql_innovation_adaptive_kalman_filter_oscillator`, `tv_0enoetmo_smartphase_analyzer`, `tv_0ghsw1kr_moving_regression`, `tv_0j7owdat_flowscope_hapharmonic`, `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc`, `tv_0nz4m9e7_holographic_market_microstructure_alphanatt`, `tv_0s4usqeb_nasan_risk_score_postion_size_estimator`, `tv_0sbntaqj_trading_abc`, `tv_0x1dgqjw_xabcd_harmonic_pattern_custom_range_interactive`, `tv_10xmhfge_volume_per_point`, `tv_119rqjou_potential_breakout_on_btcusd_to_the_upside`, `tv_12m8jqu6_function_polynomial_regression` and 922 more
- **research-method** (65) — `tv_method_atr_trailing`, `tv_method_bump_run`, `tv_method_candlestick_patterns`, `tv_method_covered_call`, `tv_method_cup_handle`, `tv_method_doji`, `tv_method_dominance_rotation`, `tv_method_double_top_bottom`, `tv_method_elliott_wave`, `tv_method_engulfing`, `tv_method_fair_value_gap`, `tv_method_fib_extensions` and 53 more
- **trend** (32) — `ema_crossover`, `ichimoku_cloud`, `ma_crossover`, `ma_ribbon`, `macd`, `ppo`, `tv_builtin_accumulative_swing_index`, `tv_builtin_arnaud_legoux_moving_average`, `tv_builtin_aroon`, `tv_builtin_chop_zone`, `tv_builtin_choppiness_index`, `tv_builtin_double_ema` and 20 more
- **momentum** (20) — `dual_momentum_12_1`, `ts_momentum`, `tv_builtin_accelerator_oscillator`, `tv_builtin_awesome_oscillator`, `tv_builtin_chande_momentum_oscillator`, `tv_builtin_connors_rsi`, `tv_builtin_coppock_curve`, `tv_builtin_detrended_price_oscillator`, `tv_builtin_fisher_transform`, `tv_builtin_know_sure_thing`, `tv_builtin_momentum`, `tv_builtin_rank_correlation_index` and 8 more
- **other** (16) — `tv_builtin_52_week_high_low`, `tv_builtin_advance_decline`, `tv_builtin_average_price`, `tv_builtin_compare`, `tv_builtin_correlation_coefficient`, `tv_builtin_correlation_log`, `tv_builtin_majority_rule`, `tv_builtin_median_price`, `tv_builtin_overlay`, `tv_builtin_pivot_points_standard`, `tv_builtin_ratio`, `tv_builtin_regression_trend` and 4 more
- **volatility** (14) — `implied_vs_realised_vol`, `tv_builtin_bollinger_bands_b`, `tv_builtin_bollinger_bands_width`, `tv_builtin_chaikin_volatility`, `tv_builtin_chande_kroll_stop`, `tv_builtin_envelopes`, `tv_builtin_mass_index`, `tv_builtin_relative_volatility_index`, `tv_builtin_standard_error`, `tv_builtin_standard_error_bands`, `tv_builtin_volatility_index`, `tv_builtin_volatility_o_h_l_c` and 2 more
- **volume** (13) — `tv_builtin_accumulation_distribution`, `tv_builtin_anchored_vwap`, `tv_builtin_chaikin_oscillator`, `tv_builtin_ease_of_movement`, `tv_builtin_elder_s_force_index`, `tv_builtin_klinger_oscillator`, `tv_builtin_money_flow_index`, `tv_builtin_net_volume`, `tv_builtin_price_volume_trend`, `tv_builtin_session_volume_profile`, `tv_builtin_volume_oscillator`, `tv_builtin_volume_profile_fixed_range` and 1 more
- **mean-reversion** (12) — `bb_reversion`, `dca_bot`, `discount_to_anchor`, `fib_retracement`, `grid`, `jlp_vs_sol_relative_value`, `kalman_hedge_ratio`, `ladder_grid`, `ou_half_life_sizing`, `pairs_cointegration`, `vwap_reversion`, `zscore`
- **crypto-native** (6) — `exchange_net_flow`, `funding_utilization_extremes`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence`, `staking_ratio_flow`
- **microstructure** (5) — `avellaneda_stoikov_mm`, `dex_cex_dislocation`, `order_book_imbalance`, `scalping`, `trade_flow_imbalance`
- **breakout** (4) — `bb_breakout`, `breakout`, `keltner`, `swing_confluence`
- **sma-gated** (4) — `atr_position_sizing`, `garch_vol_forecast`, `sma_regime`, `voltarget`
- **leverage-tier** (3) — `lev_high`, `lev_low`, `lev_medium`
- **regime-filter** (3) — `adx_filtered_trend`, `hurst_regime_test`, `vol_regime_hmm`
- **baseline** (2) — `buy_and_hold`, `dca`
- **event** (2) — `event_driven`, `prediction_markets`
- **oscillator-reversion** (2) — `rsi`, `stochastic`
- **alt-data** (1) — `social_sentiment`
- **arbitrage** (1) — `triangular_arbitrage`
- **intraday** (1) — `day_trading`
- **trigger** (1) — `trigger_trade`
- **volume-flow** (1) — `obv_trend`

### `status`

- **spec-only** (1103) — `avellaneda_stoikov_mm`, `day_trading`, `dex_cex_dislocation`, `discount_to_anchor`, `event_driven`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence` and 1091 more
- **measured** (27) — `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `dual_momentum_12_1`, `garch_vol_forecast`, `grid`, `hurst_regime_test`, `ichimoku_cloud`, `keltner` and 15 more
- **implemented** (12) — `dca`, `dca_bot`, `ema_crossover`, `fib_retracement`, `jlp_vs_sol_relative_value`, `lev_high`, `lev_low`, `lev_medium`, `ppo`, `swing_confluence`, `triangular_arbitrage`, `trigger_trade`

### `success_likelihood`

- **low** (1108) — `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `dca_bot`, `funding_utilization_extremes`, `hurst_regime_test`, `ichimoku_cloud`, `implied_vs_realised_vol`, `jlp_vs_sol_relative_value` and 1096 more
- **very-low** (34) — `avellaneda_stoikov_mm`, `day_trading`, `dca`, `dex_cex_dislocation`, `discount_to_anchor`, `dual_momentum_12_1`, `ema_crossover`, `event_driven`, `exchange_net_flow`, `fib_retracement`, `garch_vol_forecast`, `grid` and 22 more
