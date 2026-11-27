```
==============================================================================
BACKTEST REPORT -- HYPE 1d
==============================================================================
Historical simulation for research and education only. NOT investment advice. Simulated past performance does not predict future results.

Range          : 2024-12-05 .. 2026-11-26  (722 bars)
Mode           : spot
Capital        : 10,000.00 USD
Accounting     : monetary values are in USD; no USD conversion
Costs          : fee 25bps, slippage 2bps
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
                adx_trend_14_25       -27.69%  -15.14%  -0.122   -0.183       -63.99%  -0.237    28.57%           14             25.62%      790.91               0.00                  0      7,231.22
              atr_sized_14_0.01         8.44%    4.19%   0.877    1.411        -6.14%   0.682    92.46%          199              4.32%       64.67               0.00                  0     10,844.17
               bb_breakout_20_2        23.17%   11.13%   0.455    0.737       -41.35%   0.269    30.77%           13             26.04%      794.29               0.00                  0     12,317.38
              bb_reversion_20_2        64.19%   28.53%   0.779    1.227       -41.05%   0.695    58.33%           12             23.13%      927.06               0.00                  0     16,418.74
                 breakout_20_10         4.49%    2.25%   0.324    0.506       -52.72%   0.043    33.33%           12             36.01%      712.58               0.00                  0     10,449.31
                   buy_and_hold       387.54%  123.00%   1.284    2.063       -68.02%   1.808   100.00%            1             99.86%      158.92               0.00                  0     48,754.13
                       dca_10x7       193.01%   72.33%   1.041    1.633       -64.22%   1.126    83.33%           30             95.51%      127.32               0.00                  0     29,300.88
             dual_momentum_12_1       -30.80%  -17.00%   0.085    0.129       -73.31%  -0.232    40.00%           45             51.25%    2,412.03               0.00                  0      6,919.94
           ema_crossover_50_200        41.35%   19.15%   0.592    0.911       -48.88%   0.392    50.00%            2             57.34%      113.95               0.00                  0     14,135.16
             fib_60_0.382_0.786        67.25%   29.74%   0.754    1.163       -36.44%   0.816    55.56%            9             34.07%      618.21               0.00                  0     16,725.24
       garch_voltarget_0.94_0.6        79.10%   34.32%   0.883    1.422       -44.01%   0.780    90.16%          122             39.80%      937.96               0.00                  0     17,909.90
                 grid_50_4_0.05         7.15%    3.56%   0.323    0.480       -47.91%   0.074    51.46%          103             26.80%    1,158.37               0.00                  0     10,714.58
     hurst_switch_250_0.55_0.45         0.00%    0.00%   0.000    0.000         0.00%   0.000     0.00%            0              0.00%        0.00               0.00                  0     10,000.00
               ichimoku_9_26_52        23.80%   11.42%   0.477    0.730       -65.54%   0.174    28.57%           21             48.75%    1,396.96               0.00                  0     12,380.27
                keltner_20_14_2        66.75%   29.54%   0.803    1.323       -33.98%   0.869    44.44%            9             23.13%      796.16               0.00                  0     16,675.06
      lev_high_20x_macd_12_26_9        34.08%   16.01%   0.546    0.896       -62.95%   0.254    23.33%           30             43.21%    1,848.28               0.00                  0     13,408.37
        lev_low_2x_macd_12_26_9        34.08%   16.01%   0.546    0.896       -62.95%   0.254    23.33%           30             43.21%    1,848.28               0.00                  0     13,408.37
     lev_medium_5x_macd_12_26_9        34.08%   16.01%   0.546    0.896       -62.95%   0.254    23.33%           30             43.21%    1,848.28               0.00                  0     13,408.37
             ma_crossover_20_50       166.60%   64.28%   1.074    1.723       -39.91%   1.611    50.00%            6             56.51%      541.61               0.00                  0     26,660.14
                 ma_ribbon_5x10       125.67%   50.99%   0.980    1.532       -42.95%   1.187    68.42%          209             54.10%    1,304.58               0.00                  0     22,567.34
                   macd_12_26_9        34.08%   16.01%   0.546    0.896       -62.95%   0.254    23.33%           30             43.21%    1,848.28               0.00                  0     13,408.37
                   obv_trend_20        38.50%   17.92%   0.572    0.943       -63.29%   0.283    29.09%           55             44.88%    3,403.99               0.00                  0     13,849.85
           ou_reversion_250_2.5        19.33%    9.36%   0.648    1.337        -8.52%   1.098   100.00%            2              1.94%      116.22               0.00                  0     11,933.50
                    ppo_12_26_9        14.47%    7.08%   0.415    0.675       -57.20%   0.124    24.14%           29             41.00%    1,433.59               0.00                  0     11,447.03
                   rsi_14_30_50        -6.96%   -3.58%   0.039    0.057       -38.04%  -0.094    33.33%            3             10.11%      162.79               0.00                  0      9,304.30
                 sma_regime_200        19.10%    9.25%   0.450    0.696       -55.27%   0.167    14.29%            7             53.32%      348.82               0.00                  0     11,909.70
                     stoch_14_3        67.86%   29.98%   0.731    1.166       -39.01%   0.769    53.85%           13             30.75%    1,103.84               0.00                  0     16,785.99
               swing_20_10_50_2         4.49%    2.25%   0.324    0.506       -52.72%   0.043    33.33%           12             36.01%      712.58               0.00                  0     10,449.31
trigger_rsi_lt30+bb_touch_lo_L3        22.91%   11.01%   0.887    1.711        -8.77%   1.255    75.00%            4              1.66%      243.49               0.00                  0     12,290.69
                 ts_momentum_60       111.37%   46.07%   0.898    1.443       -59.06%   0.780    31.25%           16             58.31%    1,533.55               0.00                  0     21,136.79
              vol_regime_20_0.5        16.78%    8.17%   0.393    0.639       -34.23%   0.239    50.00%           14             27.56%      894.50               0.00                  0     11,677.72
           voltarget_100_20_0.6        81.19%   35.11%   0.877    1.409       -45.34%   0.774    89.01%          182             41.39%    1,038.11               0.00                  0     18,119.26
         vwap_reversion_20_0.02        68.54%   30.25%   0.727    1.087       -47.09%   0.642    82.93%           41             44.32%    3,228.70               0.00                  0     16,853.59
                   zscore_20_-2        75.97%   33.12%   0.868    1.386       -41.05%   0.807    63.64%           11             19.53%      840.95               0.00                  0     17,597.14

Gross (zero-cost) comparison, to show cost drag:
                       strategy  total return     cagr  sharpe  max drawdown
-------------------------------  ------------  -------  ------  ------------
                adx_trend_14_25       -19.78%  -10.56%  -0.026       -60.47%
              atr_sized_14_0.01         9.09%    4.50%   0.942        -5.88%
               bb_breakout_20_2        31.12%   14.70%   0.521       -38.85%
              bb_reversion_20_2        73.46%   32.16%   0.850       -40.75%
                 breakout_20_10        11.62%    5.72%   0.378       -50.75%
                   buy_and_hold       389.13%  123.37%   1.286       -67.95%
                       dca_10x7       194.28%   72.71%   1.044       -64.11%
             dual_momentum_12_1        -6.68%   -3.44%   0.257       -63.50%
           ema_crossover_50_200        42.49%   19.63%   0.598       -48.79%
             fib_60_0.382_0.786        73.43%   32.15%   0.794       -36.18%
       garch_voltarget_0.94_0.6        88.48%   37.83%   0.954       -41.98%
                 grid_50_4_0.05        18.73%    9.08%   0.421       -46.92%
     hurst_switch_250_0.55_0.45         0.00%    0.00%   0.000         0.00%
               ichimoku_9_26_52        37.77%   17.61%   0.567       -60.96%
                keltner_20_14_2        74.71%   32.64%   0.862       -31.47%
      lev_high_20x_macd_12_26_9        52.57%   23.84%   0.649       -57.69%
        lev_low_2x_macd_12_26_9        52.57%   23.84%   0.649       -57.69%
     lev_medium_5x_macd_12_26_9        52.57%   23.84%   0.649       -57.69%
             ma_crossover_20_50       172.02%   65.96%   1.095       -39.45%
                 ma_ribbon_5x10       138.72%   55.35%   1.038       -41.13%
                   macd_12_26_9        52.57%   23.84%   0.649       -57.69%
                   obv_trend_20        72.54%   31.80%   0.758       -54.42%
           ou_reversion_250_2.5        20.50%    9.90%   0.680        -8.25%
                    ppo_12_26_9        28.81%   13.67%   0.505       -51.97%
                   rsi_14_30_50        -5.33%   -2.73%   0.065       -37.79%
                 sma_regime_200        22.59%   10.86%   0.471       -53.72%
                     stoch_14_3        78.90%   34.24%   0.790       -37.85%
               swing_20_10_50_2        11.62%    5.72%   0.378       -50.75%
trigger_rsi_lt30+bb_touch_lo_L3        25.34%   12.11%   0.968        -8.21%
                 ts_momentum_60       126.70%   51.34%   0.959       -57.05%
              vol_regime_20_0.5        25.72%   12.29%   0.483       -32.88%
           voltarget_100_20_0.6        91.57%   38.97%   0.950       -43.22%
         vwap_reversion_20_0.02       100.82%   42.33%   0.875       -45.62%
                   zscore_20_-2        84.38%   36.31%   0.931       -40.75%

------------------------------------------------------------------------------
WALK-FORWARD -- in-sample vs out-of-sample (net)
------------------------------------------------------------------------------
        strategy  is return  is sharpe  is maxdd  oos return  oos sharpe  oos maxdd
----------------  ---------  ---------  --------  ----------  ----------  ---------
       adx_trend    -12.38%      0.009   -54.54%     -17.47%      -0.396    -41.87%
       atr_sized      4.45%      0.777    -6.14%       3.80%       1.069     -2.35%
     bb_breakout     -9.07%      0.084   -41.35%      35.45%       1.211    -29.53%
    bb_reversion     68.32%      1.009   -41.05%      -2.45%       0.041    -20.23%
        breakout     -6.87%      0.198   -52.72%      12.20%       0.619    -31.51%
    buy_and_hold    223.48%      1.312   -68.02%      50.38%       1.231    -38.45%
             dca     94.41%      0.974   -64.22%      18.57%       0.755    -38.45%
   dual_momentum    -22.44%      0.110   -70.64%     -10.78%       0.020    -52.67%
   ema_crossover     -6.21%      0.194   -48.88%      50.38%       1.231    -38.45%
 fib_retracement     61.32%      0.936   -36.44%       3.68%       0.390    -29.12%
 garch_voltarget     44.30%      0.867   -44.01%      23.90%       0.933    -20.09%
            grid     12.15%      0.433   -47.91%      -4.47%      -0.151    -18.74%
    hurst_switch       -inf       -inf      -inf        -inf        -inf       -inf
        ichimoku     -6.82%      0.185   -65.54%      32.56%       1.038    -28.71%
         keltner     46.06%      0.826   -33.51%      14.17%       0.747    -20.01%
        lev_high     -2.25%      0.312   -62.95%      37.17%       1.207    -35.45%
         lev_low     -2.25%      0.312   -62.95%      37.17%       1.207    -35.45%
      lev_medium     -2.25%      0.312   -62.95%      37.17%       1.207    -35.45%
    ma_crossover    103.87%      1.117   -39.91%      30.48%       0.983    -28.55%
       ma_ribbon     64.96%      0.902   -42.95%      36.50%       1.151    -28.55%
            macd     -2.25%      0.312   -62.95%      37.17%       1.207    -35.45%
       obv_trend      5.29%      0.376   -63.29%      31.24%       1.008    -32.01%
    ou_reversion       -inf       -inf      -inf        -inf        -inf       -inf
             ppo    -18.68%      0.087   -57.20%      34.92%       1.157    -35.45%
             rsi     -3.40%      0.105   -38.04%      -3.68%      -0.264    -14.48%
      sma_regime    -19.79%     -0.056   -55.27%      48.14%       1.209    -37.12%
      stochastic     85.34%      0.990   -39.01%      -9.43%      -0.280    -21.15%
swing_confluence     -6.87%      0.198   -52.72%      12.20%       0.619    -31.51%
   trigger_trade      9.18%      0.523    -8.77%      12.58%       2.296     -0.27%
     ts_momentum     71.94%      0.930   -59.06%      22.65%       0.833    -32.09%
      vol_regime       -inf       -inf      -inf        -inf        -inf       -inf
       voltarget     49.60%      0.899   -45.34%      20.88%       0.852    -21.11%
  vwap_reversion     35.22%      0.664   -47.09%      24.64%       0.987    -31.33%
          zscore     68.32%      1.009   -41.05%       4.55%       0.404    -14.48%

Out-of-sample indicators may warm up from the trailing in-sample bars; reading earlier history is not look-ahead.

------------------------------------------------------------------------------
VERSUS BUY-AND-HOLD BASELINE
------------------------------------------------------------------------------
Baseline buy-and-hold total return: 387.54%
UNDERPERFORMED the baseline:
  adx_trend_14_25          -415.23 pp vs baseline
  atr_sized_14_0.01        -379.10 pp vs baseline
  bb_breakout_20_2         -364.37 pp vs baseline
  bb_reversion_20_2        -323.35 pp vs baseline
  breakout_20_10           -383.05 pp vs baseline
  dca_10x7                 -194.53 pp vs baseline
  dual_momentum_12_1       -418.34 pp vs baseline
  ema_crossover_50_200     -346.19 pp vs baseline
  fib_60_0.382_0.786       -320.29 pp vs baseline
  garch_voltarget_0.94_0.6 -308.44 pp vs baseline
  grid_50_4_0.05           -380.40 pp vs baseline
  hurst_switch_250_0.55_0.45 -387.54 pp vs baseline
  ichimoku_9_26_52         -363.74 pp vs baseline
  keltner_20_14_2          -320.79 pp vs baseline
  lev_high_20x_macd_12_26_9 -353.46 pp vs baseline
  lev_low_2x_macd_12_26_9  -353.46 pp vs baseline
  lev_medium_5x_macd_12_26_9 -353.46 pp vs baseline
  ma_crossover_20_50       -220.94 pp vs baseline
  ma_ribbon_5x10           -261.87 pp vs baseline
  macd_12_26_9             -353.46 pp vs baseline
  obv_trend_20             -349.04 pp vs baseline
  ou_reversion_250_2.5     -368.21 pp vs baseline
  ppo_12_26_9              -373.07 pp vs baseline
  rsi_14_30_50             -394.50 pp vs baseline
  sma_regime_200           -368.44 pp vs baseline
  stoch_14_3               -319.68 pp vs baseline
  swing_20_10_50_2         -383.05 pp vs baseline
  trigger_rsi_lt30+bb_touch_lo_L3 -364.63 pp vs baseline
  ts_momentum_60           -276.17 pp vs baseline
  vol_regime_20_0.5        -370.76 pp vs baseline
  voltarget_100_20_0.6     -306.35 pp vs baseline
  vwap_reversion_20_0.02   -319.01 pp vs baseline
  zscore_20_-2             -311.57 pp vs baseline
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
