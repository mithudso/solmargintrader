# Compound 5m frontier: fewer, stronger, longer calls (2026-11-07)

The owner's question: the reversion metrics "are doing ok in testing" (52% out-of-sample hit on SOL)
but every row says the profit is eaten by fees. How do you get around that, and is there a better
strategy nearby? This page answers both with the frontier sweep (run `20261107T202943Z`, 1,250
configurations, ten coins, full 1-minute history) and the in-sample-only tuner
(`research/frontier_tune.py`, results in `research/results/frontier-2026-11-07.json`).
Simulation only; nothing here places an order.

## 1. The 52% hit rate was never an edge

On SOL (90,316 recent 5m bars) RSI, Bollinger, z-score, CCI, stochastic and VWAP reversion call the next
bar right 51.3-51.9% of the time, and their average signed move is **-0.23 to +0.16 bps per call**. The
wins are smaller than the losses. That holds from the next bar's open as well as close-to-close, so it is
not a fill-timing artifact, and it holds at every holding period from 5 minutes to 4 hours. The best raw
number anywhere was liquidity_sweep held 1 hour: **+1.25 bps** against a **13 bps** round trip. No fee
trick turns zero gross into profit: the fees are not the problem, the missing gross edge is.

## 2. How a call can beat the fees

A round trip on Hyperliquid costs 13 bps (4.5 bps taker + 2 bps slippage, each side). A 5m bar moves
6-23 bps. The levers, in the order they matter here:

1. **Trade only the strongest readings.** `entry_quantile` (new) takes a call only when |composite| is in
   the top (1 - q) of its own trailing two weeks: q = 0.98 keeps the strongest 2%.
2. **Hold long enough for the move to dwarf the toll.** `hold` (new) keeps a position N bars after entry
   (only a blocking gate ends it early). One round trip then pays for an hour or a day of movement.
3. **Do not lever a long hold.** At 5x a 24-hour hold is mostly volatility drag: `htf_trend` top 2%
   held 24 h on SOL made **+20%** out-of-sample at 1x and **-53%** at 5x, same calls, same costs.
4. **Pay maker fees where the strategy allows it.** Hyperliquid's maker fee is 1.5 bps (0 above
   $500M/14 days); taker 4.5. Resting limit orders fill only when price comes to you, which is adverse
   selection; the repo has never measured the fill rate, so no number here assumes maker fills.
5. **Cheaper venue.** Hyperliquid's 13 bps beats Jupiter's 16 (already the default since #75).

Every Compound backtest row now carries **net bps 1h / 24h**: what each call earned held that long from
the next bar's open, after one round trip. That column is the direct answer to "can this metric pay its
fees if I hold it?".

## 3. The frontier sweep: every metric, strongest 2%, held 1 h / 4 h / 24 h, 1x

Out-of-sample = the last 30% of each coin's history. Medians across the ten coins.

| configuration (ten coins) | in-sample median Sharpe | OOS median Sharpe | OOS median return | OOS > 0 | beat buy & hold |
| --- | --- | --- | --- | --- | --- |
| RSI alone, every call, 5x (the old view) | -11.50 | -14.46 | -100.0% | 0/10 | 0/10 |
| Bollinger alone, every call, 5x | -14.00 | -17.85 | -100.0% | 0/10 | 0/10 |
| Compound, every call, 5x | -17.21 | -20.96 | -100.0% | 0/10 | 0/10 |
| htf_trend: top 2%, held 1 h, 1x | +0.03 | +0.57 | +15.5% | 8/10 | 7/10 |
| htf_trend: top 2%, held 4 h, 1x | +0.01 | +0.54 | +14.6% | 8/10 | 7/10 |
| htf_trend: top 2%, held 24 h, 1x | +0.11 | +0.49 | +9.3% | 6/10 | 5/10 |
| mom_skip: top 2%, held 1 h, 1x | -0.23 | -0.32 | -17.9% | 2/10 | 7/10 |
| mom_skip: top 2%, held 4 h, 1x | -0.12 | -0.40 | -19.1% | 1/10 | 5/10 |
| mom_skip: top 2%, held 24 h, 1x | +0.52 | -0.56 | -32.1% | 3/10 | 5/10 |
| rsi: top 2%, held 1 h, 1x | -1.36 | -3.20 | -93.3% | 0/10 | 1/10 |
| rsi: top 2%, held 4 h, 1x | -1.57 | -2.91 | -94.2% | 0/10 | 0/10 |
| rsi: top 2%, held 24 h, 1x | -1.08 | -2.26 | -93.3% | 0/10 | 0/10 |
| bollinger: top 2%, held 1 h, 1x | -4.24 | -5.96 | -99.8% | 0/10 | 0/10 |
| bollinger: top 2%, held 4 h, 1x | -2.73 | -3.79 | -98.9% | 0/10 | 0/10 |
| bollinger: top 2%, held 24 h, 1x | -2.31 | -2.97 | -97.7% | 0/10 | 0/10 |
| zscore: top 2%, held 1 h, 1x | -2.10 | -3.68 | -97.6% | 0/10 | 0/10 |
| zscore: top 2%, held 4 h, 1x | -1.97 | -3.00 | -97.3% | 0/10 | 0/10 |
| zscore: top 2%, held 24 h, 1x | -1.40 | -2.12 | -95.3% | 0/10 | 0/10 |
| cci: top 2%, held 1 h, 1x | -4.25 | -6.06 | -99.9% | 0/10 | 0/10 |
| cci: top 2%, held 4 h, 1x | -2.68 | -3.94 | -99.4% | 0/10 | 0/10 |
| cci: top 2%, held 24 h, 1x | -2.36 | -3.19 | -99.0% | 0/10 | 0/10 |
| vwap_reversion: top 2%, held 1 h, 1x | -2.69 | -3.53 | -98.2% | 0/10 | 0/10 |
| vwap_reversion: top 2%, held 4 h, 1x | -2.06 | -2.83 | -97.2% | 0/10 | 0/10 |
| vwap_reversion: top 2%, held 24 h, 1x | -1.80 | -2.42 | -93.7% | 0/10 | 1/10 |
| liquidity_sweep: top 2%, held 1 h, 1x | -5.62 | -8.73 | -100.0% | 0/10 | 0/10 |
| liquidity_sweep: top 2%, held 4 h, 1x | -2.84 | -4.25 | -99.3% | 0/10 | 0/10 |
| liquidity_sweep: top 2%, held 24 h, 1x | -2.33 | -3.42 | -98.3% | 0/10 | 0/10 |
| ou_reversion: top 2%, held 1 h, 1x | -2.15 | -2.72 | -88.7% | 0/10 | 0/10 |
| ou_reversion: top 2%, held 4 h, 1x | -1.51 | -2.17 | -85.9% | 1/10 | 0/10 |
| ou_reversion: top 2%, held 24 h, 1x | -1.09 | -1.62 | -84.7% | 0/10 | 1/10 |
| vr_regime: top 2%, held 1 h, 1x | -3.25 | -4.71 | -72.3% | 0/10 | 1/10 |
| vr_regime: top 2%, held 4 h, 1x | -2.42 | -3.59 | -68.0% | 0/10 | 1/10 |
| vr_regime: top 2%, held 24 h, 1x | -1.80 | -2.50 | -76.8% | 0/10 | 0/10 |
| pairs_spread: top 2%, held 1 h, 1x | -0.28 | -0.55 | -44.2% | 0/10 | 3/10 |
| pairs_spread: top 2%, held 4 h, 1x | -0.30 | -0.54 | -42.3% | 1/10 | 3/10 |
| pairs_spread: top 2%, held 24 h, 1x | -0.25 | -0.41 | -38.5% | 1/10 | 4/10 |
| keltner: top 2%, held 1 h, 1x | -5.08 | -6.37 | -99.5% | 0/10 | 0/10 |
| keltner: top 2%, held 4 h, 1x | -3.47 | -3.96 | -98.9% | 0/10 | 0/10 |
| keltner: top 2%, held 24 h, 1x | -2.68 | -2.52 | -97.0% | 0/10 | 0/10 |
| consec_run: top 2%, held 1 h, 1x | -4.19 | -7.01 | -99.0% | 0/10 | 0/10 |
| consec_run: top 2%, held 4 h, 1x | -2.60 | -3.58 | -98.2% | 0/10 | 0/10 |
| consec_run: top 2%, held 24 h, 1x | -1.78 | -2.39 | -97.2% | 0/10 | 0/10 |

Median buy-and-hold over the same out-of-sample windows: -22.0% (range -62% to +49%).

**What survived:** one metric family. `htf_trend` (the coin's 15-minute close against an EMA of 15-minute
closes, scaled by ATR) taking only its strongest 2% of readings, held 1-4 hours, unlevered, was profitable
out-of-sample on 8 of 10 coins and beat buying and holding on 7. **Read it with three caveats:**
its in-sample Sharpe was about zero (+0.01 to +0.11), so nothing in the training years pointed to it;
the out-of-sample stretch fell for most coins (median buy-and-hold -22%), the regime where trend
following shines and the only regime this test saw; and 1,250 configurations were tried, so the best of
them would look good by luck alone.

**What did not:** every reversion metric, at every hold, lost on every coin (RSI top 2% held 1 h: -93%).
Selectivity and longer holds made them lose more slowly, not win. The six new research metrics
(`keltner`, `mom_skip`, `vr_regime`, `ou_reversion`, `consec_run`, `pairs_spread`) are in the scorecard,
off by default, and none earned a vote: `mom_skip` held 24 h had the best in-sample Sharpe (+0.52)
and lost out-of-sample (-0.56), the textbook overfit.
