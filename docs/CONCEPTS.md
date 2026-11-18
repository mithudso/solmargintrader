# Conceptual index

**Generated** from `index/CONCEPT-INDEX.json` (2026-11-18T07:57:11+00:00). 21 concepts.

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

`risk-rails` · **2024 files** · matched on `dry_run`, `dryrun`, `risk`, `rails`, `kill`, `guard`, `confirm`, `fail-closed`

The extension can place real orders. Dry-run is the default, rails live in code and fail closed, and a fresh install must never be able to trade.

Strongest files:

- `research/json/tradingview-card-coverage.json` (1724 hits)
- `research/json/tradingview-script-understanding.json` (317 hits)
- `llms-executable.txt` (251 hits)
- `research/json/zec-expanded-20261113.llms/special-runner-summary.json` (228 hits)
- `docs/operations-registry.json` (222 hits)
- `docs/FILES.md` (182 hits)
- `llms-filemap.txt` (164 hits)
- `FILES.md` (157 hits)

Full list: `python3 index/search.py --concept risk-rails -n 2024`

### Cross-asset and cross-timeframe transfer

`transfer` · **1862 files** · matched on `cross_asset`, `cross-asset`, `transfer`, `doge`, `zec`, `universe`, `top_coins`

The same 25 strategies score 25/25 on BTC daily and 0/25 on SOL hourly. The dataset has repeatedly explained more than the strategy.

Strongest files:

- `llms-executable.txt` (504 hits)
- `memory.md` (421 hits)
- `docs/FILES.md` (415 hits)
- `llms-filemap.txt` (276 hits)
- `research/papers/coin-intelligence/zec-zcash.md` (196 hits)
- `extension/src/perps/archive-presets.js` (186 hits)
- `research/json/results/coinbase50_20261111_summary.json` (183 hits)
- `research/papers/coin-intelligence/doge-dogecoin.md` (147 hits)

Full list: `python3 index/search.py --concept transfer -n 1862`

### Cost model

`costs` · **1631 files** · matched on `fee_bps`, `slippage`, `slippage_bps`, `costconfig`, `break-even`, `borrow`, `financing`

Fees and slippage are never optional and must be applied exactly once. The engine runs fee_bps=6.0, slippage_bps=2.0, fill_delay=1.

Strongest files:

- `research/json/strategy_experiment/results/results.json` (2176 hits)
- `research/json/strategy_experiment/results/initial-gapped-run/results.json` (1632 hits)
- `research/json/zec-expanded-20261113.llms/special-runner-summary.json` (352 hits)
- `llms/jupsol-llms.txt` (117 hits)
- `llms-executable.txt` (107 hits)
- `research/scripts/ratio_rotation.py` (94 hits)
- `soltui/coin_fit.py` (73 hits)
- `backtester/core/engine.py` (69 hits)

Full list: `python3 index/search.py --concept costs -n 1631`

### Lookahead and fill timing

`lookahead` · **1575 files** · matched on `lookahead`, `fill_delay`, `warmup`, `warmup_bars`, `displacement`, `centred`, `shift`

A signal at bar t may use data only through t. Centred indicators, same-bar fills and displaced clouds are the recurring hazards.

Strongest files:

- `research/json/tradingview-card-coverage.json` (63 hits)
- `research/scripts/decide.py` (44 hits)
- `.cdo/reviews-2026-11-12/backtester-boundaries-tools.json` (42 hits)
- `.cdo/reviews-2026-11-12/medium-files.json` (42 hits)
- `research/json/strategy_experiment/audit_integrity.json` (40 hits)
- `research/json/tradingview-script-profiles/shard-b.jsonl` (39 hits)
- `research/scripts/ratio_rotation.py` (39 hits)
- `research/json/tradingview-script-profiles/shard-a.jsonl` (36 hits)

Full list: `python3 index/search.py --concept lookahead -n 1575`

### On-chain execution reality

`execution-onchain` · **1227 files** · matched on `jupiter`, `jlp`, `oracle`, `priority`, `slippage`, `perps`, `solana`

Oracle-priced perps, priority fees as a product, per-account fee markets, dropped-versus-reverted. Decides whether a strategy is executable at all.

Strongest files:

- `llms-executable.txt` (937 hits)
- `llms-filemap.txt` (752 hits)
- `docs/FILES.md` (700 hits)
- `docs/design/oracle-ui-2399/report.json` (668 hits)
- `research/json/strategy_experiment/results/results.json` (544 hits)
- `memory.md` (499 hits)
- `llms/jupsol-llms.txt` (427 hits)
- `research/json/strategy_experiment/results/initial-gapped-run/results.json` (408 hits)

Full list: `python3 index/search.py --concept execution-onchain -n 1227`

### Grid trading

`grid` · **940 files** · matched on `grid`, `gridsim`, `ladder`, `recenter`, `anchor_window`, `levels`

A resting grid converts a sustained trend into a maximum-size losing position; the re-centring gate fired once in 1,875 bars.

Strongest files:

- `research/json/tradingview-card-coverage.json` (800 hits)
- `research/json/results/coinbase50_20261111_summary.json` (530 hits)
- `research/json/tradingview-script-understanding.json` (256 hits)
- `llms-filemap.txt` (227 hits)
- `llms-executable.txt` (220 hits)
- `docs/FILES.md` (204 hits)
- `research/json/strategy_experiment/audit_realism.json` (178 hits)
- `FILES.md` (176 hits)

Full list: `python3 index/search.py --concept grid -n 940`

### Data integrity

`data-integrity` · **877 files** · matched on `validate_bars`, `strict_gaps`, `allow_gaps`, `datavalidationerror`, `monotone`, `gap`

Gaps refused rather than filled, columns resolved by name, timestamps monotone. A concatenated XRP series hides a 2.5-year join.

Strongest files:

- `research/json/zec-reversal-excursions-20261115/results.json` (528 hits)
- `research/json/strategy_experiment/results/initial-gapped-run/results.json` (272 hits)
- `research/json/tradingview-card-coverage.json` (267 hits)
- `research/json/tradingview-script-understanding.json` (144 hits)
- `ecosystem/web/styles.css` (109 hits)
- `research/json/tradingview-card-readiness.json` (106 hits)
- `llms-filemap.txt` (95 hits)
- `docs/FILES.md` (80 hits)

Full list: `python3 index/search.py --concept data-integrity -n 877`

### Buy-and-hold benchmark

`benchmark` · **638 files** · matched on `buy_and_hold`, `benchmark`, `baseline`

Zero parameters, and it out-ranked all but one or two strategies on SOL and all five recommended configurations on ZEC.

Strongest files:

- `.cdo/reviews-2026-11-12/coverage.json` (848 hits)
- `research/json/strategy_experiment/results/results.json` (560 hits)
- `research/json/strategy_experiment/results/initial-gapped-run/results.json` (424 hits)
- `research/json/results/news_events_20261112_manifest.json` (280 hits)
- `research/json/strategy_experiment/audit_realism.json` (178 hits)
- `research/json/tradingview-card-coverage.json` (112 hits)
- `docs/FILES.md` (92 hits)
- `.cdo/reviews-2026-11-12/research-scripts.json` (81 hits)

Full list: `python3 index/search.py --concept benchmark -n 638`

### Evidence floor

`evidence-floor` · **426 files** · matched on `min_total_trades`, `min_rankable_trades`, `insufficient`, `dropped`, `evidence floor`, `rankable`

Below a minimum trade count a result is not eligible to be reported as an improvement. cpcv_evaluate prints DROPPED but still returns paths, which is how a 6-trade Sharpe reached a headline.

Strongest files:

- `research/json/strategy_experiment/results/results.json` (334 hits)
- `research/json/strategy_experiment/results/initial-gapped-run/results.json` (284 hits)
- `research/json/strategy_experiment/audit_realism.json` (112 hits)
- `research/json/strategy_experiment/audit_realism.md` (112 hits)
- `research/scripts/cross_asset_cpcv.py` (67 hits)
- `research/json/strategy_experiment/audit_integrity.json` (55 hits)
- `research/json/strategy_experiment/audit_integrity.md` (54 hits)
- `soltui/cumulative.py` (39 hits)

Full list: `python3 index/search.py --concept evidence-floor -n 426`

### Combinatorial purged cross-validation

`cpcv` · **273 files** · matched on `cpcv`, `purged`, `combinatorial`, `n_groups`, `k_test`, `path_sharpes`

The repo's primary evaluation method: 8 blocks, k=2, up to 28 paths. Replaced the single 70/30 split, whose in-sample window ended on the highest close in the series.

Strongest files:

- `llms-executable.txt` (287 hits)
- `llms-filemap.txt` (105 hits)
- `docs/FILES.md` (84 hits)
- `FILES.md` (77 hits)
- `research/scripts/cpcv_sweep.py` (68 hits)
- `research/scripts/verify_numbers.py` (63 hits)
- `backtester/core/cpcv.py` (60 hits)
- `backtester/tests/test_cross_asset_cpcv.py` (41 hits)

Full list: `python3 index/search.py --concept cpcv -n 273`

### Overfitting and PBO

`overfitting-pbo` · **198 files** · matched on `pbo`, `overfitting`, `cscv`, `deflated`, `anti-informative`, `multiple-testing`

PBO measured 0.700 at daily horizons against a 0.500 noise line, so in-sample rank is anti-informative. This is the finding that governs how every other number here may be read.

Strongest files:

- `research/scripts/cpcv_sweep.py` (109 hits)
- `backtester/tests/test_cpcv.py` (62 hits)
- `research/papers/RANKED_LISTS.md` (42 hits)
- `research/scripts/verify_numbers.py` (39 hits)
- `FILES.md` (34 hits)
- `docs/FILES.md` (34 hits)
- `research/json/results/coinbase50_20261111_summary.json` (33 hits)
- `research/scripts/geometry.py` (30 hits)

Full list: `python3 index/search.py --concept overfitting-pbo -n 198`

### Perturbation and robustness

`robustness` · **198 files** · matched on `perturb`, `perturbation`, `ratio_to_iqr`, `sign_flips`, `stability`

Second independent axis beside CPCV: nudge each parameter +/-10% and re-run. A point that collapses is a spike, not a plateau.

Strongest files:

- `llms-filemap.txt` (132 hits)
- `docs/FILES.md` (107 hits)
- `FILES.md` (100 hits)
- `llms-executable.txt` (89 hits)
- `research/scripts/perturb.py` (56 hits)
- `research/json/native-pairs-week-20261117/markets/ETH-USD/summary.json` (33 hits)
- `llms-sitemap.txt` (32 hits)
- `research/json/zec-expanded-20261113.llms/summary-statistics.json` (32 hits)

Full list: `python3 index/search.py --concept robustness -n 198`

---

## Strategy families

These are not editorial: each is a value of the `FAMILY` dict in `backtester/core/strategies/__init__.py`, which is what the engine itself uses to decide that two signals measure the same thing (the combination sweep skips same-family pairs for exactly that reason).

The families also carry a historical measured finding. Of the study's 25 strategies run on five assets, the eight positive on all five are drawn from breakout, trend, momentum, regime-filter and volume-flow — and **not one is from a reversion family**. No reversion-family strategy clears all five. See `research/CROSS-ASSET-TRANSFER.md`.

| Family | Files | Matched on |
|---|---|---|
| `trend` | 946 | `trend`, `ma_crossover`, `macd`, `ichimoku` |
| `oscillator-reversion` | 630 | `rsi`, `stochastic`, `oscillator` |
| `baseline` | 565 | `buy_and_hold`, `baseline` |
| `momentum` | 483 | `momentum`, `ts_momentum`, `dual_momentum` |
| `regime-filter` | 390 | `regime`, `sma_regime`, `adx_trend`, `hurst`, `vol_regime` |
| `breakout` | 312 | `breakout`, `bb_breakout`, `keltner` |
| `mean-reversion` | 168 | `mean-reversion`, `zscore`, `bb_reversion`, `vwap_reversion`, `ou_reversion` |
| `volume-flow` | 166 | `obv`, `volume-flow` |
| `risk-overlay` | 73 | `voltarget`, `atr_sized`, `garch`, `risk-overlay` |

---

## Strategy-card axes

Facts already written in indexed frontmatter, inverted so a value points back at its source files. Useful for questions the prose does not index — "which specs were never implemented", "which are rated very-low and why".

### `evaluation`

- **null** (1769) — `dca_bot`, `jlp_vs_sol_relative_value`, `triangular_arbitrage`, `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc`, `tv_43000474007_understanding_range_charts`, `tv_43000502272_learn_to_use_kagi_charts`, `tv_43000502273_introduction_to_line_break_charts`, `tv_43000502276_learn_using_point_and_figure_charts`, `tv_43000724995_understanding_volume_candle_charts`, `tv_43000725590_time_price_opportunity_charts_explained`, `tv_43000745275_session_volume_profile_charts_explained`, `tv_43000762388_understanding_crypto_open_interest` and 1757 more
- **None** (20) — `avellaneda_stoikov_mm`, `day_trading`, `dex_cex_dislocation`, `discount_to_anchor`, `event_driven`, `exchange_net_flow`, `funding_utilization_extremes`, `implied_vs_realised_vol`, `kalman_hedge_ratio`, `liquidation_cascade_proximity`, `mvrv_nupl_valuation`, `open_interest_divergence` and 8 more
- **single-split-70-30** (18) — `pairs_cointegration`, `atr_position_sizing`, `bb_reversion`, `breakout`, `buy_and_hold`, `garch_vol_forecast`, `grid`, `ichimoku_cloud`, `keltner`, `ma_crossover`, `ma_ribbon`, `macd` and 6 more
- **cpcv-8-groups-k2** (6) — `adx_filtered_trend`, `bb_breakout`, `dual_momentum_12_1`, `obv_trend`, `vol_regime_hmm`, `zscore`
- **cpcv-8-groups-k2-sol-btc-eth** (2) — `hurst_regime_test`, `ou_half_life_sizing`
- **ZEC 250-trial study 2026-11-10: chronological 50/50 holdout and five expanding walk-forward folds; 10 bps fee, 2 bps slippage, 0.1 bps/hour synthetic carry** (1) — `volty_expan_close`
- **real-sol-daily-and-hourly-recentred-blocks** (1) — `ladder_grid`

### `family`

- **source-defined** (939) — `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc`, `tv_43000474007_understanding_range_charts`, `tv_43000502272_learn_to_use_kagi_charts`, `tv_43000502273_introduction_to_line_break_charts`, `tv_43000502276_learn_using_point_and_figure_charts`, `tv_43000724995_understanding_volume_candle_charts`, `tv_43000725590_time_price_opportunity_charts_explained`, `tv_43000745275_session_volume_profile_charts_explained`, `tv_43000762388_understanding_crypto_open_interest`, `tv_43000762390_funding_rate_a_guide_to_market_sentiment`, `tv_4psxdoyc_a_technique_from_1202_really`, `tv_7biqbrfz_how_to_utilize_multi_time_frame_analysis_in_your_trading` and 927 more
- **research-method** (65) — `tv_method_bump_run`, `tv_method_candlestick_patterns`, `tv_method_cup_handle`, `tv_method_double_top_bottom`, `tv_method_elliott_wave`, `tv_method_flag_pennant`, `tv_method_fourier_cycle`, `tv_method_gann`, `tv_method_gap_fill`, `tv_method_hammer`, `tv_method_harami`, `tv_method_harmonic_xabcd` and 53 more
- **trend** (32) — `ema_crossover`, `ichimoku_cloud`, `tv_builtin_accumulative_swing_index`, `tv_builtin_chop_zone`, `tv_builtin_moving_average_adaptive`, `tv_builtin_moving_average_channel`, `tv_builtin_parabolic_sar`, `tv_builtin_supertrend`, `tv_builtin_williams_alligator`, `ma_crossover`, `ma_ribbon`, `macd` and 20 more
- **momentum** (20) — `dual_momentum_12_1`, `tv_builtin_fisher_transform`, `ts_momentum`, `tv_builtin_accelerator_oscillator`, `tv_builtin_awesome_oscillator`, `tv_builtin_chande_momentum_oscillator`, `tv_builtin_connors_rsi`, `tv_builtin_coppock_curve`, `tv_builtin_detrended_price_oscillator`, `tv_builtin_know_sure_thing`, `tv_builtin_momentum`, `tv_builtin_rank_correlation_index` and 8 more
- **other** (16) — `tv_builtin_compare`, `tv_builtin_overlay`, `tv_builtin_52_week_high_low`, `tv_builtin_advance_decline`, `tv_builtin_average_price`, `tv_builtin_correlation_coefficient`, `tv_builtin_correlation_log`, `tv_builtin_majority_rule`, `tv_builtin_median_price`, `tv_builtin_pivot_points_standard`, `tv_builtin_ratio`, `tv_builtin_regression_trend` and 4 more
- **volatility** (14) — `tv_builtin_relative_volatility_index`, `tv_builtin_standard_error_bands`, `tv_builtin_volatility_index`, `implied_vs_realised_vol`, `tv_builtin_bollinger_bands_b`, `tv_builtin_bollinger_bands_width`, `tv_builtin_chaikin_volatility`, `tv_builtin_chande_kroll_stop`, `tv_builtin_envelopes`, `tv_builtin_mass_index`, `tv_builtin_standard_error`, `tv_builtin_volatility_o_h_l_c` and 2 more
- **volume** (13) — `tv_builtin_klinger_oscillator`, `tv_builtin_session_volume_profile`, `tv_builtin_volume_profile_fixed_range`, `tv_builtin_volume_profile_visible_range`, `tv_builtin_accumulation_distribution`, `tv_builtin_anchored_vwap`, `tv_builtin_chaikin_oscillator`, `tv_builtin_ease_of_movement`, `tv_builtin_elder_s_force_index`, `tv_builtin_money_flow_index`, `tv_builtin_net_volume`, `tv_builtin_price_volume_trend` and 1 more
- **mean-reversion** (12) — `dca_bot`, `jlp_vs_sol_relative_value`, `ladder_grid`, `pairs_cointegration`, `bb_reversion`, `fib_retracement`, `grid`, `ou_half_life_sizing`, `vwap_reversion`, `zscore`, `discount_to_anchor`, `kalman_hedge_ratio`
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
- **volatility-breakout** (1) — `volty_expan_close`
- **volume-flow** (1) — `obv_trend`

### `status`

- **spec-only** (1108) — `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc`, `tv_43000474007_understanding_range_charts`, `tv_43000502272_learn_to_use_kagi_charts`, `tv_43000502273_introduction_to_line_break_charts`, `tv_43000502276_learn_using_point_and_figure_charts`, `tv_43000724995_understanding_volume_candle_charts`, `tv_43000725590_time_price_opportunity_charts_explained`, `tv_43000745275_session_volume_profile_charts_explained`, `tv_43000762388_understanding_crypto_open_interest`, `tv_43000762390_funding_rate_a_guide_to_market_sentiment`, `tv_4psxdoyc_a_technique_from_1202_really`, `tv_7biqbrfz_how_to_utilize_multi_time_frame_analysis_in_your_trading` and 1096 more
- **documentation-only** (678) — `tv_2lgyzykc_ultimate_strategy_template`, `tv_9iwinz7i_how_to_use_leverage_and_margin_in_pinescript`, `tv_ihvpg6ts_stop_loss_and_take_profit_in_example`, `tv_kzp8e4x3_monthly_returns_in_pinescript_strategies`, `tv_m9taaikp_oscillator_evaluator_analysis_tool`, `tv_n8bgynwl_template_trailing_strategy_backtester`, `tv_otfw8b2a_trading_report_generator_from_csv`, `tv_xaeg4zjg_how_to_set_backtest_time_ranges`, `tv_00jfil5w_security_revisited_pinecoders`, `tv_06gcx5ql_innovation_adaptive_kalman_filter_oscillator`, `tv_0enoetmo_smartphase_analyzer`, `tv_0ghsw1kr_moving_regression` and 666 more
- **measured** (28) — `ladder_grid`, `pairs_cointegration`, `volty_expan_close`, `adx_filtered_trend`, `atr_position_sizing`, `bb_breakout`, `bb_reversion`, `breakout`, `buy_and_hold`, `dual_momentum_12_1`, `garch_vol_forecast`, `grid` and 16 more
- **implemented** (12) — `dca_bot`, `jlp_vs_sol_relative_value`, `triangular_arbitrage`, `dca`, `ema_crossover`, `fib_retracement`, `lev_high`, `lev_low`, `lev_medium`, `ppo`, `swing_confluence`, `trigger_trade`

### `success_likelihood`

- **low** (1113) — `dca_bot`, `jlp_vs_sol_relative_value`, `ladder_grid`, `pairs_cointegration`, `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc`, `tv_43000474007_understanding_range_charts`, `tv_43000502272_learn_to_use_kagi_charts`, `tv_43000502273_introduction_to_line_break_charts`, `tv_43000502276_learn_using_point_and_figure_charts`, `tv_43000724995_understanding_volume_candle_charts`, `tv_43000725590_time_price_opportunity_charts_explained`, `tv_43000745275_session_volume_profile_charts_explained` and 1101 more
- **very-low** (35) — `triangular_arbitrage`, `volty_expan_close`, `dca`, `dual_momentum_12_1`, `ema_crossover`, `fib_retracement`, `garch_vol_forecast`, `grid`, `keltner`, `lev_high`, `lev_low`, `lev_medium` and 23 more
