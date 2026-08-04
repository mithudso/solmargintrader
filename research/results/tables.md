
### SHORT horizon — singles (16 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `ma_crossover_12_48` | trend | **0.488** | -2.490 | 3.4% | -59.7% | -11.8% | 29 |
| 2 | `zscore_20_-2` | mean-reversion | **0.441** | -1.285 | 2.8% | -37.3% | -19.0% | 48 |
| 3 | `bb_reversion_20_2` | mean-reversion | **0.086** | -1.274 | -0.9% | -37.3% | -18.0% | 52 |
| 4 | `sma_regime_168` | regime-filter | **-0.519** | -2.101 | -7.0% | -51.4% | -15.2% | 49 |
| 5 | `voltarget_168_24_0.8` | risk-overlay | **-0.519** | -2.105 | -7.0% | -51.5% | -15.2% | 49 |
| 6 | `rsi_7_30_55` | oscillator-reversion | **-0.527** | -1.620 | -7.4% | -45.9% | -23.9% | 49 |
| 7 | `bb_breakout_20_2` | breakout | **-0.684** | -0.901 | -6.9% | -23.6% | -15.9% | 50 |
| 8 | `stoch_14_3` | oscillator-reversion | **-0.719** | -0.311 | -7.9% | -14.6% | -13.9% | 37 |
| 9 | `grid_48_4_0.03` | mean-reversion | **-1.510** | -1.593 | -8.8% | -27.1% | -13.3% | 694 |
| 10 | `vwap_reversion_20_0.01` | mean-reversion | **-1.516** | -1.777 | -17.2% | -50.5% | -23.3% | 55 |
| 11 | `ts_momentum_24` | momentum | **-1.677** | -2.272 | -18.1% | -57.8% | -23.3% | 126 |
| 12 | `keltner_12_7_2` | breakout | **-1.954** | 0.448 | -7.9% | 5.3% | -9.0% | 13 |
| 13 | `breakout_12_6` | breakout | **-2.272** | -0.936 | -22.2% | -29.6% | -27.1% | 59 |
| 14 | `obv_trend_24` | volume-flow | **-2.331** | -0.499 | -25.8% | -23.3% | -29.4% | 153 |
| 15 | `macd_6_13_5` | trend | **-4.621** | -2.016 | -42.4% | -56.4% | -46.0% | 205 |

_1 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`._

### SHORT horizon — pairs (140 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(sma_regime+bb_reversion)` | regime-filter+mean-reversion | **2.572** | -1.691 | 9.0% | -15.6% | -3.5% | 18 |
| 2 | `all(sma_regime+zscore)` | regime-filter+mean-reversion | **2.572** | -1.407 | 9.0% | -13.0% | -3.5% | 18 |
| 3 | `all(sma_regime+rsi)` | regime-filter+oscillator-reversion | **1.456** | -2.147 | 5.2% | -21.1% | -4.6% | 17 |
| 4 | `all(stochastic+zscore)` | oscillator-reversion+mean-reversion | **1.258** | -0.385 | 9.7% | -13.9% | -11.3% | 35 |
| 5 | `any(ma_crossover+bb_breakout)` | trend+breakout | **1.240** | -1.283 | 12.3% | -42.3% | -13.1% | 33 |
| 6 | `any(ma_crossover+zscore)` | trend+mean-reversion | **0.678** | -2.514 | 6.6% | -71.4% | -26.0% | 55 |
| 7 | `all(stochastic+bb_reversion)` | oscillator-reversion+mean-reversion | **0.618** | -0.383 | 4.1% | -14.1% | -10.7% | 36 |
| 8 | `any(ma_crossover+stochastic)` | trend+oscillator-reversion | **0.513** | -1.670 | 4.0% | -57.9% | -17.4% | 45 |
| 9 | `any(ma_crossover+keltner)` | trend+breakout | **0.441** | -1.950 | 2.9% | -52.6% | -12.5% | 29 |
| 10 | `any(ma_crossover+bb_reversion)` | trend+mean-reversion | **0.405** | -2.491 | 2.4% | -71.2% | -24.9% | 56 |
| 11 | `all(ts_momentum+bb_reversion)` | momentum+mean-reversion | **0.402** | -1.289 | 0.7% | -6.5% | -3.0% | 14 |
| 12 | `any(ma_crossover+rsi)` | trend+oscillator-reversion | **0.120** | -2.420 | -1.8% | -70.9% | -29.5% | 51 |
| 13 | `all(ma_crossover+bb_reversion)` | trend+mean-reversion | **0.103** | -1.055 | 0.2% | -10.8% | -3.1% | 24 |
| 14 | `any(ma_crossover+sma_regime)` | trend+regime-filter | **0.088** | -2.880 | -1.3% | -68.5% | -16.4% | 31 |
| 15 | `all(rsi+zscore)` | oscillator-reversion+mean-reversion | **0.063** | -1.521 | -1.1% | -40.9% | -21.3% | 44 |

_15 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(breakout+rsi)`, `all(breakout+stochastic)`, `all(breakout+bb_reversion)`, `all(breakout+zscore)`, `all(breakout+vwap_reversion)`, `all(bb_breakout+rsi)`, `all(bb_breakout+stochastic)`, `all(bb_breakout+bb_reversion)`, `all(bb_breakout+zscore)`, `all(bb_breakout+vwap_reversion)`, `all(keltner+rsi)`, `all(keltner+stochastic)`…._

### SHORT horizon — triples (32 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `all(zscore+sma_regime+rsi)` | mean-reversion+regime-filter+oscillator-reversion | **2.555** | -1.569 | 8.9% | -13.9% | -3.7% | 17 |
| 2 | `all(bb_reversion+sma_regime+rsi)` | mean-reversion+regime-filter+oscillator-reversion | **2.555** | -1.569 | 8.9% | -13.9% | -3.7% | 17 |
| 3 | `all(ma_crossover+zscore+sma_regime)` | trend+mean-reversion+regime-filter | **1.435** | 1.026 | 2.4% | 4.9% | -1.4% | 11 |
| 4 | `all(ma_crossover+bb_reversion+sma_regime)` | trend+mean-reversion+regime-filter | **1.435** | 0.805 | 2.4% | 3.8% | -1.4% | 11 |
| 5 | `vote(ma_crossover+sma_regime+bb_breakout)` | trend+regime-filter+breakout | **0.295** | -2.074 | 1.3% | -36.7% | -10.2% | 607 |
| 6 | `vote(ma_crossover+zscore+bb_breakout)` | trend+mean-reversion+breakout | **0.187** | -2.331 | 0.5% | -39.9% | -12.9% | 1098 |
| 7 | `vote(ma_crossover+zscore+sma_regime)` | trend+mean-reversion+regime-filter | **0.132** | -2.816 | 0.1% | -49.2% | -14.0% | 1100 |
| 8 | `all(ma_crossover+zscore+rsi)` | trend+mean-reversion+oscillator-reversion | **0.084** | -1.704 | 0.1% | -14.9% | -3.1% | 21 |
| 9 | `vote(ma_crossover+zscore+rsi)` | trend+mean-reversion+oscillator-reversion | **0.068** | -2.138 | -0.5% | -41.4% | -16.4% | 1013 |
| 10 | `vote(ma_crossover+bb_reversion+bb_breakout)` | trend+mean-reversion+breakout | **0.013** | -2.323 | -0.7% | -39.8% | -12.2% | 1109 |
| 11 | `vote(ma_crossover+bb_reversion+sma_regime)` | trend+mean-reversion+regime-filter | **-0.022** | -2.793 | -1.1% | -49.0% | -13.4% | 1110 |
| 12 | `vote(ma_crossover+bb_reversion+rsi)` | trend+mean-reversion+oscillator-reversion | **-0.072** | -2.110 | -1.5% | -41.2% | -15.8% | 1013 |
| 13 | `all(ma_crossover+bb_reversion+rsi)` | trend+mean-reversion+oscillator-reversion | **-0.116** | -1.704 | -0.5% | -14.9% | -3.1% | 23 |
| 14 | `vote(ma_crossover+sma_regime+rsi)` | trend+regime-filter+oscillator-reversion | **-0.155** | -2.835 | -2.1% | -50.2% | -14.8% | 1113 |
| 15 | `all(ma_crossover+sma_regime+rsi)` | trend+regime-filter+oscillator-reversion | **-0.233** | -0.190 | -0.6% | -1.5% | -3.2% | 11 |

_8 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(ma_crossover+zscore+bb_breakout)`, `all(ma_crossover+bb_reversion+bb_breakout)`, `all(ma_crossover+rsi+bb_breakout)`, `all(zscore+sma_regime+bb_breakout)`, `all(zscore+rsi+bb_breakout)`, `all(bb_reversion+sma_regime+bb_breakout)`, `all(bb_reversion+rsi+bb_breakout)`, `all(sma_regime+rsi+bb_breakout)`._

### MEDIUM horizon — singles (16 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `zscore_20_-2` | mean-reversion | **0.699** | -0.170 | 41.3% | -64.8% | -52.0% | 10 |
| 2 | `bb_reversion_20_2` | mean-reversion | **0.193** | -0.152 | -4.8% | -63.9% | -52.0% | 10 |
| 3 | `stoch_14_3` | oscillator-reversion | **0.024** | 0.153 | -18.1% | -20.2% | -44.4% | 11 |
| 4 | `sma_regime_100` | regime-filter | **-0.516** | 0.443 | -35.8% | 34.8% | -43.1% | 13 |
| 5 | `vwap_reversion_20_0.02` | mean-reversion | **-0.532** | 0.032 | -53.9% | -58.6% | -61.8% | 23 |
| 6 | `voltarget_100_20_0.6` | risk-overlay | **-0.569** | 0.307 | -31.1% | 15.7% | -34.8% | 73 |
| 7 | `grid_50_4_0.05` | mean-reversion | **-0.590** | -0.119 | -38.9% | -36.9% | -48.5% | 100 |
| 8 | `macd_12_26_9` | trend | **-0.720** | 1.347 | -52.8% | 1356.5% | -59.2% | 21 |
| 9 | `bb_breakout_20_2` | breakout | **-0.841** | 1.837 | -34.9% | 2843.6% | -40.9% | 11 |
| 10 | `ts_momentum_60` | momentum | **-0.874** | 0.959 | -51.1% | 392.8% | -51.3% | 25 |
| 11 | `obv_trend_20` | volume-flow | **-1.383** | 1.494 | -69.2% | 1932.1% | -69.2% | 37 |

_5 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`, `ma_crossover_20_50`, `breakout_20_10`, `keltner_20_14_2`, `rsi_14_30_50`._

### MEDIUM horizon — pairs (140 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `any(breakout+zscore)` | breakout+mean-reversion | **0.584** | 0.867 | 30.8% | 281.8% | -61.8% | 16 |
| 2 | `all(macd+stochastic)` | trend+oscillator-reversion | **0.391** | 0.223 | 9.9% | 8.0% | -12.4% | 10 |
| 3 | `any(keltner+zscore)` | breakout+mean-reversion | **0.305** | 0.776 | 3.9% | 190.7% | -55.3% | 16 |
| 4 | `all(ts_momentum+stochastic)` | momentum+oscillator-reversion | **0.240** | -0.275 | 4.5% | -22.0% | -18.0% | 10 |
| 5 | `any(bb_breakout+zscore)` | breakout+mean-reversion | **0.177** | 1.193 | -8.0% | 937.6% | -62.1% | 21 |
| 6 | `any(breakout+bb_reversion)` | breakout+mean-reversion | **0.174** | 0.875 | -11.8% | 291.5% | -61.8% | 16 |
| 7 | `all(ts_momentum+breakout)` | momentum+breakout | **0.100** | 1.000 | -2.2% | 361.4% | -31.0% | 10 |
| 8 | `any(breakout+rsi)` | breakout+oscillator-reversion | **0.081** | 1.139 | -13.8% | 768.0% | -57.9% | 11 |
| 9 | `any(stochastic+bb_reversion)` | oscillator-reversion+mean-reversion | **-0.011** | -0.029 | -23.4% | -56.7% | -52.3% | 13 |
| 10 | `any(stochastic+zscore)` | oscillator-reversion+mean-reversion | **-0.011** | -0.045 | -23.4% | -57.7% | -52.3% | 13 |
| 11 | `any(sma_regime+zscore)` | regime-filter+mean-reversion | **-0.015** | 0.212 | -25.8% | -48.7% | -62.2% | 17 |
| 12 | `all(macd+vwap_reversion)` | trend+mean-reversion | **-0.026** | 0.008 | -5.8% | -16.3% | -31.4% | 18 |
| 13 | `any(breakout+stochastic)` | breakout+oscillator-reversion | **-0.041** | 1.116 | -29.3% | 748.9% | -60.6% | 17 |
| 14 | `any(ma_crossover+zscore)` | trend+mean-reversion | **-0.055** | 0.814 | -30.2% | 220.3% | -70.6% | 13 |
| 15 | `all(stochastic+vwap_reversion)` | oscillator-reversion+mean-reversion | **-0.099** | 0.066 | -24.6% | -29.4% | -43.7% | 14 |

_52 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(ma_crossover+sma_regime)`, `all(ma_crossover+breakout)`, `any(ma_crossover+breakout)`, `all(ma_crossover+bb_breakout)`, `any(ma_crossover+bb_breakout)`, `all(ma_crossover+keltner)`, `any(ma_crossover+keltner)`, `all(ma_crossover+rsi)`, `all(ma_crossover+stochastic)`, `all(ma_crossover+bb_reversion)`, `all(ma_crossover+zscore)`, `all(macd+keltner)`…._

### MEDIUM horizon — triples (20 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `vote(zscore+stochastic+sma_regime)` | mean-reversion+oscillator-reversion+regime-filter | **-0.002** | 0.092 | -8.9% | -15.9% | -37.7% | 184 |
| 2 | `vote(zscore+stochastic+macd)` | mean-reversion+oscillator-reversion+trend | **-0.144** | 0.741 | -16.5% | 123.2% | -42.0% | 234 |
| 3 | `vote(bb_reversion+stochastic+sma_regime)` | mean-reversion+oscillator-reversion+regime-filter | **-0.218** | 0.118 | -20.1% | -12.8% | -37.7% | 184 |
| 4 | `vote(zscore+sma_regime+macd)` | mean-reversion+regime-filter+trend | **-0.238** | 0.494 | -17.7% | 55.3% | -35.9% | 238 |
| 5 | `vote(bb_reversion+stochastic+macd)` | mean-reversion+oscillator-reversion+trend | **-0.344** | 0.765 | -26.7% | 131.9% | -42.0% | 233 |
| 6 | `vote(bb_reversion+sma_regime+macd)` | mean-reversion+regime-filter+trend | **-0.477** | 0.516 | -27.4% | 61.1% | -35.9% | 246 |
| 7 | `vote(stochastic+sma_regime+macd)` | oscillator-reversion+regime-filter+trend | **-0.493** | 0.618 | -29.0% | 90.7% | -35.0% | 247 |
| 8 | `vote(stochastic+sma_regime+vwap_reversion)` | oscillator-reversion+regime-filter+mean-reversion | **-0.524** | 0.197 | -34.9% | -4.5% | -40.8% | 193 |
| 9 | `vote(stochastic+vwap_reversion+macd)` | oscillator-reversion+mean-reversion+trend | **-0.614** | 0.799 | -40.1% | 152.7% | -47.4% | 239 |
| 10 | `vote(sma_regime+vwap_reversion+macd)` | regime-filter+mean-reversion+trend | **-0.816** | 0.566 | -42.4% | 76.8% | -47.1% | 271 |

_10 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(zscore+stochastic+sma_regime)`, `all(zscore+stochastic+macd)`, `all(zscore+sma_regime+macd)`, `all(bb_reversion+stochastic+sma_regime)`, `all(bb_reversion+stochastic+macd)`, `all(bb_reversion+sma_regime+macd)`, `all(stochastic+sma_regime+vwap_reversion)`, `all(stochastic+sma_regime+macd)`, `all(stochastic+vwap_reversion+macd)`, `all(sma_regime+vwap_reversion+macd)`._

### LONG horizon — singles (16 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `obv_trend_60` | volume-flow | **-0.153** | 1.271 | -24.0% | 982.7% | -43.7% | 18 |
| 2 | `grid_120_4_0.1` | mean-reversion | **-0.296** | 0.001 | -26.5% | -23.1% | -39.1% | 143 |
| 3 | `voltarget_200_60_0.6` | risk-overlay | **-0.395** | 0.975 | -23.6% | 219.9% | -27.9% | 67 |
| 4 | `ts_momentum_200` | momentum | **-1.976** | 1.098 | -77.2% | 506.2% | -77.7% | 15 |

_12 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`, `ma_crossover_50_200`, `macd_26_52_18`, `sma_regime_200`, `breakout_60_30`, `bb_breakout_60_2`, `keltner_50_30_2`, `rsi_30_35_55`, `stoch_40_5`, `bb_reversion_60_2`, `zscore_60_-2`, `vwap_reversion_60_0.05`._

### LONG horizon — pairs (140 configurations evaluated)

| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | IS return | OOS maxDD | OOS trades |
|---|---|---|---|---|---|---|---|---|
| 1 | `any(rsi+obv_trend)` | oscillator-reversion+volume-flow | **0.226** | 1.288 | -8.8% | 1392.3% | -50.5% | 15 |
| 2 | `all(vwap_reversion+obv_trend)` | mean-reversion+volume-flow | **0.186** | 0.359 | 2.7% | 20.7% | -26.3% | 12 |
| 3 | `any(macd+obv_trend)` | trend+volume-flow | **0.136** | 0.805 | -10.4% | 215.4% | -41.9% | 11 |
| 4 | `any(bb_reversion+obv_trend)` | mean-reversion+volume-flow | **0.030** | 0.930 | -28.9% | 368.6% | -66.8% | 17 |
| 5 | `any(zscore+obv_trend)` | mean-reversion+volume-flow | **0.030** | 0.930 | -28.9% | 368.6% | -66.8% | 17 |
| 6 | `all(macd+obv_trend)` | trend+volume-flow | **-0.129** | 1.312 | -18.3% | 759.4% | -34.7% | 13 |
| 7 | `any(keltner+obv_trend)` | breakout+volume-flow | **-0.186** | 1.007 | -26.3% | 410.9% | -43.7% | 16 |
| 8 | `any(bb_breakout+obv_trend)` | breakout+volume-flow | **-0.233** | 1.413 | -28.4% | 1556.9% | -43.7% | 18 |
| 9 | `any(breakout+obv_trend)` | breakout+volume-flow | **-0.255** | 1.407 | -30.3% | 1599.1% | -43.7% | 17 |
| 10 | `any(keltner+bb_reversion)` | breakout+mean-reversion | **-0.338** | 0.387 | -48.3% | -4.5% | -66.3% | 11 |
| 11 | `any(keltner+zscore)` | breakout+mean-reversion | **-0.338** | 0.387 | -48.3% | -4.5% | -66.3% | 11 |
| 12 | `any(bb_breakout+bb_reversion)` | breakout+mean-reversion | **-0.349** | 0.750 | -47.3% | 165.4% | -67.7% | 10 |
| 13 | `any(bb_breakout+zscore)` | breakout+mean-reversion | **-0.349** | 0.750 | -47.3% | 165.4% | -67.7% | 10 |
| 14 | `any(sma_regime+obv_trend)` | regime-filter+volume-flow | **-0.408** | 0.886 | -40.5% | 292.7% | -48.7% | 13 |
| 15 | `any(stochastic+obv_trend)` | oscillator-reversion+volume-flow | **-0.513** | 0.939 | -61.4% | 397.8% | -72.7% | 15 |

_106 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(ma_crossover+ts_momentum)`, `all(ma_crossover+sma_regime)`, `any(ma_crossover+sma_regime)`, `all(ma_crossover+breakout)`, `any(ma_crossover+breakout)`, `all(ma_crossover+bb_breakout)`, `any(ma_crossover+bb_breakout)`, `all(ma_crossover+keltner)`, `any(ma_crossover+keltner)`, `all(ma_crossover+rsi)`, `any(ma_crossover+rsi)`, `all(ma_crossover+stochastic)`…._
