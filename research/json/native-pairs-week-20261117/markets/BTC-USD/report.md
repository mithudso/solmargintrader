# BTC/USD: native spot market backtest and correlation study

Report version: 2.0.0

## Exactly what was tested

**Trading market: BTC/USD. Venue: Coinbase Exchange spot. Native product: BTC-USD. Prices, fees, cash and account equity use USD.**
Each reference account starts with 10,000 USD units. This normalized simulation has no order-book capacity model; it does not assert that this size is executable.
Requested acquisition: **2026-11-10T19:46:00Z to 2026-11-17T19:46:00Z**, exclusive (10,080 minutes).
Actual backtest input: **2026-11-10T19:46:00Z to 2026-11-13T20:16:00Z**, exclusive (**4,350 consecutive real one-minute bars**). Gap policy: **longest**.
**REDUCED WINDOW: this is not a complete-week backtest.** The venue supplied 10,078/10,080 minutes; 5,728 other observed bars were excluded. The longest continuous segment was selected by timestamp count, with the earliest segment breaking ties. No price or outcome determines the segment and no candles are filled.

## Market strategy backtests

1,707 underlying spot templates × six filter/control variants × 1m/5m/10m/1h bars × four cost scenarios. Each scenario charges 10, 15, 25 or 60 bps per fill plus 2 bps execution allowance. Closed-bar signals fill at the next open; spot exposure is long/cash. Cash and buy-and-hold controls use the same clock and cost model.
The first 60% is the training prefix, the next 20% is validation and the last 20% is the final test. Full-window accounts are also descriptive. Selection ranks validation net return only, requires ten validation exits, and never reranks on test results. These short-window profits have no multiple-search profitability qualification.
Strategy matrix: 491,712 rows; 408,216 completed evaluations. Separate Volty/grid/DCA reference models: 7,920 rows. Repeated overlapping candidates are not independent trials.

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
| 1m | 10 | all [macd {"fast": 12, "signal": 9, "slow": 26}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}; voltarget {"target_vol": 0.015811388300841896, "trend_window": 100, "vol_window": 20}] (`dd4e3bf3c3a76eaea572e0c3`) | Underlying strategy + positive 64-bar log-price regression slope filter | 0.14% | -3.37% | 17 |
| 1m | 15 | all [macd {"fast": 12, "signal": 9, "slow": 26}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}; voltarget {"target_vol": 0.015811388300841896, "trend_window": 100, "vol_window": 20}] (`dd4e3bf3c3a76eaea572e0c3`) | Underlying strategy + positive 64-bar log-price regression slope filter | 0.05% | -4.68% | 17 |
| 1m | 25 | all [macd {"fast": 12, "signal": 9, "slow": 26}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}; voltarget {"target_vol": 0.015811388300841896, "trend_window": 100, "vol_window": 20}] (`dd4e3bf3c3a76eaea572e0c3`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.13% | -7.25% | 17 |
| 1m | 60 | all [macd {"fast": 12, "signal": 9, "slow": 26}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}; voltarget {"target_vol": 0.015811388300841896, "trend_window": 100, "vol_window": 20}] (`dd4e3bf3c3a76eaea572e0c3`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.74% | -15.72% | 17 |
| 5m | 10 | mean [swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}; voltarget {"target_vol": 0.035355339059327376, "trend_window": 100, "vol_window": 20}] (`08428514eb850833355926cc`) | Underlying strategy + causal 48-bar shape filter | -0.18% | -0.91% | 60 |
| 5m | 15 | mean [swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}; voltarget {"target_vol": 0.035355339059327376, "trend_window": 100, "vol_window": 20}] (`08428514eb850833355926cc`) | Underlying strategy + causal 48-bar shape filter | -0.25% | -1.31% | 60 |
| 5m | 25 | mean [swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}; voltarget {"target_vol": 0.035355339059327376, "trend_window": 100, "vol_window": 20}] (`08428514eb850833355926cc`) | Underlying strategy + causal 48-bar shape filter | -0.38% | -2.10% | 61 |
| 5m | 60 | single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}] (`3440ccda392e28465604a354`) | Underlying strategy without an extra filter | -0.66% | -0.44% | 65 |
| 10m | 10 | single [ma ribbon {"base": 10, "windows": 10}] (`c7a5a23f67f4e6ff21ae0aef`) | Underlying strategy without an extra filter | -0.25% | -0.57% | 33 |
| 10m | 15 | single [ma ribbon {"base": 10, "windows": 10}] (`c7a5a23f67f4e6ff21ae0aef`) | Underlying strategy without an extra filter | -0.30% | -0.69% | 33 |
| 10m | 25 | single [ma ribbon {"base": 10, "windows": 10}] (`c7a5a23f67f4e6ff21ae0aef`) | Underlying strategy without an extra filter | -0.41% | -0.94% | 34 |
| 10m | 60 | single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}] (`3440ccda392e28465604a354`) | Underlying strategy without an extra filter | -0.68% | 0.01% | 44 |

Selected policy definitions (parameters are the frozen configuration):

- `dd4e3bf3c3a76eaea572e0c3` at 1m: all [macd {"fast": 12, "signal": 9, "slow": 26}; bb breakout {"num_std": 2.0, "squeeze_lookback": 0, "squeeze_quantile": 0.25, "window": 20}; voltarget {"target_vol": 0.015811388300841896, "trend_window": 100, "vol_window": 20}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `08428514eb850833355926cc` at 5m: mean [swing confluence {"breakout": 20, "exit_lookback": 10, "ma_window": 50, "min_confirms": 2}; rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}; voltarget {"target_vol": 0.035355339059327376, "trend_window": 100, "vol_window": 20}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `3440ccda392e28465604a354` at 5m: single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `c7a5a23f67f4e6ff21ae0aef` at 10m: single [ma ribbon {"base": 10, "windows": 10}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `3440ccda392e28465604a354` at 10m: single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}]. persistence=1 bars; exposure rebalance threshold=0.0.

All candidate member parameters and underlying policy configurations, including candidates that were not selected, are retained in run-plan.json.zlib. Strategy result files identify candidate_id, mode, cadence, split and fee scenario.

## Return correlations: diagnostics separate from market backtests

Target: future **BTC/USD log returns**, at 1/5/10/15/30/60-minute horizons. Predictors: past-only target returns, candle body/range, volume, volatility, range position, and available reference-market returns. All reference markets share the target's USD quote and venue. A comparison of ETH/USD returns with BTC/USD returns is not an ETH/BTC market backtest.
Searched 18 features. Outcomes are nonoverlapping within each horizon and purged at split ends. An approximate 60-minute block-permutation maximum statistic covers every validation/test feature and horizon (1,999 replicates). The resulting p-values are then multiplied by 6 planned market combinations (Bonferroni, capped at one) for batch-wide claims. Train correlations rank the shortlist before validation or test is inspected.
**Batch-family corrected final-test associations at p ≤ 0.05: 0.** An association under this approximate stationary null does not establish a causal effect, a leading trade or net profit.

| Same-minute return comparison (descriptive only) | Pearson r | Matched observations |
|---|---:|---:|
| BTC/USD returns vs ETH/USD returns | 0.8865 | 4,349 |
| BTC/USD returns vs ZEC/USD returns | 0.6459 | 4,341 |

| Training-selected predictor | Future horizon | Train r | Validation r | Test r | Batch-family test p |
|---|---:|---:|---:|---:|---:|
| return_1m | 60m | -0.3356 | unavailable | unavailable | unavailable |
| return_5m | 60m | -0.2751 | unavailable | unavailable | unavailable |
| volatility_30m | 60m | 0.2573 | unavailable | unavailable | unavailable |
| body_return | 60m | -0.2553 | unavailable | unavailable | unavailable |
| ZEC_return_60m | 30m | -0.2048 | unavailable | unavailable | unavailable |
| ZEC_return_5m | 30m | 0.1992 | unavailable | unavailable | unavailable |
| ZEC_return_5m | 60m | -0.1941 | unavailable | unavailable | unavailable |
| volatility_30m | 30m | 0.1939 | unavailable | unavailable | unavailable |
| ETH_return_5m | 60m | -0.1873 | unavailable | unavailable | unavailable |
| ZEC_return_60m | 15m | -0.1799 | -0.0112 | 0.0371 | 1.0000 |
| return_15m | 60m | 0.1798 | unavailable | unavailable | unavailable |
| ETH_return_15m | 10m | -0.1614 | -0.1340 | -0.0442 | 1.0000 |

### Correlation coverage: estimated versus unavailable tests

A sparse reference invalidates only that reference's affected features. Target-only tests retain their own observations. Null blocks shuffle the complete regular target clock before each feature mask is applied. Zero corrected findings is not evidence that unavailable tests found no association.

| Split | Future horizon | Computed feature tests | Insufficient history | Constant feature/target | Observations per feature (range) |
|---|---:|---:|---:|---:|---:|
| validation | 1m | 18 | 0 | 0 | 808–869 |
| validation | 5m | 18 | 0 | 0 | 160–173 |
| validation | 10m | 18 | 0 | 0 | 79–86 |
| validation | 15m | 18 | 0 | 0 | 52–57 |
| validation | 30m | 0 | 18 | 0 | 25–28 |
| validation | 60m | 0 | 18 | 0 | 13–14 |
| test | 1m | 18 | 0 | 0 | 747–869 |
| test | 5m | 18 | 0 | 0 | 149–173 |
| test | 10m | 18 | 0 | 0 | 74–86 |
| test | 15m | 18 | 0 | 0 | 49–57 |
| test | 30m | 0 | 18 | 0 | 24–28 |
| test | 60m | 0 | 18 | 0 | 12–14 |

## Other analyses and their limits

Volty: 50 frozen settings, four cadences, four costs and three OHLC intrabar paths; synthetic 1x long/short with 0.1 bps/hour carry, not actual perpetual funding or fills. Grid/DCA: 20 frozen canonical configurations on 1m/5m/1h, with pessimistic OHLC execution; 10m is explicitly unsupported.
Cycles: whole-search price/return spectra, confirmed pivot spacing, and forecasts fitted before evaluation (harmonic-plus-trend versus separate linear-trend and last-price persistence forecasts). These forecast controls are separate from the linear strategy filter above.
696 global/rolling cycle tests share a within-market Holm correction. Smallest corrected p: 1.000000; first-test resolution floor: 0.348000. A floor above 0.05 makes this inconclusive. Cycle results are exploratory per market; no batch-wide cycle significance claim is made.
Reversals: frozen one/two-up-bar definitions, intrabar/midpoint/close policies, 5/10/20m excursion horizons, nonoverlap controls and unconditional baselines. These descriptive excursions are not executable fills.
Captured receive-time books, historical top50 universes, Oracle barrier/exit50 replay, long-history daily CPCV and the original long-history shape router require unavailable inputs. coverage.json maps every transferred study and exclusion. One week cannot establish robustness across regimes; modelled costs do not supply observed spreads, depth, latency, funding or fills. Annualized Sharpe is omitted.

## Reproduction and integrity

inputs/*.json.zlib retain exact provider pages and normalized candles. run-plan.json.zlib freezes products, options, code hashes and the complete catalogue. manifest.json binds generated artifacts. Offline verification rechecks candle normalization, hashes, report reproduction and result counts. A finished run is immutable. Acquire a new output directory to change markets or options.
