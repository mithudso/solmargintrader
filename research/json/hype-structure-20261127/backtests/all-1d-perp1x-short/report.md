```
==============================================================================
BACKTEST REPORT -- HYPE 1d
==============================================================================
Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.

Range          : 2024-12-05 .. 2026-11-26  (722 bars)
Mode           : perp @ 1x
Capital        : 10,000.00 USD
Accounting     : monetary values are in USD; no USD conversion
Costs          : fee 6bps, slippage 2bps
Borrow (max/hr): long 1.6bps, short 0.3bps @ utilization 0.5 (floor 0bps)
                 Borrow fees are charged on notional to BOTH sides and are never negative.
Fill           : signal at bar t -> fill at t+1 open
Sharpe         : mean(excess)/stdev(excess, ddof=1) * sqrt(periods_per_year); 365-day crypto year; risk-free rate is an explicit parameter
Periods/year   : 365
Data           : csv:HYPE_1d.csv (sha256:772e446a5838794c)
Seed           : 0

------------------------------------------------------------------------------
FULL SAMPLE -- net of fees, slippage, and borrow costs
------------------------------------------------------------------------------
                       strategy  total return     cagr  sharpe  sortino  max drawdown  calmar  win rate  trade count  exposure fraction  total fees  total borrow fees  liquidation count  final equity
-------------------------------  ------------  -------  ------  -------  ------------  ------  --------  -----------  -----------------  ----------  -----------------  -----------------  ------------
                adx_trend_14_25       -44.28%  -25.63%  -0.403   -0.589       -69.92%  -0.367    68.11%          185             25.67%      213.83           3,032.11                  0      5,571.70
              atr_sized_14_0.01         3.96%    1.99%   0.433    0.677        -6.47%   0.307    87.44%          199              4.32%       18.79             484.22                  0     10,396.21
               bb_breakout_20_2        -5.31%   -2.73%   0.185    0.291       -46.10%  -0.059    77.13%          188             26.08%      207.45           3,317.62                  0      9,468.61
              bb_reversion_20_2        21.51%   10.36%   0.442    0.672       -43.03%   0.241    32.93%          167             23.18%      237.63           4,079.91                  0     12,150.54
                 breakout_20_10       -29.25%  -16.07%  -0.015   -0.023       -57.88%  -0.278    65.00%          260             36.07%      172.01           4,043.28                  0      7,074.54
                   buy_and_hold       143.44%   56.89%   0.943    1.491       -72.05%   0.790    94.17%          721             99.82%       73.92          15,083.79                  1     24,343.79
                       dca_10x7         2.18%    1.10%   0.481    0.734       -69.62%   0.016    49.13%          690             95.51%       52.82          10,956.61                  1     10,217.90
             dual_momentum_12_1       -56.74%  -34.57%  -0.249   -0.367       -80.00%  -0.432    64.05%          370             51.34%      595.11           5,485.66                  0      4,326.16
           ema_crossover_50_200       -22.19%  -11.93%   0.131    0.197       -55.46%  -0.215    70.29%          414             57.42%       29.53           5,482.08                  0      7,780.52
             fib_60_0.382_0.786        10.04%    4.96%   0.355    0.530       -38.43%   0.129    59.35%          246             34.13%      154.81           4,953.84                  0     11,004.49
       garch_voltarget_0.94_0.6        18.08%    8.78%   0.409    0.637       -45.85%   0.191    83.22%          149             39.84%      225.50           6,215.43                  0     11,807.64
                 grid_50_4_0.05       -24.78%  -13.42%  -0.026   -0.037       -52.56%  -0.255    24.10%          195             26.85%      290.78           3,603.17                  0      7,521.97
     hurst_switch_250_0.55_0.45         0.00%    0.00%   0.000    0.000         0.00%   0.000     0.00%            0              0.00%        0.00               0.00                  0     10,000.00
               ichimoku_9_26_52       -22.22%  -11.95%   0.083    0.124       -69.52%  -0.172    81.53%          352             48.83%      348.06           5,653.10                  0      7,777.63
                keltner_20_14_2        31.18%   14.73%   0.529    0.844       -40.46%   0.364    75.45%          167             23.17%      207.85           4,031.45                  0     13,117.58
      lev_high_20x_macd_12_26_9       -11.42%   -5.95%   0.227    0.363       -67.48%  -0.088    64.74%          312             43.29%      454.43           4,843.58                  0      8,858.13
        lev_low_2x_macd_12_26_9       -11.42%   -5.95%   0.227    0.363       -67.48%  -0.088    64.74%          312             43.29%      454.43           4,843.58                  0      8,858.13
     lev_medium_5x_macd_12_26_9       -11.42%   -5.95%   0.227    0.363       -67.48%  -0.088    64.74%          312             43.29%      454.43           4,843.58                  0      8,858.13
             ma_crossover_20_50        50.17%   22.86%   0.638    0.995       -42.31%   0.540    73.04%          408             56.59%      125.78           8,152.32                  0     15,017.26
                 ma_ribbon_5x10        26.71%   12.73%   0.499    0.760       -48.41%   0.263    70.23%          383             54.17%      287.23           8,117.85                  0     12,671.10
                   macd_12_26_9       -11.42%   -5.95%   0.227    0.363       -67.48%  -0.088    64.74%          312             43.29%      454.43           4,843.58                  0      8,858.13
                   obv_trend_20        -1.92%   -0.98%   0.308    0.495       -64.72%  -0.015    75.00%          324             44.95%      849.56           5,412.07                  0      9,807.58
           ou_reversion_250_2.5        17.12%    8.33%   0.590    1.184        -8.54%   0.975    71.43%           14              1.94%       34.12             266.36                  0     11,712.01
                    ppo_12_26_9       -23.23%  -12.52%   0.094    0.148       -62.27%  -0.201    67.23%          296             41.07%      361.96           3,894.99                  0      7,677.31
                   rsi_14_30_50       -18.88%  -10.05%  -0.182   -0.260       -40.62%  -0.247    30.14%           73             10.13%       46.09           1,365.52                  0      8,112.16
                 sma_regime_200       -27.97%  -15.30%   0.042    0.063       -59.69%  -0.256    85.45%          385             53.40%       83.46           4,611.96                  0      7,203.29
                     stoch_14_3        11.73%    5.78%   0.388    0.601       -44.79%   0.129    29.73%          222             30.81%      265.08           5,289.70                  0     11,173.46
               swing_20_10_50_2       -29.25%  -16.07%  -0.015   -0.023       -57.88%  -0.278    65.00%          260             36.07%      172.01           4,043.28                  0      7,074.54
trigger_rsi_lt30+bb_touch_lo_L3        22.06%   10.62%   0.867    1.641        -8.68%   1.223    83.33%           12              1.67%       72.09             251.76                  0     12,205.59
                 ts_momentum_60        26.56%   12.66%   0.506    0.793       -61.55%   0.206    83.85%          421             58.39%      338.95           8,299.98                  0     12,655.50
              vol_regime_20_0.5       -15.76%   -8.32%   0.006    0.010       -39.45%  -0.211    32.16%          199             27.61%      232.94           3,865.13                  0      8,423.96
           voltarget_100_20_0.6        16.91%    8.23%   0.400    0.622       -47.15%   0.175    77.78%          225             41.44%      249.83           6,699.44                  0     11,691.26
         vwap_reversion_20_0.02        -1.71%   -0.87%   0.326    0.473       -53.00%  -0.016    21.88%          320             44.42%      744.65           7,365.13                  0      9,829.15
                   zscore_20_-2        36.81%   17.20%   0.579    0.894       -43.03%   0.400    36.17%          141             19.57%      218.72           3,419.52                  0     13,681.23

Gross (zero-cost) comparison, to show cost drag:
                       strategy  total return     cagr  sharpe  max drawdown
-------------------------------  ------------  -------  ------  ------------
                adx_trend_14_25       -11.82%   -6.17%   0.042       -55.59%
              atr_sized_14_0.01         8.99%    4.46%   0.949        -5.80%
               bb_breakout_20_2        29.94%   14.18%   0.520       -35.45%
              bb_reversion_20_2        64.68%   28.73%   0.829       -39.83%
                 breakout_20_10        12.90%    6.33%   0.366       -45.36%
                   buy_and_hold       295.02%  100.46%   1.235       -63.63%
                       dca_10x7       112.27%   46.38%   0.898       -55.43%
             dual_momentum_12_1         4.07%    2.04%   0.304       -54.00%
           ema_crossover_50_200        32.92%   15.50%   0.536       -41.79%
             fib_60_0.382_0.786        61.13%   27.32%   0.759       -35.23%
       garch_voltarget_0.94_0.6        82.49%   35.60%   1.004       -37.61%
                 grid_50_4_0.05        14.16%    6.93%   0.371       -45.03%
     hurst_switch_250_0.55_0.45         0.00%    0.00%   0.000         0.00%
               ichimoku_9_26_52        37.79%   17.62%   0.577       -54.57%
                keltner_20_14_2        73.57%   32.20%   0.896       -28.81%
      lev_high_20x_macd_12_26_9        41.56%   19.24%   0.593       -52.16%
        lev_low_2x_macd_12_26_9        41.56%   19.24%   0.593       -52.16%
     lev_medium_5x_macd_12_26_9        41.56%   19.24%   0.593       -52.16%
             ma_crossover_20_50       132.95%   53.44%   1.045       -38.54%
                 ma_ribbon_5x10       110.76%   45.85%   1.006       -35.45%
                   macd_12_26_9        41.56%   19.24%   0.593       -52.16%
                   obv_trend_20        60.69%   27.14%   0.715       -50.63%
           ou_reversion_250_2.5        20.12%    9.73%   0.674        -8.27%
                    ppo_12_26_9        19.34%    9.36%   0.425       -46.73%
                   rsi_14_30_50        -4.76%   -2.44%   0.063       -35.92%
                 sma_regime_200        18.99%    9.20%   0.422       -46.55%
                     stoch_14_3        67.28%   29.75%   0.759       -33.56%
               swing_20_10_50_2        12.90%    6.33%   0.366       -45.36%
trigger_rsi_lt30+bb_touch_lo_L3        25.29%   12.09%   0.967        -8.22%
                 ts_momentum_60       112.94%   46.62%   0.971       -50.47%
              vol_regime_20_0.5        25.22%   12.06%   0.489       -31.48%
           voltarget_100_20_0.6        86.41%   37.06%   1.007       -38.44%
         vwap_reversion_20_0.02        79.39%   34.43%   0.815       -43.85%
                   zscore_20_-2        73.19%   32.06%   0.901       -39.83%

------------------------------------------------------------------------------
WALK-FORWARD -- in-sample vs out-of-sample (net)
------------------------------------------------------------------------------
        strategy  is return  is sharpe  is maxdd  oos return  oos sharpe  oos maxdd
----------------  ---------  ---------  --------  ----------  ----------  ---------
       adx_trend    -24.67%     -0.232   -58.93%     -26.03%      -0.765    -45.30%
       atr_sized      2.28%      0.412    -6.47%       1.54%       0.457     -2.85%
     bb_breakout    -24.13%     -0.195   -46.10%      24.80%       0.957    -31.71%
    bb_reversion     37.81%      0.716   -43.03%     -11.83%      -0.462    -27.63%
        breakout    -30.60%     -0.167   -57.88%       1.94%       0.341    -34.07%
    buy_and_hold    108.68%      1.024   -72.05%      15.96%       0.711    -42.22%
             dca     -5.51%      0.449   -69.62%      -9.95%       0.096    -43.51%
   dual_momentum    -43.78%     -0.206   -75.03%     -23.04%      -0.365    -54.48%
   ema_crossover    -33.37%     -0.250   -55.46%      15.96%       0.711    -42.22%
 fib_retracement     29.40%      0.622   -38.43%     -14.96%      -0.182    -34.83%
 garch_voltarget     16.46%      0.475   -45.85%       0.82%       0.293    -29.21%
            grid    -14.65%      0.097   -52.56%     -11.87%      -0.654    -21.20%
    hurst_switch       -inf       -inf      -inf        -inf        -inf       -inf
        ichimoku    -28.92%     -0.164   -69.52%       9.17%       0.555    -32.50%
         keltner     23.28%      0.556   -39.92%       6.40%       0.462    -20.13%
        lev_high    -27.58%     -0.002   -67.48%      22.31%       0.872    -36.82%
         lev_low    -27.58%     -0.002   -67.48%      22.31%       0.872    -36.82%
      lev_medium    -27.58%     -0.002   -67.48%      22.31%       0.872    -36.82%
    ma_crossover     39.81%      0.695   -42.31%       4.35%       0.452    -38.43%
       ma_ribbon     13.64%      0.452   -48.41%      11.63%       0.608    -31.65%
            macd    -27.58%     -0.002   -67.48%      22.31%       0.872    -36.82%
       obv_trend    -15.19%      0.137   -64.72%      16.00%       0.701    -32.99%
    ou_reversion       -inf       -inf      -inf        -inf        -inf       -inf
             ppo    -38.80%     -0.229   -62.27%      19.99%       0.815    -36.82%
             rsi    -14.14%     -0.134   -40.62%      -5.52%      -0.440    -15.64%
      sma_regime    -39.50%     -0.454   -59.69%      15.92%       0.708    -40.14%
      stochastic     38.07%      0.677   -44.79%     -19.07%      -0.804    -25.18%
swing_confluence    -30.60%     -0.167   -57.88%       1.94%       0.341    -34.07%
   trigger_trade      8.79%      0.508    -8.68%      12.20%       2.289     -0.08%
     ts_momentum     25.06%      0.567   -61.55%      -1.62%       0.321    -41.95%
      vol_regime       -inf       -inf      -inf        -inf        -inf       -inf
       voltarget     18.92%      0.506   -47.15%      -2.27%       0.202    -30.72%
  vwap_reversion     -7.95%      0.290   -53.00%       6.78%       0.469    -39.91%
          zscore     37.81%      0.716   -43.03%      -0.72%       0.097    -17.25%

Out-of-sample indicators may warm up from the trailing in-sample bars; reading earlier history is not look-ahead.

------------------------------------------------------------------------------
VERSUS BUY-AND-HOLD BASELINE
------------------------------------------------------------------------------
Baseline buy-and-hold total return: 143.44%
UNDERPERFORMED the baseline:
  adx_trend_14_25          -187.72 pp vs baseline
  atr_sized_14_0.01        -139.48 pp vs baseline
  bb_breakout_20_2         -148.75 pp vs baseline
  bb_reversion_20_2        -121.93 pp vs baseline
  breakout_20_10           -172.69 pp vs baseline
  dca_10x7                 -141.26 pp vs baseline
  dual_momentum_12_1       -200.18 pp vs baseline
  ema_crossover_50_200     -165.63 pp vs baseline
  fib_60_0.382_0.786       -133.39 pp vs baseline
  garch_voltarget_0.94_0.6 -125.36 pp vs baseline
  grid_50_4_0.05           -168.22 pp vs baseline
  hurst_switch_250_0.55_0.45 -143.44 pp vs baseline
  ichimoku_9_26_52         -165.66 pp vs baseline
  keltner_20_14_2          -112.26 pp vs baseline
  lev_high_20x_macd_12_26_9 -154.86 pp vs baseline
  lev_low_2x_macd_12_26_9  -154.86 pp vs baseline
  lev_medium_5x_macd_12_26_9 -154.86 pp vs baseline
  ma_crossover_20_50       -93.27 pp vs baseline
  ma_ribbon_5x10           -116.73 pp vs baseline
  macd_12_26_9             -154.86 pp vs baseline
  obv_trend_20             -145.36 pp vs baseline
  ou_reversion_250_2.5     -126.32 pp vs baseline
  ppo_12_26_9              -166.66 pp vs baseline
  rsi_14_30_50             -162.32 pp vs baseline
  sma_regime_200           -171.41 pp vs baseline
  stoch_14_3               -131.70 pp vs baseline
  swing_20_10_50_2         -172.69 pp vs baseline
  trigger_rsi_lt30+bb_touch_lo_L3 -121.38 pp vs baseline
  ts_momentum_60           -116.88 pp vs baseline
  vol_regime_20_0.5        -159.20 pp vs baseline
  voltarget_100_20_0.6     -126.53 pp vs baseline
  vwap_reversion_20_0.02   -145.15 pp vs baseline
  zscore_20_-2             -106.63 pp vs baseline
No strategy beat simply holding the asset over this period.

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
