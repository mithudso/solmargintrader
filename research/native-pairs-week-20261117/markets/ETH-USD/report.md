# ETH/USD: native spot market backtest and correlation study

Report version: 2.0.0

## Exactly what was tested

**Trading market: ETH/USD. Venue: Coinbase Exchange spot. Native product: ETH-USD. Prices, fees, cash and account equity use USD.**
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
| 1m | 10 | single [fib retracement {"entry_ratio": 0.2865, "invalid_ratio": 0.786, "lookback": 120}] (`3f022f47b5ffe197135461dc`) | Underlying strategy + causal 48-bar shape filter | -0.62% | -3.09% | 19 |
| 1m | 15 | single [grid {"anchor_window": 48, "levels": 8, "step": 0.03}] (`8b800359b3ecf7907deec0a9`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.89% | -0.95% | 85 |
| 1m | 25 | single [grid {"anchor_window": 48, "levels": 8, "step": 0.03}] (`8b800359b3ecf7907deec0a9`) | Underlying strategy + positive 64-bar log-price regression slope filter | -1.41% | -1.62% | 86 |
| 1m | 60 | single [grid {"anchor_window": 48, "levels": 8, "step": 0.03}] (`8b800359b3ecf7907deec0a9`) | Underlying strategy + positive 64-bar log-price regression slope filter | -3.21% | -3.92% | 90 |
| 5m | 10 | weighted [rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}; zscore {"entry_z": -2.0, "exit_z": 0.0, "window": 20}; bb reversion {"num_std": 2.0, "window": 20}] (`1f3f55af212891c52bda4bc4`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.12% | -0.17% | 5 |
| 5m | 15 | single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}] (`3440ccda392e28465604a354`) | Underlying strategy + causal 48-bar shape filter | -0.20% | 0.05% | 52 |
| 5m | 25 | single [grid {"anchor_window": 240, "levels": 4, "step": 0.1}] (`a443e20c7a06fadf8c7a8e07`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.31% | -0.26% | 38 |
| 5m | 60 | single [grid {"anchor_window": 240, "levels": 4, "step": 0.1}] (`a443e20c7a06fadf8c7a8e07`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.49% | -0.79% | 38 |
| 10m | 10 | single [ma ribbon {"base": 10, "windows": 4}] (`5042cef948abcd163ca09d1f`) | Underlying strategy + positive 64-bar log-price regression slope filter | -0.22% | -2.08% | 13 |
| 10m | 15 | single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}] (`3440ccda392e28465604a354`) | Underlying strategy + causal 48-bar shape filter | -0.32% | -0.08% | 30 |
| 10m | 25 | single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}] (`3440ccda392e28465604a354`) | Underlying strategy + causal 48-bar shape filter | -0.37% | -0.20% | 30 |
| 10m | 60 | single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}] (`3440ccda392e28465604a354`) | Underlying strategy + causal 48-bar shape filter | -0.55% | -0.64% | 30 |

Selected policy definitions (parameters are the frozen configuration):

- `3f022f47b5ffe197135461dc` at 1m: single [fib retracement {"entry_ratio": 0.2865, "invalid_ratio": 0.786, "lookback": 120}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `8b800359b3ecf7907deec0a9` at 1m: single [grid {"anchor_window": 48, "levels": 8, "step": 0.03}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `1f3f55af212891c52bda4bc4` at 5m: weighted [rsi {"exit_level": 50.0, "oversold": 30.0, "period": 14}; zscore {"entry_z": -2.0, "exit_z": 0.0, "window": 20}; bb reversion {"num_std": 2.0, "window": 20}]. persistence=1 bars; exposure rebalance threshold=0.0. weights fitted by inverse-absolute-correlation on the initial max(member warmup + 64, 256) bars, before validation; configured seed weights are not the fitted weights.
- `3440ccda392e28465604a354` at 5m: single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `a443e20c7a06fadf8c7a8e07` at 5m: single [grid {"anchor_window": 240, "levels": 4, "step": 0.1}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `5042cef948abcd163ca09d1f` at 10m: single [ma ribbon {"base": 10, "windows": 4}]. persistence=1 bars; exposure rebalance threshold=0.0.
- `3440ccda392e28465604a354` at 10m: single [grid {"anchor_window": 120, "levels": 8, "step": 0.1}]. persistence=1 bars; exposure rebalance threshold=0.0.

All candidate member parameters and underlying policy configurations, including candidates that were not selected, are retained in run-plan.json.zlib. Strategy result files identify candidate_id, mode, cadence, split and fee scenario.

## Return correlations: diagnostics separate from market backtests

Target: future **ETH/USD log returns**, at 1/5/10/15/30/60-minute horizons. Predictors: past-only target returns, candle body/range, volume, volatility, range position, and available reference-market returns. All reference markets share the target's USD quote and venue. A comparison of ETH/USD returns with BTC/USD returns is not an ETH/BTC market backtest.
Searched 18 features. Outcomes are nonoverlapping within each horizon and purged at split ends. An approximate 60-minute block-permutation maximum statistic covers every validation/test feature and horizon (1,999 replicates). The resulting p-values are then multiplied by 6 planned market combinations (Bonferroni, capped at one) for batch-wide claims. Train correlations rank the shortlist before validation or test is inspected.
**Batch-family corrected final-test associations at p ≤ 0.05: 0.** An association under this approximate stationary null does not establish a causal effect, a leading trade or net profit.

| Same-minute return comparison (descriptive only) | Pearson r | Matched observations |
|---|---:|---:|
| ETH/USD returns vs BTC/USD returns | 0.8865 | 4,349 |
| ETH/USD returns vs ZEC/USD returns | 0.6641 | 4,341 |

| Training-selected predictor | Future horizon | Train r | Validation r | Test r | Batch-family test p |
|---|---:|---:|---:|---:|---:|
| volatility_30m | 30m | 0.2599 | unavailable | unavailable | unavailable |
| BTC_return_15m | 60m | 0.2109 | unavailable | unavailable | unavailable |
| ZEC_return_60m | 30m | -0.2032 | unavailable | unavailable | unavailable |
| volume_relative_60m | 10m | -0.1836 | 0.0864 | 0.0232 | 1.0000 |
| ZEC_return_5m | 15m | 0.1828 | -0.2568 | 0.1226 | 1.0000 |
| volatility_30m | 15m | 0.1808 | -0.3891 | -0.2164 | 1.0000 |
| volume_relative_60m | 15m | -0.1796 | -0.0156 | 0.0230 | 1.0000 |
| return_15m | 10m | -0.1753 | -0.1338 | -0.0120 | 1.0000 |
| ZEC_return_5m | 60m | -0.1734 | unavailable | unavailable | unavailable |
| ZEC_return_60m | 15m | -0.1719 | 0.0615 | 0.1947 | 1.0000 |
| return_15m | 15m | -0.1681 | 0.1407 | -0.0557 | 1.0000 |
| volatility_30m | 60m | 0.1675 | unavailable | unavailable | unavailable |

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
