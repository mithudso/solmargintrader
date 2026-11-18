# ZEC GUM at 25× on five-minute signals

The original ZEC Volty replay already opened longs and shorts. In the matched 21-day replay, ungated Volty returned **+6.92% short-only**, **−1.99% long-only**, and **+4.75% with both sides enabled**. In the final seven days, ungated short-only returned **−0.25%**. The Z-score and RSI variant was the only short-only profile positive in that week, at **+0.33% across four exits**.

## Matched results

The 21-day window ran from October 28 to November 18, 2026. The added week ran from November 11 to November 18. All boundaries were 01:10 UTC, with the end excluded. Each profile, direction, and window started flat with $1,000 in paper equity. Net return uses starting equity. Maximum drawdown measures the largest decline from peak equity.

| Frozen profile | Entries | Week net | Week drawdown | Week exits | Week liq. | 21-day net | 21-day drawdown | 21-day exits | 21-day liq. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [Volty 10 × 1.5](zec_gum_25x_5m_card_1.md) | Both | −2.79% | 4.95% | 112 | 0 | +4.75% | 5.47% | 285 | 0 |
| Volty 10 × 1.5 | Long only | −3.19% | 5.65% | 61 | 0 | −1.99% | 8.82% | 146 | 0 |
| Volty 10 × 1.5 | Short only | −0.25% | 1.67% | 55 | 0 | +6.92% | 2.57% | 141 | 0 |
| [Volty with Z-score and RSI](zec_gum_25x_5m_card_2.md) | Both | −3.46% | 4.19% | 18 | 0 | −4.60% | 8.16% | 41 | 0 |
| Volty with Z-score and RSI | Long only | −3.79% | 4.48% | 14 | 0 | −5.29% | 6.47% | 27 | 0 |
| Volty with Z-score and RSI | Short only | +0.33% | 1.41% | 4 | 0 | +0.69% | 3.22% | 14 | 0 |
| [Volty with RSI](zec_gum_25x_5m_card_3.md) | Both | −3.00% | 4.11% | 23 | 0 | −3.00% | 7.07% | 55 | 0 |
| Volty with RSI | Long only | −2.72% | 3.20% | 18 | 0 | −4.56% | 5.52% | 37 | 0 |
| Volty with RSI | Short only | −0.29% | 1.42% | 5 | 0 | +1.56% | 2.77% | 18 | 0 |

Short-only had higher net return and lower drawdown than the matching long-only and two-sided runs for all three profiles in both windows. In the ungated 21-day two-sided account, the **139 short exits contributed +$68.76** and the **146 long exits contributed −$21.26**. The standalone short account had 141 exits because the entry restriction changed subsequent account state. All 18 runs had zero modeled liquidations. Two of the three short-only variants still lost in the added week, and that week is part of the same 21-day window. The results support testing the short-only variant on fresh paper data. The shared price history and related rules limit what these comparisons establish about future performance.

## What 25× means here

The replay targets $250 of position exposure with about $10 of initial margin before costs and lot rounding. A short benefits from a falling mark. A long benefits from a rising mark. At $250 exposure, a 1% move changes gross P&L by about $2.50 in either direction. That is 25% of the approximate initial margin and 0.25% of the starting account. Maintenance margin, fees, and funding affect liquidation. A gap can produce a worse stop fill than the trigger. The replay estimates fills and marks from minute trade candles.

## Reproduce the replay

The [original study](zec_gum_25x_5m_walk_forward.md) froze the selection, bracket and cost model. The comparison keeps completed five-minute signals, both signal directions for exits, and one net position. All profiles kept take-profit disabled and their original stop distances of 0.8%, 1.2%, and 0.8% in table order. Costs include GUM lot rounding, a 3.5 bps taker fee and 2 bps assumed slippage per side, $0.01 per side, and observed hourly funding. The comparison changes only which direction can open a new position. For each profile and window the runner verifies every original two-sided metric against the published artifact. It also checks that adding the final week leaves earlier closed-bar decisions unchanged.

Run the [offline direction replay](../../scripts/perps/zec-gum-directions.mjs) from the repository root with the two frozen captures and a new output filename.

```sh
node research/scripts/perps/zec-gum-directions.mjs --base /path/to/frozen-42-days.json \
  --week /path/to/frozen-added-week.json --output /path/to/new-directions.json
```

[Direction replay JSON](../../json/results/zec_gum_25x_5m_directions.json) contains full precision, signed side-level P&L, USD funding, and source hashes. Its SHA-256 is `909b2bc74aceb1f212695df45d7a2d45df5d27bc9908129e2f96c8039eb880cd`.
