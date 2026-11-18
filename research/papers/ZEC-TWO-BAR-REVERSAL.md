# Do two candles predict a ZEC reversal?

The next 10-minute candle reversed after two up candles in 19 of 24 observed cases, but after two down candles in only 16 of 29. This exploratory one-day study identifies an asymmetric pattern worth testing; it does not establish a profitable or reliable live betting rule.

Version: 1.0.0
Date: 2026-11-14
Author: Oraclebot Research
Status: Exploratory working paper; descriptive, not peer reviewed or prospectively validated.

[Download the paper as PDF](https://oraclebot.io/papers/zec-two-bar-reversal.pdf)

## Abstract

We examine candle-color streaks in 134,746 executed Coinbase ZEC-USD trades captured over a fixed 24-hour window. We construct complete receipt-time candles at 10 seconds, 1 minute, 5 minutes, 10 minutes and 1 hour, preserve flats, and conservatively exclude recorded gap candidates. In 135 valid 10-minute candles, the next candle was down after a rolling pair of up candles in 19/24 cases (79.2%). It was up after a rolling pair of down candles in 16/29 cases (55.2%), with one additional flat outcome. Mean fully observed up and down streaks terminating in the opposite color were 1.80 and 1.72 bars. These descriptive frequencies depend on the event definition and come from one previously examined day. They neither estimate an established future success probability nor simulate executable net returns.

## 1. Question and interpretation

The practical question is whether a trader should fade ZEC after two consecutive 10-minute candles of the same color. The evidence supports a candidate hypothesis after two up candles. It provides much weaker support for the symmetric rule after two down candles.

An average streak length is not a reversal timer. Even an independent fair up/down process has an expected run length of two. Its next direction remains 50/50 after two identical outcomes. Only a measured conditional distribution, evaluated beyond the discovery sample, can support a forecast.

This paper concerns the next completed 10-minute candle after two completed 10-minute candles. It does not predict the next ten seconds or describe two price ticks.

## 2. Data and construction

The immutable capture runs from 2026-11-12T04:56:27.224912Z through 2026-11-13T04:56:27.224912Z. The raw write-ahead log contains 1,459,542 records across captured channels. The accepted trade tape contains 134,746 executed trades; the larger record count is not the trade count.

We assign trades to fixed UTC-aligned buckets by receipt time, matching the accepted historical replay. Open and close are the first and last executed trade prices in a bucket. An up candle has close greater than open; a down candle has close less than open; an equal open and close is flat. These are trade-price candle bodies, not quote-midpoint returns or exchange-timestamp candles.

Only complete buckets inside the capture window enter the analysis. Empty buckets are invalid and are not forward-filled. The conservative main sample invalidates every bucket intersecting a recorded connection gap, connection-open marker, receipt-silence interval or trade-ID-gap candidate. Point markers invalidate their containing bucket. These exclusions are conservative: not every candidate proves missing trades.

There are 143 complete 10-minute buckets, covering 2026-11-12T05:00:00Z to 2026-11-13T04:50:00Z, exclusive. Eight intersect gap candidates, leaving 135 valid bars: 62 up, 72 down and one flat. Capture edges, invalid buckets and flats break streaks.

Mean streak lengths use fully observed runs that end directly in the opposite color. Runs touching an unknown boundary are censored. The 10-minute mean up streak is 54 bars across 30 qualifying runs, or 1.80 bars. The mean down streak is 50 bars across 29 qualifying runs, or 1.7241 bars. These run samples differ from the conditional-event samples below.

## 3. Main 10-minute results

A rolling pair means the last two adjacent candles have the specified color, and the next candle is also observed and valid. A longer run can supply several pairs; the opportunities can overlap.

```
Last two bars   Next up   Next down   Next flat   Total
Up, up               5          19           0      24
Down, down          16          12           1      29
```

After two up bars, the observed reversal frequency is 19/24 = 79.2%; continuation is 5/24 = 20.8%.

After two down bars, reversal is 16/29 = 55.2%; continuation is 12/29 = 41.4%; flat is 1/29 = 3.4%. In particular, 100% minus the 41.4% continuation rate is not all reversal: it also includes the flat bar.

For descriptive context, all valid 10-minute bars are down 72/135 = 53.3%, up 62/135 = 45.9%, and flat 1/135 = 0.7%. The conditional reversal rates exceed these corresponding unconditional color frequencies by 25.8 and 9.2 percentage points. Those baselines include a different eligibility set and are not matched controls or formal tests of incremental skill.

### A newly formed streak of exactly two

A different entry rule fires only when a new directional streak first reaches two candles. We require the immediately preceding candle to have the opposite color, and all four bars through the outcome must be valid.

```
Sequence before outcome   Next up   Next down   Next flat   Total
Down, up, up                    5          14           0      19
Up, down, down                  6           7           0      13
```

Under this definition, reversal after two up bars is 14/19 = 73.7%. Reversal after two down bars is only 6/13 = 46.2%. The corresponding continuation rates are 26.3% and 53.8%. A trader must choose between these two event definitions before testing a rule.

## 4. Other intervals and sensitivity

The same conservative candle-body procedure gives:

```
Bar size   Valid bars   Mean up run   Mean down run   UU -> U         DD -> D
10 sec          8149          1.79            1.94    637/1399 45.5%  839/1706 49.2%
1 min           1430          1.98            2.05    160/342  46.8%  180/368  48.9%
5 min            279          1.77            1.88     18/57   31.6%   27/64   42.2%
10 min           135          1.80            1.72      5/24   20.8%   12/29   41.4%
1 hour            17          2.00            2.00      1/2    50.0%    1/2    50.0%
```

The hourly event samples contain only two cases per condition and provide little guidance. At one minute, restricting to newly formed two-bar streaks yields about 50.3% continuation in each direction. The one-minute observations therefore do not show a strong third-bar continuation tendency.

Including observed bars that intersect gap candidates changes 10-minute candle-body reversal to 21/27 = 77.8% after two up bars and 20/36 = 55.6% after two down bars. The asymmetry remains descriptive rather than validated.

A separate sensitivity labels every bar by its close versus the previous bar's close. Both the conditioning bars and the outcome then have different definitions; the previous/current buckets must also be valid. Under this conservative close-to-close definition, reversal is 20/25 = 80.0% after two up moves but only 10/26 = 38.5% after two down moves.

This sensitivity does not turn the candle-body result into a trading return. It shows that the proposed two-down reversal tendency is not robust to a reasonable change in the measurement. All 20 interval, gap-policy and direction-definition combinations are retained in the results file, including one-, two- and three-bar conditions.

## 5. Can the observed rate justify a bet?

Not by itself. The two-up pattern is a reasonable paper-trading candidate; this sample is insufficient evidence for committing live capital to either rule.

A red next candle means its last executed price is below its first executed price. The study does not promise an obtainable fill at either price. It also does not directly measure the next close relative to the trader's actual entry, and it does not establish that a candle-color event matches a particular betting contract's strike, resolution time, price source or treatment of ties.

For a variable-payoff trade, positive expected net return requires:

```
p * average winning return - (1 - p) * average losing return - average cost > 0
```

This expression assumes outcomes are classified as wins/losses with positive average magnitudes and costs use the same return units. Flat outcomes require their own term or explicit settlement treatment. A high hit rate can still lose money if losses are larger than wins.

For a binary contract risking one unit to earn net profit b on a win and lose one unit on a loss, the break-even probability is 1/(1+b), before fees and ties. An 80% net-profit payout would require 55.6% wins. That payout is an arithmetic illustration, not an available quote; the observed sample frequency is not an established probability to insert into a live decision.

The owner's previously requested 0.15% and 0.25% fees are per fill. A two-sided round trip would cost approximately 0.30% or 0.50% before spread, slippage, funding or borrow, depending on the instrument. Those are cost scenarios, not verified current venue fees or proof of maker fills. A bearish forecast also does not create a short-selling facility for spot holdings. This streak study has not simulated fills, short availability, liquidation risk, trade sizing or net P&L.

## 6. Limits and a validation protocol

The strongest rate was identified after examining multiple intervals and an already studied day. The sample contains only 24 rolling two-up and 29 rolling two-down opportunities at ten minutes. Overlap and market-regime dependence prevent treating these as independent trials. The large raw tick count does not produce a large number of independent 10-minute events. No formal significance claim or independence-based confidence bound is made.

Before prospective evaluation, freeze the following candidate protocol. This is a proposal; no new forward test was started for this paper.

1. Fix the market, receipt-clock policy, UTC alignment, flat/gap treatment, and rolling-pair or new-streak event definition.
2. Test the two-up bearish candidate and the two-down bullish candidate separately. Do not pool them into a symmetric rule. Use an identical eligible-time unconditional baseline and a no-position baseline.
3. Resolve direction on fresh unseen days across market regimes. Retain every qualifying event and abstention. Group or block evaluation by day and handle overlapping positions explicitly.
4. For economic evaluation, define an obtainable post-signal entry and time-based exit, venue, quotes, fees, spread, slippage, short permissions and tie settlement before observing outcomes. Fix a sample-size/stopping rule; do not stop because the win rate temporarily looks favorable.
5. Report counts, return magnitudes, net P&L, downside, coverage and parameter changes alongside hit rate. Reserve an untouched confirmation period and account for the full family of tested rules.

This protocol is how the current observation could become a credible decision input. More sampling may confirm, weaken or reverse it.

## 7. Reproducibility and data availability

The original empirical study is stored in shared MongoDB as run:3768d71af70c8382f508829ab67f0f7b91b367174baa7c372c02d432439c1e3c, finished at revision 6. Its immutable artifacts are:

- Analysis source: art:b7b9b518c0c9baf5243a63fb39db79e5c2f2afdae3324cda691456811468074f.
- Full results: art:cdc43a1d1cc172598c31ea8e98595eb900f6c5a5076361e1d677e1c7f033034f.
- Original report: art:a66dd7bcaaea92c32d973960b78e1a0403fcf04a919d7668601ce236600bc773.

The paper publication run is run:d8e77d4b36700570cffa6d3ea515c46722d997347296de304beda966a69f7ced. MongoDB stores the canonical evidence and this paper. The website and repository copies are public publication projections. Artifact storage and an independent arithmetic review do not constitute peer review, a trusted literature qualification, or proof of a trading edge.

The public reproducibility package contains the full counts and a parameterized version of the original calculation. The code requires Python and NumPy, verifies input hashes, reads without modifying the original capture, and prints the same 20-combination results. Raw tick data remain in the owner's capture storage and MongoDB time-series collection; this publication does not distribute the raw tape. A reader needs those exact inputs to reproduce the trade-to-candle construction.

Public paper and reproducibility package:
[Paper source](https://github.com/mithudso/solmargintrader/blob/master/research/ZEC-TWO-BAR-REVERSAL.md)

[Code and complete counts](https://github.com/mithudso/solmargintrader/tree/master/research/zec-two-bar-reversal-20261114)

Original raw WAL SHA-256:
```
eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31
```

Accepted trade-tape SHA-256:
```
21db6ff5a1b6fdd12f887ef506f654ff634af3c355ca898d2f0838de09fd6f4c
```

The source and results were read back from MongoDB and matched exactly. The parameterized public calculation reproduced every retained combination and verified both input hashes with exit code 0. A separate read-only implementation previously matched all run means and conditional counts at 10 seconds, 1 minute, 5 minutes and 10 minutes.

## Conclusion

Two up 10-minute ZEC candles preceded a red candle unusually often in this one-day sample. The corresponding two-down rule was much weaker and changed substantially with event definitions. The defensible next step is frozen prospective evaluation with actual settlement and costs, rather than treating 79.2% as a dependable live success probability.
