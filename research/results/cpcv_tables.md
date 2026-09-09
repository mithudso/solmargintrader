
### SHORT horizon — CPCV (8 blocks, k=2, 28 paths per configuration)
**PBO = 0.343** across 35 splits of 25 fully-evaluable configurations.

| # | strategy | family | median Sharpe | IQR spread | % paths positive | median path return | trades |
|---|---|---|---|---|---|---|---|
| 1 | `stoch_14_3` | oscillator-reversion | **-0.341** | 2.117 | 38% | -5.2% | 240 |
| 2 | `ou_reversion_250_2.5` | mean-reversion | **-0.595** | 1.333 | 33% | -3.4% | 196 |
| 3 | `keltner_12_7_2` | breakout | **-0.961** | 2.477 | 29% | -4.9% | 88 |
| 4 | `vol_regime_24_0.5` | regime-filter | **-1.048** | 1.677 | 19% | -8.8% | 290 |
| 5 | `zscore_20_-2` | mean-reversion | **-1.152** | 1.213 | 19% | -12.5% | 294 |
| 6 | `bb_reversion_20_2` | mean-reversion | **-1.316** | 1.396 | 14% | -15.4% | 308 |
| 7 | `buy_and_hold` | baseline | **-1.456** | 2.154 | 29% | -22.9% | 16 |
| 8 | `bb_breakout_20_2` | breakout | **-1.487** | 3.114 | 29% | -11.5% | 270 |
| 9 | `obv_trend_24` | volume-flow | **-1.580** | 1.668 | 24% | -18.0% | 852 |
| 10 | `rsi_7_30_55` | oscillator-reversion | **-1.723** | 1.052 | 14% | -19.8% | 328 |
| 11 | `ichimoku_9_26_52` | trend | **-1.877** | 1.174 | 0% | -18.6% | 392 |
| 12 | `breakout_12_6` | breakout | **-1.905** | 2.809 | 14% | -16.9% | 350 |
| 13 | `grid_48_4_0.03` | mean-reversion | **-2.022** | 0.731 | 0% | -12.4% | 4304 |
| 14 | `vwap_reversion_20_0.01` | mean-reversion | **-2.189** | 0.836 | 0% | -24.3% | 398 |
| 15 | `voltarget_168_24_0.8` | sma-gated | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 16 | `sma_regime_168` | sma-gated | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 17 | `garch_voltarget_0.94_0.8` | sma-gated | **-2.282** | 1.278 | 5% | -19.9% | 292 |
| 18 | `ma_crossover_12_48` | trend | **-2.385** | 3.326 | 10% | -23.5% | 204 |
| 19 | `atr_sized_7_0.01` | sma-gated | **-2.548** | 2.298 | 5% | -12.4% | 3191 |
| 20 | `ts_momentum_24` | momentum | **-2.564** | 2.018 | 0% | -24.2% | 716 |
| 21 | `ma_ribbon_5x6` | trend | **-2.767** | 2.727 | 5% | -19.5% | 4572 |
| 22 | `macd_6_13_5` | trend | **-3.083** | 2.223 | 0% | -33.4% | 1156 |
| 23 | `hurst_switch_250_0.55_0.45` | regime-filter | **-3.123** | 2.107 | 14% | -12.8% | 170 |
| 24 | `adx_trend_7_25` | regime-filter | **-3.736** | 2.496 | 5% | -27.4% | 680 |
| 25 | `dual_momentum_24_2` | momentum | **-4.633** | 2.094 | 0% | -39.2% | 728 |

### MEDIUM horizon — CPCV (8 blocks, k=2, 28 paths per configuration)
**PBO = 0.700** across 20 splits of 25 fully-evaluable configurations.

| # | strategy | family | median Sharpe | IQR spread | % paths positive | median path return | trades |
|---|---|---|---|---|---|---|---|
| 1 | `hurst_switch_250_0.55_0.45` | regime-filter | **+0.699** | 1.167 | 93% | +16.7% | 24 |
| 2 | `buy_and_hold` | baseline | **+0.534** | 1.434 | 68% | +9.4% | 16 |
| 3 | `bb_breakout_20_2` | breakout | **+0.481** | 1.694 | 67% | +15.9% | 58 |
| 4 | `ou_reversion_250_2.5` | mean-reversion | **+0.412** | 0.790 | 93% | +10.5% | 26 |
| 5 | `adx_trend_14_25` | regime-filter | **+0.336** | 2.368 | 71% | +7.0% | 44 |
| 6 | `macd_12_26_9` | trend | **+0.321** | 1.277 | 67% | +3.8% | 118 |
| 7 | `rsi_14_30_50` | oscillator-reversion | **+0.238** | 0.664 | 71% | -0.0% | 18 |
| 8 | `keltner_20_14_2` | breakout | **+0.213** | 1.656 | 76% | +2.2% | 38 |
| 9 | `obv_trend_20` | volume-flow | **+0.189** | 1.536 | 67% | -9.8% | 220 |
| 10 | `breakout_20_10` | breakout | **+0.078** | 1.911 | 52% | -6.4% | 52 |
| 11 | `zscore_20_-2` | mean-reversion | **+0.036** | 0.964 | 52% | -10.0% | 50 |
| 12 | `ts_momentum_60` | momentum | **+0.025** | 1.752 | 52% | -19.4% | 142 |
| 13 | `ichimoku_9_26_52` | trend | **+0.023** | 2.055 | 57% | -10.9% | 82 |
| 14 | `voltarget_100_20_0.6` | sma-gated | **-0.021** | 1.154 | 38% | -14.7% | 645 |
| 15 | `garch_voltarget_0.94_0.6` | sma-gated | **-0.028** | 1.207 | 48% | -12.2% | 711 |
| 16 | `atr_sized_14_0.01` | sma-gated | **-0.038** | 1.289 | 48% | -0.3% | 743 |
| 17 | `stoch_14_3` | oscillator-reversion | **-0.043** | 1.175 | 48% | -13.3% | 56 |
| 18 | `sma_regime_100` | sma-gated | **-0.066** | 1.522 | 48% | -16.4% | 96 |
| 19 | `bb_reversion_20_2` | mean-reversion | **-0.114** | 0.910 | 43% | -19.1% | 50 |
| 20 | `grid_50_4_0.05` | mean-reversion | **-0.152** | 0.369 | 29% | -16.7% | 599 |
| 21 | `vol_regime_20_0.5` | regime-filter | **-0.172** | 0.759 | 40% | -18.7% | 94 |
| 22 | `vwap_reversion_20_0.02` | mean-reversion | **-0.265** | 0.587 | 29% | -38.4% | 152 |
| 23 | `dual_momentum_12_1` | momentum | **-0.319** | 1.459 | 43% | -37.2% | 212 |
| 24 | `ma_crossover_20_50` | trend | **-0.334** | 2.186 | 38% | -31.7% | 38 |
| 25 | `ma_ribbon_5x10` | trend | **-0.336** | 1.957 | 43% | -29.0% | 965 |

### LONG horizon — CPCV (8 blocks, k=2, 28 paths per configuration)
**PBO = 0.700** across 20 splits of 25 fully-evaluable configurations.

| # | strategy | family | median Sharpe | IQR spread | % paths positive | median path return | trades |
|---|---|---|---|---|---|---|---|
| 1 | `obv_trend_60` | volume-flow | **+0.774** | 1.571 | 81% | +44.6% | 98 |
| 2 | `vol_regime_60_0.5` | regime-filter | **+0.696** | 0.823 | 80% | +36.1% | 54 |
| 3 | `adx_trend_30_25` | regime-filter | **+0.651** | 2.286 | 57% | +26.2% | 14 |
| 4 | `rsi_30_35_55` | oscillator-reversion | **+0.593** | 0.895 | 71% | +20.8% | 10 |
| 5 | `hurst_switch_250_0.55_0.45` | regime-filter | **+0.558** | 1.505 | 80% | +11.3% | 32 |
| 6 | `buy_and_hold` | baseline | **+0.534** | 1.434 | 68% | +9.4% | 16 |
| 7 | `macd_26_52_18` | trend | **+0.517** | 1.142 | 76% | +16.1% | 50 |
| 8 | `ou_reversion_250_3` | mean-reversion | **+0.412** | 0.806 | 73% | +10.5% | 24 |
| 9 | `dual_momentum_24_1` | momentum | **+0.358** | 1.715 | 57% | +5.5% | 156 |
| 10 | `stoch_40_5` | oscillator-reversion | **+0.316** | 0.752 | 57% | +6.3% | 34 |
| 11 | `voltarget_200_60_0.6` | sma-gated | **+0.295** | 1.558 | 76% | +5.0% | 661 |
| 12 | `ma_crossover_50_200` | trend | **+0.290** | 1.162 | 52% | +0.0% | 16 |
| 13 | `sma_regime_200` | sma-gated | **+0.254** | 1.620 | 71% | -2.2% | 44 |
| 14 | `ichimoku_18_52_104` | trend | **+0.243** | 0.950 | 71% | +2.5% | 56 |
| 15 | `garch_voltarget_0.97_0.6` | sma-gated | **+0.239** | 1.558 | 76% | +2.3% | 672 |
| 16 | `ts_momentum_200` | momentum | **+0.200** | 2.341 | 52% | -12.7% | 54 |
| 17 | `ma_ribbon_5x20` | trend | **+0.171** | 1.319 | 57% | -2.6% | 1030 |
| 18 | `atr_sized_30_0.01` | sma-gated | **+0.156** | 1.715 | 67% | +0.7% | 672 |
| 19 | `breakout_60_30` | breakout | **+0.140** | 1.676 | 62% | -6.6% | 18 |
| 20 | `zscore_60_-2` | mean-reversion | **+0.120** | 0.222 | 76% | -6.0% | 24 |
| 21 | `bb_reversion_60_2` | mean-reversion | **+0.120** | 0.222 | 76% | -6.0% | 24 |
| 22 | `grid_120_4_0.1` | mean-reversion | **+0.095** | 0.869 | 52% | -2.3% | 675 |
| 23 | `keltner_50_30_2` | breakout | **-0.160** | 2.203 | 38% | -17.7% | 34 |
| 24 | `vwap_reversion_60_0.05` | mean-reversion | **-0.162** | 0.420 | 29% | -31.5% | 54 |
| 25 | `bb_breakout_60_2` | breakout | **-0.349** | 1.905 | 43% | -27.1% | 32 |
