# RS ZigZag PA source contract

Version: 1.1.0. Delta: record measured six-pass draft and publication limits.

The owner supplied a Pine file and screenshots for this investigation. This is
an audit and proposed comparison, not an executable card, completed research,
or independently reproduced result. The original file is untracked and is not
included here. Its SHA-256 is
`a708103541426c6746c1cb33b0ad5016094ce29b4342c2f92375bcadbb01e5a9`.
The screenshot does not establish that its executed source has those bytes.

## Evidence-bound findings

- The file has no `//@version` directive. TradingView says an omitted version
  defaults to Pine v1. Its official script-structure snapshot is Mongo source
  `src:d8bd6ad1141a23b8`, SHA-256
  `a6bdcd4be5280565f7cca774d68c31e65cd515f1997610ed2b5bfe2dd07630da`.
- The source's lines 2–4 and 13–20 default to an enabled 60-minute alternate
  timeframe and request the unoffset current higher-timeframe ZigZag through
  legacy `security`. TradingView states Pine v1/v2 `security` behaves like
  later `lookahead_on`, which can expose final higher-timeframe values early on
  historical lower-timeframe bars. Its official data-request snapshot is
  `src:7fb730d5cd545ce3`, SHA-256
  `5829d19aed772d21549a46703448accbc3912548716fc2e92a172719d22b8b3b`.
  On the screenshot's 15-minute chart, a 60-minute result can contain data from
  later 15-minute bars in the same hour. This conclusion applies if the
  supplied source executes as written and not to an unverified source version.
- The exact supplied source has trailing `Z` and `ZZ` tokens on lines 227–228.
  A private reference removes only those two tokens, retains the absent version
  directive, and has not been compiled or proven to match the screenshot's
  executed source. Do not silently treat adding a version directive as a
  syntax-only cleanup: changing versions can change `security` semantics.
- The ZigZag uses higher-timeframe candle direction and a two-bar extreme
  (lines 13–17); harmonic ratios use prior non-missing ZigZag values (26–35).
  Two bearish pattern labels use a `-2` visual offset (155–157). That display
  offset is distinct from the source's decision-time higher-timeframe leak.
- Target 1 defaults to 10,000 units and passes that number explicitly to
  `strategy.entry` (211, 231, 233). The screenshot's default order size of one
  is not a cap on explicit quantities. Instrument contract units, price and
  margin determine resulting notional. Target close conditions use bar high or
  low and `strategy.close` (227–234); they are close-calculated market exits,
  not necessarily resting stop-loss or take-profit orders.
- Target 2 close expressions (237, 239) mix `and`/`or` without parentheses;
  the stop-side branch can evaluate true with Target 2 disabled. No conclusion
  about an additional trade follows without the position history. Ratio
  denominators (32–35) have no explicit zero guard. The screenshot's optional
  Heikin Ashi input is off; its chart's own candle construction requires
  separate confirmation.

## Screenshots and comparison

The newer screenshot identifies `COINBASE:ZECUSDC.P`, 15-minute bars, initial
capital 100,000 USD and the March 31–November 16, 2026 report period. It shows
20,889.85% total P&L, maximum drawdown 551,844.81 USD (20.90%) and profit
factor 10.345. It shows zero commission, zero slippage, default four-tick bar
detail, on-bar-close calculation and 1x leverage labels. Trade count is obscured.
The earlier report spans June 21–November 16 and reports 17,203.27% P&L, 253
trades, 86.96% winners and profit factor 11.773. Screenshot figures remain
observed simulation outputs. Different period ranges prevent a direct 10/15
minute comparison; screenshot-to-source identity remains unverified.

Freeze one identical date interval, symbol, data provenance and settings before
comparing the 10- and 15-minute cases. Replay the exact legacy mechanism as a
labelled biased diagnostic, separately from a causal alternative that uses only
confirmed higher-timeframe values. A Pine v6 adaptation must offset the
expression inside the higher-timeframe request rather than applying an offset
in the chart timeframe. Verify prefix invariance and decisions at every lower
bar, including the first child of each hour, gaps, equal OHLC, zero ranges,
missing bars, simultaneous triggers and warmup. Specify quantity, commission,
spread, slippage, funding, position reversal, margin and liquidation behavior;
show sensitive assumptions and avoid claiming TradingView parity until its
actual source and input tape reconcile. Do not use or reset protected holdouts.

The native depth run is
`run:ba37f1d11d0e8c021761b63f1b3e082290b832edfddd611920e8124e95f637a4`.
The initial four search modes ran. A later six-pass depth packet and paired
proxy were created, as described below; source-to-runner parity, complete
queue/hold reconciliation and trusted evidence gates remain outstanding.

## Depth and publication status

The Mongo-native research run records nine draft baseline assertions and six
source-review passes. Their new-claim rates were 1/10, 3/13, 3/16, 3/19,
2/21 and 2/23. The sixth pass reached the configured cap while still producing
new information, so the depth verdict is `BUDGET_EXHAUSTED`, not saturation.
The source packet covers five readable TradingView documentation URLs from one
organization. Each of the 23 draft claims has an exact pinned Unicode quote
whose offsets were checked, but the assertions have not passed an independent
semantic evidence gate. The private Pine source, screenshot identity, matching
Coinbase history, venue economics and whole-question coverage remain incomplete.

The unqualified draft dossier is Mongo artifact
`art:f55504e4149f4a78691125fc777d6a091aa0476d08fba63c25b189a1c7574c33`,
SHA-256 `3895c67bf922bdf50b6335b1146a627b3652f681a783c365f8233c4dde1ffd6c`.
The available trusted finalization service did not expose a way to enforce the
owner's requested Terra model for the gate. No alternate-model paid gate was
launched, and no trusted research publication is claimed.
