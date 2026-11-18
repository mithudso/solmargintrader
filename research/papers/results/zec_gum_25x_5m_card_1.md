# ZEC GUM strategy card 1 — Volty 10 × 1.5

**Historical rank 1. Live-data paper preset `zec-25x-5m-1`.** The fixed configuration returned +2.63% summed across four development weeks and −2.79% in the added week.

## Configuration

| Setting | Value |
| --- | --- |
| Market | ZEC GUM perpetual, 5m signals, 25× isolated leverage |
| Target exposure | $250 per position before lot rounding, $1,000 starting virtual equity |
| Volty stops | Prior closed 5m close ± 1.5 × the 10-bar simple average of true range |
| Take profit | Disabled (0%) |
| Stop loss | 0.8% underlying price distance from fill |
| Candidate ID | `volty-10-1.5` |

The stops become eligible after the signal candle closes. An eligible opposite stop closes and reverses under the paper broker. Both directions are eligible after the true-range warmup.

The historical model uses the 3.5 bps taker fee and 2 bps assumed slippage per side, $0.01 per side, hourly GUM funding and a 75 bps liquidation fee. It uses trade candles for fills and as a proxy for the venue mark. The live paper process observes sampled marks, so marks may cross a level between polls and there is no guarantee of the historical event order.

## Fixed profile by week

Each week starts flat with $1,000 in virtual equity. October 14–November 11 informed the strategy shortlist. November 11–18 was scored after that shortlist was frozen.

| Week (end exclusive) | Fixed net return | Exits | Winners | Liquidations | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| Oct 14 → Oct 21 | −1.26% | 120 | 36 | 0 | 5.12% |
| Oct 21 → Oct 28 | −3.72% | 98 | 27 | 0 | 4.73% |
| Oct 28 → Nov 04 | +5.33% | 87 | 34 | 0 | 2.31% |
| Nov 04 → Nov 11 | +2.28% | 86 | 33 | 0 | 2.00% |
| Nov 11 → Nov 18 | −2.79% | 112 | 34 | 0 | 4.95% |

A single continuous holdout account from October 28–November 18 returned **+4.75%**, with 285 exits and 0 modeled liquidations.

## Rolling bracket walk-forward

The indicator rule stays fixed. Each fold chooses a bracket from the immediately preceding two weeks, subject to the trade and liquidation screen, then tests it on the following week. Earlier folds overlap the historical period used to nominate this indicator rule. The live preset uses the fixed card bracket.

| Training weeks | Forward test week | Selected TP / SL | Training return sum | Forward return |
| --- | --- | --- | ---: | ---: |
| Oct 14 → Oct 28 | Oct 28 → Nov 04 | 2% / 0.5% | −3.19% | −0.45% |
| Oct 21 → Nov 04 | Nov 04 → Nov 11 | 0% / 1.6% | +3.82% | +1.61% |
| Oct 28 → Nov 11 | Nov 11 → Nov 18 | 0% / 0.8% | +7.62% | −2.79% |

[Study and launch instructions](zec_gum_25x_5m_walk_forward.md) · [Versioned live presets](../../json/results/zec_gum_25x_5m_live.json) · [Full evidence](../../json/results/zec_gum_25x_5m_walk_forward.json.gz)
