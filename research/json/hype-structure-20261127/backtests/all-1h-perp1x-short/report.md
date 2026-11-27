```
==============================================================================
BACKTEST REPORT -- HYPE 1h
==============================================================================
Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.

Range          : 2026-05-03 .. 2026-11-27  (4999 bars)
Mode           : perp @ 1x
Capital        : 10,000.00 USD
Accounting     : monetary values are in USD; no USD conversion
Costs          : fee 6bps, slippage 2bps
Borrow (max/hr): long 1.6bps, short 0.3bps @ utilization 0.5 (floor 0bps)
                 Borrow fees are charged on notional to BOTH sides and are never negative.
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
                adx_trend_14_25        56.20%  118.50%   1.893    3.133       -23.83%   4.973    73.06%         1158             23.17%    2,151.42           1,431.68                  0     15,619.79
              atr_sized_14_0.01         8.98%   16.27%   0.760    1.233       -12.76%   1.275    81.49%         1010             19.89%    1,085.30             844.48                  0     10,898.18
               bb_breakout_20_2        84.88%  193.62%   2.388    3.890       -17.72%  10.924    76.75%         1445             28.91%    2,208.20           1,804.33                  0     18,488.28
              bb_reversion_20_2       -10.82%  -18.18%  -0.195   -0.275       -32.66%  -0.557    24.26%         1426             28.53%    1,606.22           1,225.84                  0      8,918.07
                 breakout_20_10        -1.02%   -1.79%   0.243    0.371       -40.62%  -0.044    72.53%         1835             36.71%    1,523.31           1,739.50                  0      9,897.71
                   buy_and_hold        23.92%   45.63%   0.865    1.276       -45.39%   1.005    97.62%         4998             99.98%       20.72           3,499.90                  0     12,391.88
                       dca_10x7        21.48%   40.64%   0.825    1.215       -45.45%   0.894    97.14%         4965             99.36%       20.97           3,477.03                  0     12,147.91
             dual_momentum_12_1       -19.75%  -32.00%  -0.335   -0.516       -52.30%  -0.612    63.68%         2470             49.41%    5,770.45           2,152.35                  0      8,024.74
           ema_crossover_50_200        61.47%  131.58%   1.645    2.496       -25.66%   5.127    87.00%         2208             44.17%      214.80           2,171.78                  0     16,146.58
             fib_60_0.382_0.786        -8.41%  -14.26%  -0.118   -0.171       -30.08%  -0.474    49.74%         1516             30.33%    1,056.12           1,258.02                  0      9,159.45
       garch_voltarget_0.94_0.6        14.32%   26.44%   0.685    1.062       -31.62%   0.836    86.84%         2318             46.37%    2,319.43           2,205.54                  0     11,432.29
                 grid_50_4_0.05        -7.58%  -12.90%  -0.580   -0.845       -14.43%  -0.894    19.13%         1307             14.06%      889.10             561.08                  0      9,242.50
     hurst_switch_250_0.55_0.45        12.07%   22.10%   0.891    1.332       -14.24%   1.552    68.68%          265              5.30%    1,078.36             232.02                  0     11,206.57
               ichimoku_9_26_52       -15.84%  -26.08%  -0.236   -0.360       -44.17%  -0.590    80.34%         2019             40.39%    2,343.92           1,731.84                  0      8,416.09
                keltner_20_14_2        27.67%   53.45%   1.214    1.951       -23.81%   2.245    65.42%          992             19.85%    1,103.17           1,004.89                  0     12,767.31
      lev_high_20x_macd_12_26_9        24.14%   46.09%   0.932    1.443       -34.62%   1.331    69.86%         2475             49.51%    3,618.83           2,422.83                  0     12,414.20
        lev_low_2x_macd_12_26_9        24.14%   46.09%   0.932    1.443       -34.62%   1.331    69.86%         2475             49.51%    3,618.83           2,422.83                  0     12,414.20
     lev_medium_5x_macd_12_26_9        24.14%   46.09%   0.932    1.443       -34.62%   1.331    69.86%         2475             49.51%    3,618.83           2,422.83                  0     12,414.20
             ma_crossover_20_50         9.30%   16.86%   0.561    0.842       -33.16%   0.508    71.10%         2415             48.31%    1,052.58           2,310.41                  0     10,929.66
                 ma_ribbon_5x10        -8.38%  -14.22%  -0.007   -0.011       -42.16%  -0.337    69.77%         2491             48.92%    1,670.97           2,211.03                  0      9,162.27
                   macd_12_26_9        24.14%   46.09%   0.932    1.443       -34.62%   1.331    69.86%         2475             49.51%    3,618.83           2,422.83                  0     12,414.20
                   obv_trend_20         0.36%    0.64%   0.313    0.473       -48.58%   0.013    73.99%         2361             47.23%    6,078.16           2,514.05                  0     10,036.22
           ou_reversion_250_2.5       -23.20%  -37.04%  -1.988   -2.801       -30.19%  -1.227    26.56%          418              8.36%      475.76             321.98                  0      7,680.23
                    ppo_12_26_9        12.26%   22.47%   0.636    0.979       -36.64%   0.613    68.90%         2463             49.27%    3,383.08           2,248.84                  0     11,226.25
                   rsi_14_30_50         2.40%    4.25%   0.297    0.426       -23.70%   0.179    27.19%          776             15.52%      530.27             592.63                  0     10,240.38
                 sma_regime_200        56.87%  120.15%   1.580    2.448       -28.61%   4.200    92.69%         2176             43.53%    1,880.97           2,399.92                  0     15,686.86
                     stoch_14_3       -35.42%  -53.53%  -1.410   -1.944       -47.53%  -1.126    21.41%         1462             29.25%    1,064.95           1,057.14                  0      6,457.77
               swing_20_10_50_2         0.92%    1.61%   0.304    0.464       -40.62%   0.040    72.75%         1820             36.41%    1,537.01           1,761.39                  0     10,091.76
trigger_rsi_lt30+bb_touch_lo_L3        23.41%   44.58%   2.260    3.846        -9.10%   4.900    56.67%          180              3.60%    1,003.05             150.03                  0     12,340.92
                 ts_momentum_60       -20.21%  -32.69%  -0.324   -0.497       -49.28%  -0.663    75.99%         2411             48.23%    2,347.18           1,787.72                  0      7,978.57
              vol_regime_20_0.5        -7.69%  -13.08%  -0.199   -0.292       -32.59%  -0.401    67.53%         1121             22.43%    2,089.95           1,019.29                  0      9,231.16
           voltarget_100_20_0.6         4.17%    7.43%   0.381    0.597       -27.24%   0.273    83.92%         1573             35.93%    2,037.80           1,631.96                  0     10,417.43
         vwap_reversion_20_0.02         6.34%   11.37%   0.464    0.668       -26.96%   0.422    32.63%         1327             26.55%    1,623.46           1,175.54                  0     10,633.86
                   zscore_20_-2         2.21%    3.91%   0.312    0.449       -25.19%   0.155    26.51%         1392             27.85%    1,651.91           1,260.18                  0     10,221.43

Gross (zero-cost) comparison, to show cost drag:
                       strategy  total return     cagr  sharpe  max drawdown
-------------------------------  ------------  -------  ------  ------------
                adx_trend_14_25        92.03%  213.80%   2.819       -16.72%
              atr_sized_14_0.01        28.28%   54.73%   2.117        -9.17%
               bb_breakout_20_2       125.01%  314.28%   3.291       -13.21%
              bb_reversion_20_2        17.50%   32.67%   0.887       -19.54%
                 breakout_20_10        31.61%   61.83%   1.203       -28.11%
                   buy_and_hold        59.12%  125.73%   1.435       -36.17%
                       dca_10x7        56.46%  119.14%   1.398       -36.10%
             dual_momentum_12_1        59.48%  126.60%   1.940       -22.06%
           ema_crossover_50_200        85.33%  194.87%   2.110       -21.24%
             fib_60_0.382_0.786        14.74%   27.24%   0.786       -26.75%
       garch_voltarget_0.94_0.6        59.57%  126.84%   1.751       -24.07%
                 grid_50_4_0.05         6.93%   12.46%   0.712        -7.46%
     hurst_switch_250_0.55_0.45        25.17%   48.21%   1.668       -11.87%
               ichimoku_9_26_52        24.92%   47.69%   1.019       -25.73%
                keltner_20_14_2        48.75%  100.58%   1.925       -16.90%
      lev_high_20x_macd_12_26_9        84.56%  192.72%   2.374       -29.27%
        lev_low_2x_macd_12_26_9        84.56%  192.72%   2.374       -29.27%
     lev_medium_5x_macd_12_26_9        84.56%  192.72%   2.374       -29.27%
             ma_crossover_20_50        42.93%   87.01%   1.366       -20.93%
                 ma_ribbon_5x10        30.44%   59.33%   1.198       -24.06%
                   macd_12_26_9        84.56%  192.72%   2.374       -29.27%
                   obv_trend_20        86.28%  197.54%   2.424       -20.06%
           ou_reversion_250_2.5       -15.22%  -25.13%  -1.291       -23.80%
                    ppo_12_26_9        68.58%  149.76%   2.078       -30.01%
                   rsi_14_30_50        13.63%   25.11%   0.818       -20.39%
                 sma_regime_200        99.68%  236.04%   2.409       -20.32%
                     stoch_14_3       -14.20%  -23.54%  -0.437       -31.56%
               swing_20_10_50_2        33.90%   66.81%   1.263       -28.15%
trigger_rsi_lt30+bb_touch_lo_L3        34.94%   69.08%   3.336        -6.96%
                 ts_momentum_60        21.13%   39.94%   0.892       -39.98%
              vol_regime_20_0.5        23.40%   44.57%   1.268       -18.84%
           voltarget_100_20_0.6        40.87%   82.32%   1.750       -15.21%
         vwap_reversion_20_0.02        34.33%   67.74%   1.391       -20.10%
                   zscore_20_-2        31.34%   61.25%   1.368       -17.90%

------------------------------------------------------------------------------
WALK-FORWARD -- in-sample vs out-of-sample (net)
------------------------------------------------------------------------------
        strategy  is return  is sharpe  is maxdd  oos return  oos sharpe  oos maxdd
----------------  ---------  ---------  --------  ----------  ----------  ---------
       adx_trend     88.75%      3.257   -20.37%     -17.25%      -3.766    -18.13%
       atr_sized     17.35%      1.749   -12.76%      -7.13%      -2.028     -9.68%
     bb_breakout     92.28%      3.255   -17.49%      -3.85%      -0.419    -17.72%
    bb_reversion      8.93%      0.711   -20.65%     -18.13%      -1.893    -26.50%
        breakout     34.16%      1.504   -34.84%     -26.22%      -4.353    -32.47%
    buy_and_hold     84.86%      2.176   -37.24%     -38.04%      -3.169    -46.70%
             dca     81.43%      2.126   -37.30%     -37.97%      -3.177    -46.62%
   dual_momentum     10.94%      0.721   -34.00%     -27.66%      -3.903    -33.95%
   ema_crossover     69.18%      2.215   -25.66%      -3.72%      -0.363    -16.20%
 fib_retracement      8.93%      0.686   -30.08%     -15.91%      -2.574    -23.96%
 garch_voltarget     46.33%      1.740   -31.32%     -21.87%      -2.870    -27.83%
            grid      0.21%      0.126    -8.47%      -7.79%      -2.093    -12.01%
    hurst_switch     14.97%      1.437    -9.47%      -2.53%      -0.474    -14.24%
        ichimoku     17.79%      0.961   -29.50%     -28.55%      -4.434    -32.40%
         keltner     46.46%      2.255   -16.65%     -12.83%      -2.609    -20.26%
        lev_high     44.01%      1.757   -34.62%     -13.44%      -1.448    -24.51%
         lev_low     44.01%      1.757   -34.62%     -13.44%      -1.448    -24.51%
      lev_medium     44.01%      1.757   -34.62%     -13.44%      -1.448    -24.51%
    ma_crossover     35.23%      1.434   -26.73%     -19.18%      -2.297    -25.20%
       ma_ribbon     25.08%      1.239   -32.04%     -26.75%      -4.130    -31.29%
            macd     44.01%      1.757   -34.62%     -13.44%      -1.448    -24.51%
       obv_trend     47.90%      1.810   -34.23%     -32.14%      -4.686    -35.36%
    ou_reversion     -4.75%     -0.724   -13.44%     -19.37%      -3.667    -19.98%
             ppo     33.29%      1.454   -35.68%     -15.71%      -1.801    -27.42%
             rsi     -6.72%     -0.353   -23.70%       9.78%       1.482    -10.41%
      sma_regime     79.09%      2.449   -28.61%     -12.41%      -1.739    -22.29%
      stochastic     -9.37%     -0.331   -32.24%     -28.75%      -3.596    -32.36%
swing_confluence     36.79%      1.586   -34.84%     -26.22%      -4.353    -32.47%
   trigger_trade     -1.90%     -0.330    -9.10%      25.80%       5.577     -4.45%
     ts_momentum      1.32%      0.385   -49.28%     -21.25%      -2.723    -25.44%
      vol_regime     10.04%      0.789   -17.78%     -16.11%      -4.226    -18.89%
       voltarget     26.78%      1.513   -21.57%     -17.83%      -2.968    -20.68%
  vwap_reversion     15.46%      0.998   -21.63%      -7.90%      -0.672    -26.96%
          zscore     15.91%      1.080   -19.23%     -11.81%      -1.148    -21.94%

Out-of-sample indicators may warm up from the trailing in-sample bars; reading earlier history is not look-ahead.

------------------------------------------------------------------------------
VERSUS BUY-AND-HOLD BASELINE
------------------------------------------------------------------------------
Baseline buy-and-hold total return: 23.92%
UNDERPERFORMED the baseline:
  atr_sized_14_0.01        -14.94 pp vs baseline
  bb_reversion_20_2        -34.74 pp vs baseline
  breakout_20_10           -24.94 pp vs baseline
  dca_10x7                 -2.44 pp vs baseline
  dual_momentum_12_1       -43.67 pp vs baseline
  fib_60_0.382_0.786       -32.32 pp vs baseline
  garch_voltarget_0.94_0.6 -9.60 pp vs baseline
  grid_50_4_0.05           -31.49 pp vs baseline
  hurst_switch_250_0.55_0.45 -11.85 pp vs baseline
  ichimoku_9_26_52         -39.76 pp vs baseline
  ma_crossover_20_50       -14.62 pp vs baseline
  ma_ribbon_5x10           -32.30 pp vs baseline
  obv_trend_20             -23.56 pp vs baseline
  ou_reversion_250_2.5     -47.12 pp vs baseline
  ppo_12_26_9              -11.66 pp vs baseline
  rsi_14_30_50             -21.51 pp vs baseline
  stoch_14_3               -59.34 pp vs baseline
  swing_20_10_50_2         -23.00 pp vs baseline
  trigger_rsi_lt30+bb_touch_lo_L3 -0.51 pp vs baseline
  ts_momentum_60           -44.13 pp vs baseline
  vol_regime_20_0.5        -31.61 pp vs baseline
  voltarget_100_20_0.6     -19.74 pp vs baseline
  vwap_reversion_20_0.02   -17.58 pp vs baseline
  zscore_20_-2             -21.70 pp vs baseline
Outperformed the baseline:
  adx_trend_14_25          +32.28 pp vs baseline
  bb_breakout_20_2         +60.96 pp vs baseline
  ema_crossover_50_200     +37.55 pp vs baseline
  keltner_20_14_2          +3.75 pp vs baseline
  lev_high_20x_macd_12_26_9 +0.22 pp vs baseline
  lev_low_2x_macd_12_26_9  +0.22 pp vs baseline
  lev_medium_5x_macd_12_26_9 +0.22 pp vs baseline
  macd_12_26_9             +0.22 pp vs baseline
  sma_regime_200           +32.95 pp vs baseline

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
