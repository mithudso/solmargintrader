# HYPE/USDT: native spot market backtest and correlation study

Report version: 2.0.0

## Exactly what was tested

**Trading market: HYPE/USDT. Venue: Binance spot. Native product: HYPEUSDT. Prices, fees, cash and account equity use USDT.**
Each reference account starts with 10,000 USDT units. This normalized simulation has no order-book capacity model; it does not assert that this size is executable.
Requested acquisition: **2026-11-20T08:49:00Z to 2026-11-27T08:49:00Z**, exclusive (10,080 minutes).
Actual backtest input: **2026-11-20T08:49:00Z to 2026-11-27T08:49:00Z**, exclusive (**10,080 consecutive real one-minute bars**). Gap policy: **strict**.

## Market strategy backtests

1,707 underlying spot templates × six filter/control variants × 1m/5m/10m/1h bars × four cost scenarios. Each scenario charges 10, 15, 25 or 60 bps per fill plus 2 bps execution allowance. Closed-bar signals fill at the next open; spot exposure is long/cash. Cash and buy-and-hold controls use the same clock and cost model.
The first 60% is the training prefix, the next 20% is validation and the last 20% is the final test. Full-window accounts are also descriptive. Selection ranks validation net return only, requires ten validation exits, and never reranks on test results. These short-window profits have no multiple-search profitability qualification.
Strategy matrix: 491,712 rows; 441,888 completed evaluations. Separate Volty/grid/DCA reference models: 7,920 rows. Repeated overlapping candidates are not independent trials.

### What each filter means

The filter is applied to each underlying strategy; a filter name alone is not a complete strategy description.

| Code in result files | Test definition |
|---|---|
| `baseline` | Underlying strategy without an extra filter |
| `shape` | Underlying strategy + causal 48-bar shape filter |
| `shape_control` | Underlying strategy + shape-availability control |
| `frequency` | Underlying strategy + fitted harmonic direction filter |
| `frequency_control` | Underlying strategy + harmonic-fit availability control |
| `linear_control` | Underlying strategy + positive 64-bar log-price regression slope filter |

Shape classification uses only the past 48 closed bars. Its allowed shapes depend on the underlying strategy family; the frozen shape rules and catalogue are in the run plan. The shape control uses the identical known-shape clock but permits every known shape.
The harmonic model fits intercept, trend and a selected sine/cosine period to 64 past closed log-price bars and freezes the fit for 16 bars. The frequency filter permits positive fitted harmonic increments after removing the trend. The linear control permits a positive slope from a separate intercept-plus-trend regression on those same 64 bars, frozen for the same 16 bars. The availability control permits all bars where the harmonic fit is available. Unknown features cannot authorize exposure.
The underlying committee combines member exposures as follows: single/all = minimum; any = maximum; majority = strictly more than half positive; supermajority = at least two thirds positive; weighted = weighted exposure; other combination modes = mean. Internal gates, fallbacks, persistence and rebalance thresholds below remain part of the policy.

### Frozen validation selections: underlying strategy plus filter

| Cadence | Fee bps/fill (+2 bps) | Underlying strategy | Extra filter/control | Validation return | Final test return | Test exits |
|---|---:|---|---|---:|---:|---:|
| 1m | 10 | single [ma ribbon {"base": 40, "windows": 5}] (`69c90c6bd446d2b0754439be`) | Underlying strategy + positive 64-bar log-price regression slope filter | 4.99% | -1.66% | 325 |
| 1m | 15 | single [ma ribbon {"base": 40, "windows": 5}] (`69c90c6bd446d2b0754439be`) | Underlying strategy + positive 64-bar log-price regression slope filter | 4.17% | -3.05% | 331 |
| 1m | 25 | single [ma ribbon {"base": 40, "windows": 5}] (`69c90c6bd446d2b0754439be`) | Underlying strategy + positive 64-bar log-price regression slope filter | 2.56% | -5.79% | 333 |
| 1m | 60 | single [voltarget {"target_vol": 0.007905694150420948, "trend_window": 200, "vol_window": 60}] (`966dec0239fbbc8476a686f5`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.22% | -0.52% | 445 |
| 5m | 10 | single [atr sized {"atr_period": 30, "risk_per_trade": 0.01, "stop_atr_multiple": 1.5, "trend_window": 200}] (`2da0b6492a2a23d8ce6d5c06`) | Underlying strategy without an extra filter | 4.76% | 6.62% | 3 |
| 5m | 15 | single [atr sized {"atr_period": 30, "risk_per_trade": 0.01, "stop_atr_multiple": 1.5, "trend_window": 200}] (`2da0b6492a2a23d8ce6d5c06`) | Underlying strategy without an extra filter | 4.64% | 6.30% | 3 |
| 5m | 25 | gate [ts momentum {"threshold": 0.0, "window": 60}; swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}] (`22c6ecf463b61d953fe4ff33`) | Underlying strategy without an extra filter | 4.42% | 0.31% | 30 |
| 5m | 60 | single [atr sized {"atr_period": 30, "risk_per_trade": 0.01, "stop_atr_multiple": 1.5, "trend_window": 200}] (`2da0b6492a2a23d8ce6d5c06`) | Underlying strategy without an extra filter | 3.61% | 3.47% | 3 |
| 10m | 10 | gate [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}] (`40363f7588411d89c7f161d1`) | Underlying strategy without an extra filter | 6.71% | 0.63% | 17 |
| 10m | 15 | gate [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}] (`40363f7588411d89c7f161d1`) | Underlying strategy without an extra filter | 6.44% | -0.08% | 17 |
| 10m | 25 | gate [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}] (`40363f7588411d89c7f161d1`) | Underlying strategy without an extra filter | 5.91% | -1.47% | 17 |
| 10m | 60 | gate [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}] (`40363f7588411d89c7f161d1`) | Underlying strategy without an extra filter | 4.07% | -6.19% | 17 |
| 1h | 10 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}] (`8fa6bfc3984f7692aa023f54`) | Underlying strategy without an extra filter | 2.64% | 1.94% | 14 |
| 1h | 15 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}] (`8fa6bfc3984f7692aa023f54`) | Underlying strategy without an extra filter | 2.50% | 1.80% | 14 |
| 1h | 25 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}] (`8fa6bfc3984f7692aa023f54`) | Underlying strategy without an extra filter | 2.23% | 1.53% | 14 |
| 1h | 60 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}] (`8fa6bfc3984f7692aa023f54`) | Underlying strategy without an extra filter | 1.27% | 0.58% | 14 |

Selected policy definitions (parameters are the frozen configuration):

- `69c90c6bd446d2b0754439be` at 1m: single [ma ribbon {"base": 40, "windows": 5}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `966dec0239fbbc8476a686f5` at 1m: single [voltarget {"target_vol": 0.007905694150420948, "trend_window": 200, "vol_window": 60}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `2da0b6492a2a23d8ce6d5c06` at 5m: single [atr sized {"atr_period": 30, "risk_per_trade": 0.01, "stop_atr_multiple": 1.5, "trend_window": 200}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `22c6ecf463b61d953fe4ff33` at 5m: gate [ts momentum {"threshold": 0.0, "window": 60}; swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}]. internal permission signal > 0: adx trend {"adx_period": 14, "adx_threshold": 25.0}. persistence=1 bars; exposure rebalance threshold=0.0.
- `40363f7588411d89c7f161d1` at 10m: gate [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}]. internal permission signal > 0: adx trend {"adx_period": 14, "adx_threshold": 25.0}. persistence=1 bars; exposure rebalance threshold=0.0.
- `8fa6bfc3984f7692aa023f54` at 1h: mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}]. persistence=1 bars; exposure rebalance threshold=0.0.

All candidate member parameters and underlying policy configurations, including candidates that were not selected, are retained in run-plan.json.zlib. Strategy result files identify candidate_id, mode, cadence, split and fee scenario.

## Return correlations: diagnostics separate from market backtests

Target: future **HYPE/USDT log returns**, at 1/5/10/15/30/60-minute horizons. Predictors: past-only target returns, candle body/range, volume, volatility, range position, and available reference-market returns. All reference markets share the target's USDT quote and venue. A comparison of ETH/USD returns with BTC/USD returns is not an ETH/BTC market backtest.
Searched 18 features. Outcomes are nonoverlapping within each horizon and purged at split ends. An approximate 60-minute block-permutation maximum statistic covers every validation/test feature and horizon (1,999 replicates). The resulting p-values are then multiplied by 1 planned market combinations (Bonferroni, capped at one) for batch-wide claims. Train correlations rank the shortlist before validation or test is inspected.
**Batch-family corrected final-test associations at p ≤ 0.05: 0.** An association under this approximate stationary null does not establish a causal effect, a leading trade or net profit.

| Same-minute return comparison (descriptive only) | Pearson r | Matched observations |
|---|---:|---:|
| HYPE/USDT returns vs BTC/USDT returns | 0.7254 | 10,079 |
| HYPE/USDT returns vs ZEC/USDT returns | 0.7133 | 10,079 |

| Training-selected predictor | Future horizon | Train r | Validation r | Test r | Batch-family test p |
|---|---:|---:|---:|---:|---:|
| BTC_return_1m | 60m | -0.2356 | -0.3871 | -0.2776 | 0.9520 |
| volume_relative_60m | 60m | 0.1394 | 0.1425 | -0.0718 | 1.0000 |
| ZEC_return_60m | 60m | 0.1357 | -0.0271 | 0.0309 | 1.0000 |
| volume_relative_60m | 30m | 0.1337 | 0.0898 | -0.1740 | 1.0000 |
| return_1m | 60m | -0.1296 | -0.3379 | -0.1482 | 1.0000 |
| ZEC_return_5m | 30m | 0.1269 | -0.1696 | -0.0736 | 1.0000 |
| range_position_48m | 60m | 0.1196 | -0.1098 | 0.0349 | 1.0000 |
| ZEC_return_15m | 60m | 0.1183 | -0.0981 | 0.1137 | 1.0000 |
| body_return | 60m | -0.1102 | -0.3426 | -0.1547 | 1.0000 |
| ZEC_return_5m | 15m | 0.1083 | -0.0503 | 0.0089 | 1.0000 |
| volatility_30m | 60m | -0.1042 | 0.3330 | 0.4571 | 0.2070 |
| BTC_return_5m | 10m | -0.1028 | -0.0282 | 0.0534 | 1.0000 |

### Correlation coverage: estimated versus unavailable tests

A sparse reference invalidates only that reference's affected features. Target-only tests retain their own observations. Null blocks shuffle the complete regular target clock before each feature mask is applied. Zero corrected findings is not evidence that unavailable tests found no association.

| Split | Future horizon | Computed feature tests | Insufficient history | Constant feature/target | Observations per feature (range) |
|---|---:|---:|---:|---:|---:|
| validation | 1m | 18 | 0 | 0 | 2015–2015 |
| validation | 5m | 18 | 0 | 0 | 403–403 |
| validation | 10m | 18 | 0 | 0 | 201–201 |
| validation | 15m | 18 | 0 | 0 | 134–134 |
| validation | 30m | 18 | 0 | 0 | 67–67 |
| validation | 60m | 18 | 0 | 0 | 33–33 |
| test | 1m | 18 | 0 | 0 | 2015–2015 |
| test | 5m | 18 | 0 | 0 | 403–403 |
| test | 10m | 18 | 0 | 0 | 201–201 |
| test | 15m | 18 | 0 | 0 | 134–134 |
| test | 30m | 18 | 0 | 0 | 67–67 |
| test | 60m | 18 | 0 | 0 | 33–33 |

## Other analyses and their limits

Volty: 50 frozen settings, four cadences, four costs and three OHLC intrabar paths; synthetic 1x long/short with 0.1 bps/hour carry, not actual perpetual funding or fills. Grid/DCA: 20 frozen canonical configurations on 1m/5m/1h, with pessimistic OHLC execution; 10m is explicitly unsupported.
Cycles: whole-search price/return spectra, confirmed pivot spacing, and forecasts fitted before evaluation (harmonic-plus-trend versus separate linear-trend and last-price persistence forecasts). These forecast controls are separate from the linear strategy filter above.
1,638 global/rolling cycle tests share a within-market Holm correction. Smallest corrected p: 1.000000; first-test resolution floor: 0.819000. A floor above 0.05 makes this inconclusive. Cycle results are exploratory per market; no batch-wide cycle significance claim is made.
Reversals: frozen one/two-up-bar definitions, intrabar/midpoint/close policies, 5/10/20m excursion horizons, nonoverlap controls and unconditional baselines. These descriptive excursions are not executable fills.
Captured receive-time books, historical top50 universes, Oracle barrier/exit50 replay, long-history daily CPCV and the original long-history shape router require unavailable inputs. coverage.json maps every transferred study and exclusion. One week cannot establish robustness across regimes; modelled costs do not supply observed spreads, depth, latency, funding or fills. Annualized Sharpe is omitted.

## Reproduction and integrity

inputs/*.json.zlib retain exact provider pages and normalized candles. run-plan.json.zlib freezes products, options, code hashes and the complete catalogue. manifest.json binds generated artifacts. Offline verification rechecks candle normalization, hashes, report reproduction and result counts. A finished run is immutable. Acquire a new output directory to change markets or options.
