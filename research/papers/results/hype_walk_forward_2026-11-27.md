# HYPE: walk-forward tests, findings and the live forward trial (2026-11-27)

A 1-hour RSI dip buyer looked best on HYPE, so it was put through rolling walk-forward tests on three real price histories and then started as a live paper trial. Result: re-optimizing the rule's parameters adds no skill, the frozen rule earns a modest positive return mainly while HYPE falls and lags holding while it rises, and the live trial is too short to settle anything. There is no validated edge.

Report version: 1.0.0. Research only. Not investment advice. No order was placed, no funded account was used and no key was loaded for any result in this paper.

## The short answer

- **Best performer in the 31-day study:** long-only dip buying and volatility-expansion entries, led by the 1h RSI(14) rule "buy below 30, exit above 55" (+15.7% over the month, +8.2% on its final test window, against HYPE -16.0%). No trend-following family was positive over that month.
- **Walk-forward tests (new):** choosing RSI parameters on the trailing 30 days and trading the next 7 days beat nothing reliably. After a 25 bps fee it lost 11.4% (Binance spot, 4 blocks) and 4.7% (Hyperliquid perp, 24 blocks). Its pick ranked 17th and 38th percentile among 60 fixed parameter sets, so it was no better than choosing one at random.
- **The frozen rule (RSI 14, 30/55):** +11.1% and +18.0% on the same blocks at 25 bps, against holding at -22.6% and +3.9%. But its parameters were chosen on this same history. Before that selection window, on Hyperliquid hourly bars, it made +10.6% over 133 days while holding made +46.3%.
- **What it is:** a defensive dip buyer. It does well when HYPE falls or chops and it trails when HYPE trends up. Over two years of daily bars nothing beat simply holding, and a plain 20/50 moving-average crossover (+71.8% at 10 bps) edged out holding (+63.8%) on the same test blocks.
- **Live forward trial:** started 2026-11-27 13:00 UTC, finite at 336 hourly bars (14 days), paper only. At the rule's historical rate it will complete only about 3 to 5 round trips (buy then sell). That is too few to judge, and the read-out rule below says so in advance.

## What was run

1. **Frozen 31-day candle study** (`research/papers/results/hype_study_2026-11-27.md`). Binance spot HYPEUSDT, 2026-10-27 to 2026-11-27, 44,640 real 1m bars, 1,707 spot templates x 6 filter modes x 1m/5m/10m/1h x 4 fee scenarios (491,712 rows). 60/20/20 chronological split: validation alone selects, the test window never reranks.
2. **Long-history cross-check.** Hyperliquid candles for HYPE: 722 daily bars from 2024-12-05 and 3,600 hourly bars from 2026-06-30.
3. **Rolling walk-forward tests (this paper).** Three histories, below.
4. **Live forward paper trial.** A frozen rule on the public Binance feed, below.

Two other HYPE studies exist and reach the same conclusion: a Coinbase spot suite (294 days) and a Binance seven-day study that found ATR-sized trend following best in the last rally week. The best strategy family flips with the window. Neither ranking should be extrapolated.

## Findings from the 31-day study

HYPE fell 16.0% over the 31 days (passive hold at 10 bps), so cash at 0% was the bar for a long-or-cash rule.

| Cadence | Strategy (frozen parameters) | Full | Validation | Test | Trades |
|---|---|---:|---:|---:|---:|
| 10m | Keltner breakout, ATR 5, EMA 12, mult 2 | +21.0% | +1.0% | +6.4% | 21 |
| 1h | majority vote of PPO, RSI(14, 30/50) and Bollinger breakout | +17.7% | +4.0% | +11.4% | 17 |
| 1h | RSI(14), buy below 30, exit 55 | +15.7% | +1.7% | +8.2% | 9 |
| 5m | Bollinger breakout, 3 std, 20 bars | +10.2% | +2.1% | +6.1% | 29 |

These are the best rows of a very large search, so they are hypotheses, not results.

- **Almost nothing survives costs.** At 10 bps, 0 of 10,242 one-minute rows were positive in full, validation and test; 140 of the hourly rows were. At 60 bps only 811 of 40,968 full-window rows were positive. One-minute trading is destroyed by costs.
- **Parameters are fragile.** For the 10m Keltner rule, 43% of nearby configurations were positive over the full window but only 11% in validation.
- **Patterns.** No serial correlation (daily lag-1 autocorrelation 0.002), no cycle that survives correction, no cross-asset lead (BTC, ETH, SOL and ZEC correlate 0.64 to 0.69 with HYPE but none lead it), and a two-up-bar reversal that is down 52.5% of the time against 50.6% unconditionally.
- **Support and resistance** (price $65.51 on 2026-11-27): support $65.32, $62.51, $60.02, $58.06, $55.74; resistance $68.78, $71.39, $74.98, $77.59. The levels describe where price paused and do not predict: out of sample they held 52.1% of touches against 53.4% for random levels.
- **Long history.** Over two years of daily bars nothing beat holding (+388.7%). Over five months of hourly bars only the RSI dip buyer did (+8.6% against +0.1%).

## Walk-forward tests

### Method

For every block, the rule's parameters are chosen using only the trailing training window, then traded on the next test window. Every test block starts in cash, so no position or profit carries across blocks and nothing before the block start can fill. Orders fill at the next bar's open. Costs apply to every fill: the fee shown plus 2 bps slippage.

- **Grid.** RSI period 7, 14 or 21; oversold 20, 25, 30 or 35; exit 45, 50, 55, 60 or 65. That is 60 parameter sets. The training pick is the best training return among sets with at least 3 executed fills (a buy and a sell are two fills).
- **Windows.** Hourly data: 720 bars (30 days) to train, 168 bars (7 days) to test, step 168. Daily data: 180 bars to train, 30 to test, step 30.
- **Compared on the same blocks.** The frozen forward-trial rule RSI(14) 30/55, a 20/50 moving-average crossover, and holding (price return, no costs, which is generous to holding).
- **Controls.** All 60 fixed sets scored on the same blocks, to rank the walk-forward pick and the frozen rule. A one-set grid reproduced the frozen rule exactly, and removing future bars left an earlier block unchanged.

| Dataset | Bars | Test bars used |
|---|---|---:|
| Binance spot HYPEUSDT, 1h | 1,537 (2026-09-24 to 2026-11-27) | 4 blocks |
| Hyperliquid HYPE perpetual, 1h | 4,800 (2026-05-11 to 2026-11-27) | 24 blocks |
| Hyperliquid HYPE perpetual, 1d | 722 (2024-12-05 to 2026-11-26) | 18 blocks |

The Binance hourly history is only 64 days (its first bar is 2026-09-24), so its four blocks are an anecdote, not a test.

### Chained out-of-sample return

| Dataset | Blocks | Fee (bps) | Walk-forward pick | Frozen RSI 14 30/55 | MA 20/50 | Hold (test blocks) |
|---|---:|---:|---:|---:|---:|---:|
| Binance HYPEUSDT 1h | 4 | 10 | -0.6% | +13.8% | -11.5% | -22.6% |
| Binance HYPEUSDT 1h | 4 | 25 | -11.4% | +11.1% | -13.3% | -22.6% |
| Binance HYPEUSDT 1h | 4 | 60 | -12.7% | +5.0% | -17.5% | -22.6% |
| Hyperliquid HYPE perp 1h | 24 | 10 | +5.3% | +28.2% | -2.8% | +3.9% |
| Hyperliquid HYPE perp 1h | 24 | 25 | -4.7% | +18.0% | -16.1% | +3.9% |
| Hyperliquid HYPE perp 1h | 24 | 60 | -10.8% | -2.6% | -40.4% | +3.9% |
| Hyperliquid HYPE perp 1d | 18 | 10 | +48.9% | +12.1% | +71.8% | +63.8% |
| Hyperliquid HYPE perp 1d | 18 | 25 | +45.2% | +11.5% | +66.5% | +63.8% |
| Hyperliquid HYPE perp 1d | 18 | 60 | +36.8% | +10.4% | +54.7% | +63.8% |

### Block by block

| Dataset | Fee | Pick: up / flat / down | Frozen: up / flat / down | Pick beat hold | Frozen beat hold | Distinct picks | Pick was 14/30/55 |
|---|---:|---|---|---:|---:|---:|---:|
| Binance 1h | 10 | 1 / 0 / 3 | 2 / 1 / 1 | 3 of 4 | 3 of 4 | 3 | 0 |
| Binance 1h | 25 | 0 / 1 / 3 | 2 / 1 / 1 | 3 of 4 | 3 of 4 | 4 | 0 |
| Hyperliquid 1h | 10 | 10 / 5 / 9 | 12 / 5 / 7 | 16 of 24 | 16 of 24 | 17 | 0 |
| Hyperliquid 1h | 25 | 6 / 7 / 11 | 11 / 5 / 8 | 16 of 24 | 15 of 24 | 14 | 0 |
| Hyperliquid 1d | 10 | 7 / 6 / 5 | 2 / 15 / 1 | 10 of 18 | 7 of 18 | 9 | 0 |
| Hyperliquid 1d | 25 | 7 / 6 / 5 | 2 / 15 / 1 | 10 of 18 | 7 of 18 | 9 | 0 |

The training window never picked the frozen rule's parameters. It changed its pick almost every block (14 to 17 distinct sets over 24 hourly blocks), which is a sign that the training ranking is noise.

### Control: every fixed parameter set on the same blocks

| Dataset | Fee | Median of 60 sets | Best set (hindsight) | Worst | Sets positive | Frozen rule percentile | Walk-forward pick percentile |
|---|---:|---:|---|---:|---:|---:|---:|
| Binance 1h | 10 | +2.1% | +16.3% (21/25/60) | -25.0% | 34 of 60 | 93 | 35 |
| Binance 1h | 25 | +0.0% | +15.4% (21/25/60) | -26.9% | 29 of 60 | 87 | 17 |
| Binance 1h | 60 | -3.4% | +13.4% (21/25/60) | -40.3% | 21 of 60 | 82 | 23 |
| Hyperliquid 1h | 10 | +7.2% | +59.8% (14/35/55) | -32.5% | 38 of 60 | 87 | 43 |
| Hyperliquid 1h | 25 | +0.0% | +37.7% (14/35/55) | -56.8% | 28 of 60 | 82 | 38 |
| Hyperliquid 1h | 60 | -12.3% | +24.6% (21/25/60) | -84.7% | 14 of 60 | 62 | 53 |
| Hyperliquid 1d | 10 | +12.1% | +157.8% (14/35/60) | -4.9% | 34 of 60 | 45 | 82 |
| Hyperliquid 1d | 25 | +11.5% | +153.2% (14/35/60) | -8.2% | 34 of 60 | 45 | 82 |
| Hyperliquid 1d | 60 | +10.4% | +142.8% (14/35/60) | -15.6% | 33 of 60 | 47 | 82 |

### What the walk-forward shows

1. **Re-optimizing does not help on hourly data.** The pick's percentile among the fixed sets was 17 to 53, which is what a random choice would give. After a 25 bps fee it was negative on both hourly datasets. This is the honest test of "tune the parameters on recent data and trade them".
2. **The frozen rule looks good partly because it was chosen with hindsight.** It sits at the 62nd to 93rd percentile of the fixed sets on the hourly data (82nd to 93rd up to 25 bps), and its 30/55 parameters came from the 31-day Binance window and from the Coinbase suite's 294 days, both of which overlap these histories. Taking only the Hyperliquid hourly blocks that ended before the 31-day window (19 blocks, 133 days) lowers the contamination but does not remove it:

   | Fee | Frozen rule | Walk-forward pick | MA 20/50 | Hold | Frozen up / flat / down |
   |---:|---:|---:|---:|---:|---|
   | 10 bps | +16.9% | +9.4% | +10.2% | +46.3% | 9 / 5 / 5 |
   | 25 bps | +10.6% | +1.7% | -1.8% | +46.3% | 8 / 5 / 6 |

   In the last 5 blocks (the overlap, a falling market) the frozen rule made +9.6% (10 bps) against holding at -29.0%. So the frozen rule's real character is risk-off: it banks small gains while HYPE falls and gives up most of the upside while it rises.
3. **Daily bars favor trend following and holding.** Over 18 monthly blocks the RSI rules trailed holding. The frozen rule was in cash in 15 of 18 blocks and made 3 round trips in 540 days; the walk-forward pick was in cash in 6 of 18. The 20/50 crossover beat holding at 10 and 25 bps (+71.8% and +66.5% against +63.8%) and lost to it at 60 bps (+54.7%). With 18 blocks and one dominant trend that is a weak signal.
4. **Costs matter more than the rule.** At 60 bps the frozen rule's edge on hourly data fell to +5.0% (Binance) and -2.6% (Hyperliquid).

### Limits of the walk-forward

- The Binance test has four blocks, and the three histories overlap in time, so they are not independent confirmations.
- Each block starts flat. A rule that would already hold a position at a block start misses that trade, which slightly understates the rule.
- "Hold" is the raw price return with no entry fee, which flatters holding by a few basis points.
- Only long or cash rules were tested. Perpetual funding, order-book depth and real fills are not modelled; fills use candle opens.
- The grid has 60 sets. A larger grid or other rule families could behave differently. This paper does not claim they would not.

## Live forward trial

The 1h RSI dip buyer was frozen and started as a finite paper trial, because a walk-forward on history already seen cannot tell a real edge from a lucky parameter set.

- **Rule.** RSI(14), buy below 30, exit above 55, long or cash, no leverage, closed Binance HYPEUSDT 1h candles. It places no order and holds no key.
- **Accounts.** The rule at two fill assumptions (next open, and one hour later) crossed with two fees (10 and 25 bps, plus 2 bps slippage), and a buy-and-hold account. The one-hour-late fill at 25 bps is the strict view.
- **Sample.** 336 closed hourly bars after activation at 2026-11-27 13:00 UTC, ending no later than 2026-12-11 12:00 UTC, with a hard expiry at 19:00 UTC that day. The run ends by itself.
- **Integrity.** The rule and the whole simulation core are hash-frozen at start, and a changed file ends the run. A bar counts as closed only when both the local clock and the venue's clock say so, and a gap in the feed ends the sample rather than being backfilled. Stored candles cannot be edited.
- **Status when this paper was written (2026-11-27 12:47 UTC):** running, 0 of 336 sample bars, because the first sample bar closes at 14:00 UTC.

### Read-out rule, fixed before any result

1. If the run ends in any state other than completed, there is no verdict.
2. If the one-hour-late, 25 bps account completed fewer than 8 round trips, the verdict is **inconclusive** and the numbers are reported descriptively only. The status output's `trades` field counts executed fills, so round trips are fills divided by two, rounded down.
3. With 8 or more trades: **supported** only if that account ends above cash and above buy-and-hold; **not supported** if it ends at or below cash; **mixed** otherwise.

The frozen rule made 31 round trips in the 168 days of Hyperliquid hourly test blocks (0.18 a day) and 9 in the 28 days of Binance test blocks (0.32 a day). A 14-day sample therefore yields about 3 to 5 round trips. The trial will most likely end **inconclusive** by its own rule. It tests that the pipeline runs unattended and gives an early warning if the rule breaks at once. Reaching 8 round trips would take about 4 to 6 weeks at those rates, and 20 about 2 to 3.5 months.

## What would change the conclusion

- A forward sample with at least 20 trades in which the strict account stays above cash and above buy-and-hold across more than one market regime.
- A perpetual-funding and order-book study on Hyperliquid, which this paper does not have, including the short side.
- Walk-forward results on other rule families with a pre-declared grid and the same controls.

## Reproduce

- Walk-forward: `python research/scripts/hype_study/walk_forward.py --out DIR` (public Binance and Hyperliquid data only). A compact summary of the run behind these tables is in `research/json/hype-walk-forward-20261127/walk_forward_summary.json`.
- 31-day study scripts: `research/scripts/hype_study/`.
- Live trial module: `ecosystem/hype_forward.py` with `python -m ecosystem.hype_forward --home DIR status` (read-only).
