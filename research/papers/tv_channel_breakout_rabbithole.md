# TradingView Channel Breakout: source contract and open research

Version: 0.1.0. Delta: record v29 source intent semantics and limitations.

The user's screenshot names Channel Breakout, a distinct built-in from Price
Channel. This is a draft research contract, not a TradingView parity proof or
completed rabbithole. TradingView Pine v6 v29 source `src:76a6738dbe0a2319`,
SHA-256 `f438bd98aefb5ed835939a63678dd707740f2265459bd19923ce12c9b056cf30`:
https://pine-facade.tradingview.com/pine-facade/get/STD%3BChannel%251BreakOut%251Strategy/last

Default length is 5. At each bar close the source uses the trailing high and
low, including the current bar. It places a long stop one tick above the high
only when `close[length]` exists. It places a short stop one tick below the low
outside that guard. The unguarded short can be submitted before six complete
bars exist; do not impose the long guard on both sides. Neither order is
explicitly cancelled in this source. Quantity and fill rules are separate.
The adapter accepts complete finite positive bars and refuses invalid extrema;
it does not claim Pine missing-value equivalence.

The matched Coinbase perpetual tape, exact tester properties, quantity, costs,
funding and margin are unknown. The user's screenshot is an observation of a
TradingView report and is not independently reproduced by a Jupiter oracle
proxy. Complete family/queue dedup, measured depth, independent negation and
trusted finalization remain open. Check fresh protected intervals before every
simulation and refuse reserved data.
