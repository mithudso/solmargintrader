# TradingView indicator and strategy card coverage

Version: 1.1.0 (2026-11-08). Delta: preserve source coverage across active and incomplete research cards.

Created **1083 specification cards** after checking existing cards, the strategy registry, indicator functions and Compound scorecard. Existing code and measured cards keep their status.

The subsequent completeness review keeps **292 new usable specifications** in the
active directory and moves **791 incomplete cards** to
`backtester/strategy_cards/incomplete/`. All 59 pre-existing cards stay active;
the active catalog has 351 cards and all 1,142 remain preserved. See
[the per-card readiness report](TRADINGVIEW-CARD-READINESS.md) and
`research/tradingview-card-readiness.json` for exact evidence, paths and gaps.
The creation dispositions below record the original existence check, not runtime
support or a claim that every newly created card is complete.

Scope: 114 built-in studies; 747 canonical script publications; 1610 canonical chart/idea publications; 2323 canonical help solutions (313 financial definition candidates); 90 other Markdown exports; 45 distinct ta-library functions plus 72 checked moving-average/candlestick/harmonic function definitions. Duplicate Markdown/HTML captures share a source row.

Publication HTML descriptions were read from `ssrIdeaData`, and help definitions from `solution.description`, not from menus, related publications or chart widget state. Captured publication script.content fields are empty. Descriptions can contain formulas and illustrative Pine snippets; no repository implementation is inferred from them. Cards preserve bounded author passages, explicit source gaps and required validation. Generic method formulas are reference specifications, not reverse-engineered proprietary code.

The machine-readable ledger is `research/tradingview-card-coverage.json`. Each publication carries its URL, physical-source hashes, normalized-description hash, excerpts with Unicode-codepoint offsets, disposition, match rationale and card/code targets. Built-in rows retain the exact input-catalog line.

The full inventory and initial matching used deterministic source extraction and curated aliases. Independent review screened 401 candidate chart titles, inspected targeted full descriptions, and audited 72 library functions plus 313 help-definition candidates. This is a complete file inventory with targeted semantic review; it is not a claim that every chart commentary page received an independent human-style semantic audit.

## How existence was checked

- Reuse a card for the same mechanism or an exact study alias. A default mismatch is a parity caveat, not another strategy.
- Reuse a scorecard/indicator function when the indicator already exists without a standalone strategy card.
- Preserve custom composite indicators separately. Mentioning RSI or MACD does not prove equivalence to the existing RSI or MACD strategy.
- Give reusable chart methods one shared specification. Keep one-off asset/price forecasts as source records; do not turn their targets into invented reusable rules.
- Keep platform tools, art, games, developer libraries and trading psychology outside the strategy roster. Record their exclusion and any referenced financial concepts.

## What these cards make available

The card CLI loads the active directory only. The SolTUI Docs index can find both
active and incomplete cards for research. SolTUI’s Strategies roster still lists
executable registry entries. Creating or retaining a `spec-only` card does not
make it runnable, backtestable or forward-testable. No executable trading rule or
order path changed.

## Built-in studies

| Study | Disposition | Card or existing code |
| --- | --- | --- |
| 52 Week High/Low | new-card | `tv_builtin_52_week_high_low` |
| Accelerator Oscillator | new-card | `tv_builtin_accelerator_oscillator` |
| Accumulation/Distribution | new-card | `tv_builtin_accumulation_distribution` |
| Accumulative Swing Index | new-card | `tv_builtin_accumulative_swing_index` |
| Advance/Decline | new-card | `tv_builtin_advance_decline` |
| Arnaud Legoux Moving Average | new-card | `tv_builtin_arnaud_legoux_moving_average` |
| Aroon | new-card | `tv_builtin_aroon` |
| Average Directional Index | existing | `adx_filtered_trend`, `backtester/core/indicators.py:directional_movement` |
| Average Price | new-card | `tv_builtin_average_price` |
| Average True Range | existing | `atr_position_sizing`, `backtester/core/indicators.py:atr` |
| Awesome Oscillator | new-card | `tv_builtin_awesome_oscillator` |
| Balance of Power | existing-code | `backtester/core/scorecard.py:_c_bop` |
| Bollinger Bands | existing | `bb_reversion`, `backtester/core/indicators.py:bollinger` |
| Bollinger Bands %B | new-card | `tv_builtin_bollinger_bands_b` |
| Bollinger Bands Width | new-card | `tv_builtin_bollinger_bands_width` |
| Chaikin Money Flow | existing-code | `backtester/core/scorecard.py:_c_cmf` |
| Chaikin Oscillator | new-card | `tv_builtin_chaikin_oscillator` |
| Chaikin Volatility | new-card | `tv_builtin_chaikin_volatility` |
| Chande Kroll Stop | new-card | `tv_builtin_chande_kroll_stop` |
| Chande Momentum Oscillator | new-card | `tv_builtin_chande_momentum_oscillator` |
| Chop Zone | new-card | `tv_builtin_chop_zone` |
| Choppiness Index | new-card | `tv_builtin_choppiness_index` |
| Commodity Channel Index | existing-code | `backtester/core/scorecard.py:_c_cci` |
| Connors RSI | new-card | `tv_builtin_connors_rsi` |
| Coppock Curve | new-card | `tv_builtin_coppock_curve` |
| Correlation Coefficient | new-card | `tv_builtin_correlation_coefficient` |
| Correlation - Log | new-card | `tv_builtin_correlation_log` |
| Detrended Price Oscillator | new-card | `tv_builtin_detrended_price_oscillator` |
| Directional Movement | existing | `adx_filtered_trend`, `backtester/core/indicators.py:directional_movement` |
| Donchian Channels | existing | `breakout`, `backtester/core/strategies/breakout.py:DonchianBreakout` |
| Double EMA | new-card | `tv_builtin_double_ema` |
| Ease of Movement | new-card | `tv_builtin_ease_of_movement` |
| Elder's Force Index | new-card | `tv_builtin_elder_s_force_index` |
| EMA Cross | existing | `ema_crossover`, `backtester/core/strategies/textbook.py:EmaCrossover` |
| Envelopes | new-card | `tv_builtin_envelopes` |
| Fisher Transform | new-card | `tv_builtin_fisher_transform` |
| Guppy Multiple Moving Average | new-card | `tv_builtin_guppy_multiple_moving_average` |
| Historical Volatility | existing | `voltarget`, `backtester/core/indicators.py:realised_vol` |
| Hull Moving Average | new-card | `tv_builtin_hull_moving_average` |
| Ichimoku Cloud | existing | `ichimoku_cloud`, `backtester/core/indicators.py:ichimoku` |
| Keltner Channels | existing | `keltner`, `backtester/core/strategies/signals.py:KeltnerBreakout` |
| Klinger Oscillator | new-card | `tv_builtin_klinger_oscillator` |
| Know Sure Thing | new-card | `tv_builtin_know_sure_thing` |
| Least Squares Moving Average | new-card | `tv_builtin_least_squares_moving_average` |
| Linear Regression Curve | alias | `tv_builtin_least_squares_moving_average` |
| Linear Regression Slope | new-card | `tv_builtin_linear_regression_slope` |
| MA Cross | existing | `ma_crossover`, `backtester/core/strategies/ma_crossover.py:MaCrossover` |
| MA with EMA Cross | new-card | `tv_builtin_ma_with_ema_cross` |
| Mass Index | new-card | `tv_builtin_mass_index` |
| McGinley Dynamic | new-card | `tv_builtin_mcginley_dynamic` |
| Median Price | new-card | `tv_builtin_median_price` |
| Momentum | new-card | `tv_builtin_momentum` |
| Money Flow Index | new-card | `tv_builtin_money_flow_index` |
| Moving Average | existing | `sma_regime`, `backtester/core/indicators.py:sma` |
| Moving Average Channel | new-card | `tv_builtin_moving_average_channel` |
| MACD | existing | `macd`, `backtester/core/indicators.py:macd` |
| Moving Average Exponential | existing | `ema_crossover`, `backtester/core/indicators.py:ema` |
| Moving Average Weighted | new-card | `tv_builtin_moving_average_weighted` |
| Moving Average Double | new-card | `tv_builtin_moving_average_double` |
| Moving Average Triple | new-card | `tv_builtin_moving_average_triple` |
| Moving Average Adaptive | new-card | `tv_builtin_moving_average_adaptive` |
| Moving Average Hamming | new-card | `tv_builtin_moving_average_hamming` |
| Moving Average Multiple | new-card | `tv_builtin_moving_average_multiple` |
| Majority Rule | new-card | `tv_builtin_majority_rule` |
| Net Volume | new-card | `tv_builtin_net_volume` |
| On Balance Volume | existing | `obv_trend`, `backtester/core/indicators.py:obv` |
| Parabolic SAR | new-card | `tv_builtin_parabolic_sar` |
| Pivot Points Standard | new-card | `tv_builtin_pivot_points_standard` |
| Price Channel | existing | `breakout`, `backtester/core/strategies/breakout.py:DonchianBreakout` |
| Price Oscillator | existing | `ppo`, `backtester/core/indicators.py:ppo` |
| Price Volume Trend | new-card | `tv_builtin_price_volume_trend` |
| Rank Correlation Index | new-card | `tv_builtin_rank_correlation_index` |
| Rate Of Change | existing | `ts_momentum`, `backtester/core/indicators.py:roc` |
| Ratio | new-card | `tv_builtin_ratio` |
| Relative Strength Index | existing | `rsi`, `backtester/core/indicators.py:rsi` |
| Relative Vigor Index | new-card | `tv_builtin_relative_vigor_index` |
| Relative Volatility Index | new-card | `tv_builtin_relative_volatility_index` |
| Standard Error | new-card | `tv_builtin_standard_error` |
| Standard Error Bands | new-card | `tv_builtin_standard_error_bands` |
| SMI Ergodic Indicator/Oscillator | new-card | `tv_builtin_smi_ergodic_indicator_oscillator` |
| Smoothed Moving Average | existing-code | `backtester/core/indicators.py:wilder_smooth` |
| Standard Deviation | existing-code | `backtester/core/scorecard.py:rstd` |
| Stochastic | existing | `stochastic`, `backtester/core/indicators.py:stochastic` |
| Stochastic RSI | new-card | `tv_builtin_stochastic_rsi` |
| Session Volume Profile | new-card | `tv_builtin_session_volume_profile` |
| SuperTrend | new-card | `tv_builtin_supertrend` |
| Spread | new-card | `tv_builtin_spread` |
| TRIX | new-card | `tv_builtin_trix` |
| Triple EMA | new-card | `tv_builtin_triple_ema` |
| True Strength Indicator | new-card | `tv_builtin_true_strength_indicator` |
| Trend Strength Index | new-card | `tv_builtin_trend_strength_index` |
| Typical Price | new-card | `tv_builtin_typical_price` |
| Ultimate Oscillator | new-card | `tv_builtin_ultimate_oscillator` |
| Volatility Close-to-Close | existing | `voltarget`, `backtester/core/indicators.py:realised_vol` |
| Volatility Zero Trend Close-to-Close | new-card | `tv_builtin_volatility_zero_trend_close_to_close` |
| Volatility O-H-L-C | new-card | `tv_builtin_volatility_o_h_l_c` |
| Volatility Index | new-card | `tv_builtin_volatility_index` |
| VWAP | existing-code | `backtester/core/scorecard.py:vwap` |
| VWMA | new-card | `tv_builtin_vwma` |
| Volume Oscillator | new-card | `tv_builtin_volume_oscillator` |
| Volume Profile Fixed Range | new-card | `tv_builtin_volume_profile_fixed_range` |
| Volume Profile Visible Range | new-card | `tv_builtin_volume_profile_visible_range` |
| Vortex Indicator | new-card | `tv_builtin_vortex_indicator` |
| Volume | existing-code | `backtester/core/scorecard.py:_c_volume` |
| Williams %R | new-card | `tv_builtin_williams_r` |
| Williams Alligator | new-card | `tv_builtin_williams_alligator` |
| Williams Fractal | new-card | `tv_builtin_williams_fractal` |
| Zig Zag | existing-code | `backtester/core/scorecard.py:zigzag_state` |
| Anchored VWAP | new-card | `tv_builtin_anchored_vwap` |
| Compare | new-card | `tv_builtin_compare` |
| Overlay | new-card | `tv_builtin_overlay` |
| Fixed Range | alias | `tv_builtin_volume_profile_fixed_range` |
| Regression Trend | new-card | `tv_builtin_regression_trend` |
| Sessions | new-card | `tv_builtin_sessions` |

## Reconciliation totals

| Disposition | Source/concept rows |
| --- | --- |
| alias | 20 |
| covered-concepts | 596 |
| duplicate | 1 |
| existing | 203 |
| existing-code | 10 |
| library | 27 |
| market-commentary | 826 |
| new-card | 1083 |
| non-signal | 2315 |
| source-insufficient | 2 |

Counts are source/concept rows, not independent strategies or measured results. A publication can reference several shared methods.

## New cards

| Card | Name |
| --- | --- |
| `tv_06gcx5ql_innovation_adaptive_kalman_filter_oscillator` | Innovation Adaptive Kalman Filter Oscillator |
| `tv_0enoetmo_smartphase_analyzer` | SmartPhase Analyzer |
| `tv_0ghsw1kr_moving_regression` | Moving Regression |
| `tv_0j7owdat_flowscope_hapharmonic` | FlowScope [Hapharmonic] |
| `tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc` | BITCOIN and CORRELATION, alternative trading strategies (CC) |
| `tv_0nz4m9e7_holographic_market_microstructure_alphanatt` | Holographic Market Microstructure / AlphaNatt |
| `tv_0s4usqeb_nasan_risk_score_postion_size_estimator` | Nasan Risk Score & Postion Size Estimator |
| `tv_0sbntaqj_trading_abc` | Trading ABC |
| `tv_0x1dgqjw_xabcd_harmonic_pattern_custom_range_interactive` | XABCD Harmonic Pattern Custom Range Interactive |
| `tv_10xmhfge_volume_per_point` | Volume per Point |
| `tv_119rqjou_potential_breakout_on_btcusd_to_the_upside` | Potential breakout on BTCUSD to the upside |
| `tv_12m8jqu6_function_polynomial_regression` | Function Polynomial Regression |
| `tv_15kb0kgb_rsi_buy_sell_force_ver_1` | RSI buy sell force ver 1  |
| `tv_17xrxgad_auto_pitchfan_fib_extension_retracement_and_zigzag_by_dgt` | Auto PitchFan, Fib Extension/Retracement and ZigZag by DGT |
| `tv_195p3ylk_commitment_of_traders_legacy_metrics` | Commitment of Traders: Legacy Metrics |
| `tv_1avreiwr_bitcoin_approaches_25_000_how_can_we_identify_a_potential_top` | Bitcoin approaches $25,000, how can we identify a potential top? |
| `tv_1cv4puad_redk_indicator_amplifier_redk_i_amp` | RedK Indicator Amplifier (RedK i-Amp) |
| `tv_1i4bnwmu_js_squeeze_pro_overlays` | (JS) Squeeze Pro Overlays |
| `tv_1imcwzbc_the_simplest_scalping_strategy_with_3_ema_s_for_20_pips_per_day` | The Simplest Scalping Strategy With 3 EMA's For 20 Pips Per Day |
| `tv_1nhvl40i_fibonacci_time_price_zones` | Fibonacci Time-Price Zones |
| `tv_1uw4irtx_all_time_high_low_widget` | All-Time High/Low Widget |
| `tv_1z60bvmr_previous_period_levels_x_alerts` | Previous Period Levels - X Alerts |
| `tv_23wjedff_ehlers_loops_bigbeluga` | Ehlers Loops [BigBeluga] |
| `tv_25py1uvb_position_cost_distribution` | Position Cost Distribution |
| `tv_2gaiphlg_periodic_activity_tracker_luxalgo` | Periodic Activity Tracker [LuxAlgo] |
| `tv_2s4bqqzq_tasc_2026_10_a_low_risk_etf_trading_strategy` | TASC 2026.10 A Low-Risk ETF-Trading Strategy |
| `tv_2sf3nchw_s_p_500_risk_off_watch_the_put_call_ratio_and_us_dollar` | S&P 500 Risk Off? Watch the Put-Call Ratio and US Dollar |
| `tv_2tennpoc_rsi_past_can_turn_rsi_into_a_directional_tool` | RSI Past Can Turn RSI Into a Directional Tool |
| `tv_2vec0xzu_annual_returns_comparison_by_muqwishi` | Annual Returns % Comparison [By MUQWISHI] |
| `tv_2vlzhblv_modified_obv_w_divergence_detection_by_cryptorhythms` | Modified OBV w/ Divergence Detection by Cryptorhythms |
| `tv_2vmbqbln_market_ekg` | Market EKG |
| `tv_34r4mh5w_market_microstructure_analytics` | Market Microstructure Analytics |
| `tv_3aqxmxoc_s_p_500_vs_stocks` | S&P 500 VS STOCKS |
| `tv_3jkrk2at_vqzl_z_score` | VQZL Z-Score |
| `tv_3lzg4gmr_machine_learning_knn_new_approach` | Machine Learning: kNN (New Approach) |
| `tv_3mkewfnn_10x_bull_vs_bear_vp_intraday_sessions_kioseff_trading` | 10x Bull Vs. Bear VP Intraday Sessions [Kioseff Trading] |
| `tv_3w5o68jp_rs_zigzag_multiple_methods_forecast_patterns_labels` | [RS]ZigZag Multiple Methods - Forecast - patterns - labels |
| `tv_3xe8qqfr_directional_volume_shapes_zeiierman` | Directional Volume Shapes (Zeiierman) |
| `tv_43000474007_understanding_range_charts` | Understanding range charts |
| `tv_43000501972_bollinger_bandwidth_bbw` | Bollinger BandWidth (BBW) |
| `tv_43000502040_volume_profile_indicators_basic_concepts` | Volume profile indicators: basic concepts |
| `tv_43000502272_learn_to_use_kagi_charts` | Learn to use Kagi charts |
| `tv_43000502273_introduction_to_line_break_charts` | Introduction to line break charts |
| `tv_43000502276_learn_using_point_and_figure_charts` | Learn using point and figure charts |
| `tv_43000502591_multi_time_period_charts_indicator` | Multi-Time Period Charts indicator |
| `tv_43000583765_bearish_abandoned_baby_how_to_spot_a_reversal_at_the_top_of_an_up` | Bearish Abandoned baby: how to spot a reversal at the top of an uptrend |
| `tv_43000583766_bullish_abandoned_baby_how_to_catch_a_reversal_at_the_bottom_of_a` | Bullish Abandoned baby: how to catch a reversal at the bottom of a downtrend |
| `tv_43000583767_doji_interpreting_market_indecision_on_a_price_chart` | Doji: interpreting market indecision on a price chart |
| `tv_43000583768_bullish_dragonfly_doji_recognizing_lower_price_rejection_in_a_dow` | Bullish Dragonfly Doji: recognizing lower price rejection in a downtrend |
| `tv_43000583769_bearish_engulfing_recognizing_sellers_taking_over_at_an_uptrend_s` | Bearish Engulfing: recognizing sellers taking over at an uptrend's peak |
| `tv_43000583771_bullish_engulfing_recognizing_buyers_taking_over_at_a_downtrend_s` | Bullish Engulfing: recognizing buyers taking over at a downtrend's base |
| `tv_43000583772_bearish_evening_star_identifying_the_end_of_an_uptrend_in_three_c` | Bearish Evening star: identifying the end of an uptrend in three candles |
| `tv_43000583773_bearish_gravestone_doji_how_to_spot_rejected_buying_at_the_top_of` | Bearish Gravestone Doji: how to spot rejected buying at the top of a move |
| `tv_43000583775_bullish_hammer_detecting_a_possible_bottom_in_a_downtrend` | Bullish Hammer: detecting a possible bottom in a downtrend |
| `tv_43000583776_bearish_hanging_man_detecting_warning_signs_at_market_highs` | Bearish Hanging man: detecting warning signs at market highs |
| `tv_43000583777_bearish_harami_how_to_confirm_a_slowdown_at_the_top_of_an_uptrend` | Bearish Harami: how to confirm a slowdown at the top of an uptrend |
| `tv_43000583778_harami_bullish` | Harami - Bullish |
| `tv_43000583780_inverted_hammer_bullish` | Inverted Hammer - Bullish |
| `tv_43000583781_kicking_bearish` | Kicking - Bearish |
| `tv_43000583782_kicking_bullish` | Kicking - Bullish |
| `tv_43000583783_long_lower_shadow_bullish` | Long Lower Shadow - Bullish |
| `tv_43000583784_long_upper_shadow_bearish` | Long Upper Shadow - Bearish |
| `tv_43000583785_marubozu_black_bearish` | Marubozu Black - Bearish |
| `tv_43000583786_marubozu_white_bullish` | Marubozu White - Bullish |
| `tv_43000583787_morning_star_bullish` | Morning Star - Bullish |
| `tv_43000583789_shooting_star_bearish` | Shooting Star - Bearish |
| `tv_43000583790_spinning_top_white` | Spinning Top White |
| `tv_43000583791_spinning_top_black` | Spinning Top Black |
| `tv_43000583792_three_black_crows_bearish` | Three Black Crows - Bearish |
| `tv_43000583793_three_white_soldiers_bullish` | Three White Soldiers - Bullish |
| `tv_43000583794_tri_star_bearish` | Tri Star - Bearish |
| `tv_43000583796_tri_star_bullish` | Tri Star - Bullish |
| `tv_43000589092_advance_decline_line` | Advance/Decline Line |
| `tv_43000589093_advance_decline_ratio` | Advance/Decline Ratio |
| `tv_43000589104_bollinger_bands_strategy` | Bollinger Bands Strategy |
| `tv_43000589126_cumulative_volume_index_cvi` | Cumulative Volume Index (CVI) |
| `tv_43000589129_dividend_yield` | Dividend Yield |
| `tv_43000589195_pivot_points_high_low` | Pivot Points High Low |
| `tv_43000591333_rob_booker_adx_breakout` | Rob Booker - ADX Breakout |
| `tv_43000591336_rob_booker_knoxville_divergence` | Rob Booker - Knoxville Divergence |
| `tv_43000591664_zigzag_indicator` | Zigzag indicator |
| `tv_43000591665_inside_bar_strategy` | InSide Bar Strategy |
| `tv_43000592285_stochastic_slow_strategy` | Stochastic Slow Strategy |
| `tv_43000592558_piercing_bullish` | Piercing - Bullish |
| `tv_43000592563_bearish_dark_cloud_cover_how_to_read_a_failed_push_higher_in_an_u` | Bearish Dark cloud cover: how to read a failed push higher in an uptrend |
| `tv_43000592704_morning_doji_star_bullish` | Morning Doji Star - Bullish |
| `tv_43000592705_bearish_evening_doji_star_recognizing_a_confirmed_reversal_at_an_` | Bearish Evening Doji star: recognizing a confirmed reversal at an uptrend's peak |
| `tv_43000592707_harami_cross_bearish` | Harami Cross - Bearish |
| `tv_43000592708_harami_cross_bullish` | Harami Cross - Bullish |
| `tv_43000592709_tweezer_bottom_bullish` | Tweezer Bottom - Bullish |
| `tv_43000592710_tweezer_top_bearish` | Tweezer Top - Bearish |
| `tv_43000592711_rising_three_methods_bullish` | Rising Three Methods - Bullish |
| `tv_43000592712_bearish_falling_three_methods_catching_a_temporary_pullback_in_a_` | Bearish Falling three methods: catching a temporary pullback in a downtrend |
| `tv_43000592713_bearish_falling_window_interpreting_a_price_gap_within_a_downtren` | Bearish Falling window: interpreting a price gap within a downtrend |
| `tv_43000592721_rising_window_bullish` | Rising Window - Bullish |
| `tv_43000592722_on_neck_bearish` | On Neck - Bearish |
| `tv_43000592723_bearish_downside_tasuki_gap_how_to_confirm_a_downtrend_will_conti` | Bearish Downside Tasuki gap: how to confirm a downtrend will continue |
| `tv_43000592725_upside_tasuki_gap_bullish` | Upside Tasuki Gap - Bullish |
| `tv_43000592726_bullish_doji_star_detecting_seller_exhaustion_at_a_downtrend_s_ba` | Bullish Doji star: detecting seller exhaustion at a downtrend's base |
| `tv_43000592727_bearish_doji_star_identifying_early_hesitation_at_the_top_of_an_u` | Bearish Doji star: identifying early hesitation at the top of an uptrend |
| `tv_43000594526_pivot_reversal_strategy` | Pivot Reversal Strategy |
| `tv_43000594546_rob_booker_intraday_pivot_points` | Rob Booker Intraday Pivot Points |
| `tv_43000594673_woodies_cci` | Woodies CCI |
| `tv_43000594676_volatility_stop` | Volatility Stop |
| `tv_43000594678_rob_booker_missed_pivot_points` | Rob Booker Missed Pivot Points |
| `tv_43000594679_rob_booker_ziv_ghost_pivots` | Rob Booker Ziv Ghost Pivots |
| `tv_43000594680_weighted_moving_average` | Weighted Moving Average |
| `tv_43000599823_barupdn_strategy` | BarUpDn Strategy |
| `tv_43000599826_bollinger_bands_strategy_directed` | Bollinger Bands Strategy Directed |
| `tv_43000599828_channel_breakout_strategy` | Channel BreakOut Strategy |
| `tv_43000599836_consecutive_up_down_strategy` | Consecutive Up/Down Strategy |
| `tv_43000599840_rob_booker_reversal` | Rob Booker Reversal |
| `tv_43000599876_greedy_strategy` | Greedy Strategy |
| `tv_43000599883_momentum_strategy` | Momentum Strategy |
| `tv_43000599884_moon_phases` | Moon Phases |
| `tv_43000599887_outside_bar_strategy` | OutSide Bar Strategy |
| `tv_43000599888_pivot_extension_strategy` | Pivot Extension Strategy |
| `tv_43000599890_volty_expan_close_strategy` | Volty Expan Close Strategy |
| `tv_43000601862_price_channel_strategy` | Price Channel Strategy |
| `tv_43000614331_technical_ratings` | Technical Ratings |
| `tv_43000628415_technical_ratings_strategy` | Technical Ratings Strategy |
| `tv_43000644914_advance_decline_ratio_bars` | Advance/Decline Ratio (Bars) |
| `tv_43000644929_keltner_channels_strategy` | Keltner Channels Strategy |
| `tv_43000644936_linear_regression` | Linear Regression |
| `tv_43000644943_macd_strategy` | MACD Strategy |
| `tv_43000645065_parabolic_sar_strategy` | Parabolic SAR Strategy |
| `tv_43000645066_rsi_strategy` | RSI Strategy |
| `tv_43000645068_supertrend_strategy` | Supertrend Strategy |
| `tv_43000652199_vwap_auto_anchored` | VWAP Auto Anchored |
| `tv_43000653216_chart_pattern_rectangle` | Chart Pattern Rectangle |
| `tv_43000668584_24_hour_volume` | 24-hour Volume |
| `tv_43000672561_up_down_volume` | Up/Down Volume |
| `tv_43000675999_gaps` | Gaps |
| `tv_43000678409_analyst_price_forecast` | Analyst price forecast |
| `tv_43000678766_visible_average_price` | Visible Average Price |
| `tv_43000692939_time_weighted_average_price` | Time Weighted Average Price |
| `tv_43000695003_average_daily_range_adr_indicator` | Average Daily Range (ADR) indicator |
| `tv_43000703071_periodic_volume_profile` | Periodic Volume Profile |
| `tv_43000703077_auto_anchored_volume_profile` | Auto Anchored Volume Profile |
| `tv_43000705489_relative_volume_at_time` | Relative Volume at Time |
| `tv_43000707882_stochastic_momentum_index_smi` | Stochastic Momentum Index (SMI) |
| `tv_43000717955_bull_bear_power` | Bull Bear Power |
| `tv_43000724995_understanding_volume_candle_charts` | Understanding volume candle charts |
| `tv_43000725590_time_price_opportunity_charts_explained` | Time price opportunity charts explained |
| `tv_43000726749_bbtrend` | BBTrend |
| `tv_43000730980_price_target_indicator` | Price target - indicator |
| `tv_43000732559_chart_pattern_inverted_cup_and_handle` | Chart Pattern Inverted Cup and Handle |
| `tv_43000736064_performance` | Performance |
| `tv_43000741165_auto_trendlines` | Auto trendlines |
| `tv_43000742575_bollinger_bars` | Bollinger Bars |
| `tv_43000745275_session_volume_profile_charts_explained` | Session volume profile charts explained |
| `tv_43000762388_understanding_crypto_open_interest` | Understanding crypto open interest |
| `tv_43000762390_funding_rate_a_guide_to_market_sentiment` | Funding rate: a guide to market sentiment |
| `tv_43000762397_long_short_accounts` | Long Short Accounts % |
| `tv_43000762399_long_short_ratio_accounts` | Long / Short Ratio Accounts |
| `tv_43000762400_liquidation_data_what_to_watch_and_why_it_matters` | Liquidation data: what to watch and why it matters |
| `tv_43000765571_rci_ribbon` | RCI Ribbon |
| `tv_43000773004_aroon_oscillator` | Aroon Oscillator |
| `tv_43000773005_negative_volume_index_nvi` | Negative Volume Index (NVI) |
| `tv_43000773006_positive_volume_index_pvi` | Positive Volume Index (PVI) |
| `tv_43000773010_price_momentum_oscillator_pmo` | Price Momentum Oscillator (PMO) |
| `tv_43000773011_pring_s_special_k` | Pring's Special K |
| `tv_43000773012_kaufman_s_adaptive_moving_average_kama` | Kaufman's Adaptive Moving Average (KAMA) |
| `tv_43000773013_chandelier_exit` | Chandelier Exit |
| `tv_43000773115_ulcer_index` | Ulcer Index |
| `tv_43000773986_1_year_active_supply` | 1 year active supply % |
| `tv_43000773987_addresses_with_balance_x_of_supply` | Addresses with balance ≥ X (% of supply) |
| `tv_43000773988_addresses_with_balance_x_usd` | Addresses with balance ≥ X (USD) |
| `tv_43000773989_average_transaction_volume` | Average transaction volume |
| `tv_43000773990_held_tokens_in_addresses_x_usd` | Held tokens in addresses ≥ X (USD) |
| `tv_43000773991_held_tokens_in_addresses_x_tokens` | Held tokens in addresses ≥ X (tokens) |
| `tv_43000773992_held_tokens_in_addresses_x_of_supply` | Held tokens in addresses ≥ X (% of supply) |
| `tv_43000773993_large_transaction_volume` | Large transaction volume |
| `tv_43000773994_realized_market_cap` | Realized market cap |
| `tv_43000773995_rvt_ratio_90_days` | RVT ratio, 90 days |
| `tv_43000773996_supply_equality_ratio` | Supply Equality Ratio |
| `tv_43000773997_transaction_fees` | Transaction fees |
| `tv_43000778534_sending_addresses` | Sending addresses |
| `tv_43000778535_receiving_addresses` | Receiving addresses |
| `tv_43000778537_spent_output_profit_ratio_sopr` | Spent Output Profit Ratio (SOPR) |
| `tv_43000778538_mean_transfer_volume` | Mean transfer volume |
| `tv_43000778539_median_transfer_volume` | Median transfer volume |
| `tv_43000778541_transfer_count` | Transfer count |
| `tv_43000778542_transfer_rate` | Transfer rate |
| `tv_43000778543_transaction_rate` | Transaction rate |
| `tv_43000778547_transaction_fees` | Transaction fees |
| `tv_43000778548_mean_transaction_fees` | Mean transaction fees |
| `tv_43000778549_median_transaction_fees` | Median transaction fees |
| `tv_43000778550_total_gas_used` | Total gas used |
| `tv_43000778551_mean_gas_used` | Mean gas used |
| `tv_43000778552_median_gas_used` | Median gas used |
| `tv_43000778553_mean_transaction_gas_price` | Mean transaction gas price |
| `tv_43000778554_median_transaction_gas_price` | Median transaction gas price |
| `tv_43000778555_block_height` | Block height |
| `tv_43000778556_blocks_mined` | Blocks mined |
| `tv_43000778557_mean_block_interval` | Mean block interval |
| `tv_43000778558_median_block_interval` | Median block interval |
| `tv_43000778559_total_block_size_in_bytes` | Total block size in bytes |
| `tv_43000778560_mean_block_size_in_bytes` | Mean block size in bytes |
| `tv_43000778561_hash_rate` | Hash Rate |
| `tv_43000778562_difficulty` | Difficulty |
| `tv_43000778563_total_utxos` | Total UTXOs |
| `tv_43000778564_created_utxos` | Created UTXOs |
| `tv_43000778565_spent_utxos` | Spent UTXOs |
| `tv_43000778566_mean_utxo_value_created` | Mean UTXO value created |
| `tv_43000778567_median_utxo_value_created` | Median UTXO value created |
| `tv_43000778568_total_utxo_value_created` | Total UTXO value created |
| `tv_43000778569_mean_utxo_value_spent` | Mean UTXO value spent |
| `tv_43000778570_median_utxo_value_spent` | Median UTXO value spent |
| `tv_43000778572_total_utxo_value_spent` | Total UTXO value spent |
| `tv_43000778573_total_transactions_size_in_bytes` | Total transactions size in bytes |
| `tv_43000778574_mean_transaction_size_in_bytes` | Mean transaction size in bytes |
| `tv_43000778575_el_salvador_government_balance` | El Salvador Government balance |
| `tv_43000778576_power_law_model` | Power-Law Model |
| `tv_43000778577_stock_to_flow_ratio_in_usd` | Stock-to-Flow Ratio in USD |
| `tv_43000778578_ethereum_new_deposits` | Ethereum new deposits |
| `tv_43000778579_ethereum_new_value_staked` | Ethereum new value staked |
| `tv_43000778580_ethereum_new_unique_depositors` | Ethereum new unique depositors |
| `tv_43000778581_ethereum_total_number_of_deposits` | Ethereum total number of deposits |
| `tv_43000778582_ethereum_total_unique_depositors` | Ethereum total unique depositors |
| `tv_43000778583_ethereum_total_value_staked` | Ethereum total value staked |
| `tv_43000778584_mean_transaction_gas_limit` | Mean transaction gas limit |
| `tv_43000778585_median_transaction_gas_limit` | Median transaction gas limit |
| `tv_43000778587_active_addresses_with_contracts` | Active addresses with contracts |
| `tv_43000778588_us_spot_crypto_etf_balances` | US spot crypto ETF balances |
| `tv_43000778589_us_spot_crypto_etf_flows` | US spot crypto ETF flows |
| `tv_43000778590_etf_balances` | ETF balances |
| `tv_43000778591_etf_flows` | ETF flows |
| `tv_43000783958_auto_key_levels` | Auto key levels |
| `tv_43000784529_top_trader_long_short_accounts` | Top trader long/short accounts |
| `tv_43000784530_top_trader_long_short_accounts_ratio` | Top trader long/short accounts ratio |
| `tv_43000784531_top_trader_long_short_positions` | Top trader long/short positions |
| `tv_43000784532_top_trader_long_short_positions_ratio` | Top trader long/short positions ratio |
| `tv_43000784533_index_price` | Index price |
| `tv_43000784534_mark_price` | Mark price |
| `tv_43000784535_premium` | Premium |
| `tv_43000784536_basis` | Basis |
| `tv_43000793423_options_volume_profile_see_call_and_put_volume_right_on_the_chart` | Options Volume Profile: see call and put volume right on the chart |
| `tv_43000796657_supply_in_profit` | Supply in Profit |
| `tv_43000796930_expected_move_see_the_market_s_projected_price_range_on_the_chart` | Expected Move: see the market's projected price range on the chart |
| `tv_4774rrry_your_strength_meter_for_candlestick_best_momentum_indicator` | Your Strength Meter For Candlestick / Best Momentum Indicator 🕯 |
| `tv_49yiv1jw_machine_learning_logistic_regression` | Machine Learning: Logistic Regression |
| `tv_4kigelgo_finra_daily_short_sale_volume` | FINRA Daily Short Sale Volume |
| `tv_4lbygqj0_weighted_percentile_nearest_rank` | Weighted percentile nearest rank |
| `tv_4n9sh3lz_funamental_and_financials` | Funamental and financials |
| `tv_4nmghanl_redk_slow_smooth_average_rss_wma` | RedK Slow_Smooth Average (RSS_WMA) |
| `tv_4odvb8q4_relative_currency_strength` | Relative Currency Strength |
| `tv_4psxdoyc_a_technique_from_1202_really` | A technique from 1202 - Really?  |
| `tv_4rlnnl5e_polynomial_linear_regression_volume_profile_bigbeluga` | Polynomial/Linear Regression Volume Profile [BigBeluga] |
| `tv_5a8qkpsh_point_of_control_v2` | Point of Control V2  |
| `tv_5eglveln_relative_bandwidth_filter` | Relative Bandwidth Filter |
| `tv_5fqgmcio_adaptive_candlestick_pattern_recognition_system` | Adaptive Candlestick Pattern Recognition System |
| `tv_5ghqjxjj_vol_control_fund_positioning` | Vol-Control Fund Positioning |
| `tv_5js51rsp_multitimeframe_fair_value_gap_fvg_zeiierman` | Multitimeframe Fair Value Gap – FVG (Zeiierman) |
| `tv_5kgra3dl_dynamic_volume_clusters_with_retest_signals_zeiierman` | Dynamic Volume Clusters with Retest Signals (Zeiierman) |
| `tv_5nsvcovp_industry_group_strength` | Industry Group Strength |
| `tv_5qth3kyd_multi_layer_volume_profile_bigbeluga` | Multi-Layer Volume Profile [BigBeluga] |
| `tv_5uubjdyo_range_sentiment_profile_luxalgo` | Range Sentiment Profile [LuxAlgo] |
| `tv_5v1unbrn_average_force` | Average Force |
| `tv_5wxlrdaq_tasc_2022_06_ehlers_loops` | TASC 2022.06 Ehlers Loops |
| `tv_66gsofej_separated_moving_average_evo` | Separated Moving Average - evo |
| `tv_672uph9q_enhanced_time_segmented_volume` | Enhanced Time Segmented Volume |
| `tv_680r1i3z_strength_of_divergence_across_multiple_indicators` | Strength of Divergence Across Multiple Indicators |
| `tv_68z68uzz_vix_cheat_sheet` | VIX Cheat Sheet |
| `tv_69wrttlx_correlation_array_s` | Correlation [array's] |
| `tv_6aln4qkl_zahorchak_measure` | Zahorchak Measure |
| `tv_6f7ztdvh_equity_bond_currency_dashboard` | Equity Bond Currency Dashboard |
| `tv_6qwqyut8_tasc_2025_07_laguerre_filters` | TASC 2025.07 Laguerre Filters |
| `tv_6qx7rznd_outlier_detector_with_n_sigma_confidence_intervals` | Outlier Detector with N-Sigma Confidence Intervals |
| `tv_6tsfpe3w_reflex_trendflex` | Reflex & Trendflex |
| `tv_6wr1ceuo_deviation_trend_profile_bigbeluga` | Deviation Trend Profile [BigBeluga] |
| `tv_6yqqyzp9_vicious_mortgage_rates_v1_0` | Vicious Mortgage Rates V1.0 |
| `tv_7biqbrfz_how_to_utilize_multi_time_frame_analysis_in_your_trading` | How to utilize Multi-time frame analysis in your trading |
| `tv_7emr6ckb_fancy_triple_moving_averages_bigbitsio` | Fancy Triple Moving Averages [BigBitsIO] |
| `tv_7gx1fmgo_everything_bitcoin_kioseff_trading` | Everything Bitcoin [Kioseff Trading] |
| `tv_7jm5ebze_yelober_sector_rotation_detector` | Yelober - Sector Rotation Detector |
| `tv_7kmrab2f_gann_square_of_144` | Gann Square of 144 |
| `tv_7prbcbjk_stochastic_heat_map` | Stochastic Heat Map |
| `tv_7qjxp2op_fundamentals_graphing_kioseff_trading` | Fundamentals Graphing [Kioseff Trading] |
| `tv_7s0lx2bw_redk_volume_accelerated_directional_energy_ratio_redk_vader` | RedK Volume-Accelerated Directional Energy Ratio (RedK VADER) |
| `tv_7skzirbb_machine_learning_neural_network_engine` | Machine Learning Neural Network Engine |
| `tv_7tsb40pn_magic_change_of_bill_williams_s_awesome_oscillator` | \"Magic Change\" of Bill Williams's Awesome Oscillator |
| `tv_7vcb6m4j_volume_delta_footprint_map_zeiierman` | Volume Delta Footprint Map (Zeiierman) |
| `tv_84vjsklo_nunchucks` | Nunchucks |
| `tv_8ea9mvz5_technical_ratings_on_multi_frames_assets` | Technical Ratings on Multi-frames / Assets |
| `tv_8ezad3cw_supertrend_ladder_atr` | Supertrend - Ladder ATR |
| `tv_8hiw5vzw_tutorial_how_to_identify_potentially_strong_trend_days` | Tutorial / How To Identify Potentially Strong Trend Days |
| `tv_8jahmkxs_bear_market_probability_model` | Bear Market Probability Model |
| `tv_8lxcviym_bayesian_bbsma_oscillator` | Bayesian BBSMA Oscillator |
| `tv_8mvftxpg_tape_lucf` | Tape [LucF] |
| `tv_8njgasbv_volume_rotor_clock_hapharmonic` | Volume Rotor Clock [hapharmonic] |
| `tv_8os1nbr8_inwcoin_martingale_strategy_for_bitcoin` | inwCoin Martingale Strategy ( for Bitcoin ) |
| `tv_8owcuqfq_multi_distribution_volume_profile_zeiierman` | Multi-Distribution Volume Profile (Zeiierman) |
| `tv_8utwhfo3_rsi_radar_multi_time_frame` | RSI Radar Multi Time Frame |
| `tv_8zsalctc_trendflex_oscillator_dr_john_ehlers` | TrendFlex Oscillator - Dr. John Ehlers |
| `tv_93tde1fd_liquidity_price_depth_chart_luxalgo` | Liquidity Price Depth Chart [LuxAlgo] |
| `tv_94gz1qy4_pandora_vast_volatility_treasure_trove` | [Pandora] Vast Volatility Treasure Trove |
| `tv_94xv1hsx_linear_correlation_oscillator` | Linear Correlation Oscillator |
| `tv_96cld5is_trend_correlation_heatmap` | Trend Correlation Heatmap |
| `tv_9bkoihdl_numbers_renko` | Numbers Renko |
| `tv_9gviczng_sk_fibonacci_auto_trend_scouter` | [SK] Fibonacci Auto Trend Scouter |
| `tv_9k34g20s_normalized_oscillators_spider_chart_luxalgo` | Normalized Oscillators Spider Chart [LuxAlgo] |
| `tv_9mpc4ifp_volume_spread_analysis_iq_tradingiq` | Volume Spread Analysis IQ [TradingIQ] |
| `tv_9pd60gmz_blackcat_l2_ehlers_swamicharts_rsi` | [blackcat] L2 Ehlers SwamiCharts RSI |
| `tv_9q1vcipg_monte_carlo_ct_ss` | Monte Carlo CT [SS] |
| `tv_9roydod6_probability_grid_luxalgo` | Probability Grid [LuxAlgo] |
| `tv_9uiewdmd_trend_following_moving_averages` | Trend Following Moving Averages |
| `tv_a35ki2pb_px_external_level` | [PX] External Level |
| `tv_a3eudme3_raff_regression_channel_rrc` | Raff Regression Channel (RRC) |
| `tv_a4lgcdz1_dominance_pie_chart` | Dominance Pie Chart |
| `tv_a4qsrfcq_how_to_trade_a_scythe_pattern_spy_used_as_example` | How to Trade a Scythe Pattern (SPY used as example) |
| `tv_a7a6ys0y_chart_patterns_screener_trendoscope` | Chart Patterns Screener [Trendoscope] |
| `tv_a8peqinu_smart_nr2_nr20_and_inside_bar_zeiierman` | Smart NR2-NR20 and Inside Bar (Zeiierman) |
| `tv_aapsyqft_gann_box_zeiierman` | Gann Box (Zeiierman) |
| `tv_abwbbb9h_equivolume_bars` | Equivolume Bars |
| `tv_akskg1ih_mcginley_dynamic_improved_john_r_mcginley_jr` | McGinley Dynamic (Improved) - John R. McGinley, Jr. |
| `tv_apsqmw8f_combo_strategy_123_reversal_fractal_chaos_bands` | Combo Strategy 123 Reversal & Fractal Chaos Bands |
| `tv_arpbta5n_kernel_regression_toolkit` | Kernel Regression Toolkit |
| `tv_asev0vxd_tasc_2022_07_pairs_rotation_with_ehlers_loops` | TASC 2022.07 Pairs Rotation With Ehlers Loops |
| `tv_asr7nob2_liquidity_sentiment_profile_luxalgo` | Liquidity Sentiment Profile [LuxAlgo] |
| `tv_asvg5mjc_monte_carlo_simulation_random_walk` | Monte Carlo Simulation - Random Walk |
| `tv_atzwb4pu_bin_based_support_and_resistance_ss` | BIN Based Support and Resistance [SS] |
| `tv_audl9zek_tasc_2022_6_ehlers_loops_sectors` | TASC 2022.6 Ehlers' Loops - Sectors |
| `tv_ausph7vf_fair_value_ms` | Fair Value MS |
| `tv_axtmvrud_fair_value_gap_profile_rolling_poc_bigbeluga` | Fair Value Gap Profile + Rolling POC [BigBeluga] |
| `tv_b094banp_laguerre_rsi` | Laguerre RSI |
| `tv_b0kzf6ug_polynomial_regression_bands_channel_dw` | Polynomial Regression Bands + Channel [DW] |
| `tv_b3almahh_indices_sector_sigmaspikes` | Indices Sector SigmaSpikes |
| `tv_b3pcu8qn_ce_42macro_equity_factor_table` | CE - 42MACRO Equity Factor Table  |
| `tv_b4jcgfrd_linear_continuation` | Linear Continuation |
| `tv_bbeeqrdm_time_of_day_day_of_week_sigma_spike` | Time of day / day of week Sigma Spike |
| `tv_bbhc0nit_mcdonald_s_pattern_luxalgo` | McDonald's Pattern [LuxAlgo] |
| `tv_bbidyx3r_berlin_range_index_bar_color_version` | BERLIN Range Index / Bar color version |
| `tv_bcuqpa0q_multi_time_frame_candles_with_volume_info_3d` | Multi Time Frame Candles with Volume Info / 3D |
| `tv_bdk3oefq_tasc_2025_11_the_points_and_line_chart` | TASC 2025.11 The Points and Line Chart |
| `tv_beczr3nb_buyers_sellers_profile_dynamic_s_r_zeiierman` | Buyers & Sellers Profile + Dynamic S/R (Zeiierman) |
| `tv_bfu1hmks_neural_weight_oscillator_zeiierman` | Neural Weight Oscillator (Zeiierman) |
| `tv_bfxf4ixh_built_in_kelly_ratio_for_dynamic_position_sizing` | Built-in Kelly ratio for dynamic position sizing |
| `tv_blgcy3yu_this_is_my_plan_to_trade_btcusd_based_on_historical_price_data` | This is my plan to trade BTCUSD based on historical price data. |
| `tv_bluvjpa3_aggregate_btc_candles` | Aggregate BTC Candles |
| `tv_bmbdsegq_the_bitcoin_cheatsheet_the_price_and_time_of_the_next_top` | The BITCOIN Cheatsheet! The price and time of the next Top! |
| `tv_bmkcccil_day_trading_booster_by_dgt` | Day Trading Booster by DGT |
| `tv_bmxmwmne_momentum_acceleration_by_dgt` | Momentum Acceleration by DGT |
| `tv_bnhlqnsp_volume_bull_bear_activity_zc` | Volume Bull/Bear Activity [ZC] |
| `tv_bswaptez_breakout_volume_delta_flux_charts` | Breakout Volume Delta / Flux Charts |
| `tv_bugfwu53_atr_based_trendlines_jd` | ATR Based Trendlines - JD |
| `tv_builtin_52_week_high_low` | 52 Week High/Low |
| `tv_builtin_accelerator_oscillator` | Accelerator Oscillator |
| `tv_builtin_accumulation_distribution` | Accumulation/Distribution |
| `tv_builtin_accumulative_swing_index` | Accumulative Swing Index |
| `tv_builtin_advance_decline` | Advance/Decline |
| `tv_builtin_anchored_vwap` | Anchored VWAP |
| `tv_builtin_arnaud_legoux_moving_average` | Arnaud Legoux Moving Average |
| `tv_builtin_aroon` | Aroon |
| `tv_builtin_average_price` | Average Price |
| `tv_builtin_awesome_oscillator` | Awesome Oscillator |
| `tv_builtin_bollinger_bands_b` | Bollinger Bands %B |
| `tv_builtin_bollinger_bands_width` | Bollinger Bands Width |
| `tv_builtin_chaikin_oscillator` | Chaikin Oscillator |
| `tv_builtin_chaikin_volatility` | Chaikin Volatility |
| `tv_builtin_chande_kroll_stop` | Chande Kroll Stop |
| `tv_builtin_chande_momentum_oscillator` | Chande Momentum Oscillator |
| `tv_builtin_chop_zone` | Chop Zone |
| `tv_builtin_choppiness_index` | Choppiness Index |
| `tv_builtin_compare` | Compare |
| `tv_builtin_connors_rsi` | Connors RSI |
| `tv_builtin_coppock_curve` | Coppock Curve |
| `tv_builtin_correlation_coefficient` | Correlation Coefficient |
| `tv_builtin_correlation_log` | Correlation - Log |
| `tv_builtin_detrended_price_oscillator` | Detrended Price Oscillator |
| `tv_builtin_double_ema` | Double EMA |
| `tv_builtin_ease_of_movement` | Ease of Movement |
| `tv_builtin_elder_s_force_index` | Elder's Force Index |
| `tv_builtin_envelopes` | Envelopes |
| `tv_builtin_fisher_transform` | Fisher Transform |
| `tv_builtin_guppy_multiple_moving_average` | Guppy Multiple Moving Average |
| `tv_builtin_hull_moving_average` | Hull Moving Average |
| `tv_builtin_klinger_oscillator` | Klinger Oscillator |
| `tv_builtin_know_sure_thing` | Know Sure Thing |
| `tv_builtin_least_squares_moving_average` | Least Squares Moving Average |
| `tv_builtin_linear_regression_slope` | Linear Regression Slope |
| `tv_builtin_ma_with_ema_cross` | MA with EMA Cross |
| `tv_builtin_majority_rule` | Majority Rule |
| `tv_builtin_mass_index` | Mass Index |
| `tv_builtin_mcginley_dynamic` | McGinley Dynamic |
| `tv_builtin_median_price` | Median Price |
| `tv_builtin_momentum` | Momentum |
| `tv_builtin_money_flow_index` | Money Flow Index |
| `tv_builtin_moving_average_adaptive` | Moving Average Adaptive |
| `tv_builtin_moving_average_channel` | Moving Average Channel |
| `tv_builtin_moving_average_double` | Moving Average Double |
| `tv_builtin_moving_average_hamming` | Moving Average Hamming |
| `tv_builtin_moving_average_multiple` | Moving Average Multiple |
| `tv_builtin_moving_average_triple` | Moving Average Triple |
| `tv_builtin_moving_average_weighted` | Moving Average Weighted |
| `tv_builtin_net_volume` | Net Volume |
| `tv_builtin_overlay` | Overlay |
| `tv_builtin_parabolic_sar` | Parabolic SAR |
| `tv_builtin_pivot_points_standard` | Pivot Points Standard |
| `tv_builtin_price_volume_trend` | Price Volume Trend |
| `tv_builtin_rank_correlation_index` | Rank Correlation Index |
| `tv_builtin_ratio` | Ratio |
| `tv_builtin_regression_trend` | Regression Trend |
| `tv_builtin_relative_vigor_index` | Relative Vigor Index |
| `tv_builtin_relative_volatility_index` | Relative Volatility Index |
| `tv_builtin_session_volume_profile` | Session Volume Profile |
| `tv_builtin_sessions` | Sessions |
| `tv_builtin_smi_ergodic_indicator_oscillator` | SMI Ergodic Indicator/Oscillator |
| `tv_builtin_spread` | Spread |
| `tv_builtin_standard_error` | Standard Error |
| `tv_builtin_standard_error_bands` | Standard Error Bands |
| `tv_builtin_stochastic_rsi` | Stochastic RSI |
| `tv_builtin_supertrend` | SuperTrend |
| `tv_builtin_trend_strength_index` | Trend Strength Index |
| `tv_builtin_triple_ema` | Triple EMA |
| `tv_builtin_trix` | TRIX |
| `tv_builtin_true_strength_indicator` | True Strength Indicator |
| `tv_builtin_typical_price` | Typical Price |
| `tv_builtin_ultimate_oscillator` | Ultimate Oscillator |
| `tv_builtin_volatility_index` | Volatility Index |
| `tv_builtin_volatility_o_h_l_c` | Volatility O-H-L-C |
| `tv_builtin_volatility_zero_trend_close_to_close` | Volatility Zero Trend Close-to-Close |
| `tv_builtin_volume_oscillator` | Volume Oscillator |
| `tv_builtin_volume_profile_fixed_range` | Volume Profile Fixed Range |
| `tv_builtin_volume_profile_visible_range` | Volume Profile Visible Range |
| `tv_builtin_vortex_indicator` | Vortex Indicator |
| `tv_builtin_vwma` | VWMA |
| `tv_builtin_williams_alligator` | Williams Alligator |
| `tv_builtin_williams_fractal` | Williams Fractal |
| `tv_builtin_williams_r` | Williams %R |
| `tv_bv2arqnd_cup_finder` | Cup Finder |
| `tv_bvyz1cdf_bernoulli_process_binary_entropy_function` | Bernoulli Process - Binary Entropy Function |
| `tv_bwbicwa6_emd_trend_investorunknown` | EMD Trend [InvestorUnknown] |
| `tv_by9maioc_oscillator_workbench_chart_lucf` | Oscillator Workbench — Chart [LucF] |
| `tv_bzgubzri_smart_trader_episode_03_by_ata_sabanci_candles_and_tradelines` | Smart Trader, Episode 03, by Ata Sabanci, Candles and Tradelines |
| `tv_bzo4yadb_per_bak_self_organized_criticality` | Per Bak Self-Organized Criticality |
| `tv_c2fzxjii_evar_indicator_and_position_sizing` | EVaR Indicator and Position Sizing |
| `tv_c75af3t1_fractional_ema_kalman_filter_d7` | Fractional EMA Kalman Filter [D7] |
| `tv_c7z3p2xh_dynamic_money_flow` | Dynamic Money Flow |
| `tv_c8rargoe_relative_crypto_dominance_polar_chart_luxalgo` | Relative Crypto Dominance Polar Chart [LuxAlgo] |
| `tv_capg3ivf_bjorgum_key_levels` | Bjorgum Key Levels |
| `tv_cbnacnmq_volume_and_price_z_score_multi_asset_by_leviathan` | Volume and Price Z-Score [Multi-Asset] - By Leviathan |
| `tv_cdu6e9rm_volume_footprint_luxalgo` | Volume Footprint [LuxAlgo] |
| `tv_cgbtzxz3_zigzag_candles` | Zigzag Candles |
| `tv_cghgbnh9_naked_intrabar_poc` | Naked Intrabar POC |
| `tv_chhv7iv6_cta_trading_strategy_only_system_you_need_to_use` | CTA TRADING STRATEGY - ONLY SYSTEM YOU NEED TO USE |
| `tv_cjnk8au1_volume_bubbles_quantalgo` | Volume Bubbles [QuantAlgo] |
| `tv_cjx3k6l2_stop_loss_cascades_breakouts_kioseff_trading` | Stop Loss Cascades (Breakouts) [Kioseff Trading] |
| `tv_clk71qgy_machine_learning_adaptive_supertrend_algoalpha` | Machine Learning Adaptive SuperTrend [AlgoAlpha] |
| `tv_cluzc70g_wavetrend_3d` | WaveTrend 3D |
| `tv_cmforvlp_dual_phase_reversal_by_dgt` | Dual-Phase Reversal by DGT |
| `tv_cojscaaa_multi_asset_similarity_matrix` | Multi Asset Similarity Matrix |
| `tv_cp49eqt5_probability_cones` | Probability Cones |
| `tv_cq5x2ame_ar_forecast_scatterplot_ss` | AR Forecast Scatterplot [SS] |
| `tv_ctjx82hp_extrapolated_pivot_connector_lets_make_support_and_resistances` | Extrapolated Pivot Connector - Lets Make Support And Resistances |
| `tv_ctwzt4va_tick_travel` | Tick travel ⍗ |
| `tv_cujanbts_kinetic_slippage_index_ksi` | Kinetic Slippage Index (KSI) |
| `tv_cwm8ucfq_whale_liquidity_and_absorption_profile_algoalpha` | Whale Liquidity and Absorption Profile [AlgoAlpha] |
| `tv_cy6rizcl_probability_distribution_histogram` | Probability Distribution Histogram |
| `tv_czknkfns_technical_rank` | Technical Rank |
| `tv_cztmlgfy_magnificent_7_oscillator` | Magnificent 7 Oscillator |
| `tv_d2nmolmk_mxwll_price_action_suite_mxwll` | Mxwll Price Action Suite [Mxwll] |
| `tv_d3iafa7c_trend_impulse_channels_zeiierman` | Trend Impulse Channels (Zeiierman) |
| `tv_d4tdeuru_volume_composition_flowly_indicators` | Volume composition / Flowly Indicators |
| `tv_daukfrmd_hurst_diamond_notation_pivots` | Hurst Diamond Notation Pivots |
| `tv_ddvp5qaz_match_finder_theultimator5` | Match Finder [theUltimator5] |
| `tv_de2slurk_average_lines` | Average Lines |
| `tv_df63cmxh_quartile_vol_vol_aggregation_range_us_bars_gaps_kioseff` | (Quartile Vol.; Vol. Aggregation; Range US Bars; Gaps) [Kioseff] |
| `tv_dfy6orqi_intraday_volume_swings` | Intraday Volume Swings |
| `tv_dgmumvhd_black_scholes_options_pricing_model` | Black-Scholes Options Pricing Model |
| `tv_dh3cpnga_doubled_numbered_square_of_nine_progression_regression` | Doubled Numbered Square of Nine Progression / Regression |
| `tv_dhpw18sb_multiple_frequency_volatility_correlation` | Multiple Frequency Volatility Correlation |
| `tv_djr8hv4v_waindrops_makit0` | Waindrops [Makit0] |
| `tv_dksawola_next_pivot_projection_trendoscope` | Next Pivot Projection [Trendoscope] |
| `tv_dluyt9rs_trader_s_guide_to_options_part_2` | Trader's Guide to Options Part 2 |
| `tv_dogvqoph_stochastic_weights_basic_bigbitsio` | Stochastic Weights - Basic [BigBitsIO] |
| `tv_dq9wjj11_average_volume_profile` | Average Volume Profile |
| `tv_dqfelcpl_gex_flow_absorption_fvg_orb_mas_signals` | GEX Flow + Absorption + FVG + ORB + MAs + Signals |
| `tv_drx2sbyv_vix_curve_pro_real_time_term_structure_with_statistics` | VIX Curve Pro - Real-Time Term Structure with Statistics |
| `tv_du228vjm_flag_finder` | Flag Finder |
| `tv_dxc0pi3n_swingarm_atr_trend_indicator` | SwingArm ATR Trend Indicator |
| `tv_dyb13ida_hull_candles_bigbitsio` | Hull Candles [BigBitsIO] |
| `tv_e2s2v4fl_byo_pattern_v1_trendoscope` | BYO Pattern V1 [Trendoscope] |
| `tv_e5azkgtc_best_dollar_cost_average` | BEST Dollar Cost Average |
| `tv_e5hytuxi_my_fib_methodology_for_defining_trend` | My FIB Methodology for Defining trend. |
| `tv_e5kzxosk_tasc_2021_12_directional_movement_w_hann` | TASC 2021.12 Directional Movement w/Hann |
| `tv_e9l1xaqd_support_resistance_mtf` | Support Resistance MTF |
| `tv_eabatkg5_how_to_use_volume_with_trends` | How to use Volume with Trends. |
| `tv_ebb5mw6b_extreme_trend_reversal_points_hewhomustnotbenamed` | Extreme Trend Reversal Points [HeWhoMustNotBeNamed] |
| `tv_edel00bp_risk_adjusted_momentum_oscillator` | Risk-Adjusted Momentum Oscillator |
| `tv_eetjcnc8_dividend_calendar_zeiierman` | Dividend Calendar (Zeiierman) |
| `tv_efbdipvs_bjorgum_autotrail` | Bjorgum AutoTrail |
| `tv_efxi515c_linear_regression_channel` | Linear Regression Channel |
| `tv_eihtlrnm_jrl_mm_fibonacci` | [JRL] MM Fibonacci |
| `tv_eis1vcdx_golden_ratio_cubes_gorac` | 'Golden ratio' Cubes - 'GoRaC' |
| `tv_ej53t8wv_support_resistance_channels` | Support Resistance Channels |
| `tv_eji1igag_binomial_option_pricing_model` | Binomial Option Pricing Model |
| `tv_ejmwjmdf_dynamic_gap_probability_tool` | Dynamic Gap Probability Tool |
| `tv_ekbuz93v_delta_ladder_kioseff_trading` | Delta Ladder [Kioseff Trading] |
| `tv_ekkb1vlg_voss_predictor_a_peek_into_the_future_dr_john_ehlers` | Voss Predictor (A Peek Into the Future) - Dr. John Ehlers |
| `tv_ektpaxcq_bloomberg_financial_conditions_index_proxy` | Bloomberg Financial Conditions Index (Proxy) |
| `tv_enc8rzn0_modern_portfolio_management_indicator` | Modern Portfolio Management Indicator |
| `tv_eoijuoln_synthetic_vx3_vx4_continuous_vx_futures` | Synthetic VX3! & VX4! continuous /VX futures |
| `tv_eolvuvxl_market_manipulation_index_mmi` | Market Manipulation Index (MMI) |
| `tv_eos9u1qm_fair_value_bands_flowly_indicators` | Fair value bands / Flowly Indicators |
| `tv_eqlogqrf_rs_simple_forecast_keltner_worms` | [RS]Simple Forecast - Keltner Worms |
| `tv_er9y7zmm_log_regression_oscillator_channel_bigbeluga` | Log Regression Oscillator Channel [BigBeluga] |
| `tv_erbzovy8_fair_value_gap` | Fair Value Gap |
| `tv_ertrxbpf_musashi_fractal_dimension` | Musashi_Fractal_Dimension |
| `tv_etm15sgp_moving_averages_3d` | Moving Averages 3D |
| `tv_ev2tidhj_faith_indicator` | Faith Indicator |
| `tv_ewwysggk_smooth_theil_sen` | Smooth Theil-Sen |
| `tv_exaabrye_education_trends_and_basic_patterns` | EDUCATION - TRENDS AND BASIC PATTERNS  |
| `tv_eyhkvavh_index_generator_by_muqwishi` | Index Generator [By MUQWISHI] |
| `tv_f2oh2wqt_volumatic_support_resistance_levels_bigbeluga` | Volumatic Support/Resistance Levels [BigBeluga] |
| `tv_f2yleyoo_delta_volume_columns_pro_lucf` | Delta Volume Columns Pro [LucF] |
| `tv_f6fk5ima_function_weighted_standard_deviation` | Function - Weighted Standard Deviation |
| `tv_fd3r5rrb_33_years_ago_1987_terminal_pattern_in_spx500_diagrammed` | 33 Years Ago - 1987 TERMINAL Pattern in $SPX500 Diagrammed  |
| `tv_fgvtpifr_tf_segmented_linear_regression` | TF Segmented Linear Regression |
| `tv_fk25igs7_price_convergence` | Price Convergence |
| `tv_fletgfxw_ss_linear_modeler` | [SS] Linear Modeler |
| `tv_fnlmn99w_tasc_2026_09_adaptive_supersmoother` | TASC 2026.09 Adaptive SuperSmoother |
| `tv_fnxxrrpg_auto_pitchfork_fib_retracement_and_zig_zag_by_dgt` | Auto Pitchfork, Fib Retracement and Zig Zag by DGT |
| `tv_fqmvaak9_volume_profile_makit0` | Volume Profile [Makit0] |
| `tv_fqnxjggs_cycles_analysis` | Cycles Analysis |
| `tv_fra2t8gk_blockchain_fundamentals_active_address_sentiment_osc_cr` | Blockchain Fundamentals - Active Address Sentiment Osc. [CR] |
| `tv_ft4zyo1f_swing_structure_forecast_boswaves` | Swing Structure Forecast [BOSWaves] |
| `tv_fuzfly3o_is_it_time_to_lighten_equities_and_go_overweight_gold` | Is it time to lighten equities and go overweight gold? |
| `tv_fvpgxfb3_wolfe_scanner_multi_zigzag_hewhomustnotbenamed` | Wolfe Scanner (Multi - zigzag) [HeWhoMustNotBeNamed] |
| `tv_fwb6gwpc_support_resistance_ai_k_means_median_thinklogicai` | Support & Resistance AI (K means/median) [ThinkLogicAI] |
| `tv_fxnublkt_revolution_volatility_bands_with_range_contraction_signal_vii` | Revolution Volatility Bands With Range Contraction Signal VII |
| `tv_g30euydh_liquidity_thermal_map_bigbeluga` | Liquidity Thermal Map [BigBeluga] |
| `tv_g7gugu9i_rs_simplistic_automatic_growth_models` | [RS]Simplistic Automatic Growth Models |
| `tv_gamszeig_logarithmic_moving_average_lma_quantalgo` | Logarithmic Moving Average (LMA) [QuantAlgo] |
| `tv_gbc8qoy8_a_quick_guide_to_multi_timeframe_scaling` | A Quick Guide to Multi-Timeframe Scaling |
| `tv_gbesfgsq_nasdaq_day_and_night_breakdown` | Nasdaq Day and night breakdown |
| `tv_gdgxyl8b_recursive_reversal_chart_patterns_trendoscope` | Recursive Reversal Chart Patterns [Trendoscope] |
| `tv_gfhcvho3_how_to_use_multi_timeframe_analysis_and_what_it_means` | How to Use Multi-Timeframe Analysis and What It Means |
| `tv_gflv7t7r_swing_profile_bigbeluga` | Swing Profile [BigBeluga] |
| `tv_ghocsiv7_gap_filling_strategy` | Gap Filling Strategy  |
| `tv_gjpxvoub_education_excerpt_sma_lwma_gma_tma_ema` | Education Excerpt: SMA, LWMA, GMA, TMA, EMA |
| `tv_gjugg1kv_key_ideas_to_trade_big_daily_structures_example_on_amat` | Key Ideas to trade big daily structures. Example on AMAT |
| `tv_glj0deuy_indicator_introduction_custom_volume_periodic_peaks_troughs` | Indicator introduction: Custom Volume - Periodic Peaks & Troughs |
| `tv_gpct4m6t_machine_learning_knn_based_strategy` | Machine Learning: kNN-based Strategy |
| `tv_gqklw3yv_tasc_2026_05_the_autotune_filter` | TASC 2026.05 The AutoTune Filter |
| `tv_gsrqnt8q_trend_line_methods_tlm` | Trend Line Methods (TLM) |
| `tv_guxndiot_interactive_atr_stop_loss_tanhef` | Interactive ATR Stop-Loss [TANHEF] |
| `tv_gxqp712z_portfolio_laboratory_kioseff_trading` | Portfolio Laboratory [Kioseff Trading] |
| `tv_gy4ilk5n_momentum_based_zigzag_incl_qqe_non_repainting` | Momentum-based ZigZag (incl. QQE) NON-REPAINTING |
| `tv_gyifyer4_how_to_identify_mean_reversion_vs_complete_reversal` | How to Identify Mean Reversion VS Complete Reversal |
| `tv_gztrrvcd_distance_to_demand_vector` | Distance to Demand Vector |
| `tv_h0yse9xz_rsi_direction_bias_jd` | RSI direction bias - JD |
| `tv_h0yzptis_delta_volume_candles_lucf` | Delta Volume Candles [LucF] |
| `tv_h4xuu8kn_dynamic_rsi_regression_bands_zeiierman` | Dynamic RSI Regression Bands (Zeiierman) |
| `tv_h7koz2pw_the_one_chart_pattern_that_you_must_trade` | The One Chart Pattern That You Must Trade!!! |
| `tv_h93g3fqn_how_to_trade_holiday_s_and_low_volume_environments` | How To Trade Holiday's and Low Volume Environments |
| `tv_haxmmjon_risk_distribution_histogram` | Risk Distribution Histogram |
| `tv_hbmp20tn_volume_profile_with_a_few_polylines` | Volume Profile with a few polylines |
| `tv_hcokncdk_percent_rank_histogram` | Percent Rank Histogram |
| `tv_hdskv6q5_ltf_volume_microburst_bubbles_zeiierman` | LTF Volume Microburst Bubbles (Zeiierman) |
| `tv_hefekydl_sma_directional_matrix_luxalgo` | SMA Directional Matrix [LuxAlgo] |
| `tv_hfcy7ciq_cvd_cumulative_volume_delta_chart` | CVD - Cumulative Volume Delta (Chart) |
| `tv_hfizhwba_rs_donchian_hl_width_cycle_information` | [RS]Donchian HL Width - Cycle Information |
| `tv_hi8pzktb_evaluation_of_bitcoin` | Evaluation of Bitcoin? |
| `tv_hixxuhev_resampling_filter_pack_dw` | Resampling Filter Pack [DW] |
| `tv_hjgcuw6g_dynamic_equity_allocation_model` | Dynamic Equity Allocation Model |
| `tv_hjgk75ze_how_to_identify_ethereums_trend` | How to Identify Ethereum’s Trend |
| `tv_hjjizrog_manual_harmonic_patterns_with_interactive_inputs` | Manual Harmonic Patterns - With interactive inputs |
| `tv_hjxrfmmg_session_candles_reversals_flowly_indicators` | Session candles & reversals / Flowly Indicators |
| `tv_hkjvjhbt_breakouts_pullbacks_trendoscope` | Breakouts & Pullbacks [Trendoscope®] |
| `tv_hl1sw0i4_uhl_ma_crossover_system` | Uhl MA Crossover System |
| `tv_hl4uheb9_max_gain` | Max Gain |
| `tv_hlktlpwc_oscillator_scatterplot_analysis_trendoscope` | Oscillator Scatterplot Analysis [Trendoscope®] |
| `tv_hnpilzeg_market_sessions_by_leviathan` | Market Sessions - By Leviathan |
| `tv_hocpm5uy_alculation_a_position_size_based_on_risk` | Сalculation a position size based on risk |
| `tv_htaf8nf9_market_sessions_viewer_panel_by_muqwishi` | Market Sessions & Viewer Panel [By MUQWISHI] |
| `tv_htj7v7sx_arbitrage_matrix_luxalgo` | Arbitrage Matrix [LuxAlgo] |
| `tv_hv8ghojp_recursive_auto_pitchfork_trendoscope` | Recursive Auto-Pitchfork [Trendoscope] |
| `tv_hvk0dicj_abc_123_harmonic_ratio_custom_range_interactive` | ABC 123 Harmonic Ratio Custom Range Interactive |
| `tv_hvk5wzpi_smart_money_breakout_channels_algoalpha` | Smart Money Breakout Channels [AlgoAlpha] |
| `tv_hvn0eeko_multi_anchored_linear_regression_channels_tanhef` | Multi-Anchored Linear Regression Channels [TANHEF] |
| `tv_hxxk64fl_sip_evaluator_and_screener_trendoscope` | SIP Evaluator and Screener [Trendoscope®] |
| `tv_hyeodyzn_lowess_locally_weighted_scatterplot_smoothing_chartprime` | LOWESS (Locally Weighted Scatterplot Smoothing) [ChartPrime] |
| `tv_i0mhumsk_focus_bars_kioseff_trading` | Focus Bars [Kioseff Trading] |
| `tv_i4ifuwsu_daily_play_ace_spectrum` | Daily Play Ace Spectrum |
| `tv_i4xznaoy_std_filtered_n_pole_gaussian_filter_loxx` | STD-Filtered, N-Pole Gaussian Filter [Loxx] |
| `tv_i5qjdpxt_redk_everex_effort_versus_results_explorer` | RedK EVEREX - Effort Versus Results Explorer |
| `tv_i8qanszp_tasc_2025_01_linear_predictive_filters` | TASC 2025.01 Linear Predictive Filters |
| `tv_i9tjotjl_lube` | LUBE |
| `tv_icrp4b2u_stochastic_momentum_index_smi_of_money_flow_index_mfi` | Stochastic Momentum Index (SMI) of Money Flow Index (MFI) |
| `tv_ieahireo_rs_bar_pattern_statistics_tool` | [RS]Bar Pattern Statistics Tool |
| `tv_if0jgsn1_p_square_estimation_of_the_nth_percentile_of_a_series` | P-Square - Estimation of the Nth percentile of a series |
| `tv_ifjxxalc_the_investment_clock_orbital_graph` | The Investment Clock Orbital Graph |
| `tv_ifw3re7j_equivolume_overlay_volume_bars` | Equivolume Overlay - Volume Bars |
| `tv_ih8z9vsb_automatic_trendlines` | Automatic Trendlines |
| `tv_iini8ml2_weighted_harrell_davis_quantile_estimator_with_absolutedeviation` | Weighted Harrell-Davis Quantile Estimator with AbsoluteDeviation |
| `tv_ijpiemfw_rolling_largest_impulse_murreys_lines` | Rolling largest Impulse Murreys Lines |
| `tv_ikvq3zpr_defining_a_single_market_indicator_in_tradingview` | Defining a single market indicator in TradingView - |
| `tv_in9ftv45_divergence_for_many_indicator_v3` | Divergence for many indicator v3 |
| `tv_ioqkeiwd_ichimoku_theories_luxalgo` | Ichimoku Theories [LuxAlgo] |
| `tv_ipddusgl_dynamic_linear_regression_channels` | Dynamic Linear Regression Channels |
| `tv_ipvs7b7x_multi_ticker_anchored_candles` | Multi-Ticker Anchored Candles |
| `tv_iqq6b3pk_yield_curve_percent_inverted` | Yield Curve Percent Inverted |
| `tv_iznark90_time_sales_tape_by_muqwishi` | Time & Sales (Tape) [By MUQWISHI] |
| `tv_j38vuavw_intrabar_profile_kioseff_trading` | Intrabar Profile [Kioseff Trading] |
| `tv_j8fs5jmi_swing_high_low_anchored_spiral` | Swing High/Low Anchored Spiral |
| `tv_j9a6nwwm_volume_open_interest_footprint_by_leviathan` | Volume / Open Interest \"Footprint\" - By Leviathan |
| `tv_jcrhuirl_tensor_market_analysis_engine_tmae` | Tensor Market Analysis Engine (TMAE) |
| `tv_jdw7ww2g_technical_ratings` | Technical Ratings |
| `tv_jgafgaly_gann_theory_finally_completed_strategy` | GANN Theory Finally Completed Strategy |
| `tv_jja8tyjc_redk_auto_stepping_ladder_trader` | RedK Auto-Stepping Ladder Trader |
| `tv_jjhuhcje_stepped_trailing_strategy_example` | Stepped trailing strategy example |
| `tv_jlrxim5v_rsi_bar_chart` | RSI Bar Chart |
| `tv_jncgedj7_order_chain_kioseff_trading` | Order Chain [Kioseff Trading] |
| `tv_jpbq3j0s_t_virus_sentiment_hapharmonic` | T-Virus Sentiment [hapharmonic] |
| `tv_jpkfecgc_no_duplicates_interval_range_eq` | No Duplicates Interval Range & EQ |
| `tv_jqrhr1xy_relative_strength_of_volume_indicators_by_dgt` | Relative Strength of Volume Indicators by DGT |
| `tv_jumbqtqk_time_series_lag_reduction_filter_by_cryptorhythms` | Time Series Lag Reduction Filter by Cryptorhythms |
| `tv_juwuaxdx_deltaflow_volume_profile_bigbeluga` | DeltaFlow Volume Profile [BigBeluga] |
| `tv_jxgpf0jz_tasc_2024_07_gaps_and_extreme_closes` | TASC 2024.07 Gaps and Extreme Closes |
| `tv_jz2cehpf_be_indicator_aggregator_toolkit` | BE-Indicator Aggregator toolkit |
| `tv_jzxkmci2_williams_fractal_trailing_stops` | Williams Fractal Trailing Stops |
| `tv_k2br8xol_intraday_spark_chart_astrideunicorn` | Intraday Spark Chart [AstrideUnicorn] |
| `tv_k6olgkao_relative_candle` | Relative Candle |
| `tv_kehhfjfb_everything_you_need_to_know_about_spacs` | Everything You Need to Know About SPACs |
| `tv_kfuhomlx_redk_supply_demand_volume_viewer_v1` | RedK_Supply/Demand Volume Viewer v1 |
| `tv_kgcatbqy_sd_distance_mean_beta` | SD Distance Mean Beta |
| `tv_kjd8byiq_augmented_dickeyfuller_adf_mean_reversion_test` | Augmented Dickey–Fuller (ADF) mean reversion test |
| `tv_kjj8hddk_dynamic_dots_dashboard_a_cloud_zlema_composite` | Dynamic Dots Dashboard (a Cloud/ZLEMA Composite) |
| `tv_kjpmckbt_bitcoin_power_law_clock_luxalgo` | Bitcoin Power Law Clock [LuxAlgo] |
| `tv_kn353wpw_responsive_linear_regression_channels` | Responsive Linear Regression Channels |
| `tv_ks2qgulb_initial_balance_auction_intelligence_by_dgt` | Initial Balance Auction Intelligence by DGT |
| `tv_ksmls0hh_supertrend_parameter_sensitivity_3d_luxalgo` | Supertrend Parameter Sensitivity 3D [LuxAlgo] |
| `tv_kvrhsptp_elliott_wave_luxalgo` | Elliott Wave [LuxAlgo] |
| `tv_kzjqxdgq_cot_net_non_commercials_vs_commercials_updated_mtf_non_repaint` | COT Net Non-Commercials vs Commercials (Updated MTF Non-Repaint) |
| `tv_l0aiilvh_pivot_point_supertrend` | Pivot Point Supertrend |
| `tv_l1zvvqbx_monte_carlo_polyline_traceback_kioseff_trading` | Monte Carlo (Polyline Traceback) [Kioseff Trading] |
| `tv_l2lxyays_zig_zag_volume_profile_bull_vs_bear_kioseff_trading` | Zig-Zag Volume Profile (Bull vs. Bear) [Kioseff Trading] |
| `tv_l6nreqzb_adaptive_trend_classification_moving_averages_investorunknown` | Adaptive Trend Classification: Moving Averages [InvestorUnknown] |
| `tv_lbrwvaq7_my_trading_strategy_in_4_simple_steps` | My Trading Strategy in 4 simple steps. |
| `tv_lbxl9oqz_financials_on_chart` | Financials on Chart |
| `tv_lcgcwwwi_bar_balance_lucf` | Bar Balance [LucF] |
| `tv_ldxohpmz_volume_cluster_profile_vcp_zeiierman` | Volume Cluster Profile [VCP] (Zeiierman) |
| `tv_lei57qv6_rotation_in_international_markets` | Rotation in international markets |
| `tv_lfe3imad_how_to_find_the_best_trending_momentum_stocks_across_the_globe` | How to find the best trending momentum stocks across the globe |
| `tv_library_12ferxal_is3driver` | HarmonicPattern: is3Driver |
| `tv_library_12ferxal_is4tap` | HarmonicPattern: is4Tap |
| `tv_library_12ferxal_is5o` | HarmonicPattern: is5o |
| `tv_library_12ferxal_isabcd` | HarmonicPattern: isABCD |
| `tv_library_12ferxal_isbat` | HarmonicPattern: isBat |
| `tv_library_12ferxal_isbutterfly` | HarmonicPattern: isButterfly |
| `tv_library_12ferxal_iscrab` | HarmonicPattern: isCrab |
| `tv_library_12ferxal_isgartley` | HarmonicPattern: isGartley |
| `tv_library_12ferxal_isharmonictriangle` | HarmonicPattern: isHarmonicTriangle |
| `tv_library_12ferxal_isshark` | HarmonicPattern: isShark |
| `tv_library_12ferxal_iswolfe` | HarmonicPattern: isWolfe |
| `tv_library_94iacmva_holt` | MovingAverages: Holt |
| `tv_library_94iacmva_laguerre` | MovingAverages: Laguerre |
| `tv_library_94iacmva_one_euro` | MovingAverages: One Euro |
| `tv_library_94iacmva_slew_rate_limiter` | MovingAverages: Slew Rate Limiter |
| `tv_library_94iacmva_smooth_damp` | MovingAverages: Smooth Damp |
| `tv_library_94iacmva_super_smoother` | MovingAverages: Super Smoother |
| `tv_library_94iacmva_swma` | MovingAverages: SWMA |
| `tv_library_x8mujqgt_abandoned_baby` | BjCandlePatterns: abandonedBull, abandonedBear |
| `tv_library_x8mujqgt_doji_variants` | BjCandlePatterns: dragonflyDoji, gravestoneDoji |
| `tv_library_x8mujqgt_harami_cross` | BjCandlePatterns: haramiBullCross, haramiBearCross |
| `tv_library_x8mujqgt_kicking` | BjCandlePatterns: kickingBull, kickingBear |
| `tv_library_x8mujqgt_long_shadow` | BjCandlePatterns: lls, lus |
| `tv_library_x8mujqgt_marubozu` | BjCandlePatterns: marubullzu, marubearzu |
| `tv_library_x8mujqgt_neck` | BjCandlePatterns: bullNeck, bearNeck |
| `tv_library_x8mujqgt_piercing_dark_cloud` | BjCandlePatterns: piercing, darkCloudCover |
| `tv_library_x8mujqgt_spinning_top` | BjCandlePatterns: spinningTopBull, spinningTopBear, spinningTop |
| `tv_library_x8mujqgt_tasuki_gap` | BjCandlePatterns: tasukiBull, tasukiBear |
| `tv_library_x8mujqgt_three_methods` | BjCandlePatterns: risingThree, fallingThree |
| `tv_library_x8mujqgt_tristar` | BjCandlePatterns: triStarBull, triStarBear |
| `tv_library_x8mujqgt_tweezer` | BjCandlePatterns: tweezerBottom, tweezerTop |
| `tv_library_x8mujqgt_window_gap` | BjCandlePatterns: risingWindow, fallingWindow |
| `tv_linquv2i_zigzag_volume_bars` | Zigzag Volume Bars |
| `tv_llaoploy_liquidation_ranges_volume_oi_dots_kioseff_trading` | Liquidation Ranges + Volume/OI Dots [Kioseff Trading] |
| `tv_llg6gdb4_open_interest_footprint_iq_tradingiq` | Open Interest Footprint IQ [TradingIQ] |
| `tv_llhsdjyh_angle_market_structure_bigbeluga` | Angle Market Structure [BigBeluga] |
| `tv_lmirygpg_vortex_mtf` | Vortex MTF |
| `tv_lncfcfod_googl_ipo_base_to_study_for_future_trades` | GOOGL: IPO Base to study for Future trades |
| `tv_lper4qca_volume_analysis_heatmap_and_volume_profile` | Volume Analysis - Heatmap and Volume Profile |
| `tv_lpnsjmbh_clusters_volume_profile_luxalgo` | Clusters Volume Profile [LuxAlgo] |
| `tv_lr5qd0kk_screener_mean_reversion_channel` | Screener - Mean Reversion Channel |
| `tv_lrdshlst_sniffer` | Sniffer |
| `tv_ls42zpse_72s_adaptive_hull_moving_average` | 72s: Adaptive Hull Moving Average+ |
| `tv_lu0mtsud_earnings_snapshot_trendoscope` | Earnings Snapshot [Trendoscope] |
| `tv_lut7sbgg_range_filter_dw` | Range Filter [DW] |
| `tv_lvqopkkp_volume_surprise_luxalgo` | Volume Surprise [LuxAlgo] |
| `tv_lwoxh0vh_range_volume_change` | Range Volume Change |
| `tv_lx3zlt9l_volume_profile_3d_zeiierman` | Volume Profile 3D (Zeiierman) |
| `tv_lxhedc8e_machine_learning_using_neural_networks_educational` | Machine Learning using Neural Networks / Educational |
| `tv_lxxlkr1w_recession_warning_traffic_light` | Recession Warning Traffic Light |
| `tv_m88uomnh_techniques_for_getting_better_prices` | Techniques For Getting Better Prices 🎯 |
| `tv_mb0famot_advanced_fed_decision_forecast_model_afdfm` | Advanced Fed Decision Forecast Model (AFDFM) |
| `tv_mbxxbs1f_redk_directional_index_k_xdmi` | RedK_Directional Index / K xDMI |
| `tv_mc8mxglm_fearzone_panel` | Fearzone Panel |
| `tv_mdgjq4j5_simplified_percentile_clustering` | Simplified Percentile Clustering |
| `tv_mdtqpnt0_excalibur_ehlers_autocorrelation_periodogram_modified` | [Excalibur] Ehlers AutoCorrelation Periodogram Modified |
| `tv_mekxyft0_bias_and_sentiment_strength_bass_indicator_by_mattzab` | Bias And Sentiment Strength (BASS) Indicator by mattzab |
| `tv_method_atr_trailing` | ATR trailing band stops |
| `tv_method_bump_run` | Bump and run reversal BARR |
| `tv_method_candlestick_patterns` | Candlestick pattern recognition |
| `tv_method_covered_call` | Covered call strike selection |
| `tv_method_cup_handle` | Cup and handle |
| `tv_method_doji` | Doji indecision |
| `tv_method_dominance_rotation` | Bitcoin dominance and altcoin rotation |
| `tv_method_double_top_bottom` | Double top and double bottom |
| `tv_method_elliott_wave` | Elliott wave counts |
| `tv_method_engulfing` | Bullish and bearish engulfing |
| `tv_method_fair_value_gap` | Three-candle fair value gap |
| `tv_method_fib_extensions` | Fibonacci extension and channel projections |
| `tv_method_flag_pennant` | Flag and pennant continuation |
| `tv_method_fourier_cycle` | Fourier and dominant cycle estimation |
| `tv_method_futures_hedge` | Spot and futures hedge |
| `tv_method_gann` | Gann time and price geometry |
| `tv_method_gap_fill` | Session and CME gap fill |
| `tv_method_hammer` | Hammer and hanging man |
| `tv_method_harami` | Harami inside-body reversal |
| `tv_method_harmonic_xabcd` | XABCD harmonic ratios |
| `tv_method_head_shoulders` | Head and shoulders reversal |
| `tv_method_heikin_ashi` | Heikin Ashi trend candles |
| `tv_method_inside_bar` | Inside bar and narrow range breakout |
| `tv_method_intermarket_correlation` | Intermarket correlation and lead lag |
| `tv_method_iron_condor` | Iron condor options spread |
| `tv_method_kalman_filter` | Kalman trend state estimation |
| `tv_method_kelly_sizing` | Fractional Kelly position sizing |
| `tv_method_knn_prediction` | K nearest neighbor prediction |
| `tv_method_linear_regression_channel` | Trailing linear regression channel |
| `tv_method_liquidity_sweep` | Liquidity sweep and failed break |
| `tv_method_logistic_prediction` | Logistic regression classification |
| `tv_method_market_profile` | Time price opportunity market profile |
| `tv_method_market_structure` | Higher high and lower low market structure |
| `tv_method_martingale_sizing` | Martingale loss recovery sizing |
| `tv_method_megaphone` | Broadening megaphone formation |
| `tv_method_morning_evening_star` | Morning and evening star |
| `tv_method_neural_prediction` | Neural network return classification |
| `tv_method_oops_gap_reversal` | OOPS opening gap reversal |
| `tv_method_opening_range` | Opening range breakout |
| `tv_method_order_blocks` | Order block zones |
| `tv_method_oscillator_divergence` | Price oscillator divergence |
| `tv_method_pitchfork` | Andrews pitchfork and median lines |
| `tv_method_polynomial_regression` | Trailing polynomial regression |
| `tv_method_quasimodo` | Quasimodo market structure reversal |
| `tv_method_renko` | Renko brick trend |
| `tv_method_risk_based_sizing` | Fixed fractional risk and stop sizing |
| `tv_method_round_number_levels` | Psychological round number levels |
| `tv_method_rsi_divergence` | RSI divergence |
| `tv_method_seasonality` | Calendar and time of day seasonality |
| `tv_method_shooting_star` | Shooting star and inverted hammer |
| `tv_method_support_resistance` | Support and resistance levels |
| `tv_method_td_sequential` | TD Sequential exhaustion counts |
| `tv_method_three_soldiers_crows` | Three white soldiers and three black crows |
| `tv_method_trailing_stop` | Trailing and breakeven stops |
| `tv_method_triangle` | Ascending descending and symmetrical triangles |
| `tv_method_triple_top_bottom` | Triple top and triple bottom |
| `tv_method_value_investing` | Financial ratio value screening |
| `tv_method_vertical_debit_spread` | Vertical debit option spread |
| `tv_method_vix_timing` | VIX term structure and equity timing |
| `tv_method_volume_delta` | Cumulative volume delta |
| `tv_method_volume_footprint` | Volume footprint and absorption |
| `tv_method_volume_spread_analysis` | Volume spread analysis |
| `tv_method_wedge` | Rising and falling wedges |
| `tv_method_wyckoff` | Wyckoff accumulation and distribution |
| `tv_mfgggcef_death_cross_chart_pattern_gold` | Death Cross Chart Pattern - Gold |
| `tv_mfupuzwd_arbitrage_detector_luxalgo` | Arbitrage Detector [LuxAlgo] |
| `tv_mgslckwl_angled_volume_profile_trendoscope` | Angled Volume Profile [Trendoscope] |
| `tv_mheetfmn_a_useful_ma_weighting_function_for_controlling_lag_smoothness` | A Useful MA Weighting Function For Controlling Lag & Smoothness |
| `tv_miig3gou_grid_bot_simulator` | Grid Bot Simulator |
| `tv_mk7uyofu_adjustable_ma_alternating_extremities_luxalgo` | Adjustable MA & Alternating Extremities [LuxAlgo] |
| `tv_mketjg7e_periodic_linear_regressions_luxalgo` | Periodic Linear Regressions [LuxAlgo] |
| `tv_mll8cpjq_range_oscillator_zeiierman` | Range Oscillator (Zeiierman) |
| `tv_moaqapdw_advanced_how_to_aggressively_grow_a_small_10k_account` | [Advanced] How to aggressively grow a small (10k) account? |
| `tv_mombnm8e_tick_cvd_kioseff_trading` | Tick CVD [Kioseff Trading] |
| `tv_muxarne5_audcad_day_trade_signal_by_keltner_channel` | AUDCAD - Day trade signal by Keltner channel |
| `tv_mvkdf8qh_trendmaster_pro_2_3_with_alerts` | TrendMaster Pro 2.3 with Alerts |
| `tv_mvlwazsg_3commas_bot` | 3Commas Bot |
| `tv_mxdttwh8_footprint_iq_pro_tradingiq` | Footprint IQ Pro [TradingIQ] |
| `tv_mxn4pesd_htf_volume_spike_imbalance_projection_luxalgo` | HTF Volume Spike & Imbalance Projection [LuxAlgo] |
| `tv_mykmv8br_linear_regression_oscillator_chartprime` | Linear Regression Oscillator [ChartPrime] |
| `tv_n0f50jkv_relative_volume_at_time` | Relative Volume at Time |
| `tv_n3g6jvob_wedge_and_flag_finder_multi_zigzag` | Wedge and Flag Finder (Multi - zigzag) |
| `tv_n8agnizd_divergence_for_many_indicators_v4` | Divergence for Many Indicators v4 |
| `tv_nachnnj6_trading_plan_on_bynd_for_2022_this_is_what_i_want_to_see` | Trading plan on BYND for 2022. This is what I want to see.  |
| `tv_named_4iykx938_4_color_macd` | 4 Color MACD |
| `tv_named_5cv2hgjk_double_macd_buy_sell` | Double MACD buy sell |
| `tv_named_gq9i627q_macd_x_by_dgt` | MACD-X by DGT |
| `tv_named_hnrsbpj2_macz_vwap` | MACZ VWAP |
| `tv_named_jxvqru4q_obv_macd` | OBV MACD |
| `tv_named_nl1z2syw_macd_dema` | MACD DEMA |
| `tv_named_oqx7vju0_customizable_macd_for_any_timeframe` | Customizable MACD for any timeframe |
| `tv_named_qe0umj8p_stick_line_macd` | Stick Line MACD |
| `tv_named_qt6xlfli_impulse_macd` | Impulse MACD |
| `tv_named_slcjqy3v_supersmoothed_macd` | SuperSmoothed MACD |
| `tv_named_the_80_20_trading_strategy` | The 80 – 20 Trading Strategy |
| `tv_named_the_holy_grail_trading_strategy` | The Holy Grail Trading Strategy |
| `tv_named_three_little_indians_trading_strategy` | Three Little Indians Trading Strategy |
| `tv_named_wc7xhzhy_advanced_laguerre_ppo` | Advanced Laguerre PPO |
| `tv_named_yflkxhnp_macdas` | MACDAS |
| `tv_nbptoyxr_asset_drift_model` | Asset Drift Model |
| `tv_ngljvbwa_redk_compound_ratio_moving_average_cora_wave` | RedK Compound Ratio Moving Average (CoRa_Wave) |
| `tv_nh9youzp_unbroke_reversal_signals_kernel_bands` | Unbroke Reversal Signals + Kernel Bands |
| `tv_ni17vkdu_reflex_oscillator_dr_john_ehlers` | Reflex Oscillator - Dr. John Ehlers |
| `tv_niohixy1_logistic_rsi_stoch_roc_ao_by_dgt` | Logistic RSI, STOCH, ROC, AO, ... by DGT |
| `tv_niy5oyf7_volume_by_session` | Volume by Session |
| `tv_nj6cmjkp_donchian_zig_zag_luxalgo` | Donchian Zig-Zag [LuxAlgo] |
| `tv_nlm312nk_cvd_cumulative_volume_delta_candles` | CVD - Cumulative Volume Delta Candles |
| `tv_nlygzrmb_short_volume_stamper` | Short Volume Stamper |
| `tv_nlzhcxgf_hh_ll_zz` | HH-LL ZZ |
| `tv_nueh5q6t_linear_regression_all_data` | Linear Regression (All Data) |
| `tv_nvecqiqx_tasc_2026_03_one_percent_a_week` | TASC 2026.03 One Percent A Week |
| `tv_nw5ogfdo_ict_killzones_pivots_tfo` | ICT Killzones + Pivots [TFO] |
| `tv_nwjy3xpv_first_passage_time_distribution_analysis` | First Passage Time - Distribution Analysis |
| `tv_ny63myd9_time_volume_point_of_control_flowly_indicators` | Time & volume point of control / Flowly Indicators |
| `tv_nzvqcush_detrended_rhythm_oscillator_dro` | Detrended Rhythm Oscillator (DRO) |
| `tv_o0mu1wau_cme_equity_futures_price_limits` | CME Equity Futures Price Limits |
| `tv_o2toj6ez_bitcoin_monthly_seasonality_alpha_extract` | Bitcoin Monthly Seasonality [Alpha Extract] |
| `tv_o52gurxf_redk_momentum_bars_redk_mo_bars` | RedK Momentum Bars (RedK Mo_Bars) |
| `tv_o8trzczt_intrabar_efficiency_ratio` | Intrabar Efficiency Ratio |
| `tv_odyzzlzu_median_convergence_divergence` | Median Convergence Divergence |
| `tv_oe3v6w93_new_technical_tools_back_tested_on_old_extreme_markets` | New Technical Tools Back Tested on Old Extreme Markets |
| `tv_oihw2xg2_delta_rsi_oscillator_strategy` | Delta-RSI Oscillator Strategy |
| `tv_okuj0d2n_earnings_price_move_cheat_sheet_kt` | Earnings Price Move Cheat Sheet [KT] |
| `tv_onab2fve_fair_value_gaps_by_dgt` | Fair Value Gaps by DGT |
| `tv_oneeyhxe_projection` | Projection |
| `tv_oooobeta_htf_candles_pivots` | HTF Candles & Pivots |
| `tv_oqc4nnbf_guide_to_trading_btc_during_consolidation_by_trading_guru` | Guide to Trading BTC During CONSOLIDATION - By Trading-Guru |
| `tv_oqttrc35_tasc_2025_02_autocorrelation_indicator` | TASC 2025.02 Autocorrelation Indicator |
| `tv_ostukg4q_all_candlestick_patterns_on_backtest_by_muqwishi` | All Candlestick Patterns on Backtest [By MUQWISHI] |
| `tv_ou82izcq_reversal_finder` | Reversal finder |
| `tv_oxvr5vmy_grid_like_strategy` | Grid Like Strategy |
| `tv_oyazawb9_d_shape_breakout_signals_luxalgo` | D-Shape Breakout Signals [LuxAlgo] |
| `tv_ozhquifn_trader_s_guide_to_options_part_3` | Trader's Guide to Options Part 3 |
| `tv_p0h2afk4_probability_of_atr_index_racer8` | Probability of ATR Index [racer8] |
| `tv_p2f0pqtd_covid_statistics_tracker_model_projections_by_cryptorhythms` | COVID Statistics Tracker & Model Projections by Cryptorhythms |
| `tv_p3xsntqp_how_to_use_session_volume_hd_to_study_price_and_volume` | How to use Session Volume HD to study price and volume |
| `tv_p5ggwhl5_trailing_management_zeiierman` | Trailing Management (Zeiierman) |
| `tv_p68ukxre_iwm_185_180_march_16_put_credit_spread` | IWM 185/180 March 16 Put Credit Spread |
| `tv_p6xx04kb_vix_multi_tool` | VIX Multi-Tool |
| `tv_p9avc7vy_tpo_market_profile_kioseff_trading` | TPO Market Profile [Kioseff Trading] |
| `tv_pej263bg_volumeheatmap_experimental_version_of_marketorders_matrix` | VolumeHeatmap / Experimental Version of Marketorders Matrix |
| `tv_pk0aidt2_resampling_reverse_engineering_bands_dw` | Resampling Reverse Engineering Bands [DW] |
| `tv_pkflcpyi_mandelbrot_fibonacci_cascade_vortex_mfcv` | Mandelbrot-Fibonacci Cascade Vortex (MFCV) |
| `tv_pkhv9soh_auto_fib_speed_resistance_fans_by_dgt` | Auto Fib Speed Resistance Fans by DGT |
| `tv_pkzxrfha_atai_volume_pressure_analyzer_v_1_0_pure_up_down` | ATAI Volume Pressure Analyzer V 1.0 — Pure Up/Down |
| `tv_pl0ipxy0_htf_liquidity_levels` | HTF Liquidity Levels |
| `tv_pon9i3pi_tutorial_how_smac_can_help_find_the_ideal_covered_call_strike` | Tutorial: How SMAC can help find the Ideal Covered Call Strike |
| `tv_ppjps450_neglected_volume_by_dgt` | Neglected Volume by DGT |
| `tv_psnjpa2y_vwap_price_channel` | VWAP Price Channel |
| `tv_ptcl4kv6_volume_profile_auto_line` | Volume Profile Auto [line] |
| `tv_puwmpoyc_macd_with_htf_panels_theultimator5` | MACD with HTF Panels [theUltimator5] |
| `tv_pvpyfz2h_atr_osc_and_volume_screener_atroscvs` | ATR OSC and Volume Screener (ATROSCVS) |
| `tv_pwvoxmso_machine_learning_pivot_points_knn_ss` | Machine Learning Pivot Points (KNN) [SS] |
| `tv_pxnwlarh_how_i_trade_price_action_structures_patterns` | How I trade Price Action Structures/Patterns |
| `tv_pydmopdi_gme_identical_chart_pattern_as_amc_before_explosive_move` | GME Identical Chart Pattern as AMC Before Explosive Move!!! |
| `tv_q1hxs0v6_liquidity_void_detector_zeiierman` | Liquidity Void Detector (Zeiierman) |
| `tv_q3jrr7sn_spy_expected_move_by_vix` | SPY Expected Move by VIX |
| `tv_q7yifaaf_multi_zigzag_harmonic_patterns` | Multi ZigZag Harmonic Patterns |
| `tv_q7yqqq7g_volume_gaps_imbalances_zeiierman` | Volume Gaps & Imbalances (Zeiierman) |
| `tv_q9oqye4c_hull_suite_strategy` | Hull Suite Strategy |
| `tv_qaaxkw1p_ai_predictive_flow_zeiierman` | AI Predictive Flow (Zeiierman) |
| `tv_qakfjgfu_liquidity_levels_luxalgo` | Liquidity Levels [LuxAlgo] |
| `tv_qamnmxzi_volume_forks_trendoscope` | Volume Forks [Trendoscope] |
| `tv_qe4dq4zm_chart_vwap` | Chart VWAP |
| `tv_qeqcsffc_dekidaka_ashi_candles_and_volume_teaming_up_again` | Dekidaka-Ashi - Candles And Volume Teaming Up (Again) |
| `tv_qetnobdk_half_causal_estimator` | Half Causal Estimator |
| `tv_qhncxbml_relative_strength_rsmk_perks_markos_katsanos` | Relative Strength(RSMK) + Perks - Markos Katsanos |
| `tv_qibyvt4j_hurst_exponent` | Hurst Exponent |
| `tv_ql1t3hh0_fancy_bollinger_bands_bigbitsio` | Fancy Bollinger Bands [BigBitsIO] |
| `tv_qnqbqiex_correlation_heatmap_tradingfinder_sessions_data_science_stats` | Correlation HeatMap [TradingFinder] Sessions Data Science Stats |
| `tv_qnx9nxw0_multi_timeframe_volume_profiles_tradingiq` | Multi Timeframe Volume Profiles [TradingIQ] |
| `tv_qqlorjta_usd_jpy_three_scenarios_and_how_to_trade_them` | USD/JPY: Three Scenarios and How To Trade Them 📊 |
| `tv_qrevzodw_mad_acceleration_based_dampened_sma_projections` | [MAD] Acceleration based dampened SMA projections |
| `tv_qstlq23r_auto_adjust_to_ideal_pearson_s_r_oscillator` | Auto Adjust To Ideal Pearson's R Oscillator |
| `tv_qt7fqntr_breakout_probability_expo` | Breakout Probability (Expo) |
| `tv_qt7frw7q_3d_wave_pm` | 3D Wave-PM |
| `tv_qtkfi42t_macd_x_overlay_more_than_macd_by_dgt` | MACD-X Overlay, More Than MACD by DGT |
| `tv_qtos0wyg_dji_wall_street_pattern_in_the_chaos` | DJI (Wall Street): Pattern in the chaos. |
| `tv_qvcjkcw3_mad_position_starter_calculator` | [MAD] Position starter & calculator |
| `tv_qvsw9gup_moving_average_entanglement` | Moving Average Entanglement |
| `tv_qwmafztl_tasc_2025_06_cybernetic_oscillator` | TASC 2025.06 Cybernetic Oscillator |
| `tv_qypmcjka_lowest_highest_from_widget` | Lowest / Highest From Widget |
| `tv_r72jbjt4_market_matrix_zeiierman` | Market Matrix (Zeiierman) |
| `tv_r7o3zulh_estimated_time_at_price_kioseff_trading` | Estimated Time At Price [Kioseff Trading] |
| `tv_r8g2yhdg_order_block_finder_experimental` | Order Block Finder (Experimental) |
| `tv_rbeervr5_rolling_z_score_trend_quantalgo` | Rolling Z-Score Trend [QuantAlgo] |
| `tv_rcfo5hhf_reverse_stochastic_momentum_index_on_chart` | Reverse Stochastic Momentum Index On Chart |
| `tv_rddlqjfh_berlin_candles` | BERLIN Candles |
| `tv_rdxjz0lr_elliot_waves_complete_guide_chapter_2_3_extensions` | Elliot Waves Complete Guide / Chapter 2.3 - \"Extensions\" |
| `tv_rfbdceg1_gaps_profile_vnhilton` | Gaps Profile [vnhilton] |
| `tv_rgnbiicd_abc_on_recursive_zigzag_trendoscope` | ABC on Recursive Zigzag [Trendoscope] |
| `tv_rlkjr2sq_bjorgum_double_tap` | Bjorgum Double Tap |
| `tv_rnkr88ze_tick_delta_volume` | Tick Delta Volume |
| `tv_rs3xqwyx_support_and_resistance_logistic_regression_flux_charts` | Support and Resistance Logistic Regression / Flux Charts |
| `tv_rtofqf13_trading_activity_index_zeiierman` | Trading Activity Index (Zeiierman) |
| `tv_rtorjfrl_how_to_use_the_rsi_to_find_oversold_stocks_now_recovering` | How To: Use the RSI to find Oversold Stocks now Recovering |
| `tv_rv3pibxo_ttp_vix_spy` | TTP VIX Spy |
| `tv_rxrafvef_langlands_operadic_mobius_vortex_lomv` | Langlands-Operadic Möbius Vortex (LOMV) |
| `tv_rzs7ydmi_renko_candles_overlay` | Renko Candles Overlay |
| `tv_s2clgbm5_volume_based_support_resistance_zones` | Volume-based Support & Resistance Zones |
| `tv_s40vmzm4_asset_rotation_system_investorunknown` | Asset Rotation System [InvestorUnknown] |
| `tv_s7hgang6_intraday_intensity_modes` | Intraday Intensity Modes |
| `tv_s9knr6dg_crowding_model_bullvision` |  Crowding model ║ BullVision |
| `tv_sc6a9izn_quick_tip_add_a_signal_line_to_your_indicator_no_coding` | Quick tip: Add a signal line to your indicator, no coding! |
| `tv_seduwoij_zeiierman_trend_pressure_zeiierman` | Zeiierman Trend Pressure (Zeiierman) |
| `tv_sg5cvyr9_tick_data_detailed` | Tick Data Detailed |
| `tv_sg7vk6uh_iq_trend_beams_tradingiq` | IQ Trend Beams [TradingIQ] |
| `tv_sgfm0bj3_elastic_volume_weighted_student_t_tension` | Elastic Volume-Weighted Student-T Tension |
| `tv_shevujyq_machine_learning_rsi_bullvision` |  Machine Learning RSI ║ BullVision |
| `tv_shvvlgmm_fast_fourier_transform_fft_filter` | Fast Fourier Transform (FFT) Filter |
| `tv_shy8kacw_market_structure_volume_profiles_kioseff_trading` | Market Structure Volume Profiles [Kioseff Trading] |
| `tv_snufopt6_modified_mannarino_market_risk_indicator_mmmri_mmri` | Modified Mannarino Market Risk Indicator MMMRI MMRI |
| `tv_sq5xt0ez_hyperfork_matrix` | Hyperfork Matrix |
| `tv_sr0scav5_wavelet_trend_ml_integration_alpha_extract` | Wavelet-Trend ML Integration [Alpha Extract] |
| `tv_su8qcnj3_expected_value_monte_carlo` | Expected Value Monte Carlo |
| `tv_svp0szo5_tasc_2025_04_the_ultimate_oscillator` | TASC 2025.04 The Ultimate Oscillator |
| `tv_swwmsmqw_indicator_panel` | Indicator Panel |
| `tv_sxgyrede_dynamic_swing_anchored_vwap_zeiierman` | Dynamic Swing Anchored VWAP (Zeiierman) |
| `tv_sxzrzqzq_divergence_indicator_any_oscillator` | Divergence Indicator (any oscillator) |
| `tv_szvbr1vq_kcgmut` | KCGmut |
| `tv_t1v41bl5_session_edge_profiler_flux_charts` | Session Edge Profiler / Flux Charts |
| `tv_ta_frama` | TradingView ta library: frama |
| `tv_ta_ht` | TradingView ta library: ht |
| `tv_ta_ift` | TradingView ta library: ift |
| `tv_ta_pzo` | TradingView ta library: pzo |
| `tv_ta_relativevolume` | TradingView ta library: relativeVolume |
| `tv_ta_rms` | TradingView ta library: rms |
| `tv_ta_rwi` | TradingView ta library: rwi |
| `tv_ta_stc` | TradingView ta library: stc |
| `tv_ta_szo` | TradingView ta library: szo |
| `tv_ta_t3` | TradingView ta library: t3 |
| `tv_ta_trima` | TradingView ta library: trima |
| `tv_ta_vhf` | TradingView ta library: vhf |
| `tv_ta_vstop` | TradingView ta library: vStop |
| `tv_ta_vzo` | TradingView ta library: vzo |
| `tv_ta_wpo` | TradingView ta library: wpo |
| `tv_tbz9rgx9_weekly_volume_heatmap` | Weekly Volume Heatmap |
| `tv_tcwijygr_sigma_spike_filtered_binned_opr_adam_h_grimes` | Sigma Spike Filtered Binned OPR ( Adam H. Grimes ) |
| `tv_tdtl9jea_how_to_use_the_new_fixed_range_volume_profile_drawing_tool` | How to use the new Fixed Range Volume Profile drawing tool |
| `tv_tedvnpgs_spread_by` | Spread by |
| `tv_tjzklojn_wyckoff_theultimator5` | Wyckoff [theUltimator5] |
| `tv_tk7fhng9_adaptive_trend_finder_log` | Adaptive Trend Finder (log) |
| `tv_tkzp5uj0_hancock_rsi_volume` | Hancock - RSI Volume |
| `tv_tmlc5wma_adaptive_market_profile_auto_detect_dynamic_activity_zones` | Adaptive Market Profile – Auto Detect & Dynamic Activity Zones |
| `tv_tmqir1jp_rsi_cyclic_smoothed_v2` | RSI cyclic smoothed v2 |
| `tv_tng177sv_realtime_5d_profile_lucf` | Realtime 5D Profile [LucF] |
| `tv_tnq7fvvw_trend_target_ribbon_boswaves` | Trend Target Ribbon [BOSWaves] |
| `tv_toatqabg_diluted_earnings_per_share_signal_astrideunicorn` | Diluted Earnings Per Share Signal [AstrideUnicorn] |
| `tv_tpseizhp_volume_x_ray_lucf` | Volume X-ray [LucF] |
| `tv_tstsp9sk_peak_trading_activity_graphs_luxalgo` | Peak Trading Activity Graphs [LuxAlgo] |
| `tv_tt0t369u_volatility_stop_mtf` | Volatility Stop MTF |
| `tv_tt7060bw_modern_portfolio_theory` | Modern Portfolio Theory |
| `tv_tv3rcaj9_market_sessions_and_volume_profile_by_leviathan` | Market sessions and Volume profile - By Leviathan |
| `tv_u0r2gpti_fourier_extrapolator_of_price_w_projection_forecast_loxx` | Fourier Extrapolator of Price w/ Projection Forecast [Loxx] |
| `tv_u1l7ixmp_rolling_candle_profile_with_buy_sell_signals_zeiierman` | Rolling Candle Profile with Buy/Sell Signals (Zeiierman) |
| `tv_u64lz5n3_mesa_stochastic_multi_length` | MESA Stochastic Multi Length |
| `tv_u8imfw8n_redk_portfolio_tracker_v2_few_enhancements_and_display_options` | RedK_Portfolio Tracker v2: few enhancements and display options |
| `tv_ucux0rjl_tops_bottoms_time_of_day_report` | Tops & Bottoms - Time of Day Report |
| `tv_udti2iuw_central_bank_liquidity_gap_indicator` | Central Bank Liquidity Gap Indicator |
| `tv_uftt8roh_redk_portfolio_tracker_table_version` | RedK Portfolio Tracker [Table Version] |
| `tv_uive2izt_harmonic_patterns_based_trend_follower` | Harmonic Patterns Based Trend Follower |
| `tv_ujgvguvt_volatility_risk_premium` | Volatility Risk Premium |
| `tv_ujvs2xfg_monte_carlo_range_forecast_dw` | Monte Carlo Range Forecast [DW] |
| `tv_ukaod896_divergence_support_resistence` | Divergence-Support/Resistence |
| `tv_ukgkppqm_dynamic_volume_profile_oscillator_alphaalgos` | Dynamic Volume Profile Oscillator / AlphaAlgos |
| `tv_ulnivzea_smu_stdev_candles` | SMU STDEV Candles |
| `tv_ulvxjaub_zigzag_circles_strategy_test_1st_april_6th_june` | Zigzag Circles Strategy Test 1st April → 6th June |
| `tv_ulz8mjlu_rs_majors_volume_sum` | [RS]Majors Volume Sum |
| `tv_ulzjcb7h_volume_by_time_luxalgo` | Volume by Time [LuxAlgo] |
| `tv_unwex8n4_heatmap_volume_xdecow` | Heatmap Volume [xdecow] |
| `tv_utcrhzep_volume_profile_pivot_anchored_by_dgt` | Volume Profile, Pivot Anchored by DGT |
| `tv_uudeajsi_quadratic_regression` | Quadratic Regression |
| `tv_uvby6vlf_mad_gann_o_maticus` | [MAD] Gann o Maticus |
| `tv_uwufcff8_indicators_overlay` | Indicators Overlay |
| `tv_v8sbugsw_redk_trader_pressure_index_tpx_v1_0` | RedK Trader Pressure Index (TPX v1.0)  |
| `tv_vakdjwdk_head_shoulders_s_r_regular` | Head & Shoulders S/R Regular |
| `tv_vb8jw3i2_trend_following_mas_3d` | Trend Following MAs 3D |
| `tv_vdzfb2wa_quality_screen` | Quality Screen |
| `tv_vfzck3hx_tasc_2026_08_an_ag_selling_model` | TASC 2026.08 An Ag Selling Model |
| `tv_viwa6cr8_ma_sabres_luxalgo` | MA Sabres [LuxAlgo] |
| `tv_vnzbp63l_zigzag_trend_divergence_detector` | Zigzag Trend/Divergence Detector |
| `tv_vo99pov0_htf_candle_volume_thermometer_chartprime` | HTF Candle Volume Thermometer [ChartPrime] |
| `tv_vozihfu9_obv_traffic_lights` | OBV Traffic Lights |
| `tv_vraarpaa_tasc_2021_11_madh_moving_average_difference_hann` | TASC 2021.11 MADH Moving Average Difference, Hann |
| `tv_vrtl3vwf_machine_learning_rsi_ai_classification_ranking_zeiierman` | Machine Learning RSI / AI Classification & Ranking (Zeiierman) |
| `tv_vspwh0vn_options_max_pain_calculator_backquant` | Options Max Pain Calculator [BackQuant] |
| `tv_vt3jbshj_cointegration_heatmap_spread_table_edgeterminal` | Cointegration Heatmap & Spread Table [EdgeTerminal] |
| `tv_vuym89tw_grover_llorens_activator_strategy_analysis` | Grover Llorens Activator Strategy Analysis |
| `tv_vxui7vrm_market_structure_dashboard_flux_charts` | Market Structure Dashboard / Flux Charts |
| `tv_vy7sifia_candle_body_shapes` | Candle Body Shapes |
| `tv_vyu6a3gb_anchored_vwap_pinch_handoff_intervals_and_signals` | Anchored VWAP Pinch & Handoff, Intervals, and Signals |
| `tv_w5lbl0mv_john_ehlers_the_price_radio` | John Ehlers - The Price Radio |
| `tv_w5vmuuda_financial_growth` | Financial Growth |
| `tv_wba7j6tu_mean_deviation_index` | Mean Deviation Index |
| `tv_wbqdfanb_mboxalgos` | MBoxAlgos |
| `tv_wc3dyn1w_trend_range_detector_zeiierman` | Trend Range Detector (Zeiierman) |
| `tv_wdotecyq_pivot_and_price_discovery` | Pivot and Price Discovery |
| `tv_we9amcve_tasc_2026_04_a_synthetic_oscillator` | TASC 2026.04 A Synthetic Oscillator |
| `tv_whbzgfdu_machine_learning_lorentzian_classification` | Machine Learning: Lorentzian Classification |
| `tv_whfedbdv_chart_oscillator` | Chart Oscillator |
| `tv_wijmcwz7_financial_statement_indicator_by_zdmre` | Financial Statement Indicator by zdmre |
| `tv_wiwhv552_custom_pattern_detection` | Custom Pattern Detection |
| `tv_wixmhdwt_seasonality_tfo` | Seasonality [TFO] |
| `tv_wobqqsxf_black_scholes_option_pricing_model_w_greeks_loxx` | Black Scholes Option Pricing Model w/ Greeks [Loxx] |
| `tv_wp434cpg_btc_difficulty_adjustments` | BTC difficulty adjustments |
| `tv_wp7wwjll_supertrend_ai_clustering_luxalgo` | SuperTrend AI (Clustering) [LuxAlgo] |
| `tv_wpbrh5sq_simple_decesion_matrix_classification_algorithm_ss` | Simple Decesion Matrix Classification Algorithm [SS] |
| `tv_wtmg0nge_golden_pocket` | Golden Pocket |
| `tv_wvcqygsx_mtf_oscillator_framework_pinecoders` | MTF Oscillator Framework [PineCoders] |
| `tv_wyyxkhdn_correlation_cycle_correlationangle_market_state_john_ehlers` | Correlation Cycle, CorrelationAngle, Market State - John Ehlers |
| `tv_wz8b1fiw_auto_chart_patterns_trendoscope` | Auto Chart Patterns [Trendoscope®] |
| `tv_wzvigqk7_vama_volume_adjusted_moving_average_function` | VAMA Volume Adjusted Moving Average Function |
| `tv_x2llrvbe_higher_order_pivots` | Higher Order Pivots |
| `tv_x2y6hyok_bitcoin_bullish_percent_index` | Bitcoin Bullish Percent Index |
| `tv_x4xoo9ax_fibonacci_sequence_circles_bigbeluga` | Fibonacci Sequence Circles [BigBeluga] |
| `tv_x9qyvbyn_andean_oscillator` | Andean Oscillator |
| `tv_xascppnw_nick_rypock_trailing_reverse_nrtr_everget` | Nick Rypock Trailing Reverse (NRTR) [everget] |
| `tv_xdwgv3fx_ttrades_daily_bias_tfo` | TTrades Daily Bias [TFO] |
| `tv_xebjei3o_how_to_identify_valid_high_probability_price_action_structures` | How to identify valid, high probability price action structures |
| `tv_xfr7xhqz_cm_macd_custom_indicator_multiple_time_frame_v2` | CM MACD Custom Indicator - Multiple Time Frame - V2 |
| `tv_xfrmtqfi_using_psychology_large_price_moves_and_volume_to_spot_bottoms` | Using psychology, large price moves, and volume to spot bottoms |
| `tv_xgnuhodo_open_interest_chart_luxalgo` | Open Interest Chart [LuxAlgo] |
| `tv_xh8tldte_realtime_delta_volume_action_lucf` | Realtime Delta Volume Action [LucF] |
| `tv_xkbwnq2h_intrabar_run_count_indicator_tbiktag` | Intrabar Run Count Indicator [tbiktag] |
| `tv_xlv4mwjk_time_range_statistics` | Time Range Statistics |
| `tv_xmke97vn_developing_market_profile_tpo_honestcowboy` | Developing Market Profile / TPO [Honestcowboy] |
| `tv_xp9odtfm_volume_profile_volume_delta_oi_delta_kioseff_trading` | Volume Profile Volume Delta OI Delta [Kioseff Trading] |
| `tv_xux5vvn0_earnings_splits_dividends` | Earnings, Splits, Dividends |
| `tv_xyaiqwd8_auto_trendline_indicator_based_on_fractals` | Auto Trendline Indicator (based on fractals) |
| `tv_xzfb6isb_smart_trader_concentric_candles_aristotelian_cycloids` | Smart Trader, Concentric Candles & Aristotelian Cycloids |
| `tv_y1wyhpg2_the_best_long_term_indicator` | The best long-term indicator |
| `tv_y1x3vuyd_bollinger_band_and_t_line_timing` | Bollinger Band and T-Line Timing |
| `tv_y3pnzg2q_correlation_heatmap` | Correlation Heatmap |
| `tv_y5n6dljm_spearman_rank_correlation_coefficient` | Spearman Rank Correlation Coefficient |
| `tv_y6jyas39_market_sessions_and_tpo_forecast` | Market Sessions and TPO (+Forecast) |
| `tv_y6x4nem5_treasury_yields_heatmap_by_muqwishi` | Treasury Yields Heatmap [By MUQWISHI] |
| `tv_ya0kopdo_markov_chain_3d_fractalyst` | Markov Chain [3D] / Fractalyst |
| `tv_yftex5f0_correlation_matrix_heatmap` | Correlation Matrix Heatmap |
| `tv_yg0rpnzo_efficient_work_lucf` | Efficient Work [LucF] |
| `tv_ygno2g1v_tick_chart` | Tick Chart |
| `tv_yhpgau7a_carrier_volatility_pumori` | Carrier Volatility [Pumori] |
| `tv_yjxpjg0y_multi_asset_performance_spaghetti_by_leviathan` | Multi-Asset Performance [Spaghetti] - By Leviathan |
| `tv_ykinbu20_true_close_institutional_trading_sessions_zeiierman` | True Close – Institutional Trading Sessions (Zeiierman) |
| `tv_ykvjs2dw_htf_floating_candles_w_volume_footprint_theultimator5` | HTF Floating Candles w/ Volume Footprint [theUltimator5] |
| `tv_yln2bnaa_auto_fibonacci_and_gann_fan_retracements_combo` | Auto Fibonacci and Gann Fan/Retracements Combo |
| `tv_ypaxpury_interactive_motive_wave_checklist` | Interactive Motive Wave Checklist |
| `tv_ypz7tsjn_ichimoku_oscillator` | Ichimoku Oscillator |
| `tv_yqkwbg4m_intrabar_analyzer_kioseff_trading` | Intrabar Analyzer [Kioseff Trading] |
| `tv_yr3kt0ui_time_of_day_session_performance_stats_quantalgo` | Time-of-Day/Session Performance Stats [QuantAlgo] |
| `tv_yrdyq40y_function_simple_markov_chain_monte_carlo_simulation_mcmc` | Function - simple* Markov Chain Monte Carlo Simulation (MCMC) |
| `tv_yrff3z4j_financials_comparing_companies` | Financials - Comparing Companies |
| `tv_ysrwimbi_ridethepig_recession_strategy` | ridethepig / Recession Strategy |
| `tv_yyrxrhi9_atr_rope` | ATR Rope |
| `tv_z6rxdyt1_a_simple_novice_friendly_system` | A simple novice friendly system |
| `tv_zartjpet_simple_investing_strategy_affordable_for_all` | Simple Investing Strategy, Affordable for all! |
| `tv_zcv9cpue_managing_your_trades_using_time_of_day` | Managing Your trades using TIME of DAY |
| `tv_zdqq3mfb_minervini_qualifier` | Minervini Qualifier |
| `tv_zewvhavq_divergence_screener_trendoscope` | Divergence Screener [Trendoscope®] |
| `tv_zhfjqywg_cvd_profiles_tradingiq` | CVD Profiles [TradingIQ] |
| `tv_zkbuifk7_delta_volume_channels_lucf` | Delta Volume Channels [LucF] |
| `tv_zkf0qji2_signs_of_the_times_lucf` | Signs of the Times [LucF] |
| `tv_zkrpp4fi_us_presidential_elections_and_investment_strategies_explained` | US Presidential Elections and Investment Strategies Explained |
| `tv_zlyn2rht_zigzag_cloud` | Zigzag Cloud |
| `tv_zmdzlgaj_volume_speed_by_muqwishi` | Volume Speed [By MUQWISHI] |
| `tv_zmxb93wd_volume_footprint_voids_bigbeluga` | Volume Footprint Voids [BigBeluga] |
| `tv_zn9dhlps_volume_delta_compare_ticks_ltf_data` | Volume Delta Compare [Ticks ~ LTF data] |
| `tv_zoamxj65_moving_regression_prediction_bands` | Moving Regression Prediction Bands |
| `tv_zonrvq00_oil_strategy_weekly` | Oil Strategy Weekly |
| `tv_zr7ztqm1_renko_rsi` | Renko RSI |
| `tv_zrc6twt4_z_score_probability_indicator` | Z-Score Probability Indicator |
| `tv_zsdlpebt_trend_type_indicator_by_bobrivera990` | Trend Type Indicator by BobRivera990 |
| `tv_zsgx4esy_smart_trader_episode_06_isotropic_trend_lines` | Smart Trader, Episode 06, Isotropic Trend Lines |
| `tv_zsmaleyi_rsi_impact_heat_map_trendoscope` | RSI Impact Heat Map [Trendoscope] |
| `tv_zsnllxmm_dual_phase_trend_regime_oscillator_zeiierman` | Dual-Phase Trend Regime Oscillator (Zeiierman) |
| `tv_zus134uh_heat_map_seasons` | Heat Map Seasons |
| `tv_zvct18wt_mawreez_rsi_divergence_detector` | Mawreez' RSI Divergence Detector |
| `tv_zx1z1z2r_liquidity_heatmap_ltf_luxalgo` | Liquidity Heatmap LTF [LuxAlgo] |
| `tv_zxcxrnij_redk_multi_modal_trailingstop_redk_mmtstop` | RedK Multi-Modal TrailingStop (RedK MMTStop) |
| `tv_zxtnurdh_cup_handle` | Cup & Handle |
| `tv_zxxjiyij_adaptive_volume_delta_map` | Adaptive Volume Delta Map |

| `tv_method_short_strangle` | Short strangle option premium |

## Verification

Run `python3 scripts/check_tradingview_cards.py` for committed coverage integrity. Add `--source-root /absolute/path/to/tradingview` to verify all original source hashes and description excerpts against the local dumps. The raw sources are deliberately not committed.

The source audit does not certify author profitability claims or complete hidden formulas. Any missing formula, parameter, dataset or execution rule remains explicit on its specification card.
