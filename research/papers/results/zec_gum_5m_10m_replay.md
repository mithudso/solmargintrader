# ZEC perpetuals replay at 5m and 10m, 25× and 50×

**25× was materially safer at equal exposure. The old RSI winner did not repeat.** At fixed $250 target exposure, 25× beat 50× in 1,190 of 1,264 matched test configurations. All four configurations selected on validation lost money on the held-out test. Three configurations earned positive net P&L in both windows with at least ten exits each. They were a 10m RSI(7) rule with two entry filters and two variants of a 5m Balance of Power rule. All three used 25× with a 1.5% take profit and 0.8% stop.

## What the old archive IDs mean

The earlier seven-day sweep ranked returns on a $1,000 paper account. Its global top 50 contained 47 ZEC rows and three ETH Volty rows. Of those 47 ZEC rows, 32 used the requested cadences and leverage. None of those 32 came from the 5m/50× cell. Only five of the global top 50 made money in validation. The decoded sheet preserves all original values, with one global top 50 and one ZEC-only top 50. [Prior rankings with readable rules](../../results/zec_gum_prior_top50_decoded.csv)

| Prior configuration | What it actually did |
| --- | --- |
| `archive-949285d23496ba91b0d7be64-10m` | RSI(14) enters below 30 and exits above 100. RSI cannot exceed 100, so this version needs a bracket, liquidation or the end of the replay to close. |
| `archive-da07024ac4b744cd8bf09312-10m` | Same entry, with a signal exit above 75. In the old test it held the same long as the exit-100 version. |
| `archive-1148ff1ce2c2b74bdf9dd66b-10m` and `archive-e92b8af2a79b8010b0b3b408-10m` | Bollinger(45, 2 population standard deviations) and Z-score(45, sample standard deviation, enter ≤ −2, exit ≥ 0). Both use a 450-minute lookback. They happened to return the same P&L in the old test. |

The two old top rows opened one long at $851.22 and closed it at $960.52 at the end of the replay, 33½ hours later. Both earned **+15.96%** at 50× using $25 collateral and lost about **1.28%** in validation. At $250 fixed exposure, that same hold earned **+3.18%** at either leverage. The new test with the same unfiltered, unbracketed settings liquidated the exit-100 position at both leverage levels. At 25× and $250 exposure, the old 10m Bollinger and Z-score leaders both earned **+1.58% test / +0.64% validation**. In the new windows they returned **−5.99% / −3.17%** and **−5.42% / −3.17%** respectively.

## Held-out results

The grid covers 81 named signal configurations and 5,056 replay cases. It includes all 50 ZEC archive presets at the requested cadences, three named prior presets and 28 focused additions. At fixed exposure each pair holds the signal, filters, brackets and target notional constant while leverage changes. Fixed collateral sizes target $625 at 25× and $1,250 at 50× before lot rounding. All percentage returns and drawdowns below refer to the $1,000 starting account.

| Signal cadence | Leverage | Median test, $250 exposure | Median test, $25 collateral | Positive test rows at fixed exposure | Modeled liquidations / exits at fixed exposure |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5m | 25× | −1.04% | −2.48% | 120/624 | 942/57,035 (1.7%) |
| 5m | 50× | −5.75% | −27.13% | 0/624 | 33,128/52,394 (63.2%) |
| 10m | 25× | −1.04% | −2.54% | 30/640 | 1,095/28,573 (3.8%) |
| 10m | 50× | −3.77% | −18.68% | 2/640 | 20,977/29,116 (72.0%) |

Exit totals pool overlapping replays of the same market. They measure this grid's exposure to liquidation and cannot be read as independent trade samples. Cash returned 0%. A single buy-and-hold long at $250 target exposure liquidated at both leverage settings in both windows. The underlying trade price rose 5.05% in validation and fell 20.64% in test.

### Rules selected before scoring the holdout

Each cell used only validation to select its best return among fixed-notional rows with at least ten exits and zero refused entries. Ties preferred lower drawdown, then more exits, then configuration order. The frozen selection came before test scoring. [Rankings and frozen selections](../../results/zec_gum_5m_10m_rankings.csv)

| Cell | Validation selection | Validation | Test | Test exits / liquidations |
| --- | --- | ---: | ---: | ---: |
| 5m / 25× | RSI(14) < 30 → > 55, cadence filter, signal exits | +3.16% | −4.68% | 20 / 8 |
| 5m / 50× | Bollinger(40, 2σ), both filters, narrow bracket | −0.32% | −1.23% | 13 / 4 |
| 10m / 25× | MACD(12/26/9) line > 0 → ≤ 0, signal exits | +6.04% | −0.96% | 28 / 3 |
| 10m / 50× | MACD(12/26/9) line > 0 → ≤ 0, cadence filter, signal exits | +0.01% | −3.10% | 12 / 12 |

### Three rows positive in both windows

This screen used *both* result windows. It found three rows among 2,068 fixed-exposure rows meeting the ten-exit minimum in both windows with no validation refusals. These are historical observations after inspection. BOP means Balance of Power.

| Rule at 25× with 1.5% TP and 0.8% SL | Validation | Test | Test wins / exits | Test drawdown | Liquidations in both windows |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10m RSI(7) < 30 → > 55, shape and cadence | +0.34% | +0.84% ($8.38) | 11/19 | 0.92% | 0 |
| 5m BOP SMA(5) > 0 → ≤ 0, shape | +0.30% | +0.67% ($6.73) | 12/39 | 0.74% | 0 |
| 5m BOP SMA(5) > 0 → ≤ 0, shape and cadence | +0.10% | +0.08% ($0.83) | 5/17 | 0.67% | 0 |

The 5m shape-filtered BOP won just 31% of test trades but averaged $2.32 per winner and $0.78 per loser. The matched 50× version lost 3.24% and liquidated 21 of 39 test positions. The matched 10m RSI version at 50× lost 3.28% with 16 liquidations in 19 exits. Its 25× test win rate was 58%, with 19 exits. Adding cadence to BOP cut its test trades from 39 to 17 and its observed return from +0.67% to +0.08%.

The largest raw holdout return was **5m Volty, 25×**, using 10-bar SMA true range × 1.5 and neither filter nor bracket. It earned **+9.32%** at fixed exposure with 153 test exits and nine liquidations, following **−5.33%** in validation. With fixed $25 collateral, the same configuration shows **+23.78% test / −12.78% validation**. This is how a high return can coexist with poor replay stability.

## Indicators, graph shapes and cadence

| Family | What ran | Best validation-selected row at 25× by cadence, validation → test |
| --- | --- | --- |
| Z-score | Rolling sample SD, long at or below the entry z-score, flat at or above the exit z-score | 5m −0.03% → +1.90%. 10m +1.18% → −0.99%. |
| RSI | Wilder-style RSI, strict entry below the threshold and exit above the configured level | 5m +3.16% → −4.68%. 10m +1.99% → −2.46%. |
| Bollinger | Lower-band entry and mean exit using population SD | 5m +0.16% → −2.90%. 10m +1.59% → −3.13%. |
| Balance of Power | SMA(3), SMA(5) and SMA(10) of (close − open)/(high − low). Zero-range bars contribute zero. | 5m +0.30% → +0.67%. 10m +0.39% → −0.44%. |
| MACD | EMA 12/26 with a 9-bar signal and 78-bar warmup. Tested positive line and positive histogram separately. | 5m +2.13% → −0.53%. 10m +6.04% → −0.96%. |
| Volty | Prior close ± true-range SMA × multiplier. Active next bar. The opposite stop reverses when allowed. | 5m +2.92% → −4.13%. 10m −0.11% → −1.66%. |
| Graph shapes | Trailing 48 closed-bar log-price geometry. The standalone rule buys V rebounds or bowls outside the upper zone and exits on the upper zone or a bearish shape. | 5m −0.79% → +0.29%. 10m −0.44% → −0.43%. |
| Spectral cadence | Causal fit of trend plus one harmonic on 64 closed bars, refit every 16 bars. The standalone rule follows the sign of the projected next harmonic increment. | 5m −7.02% → −6.28%. 10m −2.84% → −3.74%. |
| Mean-reversion ensemble | Equal-weight votes from archive members, including the previous RSI + Z-score + Bollinger preset | 5m +1.98% → −1.81%. 10m −0.34% → −0.65%. |

Shape and cadence also ran as separate and combined entry filters. Shape admits ranges, V rebounds or bowls for mean reversion, rising shapes or bowls for BOP/MACD, and compression or direction-matched trends for Volty. Cadence requires the next harmonic increment to point toward the intended side. Filters do not close an existing long simply because eligibility changes. For Volty, a blocked opposite stop can defer a reversal.

At 25× and equal exposure, applying both filters improved median test return relative to the same unfiltered strategies by **2.82 points at 5m** and **1.17 points at 10m**. It cut pooled 5m exits from 28,630 to 3,681 and 10m exits from 14,362 to 2,006. Less turnover and market exposure explain part of the observed benefit. This comparison does not isolate predictive value from trade frequency. Cadence on its own lost in both periods at both cadences.

## Fees, stops and replay limits

At the first test price, the model's liquidation buffer was **2.216% long / 2.138% short at 25×** and **0.179% long / 0.173% short at 50×** using $250 fixed target exposure. The grid used signal-only exits or one of three price-distance brackets. Tight was 0.5% TP / 0.3% SL, wide was 1.5% / 0.8%, and narrow was 0.5% / 0.1%. Tight and wide stops sat past the initial liquidation threshold at 50×. The wide bracket sat inside the 25× threshold. The 0.1% stop at 50× reduced liquidation frequency, but its median test return was still **−3.66% at 5m** and **−2.44% at 10m**.

GUM terms at capture were 3.5 bps taker per side, 0.5 bps maker, 75 bps liquidation and 100 bps first-tier maintenance below $10,000. The model uses taker fills with 2 bps slippage and $0.01 network allowance per side. It uses each recorded hourly funding distribution with the minute trade price as the mark proxy. Accrual when position size changes and the exact on-chain funding timestamp may differ. Fees, tiers and quantity limits captured on November 18 were applied across the study. Market orders obey modeled lot size and first-tier limits. [GUM market terms](https://api.gum.ag/app/perps/markets) · [Funding protocol](https://github.com/jupnet/gum-perp-sdk/blob/08bc398d78350a49ae047ecbdd3ffc6233c082d3/docs/REST_API.md#get-funding-rate-history)

Signals consume only closed aggregate candles. Replay starts each scoring period flat and stages a signal for the next minute open, or next-minute stop for Volty. One-minute trade OHLC cannot establish mark-price wicks, book fills or intraminute event order. The shared paper model handles gaps at the open and chooses liquidation if an ambiguous candle spans competing levels. It accounts for open positions at the last close. Measured drawdown uses marked paper equity at replay observations.

## Data and reproduction

| Window (UTC, end exclusive) | Start | End |
| --- | --- | --- |
| Warmup | 2026-09-30 01:10 | 2026-10-14 01:10 |
| Validation | 2026-10-14 01:10 | 2026-10-28 01:10 |
| Test | 2026-10-28 01:10 | 2026-11-11 01:10 |

The 42-day input has 60,480 continuous minute candles, including 2,088 zero-range minutes, and 1,008 consecutive hourly funding observations. Its end is the start of the prior seven-day source. The two-week test slice is historically earlier than that study, so these results are a disjoint retrospective comparison. [Public trade OHLC](https://api.gum.ag/app/perps/ohlcv/ZEC?interval=1m) · [Public funding series](https://api.gum.ag/app/perps/fundingRate/ZEC/history)

From the repository root:

```sh
node research/scripts/perps/zec-leaderboard.mjs
node research/scripts/perps/zec-perps-capture.mjs --start 2026-09-30T01:10:00Z --end 2026-11-11T01:10:00Z --output ZEC.json
node research/scripts/perps/zec-perps-suite.mjs --capture ZEC.json --output summary.json
gzip -dc research/json/results/zec_gum_5m_10m_full.json.gz > published-summary.json
```

Recapture records a new terms snapshot and capture time. The exact frozen source for these results has SHA-256 `933b9f6e116d8d366d6c73ccda5ec360b30f60dbe63daa26214c3fa010c46dee`. The complete compressed result includes the source receipt, candidate rules, four validation selections, per-family selections, benchmarks and every replay. [Full run and receipt](../../json/results/zec_gum_5m_10m_full.json.gz)
