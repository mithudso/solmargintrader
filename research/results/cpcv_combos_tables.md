
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
