# RS ZigZag retrospective oracle proxy

Version: 1.0.1. Delta: record the chart symbol metadata limitation.

These results are **not TradingView replication or evidence of live profit**.
They use previously observed Jupiter ZEC/USD oracle OHLC, not Coinbase's
ZEC/USDC perpetual market, and the signal/fill implementations have not yet
received an independent audit. The owner-provided source has two stray tokens
and its identity with the screenshot's executed script is not established.

The paired comparison fixes the same October 10 21:00 UTC–November 8 19:00
UTC 2026 interval, using 41,640 complete one-minute bars. It aggregates exact
UTC-aligned 10- and 15-minute candles. The first partial hour is excluded;
last-bar market orders do not invent a next fill. A fresh read-only holdout
check over ZEC aliases preceded and followed the run, with no overlapping
unsealed reservation. This historical interval was previously examined; it is
not an untouched or prospective test.

The `legacy` mode deliberately exposes the final current hourly ZigZag at the
first lower-timeframe bar, matching the documented direction of legacy Pine
lookahead. The `confirmed` mode waits for the preceding completed hour. Both
use the same research prototype and next-open market-order sensitivity, with
100,000 USD initial capital, 10,000 explicit units and a one-price-unit
contract multiplier. Neither the actual instrument multiplier nor TradingView
position/margin behavior has been verified. A pending final position is marked
at the last close rather than forcibly liquidated.

| Chart bars | Signal path | Scenario | Return | Closed trades | Winning trades | Entry rejects |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 10 min | Legacy, biased | Uncollateralized, zero cost | +4,735.44% | 44 | 38 | 0 |
| 10 min | Legacy, biased | Uncollateralized, cost sensitivity | +3,429.00% | 44 | 35 | 0 |
| 10 min | Confirmed hour | Uncollateralized, zero cost | -268.79% | 6 | 2 | 114 |
| 10 min | Confirmed hour | Uncollateralized, cost sensitivity | -187.81% | 4 | 2 | 122 |
| 15 min | Legacy, biased | Uncollateralized, zero cost | +4,694.41% | 40 | 34 | 0 |
| 15 min | Legacy, biased | Uncollateralized, cost sensitivity | +3,507.73% | 40 | 32 | 0 |
| 15 min | Confirmed hour | Uncollateralized, zero cost | -203.59% | 6 | 4 | 72 |
| 15 min | Confirmed hour | Uncollateralized, cost sensitivity | -164.66% | 4 | 2 | 77 |

The cost sensitivity assumes 10 bps commission and 2 bps adverse slippage per
side; these are model inputs, not observed Coinbase rates. Funding and spread
are unavailable, so even those figures are not fully net. Uncollateralized
negative equity and drawdowns greater than 100% are accounting stress outputs,
not feasible account returns. The model rejects new entries when cash cannot
cover entry fees. A separate simple 1x collateral test, under the assumed
one-unit multiplier, rejected every 10,000-unit entry in all eight mode/interval/
cost combinations. Its conservative adverse-extreme maintenance rule is a
stress assumption, not TradingView or venue liquidation parity.

The frozen source is Mongo artifact
`art:daf887a414eb6078d63bbb2e557fbe6ebfc29433c43feaec69506a884bfda896`,
SHA-256 `8b5eb4f54851fad81c28137bda85e643e34c93da349c3c0178b8df271948b2bc`.
The result is Mongo artifact
`art:1ad06f6ccde823942128d9a8c707cc74a060450fd115b5bb5547a490abcf5983`,
SHA-256 `8e5c7aa71c57c0955ab055af9060d2ec4bc128bab9ddcd0c5aae37f4876dd61f`.
The commissioned comparison and scenario choices were saved in the run ledger
before calculation. Full source-to-runner, Pine order semantics, matching
Coinbase history and independent numeric review remain required.

The TradingView public scanner identified the chart as a ZEC/USDC swap, with `minmov=1` and `pricescale=100`, but returned `pointvalue=null` and `unit_id=null`. It therefore did not establish contract multiplier or notional. The captured metadata source is `src:d7230b6d54733c31`, SHA-256 `336f1fc5925292877b551b0775e1e47fd19570194117d48522854a6479474eb1`.
