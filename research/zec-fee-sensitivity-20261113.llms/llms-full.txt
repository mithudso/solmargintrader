# ZEC fee sensitivity at 0.25% and 0.15% per fill

Version: 1.0.0

The owner clarified the requested fees as **0.25% and 0.15%**, equivalent to **25 and 15 basis points per fill**. Both entries and exits pay that scenario rate. This reruns the complete prior captured-event matrix, changing fees only.

**These are conditional fee-rate results.** The existing simulator crosses recorded book depth; it does not model passive maker orders, queue priority or whether an order would receive a maker fee. Observed spread/depth, 2 bps adverse residual slippage and receipt-time latency remain in the calculation.

## Spot results

Best *active* spot return in each interval, after all modelled costs:

| Signal bars | 0.25% per fill | 0.15% per fill | Positive / active at 0.25% | Positive / active at 0.15% |
|---|---:|---:|---:|---:|
| 1m | -0.3363% | +0.6308% | 0 / 786 | 1 / 786 |
| 5m | +1.0822% | +1.8939% | 53 / 336 | 62 / 336 |
| 10m | +1.8230% | +2.0268% | 32 / 117 | 32 / 117 |
| 1h | -0.8216% | -0.7020% | 0 / 2 | 0 / 2 |

At 0.15%, the lone positive active 1m spot template combines RSI, z-score and Bollinger reversion with the `all` rule. It returned +0.6308% with 18 fills. At 0.25%, every active 1m spot template lost money. The best 5m case uses ADX to switch between swing-confluence and Bollinger reversion (8 fills); the best 10m case uses swing-confluence OR RSI (2 fills). The best active hourly spot case remains DCA and loses at both fee rates.

The leaders are descriptive maxima from hundreds of related templates, not winners chosen before this day. Only three hourly spot templates have enough contiguous warm-up history, and only two trade. Smaller bars do not create additional independent market days. No calibrated prediction accuracy or persistent profit is established.

Passive capture-start buy-and-hold returned **-9.1542% at 0.25%** and **-8.9723% at 0.15%**; cash returned 0%.

## Synthetic Volty scenarios

These separate scenarios assume 1x long/short margin exposure on spot prices and 0.1 bps/hour carry. They do not establish Coinbase short capacity or Jupiter funding/liquidation execution. Best active returns:

| Signal bars | 0.25% per fill | 0.15% per fill | Positive / active at 0.25% | Positive / active at 0.15% |
|---|---:|---:|---:|---:|
| 1m | -58.1498% | -46.2397% | 0 / 50 | 0 / 50 |
| 5m | -17.8288% | -13.0658% | 0 / 50 | 0 / 50 |
| 10m | -12.2645% | -10.2852% | 0 / 50 | 0 / 50 |
| 1h | +0.2466% | +0.4457% | 2 / 42 | 3 / 42 |

The small positive hourly Volty maxima each came from one round trip. Every active 1m, 5m and 10m Volty configuration lost money at both fee rates.

## Frozen scope and verification

- Same 827 spot parameter/ensemble templates and 50 Volty configurations, at actual 1m/5m/10m/1h closed signal bars. Two fee scenarios produce 7,060 rows: 3,252 completed strategy/benchmark rows, 3,780 insufficient-warm-up rows and 28 explicit unsupported-family rows.
- The baseline universe, all 52 imported simulation source files, interpreter and NumPy/pandas versions match the accepted original run exactly. No simulation code changed. All 3,516 rows at 25 bps exactly equal the prior accepted 25 bps results, field for field.
- Original Coinbase ZEC-USD run `50dbd4f31de24c36a30d8c3786495ad5`, 2026-11-12T04:56:27.224912Z through 2026-11-13T04:56:27.224912Z. The immutable WAL has 1,459,542 records and 134,746 match events. SHA256 `eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31`. Original WAL and prepared tape/capture hashes were independently reread and matched. Prior raw-book reconstruction evidence transfers only because the exact tape bytes match.
- Same receipt-time OHLCV, prefix-only signals, detected-gap resets, fixed weighted-training prefix, next-eligible received 1-second book samples, 1-second minimum latency, 2-second maximum book wait, 40-level capacity, $10,000 initial account and fixed-deadline liquidation. All positions closed within 1e-8 ZEC. Terminal book age: 0.220432 seconds.
- Receipt-time quotes remain reference prices. The baseline audit measured exchange-message lag up to 13.266 seconds during recovery. Lower fees do not remove delayed-data or live-execution limitations. Decision/fill drawdown is sampled and may miss intrabar extremes.
- Actual perp wrappers, resting ladder execution, paired/BTC-dependent compound, pairs and nonexecutable cards remain explicit exclusions. The registered exposure-staircase grid is included separately.
- Full rerun exited 0. The existing 39-test focused gate and Ruff passed with exit 0. The independent auditor verified all 7,060 keys/statuses and 13 run-artifact hashes, every one of 217,445 fills at both fee rates, and 14 complete SMA/hold cases with direct arithmetic and a separate ledger. Maximum cash discrepancy: 9.37e-11 USD; price discrepancy: 7.96e-13.

## Shared evidence

The complete CSV and frozen parameters are in `research/zec-fee-sensitivity-20261113.llms/`, with `summary.json`, `coverage.json`, `identity.json`, `plan.json.gz`, `rerun-provenance.json`, the original run `manifest.json`, independent `audit.json`, `archive-manifest.json` and `mongo-artifacts.json`. The actual key is `(interval,candidate_id,fee_bps)`; inherited candidate IDs are parameter-template IDs, not interval-qualified Oracle policies.

Private full fills, tape and driver: `/Users/mitch/.local/state/solmargintrader/zec-fee-sensitivity-20261113/`. Accepted output: its `attempt-01/` directory. The unchanged baseline remains `/Users/mitch/.local/state/solmargintrader/zec-granular-backtests-20261113/attempt-03/`. Nothing overwrote the earlier accepted run.

Mongo empirical run `run:80719ee0ab3841dcabf1d0723c982e16f8385d3b082f988d4641d55c97df0bfa` stores immutable result/report/plan/audit artifacts and links the prior run. This is computational evidence storage, not trusted literature qualification. No paid research, inference, embedding, live orders or runtime service changes occurred.

Original methodology and earlier 10/25/60 bps comparisons: `research/ZEC-GRANULAR-BACKTESTS.md`.
