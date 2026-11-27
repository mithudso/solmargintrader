# Does any current strategy make 1% a day? (2026-11-27)

**No.** Neither strategy the repository is currently running or preparing reaches 1% a day after
costs, at any leverage, in any window. The leveraged accounts lose faster than the 1x accounts.
The funded-owner candidate, Volty(10 × 1.5) on ZEC 5m, loses 97% of a 1x account over 295 days,
and the 25× account it was built for is liquidated in every window tested. The only accounts
that came near 1% a day were leveraged *buy and hold* ZEC accounts during ZEC's February to
September rally. That is market exposure, not an edge, and the same accounts lost 66% (3x) in
the last 89 days.

1% a day compounded is **37.8× a year** (+3,678%).

## What was tested

| Account | Rule | Why it is here |
| --- | --- | --- |
| `zec-volty` | Volty Expan Close, SMA(TR,10) × 1.5 stops around the prior close, 5m, stop-and-reverse, long or short | The frozen rule behind the standalone funded GUM owner (TASK-2660). No funded order exists yet. |
| `zec-volty-sl0.8` | Same, plus the study's 0.8% stop loss | Card #1 of the 6,048-case GUM walk-forward. |
| `hype-rsi` | RSI(14) < 30 buy, > 55 exit, 1h, long or flat | The live 14-day HYPE paper forward test. |
| `*-hold`, `*-spot-hold` | Buy and hold ZEC, HYPE, BTC | The bar any strategy must clear. |
| Experiments | Volty on 1h and 4h bars, Volty 5m with maker fills, daily SMA 20/50 trend filter | Candidate improvements, added after the first run showed what the 5m costs do. |

Data: Coinbase 5m candles committed in `research/hype-suite/history/` (2026-02-05 to 2026-11-26,
295 days, hashes in the manifest and in `results.json`). Missing 5m slots (79 to 125 per coin,
about 0.1%) become flat bars at the last close. No network is used.

Costs on every fill, every account:

| Venue model | Taker fee | Slippage | Funding | Maintenance | Liquidation fee |
| --- | ---: | ---: | ---: | ---: | ---: |
| GUM (ZEC, BTC) | 3.5 bps | 2 bps | 0.1 bps/h on notional | 1% | 0.75% |
| Hyperliquid (HYPE) | 4.5 bps | 2 bps | 0.125 bps/h | 3% | 0 |
| Coinbase spot (1x hold) | 25 bps | 2 bps | 0 | n/a | n/a |

Funding is charged whatever the side, which is conservative for a long/short rule. Position size
is leverage × current equity at each entry (compounding). Liquidation is checked on the bar's
whole assumed path (open, nearer extreme, farther extreme, close), so a wick that closes flat
still liquidates.

Windows: the full period, the first 70% and the last 30%. For Volty, three more windows matter.
The rule was **selected** on GUM data from 2026-10-14 to 2026-11-11, so February 5 to September 30
is a clean out-of-sample period *before* selection, and November 18 onward is out of sample
*after* it.

## Results

Net of all costs. "Geo/day" is the compounded daily return; the target is +1.00%.

| Account | Window | Lev | Geo/day | Total | Max DD | Trades | Liq. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| zec-volty | full 295 d | 1x | −1.19% | −97.1% | 97.3% | 3,686 | 0 |
| zec-volty | out of sample, before selection | 1x | −1.27% | −95.1% | 95.8% | 3,083 | 0 |
| zec-volty | selection window | 1x | −1.22% | −29.2% | 37.8% | 285 | 0 |
| zec-volty | out of sample, after selection | 1x | −1.14% | −9.8% | 20.8% | 102 | 0 |
| zec-volty | full 295 d | 25x | −100% | −100% | 100% | 66 | 7 |
| zec-volty | out of sample, after selection | 25x | −87.5% | −100% | 100% | 99 | 3 |
| zec-volty-sl0.8 | full 295 d | 1x | −1.16% | −96.8% | 97.6% | 4,259 | 0 |
| hype-rsi | full 295 d | 1x | +0.02% | +5.8% | 25.6% | 41 | 0 |
| hype-rsi | last 30% | 1x | +0.23% | +23.0% | 10.7% | 19 | 0 |
| hype-rsi | last 30% | 5x | +1.01% | +145.2% | 48.7% | 19 | 0 |
| hype-rsi | full 295 d | 5x | −0.10% | −24.5% | 82.7% | 41 | 0 |
| zec-spot-hold | full 295 d | 1x | +0.34% | +170.5% | 63.3% | 0 | 0 |
| zec-hold (perp) | full 295 d | 3x | +0.59% | +458.5% | 85.5% | 0 | 0 |
| zec-hold (perp) | last 30% | 3x | −1.19% | −65.6% | 92.5% | 0 | 0 |
| hype-spot-hold | full 295 d | 1x | +0.22% | +89.6% | 42.9% | 0 | 0 |
| btc-spot-hold | full 295 d | 1x | −0.06% | −17.2% | 36.2% | 0 | 0 |

The full table, with every window, leverage, Sharpe, Sortino, best and worst day, fees and
funding, is in [`report.md`](../../json/target-1pct-day/report.md) and
[`results.json`](../../json/target-1pct-day/results.json).

### Why Volty loses

Before costs, Volty 5m returned −2.4% in its own selection window and +1.1% after it: about zero.
It trades about 12 times a day. At 11 bps a round trip, fees alone cost 94% of the starting
balance over the 295 days at 1x. Leverage multiplies the fee drag and the volatility drag, so
every leveraged account dies sooner. A 25× account is liquidated by a 3.9% adverse move, which
ZEC makes inside one 5m bar several times a month.

This replay agrees with the repository's own engine (`backtester/core/volty.py`) to nine decimal
places at 1x (`research/tests/test_target_1pct_day.py`). It does not reproduce the GUM study's
+2.63% development result. That study held a fixed $250 notional on a $1,000 account (0.25×),
priced GUM trade candles, and used completed-5m entries with a next-minute path. Here the account
is fully invested and priced on Coinbase candles. Both say the same thing about the edge: it is
small and did not survive the added week (−2.79% there).

### One-year bootstrap

Seven-day blocks of each full-period daily return series, resampled into 4,000 one-year paths:

| Account | Median year | P(1%/day) | P(loss) | P(DD ≥ 50%) |
| --- | ---: | ---: | ---: | ---: |
| zec-volty 1x | 0.01× | 0% | 100% | 100% |
| hype-rsi 1x | 1.09× | 0% | 38% | 1% |
| hype-rsi 3x | 1.06× | 0% | 47% | 70% |
| zec-hold 1x | 4.07× | 4.8% | 15% | 84% |
| zec-hold 3x | 14.9× | 33.9% | 13% | 100% |
| zec-ma20/50-1d 3x | 8.85× | 23.3% | 12% | 96% |

The bootstrap replays ZEC's own past rally, so it is optimistic for the hold accounts. Even so,
every account with a real chance of hitting the target is almost certain to halve first.

## Is 1% a day realistic?

Not as a sustained target. The best leverage for long-run growth (Kelly) earns about
Sharpe² / 2 per period. To compound 1% a day, a strategy needs a daily Sharpe of 0.14
(**annualised 2.7**) *and* must be run at full Kelly, which here means about 14% daily
volatility and a likely 50% drawdown on the way. At half Kelly the Sharpe needed is about 3.8.

For scale: ZEC's own 295-day drift (+0.64% a day mean, 6.85% daily volatility) is the best input
in this data, and full Kelly on it, *with perfect hindsight*, earns 0.43% a day. No account here
had a net annualised Sharpe above 2.7 in any window longer than 200 days, and the top five were all
leveraged buy and hold of ZEC during its rally.

A realistic stretch target is 0.1% to 0.3% a day (44% to 200% a year) with a drawdown limit,
measured out of sample.

## What to try next, in order

1. **Do not fund the 25× Volty owner.** It is liquidated in every window here, including both
   out-of-sample periods. Keep it paper-only.
2. **Cut turnover before looking for signal.** At 1x over the full period the same Volty rule
   made +70% on 4h bars, +14.8% on 1h bars, and +17.8% on 5m bars with maker fills (0.5 bps, no
   slippage), against −97% for 5m taker fills. The 1h version also made +68% in the last 30%
   (32% drawdown); the 4h version lost 23% there. Every one of them lost money at 2x or more over
   the full period. These are leads, not edges, and the 1h and 4h variants were chosen after the
   5m rule, not frozen in advance. Any 5m taker strategy needs more than 11 bps of edge per round
   trip to break even.
3. **Trend filter with at most 2× leverage on daily bars.** SMA 20/50 long-or-flat cut BTC's
   drawdown from 39% to 15% and turned −24% into +15%. On ZEC it kept most of the rally with a
   lower drawdown. It traded 2 to 4 times in 295 days, so it needs the two-year Hyperliquid daily
   history and a walk-forward before anyone believes it.
4. **Delta-neutral funding carry** on the zero-fee venues already researched. Realistic yields
   are 10% to 30% a year, not 1% a day, but they do not depend on direction.
5. **Fetch GUM's funding history** for the 295 days and rerun with `--funding-bps-h` set from it,
   so the funding line uses observed rates rather than a scenario.

## Reproduce

```sh
python3 -m research.scripts.target_1pct_day                       # defaults above, about 35 s
python3 -m research.scripts.target_1pct_day --funding-bps-h 0.5   # costlier funding
python3 -m research.scripts.target_1pct_day --fee-bps 0.5 --slip-bps 0 --out /tmp/maker
python3 -m unittest research.tests.test_target_1pct_day -v        # 7 tests
```

Options: `--history DIR` (5m CSVs), `--out DIR` (default `research/json/target-1pct-day/`),
`--target 0.01`, `--leverages 1,2,3,5,10,25`, `--fee-bps 3.5`, `--slip-bps 2`,
`--funding-bps-h 0.1` (HYPE uses 1.25× this), `--mc-paths 4000`, `--seed 7`.

Limits: trade candles stand in for venue marks; the OHLC path inside a bar is assumed; funding
is a flat scenario; 295 days is one market regime per coin. This is a research model. It never
signs, sends or reads a wallet.
