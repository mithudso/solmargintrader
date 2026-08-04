
### SHORT — pairs under CPCV (334 evaluated, 320 evaluable, 11 with positive median Sharpe)

**PBO = 0.229** across 35 splits of 320 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(vol_regime+zscore)` | regime-filter+mean-reversion | **+1.091** | 2.726 | 71% | +2.8% | 84 |
| 2 | `all(vol_regime+ou_reversion)` | regime-filter+mean-reversion | **+0.944** | 2.244 | 71% | +1.4% | 68 |
| 3 | `all(ma_crossover+ou_reversion)` | trend+mean-reversion | **+0.919** | 2.168 | 71% | +1.6% | 94 |
| 4 | `all(vol_regime+bb_reversion)` | regime-filter+mean-reversion | **+0.834** | 2.726 | 71% | +1.9% | 84 |
| 5 | `all(ou_reversion+obv_trend)` | mean-reversion+volume-flow | **+0.688** | 3.779 | 52% | +1.4% | 104 |
| 6 | `all(sma_regime+zscore)` | regime-filter+mean-reversion | **+0.681** | 2.584 | 62% | +1.6% | 112 |
| 7 | `all(sma_regime+bb_reversion)` | regime-filter+mean-reversion | **+0.549** | 2.866 | 62% | +1.6% | 112 |
| 8 | `all(vol_regime+rsi)` | regime-filter+oscillator-reversion | **+0.530** | 2.329 | 57% | +1.2% | 100 |
| 9 | `all(ichimoku+ou_reversion)` | trend+mean-reversion | **+0.400** | 3.146 | 57% | +0.7% | 56 |
| 10 | `all(sma_regime+ou_reversion)` | regime-filter+mean-reversion | **+0.268** | 1.834 | 52% | +0.4% | 92 |
| 11 | `all(adx_trend+stochastic)` | regime-filter+oscillator-reversion | **+0.126** | 1.778 | 52% | +0.2% | 150 |
| 12 | `all(hurst_switch+stochastic)` | regime-filter+oscillator-reversion | **-0.040** | 2.187 | 48% | -0.1% | 90 |
| 13 | `all(sma_regime+rsi)` | regime-filter+oscillator-reversion | **-0.063** | 2.619 | 48% | -0.4% | 142 |
| 14 | `all(vol_regime+vwap_reversion)` | regime-filter+mean-reversion | **-0.117** | 2.696 | 48% | -0.7% | 132 |
| 15 | `all(breakout+bb_reversion)` | breakout+mean-reversion | **-0.227** | 2.944 | 43% | -0.5% | 12 |

_Top 15 of 320 evaluable shown._

### SHORT — triples under CPCV (70 evaluated, 61 evaluable, 6 with positive median Sharpe)

**PBO = 0.086** across 35 splits of 61 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(ma_crossover+sma_regime+zscore)` | trend+regime-filter+mean-reversion | **+1.907** | 2.680 | 76% | +2.7% | 62 |
| 2 | `all(sma_regime+zscore+obv_trend)` | regime-filter+mean-reversion+volume-flow | **+1.844** | 2.091 | 81% | +2.3% | 42 |
| 3 | `all(sma_regime+rsi+obv_trend)` | regime-filter+oscillator-reversion+volume-flow | **+0.950** | 2.734 | 67% | +1.8% | 68 |
| 4 | `all(sma_regime+rsi+zscore)` | regime-filter+oscillator-reversion+mean-reversion | **+0.735** | 2.505 | 67% | +1.6% | 100 |
| 5 | `all(ts_momentum+sma_regime+zscore)` | momentum+regime-filter+mean-reversion | **+0.708** | 2.138 | 71% | +0.5% | 26 |
| 6 | `all(ma_crossover+ts_momentum+zscore)` | trend+momentum+mean-reversion | **+0.239** | 1.847 | 62% | +0.2% | 44 |
| 7 | `all(ts_momentum+sma_regime+rsi)` | momentum+regime-filter+oscillator-reversion | **-0.104** | 2.363 | 48% | -0.2% | 58 |
| 8 | `all(ma_crossover+sma_regime+rsi)` | trend+regime-filter+oscillator-reversion | **-0.458** | 1.902 | 38% | -0.9% | 88 |
| 9 | `all(ma_crossover+zscore+obv_trend)` | trend+mean-reversion+volume-flow | **-0.485** | 3.945 | 29% | -0.1% | 22 |
| 10 | `all(ma_crossover+rsi+zscore)` | trend+oscillator-reversion+mean-reversion | **-0.638** | 2.939 | 33% | -2.3% | 114 |
| 11 | `all(ma_crossover+rsi+obv_trend)` | trend+oscillator-reversion+volume-flow | **-1.517** | 2.147 | 24% | -2.2% | 54 |
| 12 | `all(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **-1.553** | 2.351 | 29% | -5.0% | 180 |
| 13 | `all(sma_regime+breakout+obv_trend)` | regime-filter+breakout+volume-flow | **-1.559** | 1.888 | 10% | -12.6% | 350 |
| 14 | `all(ts_momentum+breakout+obv_trend)` | momentum+breakout+volume-flow | **-1.606** | 2.544 | 24% | -13.5% | 476 |
| 15 | `all(ts_momentum+rsi+zscore)` | momentum+oscillator-reversion+mean-reversion | **-1.653** | 2.503 | 14% | -1.9% | 62 |

_Top 15 of 61 evaluable shown._

### MEDIUM — pairs under CPCV (334 evaluated, 297 evaluable, 201 with positive median Sharpe)

**PBO = 0.650** across 20 splits of 297 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `any(hurst_switch+ou_reversion)` | regime-filter+mean-reversion | **+1.290** | 0.972 | 100% | +68.9% | 40 |
| 2 | `all(stochastic+ou_reversion)` | oscillator-reversion+mean-reversion | **+1.156** | 0.584 | 93% | +30.1% | 18 |
| 3 | `any(bb_breakout+ou_reversion)` | breakout+mean-reversion | **+1.052** | 1.198 | 87% | +67.1% | 76 |
| 4 | `any(macd+ou_reversion)` | trend+mean-reversion | **+0.996** | 0.929 | 87% | +84.3% | 100 |
| 5 | `any(macd+hurst_switch)` | trend+regime-filter | **+0.925** | 1.083 | 93% | +72.6% | 118 |
| 6 | `any(hurst_switch+bb_breakout)` | regime-filter+breakout | **+0.924** | 1.380 | 87% | +48.3% | 72 |
| 7 | `all(ma_ribbon+hurst_switch)` | trend+regime-filter | **+0.881** | 1.238 | 93% | +7.9% | 25 |
| 8 | `any(hurst_switch+stochastic)` | regime-filter+oscillator-reversion | **+0.875** | 1.080 | 87% | +53.5% | 58 |
| 9 | `any(adx_trend+ou_reversion)` | regime-filter+mean-reversion | **+0.850** | 1.353 | 80% | +54.7% | 58 |
| 10 | `any(bb_breakout+stochastic)` | breakout+oscillator-reversion | **+0.802** | 1.676 | 62% | +47.9% | 110 |
| 11 | `all(macd+adx_trend)` | trend+regime-filter | **+0.712** | 1.796 | 71% | +34.2% | 52 |
| 12 | `any(breakout+ou_reversion)` | breakout+mean-reversion | **+0.698** | 1.413 | 87% | +34.8% | 70 |
| 13 | `any(keltner+ou_reversion)` | breakout+mean-reversion | **+0.692** | 1.312 | 87% | +33.8% | 62 |
| 14 | `any(dual_momentum+ou_reversion)` | momentum+mean-reversion | **+0.638** | 1.224 | 73% | +30.4% | 184 |
| 15 | `any(ts_momentum+ou_reversion)` | momentum+mean-reversion | **+0.635** | 1.542 | 60% | +30.5% | 122 |

_Top 15 of 297 evaluable shown._

### MEDIUM — triples under CPCV (70 evaluated, 51 evaluable, 38 with positive median Sharpe)

**PBO = 0.886** across 35 splits of 51 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(sma_regime+breakout+obv_trend)` | regime-filter+breakout+volume-flow | **+0.380** | 1.880 | 52% | +9.6% | 82 |
| 2 | `all(ts_momentum+breakout+obv_trend)` | momentum+breakout+volume-flow | **+0.369** | 1.582 | 71% | +9.1% | 88 |
| 3 | `vote(breakout+zscore+obv_trend)` | breakout+mean-reversion+volume-flow | **+0.367** | 1.305 | 62% | +8.6% | 1373 |
| 4 | `vote(breakout+rsi+zscore)` | breakout+oscillator-reversion+mean-reversion | **+0.349** | 1.192 | 62% | +7.7% | 1090 |
| 5 | `vote(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **+0.339** | 1.013 | 62% | +7.4% | 1312 |
| 6 | `vote(ts_momentum+breakout+zscore)` | momentum+breakout+mean-reversion | **+0.326** | 1.336 | 57% | +5.4% | 1252 |
| 7 | `vote(ts_momentum+rsi+obv_trend)` | momentum+oscillator-reversion+volume-flow | **+0.311** | 1.455 | 57% | +5.3% | 1372 |
| 8 | `vote(ts_momentum+zscore+obv_trend)` | momentum+mean-reversion+volume-flow | **+0.307** | 1.076 | 62% | +5.2% | 1438 |
| 9 | `vote(ma_crossover+zscore+obv_trend)` | trend+mean-reversion+volume-flow | **+0.297** | 1.383 | 57% | +4.6% | 1493 |
| 10 | `vote(ma_crossover+rsi+zscore)` | trend+oscillator-reversion+mean-reversion | **+0.281** | 1.187 | 57% | +3.8% | 1174 |
| 11 | `all(sma_regime+zscore+obv_trend)` | regime-filter+mean-reversion+volume-flow | **+0.249** | 0.592 | 52% | +2.9% | 10 |
| 12 | `vote(breakout+rsi+obv_trend)` | breakout+oscillator-reversion+volume-flow | **+0.248** | 1.438 | 62% | +3.9% | 1193 |
| 13 | `vote(ts_momentum+rsi+zscore)` | momentum+oscillator-reversion+mean-reversion | **+0.238** | 1.061 | 67% | +2.1% | 1173 |
| 14 | `vote(sma_regime+zscore+obv_trend)` | regime-filter+mean-reversion+volume-flow | **+0.219** | 1.172 | 62% | +1.4% | 1422 |
| 15 | `vote(ma_crossover+breakout+zscore)` | trend+breakout+mean-reversion | **+0.212** | 1.611 | 57% | +0.3% | 1230 |

_Top 15 of 51 evaluable shown._

### LONG — pairs under CPCV (334 evaluated, 295 evaluable, 247 with positive median Sharpe)

**PBO = 0.650** across 20 splits of 295 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(dual_momentum+vol_regime)` | momentum+regime-filter | **+1.345** | 0.881 | 87% | +75.1% | 52 |
| 2 | `any(adx_trend+ou_reversion)` | regime-filter+mean-reversion | **+1.162** | 1.423 | 67% | +87.6% | 34 |
| 3 | `any(ou_reversion+obv_trend)` | mean-reversion+volume-flow | **+1.054** | 1.180 | 93% | +93.6% | 90 |
| 4 | `all(macd+vol_regime)` | trend+regime-filter | **+0.991** | 0.957 | 87% | +42.0% | 34 |
| 5 | `any(hurst_switch+ou_reversion)` | regime-filter+mean-reversion | **+0.965** | 1.049 | 93% | +42.6% | 46 |
| 6 | `all(dual_momentum+stochastic)` | momentum+oscillator-reversion | **+0.937** | 1.089 | 95% | +23.4% | 66 |
| 7 | `any(vol_regime+rsi)` | regime-filter+oscillator-reversion | **+0.927** | 0.868 | 100% | +57.9% | 60 |
| 8 | `any(hurst_switch+obv_trend)` | regime-filter+volume-flow | **+0.919** | 1.534 | 100% | +63.1% | 88 |
| 9 | `all(dual_momentum+hurst_switch)` | momentum+regime-filter | **+0.874** | 1.817 | 60% | +6.3% | 16 |
| 10 | `all(hurst_switch+breakout)` | regime-filter+breakout | **+0.873** | 1.762 | 53% | +6.3% | 16 |
| 11 | `any(hurst_switch+stochastic)` | regime-filter+oscillator-reversion | **+0.866** | 0.888 | 87% | +51.9% | 46 |
| 12 | `all(vol_regime+obv_trend)` | regime-filter+volume-flow | **+0.860** | 1.123 | 93% | +36.9% | 44 |
| 13 | `all(macd+adx_trend)` | trend+regime-filter | **+0.848** | 1.903 | 62% | +38.6% | 12 |
| 14 | `any(macd+ou_reversion)` | trend+mean-reversion | **+0.847** | 1.195 | 80% | +52.7% | 58 |
| 15 | `any(vol_regime+ou_reversion)` | regime-filter+mean-reversion | **+0.829** | 0.548 | 100% | +50.4% | 68 |

_Top 15 of 295 evaluable shown._

### LONG — triples under CPCV (70 evaluated, 47 evaluable, 45 with positive median Sharpe)

**PBO = 0.543** across 35 splits of 47 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `vote(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **+0.732** | 0.945 | 81% | +20.4% | 1215 |
| 2 | `vote(breakout+rsi+obv_trend)` | breakout+oscillator-reversion+volume-flow | **+0.590** | 1.413 | 81% | +20.0% | 1158 |
| 3 | `vote(sma_regime+rsi+obv_trend)` | regime-filter+oscillator-reversion+volume-flow | **+0.589** | 1.501 | 76% | +19.0% | 1283 |
| 4 | `vote(ma_crossover+rsi+obv_trend)` | trend+oscillator-reversion+volume-flow | **+0.581** | 1.486 | 81% | +18.5% | 1381 |
| 5 | `vote(ts_momentum+rsi+obv_trend)` | momentum+oscillator-reversion+volume-flow | **+0.564** | 1.695 | 71% | +21.4% | 1364 |
| 6 | `vote(sma_regime+zscore+obv_trend)` | regime-filter+mean-reversion+volume-flow | **+0.512** | 1.702 | 76% | +17.6% | 1398 |
| 7 | `all(ma_crossover+sma_regime+obv_trend)` | trend+regime-filter+volume-flow | **+0.507** | 1.397 | 81% | +18.0% | 42 |
| 8 | `all(rsi+zscore+obv_trend)` | oscillator-reversion+mean-reversion+volume-flow | **+0.475** | 1.012 | 57% | +0.7% | 10 |
| 9 | `vote(breakout+zscore+obv_trend)` | breakout+mean-reversion+volume-flow | **+0.446** | 1.536 | 71% | +13.8% | 1271 |
| 10 | `vote(ts_momentum+zscore+obv_trend)` | momentum+mean-reversion+volume-flow | **+0.425** | 1.695 | 71% | +12.2% | 1449 |
| 11 | `vote(ma_crossover+ts_momentum+sma_regime)` | trend+momentum+regime-filter | **+0.420** | 1.978 | 52% | +8.1% | 415 |
| 12 | `all(ma_crossover+ts_momentum+obv_trend)` | trend+momentum+volume-flow | **+0.410** | 1.648 | 67% | +9.9% | 46 |
| 13 | `vote(ma_crossover+ts_momentum+zscore)` | trend+momentum+mean-reversion | **+0.397** | 1.818 | 52% | +10.4% | 1168 |
| 14 | `vote(ts_momentum+breakout+obv_trend)` | momentum+breakout+volume-flow | **+0.384** | 1.792 | 62% | +10.3% | 887 |
| 15 | `vote(sma_regime+breakout+obv_trend)` | regime-filter+breakout+volume-flow | **+0.383** | 1.689 | 71% | +9.4% | 763 |

_Top 15 of 47 evaluable shown._
