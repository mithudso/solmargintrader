# HYPE: strategies, patterns and price levels

Version: 1.0.1. Data frozen 2026-11-27 08:49–08:53 UTC. HYPE traded near $65.60 on
Binance spot; the last completed Hyperliquid hour closed at $65.40.

This repeats the ZEC candle studies on HYPE and adds a two-year look at price
structure. Every result is a backtest or a description of past candles. None of
it qualifies a live trading edge, and nothing here was traded.

The working-paper edition, with two figures and a comparison against the
31-day Binance run, is [What holds up on HYPE?](HYPE-STRATEGIES-PATTERNS-LEVELS.md).

## Short answers

**Which strategies performed best?** It depends on the bar size and on whether
the market was rising or falling. No rule won at every size, and over two years
nothing beat holding.

| Horizon | Best performer in the test | Result | How far to trust it |
|---|---|---|---|
| Daily, two years | Buy and hold | +389%, with a 68% worst decline | No tested strategy beat it. A 20/50-day moving-average crossover kept +173% with a 40% worst decline. |
| Hourly, 208 days | Bollinger breakout (20 bars, 2 deviations) | +107% against +59% for holding at 6 bps, with a 17% worst decline against 42% | Made all of it in the rising part and lost 1.5% in the falling part. At 25 bps it made +49% and trailed holding. |
| 5 and 10 minutes, one week | ATR-sized trend following | +14% to +16% in a week where holding made +0.3% to +0.5% | Positive in validation and final test, at 10 and at 60 bps per fill. One week only. |
| 1 hour, one week | MACD + PPO + RSI average | +4.6% | Positive in validation and final test. Small. |
| Falling market, hourly | Oversold bounce (RSI under 30 plus lower-band touch) | +26.7% while holding lost 28.6% | Lost 1.2% in the rising part before it. Not robust to regime. |
| 1 minute | Nothing | 68 of 1,707 strategies made money at the lowest fee, 19 at the highest | None passed the validation-and-test screen. |

Every strategy tested is long or flat. No short side was tested.

**Which patterns exist?**

- Large, frequent declines. Seven of 25% or more in two years, two of them
  deeper than 65%.
- No day-to-day memory: daily return autocorrelation is +0.009. Volatility
  clusters mildly (absolute-return autocorrelation +0.116).
- HYPE moves with Bitcoin and moves further: correlation 0.54, beta 1.26 over
  two years; 0.59 and 1.04 over the last 90 days.
- A quarter of all volume trades between 13:00 and 16:59 UTC. The largest hourly
  moves fall at 14:00 and 15:00 UTC.
- Wednesday was the strongest weekday (+1.26% average). It does not survive a
  correction for testing seven days.
- The ZEC two-bar reversal pattern does not transfer. No cycle, no leading
  correlation and no reversal shape survived its own controls.

**Where are support and resistance?** See [the level map](#price-levels). The
nearest zones are $65.43–66.14, $67.76–68.34 and $68.62–70.25 above, and
$64.50–65.10, $62.42–63.35 and $59.70–60.55 below. Past returns to such levels
broke them more often than they held, and they held no more often than
arbitrary lines nearby.

## What was run

| Study | Data | Size |
|---|---|---|
| [Weekly candle study](../json/hype-week-20261127/report.md), the ZEC transfer | Binance spot HYPE/USDT, 10,080 one-minute bars, 2026-11-20 08:49 to 2026-11-27 08:49 UTC, no missing minute | 1,707 strategy templates × 6 filters × 4 bar sizes × 4 fee levels × 3 time splits, plus cash and holding benchmarks: 491,712 rows, 441,888 completed. Plus 7,920 Volty, grid and DCA rows, 1,638 cycle tests, correlation tests of 18 features at six horizons and the reversal studies |
| [All-strategy walk-forward](../json/hype-structure-20261127/backtests/all-1d-spot-6bps/report.md) | Hyperliquid perpetual candles: 722 daily bars from 2024-12-05, 4,999 hourly bars from 2026-05-03 | 34 registered strategies, first 70% against last 30%, at 6 and 25 bps, long or cash, and as a 1× perpetual long with a borrow fee |
| [Price structure](../json/hype-structure-20261127/structure.md) | The same Hyperliquid candles, plus BTC, ETH and SOL daily | Swing levels, volume by price, level tests, calendar effects, declines, co-movement |

Coinbase HYPE/USD was not used here. Its minute candles have gaps: the
[Coinbase HYPE suite](results/hype_suite_20261127.md) found that the longest
gap-free minute run in 31 days was 46 hours. Binance's first HYPE/USDT daily
candle is dated 2026-09-24 (seen at fetch time, not archived), so the long
history comes from Hyperliquid, where HYPE has traded since late 2024. USDT is not USD, and a perpetual is not spot; each
table names its market.

## Strategy results

### One week of minute bars

The week ended where it began: $65.63 to $65.60, between $55.80 and $69.80. The
training part fell 4.9%, the validation part fell 1.5% and the final-test part
rose 6.8%.

Share of the 1,707 unfiltered strategies that made money over the whole week:

| Bar size | At 10 bps per fill | At 60 bps per fill | Holding, 10 bps |
|---|---:|---:|---:|
| 1 minute | 4.0% | 1.1% | −0.2% |
| 5 minutes | 44.1% | 4.9% | +0.3% |
| 10 minutes | 65.4% | 10.0% | +0.5% |
| 1 hour (1,027 completed) | 66.4% | 38.7% | +0.6% |

Each fee level also pays a 2 bps execution allowance per fill.

The strictest screen asks for at least ten validation exits and a positive
return in validation, in the final test and over the whole week, at both 10 and
60 bps. Twelve distinct 5-minute policies pass (nine ATR-sized, two GARCH
volatility-target, one volatility-target), three 10-minute policies and three
1-hour policies. No 1-minute policy passes.

| Bars | Policy | Whole week, 10 bps | Whole week, 60 bps | Validation / test, 60 bps | Worst decline | Exits |
|---|---|---:|---:|---:|---:|---:|
| 5m | ATR-sized: ATR 45, risk 1%, stop 2 ATR, trend 200 | +16.3% | +4.1% | +2.6% / +3.5% | −6.4% | 76 |
| 5m | ATR-sized: ATR 30, risk 1%, stop 1.5 ATR, trend 200 | +16.5% | +4.0% | +3.6% / +3.5% | −7.4% | 40 |
| 10m | ATR-sized: ATR 30, risk 1%, stop 2 ATR, trend 100 | +14.3% | +4.1% | +1.2% / +0.7% | −4.6% | 98 |
| 1h | Average of MACD 12/26/9, PPO 12/26/9 and RSI 14 (30 → 50) | +4.6% | +0.5% | +1.3% / +0.6% | −5.7% | 40 |

The selection rule frozen before the test (best validation return, ten exits)
picked the 5-minute ATR 30 row. Its final test returned +6.6% at 10 bps
on three exits, while holding returned +6.8%. So the test confirms the rule did
not lose in a rally; it does not show it beats holding in one. Under 3.2% of
strategies beat holding in the final test at any bar size.

Median whole-week return of one-member strategies on 5-minute bars at 10 bps,
grouped by that member's rule. About one in eight also carries a gate or
switch, and each family spans several parameter settings:

| Best families | Median | Worst families | Median |
|---|---:|---|---:|
| ATR-sized trend | +9.9% | PPO | −15.5% |
| Moving-average regime | +9.0% | Dual momentum | −13.3% |
| EMA crossover | +8.4% | MACD | −8.7% |
| Keltner breakout | +8.1% | Z-score reversion | −8.0% |
| Ichimoku | +6.9% | Bollinger reversion, stochastic | −7.3% |

On 5-minute bars this week, slow trend filters with wide stops made money and
fast oscillators and reversion rules lost. That did not hold at other sizes: on
1-minute bars the ATR-sized family's median was −31.5% and no family had a
positive median except DCA.

Other models from the ZEC suite, at 10 bps:

- **Volty breakout stops, synthetic 1× long/short.** On 1-minute bars none of
  150 runs made money. On 5-minute bars 3% did. On 1-hour bars 60% did, and 13
  of 50 settings were positive in validation and in the final test even on the
  least favourable intrabar path. The best of those, length 2 with 1.25 ATR,
  made +28.6% over the week. On 10-minute bars six settings
  passed the same screen; length 4 with 1.25 ATR made +17.9%.
- **Ladder grid.** All eight reference grids made money on 5-minute and 1-hour
  bars (median +2.2% and +2.7%, best +4.2%). The week's range suited a grid.
- **DCA with safety orders.** Ten of twelve were positive on 5-minute bars and
  all twelve on 1-hour bars (median +0.3% and +0.6%, best +4.8%).

### Two years of daily bars

Hyperliquid perpetual candles, 2024-12-05 to 2026-11-26. Long or cash, 6 bps fee
plus 2 bps slippage, signals fill at the next open. The first 70% ends on
2026-04-23.

| Strategy | Total return | Sharpe | Worst decline | Trades | First 70% | Last 30% |
|---|---:|---:|---:|---:|---:|---:|
| Buy and hold | +389.4% | 1.29 | −68.0% | 1 | +224.7% | +51.0% |
| Moving-average crossover 20/50 | +172.7% | 1.09 | −39.7% | 6 | +107.8% | +31.5% |
| Moving-average ribbon 5×10 | +138.4% | 1.03 | −42.2% | 209 | +71.6% | +39.2% |
| Time-series momentum, 60 days | +124.6% | 0.94 | −58.3% | 16 | +77.9% | +26.4% |
| VWAP reversion 20 / 2% | +96.9% | 0.84 | −46.9% | 41 | +51.0% | +30.5% |
| Volatility target 60% | +89.7% | 0.93 | −44.3% | 180 | +54.5% | +22.9% |

Fourteen of 30 distinct strategies made money in both parts (the registry also
lists holding itself and three copies of MACD). None beat holding in either
part. Reversion rules made money here too: Z-score +83.5%, stochastic +76.4%,
against +29.4% for the Bollinger breakout. In a market that rose 389%, any
long-or-flat rule that stays invested much of the time collects part of the
rise. At 25 bps the crossover still returned +166.6% and the ribbon +125.7%.
The crossover's case is risk, not return: it gave up 56% of the gain and took
42% less of the worst decline.

A 1× perpetual long under the backtester's Jupiter-style borrow fee kept +143.4%
of the +389.4%, paid $15,084 in borrow fees on $10,000 and was liquidated once
in the model. That run also set the backtester's short permission, but no
registered strategy emits a short, so it tests the borrow fee and nothing else.

### 208 days of hourly bars

2026-05-03 to 2026-11-27. The first 70% (to 2026-09-25) rose 122%. The last 30%
fell 28.6%.

| Strategy | Total return | Sharpe | Worst decline | Trades | First 70% | Last 30% |
|---|---:|---:|---:|---:|---:|---:|
| Bollinger breakout 20 / 2 | +106.8% | 2.78 | −17.0% | 86 | +110.0% | −1.5% |
| EMA crossover 50/200 | +87.9% | 2.07 | −22.7% | 10 | +91.9% | −1.3% |
| 200-bar average regime | +83.2% | 2.02 | −25.8% | 78 | +104.2% | −10.3% |
| Buy and hold | +58.8% | 1.37 | −42.1% | 1 | +122.4% | −28.6% |
| Oversold bounce (RSI < 30 and lower-band touch) | +25.2% | 2.41 | −8.8% | 60 | −1.2% | +26.7% |
| RSI 14 (30 → 50) | +9.1% | 0.60 | −21.9% | 35 | −3.2% | +12.7% |

No strategy made money in both parts. The trend rules beat holding because they
stood aside for most of the fall. The bounce rules made money only in the fall.
At 25 bps only the EMA crossover (+80.9%) still beat holding (+58.2%), and the
oversold bounce fell to −0.3% overall.

## Patterns

### What the data supports

- **Large, frequent declines.** Seven declines of 25% or more since December
  2024: −73.7% over 107 days, −34.0% over 5, −28.9% over 19, −65.6% over 125,
  −30.6% over 9, −33.7% over 47, and the present one, −43.1% from $98.00 on
  2026-09-23 to $55.74 on 2026-11-21. A decline is counted as finished only when
  price makes a new high, so the six finished ones say nothing about how the
  present one ends.
- **High volatility.** 102% annualized over two years, 83% over the last 30
  days. The 14-day average true range is 9.7% of price.
- **Bitcoin beta above one.** Daily correlation with BTC 0.54, beta 1.26. With
  ETH 0.56 and 0.83, with SOL 0.56 and 0.74. Over the week of minute bars the
  same-minute correlation with BTC was 0.73.
- **A US-hours volume peak.** 13:00–16:59 UTC carries 26.4% of hourly volume.
  Average absolute hourly moves peak at 0.82–0.83% at 14:00 and 15:00 UTC and
  bottom at 0.49–0.50% at 06:00 and 09:00 UTC.
- **Swings of 1% a few hours apart.** In the week of minute bars, 1% peaks came
  a median 145 minutes apart and dips 158 minutes apart. The spacing was more
  even than 95% of shuffled paths in 5 of 24 comparisons, uncorrected. The
  formal cycle tests below found no clock to trade on.

### What the data does not support

- **Weekday effects.** Wednesday +1.26% (t = 2.18, 103 days), Tuesday −0.31%,
  Thursday −0.42%. Seven tests need |t| near 2.7. None reaches it.
- **Hour-of-day direction.** 01:00 UTC averaged −0.13% (t = −2.17). Twenty-four
  tests need |t| above 3. None reaches it.
- **Buying big down days.** After a daily loss of 10% or more the next day
  averaged +2.30% (standard error 1.26%, 18 cases). After a gain of 10% or more
  it averaged +1.86% (35 cases). The average day returned +0.35%. Neither case
  separates from the other, and each is within two standard errors of the
  average day.
- **The ZEC two-bar reversal.** After one or two up ten-minute bars and a first
  close below the open, price continued down 39% to 53% of the time over 5, 10
  and 20 minutes. The unconditional rate was 49.5% to 49.9%. Of 72 intervals,
  66 contain the baseline. The six that do not are two results, each repeated
  across variants, and both point the other way: 41% of 200 cases (one up bar,
  intrabar trigger, 5 minutes) and 39% of 131 cases (two up bars, midpoint
  trigger, 20 minutes, non-overlapping).
- **Reversal shapes.** The rule chosen on validation (two down 5-minute bars in
  a falling shape, predict up) was right 69% of 29 times in validation and 48%
  of 25 times in the final test, and lost money there at every cost level.
- **Cycles.** 1,638 spectrum and rolling-fit tests, smallest corrected p-value
  1.0. The correction's floor of 0.819 makes this inconclusive, not a proof of
  absence. The fitted cycle forecast was worse than assuming price stays put.
- **Leading correlations.** 18 features at six horizons. None survived the
  correction on the final test. The largest training correlation, the last
  minute's BTC return against HYPE's next hour (−0.24), kept its sign but not
  its significance (p = 0.95).

## Price levels

Levels are swing highs and lows that were the extreme of 5 days each side (daily)
or 24 hours each side (hourly). Swings are grouped so that no group is wider
than 3% (daily) or 1.2% (hourly). Volume zones spread each bar's volume across
its range. Prices are Hyperliquid perpetual prices, which can differ slightly
from Binance spot. Sides are relative to the last hourly close, $65.40.

| Zone | Side | Evidence |
|---|---|---|
| $95.34–98.00 | Resistance | All-time high $98.00 on 2026-09-23; three daily swing highs to 2026-10-29 |
| $75.99–95.65 | Resistance | 70% of the last 90 days' volume traded here; most-traded price $81.10 |
| $74.30–78.35 | Resistance | Twenty hourly swings in four adjoining groups, latest 2026-11-13; four daily swings at $75.15–77.00, including the June highs $75.83 and $77.00. 50-day average $76.13 |
| $71.04–72.91 | Resistance | Six hourly swings, latest 2026-11-16 |
| $68.62–70.25 | Resistance | Eight hourly swings, latest 2026-11-23; the week's high ($69.70 on Hyperliquid, $69.80 on Binance). 200-day average $70.40 |
| $67.76–68.34 | Resistance | Four hourly swings from June and July; 20-day average $67.72 |
| $65.43–66.14 | Resistance, just above | Five hourly swings from June and July |
| $64.50–65.10 | Support, just below | Five hourly swings, latest 2026-11-18 |
| $62.42–63.35 | Support | Four hourly swings from May to July |
| $59.70–60.55 | Support | Five hourly swings and the 2026-11-14 daily low $59.70; volume node $60.68 |
| $57.96–59.47 | Support | Three daily swings, including the September 2025 high $59.47; seven hourly swings at $57.96–58.55 |
| $55.28–56.50 | Support | Nine hourly swings, latest 2026-11-25; the 2026-11-21 low $55.74 |
| $51.08–54.00 | Support | Five daily swings at $51.08–52.61, including the 2026-08-02 low; eight hourly swings at $52.61–54.00 |
| $49.59–50.16 | Support | Three daily swing highs from 2025, including the July 2025 high $49.89 |
| $42.50–45.84 | Support | Six daily swings; the most-traded price of the two years, $43.63 |
| $38.16–41.71 | Support | Twelve daily swings; volume node $38.69 |

### Did the levels work?

Each test is a return to a swing level that was already confirmed and not yet
broken, entered at that bar's close. Tests on one side do not overlap. A level
held when no close in the horizon went through it by the touch tolerance (1.5%
daily, 0.5% hourly).

The fair comparison is not the average bar, because every test follows a move
toward the level. The placebo columns apply the same rules to lines 6% (daily)
or 2% (hourly) above and below each swing level. If swing levels mattered, they
would hold more often than those lines.

| Bars and horizon | Side | Tests | Held | Average after | Standard error | Placebo tests | Placebo held | Placebo average after |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Daily, 5 days | Support | 31 | 48% | +1.09% | 1.90% | 43 | 42% | +1.19% |
| Daily, 5 days | Resistance | 30 | 37% | +3.82% | 1.95% | 49 | 39% | +1.98% |
| Daily, 10 days | Support | 23 | 35% | +3.06% | 3.83% | 31 | 42% | +4.53% |
| Daily, 10 days | Resistance | 23 | 39% | +5.56% | 3.77% | 32 | 31% | +3.76% |
| Hourly, 24 hours | Support | 46 | 26% | −0.67% | 0.46% | 78 | 35% | −0.31% |
| Hourly, 24 hours | Resistance | 45 | 33% | −0.36% | 0.83% | 65 | 28% | −0.04% |
| Hourly, 72 hours | Support | 29 | 10% | −0.77% | 1.28% | 36 | 14% | −1.13% |
| Hourly, 72 hours | Resistance | 29 | 17% | +0.51% | 1.75% | 37 | 22% | +0.48% |

The average over all bars was +1.81% for 5 days, +3.50% for 10 days, +0.31% for
24 hours and +0.84% for 72 hours.

The swing levels did no better than arbitrary lines nearby. They held between
10% and 48% of the time; the placebo lines held between 14% and 42%, and the
largest real-against-placebo gap, in hold rate or in average return, is about
one standard error. The levels mark where price turned before. On this history
they did not make a return a reliable turn, and a level broke more often than
it held on every row.

## How this relates to the Coinbase HYPE suite

A second run of the same request, [the Coinbase HYPE suite](results/hype_suite_20261127.md),
used Coinbase HYPE-USD: 31 days of minute bars cut to a 46-hour gap-free run,
and 294 days of 5-minute, hourly and daily bars from the 2026-02-05 listing. It
named Hyperliquid candles as an unchecked second source. This study is that
check, on a gap-free Binance week and on Hyperliquid's two years.

| Question | Coinbase suite | This study |
|---|---|---|
| Is any strategy validated? | No. Every validation-selected policy lost on test | No. Nothing beat holding over two years, and no hourly rule made money in both parts |
| Hourly RSI bounce | RSI 14 (30 → 55) +16.7% on test, too few validation exits to select | RSI 14 (30 → 50) +12.7% and the oversold-bounce rule +26.7% in the falling last 30%; both lost in the rising part |
| Short test window | 5m positive at all fees on about 9 hours of test bars | 5m ATR-sized positive at 10 and 60 bps on about 34 hours of test bars |
| Short-horizon patterns | None significant on HYPE after correction | Two-bar reversal, shapes, cycles and leading correlations all fail |
| Support and resistance | No edge over a moving-average control | No edge over offset placebo lines |

The two agree where they overlap. The new evidence here is the full week of
minute bars, the 2024–2026 history that the Coinbase listing cannot reach, and
the level map.

## Not transferred from the ZEC suite

- The Jupiter GUM 25× five-minute walk-forward. It needs weeks of captured GUM
  prices and funding for HYPE. The repository's Perps records put HYPE's cap
  there at 25×.
- Order-book replay, the Oracle second-turn, barrier and exit-50 studies, the
  top-50 universe, daily CPCV and the long-history shape router. The weekly
  run's `coverage.json` lists each exclusion and its reason.

## Limits

- One week holds few independent market states. The week's winners were chosen
  from 1,707 overlapping templates; the best of many is biased upward.
- The whole-week returns include the training part. Only the validation and
  final-test columns are out of sample, and each covers about 34 hours.
- Costs are modelled. Spreads, depth, latency, funding and real fills are absent.
  Reference accounts of 10,000 USDT have no capacity model.
- The daily and hourly strategies use default parameters, one split and no
  correction for testing 34 of them.
- The level tests reuse one history. Hourly levels come from 208 days that
  contain one rise and one fall.

## Reproduce

Python 3.13 with `backtester/requirements.txt`, from the repository root.

```bash
cd /Users/mitch/dev/solmargintrader
python -m zipfile -e research/json/hype-week-20261127/artifacts.zip /Users/mitch/.local/share/solmargintrader/research/weekly-coin/HYPE-20261127-reproduction
python -m research.coin_week --output /Users/mitch/.local/share/solmargintrader/research/weekly-coin/HYPE-20261127-reproduction --phase verify
python -m research.coin_structure analyze --output research/json/hype-structure-20261127
```

A fresh week and fresh history:

```bash
python -m research.coin_week --coin HYPE --output /Users/mitch/.local/share/solmargintrader/research/weekly-coin/HYPE-new
python -m research.coin_structure fetch --coin HYPE --output /Users/mitch/.local/share/solmargintrader/research/coin-structure/HYPE-new
python -m research.coin_structure analyze --output /Users/mitch/.local/share/solmargintrader/research/coin-structure/HYPE-new
```

`research.coin_structure` works for any coin Hyperliquid lists. The backtests
ran `python -m backtester.cli --asset HYPE --data <csv> --interval 1d|1h --split 0.7`
with every registered strategy named; each run's `run_manifest.json` records its
inputs.
