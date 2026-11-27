# HYPE study: strategies, patterns and levels (2026-11-27)

Report version: 1.0.0. Research only. Not investment advice. No order was placed and no recorder, paper trial or account was touched.

## What was run

The ZEC suite, repeated for HYPE, in three layers:

1. **Frozen 31-day candle study.** `python -m research.coin_week --coin HYPE --venue binance --days 31 --references BTC,ETH,SOL,ZEC`.
   Binance spot HYPEUSDT, 2026-10-27T08:49Z to 2026-11-27T08:49Z, 44,640 consecutive real 1m bars, strict gap policy.
   1,707 spot templates x 6 filter/control modes x 1m/5m/10m/1h x 4 fee scenarios (10/15/25/60 bps + 2 bps) = 491,712 completed rows.
   60/20/20 chronological split; validation alone selects; test never reranks. Also Volty, grid, DCA reference models,
   cycle spectra, pivot spacing, reversal excursions and 26-feature return correlations.
   Raw outputs (50 MB, untracked like the ETH study): `/Users/mitch/dev/solmargintrader/research/new-hype-study/` (`report.md`, `manifest.json`).
2. **Long-history cross-check.** Hyperliquid `candleSnapshot` for HYPE: 722 daily bars (2024-12-05 onward), 3,600 hourly bars (from 2026-06-30),
   run through `backtester.cli --strategy all --split 0.7` at 10 bps fee + 5 bps slippage.
3. **Levels and patterns.** Pivot clusters, volume at price, fibonacci retrace, seasonality, and an out-of-sample test of whether the levels work
   against a random-level control. Scripts: `research/scripts/hype_study/` (`hl_fetch.py`, `levels.py`, `levels_control.py`, `rank.py`).

Why Binance: in the earlier 2026-11-10 to 2026-11-17 batch study, Coinbase HYPE-USD had only 838 consecutive minutes and was marked `insufficient_history`.
Hyperliquid candles are the perpetual's prices, so they differ slightly from Binance spot.

## Companion study

`research/papers/results/hype_suite_20261127.md` (PR 368) ran an independent version on Coinbase spot: 294 days of 5m/1h/1d history from the 2026-02-05 listing, plus 31-day runs whose 1m windows shrank to 46 hours because of gaps.
It reaches the same conclusion: no validated strategy, no tradable pattern or support edge after costs, and RSI(14) 30/55 on HYPE 1h as the one forward-test candidate (+16.7% on its test window there, +8.2% on this study's test window).
This study adds a gap-free 31-day Binance 1m window, the full 491,712-row catalogue, and the Hyperliquid daily/hourly cross-check that its notes listed as not yet checked.

## Answer: best performing strategies

Context that decides everything: **HYPE fell 16.0% over the 31 days** (passive hold, 10 bps: full -16.0%, validation -9.6%, test about +15%).
Cash is 0%. Long/cash strategies that sat out the decline look good against that baseline.

| Window / cadence | Strategy (frozen parameters) | Full | Valid. | Test | Trades | Max DD |
|---|---|---:|---:|---:|---:|---:|
| 10m | Keltner breakout, ATR 5, EMA 12, mult 2 | +21.0% | +1.0% | +6.4% | 21 | -6.0% |
| 1h | majority[PPO + RSI(14, 30/50) + Bollinger breakout] | +17.7% | +4.0% | +11.4% | 17 | -11.4% |
| 1h | RSI(14), buy below 30, exit 55 | +15.7% | +1.7% | +8.2% | 9 | n/a |
| 5m | Keltner breakout, ATR 14, EMA 20, mult 4 (+ shape filter) | +12.3% | +0.0% | +3.2% | 13 | -2.4% |
| 5m | Bollinger breakout, 3 std, 20 bars | +10.2% | +2.1% | +6.1% | 29 | -10.1% |
| 1h | trigger: RSI<30 and Bollinger lower-band touch, 3-bar hold | +10.1% | +2.5% | +3.5% | 17 | -4.8% |
| 1h | Volty synthetic 1x long/short, length 10, 1.0 ATR (nearest intrabar path) | +37.5% | +10.7% | +28.6% | 83 | -28.0% |

These are rows that were positive in full, validation and test windows at 10 bps with at least ten trades. They are the best of a very large search.

What the winners have in common: **long-only dip buying and volatility-expansion entries (RSI oversold, Bollinger/Keltner breakout, VWAP discount)**, not trend following.

### Why none of this is a validated edge

- **Selection bias.** 491,712 rows from 1,707 overlapping templates; the study itself states no multiple-search profitability qualification exists. Treat the table as hypotheses.
- **Almost nothing survives.** At 10 bps: 0 of 10,242 1m candidate rows are positive in all three windows; 18 of 10,242 at 5m; 60 at 10m; 140 at 1h.
  At 60 bps only 811 of 40,968 full-window rows are positive. The 1m cadence is destroyed by costs (median unfiltered test return -29%).
- **Parameter fragility.** Keltner 10m: 43% of 37 configurations are positive over the full window, but only 11% are positive in validation. 1h RSI: 48% of 23 positive.
  Winners with 9 to 21 trades have wide error bars.
- **Validation-selected picks mostly did not hold.** The frozen choices scored on test: 10m RSI(45, 35/55) + harmonic filter +5.9% (9 exits);
  1m Bollinger breakout + slope filter +4.1% (43 exits); 5m fib retracement -7.4%; 1h VWAP reversion -2.7%; 1h RSI+voltarget -1.8%. Voltarget variants lost 0.1% to 1.5%.
- **One regime.** A down-month followed by a +15% last week. Long-only dip buying is exactly what that tape rewards.
- **Volty depends on the intrabar path assumption.** Same 1h config: +40.5% (low-first), +37.5% (nearest), +21.0% (high-first) at 10 bps; negative at 60 bps for all paths.
  It is synthetic 1x long/short with 0.1 bps/h carry, not Hyperliquid funding or real fills. 1m Volty lost 100%; 5m lost 99.5% (median).
- **Grid and DCA reference models lost.** DCA safety: 0 of 36 positive, medians -4.5% to -5.3%. Ladder grid: 1h -16.3% median, 5m best +2.2%, 1m best +0.3%.

### Long-history cross-check (Hyperliquid HYPE, spot, net of 10 + 5 bps)

| Cadence | Buy and hold | MA 20/50 | RSI 14 (30/50) | Breakout 20/10 |
|---|---:|---:|---:|---:|
| Daily, 722 bars, full | +388.7% | +170.5% (6 trades) | -6.3% | +7.6% |
| Daily, out-of-sample 30% | +50.7% | +31.1% | -3.5% | +13.3% |
| 1h, 3,600 bars, full | +0.1% | -13.0% | +8.6% (28 trades, DD -13.4%) | -14.6% |
| 1h, out-of-sample 30% | -21.3% | -10.6% | +15.2% | -22.6% |

Over two years nothing beat holding: HYPE went from $12.72 to about $65.5. Over the last five months of hourly bars only the RSI dip-buyer beat holding, which agrees with the 31-day study.
The default perp borrow model in `backtester` is Jupiter's, so a 3x perp run with it (buy and hold -88%) is not a HYPE result.
A rerun with Hyperliquid-like funding (0.125 bps/h) kept buy and hold on top (+714% at 3x, max drawdown -93%) and MA 20/50 at +18.7%. Leverage here is a drawdown amplifier, not an edge.

## Patterns

- **Trend state (2026-11-27, price $65.51).** ATH $98.00 on 2026-09-23, now -33.2%. Returns: 7d +7.4%, 30d -18.7%, 90d -21.4%, 180d -9.1%, 365d +88.6%.
  Price is below SMA20 $67.11, SMA50 $75.76 and SMA100 $80.65, and below SMA200 $70.51.
  Annualised volatility 102% (86% over the last 30 days).
- **No serial correlation.** Daily lag-1 autocorrelation 0.002; weekly 0.008.
- **No cycle.** Spectral tests at all four cadences: smallest conservative p = 0.21 (the dominant ~6-day period is the sample's own trend).
  Confirmed-pivot spacing is descriptive and mostly unremarkable: at 1m it sits inside the null band (peak/dip CV 0.91/1.02 against 0.90 to 1.14). At 5m and 10m the peak spacing is slightly more regular
  than the null's 5th percentile (CV 0.75 against 0.79, and 0.63 against 0.72), with a median swing spacing of about 3.5 to 5 hours (peaks 205 and 300 minutes, dips 195 and 270). At 1h it sits inside or just above the band
  (median 10.5 h between peaks, 12 h between dips). That spacing is not one of the Holm-corrected tests, so it is a lead, not a finding.
  A fitted harmonic forecast has lower RMSE than persistence (0.038 vs 0.060 log price) but only because it fits the trend; it is descriptive.
- **No cross-asset lead.** Same-minute correlation: BTC 0.65, ETH 0.66, SOL 0.69, ZEC 0.64. Of 26 features x 6 horizons, 0 final-test associations survive correction. Co-movement is not a signal.
- **Two-up-bar reversal.** After two up 10-minute bars the next bar is down 52.5% of the time (Wilson 49.4% to 55.6%, n=991) against 50.6% unconditionally. No usable edge.
- **Time of day (Hyperliquid 1h bars, last 150 days).** Volatility peaks 13:00 to 16:00 UTC (average hourly range about 1.6% at 14:00). The one weak return effect, 01:00 UTC at -15 bps (t = -2.4), is not significant after 24 hour comparisons. No weekday effect.

## Support and resistance (hourly/4h/daily pivot clusters, 2% clustering, touches in brackets)

| Resistance | Support |
|---|---|
| $68.78 (10), $71.39 (7), $74.98 (15), $77.59 (13), $80.33 (6), $83.25 (13), $86.80 (8), $89.52 (7), $95.09 (5), $97.55 (4) | $65.32 (10), $62.51 (5), $60.02 (7), $58.06 (11), $55.74 (11; the 2026-11-21 low), $53.32 (9), $51.40 (6, near the 2026-08-02 low $51.08), $49.84 (5) |

Deeper structure: $45.29, $43.41, $41.86, $40.31 (15), $38.42 (19, densest), $36.57, $35.10. Volume at price over the last 365 days is heaviest at $25 to $33, with a recent node at $60.55.
The 180-day range ($51.08 to $98.00) has retracement levels: 0.382 at $80.08, 0.5 at $74.54, 0.618 at $69.00, 0.786 at $61.12.
Price sits on the $65.32 cluster, with $68.78 and $71.39 the first overhead levels and $62.51 and $60.02 the first levels below.

**These levels describe where price paused. They do not predict.** In-sample, 54% of 1,087 touches held 1.5% for six 4-hour bars. Out of sample (levels formed before 2026-06-20, tested after),
they held 52.1% (37 of 71), inside a random-level control (mean 53.4%, 95th percentile 55.7%, 200 draws). Use them as reference prices for sizing stops, not as an entry signal.

## Not reproduced for HYPE

Jupiter GUM has no HYPE market, so the 25x five-minute directional books, captured-book replays, Oracle barrier/exit50 replay and daily CPCV have no HYPE inputs. The short side was not tested here:
every strategy above is long/cash. A Hyperliquid perp study with real funding and book data is the missing next step.

## Reading this result

No strategy shows a validated edge. If anything is worth a forward paper trial, the lead candidate is the 1h RSI dip buyer: it is positive in the 31-day study and beat holding in the independent five-month Hyperliquid 1h test (+8.6% against +0.1%, out-of-sample +15.2% against -21.3%).
The 10m Keltner breakout has only the 31-day evidence and a fragile parameter neighbourhood, so it ranks second. Run either on paper with frozen parameters and a finite sample before any funded use.
