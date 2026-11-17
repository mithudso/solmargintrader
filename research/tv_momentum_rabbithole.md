# TradingView Momentum: source contract and open research

Version: 0.1.0. Delta: record the pinned built-in and a draft intent adapter.

Status: research and parity are incomplete. This is an execution-contract
extension for the existing research-only `tv_43000599883_momentum_strategy`
card, not a replacement of its checksum-bound record or a claim of profitability.

## Mechanism and order intents

The TradingView Pine v6 Momentum built-in v29.0 snapshot is Mongo source
`src:226ef9fa1b185243`, SHA-256
`c1ffb758acd11d4a6c98142e370b8059f23ca4e0281f06d4eeb34062651f80f8`:
https://pine-facade.tradingview.com/pine-facade/get/STD%3BMomentum%251Strategy/last
The `last` URL can change; the snapshot identifies the version studied.

With close C and default length 12, M[t] = C[t] - C[t-12] and
D[t] = M[t] - M[t-1]. At a bar close, if M > 0 and D > 0, the
source places or updates a long stop at high plus one minimum tick; otherwise
it cancels the long entry. Then, if M < 0 and D < 0, it places or updates a
short stop at low minus one minimum tick; otherwise it cancels the short entry.
Equality cancels. The source does not set a quantity. Fourteen closes are
needed for the first complete default-length calculation. A valid signal is an
order intent, not proof of a fill. The intent adapter emits these actions in
source order and requires explicit market tick size.

TradingView's official Momentum help describes directional change, but does
not by itself specify the stop orders or prove a trading result:
https://www.tradingview.com/support/solutions/43000599883-momentum-strategy/

The official emulator documentation says default orders fill no earlier than the
next available tick, price-based orders crossed in an interbar gap fill at the
next open, and opposite `strategy.entry` orders reverse the existing position:
https://www.tradingview.com/pine-script-docs/concepts/strategies/
These are conditional on the simulator settings. Intrabar OHLC path assumptions,
equal-distance ambiguity, order modification and cancellation timing require
separate tests against the selected broker model and chart settings.

## Evidence and limits

Hudson and Urquhart's *Technical trading and cryptocurrencies* studies daily
Bitcoin, Litecoin, Ethereum and Ripple, and reports no Bitcoin predictability
in its out-of-sample period even while reporting positive findings elsewhere:
https://link.springer.com/article/10.1007/s10479-019-03357-1
Mongo source `src:05f776a75773c4dc`, SHA-256
`82060202e1112cb2261b1fd882a30293261a9133781964f8dec72b3f33abd5fb`.
This warns against assuming persistence; its daily assets, era, rules and costs
do not establish an edge or loss for ten-minute ZEC perpetual Momentum.

The owner confirmed ten-minute bars and default inputs for the named chart,
`COINBASE:ZECUSDC.P`, with a June 21–November 16, 2026 target. Exact matched
bars, endpoint time, historical script version, sizing, margin, fees, spread,
slippage and funding remain unverified. A USD or spot proxy must be labelled
and cannot establish reproduction of the owner's reported return. The shared
OHLC emulator is a sensitivity model, not a TradingView parity proof; it omits
funding, spread, margin, liquidation and venue rejection.

The Mongo rabbithole run remains unqualified. The complete selected-family
census and STOP/queue join, source-floor assessment, independent negation,
measured depth passes, trusted gate and publication receipt remain open. Do not
call the depth saturated or the strategy card executable on this evidence.

## Backtest protocol

After checking current protected intervals and refusing reserved ranges, use a
matched and complete ten-minute tape, record provenance and exact tester
settings, and freeze them before evaluation. Preserve missing candles. Supply
explicit tick size and position size, verify order/fill traces against the chart,
and report assumed path and gap behavior, returns, trade count, drawdown,
buy-and-hold and cost sensitivity. Model or explicitly mark missing funding,
margin and liquidation; never silently set them to zero. Keep tuning separate
from untouched evaluation periods. No actual market backtest is asserted here.
