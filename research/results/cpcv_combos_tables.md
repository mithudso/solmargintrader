
### SHORT — pairs under CPCV (140 evaluated, 129 evaluable, 2 with positive median Sharpe)

**PBO = 0.371** across 35 splits of 129 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `all(sma_regime+zscore)` | regime-filter+mean-reversion | **+0.681** | 2.584 | 62% | +1.6% | 112 |
| 2 | `all(sma_regime+bb_reversion)` | regime-filter+mean-reversion | **+0.549** | 2.866 | 62% | +1.6% | 112 |
| 3 | `all(sma_regime+rsi)` | regime-filter+oscillator-reversion | **-0.063** | 2.619 | 48% | -0.4% | 142 |
| 4 | `all(breakout+bb_reversion)` | breakout+mean-reversion | **-0.227** | 2.944 | 43% | -0.5% | 12 |
| 5 | `all(breakout+zscore)` | breakout+mean-reversion | **-0.227** | 2.873 | 33% | -0.5% | 10 |
| 6 | `all(stochastic+zscore)` | oscillator-reversion+mean-reversion | **-0.238** | 1.362 | 38% | -2.9% | 208 |
| 7 | `all(ma_crossover+zscore)` | trend+mean-reversion | **-0.309** | 2.596 | 43% | -1.4% | 134 |
| 8 | `all(stochastic+bb_reversion)` | oscillator-reversion+mean-reversion | **-0.354** | 1.557 | 33% | -5.1% | 212 |
| 9 | `all(ma_crossover+bb_reversion)` | trend+mean-reversion | **-0.376** | 2.380 | 43% | -1.6% | 142 |
| 10 | `all(keltner+obv_trend)` | breakout+volume-flow | **-0.448** | 2.197 | 38% | -2.5% | 96 |
| 11 | `all(macd+keltner)` | trend+breakout | **-0.722** | 2.360 | 38% | -2.9% | 130 |
| 12 | `any(keltner+stochastic)` | breakout+oscillator-reversion | **-0.757** | 1.166 | 14% | -8.4% | 322 |
| 13 | `all(ma_crossover+rsi)` | trend+oscillator-reversion | **-0.835** | 3.378 | 43% | -3.2% | 166 |
| 14 | `all(macd+bb_breakout)` | trend+breakout | **-0.836** | 3.648 | 38% | -5.9% | 410 |
| 15 | `all(ts_momentum+keltner)` | momentum+breakout | **-0.961** | 2.477 | 29% | -4.9% | 88 |

_Top 15 of 129 evaluable shown._

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

### MEDIUM — pairs under CPCV (140 evaluated, 123 evaluable, 83 with positive median Sharpe)

**PBO = 0.857** across 35 splits of 123 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `any(bb_breakout+stochastic)` | breakout+oscillator-reversion | **+0.802** | 1.676 | 62% | +47.9% | 110 |
| 2 | `all(breakout+obv_trend)` | breakout+volume-flow | **+0.609** | 1.631 | 62% | +24.3% | 92 |
| 3 | `all(macd+breakout)` | trend+breakout | **+0.592** | 1.477 | 67% | +23.0% | 66 |
| 4 | `any(bb_breakout+zscore)` | breakout+mean-reversion | **+0.573** | 1.590 | 62% | +15.9% | 108 |
| 5 | `any(keltner+stochastic)` | breakout+oscillator-reversion | **+0.556** | 1.220 | 57% | +22.1% | 94 |
| 6 | `all(bb_breakout+obv_trend)` | breakout+volume-flow | **+0.541** | 1.727 | 62% | +19.7% | 76 |
| 7 | `all(macd+bb_breakout)` | trend+breakout | **+0.527** | 1.546 | 62% | +18.8% | 64 |
| 8 | `any(breakout+stochastic)` | breakout+oscillator-reversion | **+0.489** | 1.566 | 57% | +13.1% | 102 |
| 9 | `any(bb_breakout+rsi)` | breakout+oscillator-reversion | **+0.489** | 1.142 | 76% | +15.2% | 72 |
| 10 | `any(keltner+zscore)` | breakout+mean-reversion | **+0.470** | 1.247 | 67% | +2.1% | 88 |
| 11 | `any(macd+zscore)` | trend+mean-reversion | **+0.438** | 1.266 | 62% | -6.9% | 112 |
| 12 | `any(ma_crossover+breakout)` | trend+breakout | **+0.431** | 1.845 | 57% | +9.4% | 46 |
| 13 | `any(macd+stochastic)` | trend+oscillator-reversion | **+0.418** | 1.390 | 62% | +4.4% | 108 |
| 14 | `any(bb_breakout+bb_reversion)` | breakout+mean-reversion | **+0.407** | 1.257 | 62% | -2.4% | 108 |
| 15 | `any(rsi+obv_trend)` | oscillator-reversion+volume-flow | **+0.407** | 1.401 | 71% | +6.3% | 192 |

_Top 15 of 123 evaluable shown._

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

### LONG — pairs under CPCV (140 evaluated, 119 evaluable, 98 with positive median Sharpe)

**PBO = 0.657** across 35 splits of 119 configurations.

| # | combination | families | median Sharpe | IQR | % paths + | median ret | trades |
|---|---|---|---|---|---|---|---|
| 1 | `any(stochastic+obv_trend)` | oscillator-reversion+volume-flow | **+0.812** | 1.318 | 76% | +51.4% | 84 |
| 2 | `all(macd+rsi)` | trend+oscillator-reversion | **+0.751** | 1.071 | 86% | +19.4% | 12 |
| 3 | `any(rsi+obv_trend)` | oscillator-reversion+volume-flow | **+0.748** | 1.490 | 90% | +44.6% | 86 |
| 4 | `any(keltner+obv_trend)` | breakout+volume-flow | **+0.694** | 1.573 | 76% | +35.5% | 88 |
| 5 | `all(macd+obv_trend)` | trend+volume-flow | **+0.680** | 1.784 | 90% | +32.3% | 74 |
| 6 | `any(zscore+obv_trend)` | mean-reversion+volume-flow | **+0.664** | 1.386 | 76% | +28.5% | 92 |
| 7 | `any(bb_reversion+obv_trend)` | mean-reversion+volume-flow | **+0.664** | 1.386 | 76% | +28.5% | 92 |
| 8 | `any(bb_breakout+obv_trend)` | breakout+volume-flow | **+0.626** | 1.532 | 71% | +29.7% | 88 |
| 9 | `all(macd+stochastic)` | trend+oscillator-reversion | **+0.589** | 0.739 | 95% | +21.8% | 30 |
| 10 | `any(breakout+stochastic)` | breakout+oscillator-reversion | **+0.580** | 1.065 | 67% | +24.0% | 52 |
| 11 | `all(stochastic+obv_trend)` | oscillator-reversion+volume-flow | **+0.539** | 0.701 | 86% | +10.9% | 46 |
| 12 | `any(breakout+obv_trend)` | breakout+volume-flow | **+0.537** | 1.701 | 71% | +19.6% | 90 |
| 13 | `any(sma_regime+obv_trend)` | regime-filter+volume-flow | **+0.524** | 1.468 | 71% | +17.8% | 88 |
| 14 | `all(macd+sma_regime)` | trend+regime-filter | **+0.511** | 1.634 | 81% | +17.2% | 32 |
| 15 | `any(ts_momentum+stochastic)` | momentum+oscillator-reversion | **+0.478** | 1.353 | 62% | +9.8% | 54 |

_Top 15 of 119 evaluable shown._

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
