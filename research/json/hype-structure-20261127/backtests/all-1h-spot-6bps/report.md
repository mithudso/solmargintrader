```
==============================================================================
BACKTEST REPORT -- HYPE 1h
==============================================================================
Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.

Range          : 2026-05-03 .. 2026-11-27  (4999 bars)
Mode           : spot
Capital        : 10,000.00 USD
Accounting     : monetary values are in USD; no USD conversion
Costs          : fee 6bps, slippage 2bps
Fill           : signal at bar t -> fill at t+1 open
Sharpe         : mean(excess)/stdev(excess, ddof=1) * sqrt(periods_per_year); 365-day crypto year; risk-free rate is an explicit parameter
Periods/year   : 8760
Data           : csv:HYPE_1h.csv (sha256:71ca7fe81dce9ba9)
Seed           : 0

------------------------------------------------------------------------------
FULL SAMPLE -- net of fees, slippage, and borrow costs
------------------------------------------------------------------------------
                       strategy  total return     cagr  sharpe  sortino  max drawdown  calmar  win rate  trade count  exposure fraction  total fees  total borrow fees  liquidation count  final equity
-------------------------------  ------------  -------  ------  -------  ------------  ------  --------  -----------  -----------------  ----------  -----------------  -----------------  ------------
                adx_trend_14_25        70.75%  155.42%   2.224    3.706       -22.63%   6.868    30.49%           82             23.16%    2,275.59               0.00                  0     17,075.04
              atr_sized_14_0.01        17.66%   32.99%   1.334    2.182       -11.55%   2.857    82.46%         1009             19.89%    1,130.41               0.00                  0     11,766.41
               bb_breakout_20_2       106.85%  257.47%   2.778    4.556       -16.96%  15.180    47.67%           86             28.91%    2,353.73               0.00                  0     20,684.76
              bb_reversion_20_2         0.18%    0.32%   0.241    0.342       -26.50%   0.012    59.57%           94             28.53%    1,697.21               0.00                  0     10,018.37
                 breakout_20_10        14.07%   25.95%   0.691    1.058       -34.01%   0.763    35.44%           79             36.71%    1,643.58               0.00                  0     11,406.82
                   buy_and_hold        58.84%  125.03%   1.372    2.032       -42.14%   2.967   100.00%            1             99.98%       20.71               0.00                  0     15,884.36
                       dca_10x7        56.03%  118.10%   1.337    1.978       -42.14%   2.803    80.65%           31             99.35%       20.97               0.00                  0     15,603.28
             dual_momentum_12_1        -2.56%   -4.44%   0.226    0.351       -45.19%  -0.098    35.76%          330             49.41%    6,334.35               0.00                  0      9,744.35
           ema_crossover_50_200        87.87%  202.00%   2.066    3.152       -22.72%   8.892    60.00%           10             44.17%      230.96               0.00                  0     18,787.49
             fib_60_0.382_0.786         3.35%    5.95%   0.353    0.516       -28.49%   0.209    34.92%           63             30.33%    1,131.76               0.00                  0     10,335.33
       garch_voltarget_0.94_0.6        35.77%   70.91%   1.169    1.822       -29.20%   2.428    15.52%          116             46.37%    2,553.22               0.00                  0     13,576.99
                 grid_50_4_0.05        -2.11%   -3.67%  -0.083   -0.122       -11.05%  -0.332    21.21%         1301             14.06%      912.97               0.00                  0      9,788.64
     hurst_switch_250_0.55_0.45        14.39%   26.58%   1.028    1.544       -13.86%   1.917    51.72%           58              5.30%    1,093.33               0.00                  0     11,439.18
               ichimoku_9_26_52        -1.87%   -3.25%   0.230    0.353       -39.30%  -0.083    17.91%          134             40.39%    2,540.83               0.00                  0      9,813.17
                keltner_20_14_2        37.91%   75.65%   1.531    2.476       -21.66%   3.492    35.85%           53             19.84%    1,152.25               0.00                  0     13,790.81
      lev_high_20x_macd_12_26_9        50.80%  105.44%   1.504    2.345       -33.93%   3.108    40.11%          182             49.51%    3,988.28               0.00                  0     15,079.87
        lev_low_2x_macd_12_26_9        50.80%  105.44%   1.504    2.345       -33.93%   3.108    40.11%          182             49.51%    3,988.28               0.00                  0     15,079.87
     lev_medium_5x_macd_12_26_9        50.80%  105.44%   1.504    2.345       -33.93%   3.108    40.11%          182             49.51%    3,988.28               0.00                  0     15,079.87
             ma_crossover_20_50        31.57%   61.76%   1.070    1.615       -27.84%   2.219    33.33%           54             48.31%    1,161.79               0.00                  0     13,157.43
                 ma_ribbon_5x10        10.79%   19.67%   0.600    0.907       -33.05%   0.595    57.37%         1534             48.92%    1,848.04               0.00                  0     11,078.69
                   macd_12_26_9        50.80%  105.44%   1.504    2.345       -33.93%   3.108    40.11%          182             49.51%    3,988.28               0.00                  0     15,079.87
                   obv_trend_20        20.62%   38.90%   0.842    1.283       -39.76%   0.978    28.11%          281             47.23%    6,684.52               0.00                  0     12,062.02
           ou_reversion_250_2.5       -20.55%  -33.18%  -1.720   -2.440       -28.00%  -1.185    45.16%           31              8.36%      482.37               0.00                  0      7,944.91
                    ppo_12_26_9        36.26%   71.98%   1.210    1.876       -34.89%   2.063    39.01%          182             49.27%    3,719.70               0.00                  0     13,625.62
                   rsi_14_30_50         9.11%   16.52%   0.601    0.868       -21.87%   0.755    62.86%           35             15.52%      549.05               0.00                  0     10,911.41
                 sma_regime_200        83.24%  189.06%   2.019    3.146       -25.77%   7.337    14.10%           78             43.53%    2,060.81               0.00                  0     18,323.89
                     stoch_14_3       -27.21%  -42.68%  -0.960   -1.332       -41.71%  -1.023    51.35%           74             29.25%    1,124.24               0.00                  0      7,279.18
               swing_20_10_50_2        16.17%   30.03%   0.749    1.148       -34.01%   0.883    35.90%           78             36.41%    1,657.65               0.00                  0     11,616.52
trigger_rsi_lt30+bb_touch_lo_L3        25.19%   48.26%   2.405    4.129        -8.81%   5.481    58.33%           60              3.60%    1,010.40               0.00                  0     12,519.31
                 ts_momentum_60        -4.11%   -7.09%   0.192    0.296       -47.58%  -0.149    29.68%          155             48.23%    2,600.04               0.00                  0      9,588.99
              vol_regime_20_0.5         0.82%    1.45%   0.222    0.329       -28.57%   0.051    33.04%          115             22.42%    2,183.72               0.00                  0     10,082.48
           voltarget_100_20_0.6        19.71%   37.06%   0.939    1.484       -23.01%   1.611    80.74%          841             35.92%    2,193.08               0.00                  0     11,970.64
         vwap_reversion_20_0.02        18.50%   34.64%   0.854    1.236       -25.50%   1.358    68.48%           92             26.55%    1,717.93               0.00                  0     11,849.66
                   zscore_20_-2        14.49%   26.76%   0.747    1.080       -20.74%   1.290    60.87%           92             27.85%    1,744.25               0.00                  0     11,448.56

Gross (zero-cost) comparison, to show cost drag:
                       strategy  total return     cagr  sharpe  max drawdown
-------------------------------  ------------  -------  ------  ------------
                adx_trend_14_25        93.51%  218.05%   2.776       -17.76%
              atr_sized_14_0.01        28.97%   56.19%   2.097        -9.33%
               bb_breakout_20_2       130.38%  331.79%   3.274       -14.22%
              bb_reversion_20_2        17.16%   31.98%   0.853       -21.43%
                 breakout_20_10        30.50%   59.46%   1.141       -29.15%
                   buy_and_hold        59.05%  125.54%   1.375       -42.12%
                       dca_10x7        56.24%  118.61%   1.340       -42.12%
             dual_momentum_12_1        60.79%  129.88%   1.888       -22.89%
           ema_crossover_50_200        90.18%  208.54%   2.108       -22.13%
             fib_60_0.382_0.786        14.67%   27.12%   0.768       -27.31%
       garch_voltarget_0.94_0.6        61.30%  131.17%   1.717       -25.07%
                 grid_50_4_0.05         7.02%   12.62%   0.708        -7.82%
     hurst_switch_250_0.55_0.45        25.33%   48.54%   1.665       -12.04%
               ichimoku_9_26_52        23.54%   44.85%   0.956       -28.41%
                keltner_20_14_2        49.43%  102.18%   1.902       -17.93%
      lev_high_20x_macd_12_26_9        90.68%  209.95%   2.370       -30.30%
        lev_low_2x_macd_12_26_9        90.68%  209.95%   2.370       -30.30%
     lev_medium_5x_macd_12_26_9        90.68%  209.95%   2.370       -30.30%
             ma_crossover_20_50        43.19%   87.62%   1.322       -23.65%
                 ma_ribbon_5x10        29.27%   56.82%   1.123       -25.33%
                   macd_12_26_9        90.68%  209.95%   2.370       -30.30%
                   obv_trend_20        87.47%  200.85%   2.345       -20.86%
           ou_reversion_250_2.5       -15.73%  -25.91%  -1.306       -24.27%
                    ppo_12_26_9        73.45%  162.55%   2.077       -31.08%
                   rsi_14_30_50        14.60%   26.99%   0.847       -20.66%
                 sma_regime_200       103.85%  248.43%   2.381       -21.19%
                     stoch_14_3       -15.97%  -26.28%  -0.475       -33.50%
               swing_20_10_50_2        32.74%   64.28%   1.197       -29.18%
trigger_rsi_lt30+bb_touch_lo_L3        35.30%   69.87%   3.342        -6.98%
                 ts_momentum_60        21.89%   41.47%   0.888       -41.98%
              vol_regime_20_0.5        22.66%   43.05%   1.211       -20.15%
           voltarget_100_20_0.6        41.64%   84.06%   1.702       -16.80%
         vwap_reversion_20_0.02        35.68%   70.70%   1.391       -21.66%
                   zscore_20_-2        31.93%   62.52%   1.345       -18.10%

------------------------------------------------------------------------------
WALK-FORWARD -- in-sample vs out-of-sample (net)
------------------------------------------------------------------------------
        strategy  is return  is sharpe  is maxdd  oos return  oos sharpe  oos maxdd
----------------  ---------  ---------  --------  ----------  ----------  ---------
       adx_trend    103.31%      3.606   -18.89%     -16.01%      -3.464    -17.40%
       atr_sized     24.47%      2.347   -11.55%      -5.47%      -1.516     -9.26%
     bb_breakout    109.97%      3.655   -16.33%      -1.48%      -0.044    -16.96%
    bb_reversion     17.05%      1.127   -19.66%     -14.41%      -1.413    -25.31%
        breakout     49.83%      1.955   -32.47%     -23.87%      -3.886    -30.49%
    buy_and_hold    122.38%      2.698   -33.44%     -28.64%      -2.118    -41.41%
             dca    118.45%      2.651   -33.44%     -28.72%      -2.140    -41.41%
   dual_momentum     28.05%      1.265   -30.20%     -23.90%      -3.257    -31.25%
   ema_crossover     91.87%      2.662   -22.72%      -1.33%      -0.001    -15.39%
 fib_retracement     18.87%      1.140   -28.49%     -13.05%      -2.043    -22.74%
 garch_voltarget     67.51%      2.238   -29.20%     -18.95%      -2.409    -26.86%
            grid      3.93%      0.588    -7.98%      -5.84%      -1.523    -10.36%
    hurst_switch     16.58%      1.566    -9.13%      -1.87%      -0.317    -13.86%
        ichimoku     32.65%      1.431   -26.76%     -26.02%      -3.956    -30.10%
         keltner     55.44%      2.569   -16.11%     -11.28%      -2.258    -19.87%
        lev_high     65.14%      2.299   -33.93%      -8.32%      -0.773    -21.57%
         lev_low     65.14%      2.299   -33.93%      -8.32%      -0.773    -21.57%
      lev_medium     65.14%      2.299   -33.93%      -8.32%      -0.773    -21.57%
    ma_crossover     55.29%      1.933   -23.98%     -15.27%      -1.735    -21.67%
       ma_ribbon     43.86%      1.828   -28.83%     -22.99%      -3.433    -27.94%
            macd     65.14%      2.299   -33.93%      -8.32%      -0.773    -21.57%
       obv_trend     70.13%      2.339   -29.04%     -29.10%      -4.132    -32.54%
    ou_reversion     -3.08%     -0.438   -12.20%     -18.03%      -3.376    -18.67%
             ppo     52.77%      1.996   -34.89%     -10.80%      -1.124    -24.17%
             rsi     -3.18%     -0.074   -21.87%      12.69%       1.838    -10.31%
      sma_regime    104.21%      2.923   -25.77%     -10.27%      -1.387    -21.58%
      stochastic     -1.97%      0.111   -30.13%     -25.75%      -3.128    -30.44%
swing_confluence     52.59%      2.033   -32.47%     -23.87%      -3.886    -30.49%
   trigger_trade     -1.21%     -0.188    -8.81%      26.73%       5.743     -4.35%
     ts_momentum     17.05%      0.917   -47.58%     -18.08%      -2.235    -24.45%
      vol_regime     18.16%      1.223   -14.75%     -14.67%      -3.809    -18.07%
       voltarget     41.26%      2.097   -19.59%     -15.26%      -2.474    -18.24%
  vwap_reversion     24.27%      1.387   -20.93%      -4.64%      -0.280    -25.50%
          zscore     24.32%      1.490   -18.77%      -7.91%      -0.664    -20.74%

Out-of-sample indicators may warm up from the trailing in-sample bars; reading earlier history is not look-ahead.

------------------------------------------------------------------------------
VERSUS BUY-AND-HOLD BASELINE
------------------------------------------------------------------------------
Baseline buy-and-hold total return: 58.84%
UNDERPERFORMED the baseline:
  atr_sized_14_0.01        -41.18 pp vs baseline
  bb_reversion_20_2        -58.66 pp vs baseline
  breakout_20_10           -44.78 pp vs baseline
  dca_10x7                 -2.81 pp vs baseline
  dual_momentum_12_1       -61.40 pp vs baseline
  fib_60_0.382_0.786       -55.49 pp vs baseline
  garch_voltarget_0.94_0.6 -23.07 pp vs baseline
  grid_50_4_0.05           -60.96 pp vs baseline
  hurst_switch_250_0.55_0.45 -44.45 pp vs baseline
  ichimoku_9_26_52         -60.71 pp vs baseline
  keltner_20_14_2          -20.94 pp vs baseline
  lev_high_20x_macd_12_26_9 -8.04 pp vs baseline
  lev_low_2x_macd_12_26_9  -8.04 pp vs baseline
  lev_medium_5x_macd_12_26_9 -8.04 pp vs baseline
  ma_crossover_20_50       -27.27 pp vs baseline
  ma_ribbon_5x10           -48.06 pp vs baseline
  macd_12_26_9             -8.04 pp vs baseline
  obv_trend_20             -38.22 pp vs baseline
  ou_reversion_250_2.5     -79.39 pp vs baseline
  ppo_12_26_9              -22.59 pp vs baseline
  rsi_14_30_50             -49.73 pp vs baseline
  stoch_14_3               -86.05 pp vs baseline
  swing_20_10_50_2         -42.68 pp vs baseline
  trigger_rsi_lt30+bb_touch_lo_L3 -33.65 pp vs baseline
  ts_momentum_60           -62.95 pp vs baseline
  vol_regime_20_0.5        -58.02 pp vs baseline
  voltarget_100_20_0.6     -39.14 pp vs baseline
  vwap_reversion_20_0.02   -40.35 pp vs baseline
  zscore_20_-2             -44.36 pp vs baseline
Outperformed the baseline:
  adx_trend_14_25          +11.91 pp vs baseline
  bb_breakout_20_2         +48.00 pp vs baseline
  ema_crossover_50_200     +29.03 pp vs baseline
  sma_regime_200           +24.40 pp vs baseline

------------------------------------------------------------------------------
Configurations evaluated in this run: 34
------------------------------------------------------------------------------
SELECTION BIAS WARNING -- read before acting on the ranking above.

The best of N backtests is upward-biased by the act of selection, and the bias
grows with N. Two calibration points from the literature:

  * Harvey, Liu & Zhu (2016) audited 316+ published "significant" factors and
    argued the t-statistic bar should rise from ~2.0 to ~3.0+ once multiple
    testing is accounted for. Most published factors below t = 3.0 are likely
    false discoveries.
  * McLean & Pontiff (2016) tracked 97 published factors: returns decayed 26%
    in-sample post-publication and 58% out-of-sample.

Practical reading of this report: treat the out-of-sample column as the only
column that carries evidence, treat any strategy that fails to beat
buy-and-hold as failing, and remember that a strategy you arrived at by trying
several variants has already spent some of its statistical significance.

Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.
```
