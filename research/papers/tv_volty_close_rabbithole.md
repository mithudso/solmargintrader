# TradingView Volatility Expansion Close: source contract and open research

Version: 0.1.0. Delta: document the v30 intent adapter and existing runner check.

This draft extends the existing research-only source card without modifying its
checksum or the existing Volty runner. TradingView Pine v6 v30 source
`src:9fa8ed6b7e7c1466`, SHA-256
`52780b01f1b03db834600fca839d0bbc66fecd4916ea5de1a1adda325a831b04`:
https://pine-facade.tradingview.com/pine-facade/get/STD%3BVolty%251Expan%251Close%251Strategy/last

The source defaults to length 5 and multiplier 0.75. It calculates a simple
moving average of true range and multiplies it by the multiplier; it does not
use Wilder-smoothed ATR. Once `close[length]` is available, it places a long
stop at current close plus that width and a short stop at current close minus
that width. Its declaration does not fix order quantity. The isolated adapter
assumes complete finite positive bars and refuses invalid input; it does not
claim equivalence for Pine missing-value behavior. A fixture checks its stop
levels against the existing Volty runner on the next bar; that is not a fill
parity or profitability test.

The owner's screenshot shows a TradingView result, not an independent replay.
Matched Coinbase USDC perpetual bars, tester properties, fees, margin, funding
and actual size remain unverified. A separate Jupiter ZEC/USD oracle proxy is
exploratory. Complete shared family/queue reconciliation, independent negation,
measured depth and trusted gate/publication receipts remain open. Check current
protected intervals before each simulation and refuse reserved data.
