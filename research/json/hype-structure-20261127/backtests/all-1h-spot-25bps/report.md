```
==============================================================================
BACKTEST REPORT -- HYPE 1h
==============================================================================
Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.

Range          : 2026-05-03 .. 2026-11-27  (4999 bars)
Mode           : spot
Capital        : 10,000.00 USD
Accounting     : monetary values are in USD; no USD conversion
Costs          : fee 25bps, slippage 2bps
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
                adx_trend_14_25        25.04%   47.94%   1.062    1.744       -31.79%   1.508    25.61%           82             23.16%    6,529.21               0.00                  0     12,503.60
              atr_sized_14_0.01        -7.06%  -12.05%  -0.428   -0.686       -19.85%  -0.607    77.92%         1010             19.89%    3,387.82               0.00                  0      9,293.75
               bb_breakout_20_2        49.18%  101.60%   1.637    2.649       -21.19%   4.794    41.86%           86             28.91%    6,655.90               0.00                  0     14,918.41
              bb_reversion_20_2       -29.91%  -46.36%  -1.089   -1.527       -42.58%  -1.089    55.32%           94             28.53%    4,801.85               0.00                  0      7,009.17
                 breakout_20_10       -15.51%  -25.58%  -0.254   -0.385       -47.86%  -0.534    29.11%           79             36.71%    4,782.94               0.00                  0      8,448.68
                   buy_and_hold        58.24%  123.54%   1.365    2.020       -42.14%   2.932   100.00%            1             99.98%       69.77               0.00                  0     15,824.12
                       dca_10x7        55.43%  116.61%   1.329    1.966       -42.14%   2.767    74.19%           31             99.35%       70.68               0.00                  0     15,542.63
             dual_momentum_12_1       -72.19%  -89.39%  -3.354   -5.048       -79.74%  -1.121    24.85%          330             49.41%   12,374.23               0.00                  0      2,780.65
           ema_crossover_50_200        80.87%  182.54%   1.960    2.988       -23.92%   7.633    60.00%           10             44.17%      763.30               0.00                  0     18,086.96
             fib_60_0.382_0.786       -18.65%  -30.36%  -0.574   -0.832       -36.00%  -0.843    34.92%           63             30.33%    3,386.46               0.00                  0      8,134.93
       garch_voltarget_0.94_0.6       -12.63%  -21.07%  -0.068   -0.105       -45.10%  -0.467    13.79%          116             46.37%    6,888.00               0.00                  0      8,737.07
                 grid_50_4_0.05       -21.04%  -33.90%  -1.932   -2.778       -24.70%  -1.372    13.45%         1309             14.06%    2,773.04               0.00                  0      7,896.15
     hurst_switch_250_0.55_0.45        -8.24%  -13.98%  -0.436   -0.638       -26.52%  -0.527    32.76%           58              5.30%    3,313.29               0.00                  0      9,176.48
               ichimoku_9_26_52       -41.03%  -60.37%  -1.306   -1.978       -58.14%  -1.038    14.18%          134             40.39%    6,735.04               0.00                  0      5,897.47
                keltner_20_14_2        12.75%   23.41%   0.703    1.122       -28.49%   0.822    30.19%           53             19.84%    3,503.00               0.00                  0     11,275.16
      lev_high_20x_macd_12_26_9       -24.48%  -38.87%  -0.526   -0.806       -54.69%  -0.711    34.62%          182             49.51%    9,634.20               0.00                  0      7,551.59
        lev_low_2x_macd_12_26_9       -24.48%  -38.87%  -0.526   -0.806       -54.69%  -0.711    34.62%          182             49.51%    9,634.20               0.00                  0      7,551.59
     lev_medium_5x_macd_12_26_9       -24.48%  -38.87%  -0.526   -0.806       -54.69%  -0.711    34.62%          182             49.51%    9,634.20               0.00                  0      7,551.59
             ma_crossover_20_50         7.17%   12.90%   0.507    0.762       -34.61%   0.373    27.78%           54             48.31%    3,533.94               0.00                  0     10,716.51
                 ma_ribbon_5x10       -21.64%  -34.79%  -0.507   -0.761       -49.59%  -0.702    47.35%         1567             48.92%    5,269.58               0.00                  0      7,835.66
                   macd_12_26_9       -24.48%  -38.87%  -0.526   -0.806       -54.69%  -0.711    34.62%          182             49.51%    9,634.20               0.00                  0      7,551.59
                   obv_trend_20       -58.54%  -78.63%  -2.209   -3.280       -76.79%  -1.024    23.84%          281             47.23%   13,868.87               0.00                  0      4,146.47
           ou_reversion_250_2.5       -29.38%  -45.65%  -2.633   -3.675       -34.65%  -1.317    45.16%           31              8.36%    1,539.87               0.00                  0      7,062.02
                    ppo_12_26_9       -31.77%  -48.83%  -0.831   -1.266       -58.48%  -0.835    33.52%          182             49.27%    9,026.97               0.00                  0      6,823.34
                   rsi_14_30_50        -4.47%   -7.71%  -0.036   -0.052       -24.21%  -0.318    62.86%           35             15.52%    1,732.54               0.00                  0      9,552.55
                 sma_regime_200        36.24%   71.94%   1.180    1.827       -34.64%   2.077    12.82%           78             43.53%    5,956.72               0.00                  0     13,623.61
                     stoch_14_3       -45.05%  -64.99%  -2.009   -2.766       -53.77%  -1.209    48.65%           74             29.25%    3,319.28               0.00                  0      5,494.88
               swing_20_10_50_2       -13.63%  -22.65%  -0.186   -0.282       -47.86%  -0.473    29.49%           78             36.41%    4,834.81               0.00                  0      8,636.76
trigger_rsi_lt30+bb_touch_lo_L3        -0.33%   -0.58%   0.051    0.081       -13.59%  -0.043    43.33%           60              3.60%    3,037.54               0.00                  0      9,966.92
                 ts_momentum_60       -46.79%  -66.91%  -1.451   -2.207       -63.06%  -1.061    20.00%          155             48.23%    6,631.24               0.00                  0      5,320.75
              vol_regime_20_0.5       -34.87%  -52.84%  -1.842   -2.658       -47.50%  -1.112    31.30%          115             22.42%    5,984.41               0.00                  0      6,512.98
           voltarget_100_20_0.6       -21.42%  -34.46%  -0.746   -1.158       -40.84%  -0.844    75.53%          842             35.93%    6,005.86               0.00                  0      7,858.01
         vwap_reversion_20_0.02       -16.46%  -27.04%  -0.403   -0.576       -28.82%  -0.938    64.13%           92             26.55%    4,837.85               0.00                  0      8,353.64
                   zscore_20_-2       -19.29%  -31.32%  -0.588   -0.839       -35.90%  -0.872    57.61%           92             27.85%    4,937.13               0.00                  0      8,070.88

Gross (zero-cost) comparison, to show cost drag:
                       strategy  total return     cagr  sharpe  max drawdown
-------------------------------  ------------  -------  ------  ------------
                adx_trend_14_25        90.33%  208.95%   2.910       -14.92%
              atr_sized_14_0.01        26.82%   51.65%   2.139        -8.87%
               bb_breakout_20_2       115.74%  284.85%   3.304       -12.18%
              bb_reversion_20_2        18.11%   33.87%   0.960       -18.32%
                 breakout_20_10        32.32%   63.36%   1.254       -27.25%
                   buy_and_hold        58.94%  125.27%   1.375       -42.09%
                       dca_10x7        56.13%  118.34%   1.339       -42.09%
             dual_momentum_12_1        51.55%  107.23%   2.117       -18.03%
           ema_crossover_50_200        88.50%  203.77%   2.102       -21.91%
             fib_60_0.382_0.786        15.21%   28.17%   0.814       -26.71%
       garch_voltarget_0.94_0.6        56.25%  118.63%   1.764       -23.07%
                 grid_50_4_0.05         6.69%   12.02%   0.726        -7.10%
     hurst_switch_250_0.55_0.45        24.90%   47.65%   1.705       -10.36%
               ichimoku_9_26_52        26.33%   50.62%   1.116       -21.27%
                keltner_20_14_2        47.78%   98.29%   1.951       -15.58%
      lev_high_20x_macd_12_26_9        71.86%  158.33%   2.381       -26.38%
        lev_low_2x_macd_12_26_9        71.86%  158.33%   2.381       -26.38%
     lev_medium_5x_macd_12_26_9        71.86%  158.33%   2.381       -26.38%
             ma_crossover_20_50        42.50%   86.04%   1.358       -21.00%
                 ma_ribbon_5x10        31.05%   60.64%   1.245       -23.33%
                   macd_12_26_9        71.86%  158.33%   2.381       -26.38%
                   obv_trend_20        80.15%  180.59%   2.698       -18.26%
           ou_reversion_250_2.5       -13.98%  -23.20%  -1.251       -22.61%
                    ppo_12_26_9        58.50%  124.18%   2.082       -26.95%
                   rsi_14_30_50        12.85%   23.60%   0.794       -20.19%
                 sma_regime_200        95.80%  224.69%   2.394       -20.08%
                     stoch_14_3       -11.86%  -19.85%  -0.379       -28.93%
               swing_20_10_50_2        34.72%   68.59%   1.318       -27.34%
trigger_rsi_lt30+bb_touch_lo_L3        30.04%   58.48%   3.239        -6.64%
                 ts_momentum_60        19.52%   36.69%   0.881       -37.62%
              vol_regime_20_0.5        24.97%   47.81%   1.440       -14.84%
           voltarget_100_20_0.6        38.64%   77.29%   1.808       -14.30%
         vwap_reversion_20_0.02        31.91%   62.49%   1.398       -18.98%
                   zscore_20_-2        30.08%   58.55%   1.416       -17.47%

------------------------------------------------------------------------------
WALK-FORWARD -- in-sample vs out-of-sample (net)
------------------------------------------------------------------------------
        strategy  is return  is sharpe  is maxdd  oos return  oos sharpe  oos maxdd
----------------  ---------  ---------  --------  ----------  ----------  ---------
       adx_trend     63.71%      2.581   -24.54%     -23.63%      -5.326    -23.63%
       atr_sized      5.31%      0.646   -16.56%     -11.75%      -3.480    -13.24%
     bb_breakout     65.26%      2.554   -20.66%      -9.73%      -1.398    -20.36%
    bb_reversion     -7.52%     -0.232   -24.41%     -24.21%      -2.710    -28.34%
        breakout     21.57%      1.101   -38.01%     -30.51%      -5.241    -36.07%
    buy_and_hold    121.54%      2.687   -33.44%     -28.91%      -2.146    -41.41%
             dca    117.60%      2.640   -33.44%     -29.00%      -2.168    -41.41%
   dual_momentum    -47.37%     -2.083   -61.10%     -47.16%      -7.751    -50.31%
   ema_crossover     86.13%      2.554   -23.92%      -2.82%      -0.225    -15.39%
 fib_retracement      0.95%      0.291   -33.25%     -19.42%      -3.234    -24.91%
 garch_voltarget     23.13%      1.102   -36.35%     -29.04%      -4.053    -32.34%
            grid    -11.07%     -1.386   -13.38%     -11.32%      -3.132    -14.79%
    hurst_switch      3.62%      0.464   -17.68%     -11.44%      -2.708    -16.98%
        ichimoku     -6.49%      0.050   -37.51%     -36.94%      -6.097    -40.19%
         keltner     34.54%      1.803   -18.47%     -16.20%      -3.374    -21.71%
        lev_high      2.31%      0.405   -41.47%     -25.90%      -3.255    -33.52%
         lev_low      2.31%      0.405   -41.47%     -25.90%      -3.255    -33.52%
      lev_medium      2.31%      0.405   -41.47%     -25.90%      -3.255    -33.52%
    ma_crossover     34.93%      1.427   -27.23%     -20.57%      -2.503    -26.43%
       ma_ribbon     14.31%      0.859   -35.50%     -31.52%      -5.065    -35.36%
            macd      2.31%      0.405   -41.47%     -25.90%      -3.255    -33.52%
       obv_trend    -18.60%     -0.442   -55.77%     -49.06%      -8.210    -51.41%
    ou_reversion     -9.49%     -1.546   -16.24%     -21.98%      -4.221    -22.45%
             ppo     -5.71%      0.082   -44.56%     -27.90%      -3.646    -36.43%
             rsi     -9.58%     -0.586   -24.21%       5.65%       0.960    -10.31%
      sma_regime     65.07%      2.151   -34.64%     -17.47%      -2.590    -23.93%
      stochastic    -19.85%     -1.020   -34.08%     -31.44%      -4.020    -34.75%
swing_confluence     24.28%      1.191   -38.01%     -30.51%      -5.241    -36.07%
   trigger_trade    -11.52%     -2.411   -13.52%      12.65%       2.936     -6.15%
     ts_momentum    -22.94%     -0.617   -55.31%     -30.96%      -4.318    -33.52%
      vol_regime    -16.38%     -0.875   -31.36%     -22.11%      -5.954    -23.52%
       voltarget      4.70%      0.479   -27.75%     -24.95%      -4.394    -27.35%
  vwap_reversion     -2.19%      0.120   -23.52%     -14.59%      -1.517    -28.82%
          zscore     -1.40%      0.133   -22.25%     -18.15%      -1.974    -23.67%

Out-of-sample indicators may warm up from the trailing in-sample bars; reading earlier history is not look-ahead.

------------------------------------------------------------------------------
VERSUS BUY-AND-HOLD BASELINE
------------------------------------------------------------------------------
Baseline buy-and-hold total return: 58.24%
UNDERPERFORMED the baseline:
  adx_trend_14_25          -33.21 pp vs baseline
  atr_sized_14_0.01        -65.30 pp vs baseline
  bb_breakout_20_2         -9.06 pp vs baseline
  bb_reversion_20_2        -88.15 pp vs baseline
  breakout_20_10           -73.75 pp vs baseline
  dca_10x7                 -2.81 pp vs baseline
  dual_momentum_12_1       -130.43 pp vs baseline
  fib_60_0.382_0.786       -76.89 pp vs baseline
  garch_voltarget_0.94_0.6 -70.87 pp vs baseline
  grid_50_4_0.05           -79.28 pp vs baseline
  hurst_switch_250_0.55_0.45 -66.48 pp vs baseline
  ichimoku_9_26_52         -99.27 pp vs baseline
  keltner_20_14_2          -45.49 pp vs baseline
  lev_high_20x_macd_12_26_9 -82.73 pp vs baseline
  lev_low_2x_macd_12_26_9  -82.73 pp vs baseline
  lev_medium_5x_macd_12_26_9 -82.73 pp vs baseline
  ma_crossover_20_50       -51.08 pp vs baseline
  ma_ribbon_5x10           -79.88 pp vs baseline
  macd_12_26_9             -82.73 pp vs baseline
  obv_trend_20             -116.78 pp vs baseline
  ou_reversion_250_2.5     -87.62 pp vs baseline
  ppo_12_26_9              -90.01 pp vs baseline
  rsi_14_30_50             -62.72 pp vs baseline
  sma_regime_200           -22.01 pp vs baseline
  stoch_14_3               -103.29 pp vs baseline
  swing_20_10_50_2         -71.87 pp vs baseline
  trigger_rsi_lt30+bb_touch_lo_L3 -58.57 pp vs baseline
  ts_momentum_60           -105.03 pp vs baseline
  vol_regime_20_0.5        -93.11 pp vs baseline
  voltarget_100_20_0.6     -79.66 pp vs baseline
  vwap_reversion_20_0.02   -74.70 pp vs baseline
  zscore_20_-2             -77.53 pp vs baseline
Outperformed the baseline:
  ema_crossover_50_200     +22.63 pp vs baseline

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
