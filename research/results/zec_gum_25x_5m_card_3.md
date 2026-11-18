# ZEC GUM strategy card 3 — Volty 10 × 1.5 with RSI

**Historical rank 3. Live-data paper preset `zec-25x-5m-3`.** The fixed configuration returned +1.36% summed across four development weeks and −3.00% in the added week.

## Configuration

| Setting | Value |
| --- | --- |
| Market | ZEC GUM perpetual, 5m signals, 25× isolated leverage |
| Target exposure | $250 per position before lot rounding, $1,000 starting virtual equity |
| Volty stops | Prior closed 5m close ± 1.5 × the 10-bar simple average of true range |
| Take profit | Disabled (0%) |
| Stop loss | 0.8% underlying price distance from fill |
| Candidate ID | `gate--volty-10-1.5--rsi-14-30-50` |

The stops become eligible after the signal candle closes. An eligible opposite stop closes and reverses under the paper broker. Long eligibility uses RSI(14) below 30 to enter its oversold state and above 50 to reset. Shorts apply the same state machine to reflected OHLC prices. A blocked opposite stop leaves the current position open.

The historical model uses the 3.5 bps taker fee and 2 bps assumed slippage per side, $0.01 per side, hourly GUM funding and a 75 bps liquidation fee. It uses trade candles for fills and as a proxy for the venue mark. The live paper process observes sampled marks, so marks may cross a level between polls and there is no guarantee of the historical event order.

## Fixed profile by week

Each week starts flat with $1,000 in virtual equity. October 14–November 11 informed the strategy shortlist. November 11–18 was scored after that shortlist was frozen.

| Week (end exclusive) | Fixed net return | Exits | Winners | Liquidations | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| Oct 14 → Oct 21 | +3.36% | 32 | 10 | 0 | 2.46% |
| Oct 21 → Oct 28 | −2.16% | 21 | 3 | 0 | 2.43% |
| Oct 28 → Nov 04 | +2.80% | 12 | 4 | 0 | 2.22% |
| Nov 04 → Nov 11 | −2.64% | 20 | 2 | 0 | 3.06% |
| Nov 11 → Nov 18 | −3.00% | 23 | 2 | 0 | 4.11% |

A single continuous holdout account from October 28–November 18 returned **−3.00%**, with 55 exits and 0 modeled liquidations.

## Rolling bracket walk-forward

The indicator rule stays fixed. Each fold chooses a bracket from the immediately preceding two weeks, subject to the trade and liquidation screen, then tests it on the following week. Earlier folds overlap the historical period used to nominate this indicator rule. The live preset uses the fixed card bracket.

| Training weeks | Forward test week | Selected TP / SL | Training return sum | Forward return |
| --- | --- | --- | ---: | ---: |
| Oct 14 → Oct 28 | Oct 28 → Nov 04 | 0% / 0.8% | +1.19% | +2.80% |
| Oct 21 → Nov 04 | Nov 04 → Nov 11 | 3% / 0.8% | +0.99% | −1.66% |
| Oct 28 → Nov 11 | Nov 11 → Nov 18 | 0% / 0.2% | +0.53% | −0.69% |

[Study and launch instructions](zec_gum_25x_5m_walk_forward.md) · [Versioned live presets](zec_gum_25x_5m_live.json) · [Full evidence](zec_gum_25x_5m_walk_forward.json.gz)
