
### SHORT horizon — singles (25 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `ma_crossover_12_48` | trend | **0.488** | -2.490 | 3.4% | -59.7% | -11.8% | 29 |
| 2 | `zscore_20_-2` | mean-reversion | **0.441** | -1.285 | 2.8% | -37.3% | -19.0% | 48 |
| 3 | `ou_reversion_250_2.5` | mean-reversion | **0.089** | -0.040 | 0.0% | -3.5% | -9.4% | 33 |
| 4 | `bb_reversion_20_2` | mean-reversion | **0.086** | -1.274 | -0.9% | -37.3% | -18.0% | 52 |
| 5 | `hurst_switch_250_0.55_0.45` | regime-filter | **0.030** | -3.097 | -0.1% | -40.2% | -6.6% | 29 |
| 6 | `sma_regime_168` | sma-gated | **-0.519** | -2.101 | -7.0% | -51.4% | -15.2% | 49 |
| 7 | `voltarget_168_24_0.8` | sma-gated | **-0.519** | -2.105 | -7.0% | -51.5% | -15.2% | 49 |
| 8 | `garch_voltarget_0.94_0.8` | sma-gated | **-0.519** | -2.105 | -7.0% | -51.5% | -15.2% | 49 |
| 9 | `rsi_7_30_55` | oscillator-reversion | **-0.527** | -1.620 | -7.4% | -45.9% | -23.9% | 49 |
| 10 | `bb_breakout_20_2` | breakout | **-0.684** | -0.901 | -6.9% | -23.6% | -15.9% | 50 |
| 11 | `stoch_14_3` | oscillator-reversion | **-0.719** | -0.311 | -7.9% | -14.6% | -13.9% | 37 |
| 12 | `ichimoku_9_26_52` | trend | **-0.889** | -1.557 | -10.1% | -41.8% | -17.4% | 67 |
| 13 | `ma_ribbon_5x6` | trend | **-1.030** | -2.019 | -9.6% | -43.6% | -18.0% | 801 |
| 14 | `vol_regime_24_0.5` | regime-filter | **-1.360** | -1.386 | -10.8% | -26.9% | -15.5% | 58 |
| 15 | `grid_48_4_0.03` | mean-reversion | **-1.510** | -1.593 | -8.8% | -27.1% | -13.3% | 694 |
| 16 | `vwap_reversion_20_0.01` | mean-reversion | **-1.516** | -1.777 | -17.2% | -50.5% | -23.3% | 55 |
| 17 | `atr_sized_7_0.01` | sma-gated | **-1.665** | -2.039 | -10.4% | -27.2% | -13.2% | 434 |
| 18 | `ts_momentum_24` | momentum | **-1.677** | -2.272 | -18.1% | -57.8% | -23.3% | 126 |
| 19 | `keltner_12_7_2` | breakout | **-1.954** | 0.448 | -7.9% | 5.3% | -9.0% | 13 |
| 20 | `breakout_12_6` | breakout | **-2.272** | -0.936 | -22.2% | -29.6% | -27.1% | 59 |
| 21 | `obv_trend_24` | volume-flow | **-2.331** | -0.499 | -25.8% | -23.3% | -29.4% | 153 |
| 22 | `dual_momentum_24_2` | momentum | **-2.739** | -4.061 | -27.3% | -76.5% | -31.6% | 130 |
| 23 | `adx_trend_7_25` | regime-filter | **-3.600** | -1.991 | -28.4% | -45.7% | -29.7% | 121 |
| 24 | `macd_6_13_5` | trend | **-4.621** | -2.016 | -42.4% | -56.4% | -46.0% | 205 |

_1 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`._

### SHORT horizon — pairs (246 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(sma_regime+bb_reversion)` | sma-gated+mean-reversion | **2.572** | -1.691 | 9.0% | -15.6% | -3.5% | 18 |
| 2 | `all(vol_regime+bb_reversion)` | regime-filter+mean-reversion | **2.489** | -0.702 | 8.4% | -4.7% | -3.8% | 18 |
| 3 | `all(sma_regime+ou_reversion)` | sma-gated+mean-reversion | **1.786** | -0.882 | 5.0% | -6.2% | -3.4% | 14 |
| 4 | `all(vol_regime+ou_reversion)` | regime-filter+mean-reversion | **1.539** | -0.139 | 4.2% | -0.9% | -3.9% | 14 |
| 5 | `any(ma_crossover+bb_breakout)` | trend+breakout | **1.240** | -1.283 | 12.3% | -42.3% | -13.1% | 33 |
| 6 | `all(vol_regime+vwap_reversion)` | regime-filter+mean-reversion | **1.222** | -1.443 | 4.6% | -13.0% | -6.3% | 25 |
| 7 | `any(hurst_switch+ou_reversion)` | regime-filter+mean-reversion | **0.917** | -1.612 | 5.2% | -35.6% | -9.7% | 45 |
| 8 | `all(hurst_switch+stochastic)` | regime-filter+oscillator-reversion | **0.803** | -0.437 | 1.8% | -3.2% | -3.9% | 17 |
| 9 | `all(stochastic+ou_reversion)` | oscillator-reversion+mean-reversion | **0.792** | -0.159 | 3.0% | -4.5% | -7.5% | 23 |
| 10 | `all(stochastic+bb_reversion)` | oscillator-reversion+mean-reversion | **0.618** | -0.383 | 4.1% | -14.1% | -10.7% | 36 |
| 11 | `all(ma_ribbon+bb_reversion)` | trend+mean-reversion | **0.587** | -1.821 | 1.1% | -10.8% | -1.9% | 170 |
| 12 | `any(ma_crossover+hurst_switch)` | trend+regime-filter | **0.585** | -2.750 | 4.6% | -63.5% | -17.0% | 47 |
| 13 | `all(ma_crossover+ou_reversion)` | trend+mean-reversion | **0.546** | 0.086 | 1.4% | 0.3% | -2.9% | 17 |
| 14 | `any(ma_crossover+stochastic)` | trend+oscillator-reversion | **0.513** | -1.670 | 4.0% | -57.9% | -17.4% | 45 |
| 15 | `any(ma_crossover+keltner)` | trend+breakout | **0.441** | -1.950 | 2.9% | -52.6% | -12.5% | 29 |

_24 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(macd+hurst_switch)`, `all(ichimoku+hurst_switch)`, `all(dual_momentum+hurst_switch)`, `all(sma_regime+hurst_switch)`, `all(adx_trend+bb_reversion)`, `all(adx_trend+vwap_reversion)`, `all(adx_trend+ou_reversion)`, `all(hurst_switch+breakout)`, `all(hurst_switch+bb_breakout)`, `all(hurst_switch+keltner)`, `all(hurst_switch+obv_trend)`, `all(vol_regime+keltner)`…._

### SHORT horizon — triples (14 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(ma_crossover+bb_reversion+sma_regime)` | trend+mean-reversion+sma-gated | **1.435** | 0.805 | 2.4% | 3.8% | -1.4% | 11 |
| 2 | `vote(ma_crossover+bb_reversion+hurst_switch)` | trend+mean-reversion+regime-filter | **0.433** | -3.291 | 1.9% | -44.8% | -7.9% | 1037 |
| 3 | `vote(ma_crossover+ou_reversion+hurst_switch)` | trend+mean-reversion+regime-filter | **0.187** | -2.965 | 0.5% | -37.2% | -8.6% | 867 |
| 4 | `vote(ma_crossover+hurst_switch+sma_regime)` | trend+regime-filter+sma-gated | **0.043** | -2.619 | -0.4% | -42.1% | -10.2% | 838 |
| 5 | `vote(ma_crossover+bb_reversion+sma_regime)` | trend+mean-reversion+sma-gated | **-0.022** | -2.793 | -1.1% | -49.0% | -13.4% | 1110 |
| 6 | `vote(ma_crossover+ou_reversion+sma_regime)` | trend+mean-reversion+sma-gated | **-0.038** | -2.563 | -1.0% | -42.9% | -10.5% | 952 |
| 7 | `vote(bb_reversion+hurst_switch+sma_regime)` | mean-reversion+regime-filter+sma-gated | **-0.101** | -2.965 | -1.1% | -41.6% | -9.1% | 967 |
| 8 | `vote(ou_reversion+hurst_switch+sma_regime)` | mean-reversion+regime-filter+sma-gated | **-0.238** | -2.640 | -1.3% | -34.1% | -8.2% | 809 |
| 9 | `all(ma_crossover+bb_reversion+hurst_switch)` | trend+mean-reversion+regime-filter | **-1.178** | -0.361 | -1.2% | -2.5% | -2.4% | 11 |

_5 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(ma_crossover+ou_reversion+hurst_switch)`, `all(ma_crossover+ou_reversion+sma_regime)`, `all(ma_crossover+hurst_switch+sma_regime)`, `all(ou_reversion+hurst_switch+sma_regime)`, `all(bb_reversion+hurst_switch+sma_regime)`._

### MEDIUM horizon — singles (25 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `zscore_20_-2` | mean-reversion | **0.699** | -0.170 | 41.3% | -64.8% | -52.0% | 10 |
| 2 | `hurst_switch_250_0.55_0.45` | regime-filter | **0.564** | 0.669 | 15.6% | 64.0% | -16.3% | 10 |
| 3 | `bb_reversion_20_2` | mean-reversion | **0.193** | -0.152 | -4.8% | -63.9% | -52.0% | 10 |
| 4 | `stoch_14_3` | oscillator-reversion | **0.024** | 0.153 | -18.1% | -20.2% | -44.4% | 11 |
| 5 | `vol_regime_20_0.5` | regime-filter | **-0.377** | -0.495 | -21.2% | -58.5% | -35.3% | 15 |
| 6 | `atr_sized_14_0.01` | sma-gated | **-0.454** | 0.377 | -2.6% | 5.8% | -3.9% | 93 |
| 7 | `sma_regime_100` | sma-gated | **-0.516** | 0.443 | -35.8% | 34.8% | -43.1% | 13 |
| 8 | `ichimoku_9_26_52` | trend | **-0.531** | 0.967 | -33.3% | 336.3% | -36.7% | 11 |
| 9 | `vwap_reversion_20_0.02` | mean-reversion | **-0.532** | 0.032 | -53.9% | -58.6% | -61.8% | 23 |
| 10 | `garch_voltarget_0.94_0.6` | sma-gated | **-0.551** | 0.321 | -30.8% | 18.9% | -37.2% | 50 |
| 11 | `voltarget_100_20_0.6` | sma-gated | **-0.569** | 0.307 | -31.1% | 15.7% | -34.8% | 73 |
| 12 | `grid_50_4_0.05` | mean-reversion | **-0.590** | -0.119 | -38.9% | -36.9% | -48.5% | 100 |
| 13 | `macd_12_26_9` | trend | **-0.720** | 1.347 | -52.8% | 1356.5% | -59.2% | 21 |
| 14 | `bb_breakout_20_2` | breakout | **-0.841** | 1.837 | -34.9% | 2843.6% | -40.9% | 11 |
| 15 | `ts_momentum_60` | momentum | **-0.874** | 0.959 | -51.1% | 392.8% | -51.3% | 25 |
| 16 | `ma_ribbon_5x10` | trend | **-1.242** | 1.119 | -54.0% | 452.0% | -55.2% | 160 |
| 17 | `dual_momentum_12_1` | momentum | **-1.303** | 1.176 | -65.3% | 776.5% | -71.8% | 37 |
| 18 | `obv_trend_20` | volume-flow | **-1.383** | 1.494 | -69.2% | 1932.1% | -69.2% | 37 |

_7 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`, `ma_crossover_20_50`, `breakout_20_10`, `keltner_20_14_2`, `rsi_14_30_50`, `adx_trend_14_25`, `ou_reversion_250_2.5`._

### MEDIUM horizon — pairs (278 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(hurst_switch+bb_reversion)` | regime-filter+mean-reversion | **0.564** | 0.363 | 15.6% | 16.7% | -16.3% | 10 |
| 2 | `all(hurst_switch+vwap_reversion)` | regime-filter+mean-reversion | **0.564** | -0.000 | 15.6% | -3.8% | -16.3% | 10 |
| 3 | `all(macd+stochastic)` | trend+oscillator-reversion | **0.391** | 0.223 | 9.9% | 8.0% | -12.4% | 10 |
| 4 | `any(hurst_switch+breakout)` | regime-filter+breakout | **0.304** | 0.777 | 6.9% | 185.0% | -31.1% | 17 |
| 5 | `any(hurst_switch+ou_reversion)` | regime-filter+mean-reversion | **0.241** | 1.018 | 4.4% | 177.2% | -27.0% | 11 |
| 6 | `all(ts_momentum+stochastic)` | momentum+oscillator-reversion | **0.240** | -0.275 | 4.5% | -22.0% | -18.0% | 10 |
| 7 | `any(hurst_switch+bb_reversion)` | regime-filter+mean-reversion | **0.193** | -0.047 | -4.8% | -52.9% | -52.0% | 10 |
| 8 | `any(breakout+bb_reversion)` | breakout+mean-reversion | **0.174** | 0.875 | -11.8% | 291.5% | -61.8% | 16 |
| 9 | `all(macd+vol_regime)` | trend+regime-filter | **0.161** | 0.176 | 1.9% | 3.7% | -21.3% | 11 |
| 10 | `any(hurst_switch+stochastic)` | regime-filter+oscillator-reversion | **0.103** | 0.541 | -13.5% | 70.1% | -44.5% | 15 |
| 11 | `all(ts_momentum+breakout)` | momentum+breakout | **0.100** | 1.000 | -2.2% | 361.4% | -31.0% | 10 |
| 12 | `any(breakout+rsi)` | breakout+oscillator-reversion | **0.081** | 1.139 | -13.8% | 768.0% | -57.9% | 11 |
| 13 | `any(breakout+ou_reversion)` | breakout+mean-reversion | **0.074** | 0.970 | -8.8% | 340.8% | -40.4% | 12 |
| 14 | `any(vol_regime+breakout)` | regime-filter+breakout | **0.024** | 0.547 | -9.9% | 73.7% | -35.3% | 15 |
| 15 | `all(vol_regime+stochastic)` | regime-filter+oscillator-reversion | **-0.009** | -0.070 | -2.7% | -4.9% | -19.9% | 10 |

_99 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(ma_crossover+sma_regime)`, `all(ma_crossover+adx_trend)`, `any(ma_crossover+adx_trend)`, `all(ma_crossover+hurst_switch)`, `all(ma_crossover+breakout)`, `any(ma_crossover+breakout)`, `all(ma_crossover+bb_breakout)`, `any(ma_crossover+bb_breakout)`, `all(ma_crossover+keltner)`, `any(ma_crossover+keltner)`, `all(ma_crossover+rsi)`, `all(ma_crossover+stochastic)`…._

### MEDIUM horizon — triples (14 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `vote(hurst_switch+bb_reversion+stochastic)` | regime-filter+mean-reversion+oscillator-reversion | **0.169** | 0.127 | 0.2% | -4.8% | -31.3% | 116 |
| 2 | `all(stochastic+vol_regime+sma_regime)` | oscillator-reversion+regime-filter+sma-gated | **-0.009** | -0.070 | -2.7% | -4.9% | -19.9% | 10 |
| 3 | `vote(bb_reversion+stochastic+vol_regime)` | mean-reversion+oscillator-reversion+regime-filter | **-0.090** | -0.252 | -13.3% | -41.1% | -35.0% | 159 |
| 4 | `vote(hurst_switch+bb_reversion+sma_regime)` | regime-filter+mean-reversion+sma-gated | **-0.104** | 0.225 | -8.5% | 8.2% | -24.5% | 165 |
| 5 | `vote(hurst_switch+stochastic+sma_regime)` | regime-filter+oscillator-reversion+sma-gated | **-0.158** | 0.574 | -10.8% | 56.3% | -22.9% | 176 |
| 6 | `vote(bb_reversion+stochastic+sma_regime)` | mean-reversion+oscillator-reversion+sma-gated | **-0.218** | 0.118 | -20.1% | -12.8% | -37.7% | 184 |
| 7 | `vote(stochastic+vol_regime+sma_regime)` | oscillator-reversion+regime-filter+sma-gated | **-0.290** | 0.133 | -16.5% | -3.3% | -27.9% | 161 |
| 8 | `vote(bb_reversion+vol_regime+sma_regime)` | mean-reversion+regime-filter+sma-gated | **-0.472** | -0.107 | -22.8% | -28.3% | -29.1% | 155 |

_6 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(hurst_switch+bb_reversion+stochastic)`, `all(hurst_switch+bb_reversion+sma_regime)`, `all(hurst_switch+stochastic+sma_regime)`, `all(bb_reversion+stochastic+vol_regime)`, `all(bb_reversion+stochastic+sma_regime)`, `all(bb_reversion+vol_regime+sma_regime)`._

### LONG horizon — singles (25 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `dual_momentum_24_1` | momentum | **-0.119** | 1.245 | -19.7% | 988.7% | -40.9% | 26 |
| 2 | `obv_trend_60` | volume-flow | **-0.153** | 1.271 | -24.0% | 982.7% | -43.7% | 18 |
| 3 | `grid_120_4_0.1` | mean-reversion | **-0.296** | 0.001 | -26.5% | -23.1% | -39.1% | 143 |
| 4 | `voltarget_200_60_0.6` | sma-gated | **-0.395** | 0.975 | -23.6% | 219.9% | -27.9% | 67 |
| 5 | `garch_voltarget_0.97_0.6` | sma-gated | **-0.448** | 0.919 | -25.4% | 185.3% | -27.9% | 44 |
| 6 | `atr_sized_30_0.01` | sma-gated | **-0.464** | 0.983 | -2.5% | 17.2% | -3.5% | 66 |
| 7 | `ma_ribbon_5x20` | trend | **-0.806** | 0.668 | -40.3% | 114.7% | -45.4% | 158 |
| 8 | `ts_momentum_200` | momentum | **-1.976** | 1.098 | -77.2% | 506.2% | -77.7% | 15 |

_17 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`, `ma_crossover_50_200`, `macd_26_52_18`, `sma_regime_200`, `breakout_60_30`, `bb_breakout_60_2`, `keltner_50_30_2`, `rsi_30_35_55`, `stoch_40_5`, `bb_reversion_60_2`, `zscore_60_-2`, `vwap_reversion_60_0.05`…._

### LONG horizon — pairs (276 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(dual_momentum+stochastic)` | momentum+oscillator-reversion | **1.169** | 0.242 | 23.8% | 11.2% | -11.7% | 10 |
| 2 | `all(dual_momentum+bb_reversion)` | momentum+mean-reversion | **0.784** | -0.858 | 18.3% | -63.9% | -13.5% | 11 |
| 3 | `all(ma_ribbon+ou_reversion)` | trend+mean-reversion | **0.719** | 0.084 | 16.3% | 1.2% | -10.4% | 20 |
| 4 | `all(dual_momentum+vwap_reversion)` | momentum+mean-reversion | **0.668** | -0.737 | 18.1% | -65.1% | -14.7% | 15 |
| 5 | `any(macd+hurst_switch)` | trend+regime-filter | **0.338** | 0.953 | 7.0% | 358.3% | -37.2% | 12 |
| 6 | `any(macd+ou_reversion)` | trend+mean-reversion | **0.241** | 1.014 | -2.6% | 437.2% | -40.3% | 11 |
| 7 | `any(rsi+obv_trend)` | oscillator-reversion+volume-flow | **0.226** | 1.288 | -8.8% | 1392.3% | -50.5% | 15 |
| 8 | `all(vwap_reversion+obv_trend)` | mean-reversion+volume-flow | **0.186** | 0.359 | 2.7% | 20.7% | -26.3% | 12 |
| 9 | `any(dual_momentum+rsi)` | momentum+oscillator-reversion | **0.141** | 1.427 | -8.8% | 2291.6% | -40.8% | 20 |
| 10 | `any(macd+obv_trend)` | trend+volume-flow | **0.136** | 0.805 | -10.4% | 215.4% | -41.9% | 11 |
| 11 | `all(ma_ribbon+bb_reversion)` | trend+mean-reversion | **0.133** | -0.020 | 1.4% | -3.7% | -11.8% | 34 |
| 12 | `all(ma_ribbon+rsi)` | trend+oscillator-reversion | **0.096** | -0.340 | 0.6% | -14.6% | -4.7% | 31 |
| 13 | `any(ichimoku+bb_reversion)` | trend+mean-reversion | **0.059** | 0.276 | -23.9% | -30.6% | -61.4% | 10 |
| 14 | `any(hurst_switch+obv_trend)` | regime-filter+volume-flow | **0.031** | 1.131 | -14.3% | 588.0% | -37.2% | 20 |
| 15 | `any(bb_reversion+obv_trend)` | mean-reversion+volume-flow | **0.030** | 0.930 | -28.9% | 368.6% | -66.8% | 17 |

_191 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(ma_crossover+ts_momentum)`, `all(ma_crossover+dual_momentum)`, `all(ma_crossover+sma_regime)`, `any(ma_crossover+sma_regime)`, `all(ma_crossover+adx_trend)`, `any(ma_crossover+adx_trend)`, `all(ma_crossover+hurst_switch)`, `any(ma_crossover+hurst_switch)`, `all(ma_crossover+vol_regime)`, `any(ma_crossover+vol_regime)`, `all(ma_crossover+breakout)`, `any(ma_crossover+breakout)`…._

### LONG horizon — triples (4 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(dual_momentum+obv_trend+ma_ribbon)` | momentum+volume-flow+trend | **-0.282** | 1.015 | -13.8% | 229.8% | -20.0% | 66 |
| 2 | `all(obv_trend+ma_ribbon+ts_momentum)` | volume-flow+trend+momentum | **-0.580** | 1.246 | -23.0% | 307.9% | -24.6% | 24 |
| 3 | `vote(dual_momentum+obv_trend+ma_ribbon)` | momentum+volume-flow+trend | **-0.799** | 0.855 | -41.2% | 213.2% | -48.0% | 134 |
| 4 | `vote(obv_trend+ma_ribbon+ts_momentum)` | volume-flow+trend+momentum | **-1.342** | 0.822 | -60.0% | 187.6% | -60.3% | 169 |
