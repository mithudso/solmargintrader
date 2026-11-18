# Original versus DSO candidate

Research output, not investment advice; simulation only.

136 holdout strategy/dataset pairs; 2 changed accuracy or net return; 0 failed pairs.

All results are exploratory historical comparisons, not proof of a live edge. The final chronological 30% is a temporal holdout in this run. Previously researched data is not a fresh independent confirmation set. No parameter search or promotion runs.

Accuracy is active long/short signal(t) versus sign(close/open - 1) at t+1. Flat signals abstain; flat outcomes count as misses. Coverage and majority baseline use identical eligible timestamps. This one-bar diagnostic is distinct from holding-period strategy returns and net realized trade-event win rate. Accuracy differences may use different active timestamps; inspect counts/coverage before comparing percentages.

The common current engine applies costs, next-open fills, and terminal liquidation. Each split starts with fresh capital and no position. Stateful signals are primed on prefix history; no working-set trade crosses the split. Leverage tiers use perp mode and borrow/liquidation costs. Engine win rate counts realized events (including partial resizes), not independent round trips. Fewer than 30 active calls or realized events is insufficient evidence. Even above 30, serial dependence is not corrected.

| Dataset | Strategy | Accuracy old → new | Net return old → new | Sharpe old → new | Trades old → new |
|---|---|---:|---:|---:|---:|
| SOL_1d | adx_trend | 45.76% → 45.76% | -23.96% → -23.96% | -0.383 → -0.383 | 9 → 9 |
| SOL_1d | atr_sized | 51.50% → 51.50% | 2.22% → 2.22% | 0.324 → 0.324 | 117 → 117 |
| SOL_1d | bb_breakout | 50.31% → 50.31% | -8.20% → -8.20% | -0.033 → -0.033 | 12 → 12 |
| SOL_1d | bb_reversion | 47.75% → 47.75% | -4.65% → -4.65% | 0.161 → 0.161 | 11 → 11 |
| SOL_1d | breakout | 50.23% → 50.23% | 7.83% → 7.83% | 0.309 → 0.309 | 9 → 9 |
| SOL_1d | buy_and_hold | 48.82% → 48.82% | -35.36% → -35.36% | -0.045 → -0.045 | 1 → 1 |
| SOL_1d | dca | 48.82% → 48.82% | -35.36% → -35.36% | -0.045 → -0.045 | 1 → 1 |
| SOL_1d | dual_momentum | 48.10% → 48.10% | -51.45% → -51.45% | -0.746 → -0.746 | 39 → 39 |
| SOL_1d | ema_crossover | 49.42% → 49.42% | -41.22% → -41.22% | -0.596 → -0.596 | 2 → 2 |
| SOL_1d | fib_retracement | 51.18% → 51.18% | 20.27% → 20.27% | 0.483 → 0.483 | 8 → 8 |
| SOL_1d | garch_voltarget | 51.50% → 51.50% | -1.94% → -1.94% | 0.159 → 0.159 | 60 → 60 |
| SOL_1d | grid | 47.60% → 47.60% | -27.67% → -27.67% | -0.265 → -0.265 | 120 → 120 |
| SOL_1d | hurst_switch | 52.94% → 52.94% | 15.57% → 15.57% | 0.550 → 0.550 | 10 → 10 |
| SOL_1d | ichimoku | 51.02% → 51.02% | 3.32% → 3.32% | 0.251 → 0.251 | 13 → 13 |
| SOL_1d | keltner | 51.02% → 51.02% | -2.65% → -2.65% | 0.054 → 0.054 | 7 → 7 |
| SOL_1d | lev_high | 50.97% → 50.97% | -100.00% → -100.00% | -0.786 → -0.786 | 1 → 1 |
| SOL_1d | lev_low | 50.97% → 50.97% | -74.38% → -74.38% | -0.487 → -0.487 | 112 → 112 |
| SOL_1d | lev_medium | 50.97% → 50.97% | -99.66% → -99.66% | -0.499 → -0.499 | 95 → 95 |
| SOL_1d | ma_crossover | 48.60% → 48.60% | -34.62% → -34.62% | -0.343 → -0.343 | 7 → 7 |
| SOL_1d | ma_ribbon | 48.18% → 48.18% | -38.87% → -38.87% | -0.560 → -0.560 | 179 → 179 |
| SOL_1d | macd | 50.97% → 50.97% | 3.26% → 3.26% | 0.273 → 0.273 | 21 → 21 |
| SOL_1d | obv_trend | 47.64% → 47.64% | -36.32% → -36.32% | -0.379 → -0.379 | 37 → 37 |
| SOL_1d | ou_reversion | 47.76% → 47.76% | 20.26% → 20.26% | 0.557 → 0.557 | 6 → 6 |
| SOL_1d | ppo | 50.84% → 50.84% | -4.46% → -4.46% | 0.166 → 0.166 | 21 → 21 |
| SOL_1d | rsi | 43.75% → 43.75% | -30.99% → -30.99% | -0.484 → -0.484 | 4 → 4 |
| SOL_1d | sma_regime | 51.83% → 51.83% | -5.82% → -5.82% | 0.122 → 0.122 | 4 → 4 |
| SOL_1d | stochastic | 46.67% → 46.67% | -24.87% → -24.87% | -0.181 → -0.181 | 10 → 10 |
| SOL_1d | swing_confluence | 50.23% → 50.23% | 7.83% → 7.83% | 0.309 → 0.309 | 9 → 9 |
| SOL_1d | trigger_trade | 40.74% → 40.74% | -23.43% → -23.43% | -0.691 → -0.691 | 5 → 5 |
| SOL_1d | ts_momentum | 49.64% → 49.64% | -15.79% → -15.79% | 0.000 → 0.000 | 22 → 22 |
| SOL_1d | vol_regime | 50.35% → 50.35% | -1.98% → -1.98% | 0.126 → 0.126 | 18 → 18 |
| SOL_1d | voltarget | 51.50% → 51.50% | -4.24% → -4.24% | 0.123 → 0.123 | 89 → 89 |
| SOL_1d | vwap_reversion | 48.74% → 48.74% | -38.52% → -38.52% | -0.326 → -0.326 | 24 → 24 |
| SOL_1d | zscore | 48.28% → 48.28% | 5.80% → 5.80% | 0.298 → 0.298 | 11 → 11 |
| BTC_1d | adx_trend | 47.55% → 47.55% | -4.52% → -4.52% | -0.072 → -0.072 | 8 → 8 |
| BTC_1d | atr_sized | 49.65% → 49.65% | 1.04% → 1.04% | 0.156 → 0.156 | 123 → 123 |
| BTC_1d | bb_breakout | 46.10% → 46.10% | -15.87% → -15.87% | -0.484 → -0.484 | 12 → 12 |
| BTC_1d | bb_reversion | 47.90% → 47.90% | -6.83% → -6.83% | -0.018 → -0.018 | 13 → 13 |
| BTC_1d | breakout | 49.13% → 49.13% | -4.98% → -4.98% | -0.030 → -0.030 | 9 → 9 |
| BTC_1d | buy_and_hold | 49.22% → 49.22% | -22.70% → -22.70% | -0.124 → -0.124 | 1 → 1 |
| BTC_1d | dca | 49.22% → 49.22% | -22.70% → -22.70% | -0.124 → -0.124 | 1 → 1 |
| BTC_1d | dual_momentum | 48.54% → 48.54% | -25.45% → -25.45% | -0.535 → -0.535 | 45 → 45 |
| BTC_1d | ema_crossover | 50.15% → 50.15% | -8.00% → -8.00% | -0.006 → -0.006 | 2 → 2 |
| BTC_1d | fib_retracement | 48.26% → 48.26% | -10.99% → -10.99% | -0.216 → -0.216 | 8 → 8 |
| BTC_1d | garch_voltarget | 49.65% → 49.65% | 0.29% → 0.29% | 0.122 → 0.122 | 14 → 14 |
| BTC_1d | grid | 46.91% → 46.91% | -15.55% → -15.55% | -0.263 → -0.263 | 144 → 144 |
| BTC_1d | hurst_switch | 53.33% → 53.33% | -1.59% → -1.59% | -0.045 → -0.045 | 9 → 9 |
| BTC_1d | ichimoku | 53.88% → 53.88% | 36.73% → 36.73% | 0.940 → 0.940 | 7 → 7 |
| BTC_1d | keltner | 46.02% → 46.02% | -5.31% → -5.31% | -0.126 → -0.126 | 7 → 7 |
| BTC_1d | lev_high | 50.31% → 50.31% | -100.00% → -100.00% | -3.651 → -3.651 | 4 → 4 |
| BTC_1d | lev_low | 50.31% → 50.31% | -76.26% → -76.26% | -1.227 → -1.227 | 145 → 145 |
| BTC_1d | lev_medium | 50.31% → 50.31% | -98.82% → -98.82% | -1.271 → -1.271 | 123 → 123 |
| BTC_1d | ma_crossover | 50.29% → 50.29% | 14.34% → 14.34% | 0.421 → 0.421 | 9 → 9 |
| BTC_1d | ma_ribbon | 50.10% → 50.10% | -12.89% → -12.89% | -0.234 → -0.234 | 193 → 193 |
| BTC_1d | macd | 50.31% → 50.31% | -5.39% → -5.39% | 0.023 → 0.023 | 26 → 26 |
| BTC_1d | obv_trend | 48.19% → 48.19% | -9.55% → -9.55% | -0.086 → -0.086 | 38 → 38 |
| BTC_1d | ou_reversion | undefined → undefined | 0.00% → 0.00% | 0.000 → 0.000 | 0 → 0 |
| BTC_1d | ppo | 50.32% → 50.32% | -11.37% → -11.37% | -0.122 → -0.122 | 24 → 24 |
| BTC_1d | rsi | 44.83% → 44.83% | -8.96% → -8.96% | -0.104 → -0.104 | 4 → 4 |
| BTC_1d | sma_regime | 49.36% → 49.36% | -13.41% → -13.41% | -0.165 → -0.165 | 10 → 10 |
| BTC_1d | stochastic | 48.70% → 48.70% | -15.55% → -15.55% | -0.156 → -0.156 | 11 → 11 |
| BTC_1d | swing_confluence | 49.13% → 49.13% | -4.98% → -4.98% | -0.030 → -0.030 | 9 → 9 |
| BTC_1d | trigger_trade | 33.33% → 33.33% | -22.73% → -22.73% | -0.649 → -0.649 | 4 → 4 |
| BTC_1d | ts_momentum | 50.33% → 50.33% | 1.51% → 1.51% | 0.159 → 0.159 | 13 → 13 |
| BTC_1d | vol_regime | 50.86% → 50.86% | 8.42% → 8.42% | 0.332 → 0.332 | 15 → 15 |
| BTC_1d | voltarget | 49.65% → 49.65% | 0.21% → 0.21% | 0.120 → 0.120 | 16 → 16 |
| BTC_1d | vwap_reversion | 51.22% → 51.22% | -2.91% → -2.91% | 0.112 → 0.112 | 29 → 29 |
| BTC_1d | zscore | 47.90% → 47.90% | -6.83% → -6.83% | -0.018 → -0.018 | 13 → 13 |
| ETH_1d | adx_trend | 52.60% → 52.60% | -3.16% → -3.16% | 0.086 → 0.086 | 10 → 10 |
| ETH_1d | atr_sized | 51.84% → 51.84% | 6.01% → 6.01% | 0.678 → 0.678 | 125 → 125 |
| ETH_1d | bb_breakout | 47.95% → 47.95% | 0.29% → 0.29% | 0.170 → 0.170 | 13 → 13 |
| ETH_1d | bb_reversion | 47.52% → 47.52% | -45.39% → -45.39% | -0.577 → -0.577 | 10 → 10 |
| ETH_1d | breakout | 47.51% → 47.51% | -40.44% → -40.44% | -0.655 → -0.655 | 12 → 12 |
| ETH_1d | buy_and_hold | 50.47% → 50.47% | -18.45% → -18.45% | 0.171 → 0.171 | 1 → 1 |
| ETH_1d | dca | 50.47% → 50.47% | -18.45% → -18.45% | 0.171 → 0.171 | 1 → 1 |
| ETH_1d | dual_momentum | 49.52% → 49.52% | -12.41% → -12.41% | 0.060 → 0.060 | 50 → 50 |
| ETH_1d | ema_crossover | 50.95% → 50.95% | -13.29% → -13.29% | -0.044 → -0.044 | 3 → 3 |
| ETH_1d | fib_retracement | 50.00% → 50.00% | 6.39% → 6.39% | 0.292 → 0.292 | 6 → 6 |
| ETH_1d | garch_voltarget | 51.84% → 51.84% | 36.45% → 36.45% | 0.661 → 0.661 | 48 → 48 |
| ETH_1d | grid | 48.21% → 48.21% | -49.13% → -49.13% | -0.666 → -0.666 | 111 → 111 |
| ETH_1d | hurst_switch | 30.00% → 30.00% | -15.72% → -15.72% | -1.066 → -1.066 | 4 → 4 |
| ETH_1d | ichimoku | 52.99% → 52.99% | 54.05% → 54.05% | 0.846 → 0.846 | 10 → 10 |
| ETH_1d | keltner | 50.86% → 50.86% | 2.49% → 2.49% | 0.181 → 0.181 | 7 → 7 |
| ETH_1d | lev_high | 49.68% → 49.68% | -100.00% → -100.00% | -0.955 → -0.955 | 3 → 3 |
| ETH_1d | lev_low | 49.68% → 49.68% | -80.19% → -80.19% | -0.552 → -0.552 | 111 → 111 |
| ETH_1d | lev_medium | 49.68% → 49.68% | -99.94% → -99.94% | -0.696 → -0.696 | 99 → 99 |
| ETH_1d | ma_crossover | 51.48% → 51.48% | 33.02% → 33.02% | 0.592 → 0.592 | 5 → 5 |
| ETH_1d | ma_ribbon | 50.77% → 50.77% | 20.31% → 20.31% | 0.463 → 0.463 | 158 → 158 |
| ETH_1d | macd | 49.68% → 49.68% | -3.74% → -3.74% | 0.186 → 0.186 | 21 → 21 |
| ETH_1d | obv_trend | 49.50% → 49.50% | 8.43% → 8.43% | 0.319 → 0.319 | 47 → 47 |
| ETH_1d | ou_reversion | 40.91% → 40.91% | -14.23% → -14.23% | -0.923 → -0.923 | 3 → 3 |
| ETH_1d | ppo | 49.66% → 49.66% | 0.83% → 0.83% | 0.237 → 0.237 | 21 → 21 |
| ETH_1d | rsi | 46.90% → 46.90% | -37.78% → -37.78% | -0.446 → -0.446 | 4 → 4 |
| ETH_1d | sma_regime | 52.36% → 52.36% | 12.50% → 12.50% | 0.365 → 0.365 | 7 → 7 |
| ETH_1d | stochastic | 51.20% → 51.20% | -27.98% → -27.98% | -0.199 → -0.199 | 9 → 9 |
| ETH_1d | swing_confluence | 47.51% → 47.51% | -40.44% → -40.44% | -0.655 → -0.655 | 12 → 12 |
| ETH_1d | trigger_trade | 41.67% → 41.67% | -20.42% → -20.42% | -0.330 → -0.330 | 6 → 6 |
| ETH_1d | ts_momentum | 53.08% → 53.08% | 74.55% → 74.55% | 0.958 → 0.958 | 8 → 8 |
| ETH_1d | vol_regime | 50.25% → 50.25% | 17.64% → 17.64% | 0.440 → 0.440 | 13 → 13 |
| ETH_1d | voltarget | 51.84% → 51.84% | 39.62% → 39.62% | 0.694 → 0.694 | 81 → 81 |
| ETH_1d | vwap_reversion | 51.75% → 51.75% | -26.03% → -26.03% | -0.096 → -0.096 | 27 → 27 |
| ETH_1d | zscore | 47.76% → 47.76% | -44.31% → -44.31% | -0.552 → -0.552 | 10 → 10 |
| SOL_1h | adx_trend | 47.32% → 47.32% | 4.68% → 4.68% | 1.612 → 1.612 | 23 → 23 |
| SOL_1h | atr_sized | 46.02% → 46.02% | -8.15% → -8.15% | -2.642 → -2.642 | 205 → 205 |
| SOL_1h | bb_breakout | 48.75% → 48.75% | 4.28% → 4.28% | 1.204 → 1.204 | 19 → 19 |
| SOL_1h | bb_reversion | 50.90% → 50.90% | -4.05% → -4.05% | -0.621 → -0.621 | 26 → 26 |
| SOL_1h | breakout | 46.00% → 46.00% | -8.06% → -8.06% | -1.723 → -1.723 | 20 → 20 |
| SOL_1h | buy_and_hold | 48.22% → 48.22% | -11.95% → -11.95% | -1.256 → -1.256 | 1 → 1 |
| SOL_1h | dca | 48.22% → 48.22% | -11.95% → -11.95% | -1.256 → -1.256 | 1 → 1 |
| SOL_1h | dual_momentum | 47.13% → 47.13% | -23.64% → -23.64% | -4.573 → -4.573 | 89 → 89 |
| SOL_1h | ema_crossover | 48.22% → 48.22% | 5.44% → 5.44% | 1.247 → 1.247 | 2 → 2 |
| SOL_1h | fib_retracement | 44.10% → 44.10% | -22.26% → -22.26% | -7.551 → -7.551 | 24 → 24 |
| SOL_1h | garch_voltarget | 46.02% → 46.02% | -11.50% → -12.43% | -2.172 → -2.474 | 34 → 61 |
| SOL_1h | grid | 49.49% → 49.49% | -2.37% → -2.37% | -1.287 → -1.287 | 395 → 395 |
| SOL_1h | hurst_switch | 51.79% → 51.79% | -3.62% → -3.62% | -2.269 → -2.269 | 11 → 11 |
| SOL_1h | ichimoku | 45.13% → 45.13% | -18.20% → -18.20% | -3.798 → -3.798 | 37 → 37 |
| SOL_1h | keltner | 41.99% → 41.99% | -3.02% → -3.02% | -0.771 → -0.771 | 13 → 13 |
| SOL_1h | lev_high | 47.64% → 47.64% | -99.96% → -99.96% | -3.730 → -3.730 | 199 → 199 |
| SOL_1h | lev_low | 47.64% → 47.64% | -30.14% → -30.14% | -2.801 → -2.801 | 211 → 211 |
| SOL_1h | lev_medium | 47.64% → 47.64% | -65.97% → -65.97% | -3.014 → -3.014 | 202 → 202 |
| SOL_1h | ma_crossover | 47.93% → 47.93% | -9.54% → -9.54% | -1.674 → -1.674 | 14 → 14 |
| SOL_1h | ma_ribbon | 47.96% → 47.96% | -19.36% → -19.36% | -4.459 → -4.459 | 457 → 457 |
| SOL_1h | macd | 47.64% → 47.64% | -10.31% → -10.31% | -1.718 → -1.718 | 49 → 49 |
| SOL_1h | obv_trend | 46.88% → 46.88% | -23.32% → -23.32% | -4.509 → -4.509 | 83 → 83 |
| SOL_1h | ou_reversion | 48.55% → 48.55% | -7.39% → -7.39% | -2.680 → -2.680 | 11 → 11 |
| SOL_1h | ppo | 47.32% → 47.32% | -10.83% → -10.83% | -1.826 → -1.826 | 52 → 52 |
| SOL_1h | rsi | 50.35% → 50.35% | 8.55% → 8.55% | 1.927 → 1.927 | 15 → 15 |
| SOL_1h | sma_regime | 48.02% → 48.02% | -4.74% → -4.74% | -0.814 → -0.814 | 23 → 23 |
| SOL_1h | stochastic | 51.51% → 51.51% | 0.46% → 0.46% | 0.257 → 0.257 | 22 → 22 |
| SOL_1h | swing_confluence | 46.00% → 46.00% | -8.06% → -8.06% | -1.723 → -1.723 | 20 → 20 |
| SOL_1h | trigger_trade | 56.00% → 56.00% | 5.85% → 5.85% | 1.965 → 1.965 | 20 → 20 |
| SOL_1h | ts_momentum | 45.67% → 45.67% | -21.98% → -21.98% | -4.606 → -4.606 | 50 → 50 |
| SOL_1h | vol_regime | 50.00% → 50.00% | -0.36% → -0.36% | 0.001 → 0.001 | 24 → 24 |
| SOL_1h | voltarget | 46.02% → 46.02% | -11.50% → -12.24% | -2.172 → -2.436 | 34 → 117 |
| SOL_1h | vwap_reversion | 51.08% → 51.08% | 3.19% → 3.19% | 0.858 → 0.858 | 16 → 16 |
| SOL_1h | zscore | 50.26% → 50.26% | -5.38% → -5.38% | -0.890 → -0.890 | 25 → 25 |

Source and data hashes, split boundaries, cost conventions, and package integrity checks are in manifest.json. Full denominators, undefined metrics, baseline accuracy, coverage, failures, costs and risk metrics are in results.json and results.csv. Signed candidate-minus-original differences are in comparison.csv.
