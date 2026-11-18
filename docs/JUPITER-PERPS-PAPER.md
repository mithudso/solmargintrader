# Jupiter Perps paper panel and leverage replay

Open the [SOL JupUSD route](https://jup.ag/perps/long/JupUSD-SOL) with the unpacked SolMarginTrader extension. The floating **Perps paper** panel follows the market and side in the URL. It opens on the ETH, BTC, ZEC and HYPE routes too. The window can be dragged, resized or collapsed. Each market starts with $1,000 of virtual equity. Chrome restores the paper accounts from local IndexedDB.

Select **Fixed collateral** to keep the dollar margin constant as leverage changes. Select **Fixed notional** to keep the exposure constant and vary the margin. Take-profit and stop-loss are distances from entry in underlying price percent. A zero disables that level. The chart and preview show entry, estimated liquidation, take-profit and stop-loss. A stop at or beyond estimated liquidation displays a warning. The preview uses the currently selected side and full requested size. A strategy may open a smaller position based on its signal.

**Open paper** and **Close paper** use observed quotes. Select a strategy and use **Start strategy** to trade a new closed-bar signal or armed Volty level. Volty supports **Long**, **Short** and **Long and short**. The two-sided choice holds one net position per market and can admit either direction. A one-sided choice keeps the opposite signal as an exit. Long-only presets supply long signals. The ZEC **Volty 10 × 1.5** preset matches the ungated five-minute rule in the [frozen direction study](../research/papers/results/zec_gum_25x_5m_directions.md).

**Open positions** lists the saved paper positions across all five markets. Choose **TP / SL and signals** to edit the position's price exits or add indicator exits. MACD can cross above or below its signal line. RSI can cross 30 or 60 in either configured direction. **Any rule** uses the first qualifying newly closed candle. **All on one candle** requires all chosen crosses on that candle. A price stop can fill at a worse sampled price after a gap. Liquidation takes priority. Managing a position does not arm orders on Jupiter.

Keep at least one Perps panel open to evaluate positions. Market changes and browser reloads preserve saved positions and rules. After a missed quote interval the engine pauses strategy entries and checks existing price exits on the next fresh mark. It cannot recover intervening marks or guarantee an indicator-triggered fill while all panels were closed.

## Indicators and learning

The chart uses the 1000x indicator calculations on completed Perps candles for EMA 9/21, MACD, RSI, Balance of Power, Volty, Parabolic SAR and confirmed ZigZag. Each market has a separate prospective closed-minute price learner for the six 1000x horizons. The learner waits for enough consecutive native bars and a fresh source mark. It resolves samples only from complete future closes after their forecast was issued. The separate 1000x high-frequency quote learner needs its own faster feed.

Paper entries capture the shared 1000x feature vector from contiguous completed one-minute candles. Each close writes the trade and updates the after-cost model once in the same IndexedDB transaction. Trade outcomes are separated by venue, market, side, strategy and candle interval. The panel shows sample counts and displays estimates when a model warms up. Forecasts do not authorize orders or override stops. **Export trades** downloads a JSON copy of the saved trade journal. The journal and open paper positions survive browser restarts in the same Chrome profile.

## Market and fee rules

| Portal market | Product | Leverage cap observed | Costs and liquidation |
| --- | --- | ---: | --- |
| SOL, ETH, BTC | Oracle-priced JLP Perps with JupUSD input routes | 250× | 6 bps base on open and close. Linear impact rounds up to whole bps and is at least 1 bp at the tested sizes. Additive impact depends on recent imbalance. The current impact cap is 44 bps per side. Borrow accrues on position notional. Liquidation uses 20 bps maintenance plus closing base and linear fees and accrued borrow. |
| ZEC | GUM Beta, USDC collateral | 50× | 3.5 bps taker, 0.5 bps maker, 75 bps liquidation fee. Hourly directional funding. First maintenance tier is 100 bps. |
| HYPE | GUM Beta, USDC collateral | 25× | Same observed GUM fees. First maintenance tier is 200 bps. |

JupUSD in the ZEC and HYPE URLs does not change their underlying product. GUM documents no venue-native TP/SL for these markets. The controls in this panel simulate exits on observed prices. GUM paper position sizes are restricted to the modeled first maintenance tier and market-order quantity and notional limits. Neither product model sends orders.

The panel reads current JLP base fee, impact cap and side-specific hourly borrow from the portal's public pool-info endpoint. The linear impact step follows the documented example values for SOL, ETH and BTC. JLP fees and liquidation can differ when price impact, conversion costs or pool settings change. GUM market terms and one-hour funding are read from the public markets and funding endpoints. Its chart shows trades and the paper engine observes the separate mark. The JLP chart and quotes use Jupiter Pyth. Source clocks and missing data pause automatic entries.

Sources

- https://docs.jup.ag/user-docs/trade/perps/fees
- https://docs.jup.ag/user-docs/trade/perps/liquidation
- https://docs.jup.ag/user-docs/trade/perps/beta-markets
- https://api.gum.ag/app/perps/markets

## Seven-day replay

The replay captured 10,080 contiguous one-minute candles per market from **November 11 01:10 to November 18 01:10 UTC, 2026**. It used the final 2,016 minutes, from **November 16 15:34 UTC**, as the held-out comparison. The previous 20% is also reported in the CSV. The first 60% provides signal history. The run has **3,894 configuration rows**, each with separate validation and test P&L.

The candidates include the ZEC five-minute mean, Z-score and Bollinger strategies, the SOL and ETH hourly Volty settings selected on the prior study's worst validation path, and all 62 positive unfiltered ZEC archive presets whose RSI/Z-score/Bollinger rules can be reproduced. Five headline strategies were transferred across all five markets. The other profitable rows in the earlier study use additional mechanisms this panel does not implement.

The ZEC ensemble retains the three thresholds and uses their mean to size a new paper entry. It holds that size until exit, so its perp replay does not reproduce the spot study's fractional rebalancing. Volty uses the previous closed bar's stop levels and reverses at the opposite stop. Minute bars that hit both entry stops from flat are skipped. The replay resolves other ambiguous prices adversely, and treats a gap through a stop using the next opening price. Current funding and borrow readings were frozen as scenarios. The replay includes 2 bps slippage and $0.01 network cost per side, JLP linear impact at the documented rate, zero additive impact, and no collateral conversion. Historical GUM trade candles are a proxy for mark and book paths. Intraminute order, fills, latency and historical net flow remain unobserved.

| Scenario on $1,000 paper equity | Higher leverage | Lower leverage or exit change |
| --- | --- | --- |
| SOL hourly Volty, $25 collateral, signal exits | 250× lost 30.00%, 12 liquidations in 12 exits | 50× lost 6.63%, zero liquidations in nine exits |
| ETH hourly Volty, $25 collateral, 1.5% TP and 0.8% SL | 250× lost 32.50%, 13 liquidations in 13 exits | 50× gained 3.47%, zero liquidations in nine exits |
| ZEC five-minute mean, $250 notional, 1.5% TP and 0.8% SL | 50× lost 1.32%, seven liquidations in seven exits | 25× gained 0.75%, zero liquidations in six exits |
| HYPE five-minute mean transfer, $250 notional, same brackets | 25× lost 0.05%, one liquidation in seven exits | 5× gained 0.14%, zero liquidations in seven exits |
| BTC hourly SOL Volty transfer, $25 collateral, signal exits | 250× lost 35.00%, 14 liquidations in 14 exits | 5× lost 0.06%, zero liquidations in seven exits |

At the tested $25 JLP margin and 250×, the modeled initial liquidation threshold was about **0.06% from the assumed entry price** before carry. A 0.8% stop could not protect that position. At 50× the same formula left roughly 1.66%. In ZEC at a fixed $250 notional, 25× widened the illustrative buffer from 0.18% to 2.22% while keeping gross exposure roughly the same after lot rounding. That is the most direct example of the wider safety margin. SOL and BTC still lost on the illustrated settings after liquidation disappeared. The comparisons overlap in time and often share signals, so total exits across presets are descriptive.

Read [the complete replay grid](../research/results/jupiter_perps_leverage_20261118.csv) for both sizing bases and three exit profiles. The tight profile uses 0.5% take-profit and 0.3% stop-loss. The wide profile uses 1.5% and 0.8%. Signal-only has no extra bracket. Validation and test results did not change the published prior strategy presets.

## Reproduce

Run from the repository root. Use a new output directory to capture data and `--offline` to replay an existing capture. The CLI issues public reads in acquisition mode. The input and result hashes are in the [companion receipt](../research/json/results/jupiter_perps_leverage_20261118_receipt.json). Reobserved funding or venue-candle revisions can change a fresh capture.

```sh
node research/scripts/perps/perps-sweep.mjs --output /absolute/path/to/new-perps-capture --end 2026-11-18T01:10:00Z
node research/scripts/perps/perps-sweep.mjs --offline --output /absolute/path/to/new-perps-capture --end 2026-11-18T01:10:00Z
```

## Funded execution requirements

Funded position inventory and execution require an authenticated venue account source and a verified execution owner with order, position and settlement reconciliation. The Perps panel receives public market data and reports the live position inventory as unavailable. Existing 1000x controls, paper owners and account state keep their separate product bindings.
