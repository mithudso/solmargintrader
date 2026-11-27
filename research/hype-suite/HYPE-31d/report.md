# HYPE/USD: native spot market backtest and correlation study

Report version: 2.0.0

## Exactly what was tested

**Trading market: HYPE/USD. Venue: Coinbase Exchange spot. Native product: HYPE-USD. Prices, fees, cash and account equity use USD.**
Each reference account starts with 10,000 USD units. This normalized simulation has no order-book capacity model; it does not assert that this size is executable.
Requested acquisition: **2026-10-27T00:00:00Z to 2026-11-27T00:00:00Z**, exclusive (44,640 minutes).
Actual backtest input: **2026-11-19T21:20:00Z to 2026-11-21T19:46:00Z**, exclusive (**2,786 consecutive real one-minute bars**). Gap policy: **longest**.
**REDUCED WINDOW: this is not a complete-week backtest.** The venue supplied 43,411/44,640 minutes; 40,625 other observed bars were excluded. The longest continuous segment was selected by timestamp count, with the earliest segment breaking ties. No price or outcome determines the segment and no candles are filled.

## Market strategy backtests

1,707 underlying spot templates × six filter/control variants × 1m/5m/10m/1h bars × four cost scenarios. Each scenario charges 10, 15, 25 or 60 bps per fill plus 2 bps execution allowance. Closed-bar signals fill at the next open; spot exposure is long/cash. Cash and buy-and-hold controls use the same clock and cost model.
The first 60% is the training prefix, the next 20% is validation and the last 20% is the final test. Full-window accounts are also descriptive. Selection ranks validation net return only, requires ten validation exits, and never reranks on test results. These short-window profits have no multiple-search profitability qualification.
Strategy matrix: 491,712 rows; 357,060 completed evaluations. Separate Volty/grid/DCA reference models: 7,824 rows. Repeated overlapping candidates are not independent trials.

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
| 1m | 10 | single [atr sized {"atr_period": 30, "risk_per_trade": 0.0075, "stop_atr_multiple": 2, "trend_window": 200}] (`1f6fa03af8d139bde9a61f11`) | Underlying strategy + positive 64-bar log-price regression slope filter | 0.86% | 1.48% | 9 |
| 1m | 15 | single [atr sized {"atr_period": 30, "risk_per_trade": 0.0075, "stop_atr_multiple": 2, "trend_window": 200}] (`1f6fa03af8d139bde9a61f11`) | Underlying strategy + positive 64-bar log-price regression slope filter | 0.55% | 0.57% | 9 |
| 1m | 25 | single [voltarget {"target_vol": 0.015811388300841896, "trend_window": 300, "vol_window": 60}] (`b99bf042adf0b8f01c24996d`) | Underlying strategy without an extra filter | -0.00% | -0.12% | 277 |
| 1m | 60 | single [voltarget {"target_vol": 0.015811388300841896, "trend_window": 300, "vol_window": 60}] (`b99bf042adf0b8f01c24996d`) | Underlying strategy without an extra filter | -0.02% | -0.34% | 277 |
| 5m | 10 | single [dca {"instalments": 10, "interval": 48}] (`3f819c47ece380adbc32dc7c`) | Underlying strategy + causal 48-bar shape filter | 2.01% | 3.89% | 3 |
| 5m | 15 | single [dca {"instalments": 10, "interval": 48}] (`3f819c47ece380adbc32dc7c`) | Underlying strategy + causal 48-bar shape filter | 1.67% | 3.58% | 3 |
| 5m | 25 | single [dca {"instalments": 18, "interval": 30}] (`54e6dc2396bede599663b2b6`) | Underlying strategy + causal 48-bar shape filter | 1.01% | 2.58% | 40 |
| 5m | 60 | mean [ts momentum {"threshold": 0.0, "window": 60}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}] (`064fc09244bc9bafb884f00a`) | Underlying strategy + positive 64-bar log-price regression slope filter | 0.38% | 2.35% | 28 |
| 10m | 10 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}] (`8fa6bfc3984f7692aa023f54`) | Underlying strategy + fitted harmonic direction filter | 3.40% | 0.97% | 14 |
| 10m | 15 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}] (`8fa6bfc3984f7692aa023f54`) | Underlying strategy + fitted harmonic direction filter | 3.16% | 0.70% | 14 |
| 10m | 25 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; ts momentum {"threshold": 0.0, "window": 60}] (`a134889398842039e0f3b2ed`) | Underlying strategy + fitted harmonic direction filter | 2.82% | 0.12% | 16 |
| 10m | 60 | mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; ts momentum {"threshold": 0.0, "window": 60}] (`a134889398842039e0f3b2ed`) | Underlying strategy + fitted harmonic direction filter | 1.86% | -2.65% | 17 |

Selected policy definitions (parameters are the frozen configuration):

- `1f6fa03af8d139bde9a61f11` at 1m: single [atr sized {"atr_period": 30, "risk_per_trade": 0.0075, "stop_atr_multiple": 2, "trend_window": 200}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `b99bf042adf0b8f01c24996d` at 1m: single [voltarget {"target_vol": 0.015811388300841896, "trend_window": 300, "vol_window": 60}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `3f819c47ece380adbc32dc7c` at 5m: single [dca {"instalments": 10, "interval": 48}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `54e6dc2396bede599663b2b6` at 5m: single [dca {"instalments": 18, "interval": 30}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `064fc09244bc9bafb884f00a` at 5m: mean [ts momentum {"threshold": 0.0, "window": 60}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `8fa6bfc3984f7692aa023f54` at 10m: mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `a134889398842039e0f3b2ed` at 10m: mean [macd {"fast": 12, "signal": 9, "slow": 26}; ppo {"fast": 12, "signal": 9, "slow": 26}; ts momentum {"threshold": 0.0, "window": 60}]. persistence=1 bars; exposure rebalance threshold=0.0.

All candidate member parameters and underlying policy configurations, including candidates that were not selected, are retained in run-plan.json.zlib. Strategy result files identify candidate_id, mode, cadence, split and fee scenario.

## Return correlations: diagnostics separate from market backtests

Target: future **HYPE/USD log returns**, at 1/5/10/15/30/60-minute horizons. Predictors: past-only target returns, candle body/range, volume, volatility, range position, and available reference-market returns. All reference markets share the target's USD quote and venue. A comparison of ETH/USD returns with BTC/USD returns is not an ETH/BTC market backtest.
Searched 18 features. Outcomes are nonoverlapping within each horizon and purged at split ends. An approximate 60-minute block-permutation maximum statistic covers every validation/test feature and horizon (1,999 replicates). The resulting p-values are then multiplied by 1 planned market combinations (Bonferroni, capped at one) for batch-wide claims. Train correlations rank the shortlist before validation or test is inspected.
**Batch-family corrected final-test associations at p ≤ 0.05: 0.** An association under this approximate stationary null does not establish a causal effect, a leading trade or net profit.

| Same-minute return comparison (descriptive only) | Pearson r | Matched observations |
|---|---:|---:|
| HYPE/USD returns vs BTC/USD returns | 0.7053 | 2,785 |
| HYPE/USD returns vs ZEC/USD returns | 0.6692 | 2,785 |

| Training-selected predictor | Future horizon | Train r | Validation r | Test r | Batch-family test p |
|---|---:|---:|---:|---:|---:|
| return_60m | 30m | -0.3254 | unavailable | unavailable | unavailable |
| ZEC_return_15m | 30m | 0.2975 | unavailable | unavailable | unavailable |
| BTC_return_15m | 30m | 0.2611 | unavailable | unavailable | unavailable |
| return_60m | 15m | -0.2513 | 0.1776 | -0.0698 | 1.0000 |
| ZEC_return_60m | 30m | -0.2057 | unavailable | unavailable | unavailable |
| return_60m | 10m | -0.2018 | 0.1058 | -0.0865 | 1.0000 |
| volume_relative_60m | 15m | -0.1564 | -0.0318 | 0.0348 | 1.0000 |
| volatility_30m | 30m | 0.1563 | unavailable | unavailable | unavailable |
| ZEC_return_5m | 15m | 0.1432 | -0.1176 | -0.4414 | 0.3335 |
| return_60m | 5m | -0.1398 | 0.1050 | -0.0817 | 1.0000 |
| return_15m | 30m | 0.1371 | unavailable | unavailable | unavailable |
| ZEC_return_5m | 30m | 0.1328 | unavailable | unavailable | unavailable |

### Correlation coverage: estimated versus unavailable tests

A sparse reference invalidates only that reference's affected features. Target-only tests retain their own observations. Null blocks shuffle the complete regular target clock before each feature mask is applied. Zero corrected findings is not evidence that unavailable tests found no association.

| Split | Future horizon | Computed feature tests | Insufficient history | Constant feature/target | Observations per feature (range) |
|---|---:|---:|---:|---:|---:|
| validation | 1m | 18 | 0 | 0 | 556–556 |
| validation | 5m | 18 | 0 | 0 | 111–111 |
| validation | 10m | 18 | 0 | 0 | 55–55 |
| validation | 15m | 18 | 0 | 0 | 37–37 |
| validation | 30m | 0 | 18 | 0 | 18–18 |
| validation | 60m | 0 | 18 | 0 | 9–9 |
| test | 1m | 18 | 0 | 0 | 557–557 |
| test | 5m | 18 | 0 | 0 | 111–111 |
| test | 10m | 18 | 0 | 0 | 55–55 |
| test | 15m | 18 | 0 | 0 | 37–37 |
| test | 30m | 0 | 18 | 0 | 18–18 |
| test | 60m | 0 | 18 | 0 | 9–9 |

## Other analyses and their limits

Volty: 50 frozen settings, four cadences, four costs and three OHLC intrabar paths; synthetic 1x long/short with 0.1 bps/hour carry, not actual perpetual funding or fills. Grid/DCA: 20 frozen canonical configurations on 1m/5m/1h, with pessimistic OHLC execution; 10m is explicitly unsupported.
Cycles: whole-search price/return spectra, confirmed pivot spacing, and forecasts fitted before evaluation (harmonic-plus-trend versus separate linear-trend and last-price persistence forecasts). These forecast controls are separate from the linear strategy filter above.
438 global/rolling cycle tests share a within-market Holm correction. Smallest corrected p: 0.438000; first-test resolution floor: 0.219000. A floor above 0.05 makes this inconclusive. Cycle results are exploratory per market; no batch-wide cycle significance claim is made.
Reversals: frozen one/two-up-bar definitions, intrabar/midpoint/close policies, 5/10/20m excursion horizons, nonoverlap controls and unconditional baselines. These descriptive excursions are not executable fills.
Captured receive-time books, historical top50 universes, Oracle barrier/exit50 replay, long-history daily CPCV and the original long-history shape router require unavailable inputs. coverage.json maps every transferred study and exclusion. One week cannot establish robustness across regimes; modelled costs do not supply observed spreads, depth, latency, funding or fills. Annualized Sharpe is omitted.

## Reproduction and integrity

inputs/*.json.zlib retain exact provider pages and normalized candles. run-plan.json.zlib freezes products, options, code hashes and the complete catalogue. manifest.json binds generated artifacts. Offline verification rechecks candle normalization, hashes, report reproduction and result counts. A finished run is immutable. Acquire a new output directory to change markets or options.
