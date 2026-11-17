# ETH weekly candle study

Version: 1.0.0
UTC window: 2026-11-10T17:13:00Z to 2026-11-17T17:13:00Z (exclusive).
Source: Binance spot ETH/USDT, 10,080 completed one-minute bars.

This is an exploratory transfer of the ZEC candle studies. It does not qualify an executable edge or a live trading change.

## Scope and controls

The frozen catalogue contains 1,707 spot templates. The run uses all six baseline/shape/frequency/control modes on 1m, 5m, 10m and 1h bars. Fees are 10/15/25/60bps per fill plus 2bps modelled execution cost. Decisions use closed bars and spot exposure fills at the next open. Fresh accounts evaluate the chronological 60/20/20 windows; the selected policy is chosen only by validation return with at least ten validation exits.

Strategy matrix: 491,712 rows, including 441,888 completed evaluations. Special Volty/grid/DCA models: 7,920 rows. A completed evaluation is not evidence of profitability. Thousands of overlapping candidates are not independent trials.

Captured receive-time book replay, Oracle second-turn/barrier/exit50 studies, the historical top50 universe and daily CPCV need unavailable inputs or longer history. The original hourly/six-hour/daily shape router also lacks its required selection history. Exact transferred scopes and exclusions are in coverage.json.

## Correlations

Searched 18 causal features across six future-return horizons. Outcomes do not overlap within a horizon and are purged at split ends. All validation and test feature/horizon tests share an approximate 60-minute block-permutation maximum-statistic correction (1,999 replicates). Spearman values and contemporaneous correlations are descriptive.

Corrected test associations at p <= 0.05: **0**. These are associations under an approximate stationary null, not causal effects or net trading profits.

| Same-minute return comparison | Pearson r | Observations |
|---|---:|---:|
| ETH / BTC | 0.9019 | 10,079 |
| ETH / ZEC | 0.7047 | 10,079 |

Same-minute co-movement does not establish that the reference coin leads the target.

The following shortlist was fixed by absolute training correlation, before inspecting validation or test:

| Feature | Horizon | Train r | Validation r | Test r | Corrected test p |
|---|---:|---:|---:|---:|---:|
| return_5m | 60m | 0.1263 | 0.1162 | -0.5371 | 0.0785 |
| return_15m | 60m | 0.1149 | 0.1811 | -0.4096 | 0.3200 |
| volatility_30m | 60m | -0.1136 | 0.3325 | -0.3543 | 0.5495 |
| range_fraction | 60m | -0.1036 | 0.2347 | -0.4990 | 0.1320 |
| volatility_30m | 30m | -0.0968 | 0.1378 | -0.3380 | 0.6260 |
| BTC_return_15m | 30m | -0.0954 | 0.1906 | -0.3177 | 0.7230 |
| BTC_return_5m | 60m | 0.0948 | 0.2841 | -0.4968 | 0.1345 |
| BTC_return_15m | 60m | 0.0914 | 0.2187 | -0.4109 | 0.3160 |
| volatility_30m | 15m | -0.0874 | 0.1505 | -0.1532 | 1.0000 |
| BTC_return_1m | 15m | -0.0742 | -0.1604 | -0.2235 | 0.9885 |
| log_volume | 60m | -0.0707 | 0.0628 | -0.2101 | 0.9965 |
| range_position_48m | 60m | 0.0705 | -0.0352 | -0.2289 | 0.9855 |

## Frozen validation selections

| Cadence | Fee bps/fill | Policy | Mode | Validation return | Test return | Test exits |
|---|---:|---|---|---:|---:|---:|
| 1m | 10 | 627d7f8af016802981ea3b55 | baseline | 1.45% | -2.97% | 15 |
| 1m | 15 | 627d7f8af016802981ea3b55 | baseline | 0.24% | -4.41% | 15 |
| 1m | 25 | 3440ccda392e28465604a354 | linear_control | -1.69% | -2.41% | 134 |
| 1m | 60 | 3440ccda392e28465604a354 | linear_control | -3.91% | -5.61% | 142 |
| 5m | 10 | 56e04783ea4af1fec7bb825d | baseline | 4.65% | -2.94% | 11 |
| 5m | 15 | 56e04783ea4af1fec7bb825d | baseline | 3.61% | -4.00% | 11 |
| 5m | 25 | 56e04783ea4af1fec7bb825d | baseline | 1.56% | -6.09% | 11 |
| 5m | 60 | 175e22ba554a075641d55455 | shape | -1.13% | -13.08% | 34 |
| 10m | 10 | 4190b910edd3ca4426494fa1 | baseline | 2.80% | -2.25% | 1 |
| 10m | 15 | 4190b910edd3ca4426494fa1 | baseline | 2.69% | -2.35% | 1 |
| 10m | 25 | 4190b910edd3ca4426494fa1 | baseline | 2.49% | -2.54% | 1 |
| 10m | 60 | 4190b910edd3ca4426494fa1 | baseline | 1.76% | -3.22% | 1 |
| 1h | 10 | a894838beff8b3be57f90040 | baseline | 3.56% | 0.20% | 6 |
| 1h | 15 | a894838beff8b3be57f90040 | baseline | 3.38% | 0.10% | 6 |
| 1h | 25 | a894838beff8b3be57f90040 | baseline | 3.01% | -0.10% | 6 |
| 1h | 60 | a894838beff8b3be57f90040 | baseline | 1.74% | -0.80% | 6 |

Rows without ten validation exits cannot select a winner. Test results are reported for the frozen selection and never used to rerank it. These short-window returns have no multiple-search profit qualification.

## Cycles and causal controls

Across global spectra and rolling training-prefix fits, 1,638 whole-search null tests received one Holm correction. Minimum corrected p-value: 1.000000. The smallest attainable first Holm p-value with this test count and replicate budget is 0.819000. This cycle significance result is resolution-limited and inconclusive when that floor exceeds 0.05; it is not evidence against a cycle. Short-window selected periods and retrospective pivot spacing do not establish a stable clock.

## Limits and reproduction

One week contains very few independent market regimes. Results reuse existing ZEC hypotheses and modelled costs; observed spreads, funding, depth, latency and fills are absent. Approximate permutation inference assumes sufficiently stable dependence. Monte Carlo resolution can prevent significance after broad corrections. Annualized Sharpe ratios are deliberately omitted from the weekly summary.

Raw provider pages and normalized candles are retained together in inputs/*.json.zlib. run-plan.json.zlib freezes the complete card/queue census, templates, source hashes, options and exclusion mapping. manifest.json binds all generated artifacts. The script verifies raw-page normalization, immutable artifacts and report arithmetic offline.

```bash
python -m research.coin_week --coin ETH --output /absolute/path/to/new-study
python -m research.coin_week --coin ETH --output /absolute/path/to/new-study --resume
python -m research.coin_week --output /absolute/path/to/new-study --phase verify
```
