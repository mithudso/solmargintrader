# Native market combination backtests

Report version: 2.0.0

## Exactly what was requested

Coins: **ETH, BTC, ZEC**. Added cash quote: **USD**. Venue: **Coinbase Exchange spot**.
Requested acquisition: **2026-11-10T19:46:00Z to 2026-11-17T19:46:00Z**, exclusive. Each available native market downloads real one-minute candles once. No cross-pair OHLC is synthesized.
The frozen universe contains **6 unordered combinations**. Opposite pair order is not a second test: if the exchange lists BTC/ETH instead of ETH/BTC, that native orientation and its quote currency are reported below. Self-pairs are excluded. Delisted and absent products remain visible.
The catalogue is a current listing snapshot, not a reconstruction of historical listings. An unavailable current product is not proof that it never traded during the requested week.
Backtest history policy: **longest**, with at least **1,440 consecutive real minutes**. Reduced windows are labelled per market. Missing minutes are never interpolated.
3 native markets backtested; 3 unavailable or insufficient; 0 failed. Status: **completed**.

## Market-by-market coverage

| Requested combination | Actual native market/product | Account currency | Status/reason | Actual backtest input UTC (end exclusive) | Real minutes | Report |
|---|---|---|---|---|---:|---|
| ETH/BTC | ETH/BTC (`ETH-BTC`) | BTC | insufficient_history: fewer than 1440 consecutive real minutes; no candles filled; **REDUCED WINDOW** | 2026-11-17T08:59:00Z to 2026-11-17T15:21:00Z | 382 | — |
| ETH/ZEC | No native listing | ZEC | not_listed: absent from frozen venue catalogue | — | — | — |
| ETH/USD | ETH/USD (`ETH-USD`) | USD | completed: native candles, full transferred analysis; **REDUCED WINDOW** | 2026-11-10T19:46:00Z to 2026-11-13T20:16:00Z | 4350 | [Detailed market report](markets/ETH-USD/report.md) |
| BTC/ZEC | ZEC/BTC (`ZEC-BTC`) | BTC | inactive: delisted | — | — | — |
| BTC/USD | BTC/USD (`BTC-USD`) | USD | completed: native candles, full transferred analysis; **REDUCED WINDOW** | 2026-11-10T19:46:00Z to 2026-11-13T20:16:00Z | 4350 | [Detailed market report](markets/BTC-USD/report.md) |
| ZEC/USD | ZEC/USD (`ZEC-USD`) | USD | completed: native candles, full transferred analysis; **REDUCED WINDOW** | 2026-11-11T00:16:00Z to 2026-11-12T19:46:00Z | 2610 | [Detailed market report](markets/ZEC-USD/report.md) |

## Tests inside each market report

Each completed native market runs the ZEC candle-supported spot catalogue in six filter/control variants at 1m, 5m, 10m and 1h, four fee scenarios plus 2 bps execution allowance, cash/passive controls, synthetic Volty and canonical grid/DCA reference simulations, cycle diagnostics and reversal studies. The detailed reports spell out every selected strategy's member parameters, internal gates, fallback, persistence, weighting and additional shape/harmonic/linear filter.
Training/validation/final test are chronological 60/20/20. Validation alone selects policies with at least ten validation exits. Test results never rerank candidates. Short-window strategy profits remain exploratory and have no multiple-search profitability qualification.
Return-correlation diagnostics compare future returns of the actual target market with past-only features and reference markets sharing its quote. They are separate from native pair trading tests. Same-minute co-movement is descriptive, not a leading signal.
Every future-return correlation uses the within-market max-statistic correction, then a conservative Bonferroni multiplier of **6 planned combinations**, including unavailable ones. Cycle Holm corrections are within-market only; no batch-wide cycle significance claim is made.
Quote units differ across native pairs: ETH/BTC returns and fees are in BTC, while ETH/USD uses USD. Reference accounts begin with 10,000 of their own quote units without a capacity model. Their P&L cannot be added or compared as a common dollar account without a separate conversion/execution model.

## Correlation findings by target market

| Actual target | Computed / insufficient / constant final-test feature tests | Batch-family corrected final-test associations (p ≤ 0.05) |
|---|---:|---:|
| ETH/USD | 72 / 36 / 0 | 0 |
| BTC/USD | 72 / 36 / 0 | 0 |
| ZEC/USD | 72 / 36 / 0 | 0 |

## Integrity and continuation

batch-plan.json.zlib freezes the combination census, analytical options, source identity and current catalogue. market-catalogue.json.zlib preserves the exact catalogue response. shared-inputs retain exact candle pages; each market receives byte-identical input copies. input-binding.json freezes acquisition before analysis. batch-manifest.json binds parent and child artifacts; offline verification rechecks every child report, source normalization, count and market identity.
Use --resume with this output to continue its frozen plan. Use --phase verify to verify offline. Finished studies are immutable; choose a new output to change coins or options. An acquisition or analysis failure leaves a partial report and a nonzero exit status; it is not relabelled as an absent market.
