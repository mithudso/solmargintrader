# TradingView Price Channel: source contract and open research

Version: 0.1.0. Delta: record v29 intent semantics and limitations.

This is a research contract extension, not a replacement for the existing
checksum-bound research-only Price Channel card and not a completed rabbithole.
TradingView Pine v6 v29 source `src:32ea2fc6e5c00b2c`, SHA-256
`67b77dac93c82a93f708993f1f56be7a7558fbce94ec024c999780c20f9adb43`:
https://pine-facade.tradingview.com/pine-facade/get/STD%3BPrice%251Channel%251Strategy/last

The default period is 20. From the first bar with `close[20]` available,
the built-in submits or updates a long stop at the highest high and a short
stop at the lowest low of the latest 20 bars, including the current bar.
Both orders are inside the guard. Neither receives a tick offset and neither
is explicitly cancelled by this source. The intent adapter assumes complete,
finite, positive OHLC input and refuses invalid extrema; it does not claim
full Pine missing-value equivalence. Quantity, fills and broker properties are
separate from signal generation.

This is distinct from TradingView's Channel Breakout v29, which defaults to
five bars, offsets stops by a tick, and guards only its long entry. The owner's
screenshot of Channel Breakout must not be attributed to Price Channel.

The chart's matched Coinbase USDC perpetual tape, historical properties,
quantity, costs, funding and margin are not established. A Jupiter ZEC/USD
oracle proxy comparison is exploratory and cannot reproduce the chart or
establish profitability. Research depth, independent negation, family/queue
census, trusted semantic gates and publication receipts are still incomplete.
Before a backtest, check current protected intervals; do not use reserved data.
