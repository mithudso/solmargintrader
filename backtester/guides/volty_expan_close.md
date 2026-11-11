---
id: volty_expan_close
name: Volty Expan Close Strategy
kind: stop-strategy
status: measured
family: volatility-breakout
summary: Next-bar stop entries at prior close plus or minus a simple average of true range; independent long/short reference simulator with costed walk-forward study.
registry_key: null
runner: backtester.voltycli
warmup_bars: 6
evaluation: "ZEC 250-trial study 2026-11-10: chronological 50/50 holdout and five expanding walk-forward folds; 10 bps fee, 2 bps slippage, 0.1 bps/hour synthetic carry"
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: measured-oos
params:
  length: {default: 5, type: int, desc: "Simple average true range length; positive integer"}
  atr_mult: {default: 0.75, type: float, desc: "Positive channel width multiplier"}
---
# Volty Expan Close Strategy

Version: 1.0.1. Delta: record measured ZEC results after implementing the public stop-entry rule.

The TradingView built-in posts long and short stop entries at each close:
`upper[t+1] = close[t] + SMA(TR,length)[t] * atr_mult` and
`lower[t+1] = close[t] - SMA(TR,length)[t] * atr_mult`.
TR is `max(high-low, abs(high-previous_close), abs(low-previous_close))`.
This uses simple averaging, not Wilder ATR. The first valid order requires
`close[length]` and a complete true-range window. No current-bar observation
changes the stops active on that bar.

The standalone runner keeps both replacement stops eligible and never pyramids.
An opposite stop closes and reverses. A gap fills at the open rather than the
crossed stop. When both stops are touched, the historical OHLC path defaults to
open-high-low-close if the open is nearer the high, otherwise open-low-high-close.
The study also tests both fixed path assumptions for frozen winners. This is an
independent research model; certified TradingView broker-emulator parity is not
claimed. Native tick data would be needed to establish actual order sequence.

The model sizes each new position at one times current equity, holds fixed units
until reversal, and charges 10 bps fees plus 2 bps slippage per side. It charges
0.1 bps per hour as an explicit synthetic carry scenario on end-of-bar notional.
The carry is not observed funding. Long/short simulations use Binance spot
ZEC/USDT bars; these do not establish an executable short venue, margin model,
or live performance. This sizing is a study choice, not Pine's default quantity.

The runner searches 50 configurations per interval and uses only past training
returns to choose each of five walk-forward folds. Each test starts flat with
past data available to warm indicators. It closes at the test boundary and pays
the exit cost. Full-sample ranks are descriptive and never select a past test.
Future paper configurations are prepared separately and do not claim to run.

## Likelihood of success: very-low

Basis: measured-oos. All five first-half selected winners lost on their held-out
second half. Daily adaptive walk-forward selection gained 22.69% but trailed
passive ZEC. These exploratory results after 250 trials do not prove an edge.
Measured study results and reproduction are in `docs/VOLTY-ZEC-STUDY.md`.

## Sources

https://www.tradingview.com/support/solutions/43000599890-volty-expan-close-strategy/

Public Pine rule (corroborating reproduction):
https://community.ctrader.com/forum/ctrader-algo/44931/

Raw downloaded pages and their hashes are kept with the local study artifacts.
The older source-description card remains in the publication research archive.
