
### SHORT horizon — CPCV (8 blocks, k=2, 28 paths per configuration)
**PBO = 0.429** across 35 splits of 16 fully-evaluable configurations.

| # | strategy | family | median Sharpe | IQR spread | % paths positive | median path return | trades |
|---|---|---|---|---|---|---|---|
| 1 | `stoch_14_3` | oscillator-reversion | **-0.341** | 2.117 | 38% | -5.2% | 240 |
| 2 | `keltner_12_7_2` | breakout | **-0.961** | 2.477 | 29% | -4.9% | 88 |
| 3 | `zscore_20_-2` | mean-reversion | **-1.152** | 1.213 | 19% | -12.5% | 294 |
| 4 | `bb_reversion_20_2` | mean-reversion | **-1.316** | 1.396 | 14% | -15.4% | 308 |
| 5 | `buy_and_hold` | baseline | **-1.456** | 2.154 | 29% | -22.9% | 16 |
| 6 | `bb_breakout_20_2` | breakout | **-1.487** | 3.114 | 29% | -11.5% | 270 |
| 7 | `obv_trend_24` | volume-flow | **-1.580** | 1.668 | 24% | -18.0% | 852 |
| 8 | `rsi_7_30_55` | oscillator-reversion | **-1.723** | 1.052 | 14% | -19.8% | 328 |
| 9 | `breakout_12_6` | breakout | **-1.905** | 2.809 | 14% | -16.9% | 350 |
| 10 | `grid_48_4_0.03` | mean-reversion | **-2.022** | 0.731 | 0% | -12.4% | 4304 |
| 11 | `vwap_reversion_20_0.01` | mean-reversion | **-2.189** | 0.836 | 0% | -24.3% | 398 |
| 12 | `sma_regime_168` | regime-filter | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 13 | `voltarget_168_24_0.8` | risk-overlay | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 14 | `ma_crossover_12_48` | trend | **-2.385** | 3.326 | 10% | -23.5% | 204 |
| 15 | `ts_momentum_24` | momentum | **-2.564** | 2.018 | 0% | -24.2% | 716 |
| 16 | `macd_6_13_5` | trend | **-3.083** | 2.223 | 0% | -33.4% | 1156 |

### MEDIUM horizon — CPCV (8 blocks, k=2, 28 paths per configuration)
**PBO = 0.457** across 35 splits of 16 fully-evaluable configurations.

| # | strategy | family | median Sharpe | IQR spread | % paths positive | median path return | trades |
|---|---|---|---|---|---|---|---|
| 1 | `buy_and_hold` | baseline | **+0.534** | 1.434 | 68% | +9.4% | 16 |
| 2 | `bb_breakout_20_2` | breakout | **+0.481** | 1.694 | 67% | +15.9% | 58 |
| 3 | `macd_12_26_9` | trend | **+0.321** | 1.277 | 67% | +3.8% | 118 |
| 4 | `rsi_14_30_50` | oscillator-reversion | **+0.238** | 0.664 | 71% | -0.0% | 18 |
| 5 | `keltner_20_14_2` | breakout | **+0.213** | 1.656 | 76% | +2.2% | 38 |
| 6 | `obv_trend_20` | volume-flow | **+0.189** | 1.536 | 67% | -9.8% | 220 |
| 7 | `breakout_20_10` | breakout | **+0.078** | 1.911 | 52% | -6.4% | 52 |
| 8 | `zscore_20_-2` | mean-reversion | **+0.036** | 0.964 | 52% | -10.0% | 50 |
| 9 | `ts_momentum_60` | momentum | **+0.025** | 1.752 | 52% | -19.4% | 142 |
| 10 | `voltarget_100_20_0.6` | risk-overlay | **-0.021** | 1.154 | 38% | -14.7% | 645 |
| 11 | `stoch_14_3` | oscillator-reversion | **-0.043** | 1.175 | 48% | -13.3% | 56 |
| 12 | `sma_regime_100` | regime-filter | **-0.066** | 1.522 | 48% | -16.4% | 96 |
| 13 | `bb_reversion_20_2` | mean-reversion | **-0.114** | 0.910 | 43% | -19.1% | 50 |
| 14 | `grid_50_4_0.05` | mean-reversion | **-0.152** | 0.369 | 29% | -16.7% | 599 |
| 15 | `vwap_reversion_20_0.02` | mean-reversion | **-0.265** | 0.587 | 29% | -38.4% | 152 |
| 16 | `ma_crossover_20_50` | trend | **-0.334** | 2.186 | 38% | -31.7% | 38 |

### LONG horizon — CPCV (8 blocks, k=2, 28 paths per configuration)
**PBO = 0.457** across 35 splits of 16 fully-evaluable configurations.

| # | strategy | family | median Sharpe | IQR spread | % paths positive | median path return | trades |
|---|---|---|---|---|---|---|---|
| 1 | `obv_trend_60` | volume-flow | **+0.774** | 1.571 | 81% | +44.6% | 98 |
| 2 | `rsi_30_35_55` | oscillator-reversion | **+0.593** | 0.895 | 71% | +20.8% | 10 |
| 3 | `buy_and_hold` | baseline | **+0.534** | 1.434 | 68% | +9.4% | 16 |
| 4 | `macd_26_52_18` | trend | **+0.517** | 1.142 | 76% | +16.1% | 50 |
| 5 | `stoch_40_5` | oscillator-reversion | **+0.316** | 0.752 | 57% | +6.3% | 34 |
| 6 | `voltarget_200_60_0.6` | risk-overlay | **+0.295** | 1.558 | 76% | +5.0% | 661 |
| 7 | `ma_crossover_50_200` | trend | **+0.290** | 1.162 | 52% | +0.0% | 16 |
| 8 | `sma_regime_200` | regime-filter | **+0.254** | 1.620 | 71% | -2.2% | 44 |
| 9 | `ts_momentum_200` | momentum | **+0.200** | 2.341 | 52% | -12.7% | 54 |
| 10 | `breakout_60_30` | breakout | **+0.140** | 1.676 | 62% | -6.6% | 18 |
| 11 | `bb_reversion_60_2` | mean-reversion | **+0.120** | 0.222 | 76% | -6.0% | 24 |
| 12 | `zscore_60_-2` | mean-reversion | **+0.120** | 0.222 | 76% | -6.0% | 24 |
| 13 | `grid_120_4_0.1` | mean-reversion | **+0.095** | 0.869 | 52% | -2.3% | 675 |
| 14 | `keltner_50_30_2` | breakout | **-0.160** | 2.203 | 38% | -17.7% | 34 |
| 15 | `vwap_reversion_60_0.05` | mean-reversion | **-0.162** | 0.420 | 29% | -31.5% | 54 |
| 16 | `bb_breakout_60_2` | breakout | **-0.349** | 1.905 | 43% | -27.1% | 32 |
