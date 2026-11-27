```
==============================================================================
BACKTEST REPORT -- HYPE 1d
==============================================================================
Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.

Range          : 2024-12-05 .. 2026-11-26  (722 bars)
Mode           : spot
Capital        : 10,000.00 USD
Accounting     : monetary values are in USD; no USD conversion
Costs          : fee 6bps, slippage 2bps
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
                adx_trend_14_25       -23.74%  -12.82%  -0.064   -0.096       -62.53%  -0.205    28.57%           14             25.62%      239.99               0.00                  0      7,626.34
              atr_sized_14_0.01         8.91%    4.42%   0.922    1.488        -5.96%   0.740    92.96%          199              4.32%       19.20               0.00                  0     10,891.17
               bb_breakout_20_2        29.41%   13.94%   0.506    0.821       -40.03%   0.348    30.77%           13             26.04%      241.50               0.00                  0     12,941.14
              bb_reversion_20_2        71.85%   31.53%   0.830    1.311       -41.05%   0.768    58.33%           12             23.13%      281.71               0.00                  0     17,184.77
                 breakout_20_10         9.37%    4.64%   0.364    0.569       -51.81%   0.090    33.33%           12             36.01%      216.09               0.00                  0     10,936.83
                   buy_and_hold       389.40%  123.43%   1.286    2.066       -68.02%   1.814   100.00%            1             99.86%       47.18               0.00                  0     48,939.74
                       dca_10x7       194.46%   72.76%   1.044    1.637       -64.22%   1.133    83.33%           30             95.51%       37.82               0.00                  0     29,446.12
             dual_momentum_12_1       -17.90%   -9.50%   0.208    0.316       -70.09%  -0.136    42.22%           45             51.25%      772.04               0.00                  0      8,210.44
           ema_crossover_50_200        42.43%   19.61%   0.598    0.920       -48.88%   0.401    50.00%            2             57.34%       33.90               0.00                  0     14,242.99
             fib_60_0.382_0.786        73.07%   32.01%   0.786    1.215       -36.32%   0.881    55.56%            9             34.07%      186.82               0.00                  0     17,307.14
       garch_voltarget_0.94_0.6        86.90%   37.25%   0.932    1.504       -43.01%   0.866    90.98%          122             39.80%      284.26               0.00                  0     18,690.31
                 grid_50_4_0.05        15.49%    7.56%   0.397    0.592       -47.75%   0.158    53.40%          103             26.80%      356.74               0.00                  0     11,549.25
     hurst_switch_250_0.55_0.45         0.00%    0.00%   0.000    0.000         0.00%   0.000     0.00%            0              0.00%        0.00               0.00                  0     10,000.00
               ichimoku_9_26_52        34.09%   16.01%   0.544    0.835       -63.65%   0.251    33.33%           21             48.75%      429.67               0.00                  0     13,408.71
                keltner_20_14_2        72.55%   31.81%   0.842    1.390       -32.46%   0.980    44.44%            9             23.13%      239.98               0.00                  0     17,255.21
      lev_high_20x_macd_12_26_9        50.27%   22.90%   0.634    1.045       -61.00%   0.375    23.33%           30             43.21%      579.96               0.00                  0     15,027.47
        lev_low_2x_macd_12_26_9        50.27%   22.90%   0.634    1.045       -61.00%   0.375    23.33%           30             43.21%      579.96               0.00                  0     15,027.47
     lev_medium_5x_macd_12_26_9        50.27%   22.90%   0.634    1.045       -61.00%   0.375    23.33%           30             43.21%      579.96               0.00                  0     15,027.47
             ma_crossover_20_50       172.75%   66.19%   1.092    1.752       -39.68%   1.668    50.00%            6             56.51%      162.71               0.00                  0     27,274.98
                 ma_ribbon_5x10       138.43%   55.25%   1.026    1.607       -42.20%   1.309    70.33%          209             54.10%      399.03               0.00                  0     23,842.85
                   macd_12_26_9        50.27%   22.90%   0.634    1.045       -61.00%   0.375    23.33%           30             43.21%      579.96               0.00                  0     15,027.47
                   obv_trend_20        70.69%   31.09%   0.732    1.215       -60.17%   0.517    30.91%           55             44.88%    1,129.72               0.00                  0     17,069.19
           ou_reversion_250_2.5        20.25%    9.78%   0.671    1.408        -8.35%   1.172   100.00%            2              1.94%       34.57               0.00                  0     12,024.54
                    ppo_12_26_9        27.81%   13.22%   0.504    0.823       -55.29%   0.239    24.14%           29             41.00%      448.86               0.00                  0     12,780.63
                   rsi_14_30_50        -5.89%   -3.03%   0.057    0.085       -38.04%  -0.080    33.33%            3             10.11%       48.50               0.00                  0      9,410.98
                 sma_regime_200        22.31%   10.73%   0.471    0.730       -54.41%   0.197    14.29%            7             53.32%      104.79               0.00                  0     12,230.75
                     stoch_14_3        76.36%   33.27%   0.773    1.235       -38.78%   0.858    61.54%           13             30.75%      336.08               0.00                  0     17,636.05
               swing_20_10_50_2         9.37%    4.64%   0.364    0.569       -51.81%   0.090    33.33%           12             36.01%      216.09               0.00                  0     10,936.83
trigger_rsi_lt30+bb_touch_lo_L3        24.79%   11.86%   0.945    1.864        -8.43%   1.408    75.00%            4              1.66%       72.71               0.00                  0     12,478.93
                 ts_momentum_60       124.62%   50.63%   0.944    1.520       -58.28%   0.869    31.25%           16             58.31%      470.47               0.00                  0     22,461.78
              vol_regime_20_0.5        23.16%   11.12%   0.456    0.744       -33.48%   0.332    50.00%           14             27.56%      272.67               0.00                  0     12,315.80
           voltarget_100_20_0.6        89.71%   38.29%   0.927    1.493       -44.33%   0.864    90.00%          180             41.38%      315.07               0.00                  0     18,971.34
         vwap_reversion_20_0.02        96.95%   40.93%   0.843    1.266       -46.89%   0.873    82.93%           41             44.32%    1,044.69               0.00                  0     19,694.99
                   zscore_20_-2        83.48%   35.97%   0.915    1.467       -41.05%   0.876    63.64%           11             19.53%      255.05               0.00                  0     18,348.29

Gross (zero-cost) comparison, to show cost drag:
                       strategy  total return     cagr  sharpe  max drawdown
-------------------------------  ------------  -------  ------  ------------
                adx_trend_14_25       -21.34%  -11.44%  -0.036       -61.46%
              atr_sized_14_0.01         9.10%    4.51%   0.942        -5.89%
               bb_breakout_20_2        31.83%   15.01%   0.526       -39.41%
              bb_reversion_20_2        74.66%   32.62%   0.851       -40.96%
                 breakout_20_10        11.53%    5.68%   0.380       -51.22%
                   buy_and_hold       389.87%  123.54%   1.287       -68.00%
                       dca_10x7       194.84%   72.87%   1.045       -64.19%
             dual_momentum_12_1       -10.18%   -5.29%   0.258       -67.04%
           ema_crossover_50_200        42.77%   19.75%   0.599       -48.85%
             fib_60_0.382_0.786        74.94%   32.73%   0.798       -36.24%
       garch_voltarget_0.94_0.6        89.75%   38.30%   0.953       -42.40%
                 grid_50_4_0.05        19.06%    9.23%   0.426       -47.46%
     hurst_switch_250_0.55_0.45         0.00%    0.00%   0.000         0.00%
               ichimoku_9_26_52        38.38%   17.88%   0.571       -62.27%
                keltner_20_14_2        74.95%   32.73%   0.860       -31.71%
      lev_high_20x_macd_12_26_9        56.07%   25.28%   0.664       -59.41%
        lev_low_2x_macd_12_26_9        56.07%   25.28%   0.664       -59.41%
     lev_medium_5x_macd_12_26_9        56.07%   25.28%   0.664       -59.41%
             ma_crossover_20_50       174.38%   66.69%   1.098       -39.55%
                 ma_ribbon_5x10       142.42%   56.56%   1.043       -41.65%
                   macd_12_26_9        56.07%   25.28%   0.664       -59.41%
                   obv_trend_20        81.99%   35.41%   0.787       -57.44%
           ou_reversion_250_2.5        20.59%    9.94%   0.680        -8.27%
                    ppo_12_26_9        32.29%   15.22%   0.531       -53.71%
                   rsi_14_30_50        -5.41%   -2.77%   0.065       -37.96%
                 sma_regime_200        23.36%   11.21%   0.478       -53.95%
                     stoch_14_3        79.72%   34.55%   0.790       -38.43%
               swing_20_10_50_2        11.53%    5.68%   0.380       -51.22%
trigger_rsi_lt30+bb_touch_lo_L3        25.52%   12.19%   0.969        -8.26%
                 ts_momentum_60       129.32%   52.22%   0.963       -57.68%
              vol_regime_20_0.5        25.88%   12.36%   0.483       -33.07%
           voltarget_100_20_0.6        92.86%   39.45%   0.949       -43.70%
         vwap_reversion_20_0.02       107.40%   44.67%   0.887       -46.45%
                   zscore_20_-2        86.03%   36.92%   0.934       -40.96%

------------------------------------------------------------------------------
WALK-FORWARD -- in-sample vs out-of-sample (net)
------------------------------------------------------------------------------
        strategy  is return  is sharpe  is maxdd  oos return  oos sharpe  oos maxdd
----------------  ---------  ---------  --------  ----------  ----------  ---------
       adx_trend     -9.33%      0.064   -53.23%     -15.89%      -0.333    -41.32%
       atr_sized      4.77%      0.830    -5.96%       3.97%       1.115     -2.33%
     bb_breakout     -5.90%      0.137   -40.03%      37.53%       1.259    -28.85%
    bb_reversion     73.51%      1.053   -41.05%      -0.96%       0.119    -19.62%
        breakout     -3.99%      0.236   -51.81%      13.92%       0.663    -30.86%
    buy_and_hold    224.72%      1.314   -68.02%      50.95%       1.239    -38.45%
             dca     95.38%      0.978   -64.22%      19.13%       0.767    -38.45%
   dual_momentum    -11.74%      0.239   -68.08%      -6.97%       0.129    -52.13%
   ema_crossover     -5.50%      0.204   -48.88%      50.95%       1.239    -38.45%
 fib_retracement     65.67%      0.974   -36.32%       4.47%       0.412    -29.12%
 garch_voltarget     48.67%      0.922   -43.01%      25.89%       0.983    -19.57%
            grid     18.41%      0.499   -47.75%      -2.47%      -0.020    -18.46%
    hurst_switch       -inf       -inf      -inf        -inf        -inf       -inf
        ichimoku     -0.98%      0.264   -63.65%      35.62%       1.094    -28.55%
         keltner     49.43%      0.862   -32.10%      15.48%       0.792    -19.86%
        lev_high      5.87%      0.396   -61.00%      41.94%       1.308    -34.71%
         lev_low      5.87%      0.396   -61.00%      41.94%       1.308    -34.71%
      lev_medium      5.87%      0.396   -61.00%      41.94%       1.308    -34.71%
    ma_crossover    107.78%      1.138   -39.68%      31.47%       1.001    -28.55%
       ma_ribbon     71.61%      0.949   -42.20%      39.15%       1.203    -28.55%
            macd      5.87%      0.396   -61.00%      41.94%       1.308    -34.71%
       obv_trend     20.73%      0.527   -60.17%      41.60%       1.198    -30.97%
    ou_reversion       -inf       -inf      -inf        -inf        -inf       -inf
             ppo    -11.93%      0.176   -55.29%      39.08%       1.247    -34.71%
             rsi     -2.67%      0.121   -38.04%      -3.31%      -0.225    -14.48%
      sma_regime    -17.94%     -0.025   -54.41%      49.27%       1.224    -36.76%
      stochastic     91.79%      1.027   -38.78%      -8.05%      -0.210    -20.85%
swing_confluence     -3.99%      0.236   -51.81%      13.92%       0.663    -30.86%
   trigger_trade     10.01%      0.563    -8.43%      13.44%       2.387     -0.08%
     ts_momentum     77.92%      0.969   -58.28%      26.44%       0.904    -30.13%
      vol_regime       -inf       -inf      -inf        -inf        -inf       -inf
       voltarget     54.53%      0.955   -44.33%      22.93%       0.903    -20.62%
  vwap_reversion     50.97%      0.771   -46.89%      30.46%       1.141    -30.54%
          zscore     73.51%      1.053   -41.05%       5.74%       0.470    -14.48%

Out-of-sample indicators may warm up from the trailing in-sample bars; reading earlier history is not look-ahead.

------------------------------------------------------------------------------
VERSUS BUY-AND-HOLD BASELINE
------------------------------------------------------------------------------
Baseline buy-and-hold total return: 389.40%
UNDERPERFORMED the baseline:
  adx_trend_14_25          -413.13 pp vs baseline
  atr_sized_14_0.01        -380.49 pp vs baseline
  bb_breakout_20_2         -359.99 pp vs baseline
  bb_reversion_20_2        -317.55 pp vs baseline
  breakout_20_10           -380.03 pp vs baseline
  dca_10x7                 -194.94 pp vs baseline
  dual_momentum_12_1       -407.29 pp vs baseline
  ema_crossover_50_200     -346.97 pp vs baseline
  fib_60_0.382_0.786       -316.33 pp vs baseline
  garch_voltarget_0.94_0.6 -302.49 pp vs baseline
  grid_50_4_0.05           -373.90 pp vs baseline
  hurst_switch_250_0.55_0.45 -389.40 pp vs baseline
  ichimoku_9_26_52         -355.31 pp vs baseline
  keltner_20_14_2          -316.85 pp vs baseline
  lev_high_20x_macd_12_26_9 -339.12 pp vs baseline
  lev_low_2x_macd_12_26_9  -339.12 pp vs baseline
  lev_medium_5x_macd_12_26_9 -339.12 pp vs baseline
  ma_crossover_20_50       -216.65 pp vs baseline
  ma_ribbon_5x10           -250.97 pp vs baseline
  macd_12_26_9             -339.12 pp vs baseline
  obv_trend_20             -318.71 pp vs baseline
  ou_reversion_250_2.5     -369.15 pp vs baseline
  ppo_12_26_9              -361.59 pp vs baseline
  rsi_14_30_50             -395.29 pp vs baseline
  sma_regime_200           -367.09 pp vs baseline
  stoch_14_3               -313.04 pp vs baseline
  swing_20_10_50_2         -380.03 pp vs baseline
  trigger_rsi_lt30+bb_touch_lo_L3 -364.61 pp vs baseline
  ts_momentum_60           -264.78 pp vs baseline
  vol_regime_20_0.5        -366.24 pp vs baseline
  voltarget_100_20_0.6     -299.68 pp vs baseline
  vwap_reversion_20_0.02   -292.45 pp vs baseline
  zscore_20_-2             -305.91 pp vs baseline
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
