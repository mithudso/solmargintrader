# ZEC/USD: native spot market backtest and correlation study

Report version: 2.0.0

## Exactly what was tested

**Trading market: ZEC/USD. Venue: Coinbase Exchange spot. Native product: ZEC-USD. Prices, fees, cash and account equity use USD.**
Each reference account starts with 10,000 USD units. This normalized simulation has no order-book capacity model; it does not assert that this size is executable.
Requested acquisition: **2026-10-27T00:00:00Z to 2026-11-27T00:00:00Z**, exclusive (44,640 minutes).
Actual backtest input: **2026-11-23T11:49:00Z to 2026-11-26T09:42:00Z**, exclusive (**4,193 consecutive real one-minute bars**). Gap policy: **longest**.
**REDUCED WINDOW: this is not a complete-week backtest.** The venue supplied 44,526/44,640 minutes; 40,333 other observed bars were excluded. The longest continuous segment was selected by timestamp count, with the earliest segment breaking ties. No price or outcome determines the segment and no candles are filled.

## Market strategy backtests

1,707 underlying spot templates × six filter/control variants × 1m/5m/10m/1h bars × four cost scenarios. Each scenario charges 10, 15, 25 or 60 bps per fill plus 2 bps execution allowance. Closed-bar signals fill at the next open; spot exposure is long/cash. Cash and buy-and-hold controls use the same clock and cost model.
The first 60% is the training prefix, the next 20% is validation and the last 20% is the final test. Full-window accounts are also descriptive. Selection ranks validation net return only, requires ten validation exits, and never reranks on test results. These short-window profits have no multiple-search profitability qualification.
Strategy matrix: 491,712 rows; 406,764 completed evaluations. Separate Volty/grid/DCA reference models: 7,920 rows. Repeated overlapping candidates are not independent trials.

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
| 1m | 10 | single [vol regime {"calm_quantile": 0.5, "lookback": 250, "trend_window": 200, "vol_window": 120}] (`d54e263e9afea8e629eff375`) | Underlying strategy without an extra filter | 7.15% | 0.54% | 7 |
| 1m | 15 | single [atr sized {"atr_period": 7, "risk_per_trade": 0.01, "stop_atr_multiple": 2, "trend_window": 252}] (`222dd25a6a469939b1a4a67d`) | Underlying strategy without an extra filter | 6.04% | 0.08% | 8 |
| 1m | 25 | single [atr sized {"atr_period": 7, "risk_per_trade": 0.01, "stop_atr_multiple": 2, "trend_window": 252}] (`222dd25a6a469939b1a4a67d`) | Underlying strategy without an extra filter | 4.80% | -1.13% | 8 |
| 1m | 60 | single [atr sized {"atr_period": 7, "risk_per_trade": 0.01, "stop_atr_multiple": 2, "trend_window": 252}] (`222dd25a6a469939b1a4a67d`) | Underlying strategy + positive 64-bar log-price regression slope filter | 0.92% | -3.22% | 6 |
| 5m | 10 | single [ma ribbon {"base": 10, "windows": 4}] (`5042cef948abcd163ca09d1f`) | Underlying strategy without an extra filter | 6.74% | -0.06% | 41 |
| 5m | 15 | single [ma ribbon {"base": 10, "windows": 4}] (`5042cef948abcd163ca09d1f`) | Underlying strategy without an extra filter | 6.31% | -0.43% | 42 |
| 5m | 25 | single [ma ribbon {"base": 10, "windows": 4}] (`5042cef948abcd163ca09d1f`) | Underlying strategy without an extra filter | 5.46% | -1.16% | 42 |
| 5m | 60 | mean [swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}] (`ec1eb01fe3419c0ef7e73473`) | Underlying strategy without an extra filter | 2.58% | -3.15% | 24 |
| 10m | 10 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}; adx trend {"adx_period": 14, "adx_threshold": 25.0}] (`013703b9d7913d14558e6c45`) | Underlying strategy without an extra filter | 7.51% | 0.04% | 27 |
| 10m | 15 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}; adx trend {"adx_period": 14, "adx_threshold": 25.0}] (`013703b9d7913d14558e6c45`) | Underlying strategy without an extra filter | 7.26% | -0.29% | 30 |
| 10m | 25 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}; adx trend {"adx_period": 14, "adx_threshold": 25.0}] (`013703b9d7913d14558e6c45`) | Underlying strategy without an extra filter | 6.76% | -0.96% | 30 |
| 10m | 60 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}; adx trend {"adx_period": 14, "adx_threshold": 25.0}] (`013703b9d7913d14558e6c45`) | Underlying strategy without an extra filter | 5.02% | -3.25% | 30 |

Selected policy definitions (parameters are the frozen configuration):

- `d54e263e9afea8e629eff375` at 1m: single [vol regime {"calm_quantile": 0.5, "lookback": 250, "trend_window": 200, "vol_window": 120}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `222dd25a6a469939b1a4a67d` at 1m: single [atr sized {"atr_period": 7, "risk_per_trade": 0.01, "stop_atr_multiple": 2, "trend_window": 252}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `5042cef948abcd163ca09d1f` at 5m: single [ma ribbon {"base": 10, "windows": 4}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `ec1eb01fe3419c0ef7e73473` at 5m: mean [swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `013703b9d7913d14558e6c45` at 10m: mean [macd {"fast": 12, "signal": 9, "slow": 26}; obv trend {"ma_window": 20}; adx trend {"adx_period": 14, "adx_threshold": 25.0}]. persistence=1 bars; exposure rebalance threshold=0.0.

All candidate member parameters and underlying policy configurations, including candidates that were not selected, are retained in run-plan.json.zlib. Strategy result files identify candidate_id, mode, cadence, split and fee scenario.

## Return correlations: diagnostics separate from market backtests

Target: future **ZEC/USD log returns**, at 1/5/10/15/30/60-minute horizons. Predictors: past-only target returns, candle body/range, volume, volatility, range position, and available reference-market returns. All reference markets share the target's USD quote and venue. A comparison of ETH/USD returns with BTC/USD returns is not an ETH/BTC market backtest.
Searched 14 features. Outcomes are nonoverlapping within each horizon and purged at split ends. An approximate 60-minute block-permutation maximum statistic covers every validation/test feature and horizon (1,999 replicates). The resulting p-values are then multiplied by 1 planned market combinations (Bonferroni, capped at one) for batch-wide claims. Train correlations rank the shortlist before validation or test is inspected.
**Batch-family corrected final-test associations at p ≤ 0.05: 0.** An association under this approximate stationary null does not establish a causal effect, a leading trade or net profit.

| Same-minute return comparison (descriptive only) | Pearson r | Matched observations |
|---|---:|---:|
| ZEC/USD returns vs BTC/USD returns | 0.7465 | 4,192 |

| Training-selected predictor | Future horizon | Train r | Validation r | Test r | Batch-family test p |
|---|---:|---:|---:|---:|---:|
| volatility_30m | 60m | -0.2693 | unavailable | unavailable | unavailable |
| range_position_48m | 60m | 0.2502 | unavailable | unavailable | unavailable |
| BTC_return_1m | 15m | -0.2427 | -0.0194 | 0.1004 | 1.0000 |
| BTC_return_1m | 60m | -0.2415 | unavailable | unavailable | unavailable |
| BTC_return_15m | 15m | 0.2363 | -0.2087 | 0.0012 | 1.0000 |
| body_return | 15m | -0.2361 | -0.1361 | -0.1081 | 1.0000 |
| return_1m | 15m | -0.2243 | -0.1866 | -0.0496 | 1.0000 |
| BTC_return_5m | 10m | -0.2164 | -0.0619 | 0.1311 | 1.0000 |
| volatility_30m | 30m | -0.2142 | unavailable | unavailable | unavailable |
| return_15m | 15m | 0.2122 | 0.0724 | 0.0042 | 1.0000 |
| log_volume | 60m | -0.1941 | unavailable | unavailable | unavailable |
| return_60m | 60m | 0.1858 | unavailable | unavailable | unavailable |

### Correlation coverage: estimated versus unavailable tests

A sparse reference invalidates only that reference's affected features. Target-only tests retain their own observations. Null blocks shuffle the complete regular target clock before each feature mask is applied. Zero corrected findings is not evidence that unavailable tests found no association.

| Split | Future horizon | Computed feature tests | Insufficient history | Constant feature/target | Observations per feature (range) |
|---|---:|---:|---:|---:|---:|
| validation | 1m | 14 | 0 | 0 | 838–838 |
| validation | 5m | 14 | 0 | 0 | 167–167 |
| validation | 10m | 14 | 0 | 0 | 83–83 |
| validation | 15m | 14 | 0 | 0 | 55–55 |
| validation | 30m | 0 | 14 | 0 | 27–27 |
| validation | 60m | 0 | 14 | 0 | 13–13 |
| test | 1m | 14 | 0 | 0 | 838–838 |
| test | 5m | 14 | 0 | 0 | 167–167 |
| test | 10m | 14 | 0 | 0 | 83–83 |
| test | 15m | 14 | 0 | 0 | 55–55 |
| test | 30m | 0 | 14 | 0 | 27–27 |
| test | 60m | 0 | 14 | 0 | 13–13 |

## Other analyses and their limits

Volty: 50 frozen settings, four cadences, four costs and three OHLC intrabar paths; synthetic 1x long/short with 0.1 bps/hour carry, not actual perpetual funding or fills. Grid/DCA: 20 frozen canonical configurations on 1m/5m/1h, with pessimistic OHLC execution; 10m is explicitly unsupported.
Cycles: whole-search price/return spectra, confirmed pivot spacing, and forecasts fitted before evaluation (harmonic-plus-trend versus separate linear-trend and last-price persistence forecasts). These forecast controls are separate from the linear strategy filter above.
672 global/rolling cycle tests share a within-market Holm correction. Smallest corrected p: 1.000000; first-test resolution floor: 0.336000. A floor above 0.05 makes this inconclusive. Cycle results are exploratory per market; no batch-wide cycle significance claim is made.
Reversals: frozen one/two-up-bar definitions, intrabar/midpoint/close policies, 5/10/20m excursion horizons, nonoverlap controls and unconditional baselines. These descriptive excursions are not executable fills.
Captured receive-time books, historical top50 universes, Oracle barrier/exit50 replay, long-history daily CPCV and the original long-history shape router require unavailable inputs. coverage.json maps every transferred study and exclusion. One week cannot establish robustness across regimes; modelled costs do not supply observed spreads, depth, latency, funding or fills. Annualized Sharpe is omitted.

## Reproduction and integrity

inputs/*.json.zlib retain exact provider pages and normalized candles. run-plan.json.zlib freezes products, options, code hashes and the complete catalogue. manifest.json binds generated artifacts. Offline verification rechecks candle normalization, hashes, report reproduction and result counts. A finished run is immutable. Acquire a new output directory to change markets or options.
