# ZEC Volty TradingView alert review

Version: 1.0.1. Delta: 1.0.0 to 1.0.1; add authenticated chart settings, displayed results and current Coinbase fee comparison.

As of 2026-11-11, the available evidence does not validate enabling the listed Volty strategy as a live Coinbase spot strategy. The authenticated chart and its settings were inspected in Chrome after the user completed sign-in. No alert was created or enabled.

## What was verified

The existing study, [VOLTY-ZEC-STUDY.md](VOLTY-ZEC-STUDY.md), evaluates the original stop-entry mechanism. It uses prior close plus/minus a simple moving average of true range times the multiplier. Stops become active on the next bar. Opposite fills reverse between long and short; same-side triggers do not pyramid. The recovered Pine source uses entry IDs `VltClsLE` and `VltClsSE` and default length 5, multiplier 0.75. The shown source has no separate protective stop-loss or take-profit.

The independent review verified the nine final artifact hashes and both captured source-page hashes. Four tracked result copies match the authoritative outputs. Six focused causal/mechanics tests passed. This validates the integrity and limited mechanics of the study, not a profitable strategy or certified TradingView fill parity.

## Economic evidence

The first half of each history selected one fixed configuration from 50 candidates; the second half was held out. All five selected fixed winners lost:

| Timeframe | Selected length / multiplier | Held-out net return |
| --- | --- | --- |
| 1m | 10 / 1.25 | -99.999% |
| 5m | 7 / 1.25 | -71.917% |
| 10m | 8 / 1.25 | -64.734% |
| 1h | 8 / 1.25 | -99.378% |
| 1d | 10 / 1.25 | -75.050% |

A different procedure that reselected daily parameters from past-only expanding windows returned +22.688%. Passive ZEC over that comparison returned +1783.710%. The +1203.522% full-history daily leader is an in-sample result. Neither result establishes an edge for a fixed alert configuration.

These numbers come from Binance spot ZEC/USDT candles with a synthetic long/short book, 1x equity at entry, fixed units until reversal, 10 bps fee and 2 bps adverse slippage per side, plus synthetic carry. They are not actual Coinbase fills, observed borrowing/funding, or measured returns of the 75% spot webhook. The independent OHLC fill-path model has no certified TradingView broker-emulator parity. The five frozen future-paper specifications are `prepared_not_running`; there is no prospective Volty paper result to promote.

## Coinbase execution mismatch

The deployed webhook uses the owner's explicit policy: buy with 75% of available quote currency or sell 75% of available base currency. It ignores the Pine strategy's quantity and position state. It does not open shorts.

For example, when Volty changes from long to short, a `sell` alert would sell only 75% of available ZEC. It would leave 25% long, instead of flattening and opening the simulated short. A later `buy` alert would add ZEC instead of covering that short and reversing. Therefore the webhook produces a different, long-biased strategy. A profitable Strategy Tester display for the original cannot validate that spot implementation.

The chart's quote currency also matters. The webhook preserves the exact base/quote pair and does not replace ZEC-USDT with ZEC-USD or ZEC-USDC. The Coinbase product and available funding currency must be checked for the actual loaded chart before creating the alert.

## Actual listed chart

The inspected saved layout uses **CRYPTO:ZECUSD at 1 minute**, with the built-in **Volty Expan Close Strategy**, **Length 5**, and **ATR Mult 1**. An update is available for the loaded strategy; it was not applied. Other chart indicators were preserved.

The actual Properties dialog showed:

| Setting | Observed value |
| --- | --- |
| Initial capital | 100,000 USD |
| Default order size | 100% of equity |
| Pyramiding | 1 |
| Bar detalization | High (about 24 ticks per bar) |
| Script execution | On bar close |
| Commission | 0 percent |
| Long leverage | 2x |
| Short leverage | 2x |
| Slippage | 0 ticks |
| Order execution delay | One tick |

The displayed report covered **Oct 25–Nov 11, 2026**, with approximately **+2784.68%** total PnL, **4.32%** maximum drawdown, **3,738** trades, **47.89%** profitable trades, **2.185** profit factor and approximately **0.09%** average trade expectancy. These are the site's simulated figures under the listed zero-cost settings, not independently verified fills. They can update with the live bar.

The authenticated Coinbase fee read returned a **0.009 taker rate (0.9% per side)**. The webhook submits market orders. The approximate 1.8% two-sided fee scale is about twenty times the displayed 0.09% average trade expectancy, before slippage. This is a cost-scale comparison, not an exact recomputation of cost-adjusted PnL. The existing study already loses with a lower 0.1% fee per side, though it uses a different source, date range and fill model.

Coinbase confirmed that ZEC-USD is an online spot product. That establishes product availability, not agreement between Coinbase executable prices and the CRYPTO aggregate chart, funding availability, or a valid short-execution path.

The exact 1m length-5/multiplier-1 row in the existing 90-day sweep reports approximately -100% full-history return under its declared costed synthetic model. It is corroborating negative evidence, not a matched reproduction of this shorter TradingView report.

## Decision and next action

Do not enable live alerts under the current evidence. The displayed result excludes actual Coinbase fees, permits 2x leverage and simulates long/short execution, and does not match the deployed spot-percentage policy. This is a failure of the requested validation condition, not an added Oracle prediction gate.

A paper-only alert or an explicitly defined spot adaptation can be evaluated separately. Changing the strategy, quote pair, sizing, exits, or execution model requires a fresh matched test; this review does not authorize silently making those changes. The chart inputs and Properties were inspected without changing their saved values. No webhook secret was entered into TradingView, and no alert or trade was submitted.

## Evidence paths

- Study report: `docs/VOLTY-ZEC-STUDY.md`.
- Simulator: `backtester/core/volty.py`.
- Research runner: `research/volty_zec.py`.
- Selected-winner results: `research/results/volty_zec_20261110_winners.csv`.
- All-trial results: `research/results/volty_zec_20261110_sweep.csv`.
- Walk-forward results: `research/results/volty_zec_20261110_walk_forward.csv`.
- Source/data/artifact binding: `research/results/volty_zec_20261110_manifest.json`.
- Original source reference: https://www.tradingview.com/support/solutions/43000599890-volty-expan-close-strategy/
- Spot webhook contract: `oracle/README.md`, `oracle/coinbase_orders.py`, `oracle/webhook_orders.py`.
